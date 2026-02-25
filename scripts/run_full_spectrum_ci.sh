#!/bin/bash
#
# Full Spectrum Testing Crucible - CI Orchestration
#
# LAW 16: SEQUENTIAL RESOURCE MANAGEMENT
# Docker workers are constrained to 512MB RAM and 0.5 CPU.
# PyTest and Playwright MUST NOT run concurrently.
#
# Execution order:
# 1. Backend PyTest (API tests, RLS, F1 Math)
# 2. Teardown memory-heavy dependencies
# 3. Frontend Playwright (E2E UI tests)
#
# Exit codes:
# 0 - All tests passed
# 1 - PyTest failed
# 2 - Playwright failed
# 3 - Environment setup failed
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="${PROJECT_ROOT}/apps/api"
WEB_DIR="${PROJECT_ROOT}/apps/web"
PYTEST_RESULTS="${PROJECT_ROOT}/test-results/pytest"
PLAYWRIGHT_RESULTS="${PROJECT_ROOT}/test-results/playwright"

# Create results directories
mkdir -p "${PYTEST_RESULTS}" "${PLAYWRIGHT_RESULTS}"

echo ""
echo "=============================================="
echo "  CELESTE OS - FULL SPECTRUM TESTING CRUCIBLE"
echo "=============================================="
echo ""
echo "LAW 15: The Testing Pyramid"
echo "  - E2E UI tests prove the user journey"
echo "  - API/Backend tests prove the physics"
echo ""
echo "LAW 16: Sequential Resource Management"
echo "  - PyTest first, then teardown"
echo "  - Playwright second"
echo "  - Never concurrent"
echo ""
echo "=============================================="
echo ""

# ============================================================================
# PHASE 1: Environment Validation
# ============================================================================

log_info "Phase 1: Environment Validation"

# Check required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is required but not installed"
        exit 3
    fi
}

check_tool python3
check_tool pytest
check_tool node
check_tool npx

log_success "All required tools found"

# ============================================================================
# PHASE 2: Backend PyTest Crucible
# ============================================================================

echo ""
echo "=============================================="
echo "  PHASE 2: BACKEND PYTEST CRUCIBLE"
echo "=============================================="
echo ""

log_info "Starting Backend PyTest suite..."
log_info "Tests: RLS isolation, F1 RRF math, SSE streaming"

cd "${API_DIR}"

# Set Python path
export PYTHONPATH="${API_DIR}:${PYTHONPATH}"

# Run PyTest with coverage
PYTEST_EXIT_CODE=0
pytest tests/ \
    -v \
    --tb=short \
    --asyncio-mode=auto \
    --junitxml="${PYTEST_RESULTS}/junit.xml" \
    --cov=routes \
    --cov=action_router \
    --cov=services \
    --cov-report=html:"${PYTEST_RESULTS}/coverage" \
    --cov-report=term-missing \
    2>&1 | tee "${PYTEST_RESULTS}/output.log" || PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -ne 0 ]; then
    log_error "PyTest failed with exit code ${PYTEST_EXIT_CODE}"
    log_error "See ${PYTEST_RESULTS}/output.log for details"

    # Continue to show error details but mark as failed
    echo ""
    echo "PyTest Failures:"
    grep -A 10 "FAILED" "${PYTEST_RESULTS}/output.log" || true

    exit 1
fi

log_success "PyTest passed!"

# ============================================================================
# PHASE 3: Memory Teardown
# ============================================================================

echo ""
echo "=============================================="
echo "  PHASE 3: MEMORY TEARDOWN (LAW 16)"
echo "=============================================="
echo ""

log_info "Releasing PyTest memory before Playwright..."

# Force Python garbage collection
python3 -c "import gc; gc.collect()" 2>/dev/null || true

# Kill any lingering Python processes from tests
pkill -f "pytest" 2>/dev/null || true

# Clear system cache (if running as root in CI)
if [ "$(id -u)" -eq 0 ]; then
    sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
fi

# Wait for memory to stabilize
sleep 2

log_success "Memory released"

# ============================================================================
# PHASE 4: Frontend Playwright Matrix
# ============================================================================

echo ""
echo "=============================================="
echo "  PHASE 4: FRONTEND PLAYWRIGHT MATRIX"
echo "=============================================="
echo ""

log_info "Starting Frontend Playwright E2E suite..."
log_info "Shards: Auth, Search, Documents, Entities, Adversarial, Email, Equipment, Work Orders, Faults, Parts, Extreme Cases"

cd "${WEB_DIR}"

# Install Playwright browsers if needed
npx playwright install chromium --with-deps 2>/dev/null || true

# Run Playwright tests
PLAYWRIGHT_EXIT_CODE=0
npx playwright test \
    --reporter=html,json,list \
    --output="${PLAYWRIGHT_RESULTS}" \
    2>&1 | tee "${PLAYWRIGHT_RESULTS}/output.log" || PLAYWRIGHT_EXIT_CODE=$?

if [ $PLAYWRIGHT_EXIT_CODE -ne 0 ]; then
    log_error "Playwright failed with exit code ${PLAYWRIGHT_EXIT_CODE}"
    log_error "See ${PLAYWRIGHT_RESULTS}/output.log for details"

    # Show failure summary
    echo ""
    echo "Playwright Failures:"
    grep -E "(FAILED|✘)" "${PLAYWRIGHT_RESULTS}/output.log" | head -20 || true

    exit 2
fi

log_success "Playwright passed!"

# ============================================================================
# PHASE 5: Results Summary
# ============================================================================

echo ""
echo "=============================================="
echo "  FULL SPECTRUM RESULTS"
echo "=============================================="
echo ""

# Count PyTest results
PYTEST_PASSED=$(grep -c "passed" "${PYTEST_RESULTS}/output.log" 2>/dev/null || echo "0")
PYTEST_FAILED=$(grep -c "failed" "${PYTEST_RESULTS}/output.log" 2>/dev/null || echo "0")

# Count Playwright results
PLAYWRIGHT_PASSED=$(grep -oP '\d+(?= passed)' "${PLAYWRIGHT_RESULTS}/output.log" 2>/dev/null || echo "0")
PLAYWRIGHT_FAILED=$(grep -oP '\d+(?= failed)' "${PLAYWRIGHT_RESULTS}/output.log" 2>/dev/null || echo "0")

echo "PyTest Results:"
echo "  Passed: ${PYTEST_PASSED}"
echo "  Failed: ${PYTEST_FAILED}"
echo ""
echo "Playwright Results:"
echo "  Passed: ${PLAYWRIGHT_PASSED}"
echo "  Failed: ${PLAYWRIGHT_FAILED}"
echo ""

TOTAL_PASSED=$((PYTEST_PASSED + PLAYWRIGHT_PASSED))
TOTAL_FAILED=$((PYTEST_FAILED + PLAYWRIGHT_FAILED))

if [ "${TOTAL_FAILED}" -eq 0 ]; then
    echo ""
    log_success "=============================================="
    log_success "  ALL TESTS PASSED: ${TOTAL_PASSED} TOTAL"
    log_success "=============================================="
    echo ""
    echo "CORTEX LOCKED. READY FOR YACHT DEPLOYMENT."
    echo ""
    exit 0
else
    echo ""
    log_error "=============================================="
    log_error "  TESTS FAILED: ${TOTAL_FAILED} failures"
    log_error "=============================================="
    echo ""
    exit 1
fi
