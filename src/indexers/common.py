"""Common utilities for indexers."""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from src.utils.logging import get_logger

logger = get_logger(__name__)


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> list[str]:
    """
    Chunk text into smaller pieces with overlap.

    Uses character-based estimation (roughly 4 chars per token).

    Args:
        text: Input text
        max_tokens: Maximum tokens per chunk
        overlap: Overlap in tokens between chunks

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    # Rough estimation: 4 characters per token
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(".")
            last_newline = chunk.rfind("\n")
            break_point = max(last_period, last_newline)
            if break_point > max_chars * 0.5:  # Only break if reasonable
                chunk = chunk[: break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap_chars

        if start >= len(text):
            break

    logger.debug("chunked_text", original_len=len(text), chunks=len(chunks))
    return chunks


def write_jsonl(path: str, items: list[dict[str, Any]]) -> None:
    """
    Write list of dicts to JSONL file.

    Args:
        path: Output file path
        items: List of dicts to write
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logger.debug("wrote_jsonl", path=path, count=len(items))


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """
    Build FAISS index with L2-normalized vectors using IndexFlatIP.

    Args:
        vectors: Numpy array of shape (n, dimension) with vectors

    Returns:
        FAISS IndexFlatIP index
    """
    if vectors.shape[0] == 0:
        raise ValueError("Cannot build index from empty vectors")

    dimension = vectors.shape[1]

    # L2 normalize vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # Avoid division by zero
    normalized_vectors = vectors / norms

    # Create IndexFlatIP (inner product for cosine similarity)
    index = faiss.IndexFlatIP(dimension)

    # Ensure vectors are float32 and contiguous
    normalized_vectors = np.ascontiguousarray(normalized_vectors.astype(np.float32))

    # Add vectors to index
    index.add(normalized_vectors)

    logger.info("built_faiss_index", dimension=dimension, count=index.ntotal)

    return index

