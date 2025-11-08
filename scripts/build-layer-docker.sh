#!/bin/bash
# Build Lambda Layer using Docker (works on ARM Mac)

set -e

LAYER_DIR="layer/python"
rm -rf layer
mkdir -p "$LAYER_DIR"

echo "Building layer using Docker for x86_64 compatibility..."

# Use Docker to build in Lambda-compatible environment
docker run --rm \
    -v "$(pwd)/layer:/var/task/layer" \
    -v "$(pwd)/requirements-lambda-layer.txt:/var/task/requirements.txt" \
    public.ecr.aws/sam/build-python3.11:latest \
    /bin/bash -c "
        pip install -r /var/task/requirements.txt -t /var/task/layer/python --no-cache-dir
        find /var/task/layer/python -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
        find /var/task/layer/python -type f -name '*.pyc' -delete
        find /var/task/layer/python -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true
        find /var/task/layer/python -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true
    "

echo "Layer built successfully!"
du -sh layer

