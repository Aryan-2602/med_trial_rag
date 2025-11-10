"""Base protocol for retrievers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Retriever(Protocol):
    """Protocol for RAG retrievers."""

    def load(self) -> None:
        """
        Load/initialize the retriever.
        """
        ...

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Search for relevant documents.

        Args:
            query: Query text
            top_k: Number of results per corpus

        Returns:
            List of dicts with keys: corpus, chunk_id, score, text, metadata
        """
        ...

    def close(self) -> None:
        """Clean up resources."""
        ...

