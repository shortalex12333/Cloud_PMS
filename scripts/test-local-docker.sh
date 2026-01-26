#!/bin/bash
# Local Docker Test Runner for Certificate RLS
# Usage: ./scripts/test-local-docker.sh

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "LOCAL DOCKER RLS TEST"
echo "=========================================="

# Build and run
echo "Building and starting containers..."
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner

# Cleanup
echo ""
echo "Cleaning up containers..."
docker-compose -f docker-compose.test.yml down

echo ""
echo "Done."
