#!/bin/bash
# Build Lambda Layer for large dependencies

set -e

LAYER_DIR="layer/python/lib/python3.11/site-packages"
rm -rf layer
mkdir -p "$LAYER_DIR"

echo "Installing dependencies to layer..."
echo "Note: This builds for ARM64 Lambda (matching your Mac architecture)."

# Use available FAISS version (1.9.0 is latest available for manylinux2014)
pip install \
    faiss-cpu==1.9.0.post1 \
    numpy==1.26.0 \
    -t "$LAYER_DIR" \
    --platform manylinux2014_aarch64 \
    --only-binary :all: \
    --no-compile \
    --python-version 3.11 \
    --upgrade

echo "Removing unnecessary files to reduce size..."
find "$LAYER_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type f -name "*.pyc" -delete
find "$LAYER_DIR" -type f -name "*.pyo" -delete
find "$LAYER_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

echo "Layer built successfully!"
du -sh layer


