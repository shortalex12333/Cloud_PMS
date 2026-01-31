#!/bin/bash
# Test Runner for Entity Extraction Pipeline
# Usage: ./run_tests.sh [docker|local|mock]

set -e

MODE=${1:-local}

case "$MODE" in
  docker)
    echo "🐳 Running tests in Docker..."
    echo "Building test image..."
    docker build -t extraction-test -f Dockerfile.test .

    echo "Running tests..."
    if [ -f ".env.test.local" ]; then
      echo "Using .env.test.local for API keys"
      docker run --env-file .env.test.local extraction-test
    else
      echo "Using .env.test (no API keys - AI tests will be skipped)"
      docker run --env-file .env.test extraction-test
    fi
    ;;

  local)
    echo "🧪 Running tests locally..."
    export PYTHONPATH="${PWD}:${PYTHONPATH}"

    # Load test env vars if available
    if [ -f ".env.test.local" ]; then
      echo "Loading .env.test.local"
      export $(grep -v '^#' .env.test.local | xargs)
    fi

    pytest tests/test_async_orchestrator.py -v --tb=short
    ;;

  mock)
    echo "🎭 Running tests with mocked AI (no API costs)..."
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    export OPENAI_API_KEY=""  # Force mock mode

    pytest tests/test_async_orchestrator.py -v --tb=short -k "mock or fast_path"
    ;;

  coverage)
    echo "📊 Running tests with coverage report..."
    export PYTHONPATH="${PWD}:${PYTHONPATH}"

    if [ -f ".env.test.local" ]; then
      export $(grep -v '^#' .env.test.local | xargs)
    fi

    pytest tests/test_async_orchestrator.py -v --cov=extraction --cov-report=html --cov-report=term
    echo ""
    echo "📈 Coverage report generated: htmlcov/index.html"
    ;;

  *)
    echo "Usage: ./run_tests.sh [docker|local|mock|coverage]"
    echo ""
    echo "Modes:"
    echo "  docker   - Run tests in Docker container (matches production)"
    echo "  local    - Run tests locally with pytest"
    echo "  mock     - Run tests with mocked AI (no API costs)"
    echo "  coverage - Run tests with coverage report"
    exit 1
    ;;
esac

echo "✅ Tests complete!"
