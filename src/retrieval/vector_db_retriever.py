"""Vector database retriever using Chroma."""

from typing import Any

from src.utils.config import Config
from src.utils.logging import get_logger, log_timing
from src.utils.vector_db import VectorDBClient

logger = get_logger(__name__)


class VectorDBRetriever:
    """Retriever that uses Chroma vector database for PDF documents."""

    def __init__(self, config: Config | None = None):
        """
        Initialize vector DB retriever.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        self.config = config or Config.from_env()
        self.vector_db = VectorDBClient(self.config)
        self.loaded = False
        self.corpus_counts: dict[str, int] = {}

    def load(self) -> None:
        """Load/initialize the vector database."""
        try:
            collection = self.vector_db.get_or_create_collection()
            count = collection.count()
            self.corpus_counts["pdf"] = count
            self.loaded = True
            logger.info("vector_db_loaded", count=count)
        except Exception as e:
            logger.error("vector_db_load_failed", error=str(e))
            raise

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search for similar documents using simple cosine similarity.

        Args:
            query: Query text
            top_k: Number of results to return

        Returns:
            List of results with 'text', 'metadata', 'score', 'corpus', 'chunk_id'
        """
        if not self.loaded:
            self.load()

        # Check if collection has documents
        collection = self.vector_db.get_or_create_collection()
        if collection.count() == 0:
            logger.warning("vector_db_empty", query_preview=query[:50])
            return []

        with log_timing("vector_db_search"):
            try:
                results = self.vector_db.search(query, n_results=top_k)
            except Exception as e:
                logger.error("vector_db_search_error", error=str(e), query_preview=query[:50])
                return []

        # Check if we got any results
        if not results["ids"] or len(results["ids"]) == 0:
            logger.warning("vector_db_no_results", query_preview=query[:50])
            return []

        # Convert to standard format
        formatted_results = []
        for i, (doc_id, doc_text, metadata, distance) in enumerate(
            zip(
                results["ids"],
                results["documents"],
                results["metadatas"],
                results["distances"],
            )
        ):
            # ChromaDB uses cosine distance (0 = identical, 2 = opposite)
            # Convert to similarity score (higher is better)
            # Cosine similarity = 1 - cosine_distance
            # For cosine: distance ranges from 0 to 2, similarity = 1 - (distance/2)
            # Or simpler: similarity = 1 - distance (if distance <= 1)
            # Actually, ChromaDB with OpenAI embeddings uses cosine distance
            # where 0 = identical, 1 = orthogonal, 2 = opposite
            # So similarity = 1 - distance works for most cases
            similarity_score = max(0.0, 1.0 - float(distance))
            
            formatted_results.append({
                "text": doc_text,
                "metadata": metadata or {},
                "score": float(similarity_score),
                "corpus": "pdf",
                "chunk_id": doc_id,
            })

        logger.info(
            "vector_db_search_complete",
            query_preview=query[:50],
            results=len(formatted_results),
            top_score=formatted_results[0]["score"] if formatted_results else 0.0,
        )
        return formatted_results

    def close(self) -> None:
        """Clean up resources."""
        # Chroma handles cleanup automatically
        self.loaded = False

