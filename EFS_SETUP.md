# EFS Setup for Large Indices

## Problem
The SAS index is ~556MB, which exceeds Lambda's `/tmp` space limit (512MB). This caused `OSError: [Errno 28] No space left on device`.

## Solution
We've implemented **AWS EFS (Elastic File System)** to provide persistent, scalable storage for large indices.

## What Changed

### 1. Template (`template.yaml`)
- Added EFS file system with encryption
- Created EFS Access Point for Lambda
- Added VPC with subnet for Lambda
- Added Security Groups for EFS and Lambda
- Added VPC Endpoint for S3 (no NAT Gateway needed - saves cost!)
- Configured Lambda to mount EFS at `/mnt/efs`

### 2. Code (`src/retrieval/faiss_s3.py`)
- Updated `_load_corpus()` to use `RAG_STORAGE_PATH` environment variable
- Defaults to `/tmp` if EFS not available (for local dev)
- Uses `/mnt/efs` in Lambda (configured via environment variable)

## How It Works

1. **Lambda starts** → EFS is automatically mounted at `/mnt/efs`
2. **Retriever initializes** → Downloads indices from S3 to `/mnt/efs/rag/`
3. **Indices persist** → Survive Lambda cold starts (EFS is persistent)
4. **Subsequent invocations** → Use cached indices (ETag check)

## Benefits

✅ **No size limits** - EFS can store TBs  
✅ **Persistent** - Indices survive Lambda container recycling  
✅ **Fast** - No re-download on warm starts  
✅ **Cost-effective** - VPC Endpoint for S3 (no NAT Gateway needed)  
✅ **Accurate** - Full index available, no data loss  

## Deployment

Deploy as usual:
```bash
sam build
sam deploy
```

The EFS file system will be created automatically. First invocation will download indices (~30-60 seconds), subsequent invocations will be fast (cached).

## Costs

- **EFS**: ~$0.30/GB/month (with lifecycle policy: ~$0.025/GB for infrequent access)
- **VPC Endpoint**: Free for S3 Gateway endpoints
- **No NAT Gateway**: Saves ~$32/month + data transfer costs

For 1GB of indices: ~$0.30/month (or ~$0.03/month with lifecycle policy after 7 days)

## Local Development

For local development, the code falls back to `/tmp`:
```bash
# Local dev - uses /tmp
python -m src.api.server
```

## Troubleshooting

### Lambda can't access EFS
- Check Security Groups (EFS must allow Lambda SG on port 2049)
- Verify VPC configuration
- Check CloudWatch logs for mount errors

### Slow first invocation
- Normal! First time downloads ~556MB from S3
- Subsequent invocations use cached indices (fast)

### EFS mount fails
- Ensure Lambda is in the same VPC as EFS
- Check Access Point permissions
- Verify Security Group rules

## Next Steps

1. Deploy: `sam build && sam deploy`
2. Test: Check Lambda logs for successful EFS mount
3. Monitor: Watch for first-time download timing
4. Optimize: Consider adding more mount targets for HA (optional)

