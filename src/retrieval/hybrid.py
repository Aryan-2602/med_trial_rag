"""Hybrid retriever supporting PDF (Vector DB), SAS (SQL), and Context (Q&A cache) searches."""

import concurrent.futures
import os
from typing import Any

from src.retrieval.vector_db_retriever import VectorDBRetriever
from src.utils.agentic_router import AgenticRouter
from src.utils.config import Config
from src.utils.logging import get_logger, log_timing
from src.utils.mysql_client import MySQLClient
from src.utils.prompt_examples import PromptExamples
from src.utils.sql_generator import SQLGenerator

logger = get_logger(__name__)


class HybridRetriever:
    """
    Hybrid retriever that supports:
    - PDF: Vector search via Chroma vector database
    - SAS: SQL queries via MySQL
    - Context: Pre-computed Q&A cache (prompt examples)
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize hybrid retriever.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        self.config = config or Config.from_env()
        
        # PDF retriever (Vector DB - Chroma)
        self.pdf_retriever: VectorDBRetriever | None = None
        
        # SAS retriever (MySQL)
        self.mysql_client: MySQLClient | None = None
        self.sql_generator = SQLGenerator(config=self.config, use_llm=True)
        
        # Context retriever (Q&A cache)
        self.context_examples = PromptExamples()
        
        # Agentic reasoning layer for query routing
        self.router = AgenticRouter(self.config)
        
        self.loaded = False

    def load(self) -> None:
        """
        Load/initialize the retrievers.
        Vector DB loads automatically, no manifest needed.
        """
        # Initialize vector DB retriever for PDFs
        try:
            self.pdf_retriever = VectorDBRetriever(self.config)
            self.pdf_retriever.load()
            logger.info("vector_db_retriever_initialized")
        except Exception as e:
            logger.warning("vector_db_init_failed", error=str(e))

        # Initialize MySQL client for SAS
        try:
            self.mysql_client = MySQLClient(self.config)
            if self.mysql_client.test_connection():
                logger.info("mysql_connected", status="success")
                
                # Check if dummy tables exist (optional auto-creation)
                # Only log, don't auto-create to avoid unexpected behavior
                try:
                    from src.utils.db_initializer import check_dummy_tables_exist
                    tables_exist, has_data = check_dummy_tables_exist(self.config)
                    if not tables_exist:
                        logger.info(
                            "dummy_tables_not_found",
                            hint="Run 'make create-dummy-data' to create dummy clinical trial tables"
                        )
                    elif not has_data:
                        logger.info(
                            "dummy_tables_empty",
                            hint="Run 'make create-dummy-data' to populate dummy clinical trial tables"
                        )
                except Exception as e:
                    logger.debug("dummy_tables_check_failed", error=str(e))
            else:
                logger.warning("mysql_connection_failed", status="failed")
        except Exception as e:
            logger.warning("mysql_init_failed", error=str(e))

        # Load context examples
        try:
            self.context_examples.load()
            if self.context_examples.count() > 0:
                logger.info("context_examples_loaded", count=self.context_examples.count())
        except Exception as e:
            logger.warning("context_examples_load_failed", error=str(e))

        self.loaded = True
        logger.info(
            "hybrid_retriever_loaded",
            pdf_loaded=self.pdf_retriever.loaded if self.pdf_retriever else False,
            mysql_available=self.mysql_client is not None,
            context_examples_count=self.context_examples.count(),
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search across PDF (vector), SAS (SQL), and Context (Q&A cache) with result-aware routing.

        Modified routing strategy:
        - PDF queries: Direct PDF search (no context cache check)
        - SQL queries: Check context cache first, then generate SQL if no match
        - Uses LLM to evaluate result quality
        - Decides which results to use/combine

        Args:
            query: User query
            top_k: Number of results per source

        Returns:
            Intelligently combined list of results
        """
        if not self.loaded:
            raise RuntimeError("Retriever not loaded. Call load() first.")

        # Step 1: Use agentic reasoning to route query (without context check first)
        route = self.router.route_query(query, context_examples=None)
        logger.debug("query_routed_agentic", query=query[:50], route=route)

        # Step 2: Determine which sources to search
        search_pdf = route in ["pdf", "both", "all", "pdf+context"]
        search_sas = route in ["sas", "both", "all", "sas+context"]
        
        pdf_results: list[dict[str, Any]] = []
        sas_results: list[dict[str, Any]] = []
        context_results: list[dict[str, Any]] = []

        # Step 3: For SQL queries, check context cache FIRST before generating SQL
        if search_sas:
            context_results = self._search_context(query, top_k=3)
            
            # Check if context has a good match (similarity > 0.5)
            has_good_context_match = (
                context_results and 
                len(context_results) > 0 and 
                context_results[0].get("score", 0.0) > 0.5
            )
            
            if has_good_context_match:
                logger.info(
                    "context_cache_hit",
                    query_preview=query[:50],
                    context_score=context_results[0].get("score", 0.0),
                )
                # Use context cache, skip SQL generation
                sas_results = []  # Don't generate SQL if context has good match
            else:
                # No good context match, proceed with SQL generation
                logger.info(
                    "context_cache_miss",
                    query_preview=query[:50],
                    context_score=context_results[0].get("score", 0.0) if context_results else 0.0,
                )
                if self.mysql_client:
                    try:
                        sas_results = self._search_sas_sql(query, top_k)
                    except Exception as e:
                        logger.error("sas_sql_search_failed", error=str(e), query=query[:50])
                        sas_results = []
        else:
            # Not a SQL query, no context check needed
            context_results = []

        # Step 4: Search PDF if needed (no context check for PDF)
        if search_pdf and self.pdf_retriever and self.pdf_retriever.loaded:
            try:
                pdf_results = self.pdf_retriever.search(query, top_k)
            except Exception as e:
                logger.error("pdf_search_failed", error=str(e), query=query[:50])
                pdf_results = []

        # Step 5: Evaluate result quality using LLM
        evaluation = self.router.evaluate_result_quality(
            query=query,
            pdf_results=pdf_results,
            sas_results=sas_results,
            context_results=context_results if context_results else None,
        )

        # Step 6: Intelligently combine results based on evaluation
        combined_results = self._combine_results_intelligently(
            query=query,
            pdf_results=pdf_results,
            sas_results=sas_results,
            context_results=context_results if context_results else None,
            evaluation=evaluation,
            top_k=top_k,
        )

        logger.info(
            "hybrid_search_complete",
            query_preview=query[:50],
            route=route,
            pdf_count=len(pdf_results),
            sas_count=len(sas_results),
            context_count=len(context_results),
            recommendation=evaluation.get("recommendation", "use_both"),
            final_count=len(combined_results),
        )

        return combined_results

    def _search_sas_sql(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search SAS data using SQL queries.

        Args:
            query: Natural language query
            top_k: Maximum number of results

        Returns:
            List of results in same format as vector search
        """
        if not self.mysql_client:
            return []

        try:
            # Generate SQL from natural language
            sql = self.sql_generator.generate_sql(query, limit=top_k)

            # Execute query
            rows = self.mysql_client.execute_query_with_limit(sql, limit=top_k)

            # Convert SQL results to same format as vector search results
            results = []
            
            # Check if this is an aggregation query (has COUNT, SUM, AVG, etc.)
            is_aggregation = any(
                col.lower() in ["count", "sum", "avg", "min", "max", "total", "average", "minimum", "maximum"]
                for row in rows
                for col in row.keys()
            ) if rows else False
            
            # Format results differently for aggregations vs regular queries
            if is_aggregation and len(rows) <= 10:
                # For aggregations, create a summary text
                summary_parts = []
                for row in rows:
                    row_parts = []
                    for k, v in row.items():
                        if v is not None:
                            # Format numbers nicely
                            if isinstance(v, (int, float)):
                                if isinstance(v, float) and v.is_integer():
                                    v = int(v)
                                row_parts.append(f"{k} = {v}")
                            else:
                                row_parts.append(f"{k} = {v}")
                    if row_parts:
                        summary_parts.append(" | ".join(row_parts))
                
                # Create a single result with all aggregation data
                if summary_parts:
                    text = "\n".join(summary_parts)
                    result = {
                        "corpus": "sas",
                        "chunk_id": "sql_aggregation_result",
                        "score": 1.0,
                        "text": text,
                        "metadata": {"query_type": "aggregation", "row_count": len(rows)},
                    }
                    results.append(result)
            else:
                # Regular query results - format each row
                for idx, row in enumerate(rows):
                    # Convert row to text representation
                    text_parts = [f"{k}: {v}" for k, v in row.items() if v is not None]
                    text = " | ".join(text_parts)

                    # Create result in same format as vector search
                    result = {
                        "corpus": "sas",
                        "chunk_id": f"sql_result_{idx}",
                        "score": 1.0 - (idx * 0.1),  # Simple ranking (first result = 1.0)
                        "text": text,
                        "metadata": dict(row),  # Store original row data
                    }
                    results.append(result)

            return results

        except Exception as e:
            logger.error("sas_sql_search_failed", query=query[:50], error=str(e))
            return []

    def _search_context(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Search context cache (pre-computed Q&A examples).
        
        Uses improved similarity scoring to better match queries.
        
        Args:
            query: User query
            top_k: Maximum number of context examples to return
            
        Returns:
            List of context results in same format as other retrievers
        """
        try:
            examples = self.context_examples.get_examples(max_examples=top_k * 2, query=query)  # Get more for better scoring
            
            results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for idx, ex in enumerate(examples):
                question = ex.get("question", "").lower()
                question_words = set(question.split())
                
                # Improved similarity scoring
                # 1. Exact word matches
                exact_matches = query_words & question_words
                
                # 2. Partial word matches (substring)
                partial_matches = sum(
                    1 for qw in query_words
                    for qw2 in question_words
                    if qw in qw2 or qw2 in qw
                )
                
                # 3. Calculate Jaccard similarity
                union = query_words | question_words
                intersection = query_words & question_words
                jaccard = len(intersection) / len(union) if union else 0.0
                
                # 4. Weighted score: Jaccard (70%) + exact matches (20%) + partial (10%)
                similarity = (
                    jaccard * 0.7 +
                    (len(exact_matches) / max(len(query_words), 1)) * 0.2 +
                    min(partial_matches / max(len(query_words), 1), 1.0) * 0.1
                )
                
                result = {
                    "corpus": "context",
                    "chunk_id": f"context_{idx}",
                    "score": min(similarity, 1.0),
                    "text": ex.get("answer", ""),
                    "metadata": {
                        "question": ex.get("question", ""),
                        "source": ex.get("source", ""),
                        "query_type": "cached_answer",
                    },
                }
                results.append(result)
            
            # Sort by similarity score
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            
            # Return top_k with best scores
            return results[:top_k]
            
        except Exception as e:
            logger.error("context_search_failed", error=str(e), query=query[:50])
            return []
    
    def _combine_results_intelligently(
        self,
        query: str,
        pdf_results: list[dict[str, Any]],
        sas_results: list[dict[str, Any]],
        context_results: list[dict[str, Any]] | None,
        evaluation: dict[str, Any],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Intelligently combine results based on quality evaluation.
        
        Args:
            query: Original query
            pdf_results: PDF search results
            sas_results: SQL search results
            context_results: Context cache results (optional)
            evaluation: Quality evaluation from router
            
        Returns:
            Combined and prioritized list of results
        """
        recommendation = evaluation.get("recommendation", "use_both")
        pdf_quality = evaluation.get("pdf_quality", 0.0)
        sas_quality = evaluation.get("sas_quality", 0.0)
        context_quality = evaluation.get("context_quality", 0.0)
        
        combined: list[dict[str, Any]] = []
        
        # If context was used (and SQL was skipped), treat context as the SQL result
        use_context_as_sas = context_results and len(context_results) > 0 and len(sas_results) == 0
        
        # Apply quality thresholds (only include if quality > 0.3)
        if recommendation in ["use_pdf", "use_both", "use_all", "use_pdf_sas", "use_pdf_context"]:
            if pdf_quality > 0.3:
                # Add PDF results with quality-adjusted scores
                for result in pdf_results:
                    result["score"] = result.get("score", 0.0) * pdf_quality
                    combined.append(result)
        
        # Use context if it was selected instead of SQL, otherwise use SQL results
        if use_context_as_sas:
            # Context cache was used instead of SQL
            if context_quality > 0.3:
                for result in context_results:
                    # Context results get high priority (they're pre-computed answers)
                    result["score"] = result.get("score", 0.0) * context_quality * 1.3  # Higher boost for cache hits
                    combined.append(result)
        elif recommendation in ["use_sas", "use_both", "use_all", "use_pdf_sas", "use_sas_context"]:
            if sas_quality > 0.3:
                # Add SQL results with quality-adjusted scores
                for result in sas_results:
                    result["score"] = result.get("score", 0.0) * sas_quality
                    combined.append(result)
        
        # If context is available but SQL was also generated, include context as additional context
        if context_results and not use_context_as_sas and context_quality > 0.3:
            # Context available but SQL was also used - include context as supplementary
            for result in context_results:
                result["score"] = result.get("score", 0.0) * context_quality * 0.8  # Lower priority as supplement
                combined.append(result)
        
        # Sort by adjusted score
        combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        # Limit to top results
        return combined[:top_k * 2]  # Allow more results since we're combining sources

    def close(self) -> None:
        """Clean up resources."""
        if self.pdf_retriever:
            self.pdf_retriever.close()
        # MySQL connections are managed via context managers, no explicit close needed
        self.loaded = False

