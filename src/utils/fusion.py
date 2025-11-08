"""Reciprocal Rank Fusion (RRF) for combining ranked lists."""

from typing import Any

import numpy as np

from utils.logging import get_logger

logger = get_logger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: List of ranked lists, each containing dicts with at least
                     'chunk_id' and 'corpus' keys
        k: RRF constant (default 60)

    Returns:
        Fused ranked list sorted by RRF score (descending)
    """
    if not ranked_lists:
        return []

    # Build score map: (corpus, chunk_id) -> score
    score_map: dict[tuple[str, str], float] = {}

    for rank_list in ranked_lists:
        for rank, item in enumerate(rank_list, start=1):
            corpus = item.get("corpus", "")
            chunk_id = item.get("chunk_id", "")
            key = (corpus, chunk_id)

            # RRF score: 1 / (k + rank)
            score_map[key] = score_map.get(key, 0.0) + 1.0 / (k + rank)

    # Collect all unique items with their scores
    fused_items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    # Merge items from all lists, preserving metadata from first occurrence
    for rank_list in ranked_lists:
        for item in rank_list:
            corpus = item.get("corpus", "")
            chunk_id = item.get("chunk_id", "")
            key = (corpus, chunk_id)

            if key not in seen:
                seen.add(key)
                fused_item = item.copy()
                fused_item["score"] = score_map[key]
                fused_items.append(fused_item)

    # Sort by RRF score (descending)
    fused_items.sort(key=lambda x: x.get("score", 0.0), reverse=True)

    logger.debug(
        "fusion_complete",
        input_lists=len(ranked_lists),
        total_items=len(fused_items),
        k=k,
    )

    return fused_items

