#!/bin/bash

# Exit on error
set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Create virtual environment using uv
echo "Creating virtual environment using uv..."
cd "$PROJECT_ROOT"
uv venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies using uv
echo "Installing dependencies with uv..."
uv pip install -e .

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run:"
echo "source .venv/bin/activate" 