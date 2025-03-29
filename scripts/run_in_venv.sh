#!/bin/bash

# Exit on error
set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Virtual environment not found. Setting up..."
    "$SCRIPT_DIR/setup_venv.sh"
fi

# Activate virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Run the command
exec "$@" 