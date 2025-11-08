# Quick Fix for Lambda Size Issue

## The Problem
Your Lambda package is 130 MB zipped, which unzips to >250 MB (Lambda's limit).

## Quick Solution: Use Lambda Layers

### Step 1: Clean up failed stack
```bash
aws cloudformation delete-stack --stack-name cotrial-rag-v2
```

### Step 2: Build the dependencies layer (requires Docker)
```bash
# Make sure Docker is running
docker ps

# Build the layer (uses Docker to build for x86_64)
./scripts/build-layer.sh
```

### Step 3: Build and deploy
```bash
# Build with Docker
sam build --use-container

# Deploy (uses saved config)
sam deploy
```

## Alternative: If Docker isn't working

### Option A: Use container images instead
Update template.yaml to use `PackageType: Image` instead of zip.

### Option B: Remove unnecessary dependencies
The Lambda runtime doesn't need:
- `pandas` (only for indexing)
- `pypdf` (only for indexing)  
- `pyreadstat` (only for indexing)

These are only used when building indices, not when running the API.

## Check Current Size
```bash
# After building, check size
du -sh .aws-sam/build/RAGApiFunction/
```

Target: < 50 MB unzipped for Lambda code, rest in layer.


