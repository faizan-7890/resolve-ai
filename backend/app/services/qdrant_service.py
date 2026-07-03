"""
Qdrant vector database service for ResolveAI RAG pipeline.

Handles collection management, vector upsert, and similarity search.
Degrades gracefully if Qdrant is unavailable — the app continues to work
without vector search (falls back to empty results).
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse
from app.core.config import settings


VECTOR_DIM = 128  # Must match AIService.get_embedding() output dimensions


class QdrantService:
    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._available: bool = False
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Qdrant. Sets _available flag."""
        try:
            if settings.QDRANT_HOST == ":memory:":
                self._client = QdrantClient(":memory:")
                self._available = True
                self._ensure_collection()
                print("[Qdrant] Connected to in-memory instance (:memory:)")
                return

            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=5,
            )
            # Quick health check
            self._client.get_collections()
            self._available = True
            self._ensure_collection()
            print(f"[Qdrant] Connected to {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except Exception as e:
            self._available = False
            print(f"[Qdrant] Not available ({e}). Vector search will be disabled.")

    @property
    def is_available(self) -> bool:
        return self._available

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        if not self._available:
            return

        collection_name = settings.QDRANT_COLLECTION
        try:
            collections = self._client.get_collections().collections
            existing_names = [c.name for c in collections]

            if collection_name not in existing_names:
                self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=VECTOR_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                print(f"[Qdrant] Created collection '{collection_name}' ({VECTOR_DIM}-dim, cosine)")
            else:
                print(f"[Qdrant] Collection '{collection_name}' already exists")
        except Exception as e:
            print(f"[Qdrant] Error creating collection: {e}")
            self._available = False

    def upsert_memory(
        self,
        memory_id: int,
        vector: List[float],
        user_id: int,
        problem_summary: str,
        solution_summary: str,
    ) -> bool:
        """Store a resolved problem's embedding in Qdrant.

        Returns True on success, False on failure (non-fatal).
        """
        if not self._available:
            return False

        try:
            self._client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    qmodels.PointStruct(
                        id=memory_id,
                        vector=vector,
                        payload={
                            "user_id": user_id,
                            "problem_summary": problem_summary,
                            "solution_summary": solution_summary,
                        },
                    )
                ],
            )
            return True
        except Exception as e:
            print(f"[Qdrant] Upsert failed for memory {memory_id}: {e}")
            return False

    def search_similar(
        self,
        query_vector: List[float],
        user_id: int,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Search for similar resolved problems, filtered by user.

        Returns a list of dicts with id, problem_summary, solution_summary, similarity.
        Returns empty list if Qdrant is unavailable.
        """
        if not self._available:
            return []

        try:
            results = self._client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=query_vector,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="user_id",
                            match=qmodels.MatchValue(value=user_id),
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
            )

            return [
                {
                    "id": point.id,
                    "problem_summary": point.payload.get("problem_summary", ""),
                    "solution_summary": point.payload.get("solution_summary", ""),
                    "similarity": round(point.score, 3),
                }
                for point in results.points
            ]
        except Exception as e:
            print(f"[Qdrant] Search failed: {e}")
            return []

    def delete_memory(self, memory_id: int) -> bool:
        """Remove a vector point from Qdrant.

        Returns True on success, False on failure (non-fatal).
        """
        if not self._available:
            return False

        try:
            self._client.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=qmodels.PointIdsList(points=[memory_id]),
            )
            return True
        except Exception as e:
            print(f"[Qdrant] Delete failed for memory {memory_id}: {e}")
            return False


# Singleton instance — initialized at module import
qdrant_service = QdrantService()
