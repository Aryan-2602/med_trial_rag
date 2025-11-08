"""Manifest schema for RAG index metadata."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class CorpusEntry(BaseModel):
    """Metadata for a single corpus (PDF or SAS)."""

    prefix: str = Field(..., description="S3 prefix for corpus files")
    files: list[str] = Field(..., description="List of required files (index.faiss, ids.jsonl, docs.jsonl)")
    dimension: int = Field(..., gt=0, description="Embedding dimension")
    count: int = Field(..., ge=0, description="Number of vectors in index")

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: list[str]) -> list[str]:
        """Ensure required files are present."""
        required = {"index.faiss", "ids.jsonl", "docs.jsonl"}
        if not required.issubset(set(v)):
            raise ValueError(f"Missing required files. Must include: {required}")
        return v


class Manifest(BaseModel):
    """Root manifest schema for RAG indices."""

    version: str = Field(..., description="Version identifier (e.g., v20251101)")
    corpora: dict[str, CorpusEntry] = Field(..., description="Corpus entries keyed by name (pdf, sas)")

    def get_corpus(self, name: str) -> CorpusEntry:
        """Get corpus entry by name, raising if not found."""
        if name not in self.corpora:
            raise ValueError(f"Corpus '{name}' not found in manifest")
        return self.corpora[name]

    def model_dump_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON."""
        return self.model_dump(mode="json")

