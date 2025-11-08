# Deployment Guide

Complete guide for deploying CoTrial RAG v2 to AWS S3 and Lambda.

## Prerequisites

### 1. Install AWS CLI and SAM CLI

**AWS CLI:**
```bash
# macOS
brew install awscli

# Or use pip
pip install awscli
```

**AWS SAM CLI:**
```bash
# macOS
brew install aws-sam-cli

# Or use pip
pip install aws-sam-cli
```

### 2. Configure AWS Credentials

```bash
aws configure
```

You'll need:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (e.g., `json`)

### 3. Create S3 Bucket

```bash
# Set your bucket name (must be globally unique)
export RAG_BUCKET="your-rag-bucket-name-$(date +%s)"

# Create bucket
aws s3 mb s3://$RAG_BUCKET

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket $RAG_BUCKET \
  --versioning-configuration Status=Enabled

# Enable server-side encryption
aws s3api put-bucket-encryption \
  --bucket $RAG_BUCKET \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

## Step 1: Build and Upload Indices to S3

### Build PDF Index

```bash
# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export RAG_BUCKET="your-bucket-name"
export OPENAI_API_KEY="sk-your-key-here"

# Build PDF index
python -m src.indexers.build_pdf_index \
  --input-dir data/AllProvidedFiles_438 \
  --bucket $RAG_BUCKET \
  --prefix rag/pdf_index \
  --manifest-key rag/manifest.json \
  --model text-embedding-3-small
```

This will:
1. Extract text from PDFs
2. Chunk and embed the text
3. Build FAISS index
4. Upload to S3: `s3://$RAG_BUCKET/rag/pdf_index/vYYYYMMDD/`
5. Update manifest at `s3://$RAG_BUCKET/rag/manifest.json`

### Build SAS Index

```bash
python -m src.indexers.build_sas_index \
  --input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
  --bucket $RAG_BUCKET \
  --prefix rag/sas_index \
  --manifest-key rag/manifest.json \
  --model text-embedding-3-small
```

### Verify Indices

```bash
# List uploaded files
aws s3 ls s3://$RAG_BUCKET/rag/ --recursive

# Check manifest
aws s3 cp s3://$RAG_BUCKET/rag/manifest.json - | jq .
```

Expected structure:
```
s3://your-bucket/
  rag/
    manifest.json
    pdf_index/
      v20250101/
        index.faiss
        ids.jsonl
        docs.jsonl
    sas_index/
      v20250101/
        index.faiss
        ids.jsonl
        docs.jsonl
```

## Step 2: Build and Deploy Lambda Function

### Build SAM Application

```bash
# Make sure you're in the project root
cd /Users/aryanmaheshwari/cotrial-ragv2

# Build the application
sam build
```

This creates a build directory (`.aws-sam/`) with packaged code.

### Deploy (Guided Mode)

```bash
sam deploy --guided
```

You'll be prompted for:
- **Stack Name**: `cotrial-rag-v2` (or your preferred name)
- **AWS Region**: `us-east-1` (or your preferred region)
- **RAGBucket**: Your S3 bucket name (e.g., `your-rag-bucket-name`)
- **RAGManifestKey**: `rag/manifest.json` (default)
- **EmbedModel**: `text-embedding-3-small` (default)
- **OpenAIApiKey**: Your OpenAI API key
- **Confirm changes**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Disable rollback**: `N` (default)
- **Save arguments to configuration file**: `Y` (saves to `samconfig.toml`)

### Deploy (Using Config File)

After the first guided deployment, you can redeploy with:

```bash
sam deploy
```

This uses the saved `samconfig.toml` file.

### Verify Deployment

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name cotrial-rag-v2 \
  --query 'Stacks[0].Outputs'

# Or use SAM
sam list stack-outputs --stack-name cotrial-rag-v2
```

You should see:
- **RAGApi**: API Gateway endpoint URL
- **RAGApiFunction**: Lambda function ARN

## Step 3: Test the Deployment

### Test Health Endpoint

```bash
# Get API endpoint from stack outputs
export API_URL=$(aws cloudformation describe-stacks \
  --stack-name cotrial-rag-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RAGApi`].OutputValue' \
  --output text)

# Test health
curl $API_URL/health

# Test status
curl $API_URL/v1/status | jq .
```

### Test Chat Endpoint

```bash
curl -X POST $API_URL/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the inclusion criteria?",
    "top_k": 5
  }' | jq .
```

## Step 4: Monitor and Troubleshoot

### View Lambda Logs

```bash
# Get function name
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name cotrial-rag-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RAGApiFunction`].OutputValue' \
  --output text | awk -F: '{print $NF}')

# View recent logs
sam logs -n $FUNCTION_NAME --stack-name cotrial-rag-v2 --tail

# Or use AWS CLI
aws logs tail /aws/lambda/$FUNCTION_NAME --follow
```

### Check Lambda Metrics

```bash
# View function configuration
aws lambda get-function-configuration --function-name $FUNCTION_NAME

# Check recent invocations
aws lambda get-function --function-name $FUNCTION_NAME
```

## Step 5: Update Deployment

### Update Code

```bash
# Make your code changes
# ...

# Rebuild
sam build

# Redeploy
sam deploy
```

### Update Indices

1. Build new indices (see Step 1)
2. The Lambda will automatically use the new version from the manifest
3. No code deployment needed!

### Update Environment Variables

```bash
# Edit template.yaml or use AWS Console
# Then redeploy
sam build && sam deploy
```

## Security Best Practices

### 1. Use Secrets Manager for OpenAI API Key

Instead of passing the API key as a parameter, use AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name openai-api-key \
  --secret-string '{"api_key": "sk-your-key-here"}'

# Update Lambda code to retrieve from Secrets Manager
# (see src/utils/config.py for example)
```

### 2. Restrict S3 Bucket Access

```bash
# Create bucket policy
cat > bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/cotrial-rag-v2-RAGApiFunctionRole-*"
    },
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::your-bucket-name/*",
      "arn:aws:s3:::your-bucket-name"
    ]
  }]
}
EOF

# Apply policy
aws s3api put-bucket-policy \
  --bucket your-bucket-name \
  --policy file://bucket-policy.json
```

### 3. Enable API Gateway Authentication

Consider adding:
- API Keys
- AWS Cognito
- Lambda authorizer

## Cleanup

### Delete Stack

```bash
sam delete --stack-name cotrial-rag-v2
```

### Delete S3 Bucket

```bash
# Delete all objects first
aws s3 rm s3://$RAG_BUCKET --recursive

# Delete bucket
aws s3 rb s3://$RAG_BUCKET
```

## Troubleshooting

### Common Issues

1. **Build fails**: Ensure all dependencies are in `requirements.txt`
2. **Deployment fails**: Check IAM permissions, region availability
3. **Lambda timeout**: Increase timeout in `template.yaml` (MemorySize/Timeout)
4. **Cold start slow**: Use provisioned concurrency or Lambda Layers
5. **S3 access denied**: Check Lambda IAM role has S3 read permissions

### Debug Commands

```bash
# Test Lambda locally
sam local invoke RAGApiFunction --event events/event.json

# Start local API
sam local start-api

# Validate template
sam validate
```

## Cost Estimation

- **Lambda**: ~$0.0000166667 per GB-second (first 400K GB-seconds free)
- **API Gateway**: $3.50 per million requests
- **S3 Storage**: ~$0.023 per GB/month
- **S3 Requests**: $0.0004 per 1,000 GET requests
- **OpenAI Embeddings**: Depends on model and usage

For a small deployment (100K requests/month):
- Lambda: ~$5-10/month
- API Gateway: ~$0.35/month
- S3: ~$1-2/month
- OpenAI: Depends on usage

## Next Steps

- Set up CloudWatch alarms for errors
- Configure API Gateway throttling
- Set up CI/CD pipeline
- Monitor costs with AWS Cost Explorer
- Consider using AWS Lambda Layers for FAISS

