"""FAISS-based retriever loading indices from S3."""

import json
import os
from pathlib import Path
from typing import Any

import boto3
import faiss
import numpy as np

from data_schemas.manifest import Manifest
from retrieval.base import Retriever
from utils.config import Config
from utils.embeddings import embed_query
from utils.fusion import reciprocal_rank_fusion
from utils.logging import get_logger, log_timing
from utils.s3io import download_if_needed, get_object_json, jsonl_iter

logger = get_logger(__name__)


class FaissS3Retriever:
    """FAISS retriever that loads indices from S3."""

    def __init__(self, config: Config | None = None):
        """
        Initialize retriever.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        self.config = config or Config.from_env()
        self.s3_client = boto3.client("s3")
        self.manifest: Manifest | None = None
        self.indices: dict[str, faiss.Index] = {}
        self.id_maps: dict[str, dict[int, str]] = {}  # corpus -> ann_id -> chunk_id
        self.doc_maps: dict[str, dict[str, dict[str, Any]]] = {}  # corpus -> chunk_id -> {text, metadata}
        self.loaded = False
        self.corpus_counts: dict[str, int] = {}

    def load_from_manifest(self, bucket: str, manifest_key: str) -> None:
        """
        Load indices from S3 manifest.

        Args:
            bucket: S3 bucket name
            manifest_key: S3 key for manifest JSON
        """
        with log_timing("load_manifest", bucket=bucket, key=manifest_key):
            try:
                manifest_dict = get_object_json(bucket, manifest_key, self.s3_client)
                self.manifest = Manifest.model_validate(manifest_dict)
                logger.info(
                    "manifest_loaded",
                    version=self.manifest.version,
                    corpora=list(self.manifest.corpora.keys()),
                )
            except Exception as e:
                logger.error("manifest_load_failed", bucket=bucket, key=manifest_key, error=str(e))
                raise

        # Load each corpus
        for corpus_name, corpus_entry in self.manifest.corpora.items():
            with log_timing(f"load_corpus_{corpus_name}", corpus=corpus_name):
                self._load_corpus(bucket, corpus_name, corpus_entry)

        self.loaded = True
        logger.info(
            "retriever_loaded",
            version=self.manifest.version,
            corpus_counts=self.corpus_counts,
        )

    def _load_corpus(
        self,
        bucket: str,
        corpus_name: str,
        corpus_entry: Any,
    ) -> None:
        """Load a single corpus index and metadata."""
        version = self.manifest.version if self.manifest else "unknown"
        # Use EFS if available, otherwise fall back to /tmp
        storage_base = os.getenv("RAG_STORAGE_PATH", "/tmp")
        local_dir = Path(f"{storage_base}/rag/{corpus_name}/{version}")
        local_dir.mkdir(parents=True, exist_ok=True)

        # Download files
        prefix = corpus_entry.prefix
        for filename in corpus_entry.files:
            s3_key = f"{prefix}{filename}"
            local_path = str(local_dir / filename)
            download_if_needed(bucket, s3_key, local_path, self.s3_client)

        # Load FAISS index
        index_path = local_dir / "index.faiss"
        logger.debug("loading_faiss_index", corpus=corpus_name, path=str(index_path))
        index = faiss.read_index(str(index_path))

        # Verify dimension
        if index.d != corpus_entry.dimension:
            raise ValueError(
                f"Dimension mismatch: index has {index.d}, manifest says {corpus_entry.dimension}"
            )

        self.indices[corpus_name] = index

        # Load ID mapping (ann_id -> chunk_id)
        ids_path = local_dir / "ids.jsonl"
        id_map: dict[int, str] = {}
        for item in jsonl_iter(str(ids_path)):
            ann_id = item.get("ann_id")
            chunk_id = item.get("id")
            if ann_id is not None and chunk_id:
                id_map[int(ann_id)] = str(chunk_id)
        self.id_maps[corpus_name] = id_map

        # Load document mapping (chunk_id -> {text, metadata})
        docs_path = local_dir / "docs.jsonl"
        doc_map: dict[str, dict[str, Any]] = {}
        for item in jsonl_iter(str(docs_path)):
            chunk_id = item.get("id")
            if chunk_id:
                doc_map[str(chunk_id)] = {
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                }
        self.doc_maps[corpus_name] = doc_map

        self.corpus_counts[corpus_name] = corpus_entry.count

        logger.info(
            "corpus_loaded",
            corpus=corpus_name,
            count=corpus_entry.count,
            dimension=corpus_entry.dimension,
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search across all corpora and fuse results.

        Args:
            query: Query text
            top_k: Number of results per corpus

        Returns:
            Fused list of results with corpus, chunk_id, score, text, metadata
        """
        if not self.loaded:
            raise RuntimeError("Retriever not loaded. Call load_from_manifest() first.")

        # Embed query
        query_vector = embed_query(query, self.config)
        query_vector = query_vector.reshape(1, -1).astype(np.float32)

        # Search each corpus
        ranked_lists: list[list[dict[str, Any]]] = []

        for corpus_name, index in self.indices.items():
            with log_timing(f"search_corpus_{corpus_name}", corpus=corpus_name):
                # FAISS search (IndexFlatIP for cosine similarity)
                distances, ann_ids = index.search(query_vector, top_k)

                # Build results for this corpus
                corpus_results: list[dict[str, Any]] = []
                id_map = self.id_maps[corpus_name]
                doc_map = self.doc_maps[corpus_name]

                for i, (distance, ann_id) in enumerate(zip(distances[0], ann_ids[0], strict=False)):
                    if ann_id == -1:  # FAISS returns -1 for empty results
                        continue

                    chunk_id = id_map.get(int(ann_id))
                    if not chunk_id:
                        logger.warning("missing_chunk_id", corpus=corpus_name, ann_id=int(ann_id))
                        continue

                    doc_data = doc_map.get(chunk_id, {})
                    text = doc_data.get("text", "")
                    metadata = doc_data.get("metadata", {})

                    # Convert distance to score (for cosine, higher is better)
                    score = float(distance)

                    corpus_results.append(
                        {
                            "corpus": corpus_name,
                            "chunk_id": chunk_id,
                            "score": score,
                            "text": text,
                            "metadata": metadata,
                        }
                    )

                ranked_lists.append(corpus_results)

        # Fuse results
        fused_results = reciprocal_rank_fusion(ranked_lists, k=self.config.fusion_k)

        logger.debug(
            "search_complete",
            query_preview=query[:50],
            top_k=top_k,
            fused_count=len(fused_results),
        )

        return fused_results

    def close(self) -> None:
        """Clean up resources."""
        self.indices.clear()
        self.id_maps.clear()
        self.doc_maps.clear()
        self.loaded = False
        logger.info("retriever_closed")

