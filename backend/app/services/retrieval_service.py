"""
RAG retrieval service — no pgvector required.

Uses in-Python cosine similarity computed over JSON-decoded embedding vectors
stored in the document_chunks.embedding Text column.
"""
import logging
from sqlalchemy.orm import Session
from app.models.document import DocumentChunk
from app.services.embedding_service import get_embedding_vector, decode_embedding, cosine_similarity

logger = logging.getLogger(__name__)


def retrieve_similar_chunks(db: Session, query: str, limit: int = 3) -> list[dict]:
    """
    Computes cosine similarity between the query embedding and all stored chunk
    embeddings in Python, returning the top-N most similar chunks.

    Works with plain PostgreSQL (no pgvector extension required).
    Embeddings are stored as JSON strings in the Text column.

    Args:
        db: SQLAlchemy database session
        query: The search query text
        limit: Maximum number of results to return

    Returns:
        List of dicts with keys: id, document_id, document_title, content, score
    """
    # 1. Generate query embedding (raw float list for comparison)
    query_vector = get_embedding_vector(query)

    if not query_vector:
        logger.warning("Could not generate query embedding — returning empty results.")
        return []

    # 2. Load all chunks from DB (only content + embedding columns needed)
    chunks = db.query(DocumentChunk).all()

    if not chunks:
        return []

    # 3. Compute cosine similarity in Python
    scored: list[tuple[DocumentChunk, float]] = []
    for chunk in chunks:
        chunk_vector = decode_embedding(chunk.embedding)
        if not chunk_vector:
            continue
        score = cosine_similarity(query_vector, chunk_vector)
        scored.append((chunk, score))

    # 4. Sort by descending similarity and take top-N
    scored.sort(key=lambda x: x[1], reverse=True)
    top_chunks = scored[:limit]

    # 5. Format results
    results = []
    for chunk, score in top_chunks:
        results.append({
            "id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": chunk.document.title if chunk.document else "Untitled",
            "content": chunk.content,
            "score": score
        })

    return results
