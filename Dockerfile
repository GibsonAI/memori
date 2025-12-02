# Use Python 3.12 as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies (including dev dependencies)
RUN uv sync --all-extras

# Copy the rest of the application
COPY . .

# Install pre-commit hooks
RUN pip install pre-commit && pre-commit install || true

# Add venv to PATH so all tools are available
ENV PATH="/app/.venv/bin:$PATH"

# Default command opens a bash shell
CMD ["/bin/bash"]
