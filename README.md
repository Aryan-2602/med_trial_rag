# CoTrial RAG v2

A production-ready RAG (Retrieval-Augmented Generation) system that provides a single chat-style API to query two corpora:

- **SAS corpus**: Tabular/clinical data (chunked + embedded)
- **PDF corpus**: Documents (chunked + embedded)

Both corpora are indexed as FAISS vectors and stored on S3. At runtime, a FastAPI Lambda downloads indices from S3 into `/tmp`, loads FAISS, performs per-corpus search, then fuses results via Reciprocal Rank Fusion (RRF). It then optionally calls an LLM (OpenAI) with the fused context to produce an answer with citations.

## Features

- **Dual Corpus Support**: Query both PDF documents and SAS clinical data simultaneously
- **FAISS Vector Search**: Fast similarity search using FAISS with cosine similarity
- **Reciprocal Rank Fusion**: Combines results from multiple corpora intelligently
- **S3-Based Storage**: Indices stored on S3 for scalability
- **FastAPI API**: Modern, type-safe API with automatic documentation
- **AWS Lambda Ready**: Deployable as serverless function
- **Offline Testing**: Deterministic embeddings for testing without API keys
- **Structured Logging**: JSON logs with request IDs and timing information

## Architecture

- **Language**: Python 3.11+ with type hints
- **Framework**: FastAPI, Pydantic v2
- **Vector Search**: FAISS (IndexFlatIP for cosine similarity)
- **Storage**: S3 (read-only at runtime)
- **Embeddings**: OpenAI text-embedding-3-small (configurable)
- **Deployment**: AWS Lambda + API Gateway (SAM template included)

## Quickstart

### Prerequisites

- Python 3.11+
- AWS account with S3 bucket
- OpenAI API key (for embeddings)
- (Optional) AWS SAM CLI for deployment

### Local Development

1. **Clone and setup environment**:

```bash
# Create virtual environment (if not already created)
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# Or use the helper script:
source activate.sh

# On Windows:
# .venv\Scripts\activate
# Or use the helper script:
# activate.bat

# Install dependencies
make install
```

2. **Configure environment variables**:

```bash
cp .env.example .env
# Edit .env with your values:
# RAG_BUCKET=your-bucket-name
# OPENAI_API_KEY=sk-your-key-here
```

3. **Run the API**:

```bash
make run
```

Visit `http://localhost:8000/docs` for interactive API documentation.

4. **Run the Streamlit Frontend** (optional):

```bash
# Install frontend dependencies
make install-frontend

# Run the frontend
make run-frontend
```

Visit `http://localhost:8501` for the chat interface.

**Note:** The frontend connects to the deployed API by default. To use a local API, set the `RAG_API_URL` environment variable:
```bash
export RAG_API_URL=http://localhost:8000
make run-frontend
```

### Building Indices

#### PDF Index

```bash
export RAG_BUCKET=your-bucket-name
export OPENAI_API_KEY=sk-your-key-here

make build-index-pdf
# Or manually:
python -m src.indexers.build_pdf_index \
    --input-dir data/AllProvidedFiles_438 \
    --bucket $RAG_BUCKET \
    --prefix rag/pdf_index \
    --manifest-key rag/manifest.json \
    --model text-embedding-3-small
```

#### SAS Index

```bash
make build-index-sas
# Or manually:
python -m src.indexers.build_sas_index \
    --input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
    --bucket $RAG_BUCKET \
    --prefix rag/sas_index \
    --manifest-key rag/manifest.json \
    --model text-embedding-3-small
```

### Testing

Run tests with offline embeddings (no API keys needed):

```bash
make test
```

For coverage:

```bash
make test-cov
```

### Code Quality

Format code:

```bash
make fmt
```

Lint and type check:

```bash
make lint
```

## API Endpoints

### GET /v1/status

Get status of the RAG system.

**Response**:
```json
{
  "retriever": "faiss",
  "manifest_version": "v20250101",
  "corpora": {
    "pdf": 12345,
    "sas": 9876
  },
  "loaded": true
}
```

### POST /v1/chat

Query the RAG system.

**Request**:
```json
{
  "query": "What are the inclusion criteria?",
  "top_k": 5
}
```

**Response**:
```json
{
  "answer": "The inclusion criteria are...",
  "citations": [
    {
      "corpus": "pdf",
      "chunk_id": "protocol_chunk_0",
      "score": 0.95,
      "snippet": "Inclusion criteria: 1) Age >= 18..."
    }
  ]
}
```

### GET /health

Simple health check endpoint.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_BUCKET` | S3 bucket name for indices | **Required** |
| `RAG_MANIFEST_KEY` | S3 key for manifest JSON | `rag/manifest.json` |
| `EMBED_MODEL` | Embedding model name | `text-embedding-3-small` |
| `OPENAI_API_KEY` | OpenAI API key | **Required** (unless `EMBED_OFFLINE=1`) |
| `USE_RETRIEVER` | Retriever type | `faiss` |
| `MAX_TOKENS` | Max tokens for answer | `2048` |
| `TOP_K` | Results per corpus | `5` |
| `FUSION_K` | RRF fusion constant | `8` |
| `EMBED_OFFLINE` | Use deterministic embeddings (testing) | `0` |

## Deployment

For detailed deployment instructions, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).

### Quick Start

1. **Prerequisites**: Install AWS CLI and SAM CLI
   ```bash
   brew install awscli aws-sam-cli  # macOS
   aws configure  # Set up credentials
   ```

2. **Create S3 Bucket**:
   ```bash
   export RAG_BUCKET="your-bucket-name"
   aws s3 mb s3://$RAG_BUCKET
   ```

3. **Build and Upload Indices**:
   ```bash
   source .venv/bin/activate
   export OPENAI_API_KEY="sk-your-key"
   
   # Build PDF index
   python -m src.indexers.build_pdf_index \
     --input-dir data/AllProvidedFiles_438 \
     --bucket $RAG_BUCKET \
     --prefix rag/pdf_index \
     --manifest-key rag/manifest.json
   
   # Build SAS index
   python -m src.indexers.build_sas_index \
     --input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
     --bucket $RAG_BUCKET \
     --prefix rag/sas_index \
     --manifest-key rag/manifest.json
   ```

4. **Deploy Lambda**:
   ```bash
   sam build
   sam deploy --guided
   ```

5. **Test**:
   ```bash
   # Get API URL from stack outputs
   export API_URL=$(aws cloudformation describe-stacks \
     --stack-name cotrial-rag-v2 \
     --query 'Stacks[0].Outputs[?OutputKey==`RAGApi`].OutputValue' \
     --output text)
   
   curl $API_URL/health
   curl $API_URL/v1/status | jq .
   ```

### Lambda Configuration

- **Runtime**: Python 3.11
- **Memory**: 2048 MB (adjust based on index size)
- **Timeout**: 30 seconds
- **IAM Role**: Read-only access to S3 bucket

## Project Structure

```
cotrial-ragv2/
├── src/
│   ├── api/              # FastAPI application
│   │   ├── server.py     # Main app and routes
│   │   └── models.py     # Pydantic models
│   ├── retrieval/        # Retrieval layer
│   │   ├── base.py       # Retriever protocol
│   │   └── faiss_s3.py   # FAISS + S3 retriever
│   ├── utils/            # Utilities
│   │   ├── config.py     # Configuration
│   │   ├── embeddings.py # Embedding utilities
│   │   ├── fusion.py     # RRF fusion
│   │   ├── logging.py    # Structured logging
│   │   └── s3io.py       # S3 I/O utilities
│   ├── indexers/         # Index builders
│   │   ├── common.py     # Common utilities
│   │   ├── build_pdf_index.py
│   │   └── build_sas_index.py
│   └── data_schemas/     # Data schemas
│       └── manifest.py   # Manifest schema
├── tests/                # Test suite
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md
│   └── OPS_RUNBOOK.md
├── template.yaml         # AWS SAM template
├── Makefile             # Development commands
└── requirements.txt     # Python dependencies
```

## Security

- **No secrets in code**: All secrets via environment variables
- **S3 bucket**: Private, SSE enabled (documented)
- **Lambda IAM**: Read-only access to RAG bucket only
- **Input validation**: Pydantic models validate all inputs
- **Rate limiting**: Consider adding API Gateway throttling

## Performance

- **Cold start**: < 3s for small indices (downloads from S3 to `/tmp`)
- **Warm path**: Indices cached in `/tmp/rag/<corpus>/<version>/`
- **Vector search**: FAISS IndexFlatIP (cosine similarity via dot product)
- **Normalization**: Vectors L2-normalized at index time

## Cost Considerations

- **S3**: Storage costs for indices (~100MB-1GB depending on corpus size)
- **Lambda**: Compute time (2048 MB, 30s timeout)
- **OpenAI**: Embedding API costs per query
- **API Gateway**: Request costs

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**: Indices not loaded
   - Check S3 bucket permissions
   - Verify manifest.json exists and is valid
   - Check Lambda logs for errors

2. **Dimension mismatch**: Index dimension doesn't match embedding model
   - Rebuild index with correct model
   - Update manifest.json

3. **Missing files**: Files not found in S3
   - Verify manifest.json points to correct paths
   - Check S3 bucket and keys

4. **Cold start timeout**: Lambda timeout during startup
   - Increase Lambda timeout
   - Reduce index size or use provisioned concurrency

See [OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md) for detailed operations guide.

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Run `make fmt lint test`
4. Submit PR (see `.github/PULL_REQUEST_TEMPLATE.md`)

## License

MIT

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Operations Runbook](docs/OPS_RUNBOOK.md)
