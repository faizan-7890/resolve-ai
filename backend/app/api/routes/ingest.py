from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embeddings
from app.services.file_extractor import extract_text_from_bytes
from app.core.exceptions import EmbeddingServiceError, DatabaseError, ValidationError, exception_to_http_exception
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.validators import CommonValidators

router = APIRouter(prefix="/ingest", tags=["ingest"])

class DocumentIngestIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    content: str = Field(..., min_length=10, max_length=100000)
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        v = CommonValidators.sanitize_text(v)
        CommonValidators.validate_non_empty_string(v, "title", min_length=3, max_length=500)
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        v = CommonValidators.sanitize_text(v)
        CommonValidators.validate_non_empty_string(v, "content", min_length=10, max_length=100000)
        return v

@router.post("/", status_code=status.HTTP_201_CREATED)
def ingest_document(
    doc_in: DocumentIngestIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests a knowledge base document, breaks it down into overlapping semantic chunks,
    generates 128-dimensional vector embeddings, and stores them in PostgreSQL using pgvector.
    
    Raises:
        HTTPException: For validation, embedding, or database errors
    """
    try:
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
            try:
                embedding = get_embeddings(chunk_text_content)
                db_chunk = DocumentChunk(
                    document_id=db_doc.id,
                    content=chunk_text_content,
                    embedding=embedding
                )
                db.add(db_chunk)
                chunk_count += 1
            except EmbeddingServiceError as e:
                # Rollback if embedding generation fails
                db.rollback()
                raise exception_to_http_exception(e)

        db.commit()

        return {
            "message": "Document successfully ingested, chunked, and embedded.",
            "document_id": db_doc.id,
            "chunks_count": chunk_count
        }
    
    except EmbeddingServiceError as e:
        raise exception_to_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        db_error = DatabaseError(f"Failed to ingest document: {str(e)}")
        raise exception_to_http_exception(db_error)


MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests a knowledge base document via file upload.
    Supports PDF (.pdf), Word (.docx), and plain text (.txt, .md, .csv) files up to 10MB.

    Automatically extracts text, chunks it, generates embeddings, and stores in PostgreSQL.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 10MB (received {len(file_bytes) / 1024 / 1024:.1f}MB)."
        )

    # Extract text from the uploaded file
    try:
        content = extract_text_from_bytes(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(content.strip()) < 10:
        raise HTTPException(status_code=422, detail="Extracted text is too short to ingest (minimum 10 characters).")

    # Use the filename (without extension) as the document title
    import os
    title = os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").strip()
    if len(title) < 3:
        title = file.filename

    # Run the same chunk → embed → store pipeline as the JSON ingest endpoint
    try:
        db_doc = Document(title=title, content=content)
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)

        chunks = chunk_text(content, chunk_size=500, chunk_overlap=100)
        chunk_count = 0

        for chunk_text_content in chunks:
            try:
                embedding = get_embeddings(chunk_text_content)
                db.add(DocumentChunk(
                    document_id=db_doc.id,
                    content=chunk_text_content,
                    embedding=embedding
                ))
                chunk_count += 1
            except EmbeddingServiceError as e:
                db.rollback()
                raise exception_to_http_exception(e)

        db.commit()

        return {
            "message": f"File '{file.filename}' ingested successfully.",
            "document_id": db_doc.id,
            "document_title": title,
            "chunks_count": chunk_count,
            "file_size_kb": round(len(file_bytes) / 1024, 1)
        }

    except EmbeddingServiceError as e:
        raise exception_to_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise exception_to_http_exception(DatabaseError(f"Failed to ingest uploaded file: {str(e)}"))
