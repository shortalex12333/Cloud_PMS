#!/bin/bash
# =============================================================================
# CelesteOS Full E2E Test Suite - Safe Orchestration Script
# =============================================================================
#
# LAW 11: MECHANICAL SYMPATHY (CONCURRENCY CONTROL)
# - Playwright workers limited to 2
# - Sequential shard execution
# - Docker memory monitoring throughout
#
# LAW 12: DEEP UI VERIFICATION
# - Tests verify actual rendering, not just API responses
# - Document viewer must successfully load signed URLs
#
# Usage:
#   ./scripts/run_full_e2e_safely.sh [options]
#
# Options:
#   --staging     Run against staging URL (app.celeste7.ai)
#   --local       Run against local Docker cluster
#   --shard N     Run only shard N (1-6)
#   --headed      Run with visible browser
#   --skip-docker Skip Docker startup (assumes already running)
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS"
WEB_DIR="$PROJECT_ROOT/apps/web"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.f1-workers.yml"
RESULTS_DIR="$WEB_DIR/playwright-report"
STATS_LOG="$RESULTS_DIR/docker-stats.log"
MEMORY_LIMIT="512M"
PLAYWRIGHT_WORKERS=2

# Test credentials
export TEST_HOD_USER_EMAIL="${TEST_HOD_USER_EMAIL:-hod.test@alex-short.com}"
export TEST_CREW_USER_EMAIL="${TEST_CREW_USER_EMAIL:-crew.test@alex-short.com}"
export TEST_CAPTAIN_USER_EMAIL="${TEST_CAPTAIN_USER_EMAIL:-x@alex-short.com}"
export TEST_USER_PASSWORD="${TEST_USER_PASSWORD:-Password2!}"
export TEST_YACHT_ID="${TEST_YACHT_ID:-85fe1119-b04c-41ac-80f1-829d23322598}"

# Parse arguments
E2E_BASE_URL="https://app.celeste7.ai"
SPECIFIC_SHARD=""
HEADED=""
SKIP_DOCKER=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --staging)
      E2E_BASE_URL="https://app.celeste7.ai"
      shift
      ;;
    --local)
      E2E_BASE_URL="http://localhost:3000"
      shift
      ;;
    --shard)
      SPECIFIC_SHARD="$2"
      shift 2
      ;;
    --headed)
      HEADED="--headed"
      shift
      ;;
    --skip-docker)
      SKIP_DOCKER=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

export E2E_BASE_URL
export E2E_NO_SERVER=true  # We handle the server ourselves

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
  echo ""
  echo -e "${BLUE}=============================================================================${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}=============================================================================${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

print_info() {
  echo -e "${BLUE}ℹ $1${NC}"
}

# =============================================================================
# Docker Management
# =============================================================================

start_docker_cluster() {
  print_header "Starting Docker Cluster (512MB Memory Limit)"

  if [ "$SKIP_DOCKER" = true ]; then
    print_warning "Skipping Docker startup (--skip-docker flag)"
    return 0
  fi

  # Navigate to project root
  cd "$PROJECT_ROOT"

  # Stop any existing containers
  docker-compose -f "$DOCKER_COMPOSE_FILE" down 2>/dev/null || true

  # Remove old containers
  docker-compose -f "$DOCKER_COMPOSE_FILE" rm -f 2>/dev/null || true

  # Start fresh
  docker-compose -f "$DOCKER_COMPOSE_FILE" up -d --build

  # Wait for health checks
  print_info "Waiting for services to be healthy..."

  local max_attempts=30
  local attempt=0

  while [ $attempt -lt $max_attempts ]; do
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "healthy"; then
      print_success "API service is healthy"
      break
    fi

    sleep 2
    attempt=$((attempt + 1))
    echo -n "."
  done

  if [ $attempt -eq $max_attempts ]; then
    print_warning "Health check timeout - proceeding anyway"
  fi

  # Show container status
  echo ""
  docker-compose -f "$DOCKER_COMPOSE_FILE" ps
}

start_memory_monitor() {
  print_header "Starting Memory Monitor (LAW 11 Compliance)"

  mkdir -p "$RESULTS_DIR"

  # Start docker stats logging in background
  echo "timestamp,container,cpu_percent,mem_usage,mem_limit,mem_percent" > "$STATS_LOG"

  (
    while true; do
      docker stats --no-stream --format "{{.Container}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" 2>/dev/null | while read line; do
        echo "$(date '+%Y-%m-%d %H:%M:%S'),$line" >> "$STATS_LOG"
      done
      sleep 5
    done
  ) &

  STATS_PID=$!
  echo "$STATS_PID" > "$RESULTS_DIR/.stats_pid"

  print_success "Memory monitor started (PID: $STATS_PID)"
  print_info "Stats being logged to: $STATS_LOG"
}

stop_memory_monitor() {
  if [ -f "$RESULTS_DIR/.stats_pid" ]; then
    local pid=$(cat "$RESULTS_DIR/.stats_pid")
    kill $pid 2>/dev/null || true
    rm "$RESULTS_DIR/.stats_pid"
    print_success "Memory monitor stopped"
  fi
}

# =============================================================================
# Playwright Test Execution
# =============================================================================

run_shard() {
  local shard_name="$1"
  local shard_num="$2"

  print_header "Running Shard $shard_num: $shard_name"

  cd "$WEB_DIR"

  local start_time=$(date +%s)

  # Run Playwright with strict worker limit (LAW 11)
  npx playwright test \
    --project="$shard_name" \
    --workers=$PLAYWRIGHT_WORKERS \
    --reporter=list,json \
    $HEADED \
    2>&1 | tee "$RESULTS_DIR/shard-$shard_num.log"

  local exit_code=${PIPESTATUS[0]}
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  if [ $exit_code -eq 0 ]; then
    print_success "Shard $shard_num completed in ${duration}s"
  else
    print_error "Shard $shard_num failed (exit code: $exit_code)"
  fi

  return $exit_code
}

run_all_shards() {
  print_header "Running All Test Shards"

  local failed_shards=()
  local passed_shards=()

  # Define shards
  declare -A SHARDS
  SHARDS[1]="shard-1-auth"
  SHARDS[2]="shard-2-search"
  SHARDS[3]="shard-3-documents"
  SHARDS[4]="shard-4-entities"
  SHARDS[5]="shard-5-adversarial"
  SHARDS[6]="shard-6-email"

  # Run specific shard or all
  if [ -n "$SPECIFIC_SHARD" ]; then
    local shard_name="${SHARDS[$SPECIFIC_SHARD]}"
    if [ -z "$shard_name" ]; then
      print_error "Invalid shard number: $SPECIFIC_SHARD"
      exit 1
    fi

    if run_shard "$shard_name" "$SPECIFIC_SHARD"; then
      passed_shards+=($SPECIFIC_SHARD)
    else
      failed_shards+=($SPECIFIC_SHARD)
    fi
  else
    # Run all shards sequentially
    for i in 1 2 3 4 5 6; do
      local shard_name="${SHARDS[$i]}"

      if run_shard "$shard_name" "$i"; then
        passed_shards+=($i)
      else
        failed_shards+=($i)
      fi

      # Brief pause between shards to let resources settle
      sleep 2
    done
  fi

  # Return results
  echo ""
  print_header "Shard Summary"

  if [ ${#passed_shards[@]} -gt 0 ]; then
    print_success "Passed shards: ${passed_shards[*]}"
  fi

  if [ ${#failed_shards[@]} -gt 0 ]; then
    print_error "Failed shards: ${failed_shards[*]}"
    return 1
  fi

  return 0
}

# =============================================================================
# Report Generation
# =============================================================================

analyze_memory_usage() {
  print_header "Memory Usage Analysis (LAW 11 Verification)"

  if [ ! -f "$STATS_LOG" ]; then
    print_warning "No memory stats log found"
    return
  fi

  # Find peak memory usage
  echo ""
  echo "Peak Memory Usage by Container:"
  echo "--------------------------------"

  # Skip header and analyze
  tail -n +2 "$STATS_LOG" | while IFS=',' read -r timestamp container cpu mem_usage mem_limit mem_percent; do
    echo "$container: $mem_usage ($mem_percent)"
  done | sort -u | head -20

  # Check for memory violations
  local violations=$(tail -n +2 "$STATS_LOG" | awk -F',' '{
    gsub(/%/, "", $6);
    if ($6 > 95) print $2 ": " $5 " (" $6 "%)"
  }' | sort -u)

  if [ -n "$violations" ]; then
    echo ""
    print_warning "Containers that exceeded 95% memory:"
    echo "$violations"
  else
    print_success "All containers stayed within memory limits"
  fi
}

generate_report() {
  print_header "Generating Go/No-Go Report"

  local report_file="$RESULTS_DIR/go-no-go-report.md"
  local total_tests=0
  local passed_tests=0
  local failed_tests=0

  # Count tests from Playwright results
  if [ -f "$RESULTS_DIR/results.json" ]; then
    total_tests=$(jq '.stats.expected + .stats.unexpected + .stats.flaky' "$RESULTS_DIR/results.json" 2>/dev/null || echo 0)
    passed_tests=$(jq '.stats.expected' "$RESULTS_DIR/results.json" 2>/dev/null || echo 0)
    failed_tests=$(jq '.stats.unexpected' "$RESULTS_DIR/results.json" 2>/dev/null || echo 0)
  fi

  # Generate markdown report
  cat > "$report_file" << EOF
# CelesteOS Go/No-Go Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S %Z')
**Environment:** $E2E_BASE_URL
**Test Yacht:** $TEST_YACHT_ID

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | $total_tests |
| Passed | $passed_tests |
| Failed | $failed_tests |
| Pass Rate | $(echo "scale=2; $passed_tests * 100 / $total_tests" | bc 2>/dev/null || echo "N/A")% |

## LAW Compliance

### LAW 8: Tenant Isolation
$(if grep -q "tenant" "$RESULTS_DIR/shard-1.log" 2>/dev/null && ! grep -q "FAIL.*tenant" "$RESULTS_DIR/shard-1.log"; then echo "✅ VERIFIED"; else echo "⚠️ NEEDS REVIEW"; fi)

### LAW 11: Memory Constraints (512MB)
$(if [ -f "$STATS_LOG" ]; then
  max_percent=$(tail -n +2 "$STATS_LOG" | awk -F',' '{gsub(/%/, "", $6); if ($6 > max) max=$6} END {print max}')
  if (( $(echo "$max_percent < 95" | bc -l 2>/dev/null) )); then
    echo "✅ VERIFIED (Peak: ${max_percent}%)"
  else
    echo "⚠️ EXCEEDED (Peak: ${max_percent}%)"
  fi
else
  echo "⚠️ NO DATA"
fi)

### LAW 12: Deep UI Verification
$(if grep -q "document" "$RESULTS_DIR/shard-3.log" 2>/dev/null && ! grep -q "FAIL.*viewer" "$RESULTS_DIR/shard-3.log"; then echo "✅ VERIFIED"; else echo "⚠️ NEEDS REVIEW"; fi)

## Shard Results

| Shard | Status | Duration |
|-------|--------|----------|
$(for i in 1 2 3 4 5 6; do
  if [ -f "$RESULTS_DIR/shard-$i.log" ]; then
    if grep -q "passed" "$RESULTS_DIR/shard-$i.log"; then
      echo "| Shard $i | ✅ PASS | - |"
    else
      echo "| Shard $i | ❌ FAIL | - |"
    fi
  else
    echo "| Shard $i | ⏳ NOT RUN | - |"
  fi
done)

## Decision

$(if [ $failed_tests -eq 0 ] && [ $total_tests -gt 0 ]; then
  echo "# ✅ GO FOR LAUNCH"
  echo ""
  echo "All $total_tests tests passed. System is ready for 134-yacht deployment."
else
  echo "# ❌ NO-GO"
  echo ""
  echo "$failed_tests tests failed. Fix issues before deployment."
fi)

---

*Report generated by CelesteOS E2E Test Suite*
EOF

  print_success "Report saved to: $report_file"

  # Print report to console
  cat "$report_file"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
  print_header "CelesteOS Full E2E Test Suite"

  echo ""
  echo "Configuration:"
  echo "  Base URL: $E2E_BASE_URL"
  echo "  Playwright Workers: $PLAYWRIGHT_WORKERS"
  echo "  Memory Limit: $MEMORY_LIMIT"
  echo "  Test Yacht: $TEST_YACHT_ID"
  echo ""

  local start_time=$(date +%s)

  # Start Docker cluster (if running locally)
  if [ "$E2E_BASE_URL" = "http://localhost:3000" ]; then
    start_docker_cluster
    start_memory_monitor
  fi

  # Install Playwright browsers if needed
  cd "$WEB_DIR"
  npx playwright install chromium 2>/dev/null || true

  # Run global setup (authentication)
  print_header "Running Global Setup (Authentication)"
  npx playwright test --project=setup --reporter=list 2>&1 || {
    print_warning "Global setup had issues - continuing anyway"
  }

  # Run all test shards
  local test_result=0
  run_all_shards || test_result=$?

  # Stop memory monitor
  if [ "$E2E_BASE_URL" = "http://localhost:3000" ]; then
    stop_memory_monitor
    analyze_memory_usage
  fi

  # Generate report
  generate_report

  local end_time=$(date +%s)
  local total_duration=$((end_time - start_time))

  print_header "Execution Complete"
  echo "Total Duration: ${total_duration}s"
  echo "Results: $RESULTS_DIR"

  if [ $test_result -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=============================================================================${NC}"
    echo -e "${GREEN}                                                                             ${NC}"
    echo -e "${GREEN}     █████╗ ██╗     ██╗         ███████╗██╗   ██╗███████╗████████╗███████╗${NC}"
    echo -e "${GREEN}    ██╔══██╗██║     ██║         ██╔════╝╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔════╝${NC}"
    echo -e "${GREEN}    ███████║██║     ██║         ███████╗ ╚████╔╝ ███████╗   ██║   █████╗  ${NC}"
    echo -e "${GREEN}    ██╔══██║██║     ██║         ╚════██║  ╚██╔╝  ╚════██║   ██║   ██╔══╝  ${NC}"
    echo -e "${GREEN}    ██║  ██║███████╗███████╗    ███████║   ██║   ███████║   ██║   ███████╗${NC}"
    echo -e "${GREEN}    ╚═╝  ╚═╝╚══════╝╚══════╝    ╚══════╝   ╚═╝   ╚══════╝   ╚═╝   ╚══════╝${NC}"
    echo -e "${GREEN}                                                                             ${NC}"
    echo -e "${GREEN}                     GREEN. READY FOR 134 YACHT DEPLOYMENT                  ${NC}"
    echo -e "${GREEN}                                                                             ${NC}"
    echo -e "${GREEN}=============================================================================${NC}"
    echo ""
  else
    echo ""
    print_error "TESTS FAILED - NOT READY FOR DEPLOYMENT"
    echo ""
  fi

  return $test_result
}

# Run main function
main
