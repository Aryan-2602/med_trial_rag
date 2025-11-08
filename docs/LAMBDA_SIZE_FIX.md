# Fixing Lambda Package Size Issue

## Problem
Lambda deployment failed with:
```
Unzipped size must be smaller than 262144000 bytes (250 MB)
```

The package includes FAISS, NumPy, Pandas which are very large.

## Solution Options

### Option 1: Use Lambda Layers (Recommended)

Separate large dependencies into a Lambda Layer:

1. **Build the layer:**
   ```bash
   chmod +x scripts/build-layer.sh
   ./scripts/build-layer.sh
   ```

2. **Use the layer template:**
   ```bash
   # Copy template with layers support
   cp template-layers.yaml template.yaml
   
   # Build and deploy
   sam build --use-container
   sam deploy
   ```

### Option 2: Use Container Images (Alternative)

If Layers don't work, use Docker container images:

1. **Update template.yaml** to use container images
2. **Build and push to ECR**
3. **Deploy**

### Option 3: Reduce Dependencies

Remove unnecessary dependencies from Lambda:
- Remove pandas (only needed for indexing, not runtime)
- Remove pypdf (only needed for indexing)
- Remove pyreadstat (only needed for indexing)

## Quick Fix: Use Minimal Dependencies

For Lambda runtime, you only need:
- FastAPI, uvicorn, mangum (API)
- boto3 (S3)
- structlog (logging)
- FAISS, NumPy (search)

Everything else (pandas, pypdf, pyreadstat) is only for indexing.

## Steps to Fix

1. **Clean up failed stack:**
   ```bash
   aws cloudformation delete-stack --stack-name cotrial-rag-v2
   aws cloudformation wait stack-delete-complete --stack-name cotrial-rag-v2
   ```

2. **Build layer:**
   ```bash
   ./scripts/build-layer.sh
   ```

3. **Update template:**
   ```bash
   cp template-layers.yaml template.yaml
   ```

4. **Rebuild and deploy:**
   ```bash
   sam build --use-container
   sam deploy
   ```
