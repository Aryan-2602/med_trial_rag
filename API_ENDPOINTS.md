# API Endpoints Guide

## Base URL
```
https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod
```

## Available Endpoints

### 1. Root Endpoint
**GET** `/`

Returns API information and available endpoints.

**Example:**
```bash
curl https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/
```

**Response:**
```json
{
  "message": "CoTrial RAG v2 API",
  "docs": "/docs",
  "health": "/health",
  "status": "/v1/status",
  "chat": "/v1/chat (POST only)",
  "note": "Use /docs for interactive API documentation. Chat endpoint requires POST method."
}
```

### 2. Health Check
**GET** `/health`

Simple health check endpoint.

**Example:**
```bash
curl https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/health
```

**Response:**
```json
{"status": "ok"}
```

### 3. Status
**GET** `/v1/status`

Get detailed status of the RAG system including loaded indices.

**Example:**
```bash
curl https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/status
```

**Response:**
```json
{
  "retriever": "faiss",
  "manifest_version": "v20251104",
  "corpora": {
    "pdf": 184,
    "sas": 75651
  },
  "loaded": true
}
```

### 4. Chat (Query Endpoint)
**POST** `/v1/chat`

⚠️ **POST method required** - Cannot be accessed via browser GET request.

Query the RAG system with a question and get an answer with citations.

**Example:**
```bash
curl -X POST https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the inclusion criteria?",
    "top_k": 5
  }'
```

**Request Body:**
```json
{
  "query": "Your question here",
  "top_k": 5  // Optional: number of results per corpus (default from config)
}
```

**Response:**
```json
{
  "answer": "The answer based on retrieved documents...",
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

### 5. API Documentation
**GET** `/docs`

Interactive Swagger UI documentation. 

**Note:** If `/docs` shows a 403 error for `/openapi.json`, you can access the OpenAPI schema directly:
- **GET** `/openapi.json` - Raw OpenAPI JSON schema

**Alternative:** Use `/redoc` for ReDoc-style documentation.

## Testing in Browser

✅ **Works in browser:**
- `/` - Root endpoint
- `/health` - Health check
- `/v1/status` - Status
- `/docs` - API documentation (if `/openapi.json` loads correctly)
- `/openapi.json` - OpenAPI schema

❌ **Does NOT work in browser (requires POST):**
- `/v1/chat` - Returns "Method Not Allowed" when accessed via GET

## Testing with curl

All endpoints work with curl. Example for chat:

```bash
curl -X POST https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the inclusion criteria?"}' | python3 -m json.tool
```

## Testing with Python

```python
import requests

url = "https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/chat"

response = requests.post(
    url,
    json={"query": "What are the inclusion criteria?"}
)

print(response.json())
```

## Common Issues

### "Missing Authentication Token"
- **Cause:** You're accessing a path that doesn't exist
- **Solution:** Use one of the documented endpoints above

### "Method Not Allowed" on `/v1/chat`
- **Cause:** Trying to access POST endpoint with GET (browser)
- **Solution:** Use POST method with curl or a REST client

### 403 Error on `/docs` when loading `/openapi.json`
- **Cause:** API Gateway routing issue
- **Solution:** Access `/openapi.json` directly, or use `/redoc` instead

## Response Times

- **Health/Status:** ~100-500ms (fast)
- **Chat (first request):** ~20-30 seconds (downloads indices from S3 to EFS)
- **Chat (subsequent requests):** ~2-5 seconds (uses cached indices from EFS)

