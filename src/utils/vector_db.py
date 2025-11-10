"""Vector database client using Chroma."""

import os
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    Settings = None
    embedding_functions = None

from src.utils.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VectorDBClient:
    """Chroma vector database client for PDF embeddings."""

    def __init__(self, config: Config | None = None):
        """
        Initialize Chroma client.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        if chromadb is None:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")

        self.config = config or Config.from_env()
        
        # Determine storage path (local mode)
        use_local = os.getenv("USE_LOCAL_MODE", "0") == "1"
        if use_local:
            db_path = os.getenv("VECTOR_DB_PATH", "data/vector_db")
            Path(db_path).mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
            logger.info("chroma_client_initialized", mode="local", path=db_path)
        else:
            # For future: could use Chroma cloud or remote server
            raise ValueError("Only local mode supported currently. Set USE_LOCAL_MODE=1")

        self.collection_name = "pdf_documents"
        self.collection = None

    def get_or_create_collection(self) -> Any:
        """
        Get or create the PDF documents collection.

        Returns:
            Chroma collection
        """
        if self.collection is None:
            # Use OpenAI embeddings
            # Chroma's OpenAIEmbeddingFunction requires OPENAI_API_KEY env var
            # Set it temporarily if not already set
            original_key = os.environ.get("OPENAI_API_KEY")
            if self.config.openai_api_key:
                os.environ["OPENAI_API_KEY"] = self.config.openai_api_key
                os.environ["CHROMA_OPENAI_API_KEY"] = self.config.openai_api_key
            
            embedding_func = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.config.openai_api_key,
                model_name=self.config.embed_model,
            )
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_func,
                metadata={"description": "PDF document chunks"},
            )
            
            # Restore original key if we changed it
            if original_key and original_key != self.config.openai_api_key:
                os.environ["OPENAI_API_KEY"] = original_key
            
            logger.info("collection_ready", name=self.collection_name, count=self.collection.count())
        
        return self.collection

    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Add documents to the vector database.

        Args:
            documents: List of document texts
            ids: List of document IDs
            metadatas: Optional list of metadata dicts
        """
        collection = self.get_or_create_collection()
        
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
        
        logger.info("documents_added", count=len(documents), collection=self.collection_name)

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Search for similar documents.

        Args:
            query: Query text
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dictionary with 'ids', 'documents', 'metadatas', 'distances'
        """
        collection = self.get_or_create_collection()
        
        # Ensure OpenAI API key is set for embedding function
        if self.config.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.config.openai_api_key
            os.environ["CHROMA_OPENAI_API_KEY"] = self.config.openai_api_key
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )
        except Exception as e:
            logger.error("chroma_query_failed", error=str(e), query_preview=query[:50])
            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "distances": [],
            }
        
        # Convert to simpler format
        return {
            "ids": results["ids"][0] if results["ids"] and len(results["ids"]) > 0 else [],
            "documents": results["documents"][0] if results["documents"] and len(results["documents"]) > 0 else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] and len(results["metadatas"]) > 0 else [],
            "distances": results["distances"][0] if results["distances"] and len(results["distances"]) > 0 else [],
        }

    def delete_collection(self) -> None:
        """Delete the collection (for rebuilding)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None
            logger.info("collection_deleted", name=self.collection_name)
        except Exception as e:
            logger.warning("collection_delete_failed", error=str(e))

    def get_count(self) -> int:
        """Get number of documents in collection."""
        collection = self.get_or_create_collection()
        return collection.count()

