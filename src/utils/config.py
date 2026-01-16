"""Configuration management from environment variables."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables."""

    # Local mode configuration (primary mode)
    # S3 fields kept for potential future AWS support but not currently used
    rag_bucket: Optional[str] = None
    rag_manifest_key: str = "rag/manifest.json"

    # Embedding Model
    embed_model: str = "text-embedding-3-small"

    # OpenAI API (optional)
    openai_api_key: Optional[str] = None

    # Retrieval Configuration
    max_tokens: int = 2048
    top_k: int = 5

    # Testing
    embed_offline: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        openai_api_key = os.getenv("OPENAI_API_KEY")

        return cls(
            rag_bucket=os.getenv("RAG_BUCKET"),  # Optional, not used in local mode
            rag_manifest_key=os.getenv("RAG_MANIFEST_KEY", "rag/manifest.json"),
            embed_model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
            openai_api_key=openai_api_key,
            max_tokens=int(os.getenv("MAX_TOKENS", "2048")),
            top_k=int(os.getenv("TOP_K", "5")),
            embed_offline=os.getenv("EMBED_OFFLINE", "0") == "1",
        )

    def validate(self) -> None:
        """Validate configuration values."""
        if self.top_k < 1:
            raise ValueError("TOP_K must be >= 1")

