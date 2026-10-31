# ==============================================================================
# Multimodal RAG - Unified Makefile
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Colors for terminal output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

.PHONY: help setup dev dev-backend dev-frontend build up down ps logs logs-backend logs-frontend restart test test-backend test-frontend lint clean

# Allow passing service names to 'make logs' (e.g. 'make logs backend', 'make logs frontend')
ifeq (logs,$(firstword $(MAKECMDGOALS)))
  LOG_SERVICES := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval .PHONY: $(LOG_SERVICES))
  $(eval $(LOG_SERVICES):;@true)
endif

## Show this help message
help:
	@echo -e "$(CYAN)Multimodal RAG Orchestrator$(RESET)"
	@echo -e "Usage: make $(GREEN)<target>$(RESET)\n"
	@echo -e "Targets:"
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  $(GREEN)%-18s$(RESET) %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

## Install all dependencies for backend (Python venv) and frontend (npm)
setup: setup-env setup-backend setup-frontend
	@echo -e "$(GREEN)✓ Setup completed successfully!$(RESET)"

setup-env:
	@if [ ! -f .env ]; then \
		cp .env.dist .env 2>/dev/null || true; \
		echo -e "$(YELLOW)Created .env from .env.dist$(RESET)"; \
	fi
	@ln -sf ../.env backend/.env 2>/dev/null || cp .env backend/.env
	@ln -sf ../.env frontend/.env.local 2>/dev/null || cp .env frontend/.env.local
	@echo -e "$(GREEN)✓ Sincronizado único .env global para backend y frontend.$(RESET)"

setup-backend:
	@echo -e "$(CYAN)Setting up backend Python environment...$(RESET)"
	@python3 -m venv backend/.venv
	@backend/.venv/bin/pip install --upgrade pip
	@backend/.venv/bin/pip install -r backend/requirements.txt

setup-frontend:
	@echo -e "$(CYAN)Setting up frontend Node environment...$(RESET)"
	@cd frontend && npm install

## Start backend local development server (FastAPI with reload)
dev-backend:
	@echo -e "$(CYAN)Starting backend on http://localhost:8000 ...$(RESET)"
	@cd backend && .venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

## Start frontend local development server (Next.js)
dev-frontend:
	@echo -e "$(CYAN)Starting frontend on http://localhost:3000 ...$(RESET)"
	@cd frontend && npm run dev

## Start both backend and frontend concurrently in development mode
dev:
	@echo -e "$(CYAN)Starting backend and frontend in parallel...$(RESET)"
	@make -j 2 dev-backend dev-frontend

## Build Docker images
build:
	@echo -e "$(CYAN)Building Docker containers...$(RESET)"
	docker compose build

## Run complete stack with Docker Compose in detached mode (frees console)
up:
	@echo -e "$(CYAN)Starting all services in detached mode...$(RESET)"
	docker compose up -d --build
	@echo -e "\n$(GREEN)✓ All services running in background!$(RESET)"
	@echo -e "  Frontend UI:  $(CYAN)http://localhost:3000$(RESET)"
	@echo -e "  Backend API:  $(CYAN)http://localhost:8000/docs$(RESET)"
	@echo -e "  Qdrant DB:    $(CYAN)http://localhost:6333/dashboard$(RESET)"
	@echo -e "  Redis Cache:  $(CYAN)localhost:6379$(RESET)\n"
	@echo -e "Run '$(YELLOW)make logs$(RESET)' to view live output, or '$(RED)make down$(RESET)' to stop containers."

## View real-time logs (e.g. 'make logs', 'make logs backend', 'make logs frontend')
logs:
	@if [ -n "$(LOG_SERVICES)" ]; then \
		echo -e "$(CYAN)Streaming logs for service(s): $(LOG_SERVICES)...$(RESET)"; \
		docker compose logs -f $(LOG_SERVICES); \
	else \
		echo -e "$(CYAN)Streaming logs for all services...$(RESET)"; \
		docker compose logs -f; \
	fi

## View real-time logs for backend service
logs-backend:
	@echo -e "$(CYAN)Streaming logs for backend...$(RESET)"
	docker compose logs -f backend

## View real-time logs for frontend service
logs-frontend:
	@echo -e "$(CYAN)Streaming logs for frontend...$(RESET)"
	docker compose logs -f frontend

## Stop all Docker Compose services and clean containers
down:
	@echo -e "$(YELLOW)Stopping all services...$(RESET)"
	docker compose down
	@echo -e "$(GREEN)✓ All services stopped successfully.$(RESET)"

## List active project containers (equivalent to 'docker ps')
ps:
	@echo -e "$(CYAN)Listing active containers...$(RESET)"
	docker compose ps

## Restart Docker Compose services
restart: down up

## Run all unit and integration tests
test: test-backend test-frontend
	@echo -e "$(GREEN)✓ All test suites passed!$(RESET)"

test-backend:
	@echo -e "$(CYAN)Running Backend tests (pytest with coverage)...$(RESET)"
	@cd backend && .venv/bin/pytest -v --tb=short

test-frontend:
	@echo -e "$(CYAN)Running Frontend unit tests and linting...$(RESET)"
	@cd frontend && npm test -- --run && npm run lint

## Run linters and type checkers
lint:
	@echo -e "$(CYAN)Linting backend...$(RESET)"
	@cd backend && .venv/bin/ruff check . || true
	@echo -e "$(CYAN)Linting frontend...$(RESET)"
	@cd frontend && npm run lint

## Clean up temporary files, pycache, node build artifacts and docker volumes
clean:
	@echo -e "$(YELLOW)Cleaning caches and temporary files...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf backend/storage/uploads/* backend/storage/images/* 2>/dev/null || true
	@echo -e "$(GREEN)✓ Clean complete.$(RESET)"
