# Deployment Steps - Quick Reference

## Prerequisites
- ✅ S3 bucket created and indices uploaded
- ✅ AWS credentials configured (`aws configure`)
- ✅ Docker running (for build)

## Step 1: Build with Docker

```bash
sam build --use-container
```

**Expected output:** Should complete without errors. If it fails, see `docs/BUILD_TROUBLESHOOTING.md`

## Step 2: Deploy

```bash
sam deploy --guided
```

**When prompted, enter:**

1. **Stack Name**: `cotrial-rag-v2`
2. **AWS Region**: `us-east-2` (or your preferred region)
3. **Parameter RAGBucket**: `cotrial-ragv2` (your bucket name)
4. **Parameter RAGManifestKey**: `rag/manifest.json` (press Enter for default)
5. **Parameter EmbedModel**: `text-embedding-3-small` (press Enter for default)
6. **Parameter OpenAIApiKey**: `sk-your-actual-key-here` ⚠️ **Paste your OpenAI API key here**
7. **Confirm changes**: `Y`
8. **Allow SAM CLI IAM role creation**: `Y`
9. **Disable rollback**: `N` (press Enter for default)
10. **Save arguments to configuration file**: `Y`

## Step 3: Verify Deployment

```bash
# Get API endpoint
export API_URL=$(aws cloudformation describe-stacks \
  --stack-name cotrial-rag-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RAGApi`].OutputValue' \
  --output text)

# Test health endpoint
curl $API_URL/health

# Test status endpoint
curl $API_URL/v1/status | jq .

# Test chat endpoint
curl -X POST $API_URL/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}' | jq .
```

## Troubleshooting

### Build fails
- Check Docker is running: `docker ps`
- Try: `sam build --use-container --debug`

### Deployment fails
- Check AWS credentials: `aws sts get-caller-identity`
- Check S3 bucket exists: `aws s3 ls s3://cotrial-ragv2`
- Check CloudFormation logs in AWS Console

### API returns 503
- Check Lambda logs: `sam logs -n RAGApiFunction --stack-name cotrial-rag-v2 --tail`
- Verify manifest exists: `aws s3 ls s3://cotrial-ragv2/rag/manifest.json`

## Redeploy After Changes

```bash
sam build --use-container
sam deploy  # Uses saved config from samconfig.toml
```


