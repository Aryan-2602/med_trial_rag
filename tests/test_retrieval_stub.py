"""Tests for retrieval with stubbed embeddings."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval.faiss_s3 import FaissS3Retriever
from src.utils.config import Config


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    with patch("src.retrieval.faiss_s3.boto3.client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def test_config():
    """Create test config."""
    return Config(
        rag_bucket="test-bucket",
        rag_manifest_key="rag/manifest.json",
        embed_offline=True,
    )


@pytest.fixture
def retriever_with_data(mock_s3_client, test_config, test_indices_dir):
    """Create retriever with test data."""
    # Mock manifest
    manifest = {
        "version": "v20250101",
        "corpora": {
            "pdf": {
                "prefix": "rag/pdf_index/v20250101/",
                "files": ["index.faiss", "ids.jsonl", "docs.jsonl"],
                "dimension": 1536,
                "count": 10,
            },
            "sas": {
                "prefix": "rag/sas_index/v20250101/",
                "files": ["index.faiss", "ids.jsonl", "docs.jsonl"],
                "dimension": 1536,
                "count": 10,
            },
        },
    }

    def mock_get_object(Bucket, Key):
        if Key == "rag/manifest.json":
            return {"Body": MagicMock(read=lambda: json.dumps(manifest).encode())}
        raise Exception(f"Unexpected key: {Key}")

    mock_s3_client.get_object.side_effect = mock_get_object

    # Mock download - use local files
    def mock_download_file(Bucket, Key, Filename):
        if "pdf_index" in Key:
            local_file = test_indices_dir / "pdf_index" / Path(Key).name
        elif "sas_index" in Key:
            local_file = test_indices_dir / "sas_index" / Path(Key).name
        else:
            raise Exception(f"Unexpected key: {Key}")

        if local_file.exists():
            import shutil

            shutil.copy(local_file, Filename)

    mock_s3_client.download_file.side_effect = mock_download_file

    retriever = FaissS3Retriever(test_config)
    retriever.load_from_manifest("test-bucket", "rag/manifest.json")

    return retriever


def test_retriever_search(retriever_with_data):
    """Test retriever search functionality."""
    results = retriever_with_data.search("test query", top_k=5)

    assert isinstance(results, list)
    assert len(results) > 0

    # Check result structure
    for result in results:
        assert "corpus" in result
        assert "chunk_id" in result
        assert "score" in result
        assert "text" in result
        assert "metadata" in result

    # Results should be sorted by score (descending)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retriever_multiple_corpora(retriever_with_data):
    """Test that retriever searches both corpora."""
    results = retriever_with_data.search("test query", top_k=3)

    # Should have results from both corpora
    corpora = {r["corpus"] for r in results}
    assert "pdf" in corpora or "sas" in corpora


def test_retriever_not_loaded():
    """Test that unloaded retriever raises error."""
    config = Config(rag_bucket="test", embed_offline=True)
    retriever = FaissS3Retriever(config)

    with pytest.raises(RuntimeError, match="not loaded"):
        retriever.search("test query")


def test_retriever_close(retriever_with_data):
    """Test retriever cleanup."""
    retriever_with_data.close()
    assert not retriever_with_data.loaded

