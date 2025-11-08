# Building and Uploading Indices

This guide walks you through building FAISS indices from your PDF and SAS files and uploading them to S3.

## Prerequisites

1. **Activate your virtual environment**:
   ```bash
   source .venv/bin/activate
   # Or: source activate.sh
   ```

2. **Set environment variables**:
   ```bash
   export RAG_BUCKET="cotrial-ragv2"  # Your S3 bucket name
   export OPENAI_API_KEY="sk-your-key-here"  # Your OpenAI API key
   ```

3. **Verify your data directory**:
   ```bash
   ls -la data/AllProvidedFiles_438/
   ```

## Step 1: Build PDF Index

This will:
- Extract text from all PDF files in the directory
- Chunk the text into smaller pieces
- Generate embeddings using OpenAI
- Build a FAISS index
- Upload everything to S3
- Update/create the manifest

```bash
python -m src.indexers.build_pdf_index \
  --input-dir data/AllProvidedFiles_438 \
  --bucket $RAG_BUCKET \
  --prefix rag/pdf_index \
  --manifest-key rag/manifest.json \
  --model text-embedding-3-small
```

**Or use the Makefile**:
```bash
make build-index-pdf
```

**Expected output**:
- S3 location: `s3://$RAG_BUCKET/rag/pdf_index/vYYYYMMDD/`
  - `index.faiss` - FAISS vector index
  - `ids.jsonl` - Mapping from index IDs to document IDs
  - `docs.jsonl` - Document metadata and chunks
- Manifest updated at: `s3://$RAG_BUCKET/rag/manifest.json`

## Step 2: Build SAS Index

This will:
- Read SAS files (.sas7bdat)
- Convert rows to text representations
- Chunk and embed the data
- Build a FAISS index
- Upload to S3
- Update the manifest

```bash
python -m src.indexers.build_sas_index \
  --input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
  --bucket $RAG_BUCKET \
  --prefix rag/sas_index \
  --manifest-key rag/manifest.json \
  --model text-embedding-3-small
```

**Or use the Makefile**:
```bash
make build-index-sas
```

**Expected output**:
- S3 location: `s3://$RAG_BUCKET/rag/sas_index/vYYYYMMDD/`
  - `index.faiss` - FAISS vector index
  - `ids.jsonl` - Mapping from index IDs to document IDs
  - `docs.jsonl` - Document metadata and chunks
- Manifest updated at: `s3://$RAG_BUCKET/rag/manifest.json`

## Step 3: Verify Upload

Check that everything was uploaded correctly:

```bash
# List all files in rag/ prefix
aws s3 ls s3://$RAG_BUCKET/rag/ --recursive

# Check the manifest
aws s3 cp s3://$RAG_BUCKET/rag/manifest.json - | python3 -m json.tool
```

**Expected manifest structure**:
```json
{
  "version": "v20250101",
  "corpora": {
    "pdf": {
      "version": "v20250101",
      "prefix": "rag/pdf_index/v20250101",
      "dimension": 1536,
      "count": 1234
    },
    "sas": {
      "version": "v20250101",
      "prefix": "rag/sas_index/v20250101",
      "dimension": 1536,
      "count": 5678
    }
  }
}
```

## Step 4: Test Your API

Once indices are uploaded, test your API:

```bash
# Get your API endpoint (from deployment output)
export API_URL="https://6dkhl1qbai.execute-api.us-east-2.amazonaws.com/Prod"

# Check status (should show both corpora loaded)
curl $API_URL/v1/status | python3 -m json.tool

# Test a query
curl -X POST $API_URL/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the inclusion criteria?"}' | python3 -m json.tool
```

## Troubleshooting

### Index Build Fails

1. **Check OpenAI API key**:
   ```bash
   echo $OPENAI_API_KEY  # Should start with "sk-"
   ```

2. **Check S3 permissions**:
   ```bash
   aws s3 ls s3://$RAG_BUCKET/  # Should list without errors
   ```

3. **Check file paths**:
   ```bash
   ls -la data/AllProvidedFiles_438/  # Should show PDF files
   ```

### Manifest Not Found

If the manifest doesn't exist, the indexer will create it. If you get an error:
```bash
# Manually create an empty manifest
echo '{"version": "v20250101", "corpora": {}}' | \
  aws s3 cp - s3://$RAG_BUCKET/rag/manifest.json
```

### API Shows "Retriever not initialized"

This means:
1. The Lambda hasn't loaded the indices yet (wait for cold start)
2. The manifest path is incorrect
3. The indices don't exist in S3

**Check Lambda logs**:
```bash
aws logs tail /aws/lambda/cotrial-rag-v2-RAGApiFunction-UYQJEBFlzhdd --follow
```

Look for:
- `application_started` - successful startup
- `manifest_loaded` - manifest found and parsed
- `corpus_loaded` - corpus indices loaded

### Token Limit Errors

If you see `Requested X tokens, max 300000 tokens per request`:
- The embedding batching should handle this automatically
- If it persists, reduce `--max-tokens` (default: 512)

## Cost Estimation

**Index Building** (one-time):
- OpenAI embeddings: ~$0.02 per 1M tokens
- For 10,000 documents with 512 tokens each: ~$0.10

**S3 Storage**:
- FAISS index: ~10-50MB per corpus
- JSONL files: ~5-20MB per corpus
- Total: ~$0.01-0.02/month

**Lambda Runtime** (per query):
- Downloads indices from S3: ~1-2 seconds
- Vector search: ~100-500ms
- Embedding query: ~200-500ms
- Total: ~$0.00001 per query

## Next Steps

After building indices:
1. Test your API with various queries
2. Monitor Lambda logs for errors
3. Consider setting up CloudWatch alarms
4. Update indices when your data changes (just rebuild and upload)

