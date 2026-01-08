# CelesteOS Monorepo - Developer Commands
# Cloud-first AI-powered Yacht PMS

.PHONY: help dev-web dev-api dev test lint typecheck install clean

# Default target
help:
	@echo "CelesteOS Development Commands"
	@echo "==============================="
	@echo ""
	@echo "Development:"
	@echo "  make dev-web        - Start Next.js frontend (port 3000)"
	@echo "  make dev-api        - Start FastAPI backend (port 8000)"
	@echo "  make dev            - Start both frontend and backend"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Run linters (frontend + backend)"
	@echo "  make typecheck      - Run TypeScript type checking"
	@echo ""
	@echo "Setup:"
	@echo "  make install        - Install all dependencies"
	@echo "  make clean          - Clean build artifacts"
	@echo ""

# Start Next.js frontend
dev-web:
	@echo "🚀 Starting Next.js frontend on http://localhost:3000"
	cd apps/web && npm run dev

# Start FastAPI backend
dev-api:
	@echo "🚀 Starting FastAPI backend on http://localhost:8000"
	cd apps/api && uvicorn pipeline_service:app --reload --host 0.0.0.0 --port 8000

# Start both services (requires tmux or separate terminals)
dev:
	@echo "⚠️  Run 'make dev-web' and 'make dev-api' in separate terminals"
	@echo "   Or use: tmux new-session 'make dev-web' \\; split-window 'make dev-api'"

# Run all tests
test:
	@echo "🧪 Running frontend tests..."
	cd apps/web && npm test || true
	@echo "🧪 Running backend tests..."
	cd apps/api && pytest tests/ || true

# Run linters
lint:
	@echo "🔍 Linting frontend..."
	cd apps/web && npm run lint
	@echo "🔍 Linting backend..."
	cd apps/api && black . --check && flake8 .

# TypeScript type checking
typecheck:
	@echo "🔍 Type checking frontend..."
	cd apps/web && npm run typecheck || npx tsc --noEmit

# Install all dependencies
install:
	@echo "📦 Installing frontend dependencies..."
	cd apps/web && npm install
	@echo "📦 Installing backend dependencies..."
	cd apps/api && pip install -r requirements.txt

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf apps/web/.next apps/web/node_modules apps/web/out
	find apps/api -type d -name __pycache__ -exec rm -rf {} + || true
	find apps/api -type f -name "*.pyc" -delete || true
	@echo "✅ Cleaned!"
