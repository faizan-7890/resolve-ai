import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.ticket import Ticket, ClarificationQuestion, TicketActivityLog
from app.models.document import Document, DocumentChunk
from app.services.retrieval_service import retrieve_similar_chunks
from app.services.agent_service import run_agent_triage
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embeddings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

class QueryRequest(BaseModel):
    query: Optional[str] = None
    ticket_id: Optional[int] = None

@router.post("/", response_model=None)
def query_or_triage_ticket(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG Triage Pipeline:
    Ingest user query/ticket description -> run pgvector similarity search ->
    triage via LangGraph workflow -> Answer/Clarify/Escalate.
    If a ticket_id is provided, updates status/resolution/clarifications in PostgreSQL
    and logs resolved tickets back into the knowledge base.
    """
    query_text = payload.query
    ticket = None

    # 1. Resolve ticket if ticket_id is provided
    if payload.ticket_id is not None:
        ticket = db.query(Ticket).filter(Ticket.id == payload.ticket_id).first()
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticket #{payload.ticket_id} not found."
            )
        
        # Verify user permission
        if current_user.role != "admin" and ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this ticket."
            )
        
        # Override query_text using ticket description
        query_text = f"Title: {ticket.title}\nDescription: {ticket.description}"

    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either query or ticket_id must be provided."
        )

    # 2. Retrieve context chunks via pgvector similarity search
    retrieved_chunks = retrieve_similar_chunks(db, query_text, limit=3)
    
    # 3. Concatenate chunks to form retrieval context
    context_str = "\n\n".join(
        [f"[Doc: {chunk['document_title']}] {chunk['content']}" for chunk in retrieved_chunks]
    )
    if not context_str:
        context_str = "No relevant corporate policies or FAQ documentation found."

    # 4. Run LangGraph agent triage workflow
    agent_output = run_agent_triage(query_text, context_str)
    decision = agent_output["decision"]
    response_text = agent_output["response"]

    # 5. Process state updates if ticket-based
    if ticket:
        if decision == "Answer":
            ticket.resolution = response_text
            ticket.status = "Resolved"
            
            # Log resolution activity
            log = TicketActivityLog(
                ticket_id=ticket.id,
                action="Resolved",
                detail=f"AI Agent resolved ticket. Response: {response_text}"
            )
            db.add(log)
            
            # Logback resolved ticket to Knowledge Base for future retrieval
            try:
                kb_title = f"Resolved Ticket #{ticket.id}: {ticket.title}"
                kb_content = f"Customer Ticket Description:\n{ticket.description}\n\nAI Agent Resolution:\n{response_text}"
                
                # Save Document
                kb_doc = Document(title=kb_title, content=kb_content)
                db.add(kb_doc)
                db.commit()
                db.refresh(kb_doc)
                
                # Chunk, embed and save chunks
                chunks = chunk_text(kb_content, chunk_size=500, chunk_overlap=100)
                for c_text in chunks:
                    c_emb = get_embeddings(c_text)
                    c_chunk = DocumentChunk(
                        document_id=kb_doc.id,
                        content=c_text,
                        embedding=c_emb
                    )
                    db.add(c_chunk)
                
                logger.info(f"Successfully logged ticket #{ticket.id} back to Knowledge Base.")
            except Exception as e:
                logger.error(f"Failed to log resolved ticket #{ticket.id} back to KB: {e}")
                
        elif decision == "Clarify":
            ticket.status = "Awaiting Clarification"
            
            # Save clarification question
            clarification = ClarificationQuestion(
                ticket_id=ticket.id,
                question=response_text
            )
            db.add(clarification)
            
            # Log activity
            log = TicketActivityLog(
                ticket_id=ticket.id,
                action="Awaiting Clarification",
                detail=f"AI Agent requested clarification: {response_text}"
            )
            db.add(log)
            
        elif decision == "Escalate":
            ticket.status = "Escalated"
            
            # Log activity
            log = TicketActivityLog(
                ticket_id=ticket.id,
                action="Escalated",
                detail=f"AI Agent escalated ticket. Reason: {response_text}"
            )
            db.add(log)
            
        db.commit()

    return {
        "decision": decision,
        "response": response_text,
        "retrieved_context": retrieved_chunks
    }
