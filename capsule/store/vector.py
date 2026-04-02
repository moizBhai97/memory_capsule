"""
ChromaDB vector store for semantic search.
Stores embeddings of capsule content.
Future: swap ChromaDB for Qdrant, Pinecone, or pgvector with zero pipeline changes.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, chroma_path: str):
        import chromadb
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=chroma_path)
        self._collection = self._client.get_or_create_collection(
            name="capsules",
            metadata={"hnsw:space": "cosine"},  # cosine similarity for text
        )
        logger.info("Vector store ready: %s (%s vectors)", chroma_path, self._collection.count())

    def upsert(self, capsule_id: str, embedding: list[float], metadata: dict) -> None:
        """Store or update embedding for a capsule."""
        self._collection.upsert(
            ids=[capsule_id],
            embeddings=[embedding],
            metadatas=[_sanitize_metadata(metadata)],
        )

    def search(
        self,
        query_embedding: list[float],
        limit: int = 20,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Semantic similarity search.
        Returns list of {"id": str, "score": float, "metadata": dict}
        where score is 1.0 = perfect match, 0.0 = no match (cosine similarity)
        """
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(limit, self._collection.count() or 1),
            "include": ["metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        if not results["ids"] or not results["ids"][0]:
            return []

        return [
            {
                "id": id_,
                "score": round(1 - dist, 4),  # convert distance to similarity score
                "metadata": meta,
            }
            for id_, dist, meta in zip(
                results["ids"][0],
                results["distances"][0],
                results["metadatas"][0],
            )
        ]

    def delete(self, capsule_id: str) -> None:
        self._collection.delete(ids=[capsule_id])

    def count(self) -> int:
        return self._collection.count()


def _sanitize_metadata(metadata: dict) -> dict:
    """ChromaDB only accepts str, int, float, bool in metadata."""
    clean = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif isinstance(v, list):
            clean[k] = ",".join(str(i) for i in v)  # join lists as comma string
        elif v is None:
            clean[k] = ""
        else:
            clean[k] = str(v)
    return clean
