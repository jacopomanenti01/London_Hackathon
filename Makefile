.PHONY: help install format lint typecheck test test-unit test-integration api db-up db-down db-migrate smoke-profile

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

format: ## Format code
	uv run ruff format src/ tests/

lint: ## Lint code
	uv run ruff check src/ tests/

typecheck: ## Run type checks
	uv run mypy src/dd_platform/

test: ## Run all fast CI tests
	uv run pytest tests/unit tests/contract -v

test-unit: ## Run unit tests
	uv run pytest tests/unit -v

test-integration: ## Run integration tests (requires SurrealDB)
	uv run pytest tests/integration -v

test-contract: ## Run contract tests
	uv run pytest tests/contract -v

api: ## Start the API server
	uv run uvicorn dd_platform.main:app --reload --host 0.0.0.0 --port 8080

db-up: ## Start SurrealDB via Docker
	docker compose up -d surrealdb

db-down: ## Stop SurrealDB
	docker compose down

db-migrate: ## Run database migrations
	uv run python -c "import asyncio; from dd_platform.persistence.surreal.client import SurrealClient; from dd_platform.persistence.surreal.migrations import run_migrations; from dd_platform.settings import get_settings; s = get_settings(); c = SurrealClient(s.surrealdb); asyncio.run(c.connect()); asyncio.run(run_migrations(c))"

smoke-profile: ## Run a smoke test profile build
	curl -X POST http://localhost:8080/api/v1/profiles/build \
		-H "Content-Type: application/json" \
		-d '{"company_url": "https://www.example.com", "force_refresh": true}'
