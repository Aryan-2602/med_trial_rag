"""Indexer for PDF documents."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
import faiss
import numpy as np
from pypdf import PdfReader

from src.data_schemas.manifest import CorpusEntry, Manifest
from src.indexers.common import build_faiss_index, chunk_text, write_jsonl
from src.utils.config import Config
from src.utils.embeddings import embed_texts
from src.utils.logging import get_logger, log_timing
from src.utils.s3io import atomic_upload, get_object_json

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.warning("pdf_extraction_failed", path=pdf_path, error=str(e))
        return ""


def process_pdfs(
    input_dir: str,
    max_tokens: int = 512,
    overlap: int = 64,
    config: Config | None = None,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """
    Process PDF files and generate embeddings.

    Returns:
        Tuple of (documents list, embeddings array)
    """
    if config is None:
        config = Config.from_env()

    input_path = Path(input_dir)
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("no_pdf_files_found", input_dir=input_dir)
        return [], np.array([])

    logger.info("processing_pdfs", count=len(pdf_files))

    all_docs: list[dict[str, Any]] = []
    all_texts: list[str] = []

    for pdf_file in pdf_files:
        with log_timing("process_pdf", file=str(pdf_file)):
            text = extract_text_from_pdf(str(pdf_file))
            if not text.strip():
                continue

            chunks = chunk_text(text, max_tokens=max_tokens, overlap=overlap)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{pdf_file.stem}_chunk_{i}"
                all_docs.append(
                    {
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": {
                            "source_file": pdf_file.name,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                        },
                    }
                )
                all_texts.append(chunk)

    if not all_texts:
        logger.warning("no_text_extracted")
        return [], np.array([])

    # Embed all texts
    with log_timing("embed_texts", count=len(all_texts)):
        embeddings = embed_texts(all_texts, config)

    return all_docs, embeddings


def update_manifest(
    bucket: str,
    manifest_key: str,
    corpus_name: str,
    version: str,
    prefix: str,
    dimension: int,
    count: int,
    s3_client: Any = None,
) -> None:
    """Update manifest with new corpus entry."""
    if s3_client is None:
        s3_client = boto3.client("s3")

    # Download existing manifest or create new
    try:
        manifest_dict = get_object_json(bucket, manifest_key, s3_client)
        manifest = Manifest.model_validate(manifest_dict)
    except Exception:
        logger.info("creating_new_manifest")
        manifest = Manifest(version=version, corpora={})

    # Update version and corpus entry
    manifest.version = version
    manifest.corpora[corpus_name] = CorpusEntry(
        prefix=prefix,
        files=["index.faiss", "ids.jsonl", "docs.jsonl"],
        dimension=dimension,
        count=count,
    )

    # Upload updated manifest
    manifest_json = json.dumps(manifest.model_dump_dict(), indent=2)
    tmp_manifest = "/tmp/manifest.json"
    with open(tmp_manifest, "w") as f:
        f.write(manifest_json)

    atomic_upload(bucket, manifest_key, tmp_manifest, s3_client)
    logger.info("manifest_updated", version=version, corpus=corpus_name)


def main() -> None:
    """Main entry point for PDF indexer."""
    parser = argparse.ArgumentParser(description="Build PDF index")
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--prefix", default="rag/pdf_index", help="S3 prefix for index files")
    parser.add_argument(
        "--manifest-key", default="rag/manifest.json", help="S3 key for manifest"
    )
    parser.add_argument(
        "--model", default="text-embedding-3-small", help="Embedding model name"
    )
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens per chunk")
    parser.add_argument("--overlap", type=int, default=64, help="Overlap tokens")

    args = parser.parse_args()

    # Set config from args
    os.environ["RAG_BUCKET"] = args.bucket
    os.environ["EMBED_MODEL"] = args.model
    if "OPENAI_API_KEY" not in os.environ:
        logger.warning("OPENAI_API_KEY not set, will use offline embeddings if EMBED_OFFLINE=1")

    config = Config.from_env()

    # Process PDFs
    docs, embeddings = process_pdfs(args.input_dir, args.max_tokens, args.overlap, config)

    if len(docs) == 0:
        logger.error("no_documents_processed")
        return

    dimension = embeddings.shape[1]
    count = len(docs)

    # Build FAISS index
    with log_timing("build_faiss_index"):
        index = build_faiss_index(embeddings)

    # Generate version
    version = datetime.now().strftime("v%Y%m%d")
    version_prefix = f"{args.prefix}/{version}/"

    # Write local files
    tmp_dir = Path("/tmp/pdf_index_build")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    index_path = tmp_dir / "index.faiss"
    faiss.write_index(index, str(index_path))

    # Write ids.jsonl (ann_id -> chunk_id)
    ids_data = [{"ann_id": i, "id": doc["id"]} for i, doc in enumerate(docs)]
    ids_path = tmp_dir / "ids.jsonl"
    write_jsonl(str(ids_path), ids_data)

    # Write docs.jsonl
    docs_path = tmp_dir / "docs.jsonl"
    write_jsonl(str(docs_path), docs)

    # Upload to S3
    s3_client = boto3.client("s3")
    for filename in ["index.faiss", "ids.jsonl", "docs.jsonl"]:
        local_path = tmp_dir / filename
        s3_key = f"{version_prefix}{filename}"
        atomic_upload(args.bucket, s3_key, str(local_path), s3_client)
        logger.info("uploaded_file", key=s3_key, size=local_path.stat().st_size)

    # Update manifest
    update_manifest(
        args.bucket,
        args.manifest_key,
        "pdf",
        version,
        version_prefix,
        dimension,
        count,
        s3_client,
    )

    logger.info(
        "index_build_complete",
        corpus="pdf",
        version=version,
        count=count,
        dimension=dimension,
        prefix=version_prefix,
    )


if __name__ == "__main__":
    main()

