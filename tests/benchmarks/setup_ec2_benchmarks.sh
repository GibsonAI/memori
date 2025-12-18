#!/bin/bash
# Setup script for running benchmarks on AWS EC2

set -e

echo "Setting up Memori benchmarks on EC2..."

# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    git \
    curl \
    build-essential \
    postgresql-client \
    default-mysql-client

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Clone repository (replace with your repo URL if not already cloned)
# git clone https://github.com/MemoriLabs/Memori.git
# cd Memori

# Sync dependencies
uv sync --all-extras

# Source the runner to get run_benchmarks function
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/run_benchmarks_ec2.sh"

echo "Setup complete!"
echo ""
echo "To run all benchmarks for Postgres:"
echo "  DB_TYPE=postgres TEST_TYPE=all ./tests/benchmarks/run_benchmarks_ec2.sh"
echo ""
echo "To run end-to-end benchmarks for MySQL:"
echo "  DB_TYPE=mysql TEST_TYPE=end_to_end ./tests/benchmarks/run_benchmarks_ec2.sh"
echo ""
echo "Results will be automatically saved to the ./results directory as CSV."
