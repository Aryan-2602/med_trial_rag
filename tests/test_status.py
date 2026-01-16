"""Tests for status endpoint."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.server import app


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    with patch("src.retrieval.faiss_s3.boto3.client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_manifest_json(test_data_dir: Path):
    """Load mock manifest JSON."""
    manifest_path = test_data_dir / "mini_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {
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


@pytest.fixture
def client_with_retriever(mock_s3_client, mock_manifest_json, test_indices_dir):
    """Create test client with mocked retriever."""
    # Mock S3 get_object for manifest
    def mock_get_object(Bucket, Key):
        if Key == "rag/manifest.json":
            return {"Body": MagicMock(read=lambda: json.dumps(mock_manifest_json).encode())}
        raise Exception(f"Unexpected key: {Key}")

    mock_s3_client.get_object.side_effect = mock_get_object

    # Mock download - use local files
    def mock_download_file(Bucket, Key, Filename):
        # Map S3 keys to local test files
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

    # Create client (this will trigger startup)
    with TestClient(app) as client:
        yield client


def test_status_endpoint(client_with_retriever):
    """Test status endpoint returns correct data."""
    response = client_with_retriever.get("/v1/status")
    assert response.status_code == 200

    data = response.json()
    assert "retriever" in data
    assert "manifest_version" in data
    assert "corpora" in data
    assert "loaded" in data
    assert data["loaded"] is True
    assert "pdf" in data["corpora"]
    assert "sas" in data["corpora"]


def test_health_endpoint(client_with_retriever):
    """Test health endpoint."""
    response = client_with_retriever.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

