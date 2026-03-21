.DEFAULT_GOAL := help
SHELL := /bin/bash

# Project settings
APP_NAME    := tinaa-msp
IMAGE_TAG   := $(APP_NAME):latest
COMPOSE     := docker compose
COMPOSE_DEV := docker compose -f docker-compose.yml -f docker-compose.dev.yml

# Python interpreter — use the venv when present
PYTHON      := $(shell command -v python3 2>/dev/null || echo python)
PIP         := $(PYTHON) -m pip

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help:  ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make \033[36m<target>\033[0m\n\nTargets:\n"} \
	     /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Local setup
# ---------------------------------------------------------------------------
.PHONY: install
install:  ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install .

.PHONY: dev
dev:  ## Install dev dependencies and set up pre-commit hooks
	$(PIP) install --upgrade pip
	$(PIP) install ".[dev]"
	playwright install chromium
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — fill in real values."; fi
	pre-commit install

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
.PHONY: lint
lint:  ## Run linters (ruff check + mypy)
	ruff check tinaa/ tests/
	mypy tinaa/

.PHONY: format
format:  ## Format code with ruff
	ruff format tinaa/ tests/
	ruff check --fix tinaa/ tests/

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
.PHONY: test
test:  ## Run tests with coverage (fails below 80%)
	pytest --cov=tinaa --cov-report=term-missing --cov-fail-under=80

.PHONY: test-fast
test-fast:  ## Run tests without coverage (faster feedback loop)
	pytest -x -q

# ---------------------------------------------------------------------------
# Docker — image build
# ---------------------------------------------------------------------------
.PHONY: docker-build
docker-build:  ## Build the production Docker image
	docker build --target production -t $(IMAGE_TAG) .

.PHONY: docker-build-dev
docker-build-dev:  ## Build the development Docker image
	docker build --target development -t $(APP_NAME):dev .

# ---------------------------------------------------------------------------
# Docker Compose — production-like stack
# ---------------------------------------------------------------------------
.PHONY: docker-up
docker-up:  ## Start all services (production config)
	$(COMPOSE) up -d

.PHONY: docker-down
docker-down:  ## Stop all services and remove containers
	$(COMPOSE) down

.PHONY: docker-logs
docker-logs:  ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: docker-ps
docker-ps:  ## Show running service status
	$(COMPOSE) ps

# ---------------------------------------------------------------------------
# Docker Compose — development stack (hot reload)
# ---------------------------------------------------------------------------
.PHONY: docker-dev
docker-dev:  ## Start development environment with hot reload
	$(COMPOSE_DEV) up

.PHONY: docker-dev-down
docker-dev-down:  ## Stop development environment
	$(COMPOSE_DEV) down

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
.PHONY: migrate
migrate:  ## Run database migrations (upgrade to head)
	$(PYTHON) -m alembic upgrade head

.PHONY: migrate-new
migrate-new:  ## Create a new migration (use: make migrate-new MSG="describe change")
	$(PYTHON) -m alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrate-down
migrate-down:  ## Rollback last migration
	$(PYTHON) -m alembic downgrade -1

.PHONY: migrate-status
migrate-status:  ## Show current migration revision
	$(PYTHON) -m alembic current

# ---------------------------------------------------------------------------
# Runtime — local (without Docker)
# ---------------------------------------------------------------------------
.PHONY: api
api:  ## Start the FastAPI server locally (dev mode, hot reload)
	uvicorn tinaa.api.app:create_app --factory --host 0.0.0.0 --port 8765 --reload --log-level debug

.PHONY: mcp
mcp:  ## Start the MCP server (stdio mode, for Claude Code integration)
	TINAA_MODE=mcp tinaa

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
.PHONY: clean
clean:  ## Remove build artifacts, caches, and coverage reports
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml dist build *.egg-info

.PHONY: clean-docker
clean-docker:  ## Remove stopped containers and dangling images for this project
	$(COMPOSE) down --volumes --remove-orphans
	docker image prune -f --filter "label=org.opencontainers.image.title=TINAA MSP"
