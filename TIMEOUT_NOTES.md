# API Gateway Timeout Limitations

## Issue

API Gateway REST API has a **hard limit of 29 seconds** for request timeout. This affects:

1. **First request to `/v1/status`**: Takes ~29 seconds during cold start (downloading 556MB indices from S3 to EFS)
2. **`/v1/chat` endpoint**: May timeout if OpenAI embedding call + processing takes > 29 seconds

## Current Behavior

- **Lambda timeout**: 60 seconds (configured)
- **API Gateway REST timeout**: 29 seconds (hard limit)
- **Result**: API Gateway times out before Lambda can complete

## Solutions

### 1. Wait for Warm Lambda (Recommended)

After the first request, the Lambda container is "warm" and indices are cached in EFS:

1. **First request**: ~29 seconds (downloads indices)
2. **Subsequent requests**: ~2-5 seconds (uses cached indices)

**Workaround**: Make a request to `/health` first, wait 30 seconds, then use `/v1/status` or `/v1/chat`.

### 2. Use Provisioned Concurrency

Keep Lambda warm to eliminate cold starts:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --qualifier $LATEST \
  --provisioned-concurrent-executions 1
```

**Cost**: ~$0.015/hour = ~$11/month for 1 concurrent execution

### 3. Switch to HTTP API (Future)

API Gateway HTTP API supports up to 30 seconds (still tight, but better). Would require template changes.

### 4. Implement Async Pattern

Use async processing with polling:
- Client sends request → returns job ID immediately
- Client polls for results
- More complex but avoids timeout

## Current Optimizations Applied

1. ✅ **OpenAI timeout**: 15 seconds per request (fails fast)
2. ✅ **Status endpoint**: Non-blocking initialization (returns quickly if already initialized)
3. ✅ **EFS caching**: Indices persist across invocations (subsequent calls are fast)

## Expected Behavior

### Cold Start (First Request After Deployment/Idle)
- **Time**: ~29 seconds
- **What happens**: Downloads 556MB from S3 to EFS
- **Result**: May timeout at API Gateway (29s limit)

### Warm Start (Subsequent Requests)
- **Time**: ~2-5 seconds
- **What happens**: Uses cached indices from EFS
- **Result**: Should complete successfully

## Testing

### Test Warm Lambda

```bash
# 1. First request (may timeout)
curl https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/status

# 2. Wait 30 seconds

# 3. Second request (should be fast)
curl https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/status
```

### Test Chat Endpoint

```bash
# First request (may timeout if cold start)
curl -X POST https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the inclusion criteria?"}'

# Wait 30 seconds, then try again (should work)
```

## Monitoring

Check Lambda logs to see if requests are completing:

```bash
aws logs tail /aws/lambda/cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ --follow
```

Look for:
- `retriever_initialized` - Initialization complete
- `Duration: X ms` - Request duration
- `Task timed out` - Lambda timeout (shouldn't happen with 60s timeout)
- `Endpoint request timed out` - API Gateway timeout (expected on cold start)

## Recommendations

1. **For production**: Use provisioned concurrency (1-2 instances) to keep Lambda warm
2. **For development**: Accept that first request may timeout, subsequent requests work
3. **For better UX**: Implement async pattern with job queue
4. **For cost optimization**: Use HTTP API instead of REST API (when supported)

## Cost Impact

- **Provisioned concurrency**: ~$11/month per instance
- **EFS storage**: ~$0.30/GB/month (with lifecycle: ~$0.03/GB after 7 days)
- **Lambda execution**: Pay per request (first request is slow but free tier covers it)

For a small deployment, provisioned concurrency is worth it to avoid timeouts.

