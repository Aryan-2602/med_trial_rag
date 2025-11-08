#!/usr/bin/env python3
"""Generate test FAISS indices for testing."""

import json
from pathlib import Path

import faiss
import numpy as np

# Test data directory
test_data_dir = Path(__file__).parent.parent / "tests" / "data"
pdf_dir = test_data_dir / "pdf_index"
sas_dir = test_data_dir / "sas_index"

# Create directories
pdf_dir.mkdir(parents=True, exist_ok=True)
sas_dir.mkdir(parents=True, exist_ok=True)

# Generate FAISS index
dimension = 1536
count = 10

np.random.seed(42)
vectors = np.random.randn(count, dimension).astype(np.float32)
faiss.normalize_L2(vectors)

index = faiss.IndexFlatIP(dimension)
index.add(vectors)

# Write indices for both corpora
for corpus_dir in [pdf_dir, sas_dir]:
    # Write FAISS index
    index_path = corpus_dir / "index.faiss"
    faiss.write_index(index, str(index_path))
    print(f"Created {index_path}")

    # Write ids.jsonl
    ids_path = corpus_dir / "ids.jsonl"
    ids_data = [{"ann_id": i, "id": f"{corpus_dir.name}_chunk_{i}"} for i in range(count)]
    with open(ids_path, "w") as f:
        for item in ids_data:
            f.write(json.dumps(item) + "\n")
    print(f"Created {ids_path}")

    # Write docs.jsonl
    docs_path = corpus_dir / "docs.jsonl"
    docs_data = [
        {
            "id": f"{corpus_dir.name}_chunk_{i}",
            "text": f"This is {corpus_dir.name} document chunk {i} with some test content.",
            "metadata": {"source": f"test_{corpus_dir.name}.pdf", "chunk_index": i},
        }
        for i in range(count)
    ]
    with open(docs_path, "w") as f:
        for item in docs_data:
            f.write(json.dumps(item) + "\n")
    print(f"Created {docs_path}")

print("Test indices generated successfully!")

