"""Embedding utilities for text to vectors."""

import hashlib
import os

import numpy as np
from openai import OpenAI

from src.utils.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _deterministic_embedding(text: str, dimension: int = 1536) -> np.ndarray:
    """
    Generate deterministic embedding for testing.

    Uses hash-based seeding to create consistent vectors.
    """
    seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = np.random.RandomState(seed=seed)
    vec = rng.randn(dimension).astype(np.float32)
    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def embed_texts(texts: list[str], config: Config | None = None, batch_size: int = 1000) -> np.ndarray:
    """
    Embed multiple texts into vectors with batching to handle API limits.

    Args:
        texts: List of text strings
        config: Config instance (uses Config.from_env() if None)
        batch_size: Number of texts to process per API call (default 1000)

    Returns:
        Numpy array of shape (len(texts), dimension) with L2-normalized vectors
    """
    if config is None:
        config = Config.from_env()

    if config.embed_offline:
        logger.debug("using_offline_embeddings", count=len(texts))
        vectors = np.array([_deterministic_embedding(text) for text in texts])
        return vectors

    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY required when EMBED_OFFLINE=0")

    # Create client with timeout to avoid hanging
    client = OpenAI(
        api_key=config.openai_api_key,
        timeout=20.0,  # 20 second timeout per request
        max_retries=2,  # Retry up to 2 times
    )
    logger.debug("embedding_texts", count=len(texts), model=config.embed_model, batch_size=batch_size)

    all_vectors = []

    # Process in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(texts) + batch_size - 1) // batch_size

        logger.debug(
            "embedding_batch",
            batch_num=batch_num,
            total_batches=total_batches,
            batch_size=len(batch),
        )

        try:
            response = client.embeddings.create(
                model=config.embed_model,
                input=batch,
            )
            batch_vectors = np.array([item.embedding for item in response.data], dtype=np.float32)

            # L2 normalize
            norms = np.linalg.norm(batch_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0  # Avoid division by zero
            batch_vectors = batch_vectors / norms

            all_vectors.append(batch_vectors)

        except Exception as e:
            error_str = str(e)
            # If token limit error, try smaller batch
            if "max_tokens_per_request" in error_str or "token" in error_str.lower():
                if batch_size > 100:
                    logger.warning(
                        "token_limit_hit",
                        batch_size=batch_size,
                        retrying_with_smaller_batch=True,
                    )
                    # Recursively try with smaller batch size
                    return embed_texts(texts, config, batch_size=max(100, batch_size // 2))
                else:
                    logger.error("embedding_error", error=error_str, batch_size=len(batch))
                    raise
            else:
                logger.error("embedding_error", error=error_str, count=len(batch))
                raise

    # Concatenate all batches
    if all_vectors:
        vectors = np.vstack(all_vectors)
        logger.debug("embedding_complete", total_count=len(texts), vector_shape=vectors.shape)
        return vectors
    else:
        raise ValueError("No vectors were generated")


def embed_query(text: str, config: Config | None = None) -> np.ndarray:
    """
    Embed a single query text.

    Args:
        text: Query text string
        config: Config instance (uses Config.from_env() if None)

    Returns:
        Numpy array of shape (dimension,) with L2-normalized vector
    """
    if config is None:
        config = Config.from_env()

    if config.embed_offline:
        logger.debug("using_offline_embedding", query_preview=text[:50])
        return _deterministic_embedding(text)

    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY required when EMBED_OFFLINE=0")

    # Create client with timeout to avoid hanging (must complete within API Gateway timeout)
    client = OpenAI(
        api_key=config.openai_api_key,
        timeout=15.0,  # 15 second timeout per request (API Gateway REST has 29s limit)
        max_retries=1,  # Single retry for faster failure
    )
    logger.debug("embedding_query", query_preview=text[:50], model=config.embed_model)

    try:
        response = client.embeddings.create(
            model=config.embed_model,
            input=[text],
        )
        vector = np.array(response.data[0].embedding, dtype=np.float32)

        # L2 normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector
    except Exception as e:
        logger.error("embedding_error", error=str(e), query_preview=text[:50])
        raise

