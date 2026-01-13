#!/bin/bash
# ============================================================================
# CI Gate Script
# ============================================================================
# Enforces: build + typecheck + lint + contracts + e2e + artifacts
# Returns non-zero exit code if any step fails
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

echo "=============================================="
echo "CI Gate - Full Verification Pipeline"
echo "=============================================="
echo "Repo root: $REPO_ROOT"
echo ""

FAILED_STEPS=()

run_step() {
    local step_name=$1
    local step_command=$2

    echo ""
    echo "--- Step: $step_name ---"
    echo "Command: $step_command"
    echo ""

    if eval "$step_command"; then
        echo -e "${GREEN}PASSED: $step_name${NC}"
        return 0
    else
        echo -e "${RED}FAILED: $step_name${NC}"
        FAILED_STEPS+=("$step_name")
        return 1
    fi
}

# ----------------------------------------------------------------------------
# Step 1: Environment Verification
# ----------------------------------------------------------------------------

run_step "Environment Verification" "./scripts/e2e/verify_env.sh" || true

# ----------------------------------------------------------------------------
# Step 2: Frontend Build
# ----------------------------------------------------------------------------

run_step "Frontend Build" "cd apps/web && npm run build" || true

# ----------------------------------------------------------------------------
# Step 3: TypeScript Check
# ----------------------------------------------------------------------------

run_step "TypeScript Check" "cd apps/web && npm run typecheck" || true

# ----------------------------------------------------------------------------
# Step 4: ESLint
# ----------------------------------------------------------------------------

run_step "ESLint" "cd apps/web && npm run lint" || true

# ----------------------------------------------------------------------------
# Step 5: Contract Tests
# ----------------------------------------------------------------------------

run_step "Contract Tests" "npm run test:contracts" || true

# ----------------------------------------------------------------------------
# Step 6: E2E Tests
# ----------------------------------------------------------------------------

run_step "E2E Tests" "npm run test:e2e" || true

# ----------------------------------------------------------------------------
# Step 7: Artifacts Verification
# ----------------------------------------------------------------------------

echo ""
echo "--- Step: Artifacts Verification ---"
echo ""

ARTIFACTS_DIR="$REPO_ROOT/test-results/artifacts"

if [ -d "$ARTIFACTS_DIR" ]; then
    ARTIFACT_COUNT=$(find "$ARTIFACTS_DIR" -type f -name "*.json" | wc -l | tr -d ' ')

    if [ "$ARTIFACT_COUNT" -ge 5 ]; then
        echo -e "${GREEN}PASSED: Artifacts Verification ($ARTIFACT_COUNT JSON files found)${NC}"
    else
        echo -e "${RED}FAILED: Artifacts Verification (only $ARTIFACT_COUNT JSON files, need >= 5)${NC}"
        FAILED_STEPS+=("Artifacts Verification")
    fi

    echo ""
    echo "Artifact files:"
    find "$ARTIFACTS_DIR" -type f -name "*.json" | head -20
else
    echo -e "${RED}FAILED: Artifacts directory not found at $ARTIFACTS_DIR${NC}"
    FAILED_STEPS+=("Artifacts Verification")
fi

# ----------------------------------------------------------------------------
# Final Summary
# ----------------------------------------------------------------------------

echo ""
echo "=============================================="
echo "CI Gate Summary"
echo "=============================================="

if [ ${#FAILED_STEPS[@]} -eq 0 ]; then
    echo -e "${GREEN}ALL STEPS PASSED${NC}"
    echo ""
    echo "You may proceed with deployment."
    exit 0
else
    echo -e "${RED}FAILED STEPS:${NC}"
    for step in "${FAILED_STEPS[@]}"; do
        echo "  - $step"
    done
    echo ""
    echo -e "${RED}DO NOT DEPLOY until all steps pass.${NC}"
    exit 1
fi
