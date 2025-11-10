"""Pydantic models for API requests and responses."""

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    query: str = Field(..., description="User query text", min_length=1)
    top_k: Optional[int] = Field(None, description="Number of results per corpus (default from config)")


class Citation(BaseModel):
    """Citation model for answer sources."""

    corpus: str = Field(..., description="Corpus name (pdf or sas)")
    chunk_id: str = Field(..., description="Chunk identifier")
    score: float = Field(..., description="Relevance score")
    snippet: str = Field(..., description="Text snippet from document")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    answer: str = Field(..., description="Generated answer")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    retriever: str = Field(..., description="Retriever type")
    manifest_version: str = Field(..., description="Version identifier (vector_db for Chroma)")
    corpora: dict[str, int] = Field(..., description="Corpus name to document count mapping")
    loaded: bool = Field(..., description="Whether retriever is loaded")

