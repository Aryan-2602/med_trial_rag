# Operations Runbook

## Overview

This runbook provides operational procedures for managing the CoTrial RAG v2 system, including deployment, index updates, troubleshooting, and monitoring.

## Table of Contents

1. [Deployment](#deployment)
2. [Index Management](#index-management)
3. [Rolling Out New Index Versions](#rolling-out-new-index-versions)
4. [Rollback Procedures](#rollback-procedures)
5. [Common Errors & Fixes](#common-errors--fixes)
6. [Monitoring & Observability](#monitoring--observability)
7. [Performance Tuning](#performance-tuning)

## Deployment

### Initial Deployment

1. **Prerequisites**:
   - AWS account with CLI configured
   - S3 bucket created (private, SSE enabled)
   - OpenAI API key
   - AWS SAM CLI installed

2. **Build SAM application**:
   ```bash
   sam build
   ```

3. **Deploy**:
   ```bash
   sam deploy --guided
   ```
   Provide:
   - Stack name: `cotrial-rag-v2`
   - Region: `us-east-1` (or preferred)
   - RAGBucket: Your S3 bucket name
   - RAGManifestKey: `rag/manifest.json`
   - EmbedModel: `text-embedding-3-small`
   - OpenAIApiKey: Your OpenAI API key

4. **Verify deployment**:
   ```bash
   # Get API endpoint from stack outputs
   aws cloudformation describe-stacks \
     --stack-name cotrial-rag-v2 \
     --query 'Stacks[0].Outputs'

   # Test health endpoint
   curl https://<api-id>.execute-api.<region>.amazonaws.com/Prod/health
   ```

### Updating Deployment

1. **Update code**:
   ```bash
   git pull
   sam build
   ```

2. **Deploy changes**:
   ```bash
   sam deploy
   ```

3. **Verify**:
   - Check CloudWatch logs for startup errors
   - Test `/v1/status` endpoint

## Index Management

### Building PDF Index

1. **Prepare environment**:
   ```bash
   export RAG_BUCKET=your-bucket-name
   export OPENAI_API_KEY=sk-your-key
   ```

2. **Run indexer**:
   ```bash
   python -m src.indexers.build_pdf_index \
     --input-dir /path/to/pdfs \
     --bucket $RAG_BUCKET \
     --prefix rag/pdf_index \
     --manifest-key rag/manifest.json \
     --model text-embedding-3-small
   ```

3. **Verify upload**:
   ```bash
   aws s3 ls s3://$RAG_BUCKET/rag/pdf_index/ --recursive
   ```

### Building SAS Index

1. **Run indexer**:
   ```bash
   python -m src.indexers.build_sas_index \
     --input-dir /path/to/sas/files \
     --bucket $RAG_BUCKET \
     --prefix rag/sas_index \
     --manifest-key rag/manifest.json \
     --model text-embedding-3-small
   ```

2. **Verify upload**:
   ```bash
   aws s3 ls s3://$RAG_BUCKET/rag/sas_index/ --recursive
   ```

### Verifying Manifest

```bash
aws s3 cp s3://$RAG_BUCKET/rag/manifest.json - | jq .
```

Should show:
- Valid JSON
- Both `pdf` and `sas` corpora
- Correct file paths
- Dimension and count match expectations

## Rolling Out New Index Versions

### Procedure

1. **Build new index** (see [Index Management](#index-management))

2. **Verify new version uploaded**:
   ```bash
   # Check S3 for new version directory
   aws s3 ls s3://$RAG_BUCKET/rag/pdf_index/
   # Should see: v20250101/, v20250102/, etc.
   ```

3. **Verify manifest updated**:
   ```bash
   aws s3 cp s3://$RAG_BUCKET/rag/manifest.json - | jq '.version'
   ```

4. **Test in Lambda**:
   - Trigger a test query to Lambda
   - Check CloudWatch logs for index load
   - Verify `/v1/status` shows new version

5. **Monitor**:
   - Check error rates
   - Monitor query latency
   - Verify results quality

### Version Naming Convention

- Format: `vYYYYMMDD` (e.g., `v20250101`)
- Generated automatically by indexers
- Stored in manifest `version` field

### Automated Rollout (Future)

Consider implementing:
- Blue-green deployment (two manifest versions)
- Canary releases (gradual traffic shift)
- Automated testing before rollout

## Rollback Procedures

### Quick Rollback

1. **Download current manifest**:
   ```bash
   aws s3 cp s3://$RAG_BUCKET/rag/manifest.json manifest-backup.json
   ```

2. **Edit manifest** (point to previous version):
   ```bash
   # Edit manifest-backup.json
   # Change version: "v20250101" → "v20241231"
   # Update corpus prefixes to previous version
   ```

3. **Upload rollback manifest**:
   ```bash
   aws s3 cp manifest-backup.json s3://$RAG_BUCKET/rag/manifest.json
   ```

4. **Verify rollback**:
   - Check `/v1/status` endpoint
   - Verify version in response
   - Test queries

### Full Rollback (Re-upload Previous Index)

If previous index files were deleted:

1. **Locate backup** (if exists):
   ```bash
   aws s3 ls s3://$RAG_BUCKET/rag/pdf_index/ --recursive
   ```

2. **Re-upload previous index** (if available):
   ```bash
   # From local backup or previous S3 version
   aws s3 cp --recursive \
     ./backup/pdf_index/v20241231/ \
     s3://$RAG_BUCKET/rag/pdf_index/v20241231/
   ```

3. **Update manifest** (as above)

## Common Errors & Fixes

### 503 Service Unavailable: "Indices not loaded"

**Symptoms**:
- `/v1/status` returns `"loaded": false`
- `/v1/chat` returns 503

**Causes & Fixes**:

1. **Missing manifest**:
   ```bash
   # Check manifest exists
   aws s3 ls s3://$RAG_BUCKET/rag/manifest.json
   # If missing, create/upload manifest
   ```

2. **S3 permissions**:
   ```bash
   # Verify Lambda role has s3:GetObject permission
   aws iam get-role-policy \
     --role-name <lambda-role> \
     --policy-name <policy-name>
   ```

3. **Invalid manifest JSON**:
   ```bash
   # Validate JSON
   aws s3 cp s3://$RAG_BUCKET/rag/manifest.json - | jq .
   ```

4. **Missing index files**:
   ```bash
   # Check files exist
   aws s3 ls s3://$RAG_BUCKET/rag/pdf_index/v20250101/
   # Should see: index.faiss, ids.jsonl, docs.jsonl
   ```

### Dimension Mismatch

**Symptoms**:
- Error: "Dimension mismatch: index has X, manifest says Y"
- Lambda logs show dimension error

**Fixes**:

1. **Rebuild index with correct model**:
   ```bash
   # Use same model as index was built with
   python -m src.indexers.build_pdf_index \
     --model text-embedding-3-small  # or whatever model was used
   ```

2. **Update manifest dimension**:
   ```bash
   # Edit manifest.json
   # Set dimension to match index (1536 for text-embedding-3-small)
   ```

### S3 Permissions

**Symptoms**:
- 403 Forbidden errors in CloudWatch logs
- "Access Denied" errors

**Fixes**:

1. **Check Lambda IAM role**:
   ```bash
   # Get role name
   aws lambda get-function-configuration \
     --function-name <function-name> \
     --query 'Role'

   # Check policies
   aws iam list-attached-role-policies --role-name <role-name>
   ```

2. **Add S3 read policy**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": [
         "s3:GetObject",
         "s3:ListBucket"
       ],
       "Resource": [
         "arn:aws:s3:::your-bucket-name/*",
         "arn:aws:s3:::your-bucket-name"
       ]
     }]
   }
   ```

### Cold Start Timeout

**Symptoms**:
- Lambda timeout during startup
- CloudWatch logs show timeout

**Fixes**:

1. **Increase timeout**:
   ```yaml
   # In template.yaml
   Timeout: 60  # Increase from 30
   ```

2. **Reduce index size**:
   - Use smaller embedding dimensions
   - Reduce corpus size
   - Shard indices

3. **Use provisioned concurrency**:
   ```bash
   aws lambda put-provisioned-concurrency-config \
     --function-name <function-name> \
     --qualifier $LATEST \
     --provisioned-concurrent-executions 1
   ```

### Embedding API Errors

**Symptoms**:
- "OPENAI_API_KEY required" errors
- Embedding API timeouts

**Fixes**:

1. **Check API key**:
   ```bash
   # Verify in Lambda environment
   aws lambda get-function-configuration \
     --function-name <function-name> \
     --query 'Environment.Variables.OPENAI_API_KEY'
   ```

2. **Use Secrets Manager** (recommended):
   ```python
   # In Lambda code
   import boto3
   import json
   
   secrets_client = boto3.client('secretsmanager')
   secret = secrets_client.get_secret_value(SecretId='openai-api-key')
   os.environ['OPENAI_API_KEY'] = json.loads(secret['SecretString'])['api_key']
   ```

3. **Check rate limits**:
   - Monitor OpenAI API usage
   - Consider caching embeddings

## Monitoring & Observability

### CloudWatch Logs

**Log Group**: `/aws/lambda/<function-name>`

**Key Log Fields**:
- `request_id`: Request identifier
- `duration_ms`: Operation timing
- `corpus`: Corpus name (pdf/sas)
- `count`: Document counts
- `error`: Error messages

**Useful Queries**:
```bash
# Recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern "error" \
  --start-time $(date -d '1 hour ago' +%s)000

# Cold starts
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern "starting_application"
```

### Status Endpoint Monitoring

**Endpoint**: `GET /v1/status`

**Monitor**:
- `loaded`: Should be `true`
- `manifest_version`: Track version changes
- `corpora`: Document counts per corpus

**Alert if**:
- `loaded: false`
- Version mismatch (if expected)
- Corpus counts drop unexpectedly

### CloudWatch Metrics

**Key Metrics**:
- Invocations (request rate)
- Duration (p50, p95, p99)
- Errors (4xx, 5xx)
- Throttles

**Alarms**:
```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name rag-high-error-rate \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

## Performance Tuning

### Lambda Configuration

**Memory**: 2048 MB (adjust based on index size)
- Larger memory = more CPU = faster execution
- Monitor actual memory usage

**Timeout**: 30s (adjust based on cold start)
- Cold start: 3-5s typical
- Warm query: < 1s typical

### Index Optimization

1. **Reduce index size**:
   - Use smaller embedding dimensions
   - Reduce chunk size
   - Filter documents before indexing

2. **Use approximate search**:
   - Switch to `IndexIVFFlat` for large corpora
   - Trade-off: accuracy vs speed

3. **Cache indices**:
   - Use `/tmp` (persists across invocations)
   - Consider Lambda Layers for FAISS

### Query Optimization

1. **Reduce top_k**:
   - Lower `TOP_K` = faster search
   - Balance between speed and recall

2. **Batch queries** (future):
   - Process multiple queries in one invocation
   - Share embedding computation

## Backup & Recovery

### Backup Strategy

1. **Index files**:
   - S3 versioning enabled (recommended)
   - Or manual backups to different bucket

2. **Manifest**:
   - Keep version history
   - Backup before updates

### Recovery Procedures

1. **Index corruption**:
   - Rebuild from source files
   - Or restore from S3 version

2. **Manifest corruption**:
   - Restore from backup
   - Or recreate from index metadata

## Maintenance Windows

### Recommended Schedule

- **Index updates**: Weekly/monthly (as new data arrives)
- **Lambda updates**: As needed (code changes)
- **Monitoring review**: Daily (check logs, metrics)

### Pre-Maintenance Checklist

- [ ] Backup current manifest
- [ ] Verify S3 bucket versioning
- [ ] Test rollback procedure
- [ ] Notify stakeholders

## Emergency Contacts

- **On-call engineer**: [Contact info]
- **AWS Support**: [Support plan details]
- **OpenAI Support**: [API support]

## Appendix

### Useful Commands

```bash
# Check Lambda status
aws lambda get-function --function-name <name>

# View recent logs
aws logs tail /aws/lambda/<function-name> --follow

# Test API endpoint
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/Prod/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Check S3 bucket size
aws s3 ls s3://$RAG_BUCKET/rag/ --recursive --summarize
```

