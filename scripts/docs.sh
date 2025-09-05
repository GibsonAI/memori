#!/bin/bash
# Quick MkDocs helper script for Unix systems (macOS, Linux)

echo "🚀 Memori SDK - Documentation Helper"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3 from https://python.org/"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Python script with all arguments
python3 "$SCRIPT_DIR/docs_dev.py" "$@"