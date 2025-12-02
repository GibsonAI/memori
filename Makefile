.PHONY: help dev-up dev-down dev-shell dev-build dev-clean test lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-up: ## Start development environment (builds and runs containers)
	docker compose up -d --build
	@echo ""
	@echo "✓ Development environment is ready!"
	@echo "  Run 'make dev-shell' to enter the development container"
	@echo "  Run 'make test' to run tests"

dev-down: ## Stop development environment
	docker compose down

dev-shell: ## Open a shell in the development container
	docker compose exec dev /bin/bash

init-db: ## Initialize database schema for integration tests
	docker compose exec -e PYTHONPATH=/app dev python tests/database/init_db.py

init-postgres: ## Initialize PostgreSQL schema
	docker compose exec -e PYTHONPATH=/app dev python tests/build/postgresql.py

init-mysql: ## Initialize MySQL schema
	docker compose exec -e PYTHONPATH=/app dev python tests/build/mysql.py

init-oracle: ## Initialize Oracle schema
	docker compose exec -e PYTHONPATH=/app dev python tests/build/oracle.py

init-mongodb: ## Initialize MongoDB schema
	docker compose exec -e PYTHONPATH=/app dev python tests/build/mongodb.py

init-sqlite: ## Initialize SQLite schema
	docker compose exec -e PYTHONPATH=/app dev python tests/build/sqlite.py

dev-build: ## Rebuild the development container
	docker compose build --no-cache

dev-clean: ## Complete teardown: stop containers, remove images, prune build cache
	docker compose down -v
	docker builder prune -f
	docker compose rm -f
	@echo "✓ Docker environment cleaned (containers, volumes, and build cache removed)"

test: ## Run tests in the container
	docker compose exec dev pytest

run-integration: ## Run integration test scripts directly (e.g., make run-integration FILE=tests/llm/clients/oss/openai/async.py ARGS="--db mysql")
	@echo "Running integration test: $(FILE) $(ARGS)"
	docker compose exec -e PYTHONPATH=/app dev python $(FILE) $(ARGS)

run-integration-enterprise: ## Run integration test in enterprise mode (e.g., make run-integration-enterprise FILE=tests/llm/clients/oss/openai/sync.py)
	@echo "Running integration test in ENTERPRISE mode: $(FILE) $(ARGS)"
	docker compose exec -e PYTHONPATH=/app -e MEMORI_ENTERPRISE=1 dev python $(FILE) $(ARGS)

lint: ## Run linting (format check)
	docker compose exec dev uv run ruff check .

security: ## Run security scans (Bandit + pip-audit)
	docker compose exec dev uv run bandit -r memori -ll -ii
	docker compose exec dev uv run pip-audit --require-hashes --disable-pip || true

format: ## Format code
	docker compose exec dev uv run ruff format .

clean: ## Clean up containers, volumes, and Python cache files
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
