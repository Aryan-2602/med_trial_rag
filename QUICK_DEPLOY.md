# Quick Deployment Checklist

## Prerequisites
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS SAM CLI installed (`brew install aws-sam-cli`)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] OpenAI API key ready

## Step 1: Create S3 Bucket
```bash
export RAG_BUCKET="your-unique-bucket-name"
aws s3 mb s3://$RAG_BUCKET
```

## Step 2: Build Indices
```bash
export OPENAI_API_KEY="sk-your-key"

# PDF index
python -m src.indexers.build_pdf_index \
  --input-dir data/AllProvidedFiles_438 \
  --bucket $RAG_BUCKET \
  --prefix rag/pdf_index

# SAS index  
python -m src.indexers.build_sas_index \
  --input-dir data/AllProvidedFiles_438/h3e_us_s130_control_data \
  --bucket $RAG_BUCKET \
  --prefix rag/sas_index
```

## Step 3: Deploy Lambda
```bash
sam build
sam deploy --guided
# Enter: bucket name, OpenAI API key, region
```

## Step 4: Test
```bash
# Get API URL
export API_URL=$(aws cloudformation describe-stacks \
  --stack-name cotrial-rag-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RAGApi`].OutputValue' \
  --output text)

curl $API_URL/health
curl $API_URL/v1/status | jq .
```

## Cleanup
```bash
sam delete --stack-name cotrial-rag-v2
aws s3 rb s3://$RAG_BUCKET --force
```
