"""Agentic reasoning layer for intelligent query routing."""

import json
import os
from typing import Any, Literal

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.utils.config import Config
from src.utils.logging import get_logger, log_timing

logger = get_logger(__name__)


class AgenticRouter:
    """
    Agentic reasoning layer that uses LLM to determine query routing.
    
    Intelligently decides whether to search:
    - PDF documents (vector database) - for protocol, inclusion/exclusion criteria, study design, etc.
    - SAS/patient data (SQL database) - for patient demographics, events, visits, treatments, etc.
    - Context (pre-computed Q&A cache) - for similar questions that have been answered before
    - Both/All - when query requires information from multiple sources
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize agentic router.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        if OpenAI is None:
            raise ImportError("openai not installed. Install with: pip install openai")

        self.config = config or Config.from_env()
        self.client = OpenAI(api_key=self.config.openai_api_key)
        
        # Use a fast, cost-effective model for routing decisions
        # Can be overridden via environment variable
        self.model = os.getenv("ROUTER_MODEL", "gpt-4o-mini")  # Fast and cheap for simple routing decisions
        
        # System prompt with context about data sources
        self.system_prompt = """You are an intelligent query routing system for a clinical trial RAG system.

You need to determine which data source(s) to search based on the user's query:

**PDF Documents (Vector Search):**
- Protocol documents, study design, methodology
- Inclusion/exclusion criteria
- Procedures, guidelines, specifications
- General study information and documentation
- Questions about "what", "how", "why" regarding study design

**SAS/Patient Data (SQL Database):**
- Patient demographics (age, sex, race, etc.)
- Subject counts, statistics, aggregations
- Treatment assignments, arms, groups
- Visit data, events, adverse events
- Specific patient records or data points
- Questions about "how many", "which patients", "show me data"

**Context (Pre-computed Q&A Cache):**
- Similar questions that have been answered before
- Pre-computed analysis results
- Cached answers from previous queries
- ONLY used for SQL/data queries (not for PDF/document queries)
- Acts as a fast lookup/caching mechanism for data queries

**Routing Strategy:**
- PDF queries: Use "pdf" (context cache not needed, PDF search works well)
- SQL/data queries: Use "sas" (context will be checked automatically before SQL)
- Mixed queries: Use "both"

**Combinations:**
- "both": PDF + SAS (context checked for SQL part only)
- "all": PDF + SAS + Context (rare, only if explicitly needed)

Respond with a JSON object:
{
  "route": "pdf" | "sas" | "both",
  "reasoning": "brief explanation of why this route was chosen",
  "confidence": 0.0-1.0
}

Be decisive and choose the most appropriate route. Do NOT use "context" as a standalone route - it's checked automatically for SQL queries."""

    @log_timing("agentic_routing")
    def route_query(self, query: str, context_examples: list[dict[str, Any]] | None = None) -> str:
        """
        Use LLM to intelligently route the query.

        Args:
            query: User query text
            context_examples: Optional list of similar context examples to consider

        Returns:
            Route string: "pdf", "sas", "context", "both", "all", "pdf+context", or "sas+context"
        """
        # Build enhanced prompt with context examples if available
        user_prompt = f"Route this query: {query}"
        if context_examples and len(context_examples) > 0:
            examples_text = "\n".join([
                f"- Similar Q: {ex.get('question', '')[:100]}"
                for ex in context_examples[:3]
            ])
            user_prompt += f"\n\nSimilar questions found in context cache:\n{examples_text}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent routing
                max_tokens=150,  # Small response for routing decision
            )

            # Parse response
            content = response.choices[0].message.content
            if not content:
                logger.warning("empty_routing_response", query=query[:50])
                return self._fallback_route(query)

            routing_decision = json.loads(content)
            route = routing_decision.get("route", "").lower()
            reasoning = routing_decision.get("reasoning", "")
            confidence = routing_decision.get("confidence", 0.0)

            # Validate route (simplified - context is handled automatically for SQL)
            valid_routes = ["pdf", "sas", "both"]
            if route not in valid_routes:
                logger.warning("invalid_route_from_llm", route=route, query=query[:50])
                return self._fallback_route(query)

            logger.info(
                "query_routed_agentic",
                query_preview=query[:50],
                route=route,
                reasoning=reasoning,
                confidence=confidence,
            )

            return route

        except json.JSONDecodeError as e:
            logger.error("json_decode_error", error=str(e), response=content[:100] if 'content' in locals() else "N/A")
            return self._fallback_route(query)
        except Exception as e:
            logger.error("agentic_routing_failed", error=str(e), query=query[:50])
            return self._fallback_route(query)

    def _fallback_route(self, query: str) -> str:
        """
        Fallback routing using simple heuristics if LLM fails.

        Args:
            query: User query text

        Returns:
            Route string
        """
        query_lower = query.lower()

        # Simple keyword-based fallback
        sql_keywords = [
            "how many", "count", "patient", "subject", "age", "sex", "gender",
            "treatment", "arm", "visit", "event", "show me", "list", "filter"
        ]
        
        doc_keywords = [
            "inclusion", "exclusion", "criteria", "protocol", "design",
            "methodology", "procedure", "guideline"
        ]

        has_sql = any(kw in query_lower for kw in sql_keywords)
        has_doc = any(kw in query_lower for kw in doc_keywords)

        if has_sql and has_doc:
            route = "both"
        elif has_sql:
            route = "sas"
        else:
            route = "pdf"  # Default to PDF

        logger.info("fallback_routing_used", query=query[:50], route=route)
        return route
    
    def evaluate_result_quality(
        self,
        query: str,
        pdf_results: list[dict[str, Any]],
        sas_results: list[dict[str, Any]],
        context_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Use LLM to evaluate the quality of retrieved results and decide which to use.
        
        Args:
            query: Original user query
            pdf_results: Results from PDF vector search
            sas_results: Results from SQL database
            context_results: Results from context cache (optional)
            
        Returns:
            Dict with evaluation scores and recommendations
        """
        # Build summary of results
        pdf_summary = f"Found {len(pdf_results)} PDF results. Top result: {pdf_results[0].get('text', '')[:200] if pdf_results else 'None'}..."
        sas_summary = f"Found {len(sas_results)} SQL results. Top result: {sas_results[0].get('text', '')[:200] if sas_results else 'None'}..."
        context_summary = ""
        if context_results:
            context_summary = f"Found {len(context_results)} context cache results. Top match: {context_results[0].get('question', '')[:100] if context_results else 'None'}..."
        
        evaluation_prompt = f"""Evaluate the quality of retrieved results for this query:

Query: {query}

Results Summary:
- PDF: {pdf_summary}
- SQL: {sas_summary}
{f"- Context: {context_summary}" if context_summary else ""}

Evaluate each source and respond with JSON:
{{
  "pdf_quality": 0.0-1.0,
  "sas_quality": 0.0-1.0,
  "context_quality": 0.0-1.0,
  "recommendation": "use_pdf" | "use_sas" | "use_context" | "use_both" | "use_all" | "use_pdf_sas" | "use_pdf_context" | "use_sas_context",
  "reasoning": "brief explanation",
  "confidence": 0.0-1.0
}}

Consider:
- Relevance to the query
- Completeness of information
- Quality of the data
- Whether results complement each other"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating search result quality for clinical trial queries."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            
            content = response.choices[0].message.content
            if content:
                evaluation = json.loads(content)
                logger.info(
                    "result_quality_evaluated",
                    query_preview=query[:50],
                    pdf_quality=evaluation.get("pdf_quality", 0.0),
                    sas_quality=evaluation.get("sas_quality", 0.0),
                    recommendation=evaluation.get("recommendation", "use_both"),
                )
                return evaluation
        except Exception as e:
            logger.error("result_quality_evaluation_failed", error=str(e), query=query[:50])
        
        # Fallback: simple heuristic
        return {
            "pdf_quality": 0.7 if pdf_results else 0.0,
            "sas_quality": 0.7 if sas_results else 0.0,
            "context_quality": 0.8 if context_results else 0.0,
            "recommendation": "use_both" if pdf_results and sas_results else ("use_pdf" if pdf_results else "use_sas"),
            "reasoning": "Fallback evaluation",
            "confidence": 0.5,
        }

