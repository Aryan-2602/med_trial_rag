# NAT Gateway Cost Information

## What Was Added

To enable Lambda in VPC to access the internet (for OpenAI API calls), we added:

1. **NAT Gateway** - Routes outbound internet traffic from Lambda
2. **Elastic IP** - Required for NAT Gateway
3. **Public Subnet** - Where NAT Gateway lives
4. **Private Route Table** - Routes Lambda traffic through NAT Gateway

## Cost Breakdown

### Monthly Costs (us-east-2)

- **NAT Gateway**: $0.045/hour = **~$32.40/month**
- **Elastic IP** (when attached to NAT): **Free**
- **Data Transfer**: 
  - First 1 GB/month: Free
  - Additional: $0.045/GB
  - OpenAI API calls: ~$0.01-0.05/month (minimal)

**Total: ~$32-33/month** (mostly the NAT Gateway)

### Cost Optimization Options

1. **Use Provisioned Concurrency** (recommended)
   - Keeps Lambda warm, reduces initialization time
   - Cost: ~$11/month
   - Makes requests fast, but still need NAT Gateway

2. **Use AWS PrivateLink** (not available)
   - OpenAI doesn't support PrivateLink endpoints
   - Would eliminate need for NAT Gateway

3. **Remove VPC** (not recommended)
   - Would eliminate NAT Gateway cost
   - But can't use EFS (needed for large indices)
   - Would hit Lambda `/tmp` 512MB limit again

## Current Architecture Trade-offs

✅ **What We Have:**
- EFS for large indices (no size limits)
- NAT Gateway for internet access (OpenAI API)
- Persistent indices (survive cold starts)
- Full functionality

❌ **Costs:**
- NAT Gateway: ~$32/month
- EFS: ~$0.30/GB/month (minimal)
- Lambda: Pay per request (free tier covers it)

## Recommendations

1. **For Production**: Keep NAT Gateway + add Provisioned Concurrency
   - Total: ~$43/month for infrastructure
   - Fast, reliable, no timeouts

2. **For Development/Testing**: 
   - Keep NAT Gateway (can't avoid it with VPC)
   - Skip Provisioned Concurrency (save $11/month)
   - Accept that first request may timeout
   - Subsequent requests work fine

3. **Cost Reduction**: 
   - If indices are updated infrequently, consider:
     - Deploying only when needed
     - Using scheduled Lambda to keep warm
     - Using Step Functions for async processing

## Next Steps

The system is working correctly! The timeout is just due to API Gateway's 29-second limit. To fix:

```bash
# Enable provisioned concurrency (recommended)
aws lambda put-provisioned-concurrency-config \
  --function-name cotrial-rag-v2-RAGApiFunction-oN8Ee4rrkozJ \
  --qualifier \$LATEST \
  --provisioned-concurrent-executions 1
```

Or accept that first request may timeout, but subsequent requests work fine.

