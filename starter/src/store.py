"""Store and search vectors using local Qdrant."""
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from .models import Chunk


class QdrantVectorStore:
    """Persistent vector store adapter using local Qdrant storage."""

    def __init__(self, storage_path: str = "./qdrant_db", dimensions: int = 384) -> None:
        self.storage_path = storage_path
        self.dimensions = dimensions
        self.client = QdrantClient(path=storage_path)

    def get_collection_name(self, strategy: str) -> str:
        return f"corpus_{strategy}"

    def create_collection(self, strategy: str) -> None:
        col_name = self.get_collection_name(strategy)
        if not self.client.collection_exists(col_name):
            self.client.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(size=self.dimensions, distance=Distance.COSINE),
            )

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Write chunks and vectors with stable IDs and metadata payload."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match vector count ({len(vectors)})")

        self.create_collection(strategy)
        col_name = self.get_collection_name(strategy)

        points = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            payload = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "source": chunk.source,
                "page": chunk.page,
                "text": chunk.text,
                **chunk.metadata,
            }
            points.append(
                PointStruct(
                    id=idx + 1,
                    vector=vec,
                    payload=payload,
                )
            )

        # Batch upsert
        self.client.upsert(collection_name=col_name, points=points)

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank by cosine similarity, optionally applying metadata filters, returning top-k."""
        col_name = self.get_collection_name(strategy)
        if not self.client.collection_exists(col_name):
            raise RuntimeError(f"Collection {col_name} does not exist. Run upsert first.")

        query_filter = None
        if filters:
            conditions = []
            for k, v in filters.items():
                conditions.append(
                    FieldCondition(key=k, match=MatchValue(value=v))
                )
            if conditions:
                query_filter = Filter(must=conditions)

        results = self.client.query_points(
            collection_name=col_name,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

        hits: list[dict[str, Any]] = []
        for pt in results.points:
            hits.append(
                {
                    "chunk_id": pt.payload.get("chunk_id", str(pt.id)),
                    "score": float(pt.score),
                    "text": pt.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in pt.payload.items() if k not in ("text", "chunk_id")
                    },
                }
            )
        return hits
