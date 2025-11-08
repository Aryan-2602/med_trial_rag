"""Pytest configuration and fixtures."""

import json
import os
import tempfile
from pathlib import Path
from typing import Generator

import faiss
import numpy as np
import pytest

# Set offline mode for tests
os.environ["EMBED_OFFLINE"] = "1"
os.environ["RAG_BUCKET"] = "test-bucket"
os.environ["RAG_MANIFEST_KEY"] = "rag/manifest.json"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_data_dir() -> Path:
    """Get path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def mini_manifest(test_data_dir: Path) -> dict:
    """Load mini manifest for testing."""
    manifest_path = test_data_dir / "mini_manifest.json"
    if not manifest_path.exists():
        # Create a minimal manifest
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
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    with open(manifest_path) as f:
        return json.load(f)


@pytest.fixture
def fake_faiss_index() -> faiss.Index:
    """Create a small FAISS index for testing."""
    dimension = 1536
    count = 10

    # Generate random normalized vectors
    np.random.seed(42)
    vectors = np.random.randn(count, dimension).astype(np.float32)
    faiss.normalize_L2(vectors)

    # Create IndexFlatIP
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    return index


@pytest.fixture
def fake_ids_jsonl(temp_dir: Path) -> Path:
    """Create fake ids.jsonl file."""
    ids_data = [{"ann_id": i, "id": f"chunk_{i}"} for i in range(10)]
    ids_path = temp_dir / "ids.jsonl"
    with open(ids_path, "w") as f:
        for item in ids_data:
            f.write(json.dumps(item) + "\n")
    return ids_path


@pytest.fixture
def fake_docs_jsonl(temp_dir: Path) -> Path:
    """Create fake docs.jsonl file."""
    docs_data = [
        {
            "id": f"chunk_{i}",
            "text": f"This is test document chunk {i} with some content.",
            "metadata": {"source": f"test_{i}.pdf", "chunk_index": i},
        }
        for i in range(10)
    ]
    docs_path = temp_dir / "docs.jsonl"
    with open(docs_path, "w") as f:
        for item in docs_data:
            f.write(json.dumps(item) + "\n")
    return docs_path


@pytest.fixture
def test_indices_dir(test_data_dir: Path, fake_faiss_index: faiss.Index) -> Path:
    """Create test indices directory with FAISS files."""
    pdf_dir = test_data_dir / "pdf_index"
    sas_dir = test_data_dir / "sas_index"

    for corpus_dir in [pdf_dir, sas_dir]:
        corpus_dir.mkdir(parents=True, exist_ok=True)

        # Write FAISS index
        index_path = corpus_dir / "index.faiss"
        faiss.write_index(fake_faiss_index, str(index_path))

        # Write ids.jsonl
        ids_path = corpus_dir / "ids.jsonl"
        ids_data = [{"ann_id": i, "id": f"{corpus_dir.name}_chunk_{i}"} for i in range(10)]
        with open(ids_path, "w") as f:
            for item in ids_data:
                f.write(json.dumps(item) + "\n")

        # Write docs.jsonl
        docs_path = corpus_dir / "docs.jsonl"
        docs_data = [
            {
                "id": f"{corpus_dir.name}_chunk_{i}",
                "text": f"This is {corpus_dir.name} document chunk {i}.",
                "metadata": {"source": f"test_{corpus_dir.name}.pdf", "chunk_index": i},
            }
            for i in range(10)
        ]
        with open(docs_path, "w") as f:
            for item in docs_data:
                f.write(json.dumps(item) + "\n")

    return test_data_dir

