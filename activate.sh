#!/bin/bash
# Quick activation script for the virtual environment

source .venv/bin/activate
echo "Virtual environment activated!"
echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo ""
echo "To deactivate, run: deactivate"

