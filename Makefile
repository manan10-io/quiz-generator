.PHONY: help dev dev-backend dev-frontend build up down logs test test-backend \
        migrate migrate-create lint format clean install

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Local development (no Docker) ──────────────────────────────────────────────

install: ## Install all dependencies (frontend + backend)
	cd frontend && npm install
	cd backend && pip install -r requirements.txt

dev-backend: ## Run backend with hot-reload (requires venv activated)
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run frontend dev server
	cd frontend && npm run dev

# ─── Docker Compose ──────────────────────────────────────────────────────────────

build: ## Build all Docker images
	docker compose build

up: ## Start full stack (Postgres + Redis + backend + frontend)
	docker compose up --build

dev: ## Start full stack with hot-reload for local development
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down: ## Stop and remove all containers
	docker compose down

down-volumes: ## Stop containers AND delete all data (Postgres, Redis, uploads)
	docker compose down -v

logs: ## Tail logs from all services
	docker compose logs -f

logs-backend: ## Tail backend logs only
	docker compose logs -f backend

logs-frontend: ## Tail frontend logs only
	docker compose logs -f frontend

# ─── Database ─────────────────────────────────────────────────────────────────────

migrate: ## Apply all pending Alembic migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add foo column")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Roll back the most recent migration
	cd backend && alembic downgrade -1

# ─── Testing ──────────────────────────────────────────────────────────────────────

test: test-backend ## Run all test suites

test-backend: ## Run backend pytest suite
	cd backend && pytest -v

test-backend-cov: ## Run backend tests with coverage report
	cd backend && pytest --cov=app --cov-report=term-missing

# ─── Code quality ─────────────────────────────────────────────────────────────────

lint: ## Lint both frontend and backend
	cd frontend && npm run lint
	cd backend && python -m py_compile $$(find app -name "*.py")

format-frontend: ## Format frontend code
	cd frontend && npx prettier --write "src/**/*.{ts,tsx}"

type-check: ## Run TypeScript type checking
	cd frontend && npm run type-check

# ─── Cleanup ──────────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and node_modules
	cd frontend && rm -rf .next node_modules
	cd backend && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
		rm -rf .pytest_cache .mypy_cache htmlcov .coverage
