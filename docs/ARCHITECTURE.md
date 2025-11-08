# Architecture Documentation

## Overview

CoTrial RAG v2 is a retrieval-augmented generation system that enables querying over two distinct corpora (PDF documents and SAS clinical data) through a unified API. The system uses FAISS for vector similarity search, S3 for index storage, and FastAPI for the API layer.

## System Components

### 1. Indexing Pipeline

```
PDF/SAS Files → Text Extraction → Chunking → Embedding → FAISS Index → S3 Storage
```

#### PDF Indexer (`src/indexers/build_pdf_index.py`)
- Extracts text from PDF files using `pypdf`
- Chunks text with overlap (configurable tokens)
- Generates embeddings via OpenAI API
- Builds FAISS IndexFlatIP (cosine similarity)
- Uploads to S3 and updates manifest

#### SAS Indexer (`src/indexers/build_sas_index.py`)
- Reads SAS files using `pyreadstat` or `pandas`
- Converts rows to semantic text representations
- Chunks if needed, then embeds
- Same FAISS + S3 workflow as PDF indexer

### 2. Storage Layer

#### Manifest Schema (`src/data_schemas/manifest.py`)
JSON file at `s3://{RAG_BUCKET}/{RAG_MANIFEST_KEY}`:

```json
{
  "version": "v20250101",
  "corpora": {
    "pdf": {
      "prefix": "rag/pdf_index/v20250101/",
      "files": ["index.faiss", "ids.jsonl", "docs.jsonl"],
      "dimension": 1536,
      "count": 12345
    },
    "sas": { ... }
  }
}
```

#### Index Artifacts
Each corpus version has:
- `index.faiss`: FAISS index file (L2-normalized vectors, IndexFlatIP)
- `ids.jsonl`: Mapping `ann_id` (FAISS internal) → `chunk_id` (semantic ID)
- `docs.jsonl`: Mapping `chunk_id` → `{text, metadata}`

### 3. Retrieval Layer

#### Retriever Protocol (`src/retrieval/base.py`)
Defines interface:
- `load_from_manifest(bucket, manifest_key)`: Load indices from S3
- `search(query, top_k)`: Search and return results
- `close()`: Cleanup resources

#### FAISS S3 Retriever (`src/retrieval/faiss_s3.py`)
- Downloads manifest from S3
- For each corpus:
  - Downloads index files to `/tmp/rag/<corpus>/<version>/`
  - Loads FAISS index
  - Builds in-memory maps: `ann_id → chunk_id → {text, metadata}`
- At search time:
  - Embeds query
  - Searches each corpus FAISS index
  - Fuses results via RRF

### 4. Fusion Strategy

#### Reciprocal Rank Fusion (`src/utils/fusion.py`)
Combines ranked lists from multiple corpora:

```
For each document d at rank r in list:
  score += 1 / (k + r)
  
Sort by combined score (descending)
```

Default `k=60` (configurable via `FUSION_K`).

### 5. API Layer

#### FastAPI Application (`src/api/server.py`)
- **Startup**: Loads retriever from manifest
- **Routes**:
  - `GET /v1/status`: System status
  - `POST /v1/chat`: Query endpoint
  - `GET /health`: Health check
- **Middleware**: Request ID tracking, structured logging

#### Request Flow

```
Client Request
  ↓
FastAPI Middleware (request ID, logging)
  ↓
Chat Endpoint
  ↓
Embed Query (OpenAI or offline)
  ↓
Retriever.search(query, top_k)
  ├─→ FAISS Search (PDF corpus)
  ├─→ FAISS Search (SAS corpus)
  └─→ RRF Fusion
  ↓
Generate Answer (simple concatenation or LLM)
  ↓
Return Response with Citations
```

## Data Flow

### Indexing Flow

```
1. PDF/SAS Files → Indexer
2. Text Extraction
3. Chunking (with overlap)
4. Embedding (OpenAI API)
5. L2 Normalization
6. FAISS Index Creation (IndexFlatIP)
7. Write Artifacts:
   - index.faiss
   - ids.jsonl (ann_id → chunk_id)
   - docs.jsonl (chunk_id → {text, metadata})
8. Upload to S3: s3://bucket/{prefix}/v{version}/
9. Update Manifest (download, modify, upload)
```

### Query Flow

```
1. Client → POST /v1/chat {"query": "..."}
2. FastAPI → Embed Query
3. Retriever.search():
   a. Embed query vector (L2 normalized)
   b. For each corpus:
      - FAISS search (IndexFlatIP, top_k results)
      - Map ann_id → chunk_id → {text, metadata}
      - Build ranked list
   c. RRF Fusion (combine ranked lists)
4. Generate Answer:
   - Concatenate top snippets (or call LLM)
5. Return: {answer, citations[]}
```

## Cold Start vs Warm Path

### Cold Start (< 3s target)
1. Lambda initialization
2. Download manifest from S3
3. Download index files to `/tmp/rag/<corpus>/<version>/`
4. Load FAISS indices into memory
5. Build ID and doc maps
6. Ready to serve requests

### Warm Path
- Indices already in `/tmp` (persists across invocations)
- Only load if version changed (ETag check)
- Fast response time (< 100ms for small indices)

## Vector Similarity

### Normalization Strategy
- **Index time**: All document vectors L2-normalized before adding to FAISS
- **Query time**: Query vector L2-normalized before search
- **FAISS Index**: `IndexFlatIP` (Inner Product)
- **Similarity**: Cosine similarity = dot product (when vectors normalized)

### Why IndexFlatIP?
- Fast exact search (no approximation)
- Simple, no training required
- Works well for moderate corpus sizes (< 1M vectors)
- Can upgrade to `IndexIVFFlat` or `HNSW` for larger corpora

## Error Handling

### Retriever Errors
- **Missing manifest**: 503 Service Unavailable
- **Missing corpus files**: 503 with structured log
- **Dimension mismatch**: Validation error at load time
- **S3 permissions**: 403/404 logged, 503 to client

### API Errors
- **Invalid request**: 422 Validation Error (Pydantic)
- **Retriever not loaded**: 503 Service Unavailable
- **Embedding failure**: 500 with error details
- **Search failure**: 500 with error details

All errors logged with structured JSON (request_id, error, context).

## Threat Model

### Security Considerations

1. **S3 Access**
   - Lambda IAM role: Read-only on RAG bucket
   - Bucket policy: Private, SSE enabled
   - No write access from Lambda (read-only at runtime)

2. **Secrets Management**
   - OpenAI API key: Environment variable (or Secrets Manager)
   - No secrets in code or version control
   - Rotate keys periodically

3. **Input Validation**
   - Pydantic models validate all inputs
   - Query length limits (configurable)
   - Top-k bounds (reasonable limits)

4. **API Security**
   - Consider API Gateway throttling
   - Add authentication/authorization (not in current scope)
   - Rate limiting (API Gateway or application-level)

### Attack Vectors

1. **S3 Bucket Enumeration**: Prevented by private bucket
2. **Manifest Tampering**: Use versioned manifests, verify checksums
3. **Query Injection**: Input validation via Pydantic
4. **DoS via Large Queries**: Query length limits, timeout

## Scalability

### Current Limits
- **Corpus size**: ~100K-1M vectors per corpus (IndexFlatIP)
- **Lambda memory**: 2048 MB (adjustable)
- **Lambda timeout**: 30s (adjustable)
- **Cold start**: < 3s for small indices

### Future Scaling Options

1. **Larger Corpora**
   - Switch to `IndexIVFFlat` (approximate, faster)
   - Use `HNSW` for very large indices
   - Shard indices across multiple S3 objects

2. **Performance**
   - Provisioned concurrency (eliminate cold starts)
   - Lambda Layers for FAISS (faster startup)
   - Regional replication (S3 + Lambda)

3. **Cost Optimization**
   - Batch embeddings (multiple queries)
   - Cache embeddings (per query text)
   - Use smaller embedding models (e.g., `text-embedding-ada-002`)

## Future Roadmap

### Short-term
- [ ] Reranker (cross-encoder) for better relevance
- [ ] Hybrid search (keyword + vector)
- [ ] LLM integration for answer generation (beyond simple concatenation)

### Medium-term
- [ ] RAGAs evaluation framework
- [ ] Batch query processing
- [ ] Multi-region deployment

### Long-term
- [ ] Real-time index updates (streaming)
- [ ] Multi-modal support (images, tables)
- [ ] Advanced fusion strategies (weighted RRF)

## Dependencies

### Core
- `fastapi`: Web framework
- `faiss-cpu`: Vector search
- `boto3`: AWS SDK
- `openai`: Embeddings API
- `pydantic`: Data validation

### Indexing
- `pypdf`: PDF text extraction
- `pandas`: Data manipulation
- `pyreadstat`: SAS file reading

### Deployment
- `mangum`: ASGI adapter for Lambda
- `structlog`: Structured logging

## Testing Strategy

### Unit Tests
- Fusion algorithm (deterministic)
- Embedding utilities (offline mode)
- Chunking logic
- Manifest schema validation

### Integration Tests
- Status endpoint (with mocked S3)
- Retrieval with test fixtures
- End-to-end query flow (offline embeddings)

### Test Fixtures
- Small FAISS indices (generated in tests)
- Mock manifest JSON
- Deterministic embeddings (hash-based)

## Observability

### Logging
- **Format**: JSON (structured)
- **Fields**: request_id, timestamp (UTC), level, message, context
- **Timings**: Per-operation duration (ms)
- **Sizes**: Index counts, result counts

### Metrics (Future)
- Query latency (p50, p95, p99)
- Cold start frequency
- Error rates
- Index load times

### Tracing (Future)
- AWS X-Ray integration
- Distributed tracing across services

