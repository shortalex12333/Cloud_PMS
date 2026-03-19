#!/usr/bin/env bash
# verify-local.sh — Single command to verify the entire Cloud_PMS stack locally.
#
# Usage:
#   ./scripts/verify-local.sh          # Full E2E suite
#   ./scripts/verify-local.sh --quick  # Build + unit tests only (no Docker/Playwright)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR="$REPO_ROOT/apps/web"
ENV_FILE="$WEB_DIR/.env.e2e"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
header() { echo -e "\n${YELLOW}━━━ $1 ━━━${NC}"; }

ERRORS=0

# ─── Quick mode ──────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--quick" ]]; then
  header "Quick Verification (build + unit tests)"
  cd "$WEB_DIR"
  echo "Building..."
  if npm run build > /dev/null 2>&1; then pass "npm run build"; else fail "npm run build"; ERRORS=$((ERRORS + 1)); fi
  echo "Unit tests..."
  if npm run test:unit 2>&1 | tail -5; then pass "Unit tests"; else fail "Unit tests"; ERRORS=$((ERRORS + 1)); fi
  [[ $ERRORS -eq 0 ]] && { echo -e "\n${GREEN}Quick verification passed.${NC}"; exit 0; } || { echo -e "\n${RED}$ERRORS error(s).${NC}"; exit 1; }
fi

# ─── Full verification ──────────────────────────────────────────────────────
header "Step 1: Docker Stack"
if ! docker info > /dev/null 2>&1; then fail "Docker not running"; exit 1; fi
pass "Docker daemon running"

RUNNING=$(docker compose -f "$REPO_ROOT/docker-compose.yml" --profile full ps --status running -q 2>/dev/null | wc -l | tr -d ' ')
if [[ "$RUNNING" -lt 3 ]]; then
  warn "Starting Docker stack..."
  cd "$REPO_ROOT" && docker compose --profile full up --build -d
  sleep 15
  RUNNING=$(docker compose -f "$REPO_ROOT/docker-compose.yml" --profile full ps --status running -q 2>/dev/null | wc -l | tr -d ' ')
fi
pass "Docker stack ($RUNNING containers)"

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then pass "API health (port 8000)"; else warn "API health check failed"; fi

header "Step 2: Next.js Dev Server"
NEXTJS_PID="" STARTED_NEXTJS=false
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
  pass "Next.js already on :3000"
else
  warn "Starting Next.js..."
  cd "$WEB_DIR" && nohup npm run dev > /tmp/verify-nextjs.log 2>&1 & NEXTJS_PID=$! STARTED_NEXTJS=true
  for i in $(seq 1 30); do curl -sf http://localhost:3000 > /dev/null 2>&1 && break; sleep 2; done
  if curl -sf http://localhost:3000 > /dev/null 2>&1; then pass "Next.js started (PID: $NEXTJS_PID)"; else fail "Next.js failed"; ERRORS=$((ERRORS + 1)); fi
fi

header "Step 3: E2E Tests"
if [[ ! -f "$ENV_FILE" ]]; then fail ".env.e2e not found"; ERRORS=$((ERRORS + 1)); else
  pass "Found .env.e2e"
  cd "$WEB_DIR"
  set -a; source "$ENV_FILE"; set +a
  if npx playwright test 2>&1 | tee /tmp/verify-e2e.log | tail -20; then pass "E2E tests"; else fail "E2E tests (see /tmp/verify-e2e.log)"; ERRORS=$((ERRORS + 1)); fi
fi

[[ "$STARTED_NEXTJS" == true && -n "$NEXTJS_PID" ]] && kill "$NEXTJS_PID" 2>/dev/null || true

header "Summary"
[[ $ERRORS -eq 0 ]] && { echo -e "${GREEN}All checks passed.${NC}"; exit 0; } || { echo -e "${RED}$ERRORS check(s) failed.${NC}"; exit 1; }
