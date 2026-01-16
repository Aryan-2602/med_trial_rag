# CoTrial RAG v2

A production-ready RAG (Retrieval-Augmented Generation) system with intelligent agentic routing that queries three data sources:

- **PDF Documents**: Protocol documents, study design (ChromaDB vector search)
- **SQL Database**: Patient data, statistics, aggregations (MySQL)
- **Context Cache**: Pre-computed Q&A pairs (JSON-based caching)

The system uses **result-aware routing** with LLM-based quality evaluation to intelligently combine results from multiple sources.

## Features

- **Hybrid Architecture**: PDF (vector search), SAS (SQL queries), Context (Q&A cache)
- **Agentic Routing**: LLM-based intelligent query routing with result quality evaluation
- **ChromaDB Vector Search**: Fast semantic similarity search for PDF documents
- **LLM-based SQL Generation**: GPT converts natural language to accurate SQL queries
- **Context Cache**: Pre-computed Q&A pairs act as fast lookup for similar queries
- **Parallel Search**: PDF and SQL searches execute simultaneously
- **Result Quality Evaluation**: LLM evaluates and combines results intelligently
- **FastAPI API**: Modern, type-safe API with automatic documentation
- **Static HTML/CSS/JS Frontend**: Clean, responsive chat interface for querying
- **GPT-4o Answer Generation**: High-quality synthesized answers from retrieved context

## Architecture

- **Language**: Python 3.11+ with type hints
- **Framework**: FastAPI, Pydantic v2
- **PDF Search**: ChromaDB with OpenAI embeddings (text-embedding-3-small)
- **SAS Search**: MySQL with LLM-generated SQL queries
- **Context Cache**: JSON-based Q&A examples (auto-cleaned on load)
- **Storage**: Local ChromaDB, MySQL database
- **Embeddings**: OpenAI text-embedding-3-small
- **LLM Models**: GPT-4o (answers), GPT-4o-mini (routing, SQL generation)

## Quick Start

### Easiest Way (One Command)

```bash
# Set credentials
export MYSQL_PASSWORD=your_mysql_password
export OPENAI_API_KEY=sk-your-key-here

# Run everything
./run_app.sh
```

Opens at: **http://localhost:8501**

### Prerequisites

- Python 3.9+
- MySQL 8.0+ running on local machine
- OpenAI API key
- Git

### Complete Setup Guide

For detailed setup instructions, see **[SETUP.md](SETUP.md)** - a comprehensive guide covering:
- Automated setup script
- Manual step-by-step setup
- Troubleshooting
- Configuration options
- Verification checklist

### Quick Setup Steps

1. **Clone and navigate**:
```bash
git clone <repository-url>
cd cotrial-ragv2
```

2. **Set environment variables**:
```bash
export MYSQL_PASSWORD=your_mysql_password
export OPENAI_API_KEY=sk-your-key-here
```

3. **Run the setup script**:
```bash
chmod +x run_app.sh
./run_app.sh
```

This will automatically:
- Create virtual environment
- Install dependencies
- Check MySQL connection
- Build PDF indices (if needed)
- Start both API and frontend

**Access the app:** http://localhost:8501

For more details, see **[SETUP.md](SETUP.md)** or **[QUICK_START.md](QUICK_START.md)**

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Quick start guide
- **[docs/AGENTIC_ROUTING_ARCHITECTURE.md](docs/AGENTIC_ROUTING_ARCHITECTURE.md)** - Agentic routing architecture
- **[docs/LLM_SQL_GENERATION_GUIDE.md](docs/LLM_SQL_GENERATION_GUIDE.md)** - SQL generation guide for LLMs
- **[docs/SQL_SCHEMA.md](docs/SQL_SCHEMA.md)** - MySQL schema documentation

## API Endpoints

### GET /v1/status

Get status of the RAG system.

**Response**:
```json
{
  "retriever": "hybrid",
  "manifest_version": "v20251108",
  "corpora": {
    "pdf": 184,
    "sas": -1
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

Visit `http://localhost:8000/docs` for interactive API documentation.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_LOCAL_MODE` | Use local mode | `1` |
| `VECTOR_DB_PATH` | ChromaDB storage path | `data/vector_db` |
| `MYSQL_HOST` | MySQL host | `localhost` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_DB` | MySQL database name | `cotrial_rag` |
| `MYSQL_USER` | MySQL user | `root` |
| `MYSQL_PASSWORD` | MySQL password | **Required** |
| `EMBED_MODEL` | Embedding model name | `text-embedding-3-small` |
| `OPENAI_API_KEY` | OpenAI API key | **Required** |
| `ANSWER_MODEL` | Model for answer generation | `gpt-4o` |
| `ROUTER_MODEL` | Model for routing decisions | `gpt-4o-mini` |
| `SQL_MODEL` | Model for SQL generation | `gpt-4o-mini` |
| `TOP_K` | Results per corpus | `5` |

## Project Structure

```
cotrial-ragv2/
├── src/
│   ├── api/                  # FastAPI application
│   │   ├── server.py         # Main app and routes
│   │   └── models.py         # Pydantic models
│   ├── retrieval/            # Retrieval layer
│   │   ├── base.py           # Retriever protocol
│   │   ├── hybrid.py         # Hybrid retriever (PDF + SQL + Context)
│   │   └── vector_db_retriever.py # ChromaDB retriever
│   ├── utils/                # Utilities
│   │   ├── agentic_router.py # LLM-based query routing
│   │   ├── answer_generator.py # GPT-4o answer generation
│   │   ├── config.py         # Configuration
│   │   ├── embeddings.py     # Embedding utilities
│   │   ├── logging.py        # Structured logging
│   │   ├── mysql_client.py   # MySQL client
│   │   ├── prompt_examples.py # Context cache loader
│   │   ├── sql_generator.py  # LLM-based SQL generation
│   │   └── vector_db.py      # ChromaDB client
│   ├── indexers/             # Index builders
│   │   └── common.py         # Common utilities
│   └── frontend/             # Streamlit frontend
│       └── app.py            # Chat interface
├── scripts/                  # Utility scripts
│   ├── build_pdf_index_vector_db.py
│   ├── migrate_sas_to_mysql_optimized.py
│   ├── process_qa_for_prompt_engineering.py
│   └── batch_clean_prompt_engineering.py
├── docs/                     # Documentation
│   ├── AGENTIC_ROUTING_ARCHITECTURE.md
│   ├── LLM_SQL_GENERATION_GUIDE.md
│   └── SQL_SCHEMA.md
├── data/                     # Data directory
│   ├── vector_db/            # ChromaDB storage
│   ├── prompt_engineering/   # Q&A context cache
│   └── AllProvidedFiles_438/ # Source files
├── tests/                    # Test suite
├── Makefile                  # Development commands
├── run_app.sh                # Run everything script
├── run_api_only.sh           # Run API only
└── requirements.txt          # Python dependencies
```

## Testing

```bash
# Test local setup
make test-local

# Run unit tests
make test
```

## Code Quality

```bash
# Format code
make fmt

# Lint and type check
make lint
```

## Query Examples

### PDF Queries (Document Content)
- "What are the inclusion criteria?"
- "What are the exclusion criteria?"
- "What is the study protocol?"
- "What is the dosing schedule?"

### SQL Queries (Data Analysis)
- "How many patients are in the study?"
- "What are the most common adverse events?"
- "Show me patients with age > 65"
- "Which treatments are listed in PDSUMM and how many rows each?"

### Hybrid Queries (Both)
- "What are the inclusion criteria and how many patients meet them?"

## Troubleshooting

**Port already in use:**
```bash
lsof -i :8000  # Check API port
lsof -i :8501  # Check frontend port
```

**MySQL connection failed:**
- Check MySQL is running: `brew services list` (macOS)
- Verify password: `mysql -u root -p${MYSQL_PASSWORD} -e "SELECT 1;"`

**Vector DB not found:**
```bash
make build-pdf-indices-local
```

**Dependencies missing:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-frontend.txt
```

## License

MIT
