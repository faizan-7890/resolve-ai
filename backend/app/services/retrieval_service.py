from sqlalchemy.orm import Session
from app.models.document import DocumentChunk
from app.services.embedding_service import get_embeddings

def retrieve_similar_chunks(db: Session, query: str, limit: int = 3) -> list[dict]:
    """
    Computes embedding of the query and runs a pgvector cosine similarity search
    against the document_chunks table, returning matched chunks with metadata.
    """
    # 1. Generate query embedding
    query_embedding = get_embeddings(query)
    
    # 2. Query document chunks ordered by pgvector cosine distance
    distance_expr = DocumentChunk.embedding.cosine_distance(query_embedding)
    
    # We join Document to load title/metadata if needed
    query_results = (
        db.query(DocumentChunk, distance_expr.label("distance"))
        .order_by(distance_expr)
        .limit(limit)
        .all()
    )
    
    # 3. Format results, mapping distance to cosine similarity score (1 - distance)
    results = []
    for chunk, distance in query_results:
        # Distance ranges from 0 (identical) to 2 (opposite). Cosine similarity score = 1 - distance
        similarity_score = 1.0 - float(distance) if distance is not None else 0.0
        
        results.append({
            "id": chunk.id,
            "document_id": chunk.document_id,
            "document_title": chunk.document.title if chunk.document else "Untitled",
            "content": chunk.content,
            "score": similarity_score
        })
        
    return results
