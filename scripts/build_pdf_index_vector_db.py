"""Build PDF index using Chroma vector database."""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexers.common import chunk_text
from src.utils.config import Config
from src.utils.logging import get_logger, log_timing
from src.utils.vector_db import VectorDBClient

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
        logger.error("pdf_extraction_failed", file=pdf_path, error=str(e))
        return ""


def process_pdfs(
    input_dir: str,
    max_tokens: int = 512,
    overlap: int = 64,
) -> list[dict[str, Any]]:
    """
    Process PDF files and extract chunks.

    Returns:
        List of document chunks with text and metadata
    """
    input_path = Path(input_dir)
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("no_pdf_files_found", input_dir=input_dir)
        return []

    logger.info("processing_pdfs", count=len(pdf_files))

    all_docs: list[dict[str, Any]] = []

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

    logger.info("pdfs_processed", total_chunks=len(all_docs))
    return all_docs


def main() -> None:
    """Main entry point for PDF indexer using vector DB."""
    parser = argparse.ArgumentParser(description="Build PDF index using Chroma vector DB")
    parser.add_argument("--input-dir", required=True, help="Directory containing PDF files")
    parser.add_argument(
        "--model", default="text-embedding-3-small", help="Embedding model name"
    )
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens per chunk")
    parser.add_argument("--overlap", type=int, default=64, help="Overlap tokens")
    parser.add_argument("--reset", action="store_true", help="Reset/delete existing collection")

    args = parser.parse_args()

    # Set config from args
    os.environ["EMBED_MODEL"] = args.model
    if "OPENAI_API_KEY" not in os.environ:
        logger.error("OPENAI_API_KEY not set - required for embeddings")
        return

    # Set local mode
    os.environ["USE_LOCAL_MODE"] = "1"

    config = Config.from_env()

    # Initialize vector DB
    vector_db = VectorDBClient(config)

    # Reset collection if requested
    if args.reset:
        vector_db.delete_collection()
        logger.info("collection_reset")

    # Process PDFs
    docs = process_pdfs(args.input_dir, args.max_tokens, args.overlap)

    if len(docs) == 0:
        logger.error("no_documents_processed")
        return

    # Add documents to vector DB
    # Chroma will handle embeddings automatically using the embedding function
    with log_timing("add_to_vector_db", count=len(docs)):
        documents = [doc["text"] for doc in docs]
        ids = [doc["id"] for doc in docs]
        metadatas = [doc["metadata"] for doc in docs]

        vector_db.add_documents(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

    # Get final count
    count = vector_db.get_count()

    logger.info(
        "index_build_complete",
        corpus="pdf",
        count=count,
        vector_db="chroma",
    )


if __name__ == "__main__":
    main()

