"""Answer generation using GPT from retrieved context."""

import os
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from src.utils.config import Config
from src.utils.logging import get_logger, log_timing
from src.utils.prompt_examples import PromptExamples

logger = get_logger(__name__)


class AnswerGenerator:
    """Generate answers using GPT from retrieved context."""

    def __init__(self, config: Config | None = None):
        """
        Initialize answer generator.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        if OpenAI is None:
            raise ImportError("openai not installed. Install with: pip install openai")

        self.config = config or Config.from_env()
        
        if not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for answer generation")
        
        self.client = OpenAI(api_key=self.config.openai_api_key)
        self.model = os.getenv("ANSWER_MODEL", "gpt-4o")  # Latest GPT-4o model for better performance
        
        # Load prompt examples for few-shot learning
        self.prompt_examples = PromptExamples()
        try:
            self.prompt_examples.load()
            if self.prompt_examples.count() > 0:
                logger.info("prompt_examples_loaded", count=self.prompt_examples.count())
        except Exception as e:
            logger.warning("prompt_examples_load_failed", error=str(e))
            self.prompt_examples = None

    @log_timing("generate_answer")
    def generate(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        max_context_tokens: int = 3000,
    ) -> str:
        """
        Generate answer from query and context chunks using GPT.

        Args:
            query: User query
            context_chunks: List of retrieved chunks with 'text', 'corpus', 'score', etc.
            max_context_tokens: Maximum tokens to use for context (rough estimate)

        Returns:
            Generated answer string
        """
        if not context_chunks:
            return "I couldn't find any relevant information to answer your question."

        # Build context from chunks with proper formatting
        context_sections = []
        total_chars = 0
        max_chars = max_context_tokens * 4  # Rough estimate: 4 chars per token

        for chunk in context_chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue
            
            corpus = chunk.get("corpus", "unknown").upper()
            score = chunk.get("score", 0.0)
            
            # Special handling for context cache results
            if corpus == "CONTEXT":
                metadata = chunk.get("metadata", {})
                original_q = metadata.get("question", "")
                context_part = f"[Source: CONTEXT CACHE (Similar Q: {original_q[:80]}...), Relevance: {score:.2f}]\n{text}"
            else:
                context_part = f"[Source: {corpus}, Relevance: {score:.2f}]\n{text}"
            
            if total_chars + len(context_part) > max_chars:
                break
            
            context_sections.append(context_part)
            total_chars += len(context_part)

        if not context_sections:
            return "I found some documents but couldn't extract meaningful content to answer your question."

        context = "\n\n---\n\n".join(context_sections)

        # Check if we have context cache results (pre-computed answers)
        context_results = [chunk for chunk in context_chunks if chunk.get("corpus") == "context"]
        has_context_cache = len(context_results) > 0
        
        # Get relevant prompt examples for few-shot learning (as templates)
        examples_text = ""
        if self.prompt_examples:
            try:
                examples_text = self.prompt_examples.format_for_prompt(
                    max_examples=3,
                    query=query
                )
            except Exception as e:
                logger.warning("prompt_examples_format_failed", error=str(e))

        # Build prompt - enhanced for context-aware generation
        system_prompt = """You are a helpful assistant that answers questions about clinical trial data and documents.

Your task is to:
1. Answer the user's question based ONLY on the provided context
2. Be accurate and cite specific information from the context
3. If the context doesn't contain enough information, say so clearly
4. Write in a clear, professional manner
5. Focus on the most relevant information from the context
6. Follow the style and format of the example answers provided below
7. If context cache results are available, use them as templates but adapt to the current query

Do NOT:
- Make up information not in the context
- Speculate beyond what's provided
- Include information from outside the context"""

        
        # Include examples in user prompt if available
        examples_section = f"\n\n{examples_text}\n" if examples_text else ""
        
        # Add note about context cache if present
        context_note = ""
        if has_context_cache:
            context_note = "\n\nNote: Some results are from the context cache (pre-computed answers). Use them as templates but adapt to the current query."
        
        user_prompt = f"""Context from documents:

{context}

---{examples_section}{context_note}Question: {query}

Please provide a clear, accurate answer based on the context above. If the context doesn't fully answer the question, indicate what information is missing."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more factual answers
                max_tokens=1000,  # Reasonable limit for answers
            )

            answer = response.choices[0].message.content
            if not answer:
                logger.warning("empty_answer_from_gpt", query=query[:50])
                return "I couldn't generate an answer. Please check the sources below for more information."

            logger.info(
                "answer_generated",
                query_preview=query[:50],
                chunks_used=len(context_sections),
                answer_length=len(answer),
            )

            return answer.strip()

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e), query_preview=query[:50])
            # Fallback: return first chunk as answer
            if context_chunks:
                first_chunk = context_chunks[0].get("text", "").strip()
                if first_chunk:
                    return f"Based on the documents: {first_chunk[:500]}..."
            return "I encountered an error generating an answer. Please check the sources below."

