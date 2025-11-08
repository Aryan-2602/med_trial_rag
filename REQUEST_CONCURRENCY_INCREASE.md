# Request Lambda Concurrency Limit Increase

## Current Situation

Your AWS account has **10 concurrent executions** total, which is the default limit for new accounts.

To enable provisioned concurrency (1 execution), AWS requires at least **10 unreserved** concurrent executions remain available. This means you need a total limit of at least **11** (1 reserved + 10 unreserved minimum).

## Request Limit Increase

### Option 1: AWS Console (Easiest)

1. Go to: https://console.aws.amazon.com/support/home
2. Click **"Create case"**
3. Select:
   - **Case type**: Service limit increase
   - **Service**: Lambda
   - **Limit type**: Concurrent executions
   - **Region**: us-east-2
   - **New limit value**: 100 (recommended, allows room for growth)
4. **Use case description**: 
   ```
   Need to enable provisioned concurrency for Lambda function 
   cotrial-rag-v2-RAGApiFunction. Current limit (10) doesn't allow 
   reserving 1 execution while maintaining 10 unreserved minimum.
   ```
5. Submit the request

**Typical approval time**: 1-24 hours

### Option 2: AWS CLI

```bash
# Create support case (requires AWS Support plan)
aws support create-case \
  --service-code lambda \
  --severity-code normal \
  --category-code service-limit-increase \
  --subject "Lambda Concurrent Executions Increase Request" \
  --communication-body "Requesting increase from 10 to 100 concurrent executions to enable provisioned concurrency for RAG API Lambda function."
```

**Note**: This requires AWS Support plan (Basic/Developer/Business/Enterprise).

### Option 3: Use Service Quotas Console

1. Go to: https://console.aws.amazon.com/servicequotas/
2. Search for: "Lambda"
3. Find: "Concurrent executions"
4. Click **"Request quota increase"**
5. Enter: **100** (or desired limit)
6. Submit

## After Approval

Once your limit is increased (e.g., to 100), you can enable provisioned concurrency:

```bash
# Enable provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --qualifier live \
  --provisioned-concurrent-executions 1
```

## Alternative: No Provisioned Concurrency

If you don't want to wait for the limit increase, the system still works:

- **First request** (after 15+ min idle): May timeout (~29s) due to initialization
- **Subsequent requests**: Fast (~2-5s) - Lambda stays warm for ~15 minutes
- **Cost**: Free (no provisioned concurrency charges)

The system is functional; provisioned concurrency just eliminates cold starts.

