"""Tests for Reciprocal Rank Fusion."""

import pytest

from src.utils.fusion import reciprocal_rank_fusion


def test_fusion_single_list():
    """Test fusion with single list."""
    ranked_list = [
        {"corpus": "pdf", "chunk_id": "chunk_1", "score": 0.9},
        {"corpus": "pdf", "chunk_id": "chunk_2", "score": 0.8},
        {"corpus": "pdf", "chunk_id": "chunk_3", "score": 0.7},
    ]

    result = reciprocal_rank_fusion([ranked_list])

    assert len(result) == 3
    assert result[0]["chunk_id"] == "chunk_1"
    assert result[0]["score"] > result[1]["score"]
    assert result[1]["score"] > result[2]["score"]


def test_fusion_multiple_lists():
    """Test fusion with multiple lists."""
    list1 = [
        {"corpus": "pdf", "chunk_id": "chunk_1"},
        {"corpus": "pdf", "chunk_id": "chunk_2"},
    ]
    list2 = [
        {"corpus": "sas", "chunk_id": "chunk_2"},
        {"corpus": "sas", "chunk_id": "chunk_1"},
    ]

    result = reciprocal_rank_fusion([list1, list2])

    # Should have 3 unique items
    unique_ids = {r["chunk_id"] for r in result}
    assert len(unique_ids) == 2  # chunk_1 and chunk_2

    # chunk_2 should rank higher (appears in both lists)
    chunk_2_scores = [r["score"] for r in result if r["chunk_id"] == "chunk_2"]
    chunk_1_scores = [r["score"] for r in result if r["chunk_id"] == "chunk_1"]
    assert len(chunk_2_scores) == 1
    assert len(chunk_1_scores) == 1
    assert chunk_2_scores[0] > chunk_1_scores[0]


def test_fusion_empty_list():
    """Test fusion with empty list."""
    result = reciprocal_rank_fusion([])
    assert result == []


def test_fusion_custom_k():
    """Test fusion with custom k parameter."""
    ranked_list = [
        {"corpus": "pdf", "chunk_id": "chunk_1"},
        {"corpus": "pdf", "chunk_id": "chunk_2"},
    ]

    result_k60 = reciprocal_rank_fusion([ranked_list], k=60)
    result_k10 = reciprocal_rank_fusion([ranked_list], k=10)

    # With smaller k, the difference between ranks is more pronounced
    assert len(result_k60) == 2
    assert len(result_k10) == 2

    # Both should have scores
    assert all("score" in r for r in result_k60)
    assert all("score" in r for r in result_k10)


def test_fusion_preserves_metadata():
    """Test that fusion preserves original metadata."""
    ranked_list = [
        {
            "corpus": "pdf",
            "chunk_id": "chunk_1",
            "text": "Some text",
            "metadata": {"source": "test.pdf"},
        },
    ]

    result = reciprocal_rank_fusion([ranked_list])

    assert len(result) == 1
    assert result[0]["text"] == "Some text"
    assert result[0]["metadata"]["source"] == "test.pdf"
    assert "score" in result[0]

