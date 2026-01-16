# Agentic Routing Architecture

## Overview

The system now implements a sophisticated **result-aware routing** architecture with three data sources:

1. **PDF Documents** (Vector DB) - Protocol documents, study design
2. **SQL Database** (SAS data) - Patient data, statistics, aggregations
3. **Context Cache** (Q&A examples) - Pre-computed answers as a caching mechanism

## Architecture Flow

```
User Query
    ↓
[Step 1: Context Cache Lookup]
    ↓ (Fast similarity search)
[Step 2: Agentic Router]
    ↓ (LLM decides: pdf | sas | context | both | all | pdf+context | sas+context)
[Step 3: Parallel Search]
    ├─ PDF Vector Search (if needed)
    └─ SQL Query Generation & Execution (if needed)
    ↓
[Step 4: Result Quality Evaluation]
    ↓ (LLM evaluates quality of each source)
[Step 5: Intelligent Result Combination]
    ↓ (Quality-adjusted scores, filtering, prioritization)
[Step 6: Answer Generation]
    ↓ (GPT-4o with context-aware templates)
Final Answer
```

## Key Components

### 1. AgenticRouter (`src/utils/agentic_router.py`)

**Responsibilities:**
- Pre-retrieval routing: Decides which sources to search
- Post-retrieval evaluation: Evaluates result quality
- Context-aware routing: Considers similar questions from cache

**Routing Options:**
- `"pdf"` - PDF documents only
- `"sas"` - SQL database only
- `"context"` - Context cache only
- `"both"` - PDF + SQL
- `"all"` - PDF + SQL + Context
- `"pdf+context"` - PDF + Context
- `"sas+context"` - SQL + Context

**Methods:**
- `route_query(query, context_examples)` - Initial routing decision
- `evaluate_result_quality(query, pdf_results, sas_results, context_results)` - Post-retrieval evaluation

### 2. HybridRetriever (`src/retrieval/hybrid.py`)

**Responsibilities:**
- Parallel search execution
- Context cache integration
- Intelligent result combination

**Key Features:**
- **Parallel Search**: PDF and SQL searches run simultaneously using `ThreadPoolExecutor`
- **Context Integration**: Fast lookup of similar questions before routing
- **Quality-Based Combination**: Results combined based on LLM quality evaluation

**Methods:**
- `search(query, top_k)` - Main search method with result-aware routing
- `_search_context(query, top_k)` - Context cache search
- `_search_sas_sql(query, top_k)` - SQL-based search
- `_combine_results_intelligently(...)` - Quality-aware result combination

### 3. AnswerGenerator (`src/utils/answer_generator.py`)

**Responsibilities:**
- Generate answers from retrieved context
- Template-based generation using context cache

**Key Features:**
- **Context-Aware**: Special handling for context cache results
- **Template Usage**: Uses context cache as templates for answer style
- **Few-Shot Learning**: Includes prompt examples for better formatting

## Result-Aware Routing (Option 2)

### Implementation Details

1. **Parallel Search**
   ```python
   with ThreadPoolExecutor(max_workers=2) as executor:
       futures["pdf"] = executor.submit(pdf_retriever.search, query, top_k)
       futures["sas"] = executor.submit(_search_sas_sql, query, top_k)
   ```

2. **Quality Evaluation**
   - LLM evaluates each source's results
   - Scores: `pdf_quality`, `sas_quality`, `context_quality` (0.0-1.0)
   - Recommendation: Which sources to use/combine

3. **Intelligent Combination**
   - Quality threshold: Only include results with quality > 0.3
   - Score adjustment: Results scores multiplied by quality scores
   - Context boost: Context cache results get 1.2x multiplier
   - Prioritization: Sorted by adjusted scores

## Context Cache as Third Route

### How It Works

1. **Fast Lookup**: Context cache is searched first (keyword similarity)
2. **Routing Input**: Similar questions inform routing decision
3. **Template Usage**: Context results used as templates in answer generation
4. **Caching Mechanism**: Pre-computed Q&A pairs act as fast lookup

### Context Search

- **Location**: `data/prompt_engineering/*.json`
- **Format**: `{"question": "...", "answer": "...", "source": "..."}`
- **Similarity**: Keyword overlap between query and cached questions
- **Auto-cleaning**: Structured answers converted to natural language

## Quality Evaluation

The LLM evaluates results based on:
- **Relevance**: How well results match the query
- **Completeness**: Whether results fully answer the question
- **Quality**: Data quality and accuracy
- **Complementarity**: Whether results from different sources complement each other

**Evaluation Output:**
```json
{
  "pdf_quality": 0.8,
  "sas_quality": 0.6,
  "context_quality": 0.9,
  "recommendation": "use_all",
  "reasoning": "PDF provides protocol context, SQL provides data, context cache has similar answer",
  "confidence": 0.85
}
```

## Benefits

1. **Performance**: Parallel search reduces latency
2. **Quality**: LLM evaluation ensures only good results are used
3. **Intelligence**: Context-aware routing improves accuracy
4. **Caching**: Context cache provides fast answers for similar questions
5. **Flexibility**: Multiple routing options handle diverse query types

## Configuration

**Environment Variables:**
- `ROUTER_MODEL` - Model for routing (default: `gpt-4o-mini`)
- `ANSWER_MODEL` - Model for answer generation (default: `gpt-4o`)
- `SQL_MODEL` - Model for SQL generation (default: `gpt-4o-mini`)

**Context Cache:**
- Location: `data/prompt_engineering/`
- Auto-loaded on startup
- Auto-cleaned on load (removes "Not computable" entries)

## Example Flow

**Query**: "How many immune-system disorder AEs are recorded?"

1. **Context Lookup**: Finds similar question in cache
2. **Routing**: Router sees context match, routes to `"sas+context"`
3. **Parallel Search**: 
   - SQL: `SELECT COUNT(*) FROM events WHERE aeterm LIKE '%immune%'`
   - Context: Similar Q&A from cache
4. **Quality Evaluation**: 
   - SQL quality: 0.9 (direct answer)
   - Context quality: 0.7 (similar but not exact)
5. **Combination**: SQL results prioritized, context used as template
6. **Answer Generation**: GPT-4o generates answer using SQL data + context template

## Future Enhancements

- **Learning**: Track which routes work best for different query types
- **Caching**: Cache routing decisions for similar queries
- **Feedback Loop**: Use answer quality to improve routing
- **Multi-stage Routing**: Re-route if initial results are insufficient

