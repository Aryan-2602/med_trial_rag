# SAM Build Troubleshooting

## Issue: Build fails with dependency resolution errors

If you get errors like:
```
Error: PythonPipBuilder:ResolveDependencies - {faiss-cpu==1.12.0(wheel), ...}
```

This usually happens when building on ARM64 (Apple Silicon) for Lambda x86_64.

## Solutions

### Option 1: Use Docker (Recommended)

SAM will automatically use Docker if available:

```bash
# Ensure Docker is running
docker ps

# Build with Docker
sam build --use-container
```

### Option 2: Build on x86_64 machine or CI/CD

Build on a Linux x86_64 machine or use GitHub Actions/CI.

### Option 3: Use Lambda Layers

For FAISS specifically, consider using a pre-built Lambda Layer:
- AWS doesn't provide one, but you can build your own layer
- More complex setup

## Common Build Issues

### Issue: "Runtime python3.11 not found"

Make sure you have the correct Python version. Lambda supports:
- python3.9
- python3.10
- python3.11
- python3.12

### Issue: "No module named 'src'"

Make sure you're building from the project root:
```bash
cd /path/to/cotrial-ragv2
sam build
```

### Issue: Build succeeds but deployment fails

Check:
1. IAM permissions for SAM
2. S3 bucket exists and is accessible
3. CloudFormation stack limits

## Verify Build

After building, check the output:
```bash
ls -la .aws-sam/build/RAGApiFunction/
```

You should see:
- `src/` directory
- `requirements.txt` or installed packages
- Lambda handler file
