#!/bin/bash
# Strict Test Runner
# Runs tests and validates results through the gatekeeper

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESULTS_FILE="$SCRIPT_DIR/results/matrix_results.jsonl"
VALIDATED_FILE="$SCRIPT_DIR/results/validated_results.jsonl"

echo "=== STRICT TEST RUNNER ==="
echo ""
echo "Step 1: Clear previous results"
rm -f "$RESULTS_FILE" "$VALIDATED_FILE"

echo ""
echo "Step 2: Run tests (this will generate $RESULTS_FILE)"
cd "$PROJECT_ROOT"

# Load environment variables
if [ -f .env.e2e ]; then
  export $(grep -v '^#' .env.e2e | xargs)
fi

# Run the strict tests
npx playwright test tests/e2e/microactions_matrix_strict.spec.ts --reporter=list || true

echo ""
echo "Step 3: Validate results through gatekeeper"
if [ ! -f "$RESULTS_FILE" ]; then
  echo "ERROR: No results file generated at $RESULTS_FILE"
  exit 1
fi

# Run validator
npx ts-node "$SCRIPT_DIR/lib/validate-results.ts" "$RESULTS_FILE" "$VALIDATED_FILE"

echo ""
echo "=== ONLY VALIDATOR OUTPUT MATTERS ==="
echo ""
echo "Raw test results: $RESULTS_FILE"
echo "Validated results: $VALIDATED_FILE"
