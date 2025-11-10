"""FastAPI server for RAG system."""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import ChatRequest, ChatResponse, Citation, StatusResponse
from src.retrieval.hybrid import HybridRetriever
from src.utils.answer_generator import AnswerGenerator
from src.utils.config import Config
from src.utils.logging import configure_logging, get_logger, get_request_id, set_request_id

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Global retriever instance (hybrid: PDF via Vector DB, SAS via SQL)
retriever: HybridRetriever | None = None
config: Config | None = None
answer_generator: AnswerGenerator | None = None
_initialized = False


def _ensure_initialized() -> None:
    """Initialize retriever on first use (Lambda container reuse)."""
    global retriever, config, answer_generator, _initialized
    
    if _initialized:
        return
        
    logger.info("initializing_retriever")
    try:
        config = Config.from_env()
        config.validate()

        # Use hybrid retriever (PDF via Vector DB, SAS via SQL)
        retriever = HybridRetriever(config)
        retriever.load()  # Load vector DB and MySQL

        # Initialize answer generator
        try:
            answer_generator = AnswerGenerator(config)
            logger.info("answer_generator_initialized")
        except Exception as e:
            logger.warning("answer_generator_init_failed", error=str(e))
            answer_generator = None

        app.state.retriever = retriever
        app.state.config = config
        app.state.answer_generator = answer_generator

        _initialized = True
        logger.info("retriever_initialized", retriever_loaded=True, type="hybrid")
    except Exception as e:
        logger.error("initialization_failed", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown (local dev only)."""
    global retriever, config, answer_generator

    # Startup
    logger.info("starting_application")
    try:
        config = Config.from_env()
        config.validate()

        # Use hybrid retriever (PDF via Vector DB, SAS via SQL)
        retriever = HybridRetriever(config)
        retriever.load()  # Load vector DB and MySQL

        # Initialize answer generator
        try:
            answer_generator = AnswerGenerator(config)
            logger.info("answer_generator_initialized")
        except Exception as e:
            logger.warning("answer_generator_init_failed", error=str(e))
            answer_generator = None

        # Attach to app state
        app.state.retriever = retriever
        app.state.config = config
        app.state.answer_generator = answer_generator

        logger.info("application_started", retriever_loaded=True, type="hybrid")
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
    description="RAG system with Chroma Vector DB and MySQL",
    version="0.2.0",
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

    # Get status from retrievers
    manifest_version = "vector_db"  # Vector DB doesn't use manifest versioning
    corpora: dict[str, int] = {}
    
    # Get PDF count from vector DB
    if retriever.pdf_retriever and retriever.pdf_retriever.loaded:
        try:
            pdf_count = retriever.pdf_retriever.vector_db.get_count()
            corpora["pdf"] = pdf_count
        except Exception:
            corpora["pdf"] = -1  # Unknown count
    
    # Add SAS status (from MySQL)
    if retriever.mysql_client:
        try:
            # Test connection to see if SAS is available
            if retriever.mysql_client.test_connection():
                corpora["sas"] = -1  # -1 indicates SQL-based (unknown count)
        except Exception:
            pass  # MySQL not available

    return StatusResponse(
        retriever="hybrid" if config else "unknown",
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

        # Use GPT to generate answer from retrieved context
        global answer_generator
        if answer_generator is None:
            try:
                answer_generator = AnswerGenerator(config)
            except Exception as e:
                logger.warning("answer_generator_not_available", error=str(e))
                answer_generator = None

        if answer_generator:
            # Generate answer using GPT
            top_results = results[:10]  # Use top 10 for context
            answer = answer_generator.generate(
                query=request.query,
                context_chunks=top_results,
            )
        else:
            # Fallback: simple concatenation if GPT not available
            logger.warning("using_fallback_answer_generation")
            top_results = results[:5]
            answer_parts = []
            for result in top_results:
                text = result.get("text", "").strip()
                if text:
                    # Truncate long chunks
                    if len(text) > 500:
                        text = text[:500] + "..."
                    answer_parts.append(text)
            
            if answer_parts:
                answer = "\n\n".join(answer_parts)
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

