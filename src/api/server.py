"""FastAPI server for RAG system."""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from api.models import ChatRequest, ChatResponse, Citation, StatusResponse
from retrieval.faiss_s3 import FaissS3Retriever
from utils.config import Config
from utils.logging import configure_logging, get_logger, get_request_id, set_request_id

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Global retriever instance
retriever: FaissS3Retriever | None = None
config: Config | None = None
_initialized = False


def _ensure_initialized() -> None:
    """Initialize retriever on first use (Lambda container reuse)."""
    global retriever, config, _initialized
    
    if _initialized:
        return
        
    logger.info("initializing_retriever")
    try:
        config = Config.from_env()
        config.validate()

        retriever = FaissS3Retriever(config)
        retriever.load_from_manifest(config.rag_bucket, config.rag_manifest_key)

        app.state.retriever = retriever
        app.state.config = config

        _initialized = True
        logger.info("retriever_initialized", retriever_loaded=True)
    except Exception as e:
        logger.error("initialization_failed", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown (local dev only)."""
    global retriever, config

    # Startup
    logger.info("starting_application")
    try:
        config = Config.from_env()
        config.validate()

        retriever = FaissS3Retriever(config)
        retriever.load_from_manifest(config.rag_bucket, config.rag_manifest_key)

        # Attach to app state
        app.state.retriever = retriever
        app.state.config = config

        logger.info("application_started", retriever_loaded=True)
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("shutting_down_application")
    if retriever:
        retriever.close()
    logger.info("application_shutdown")


app = FastAPI(
    title="CoTrial RAG v2",
    description="RAG system with FAISS, S3, and FastAPI",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any):
    """Middleware to add request ID to context."""
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


@app.get("/v1/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Get status of the RAG system."""
    # Try to initialize, but don't block if it's taking too long
    # Status can return partial info if initialization is in progress
    try:
        if not _initialized:
            # Only initialize if not already done - don't wait for slow download
            # This allows status to return quickly on subsequent calls
            _ensure_initialized()
    except Exception as e:
        logger.warning("status_check_init_failed", error=str(e))
        # Return status even if initialization failed
        pass
    
    if not retriever or not retriever.loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retriever not initialized or indices not loaded",
        )

    manifest_version = retriever.manifest.version if retriever.manifest else "unknown"
    corpora = retriever.corpus_counts.copy()

    return StatusResponse(
        retriever=config.use_retriever if config else "unknown",
        manifest_version=manifest_version,
        corpora=corpora,
        loaded=retriever.loaded,
    )


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint that searches corpora and returns answer with citations.

    Args:
        request: Chat request with query

    Returns:
        Chat response with answer and citations
    """
    _ensure_initialized()
    
    if not retriever:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retriever not initialized",
        )

    if not retriever.loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Indices not loaded",
        )

    top_k = request.top_k or (config.top_k if config else 5)

    try:
        # Search
        results = retriever.search(request.query, top_k=top_k)

        if not results:
            return ChatResponse(
                answer="No relevant documents found for your query.",
                citations=[],
            )

        # Generate answer from top results with better formatting
        top_results = results[:5]  # Use top 5 for answer
        
        # Clean and format text snippets
        answer_parts = []
        seen_texts = set()  # Deduplicate similar content
        
        for result in top_results:
            text = result.get("text", "").strip()
            if not text:
                continue
            
            # Skip if we've seen very similar text (deduplication)
            text_lower = text.lower()[:100]  # Use first 100 chars for comparison
            if text_lower in seen_texts:
                continue
            seen_texts.add(text_lower)
            
            # Clean up SAS data - remove metadata noise
            corpus = result.get("corpus", "")
            if corpus == "sas":
                # For SAS data, try to extract meaningful content
                # SAS data often has format: "Source: file | KEY: value | KEY: value | actual content"
                if "Source:" in text and "|" in text:
                    # Split by | and filter out metadata keys
                    parts = text.split("|")
                    filtered_parts = []
                    metadata_keys = {
                        "RESPROJ", "FACILITY", "SDYID", "USDYID", "SUBJID", 
                        "INVID", "USUBJID", "SEX", "RACE", "AGEYR", "BIRTHDT",
                        "BIRTHDTIMPUTFLG", "COUNTRY", "ETHNIC", "TRTSORT", "TRT"
                    }
                    
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                        # Check if this looks like metadata (KEY: value format)
                        if ":" in part:
                            key = part.split(":")[0].strip()
                            if key in metadata_keys or key == "Source":
                                continue  # Skip metadata
                        # Keep if it looks like actual content
                        if len(part) > 3:
                            filtered_parts.append(part)
                    
                    if filtered_parts:
                        text = " | ".join(filtered_parts)
                    else:
                        # If all was metadata, try to extract any meaningful text after metadata
                        # Look for content after the last metadata pattern
                        last_metadata_idx = text.rfind("|")
                        if last_metadata_idx > 0:
                            potential_content = text[last_metadata_idx + 1:].strip()
                            if len(potential_content) > 10:
                                text = potential_content
            
            # Use longer snippets for better context (up to 400 chars)
            # Try to end at sentence boundaries
            if len(text) > 400:
                # Find last sentence ending before 400 chars
                truncated = text[:400]
                last_period = truncated.rfind(".")
                last_newline = truncated.rfind("\n")
                cutoff = max(last_period, last_newline)
                if cutoff > 200:  # Only use if we have enough content
                    text = text[:cutoff + 1]
                else:
                    text = text[:400] + "..."
            
            answer_parts.append(text)
        
        # Join with better formatting
        if answer_parts:
            # Use double newlines to separate different sources
            answer = "\n\n".join(answer_parts)
            
            # Limit total length
            max_length = config.max_tokens * 4 if config else 2000
            if len(answer) > max_length:
                # Truncate at sentence boundary if possible
                truncated = answer[:max_length]
                last_period = truncated.rfind(".")
                if last_period > max_length * 0.8:  # Only if we keep most of it
                    answer = answer[:last_period + 1]
                else:
                    answer = truncated + "..."
        else:
            answer = "I found relevant documents, but couldn't extract a clear answer. Please check the sources below for more details."

        # Build citations
        citations = [
            Citation(
                corpus=r.get("corpus", ""),
                chunk_id=r.get("chunk_id", ""),
                score=r.get("score", 0.0),
                snippet=r.get("text", "")[:300],  # Truncate for display
            )
            for r in results[:10]  # Top 10 citations
        ]

        logger.info(
            "chat_request_completed",
            query_preview=request.query[:50],
            results_count=len(results),
            citations_count=len(citations),
        )

        return ChatResponse(answer=answer, citations=citations)

    except Exception as e:
        logger.error("chat_request_failed", error=str(e), query_preview=request.query[:50])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint - API information."""
    return {
        "message": "CoTrial RAG v2 API",
        "docs": "/docs",
        "health": "/health",
        "status": "/v1/status",
        "chat": "/v1/chat (POST only)",
        "note": "Use /docs for interactive API documentation. Chat endpoint requires POST method.",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


# Lambda handler for AWS SAM
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler for FastAPI app."""
    from mangum import Mangum

    asgi_handler = Mangum(app, lifespan="off")  # Lifespan handled by Lambda
    return asgi_handler(event, context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

