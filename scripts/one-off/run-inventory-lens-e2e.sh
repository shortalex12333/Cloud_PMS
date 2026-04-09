#!/bin/bash
# Run Inventory Lens E2E Integration Tests
#
# Usage:
#   ./scripts/run-inventory-lens-e2e.sh              # Run all tests
#   ./scripts/run-inventory-lens-e2e.sh --headed     # Run with visible browser
#   ./scripts/run-inventory-lens-e2e.sh --ui         # Run in UI mode
#   ./scripts/run-inventory-lens-e2e.sh --trace      # Run with trace
#   ./scripts/run-inventory-lens-e2e.sh --hod        # Run HOD journey only
#   ./scripts/run-inventory-lens-e2e.sh --crew       # Run CREW journey only

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Inventory Lens E2E Integration Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Parse arguments
MODE="default"
FILTER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --headed)
      MODE="headed"
      shift
      ;;
    --ui)
      MODE="ui"
      shift
      ;;
    --trace)
      MODE="trace"
      shift
      ;;
    --hod)
      FILTER="JOURNEY 1"
      shift
      ;;
    --crew)
      FILTER="JOURNEY 2"
      shift
      ;;
    --debug)
      MODE="debug"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Set environment variables
export RENDER_API_URL="https://pipeline-core.int.celeste7.ai"
export PLAYWRIGHT_BASE_URL="https://app.celeste7.ai"

echo -e "${YELLOW}Configuration:${NC}"
echo "  API URL: $RENDER_API_URL"
echo "  Frontend URL: $PLAYWRIGHT_BASE_URL"
echo "  Test Yacht: 85fe1119-b04c-41ac-80f1-829d23322598"
echo ""

# Build base command
CMD="npx playwright test tests/e2e/inventory-lens-integration.spec.ts"

# Add project
CMD="$CMD --project=e2e-chromium"

# Add filter if specified
if [ -n "$FILTER" ]; then
  CMD="$CMD --grep \"$FILTER\""
  echo -e "${YELLOW}Filter: $FILTER${NC}"
  echo ""
fi

# Add mode-specific flags
case $MODE in
  headed)
    CMD="$CMD --headed"
    echo -e "${YELLOW}Running in headed mode (visible browser)${NC}"
    ;;
  ui)
    CMD="$CMD --ui"
    echo -e "${YELLOW}Running in UI mode (interactive)${NC}"
    ;;
  trace)
    CMD="$CMD --trace on"
    echo -e "${YELLOW}Running with trace enabled${NC}"
    ;;
  debug)
    CMD="$CMD --headed --debug"
    echo -e "${YELLOW}Running in debug mode${NC}"
    ;;
  default)
    echo -e "${YELLOW}Running in headless mode${NC}"
    ;;
esac

echo ""
echo -e "${BLUE}Executing: $CMD${NC}"
echo ""

# Run the tests
eval $CMD

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}✅ All tests passed!${NC}"
  echo -e "${GREEN}========================================${NC}"
  echo ""
  echo "Evidence artifacts saved to:"
  echo "  test-results/artifacts/inventory-lens/"
  echo ""
  echo "To view evidence:"
  echo "  cat test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json"
  echo "  open test-results/artifacts/inventory-lens/hod-step4-log-usage.png"
  echo ""
  echo "To view HTML report:"
  echo "  npx playwright show-report"
else
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}❌ Tests failed (exit code: $EXIT_CODE)${NC}"
  echo -e "${RED}========================================${NC}"
  echo ""
  echo "To debug:"
  echo "  1. Check evidence files: test-results/artifacts/inventory-lens/"
  echo "  2. View screenshots: open test-results/artifacts/inventory-lens/*.png"
  echo "  3. View trace: npx playwright show-trace test-results/traces/trace.zip"
  echo "  4. Run with --ui flag: ./scripts/run-inventory-lens-e2e.sh --ui"
  echo ""
fi

exit $EXIT_CODE
