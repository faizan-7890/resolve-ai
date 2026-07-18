import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.models.ticket import Ticket, ClarificationQuestion, TicketActivityLog
from app.models.document import Document, DocumentChunk
from app.api.deps import get_current_user
from app.models.user import User
from app.services.retrieval_service import retrieve_similar_chunks
from app.services.agent_service import run_agent_triage, stream_agent_triage
from app.services.embedding_service import get_embeddings
from app.api.routes.ws import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tickets"])

class TicketCreate(BaseModel):
    title: str
    description: str
    category: Optional[str] = "General"
    urgency: Optional[str] = "Medium"

class ClarificationResponse(BaseModel):
    answer: str

class AnswerItem(BaseModel):
    clarification_id: int
    answer: str

class ClarificationAnswerPayload(BaseModel):
    answers: List[AnswerItem]

@router.post("/", response_model=None, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_in: TicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a new customer support ticket and logs the intake activity.
    """
    ticket = Ticket(
        user_id=current_user.id,
        title=ticket_in.title,
        description=ticket_in.description,
        category=ticket_in.category,
        urgency=ticket_in.urgency,
        status="Open"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Add activity log
    log = TicketActivityLog(
        ticket_id=ticket.id,
        action="Created",
        detail=f"Ticket intake registered successfully for user {current_user.email}."
    )
    db.add(log)
    db.commit()
    
    background_tasks.add_task(
        manager.broadcast,
        {"type": "ticket_created", "ticket_id": ticket.id, "status": ticket.status}
    )
    
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "urgency": ticket.urgency,
        "status": ticket.status,
        "created_at": ticket.created_at
    }

@router.get("/", response_model=None)
def list_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Lists support tickets. Admins see all tickets, standard users see their own.
    Supports optional ?status= filter and ?search= keyword search on title/description.
    """
    if current_user.role == "admin":
        query = db.query(Ticket)
    else:
        query = db.query(Ticket).filter(Ticket.user_id == current_user.id)

    if status:
        query = query.filter(Ticket.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Ticket.title.ilike(search_term) | Ticket.description.ilike(search_term)
        )

    tickets = query.order_by(Ticket.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "urgency": t.urgency,
            "status": t.status,
            "created_at": t.created_at
        } for t in tickets
    ]

@router.get("/{ticket_id}", response_model=None)
def get_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches the details of a single ticket including activity logs, clarifications,
    and mock structures for dashboard compatibility.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
        
    if current_user.role != "admin" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this ticket."
        )
        
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "urgency": ticket.urgency,
        "status": ticket.status,
        "resolution": ticket.resolution,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "clarifications": [
            {
                "id": c.id,
                "question": c.question,
                "answer": c.answer,
                "asked_at": c.asked_at
            } for c in ticket.clarifications
        ],
        "activity_logs": [
            {
                "id": l.id,
                "action": l.action,
                "detail": l.detail,
                "created_at": l.created_at
            } for l in ticket.activity_logs
        ],
        # Compatibility structures for UI pages (SWOT boards and action timelines)
        "diagnoses": [
            {
                "id": 1,
                "root_causes": json.dumps(["Retrieval mapping matched", "Ticket routing triage completed"]),
                "swot_analysis": json.dumps({
                    "strengths": f"RAG answered ticket with confidence.",
                    "weaknesses": "RAG limited by knowledge article coverage.",
                    "opportunities": "Log resolutions back to postgres document store.",
                    "threats": "NIM endpoint connectivity rate limits."
                }),
                "first_principles": json.dumps(["Tickets must evaluate automatically against pgvector doc chunk similarities."]),
                "created_at": ticket.created_at.isoformat()
            }
        ] if ticket.status in ("Resolved", "Escalated") else [],
        "solutions": [
            {
                "id": 1,
                "title": "AI Support Ticket Resolution Plan",
                "strategy_details": ticket.resolution or "Resolution completed.",
                "score": 9.5,
                "impact": 9.0,
                "confidence": 9.5,
                "risk": 1.0,
                "constraints": "Standard corporate escalation guidelines.",
                "selected": True
            }
        ] if ticket.status == "Resolved" else [],
        "tasks": [
            {
                "id": 1,
                "title": "Check resolved solution in customer client profile",
                "status": "Done" if ticket.status == "Resolved" else "Pending",
                "priority": "High",
                "timeline": "Immediate",
                "created_at": ticket.created_at.isoformat()
            }
        ]
    }

@router.delete("/{ticket_id}", response_model=None)
def delete_ticket(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a ticket.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
        
    if current_user.role != "admin" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this ticket."
        )
        
    db.delete(ticket)
    db.commit()
    
    background_tasks.add_task(
        manager.broadcast,
        {"type": "ticket_deleted", "ticket_id": ticket_id}
    )
    return {"message": "Ticket deleted successfully."}

@router.post("/{ticket_id}/clarify", response_model=None)
def submit_clarification_response(
    ticket_id: int,
    clarification_in: ClarificationResponse,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows customers to submit answers to clarification questions asked by the agent.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
        
    if current_user.role != "admin" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized."
        )
        
    question = (
        db.query(ClarificationQuestion)
        .filter(ClarificationQuestion.ticket_id == ticket_id, ClarificationQuestion.answer.is_(None))
        .order_by(ClarificationQuestion.asked_at.desc())
        .first()
    )
    
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending clarification question was found for this ticket."
        )
        
    question.answer = clarification_in.answer
    ticket.status = "Open"
    
    log = TicketActivityLog(
        ticket_id=ticket.id,
        action="Clarified",
        detail=f"Customer submitted response to clarification question: {clarification_in.answer}"
    )
    db.add(log)
    db.commit()
    
    background_tasks.add_task(
        manager.broadcast,
        {"type": "ticket_updated", "ticket_id": ticket_id, "status": ticket.status}
    )
    
    return {"message": "Clarification answer submitted successfully. Ticket status returned to Open."}

@router.post("/{ticket_id}/clarify/generate", response_model=None)
def generate_clarification_questions(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a clarification question for vague queries.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    pending = db.query(ClarificationQuestion).filter(
        ClarificationQuestion.ticket_id == ticket_id,
        ClarificationQuestion.answer.is_(None)
    ).first()
    
    if not pending:
        # Default fallback question or LLM custom generated
        question_text = "Could you please elaborate on your request or specify your account username so we can assist you?"
        try:
            from app.services.llm_service import generate_llm_response
            system_prompt = "You are a customer support agent. Generate a single clarification question about the user's ticket."
            user_prompt = f"Ticket: {ticket.title}\n{ticket.description}"
            question_text = generate_llm_response(system_prompt, user_prompt)
        except Exception:
            pass
            
        pending = ClarificationQuestion(ticket_id=ticket_id, question=question_text)
        db.add(pending)
        ticket.status = "Awaiting Clarification"
        
        # Log activity
        log = TicketActivityLog(
            ticket_id=ticket_id,
            action="Clarification Requested",
            detail=f"Clarification generated: {question_text}"
        )
        db.add(log)
        db.commit()
        
        background_tasks.add_task(
            manager.broadcast,
            {"type": "ticket_updated", "ticket_id": ticket_id, "status": ticket.status}
        )
        
    return {"message": "Clarifications generated successfully."}

@router.post("/{ticket_id}/clarify/answer", response_model=None)
def answer_clarification_questions(
    ticket_id: int,
    payload: ClarificationAnswerPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handles bulk clarification answers sent from React Workspace interface.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    for item in payload.answers:
        q = db.query(ClarificationQuestion).filter(ClarificationQuestion.id == item.clarification_id).first()
        if q:
            q.answer = item.answer
            
    ticket.status = "Open"
    
    log = TicketActivityLog(
        ticket_id=ticket_id,
        action="Clarified",
        detail="Customer answered pending clarification questions."
    )
    db.add(log)
    db.commit()
    
    background_tasks.add_task(
        manager.broadcast,
        {"type": "ticket_updated", "ticket_id": ticket_id, "status": ticket.status}
    )
    
    return {"message": "Clarifications submitted successfully."}

@router.post("/{ticket_id}/diagnose", response_model=None)
def run_triage_diagnose_pipeline(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes RAG context retrieval and LangGraph Triage on-demand when "Run AI Diagnosis"
    is selected in the React frontend.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    query_text = f"Title: {ticket.title}\nDescription: {ticket.description}"
    
    # Retrieve similar knowledge base chunks
    retrieved_chunks = retrieve_similar_chunks(db, query_text, limit=3)
    context_str = "\n\n".join([c["content"] for c in retrieved_chunks])
    
    # Triage via LangGraph
    agent_output = run_agent_triage(query_text, context_str)
    decision = agent_output["decision"]
    response_text = agent_output["response"]
    
    # Apply updates
    if decision == "Answer":
        ticket.resolution = response_text
        ticket.status = "Resolved"
        log = TicketActivityLog(
            ticket_id=ticket.id,
            action="Resolved",
            detail=f"AI Agent resolved ticket. Response: {response_text}"
        )
        db.add(log)
        
        # Save to KB (Logback)
        try:
            kb_title = f"Resolved Ticket #{ticket.id}: {ticket.title}"
            kb_content = f"Customer Ticket Description:\n{ticket.description}\n\nResolution:\n{response_text}"
            kb_doc = Document(title=kb_title, content=kb_content)
            db.add(kb_doc)
            db.commit()
            db.refresh(kb_doc)
            
            from app.services.chunking import chunk_text
            chunks = chunk_text(kb_content, chunk_size=500, chunk_overlap=100)
            for c_text in chunks:
                c_emb = get_embeddings(c_text)
                c_chunk = DocumentChunk(
                    document_id=kb_doc.id,
                    content=c_text,
                    embedding=c_emb
                )
                db.add(c_chunk)
        except Exception as e:
            logger.error(f"Failed to log ticket #{ticket.id} back to KB: {e}")
            
    elif decision == "Clarify":
        ticket.status = "Awaiting Clarification"
        clarification = ClarificationQuestion(ticket_id=ticket.id, question=response_text)
        db.add(clarification)
        log = TicketActivityLog(
            ticket_id=ticket.id,
            action="Awaiting Clarification",
            detail=f"AI Agent requested clarification: {response_text}"
        )
        db.add(log)
        
    elif decision == "Escalate":
        ticket.status = "Escalated"
        log = TicketActivityLog(
            ticket_id=ticket.id,
            action="Escalated",
            detail=f"AI Agent escalated ticket. Reason: {response_text}"
        )
        db.add(log)
        
    db.commit()
    db.refresh(ticket)
    
    background_tasks.add_task(
        manager.broadcast,
        {"type": "ticket_updated", "ticket_id": ticket_id, "status": ticket.status}
    )
    
    # Return mock diagnosis payload so the frontend visual boards render correctly
    return {
        "id": 1,
        "root_causes": json.dumps(["Automated support evaluation complete."]),
        "swot_analysis": json.dumps({
            "strengths": "RAG answering logic verified.",
            "weaknesses": "Dependent on database document contents.",
            "opportunities": "Feedback loop saves resolved tickets.",
            "threats": "Empty knowledge base matches."
        }),
        "first_principles": json.dumps(["Support tickets must resolve or route immediately."])
    }


@router.get("/{ticket_id}/diagnose/stream", response_model=None)
async def stream_triage_diagnose(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    SSE (Server-Sent Events) endpoint that streams LangGraph agent node transitions live.
    Frontend connects via EventSource and receives step-by-step progress events.

    Event format: data: {"step": "evaluator", "status": "running", ...}
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    query_text = f"Title: {ticket.title}\nDescription: {ticket.description}"

    # Retrieve knowledge base context (done once before streaming starts)
    retrieved_chunks = retrieve_similar_chunks(db, query_text, limit=3)
    context_str = "\n\n".join(
        [f"[Doc: {c.get('document_title', 'KB')}] {c['content']}" for c in retrieved_chunks]
    ) or "No relevant knowledge base context found."

    async def event_generator():
        async for event_str in stream_agent_triage(query_text, context_str):
            yield event_str

        # After streaming completes, persist the result
        # Re-run a quick synchronous triage for DB persistence
        try:
            agent_output = run_agent_triage(query_text, context_str)
            decision = agent_output["decision"]
            response_text = agent_output["response"]

            if decision == "Answer":
                ticket.resolution = response_text
                ticket.status = "Resolved"
                db.add(TicketActivityLog(
                    ticket_id=ticket.id,
                    action="Resolved",
                    detail=f"AI Agent resolved ticket: {response_text[:200]}"
                ))
            elif decision == "Clarify":
                ticket.status = "Awaiting Clarification"
                db.add(ClarificationQuestion(ticket_id=ticket.id, question=response_text))
                db.add(TicketActivityLog(
                    ticket_id=ticket.id,
                    action="Awaiting Clarification",
                    detail=f"AI Agent requested clarification: {response_text[:200]}"
                ))
            elif decision == "Escalate":
                ticket.status = "Escalated"
                db.add(TicketActivityLog(
                    ticket_id=ticket.id,
                    action="Escalated",
                    detail=f"AI Agent escalated ticket: {response_text[:200]}"
                ))
            db.commit()
            
            await manager.broadcast(
                {"type": "ticket_updated", "ticket_id": ticket_id, "status": ticket.status}
            )
        except Exception as e:
            logger.error(f"SSE stream: failed to persist triage result for ticket {ticket_id}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/{ticket_id}/similar", response_model=None)
def get_similar_vector_matches(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches pgvector similarity matches of other resolved tickets/policies.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    similar = retrieve_similar_chunks(db, ticket.description, limit=3)
    return [
        {
            "id": s["id"],
            "similarity": s["score"],
            "problem_summary": s["content"],
            "solution_summary": f"Source KB document: {s['document_title']}"
        } for s in similar
    ]

@router.get("/{ticket_id}/activity", response_model=None)
def get_ticket_activity_logs(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns audit action logs.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    return [
        {
            "id": l.id,
            "action": l.action,
            "detail": l.detail,
            "created_at": l.created_at.isoformat()
        } for l in ticket.activity_logs
    ]

@router.get("/{ticket_id}/export", response_model=None)
def export_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generates a downloadable markdown summary report.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    report = (
        f"# ResolveAI Support Ticket Report\n\n"
        f"- **Ticket ID**: #{ticket.id}\n"
        f"- **Title**: {ticket.title}\n"
        f"- **Status**: {ticket.status}\n"
        f"- **Category**: {ticket.category}\n"
        f"- **Urgency**: {ticket.urgency}\n"
        f"- **Created At**: {ticket.created_at.isoformat()}\n\n"
        f"## Customer Query Description\n{ticket.description}\n\n"
    )
    if ticket.resolution:
        report += f"## AI Resolution Summary\n{ticket.resolution}\n\n"
        
    report += "## Support Activity Logs\n"
    for log in ticket.activity_logs:
        report += f"- [{log.created_at.isoformat()}] **{log.action}**: {log.detail}\n"
        
    return Response(content=report, media_type="text/markdown")
