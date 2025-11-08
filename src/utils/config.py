"""Configuration management from environment variables."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables."""

    # S3 Configuration
    rag_bucket: str
    rag_manifest_key: str = "rag/manifest.json"

    # Embedding Model
    embed_model: str = "text-embedding-3-small"

    # OpenAI API (optional)
    openai_api_key: Optional[str] = None

    # Retrieval Configuration
    use_retriever: str = "faiss"
    max_tokens: int = 2048
    top_k: int = 5
    fusion_k: int = 8

    # Testing
    embed_offline: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        rag_bucket = os.getenv("RAG_BUCKET")
        if not rag_bucket:
            raise ValueError("RAG_BUCKET environment variable is required")

        openai_api_key = os.getenv("OPENAI_API_KEY")

        return cls(
            rag_bucket=rag_bucket,
            rag_manifest_key=os.getenv("RAG_MANIFEST_KEY", "rag/manifest.json"),
            embed_model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
            openai_api_key=openai_api_key,
            use_retriever=os.getenv("USE_RETRIEVER", "faiss"),
            max_tokens=int(os.getenv("MAX_TOKENS", "2048")),
            top_k=int(os.getenv("TOP_K", "5")),
            fusion_k=int(os.getenv("FUSION_K", "8")),
            embed_offline=os.getenv("EMBED_OFFLINE", "0") == "1",
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.rag_bucket:
            raise ValueError("RAG_BUCKET is required")
        if self.top_k < 1:
            raise ValueError("TOP_K must be >= 1")
        if self.fusion_k < 1:
            raise ValueError("FUSION_K must be >= 1")

