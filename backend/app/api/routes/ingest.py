from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embeddings
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ingest", tags=["ingest"])

class DocumentIngestIn(BaseModel):
    title: str
    content: str

@router.post("/", status_code=status.HTTP_201_CREATED)
def ingest_document(
    doc_in: DocumentIngestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests a knowledge base document, breaks it down into overlapping semantic chunks,
    generates 128-dimensional vector embeddings, and stores them in PostgreSQL using pgvector.
    """
    if not doc_in.title or not doc_in.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title and content are required."
        )

    # 1. Create Document header record
    db_doc = Document(
        title=doc_in.title,
        content=doc_in.content
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # 2. Split content into semantic chunks
    chunks = chunk_text(doc_in.content, chunk_size=500, chunk_overlap=100)

    # 3. Create document chunk records with generated embeddings
    chunk_count = 0
    for chunk_text_content in chunks:
        embedding = get_embeddings(chunk_text_content)
        db_chunk = DocumentChunk(
            document_id=db_doc.id,
            content=chunk_text_content,
            embedding=embedding
        )
        db.add(db_chunk)
        chunk_count += 1

    db.commit()

    return {
        "message": "Document successfully ingested, chunked, and embedded.",
        "document_id": db_doc.id,
        "chunks_count": chunk_count
    }
