#!/bin/bash
#
# Autonomous Testing Orchestrator
#
# Runs 6-hour autonomous test loop:
# 1. Sample real data from yTEST_YACHT_001
# 2. Generate test emails
# 3. Launch workers
# 4. Wait for processing
# 5. Validate results
# 6. Record metrics
# 7. Repeat for 36 cycles (10 min each)
#
# Usage:
#   ./scripts/autonomy/run_autonomy.sh [--cycles N] [--cycle-duration M]
#

set -e

# Configuration
CYCLES=${1:-36}              # Default: 36 cycles for 6 hours
CYCLE_DURATION=${2:-600}     # Default: 10 minutes per cycle
TEST_EMAIL_COUNT=50          # Emails per cycle
RESULTS_DIR="test-results/autonomy"
RUN_ID=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${RESULTS_DIR}/run_${RUN_ID}.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure results dir exists
mkdir -p "${RESULTS_DIR}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log_section() {
    echo "" | tee -a "${LOG_FILE}"
    echo "================================================================" | tee -a "${LOG_FILE}"
    echo "$1" | tee -a "${LOG_FILE}"
    echo "================================================================" | tee -a "${LOG_FILE}"
}

# Check environment variables
check_env() {
    local required_vars=(
        "MASTER_SUPABASE_URL"
        "MASTER_SUPABASE_SERVICE_KEY"
        "yTEST_YACHT_001_SUPABASE_URL"
        "yTEST_YACHT_001_SUPABASE_SERVICE_KEY"
        "OPENAI_API_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}✗ Missing required environment variable: $var${NC}"
            exit 1
        fi
    done

    log "✓ All required environment variables present"
}

# Start workers
start_workers() {
    log_section "Starting Workers"

    # Stop any existing workers
    docker-compose -f docker-compose.workers.yml down 2>/dev/null || true

    # Start workers in background
    log "Starting docker-compose workers..."
    docker-compose -f docker-compose.workers.yml up -d

    # Wait for workers to be ready
    log "Waiting 30s for workers to initialize..."
    sleep 30

    # Check worker status
    docker-compose -f docker-compose.workers.yml ps | tee -a "${LOG_FILE}"

    log "✓ Workers started"
}

# Stop workers
stop_workers() {
    log_section "Stopping Workers"
    docker-compose -f docker-compose.workers.yml down
    log "✓ Workers stopped"
}

# Sample real data
sample_data() {
    log_section "Cycle $1/$2 - Sampling Real Data"
    python3 scripts/autonomy/sample_real_data.py 2>&1 | tee -a "${LOG_FILE}"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✓ Data sampling complete"
    else
        log "✗ Data sampling failed"
        return 1
    fi
}

# Generate test emails
generate_emails() {
    log_section "Cycle $1/$2 - Generating Test Emails"
    python3 scripts/autonomy/simulate_self_email.py --count ${TEST_EMAIL_COUNT} 2>&1 | tee -a "${LOG_FILE}"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✓ Generated ${TEST_EMAIL_COUNT} test emails"
    else
        log "✗ Email generation failed"
        return 1
    fi
}

# Wait for processing
wait_for_processing() {
    local cycle=$1
    local max_cycles=$2
    local wait_time=300  # 5 minutes

    log_section "Cycle $cycle/$max_cycles - Waiting for Processing"
    log "Waiting ${wait_time}s for workers to process emails..."

    # Progress bar
    for i in $(seq 1 $wait_time); do
        if [ $((i % 30)) -eq 0 ]; then
            echo -n "." | tee -a "${LOG_FILE}"
        fi
        sleep 1
    done
    echo "" | tee -a "${LOG_FILE}"

    log "✓ Processing window complete"
}

# Validate results
validate_results() {
    log_section "Cycle $1/$2 - Validating Results"
    python3 scripts/autonomy/validate_autolinking.py 2>&1 | tee -a "${LOG_FILE}"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "✓ Validation complete"
    else
        log "✗ Validation failed"
        return 1
    fi
}

# Check worker health
check_worker_health() {
    log_section "Worker Health Check"

    # Check if containers are running
    local running=$(docker-compose -f docker-compose.workers.yml ps --quiet | wc -l)
    log "Running workers: $running/4"

    # Check logs for errors
    docker-compose -f docker-compose.workers.yml logs --tail=50 2>&1 | grep -i error | tee -a "${LOG_FILE}" || true

    if [ $running -eq 4 ]; then
        log "✓ All workers healthy"
        return 0
    else
        log "✗ Some workers are down"
        return 1
    fi
}

# Aggregate metrics
aggregate_metrics() {
    log_section "Aggregating Metrics"

    local validation_files=$(ls -1 ${RESULTS_DIR}/validation_*.json 2>/dev/null | wc -l)

    log "Total validation runs: $validation_files"

    if [ $validation_files -gt 0 ]; then
        # Extract key metrics from latest validation
        local latest=$(ls -1t ${RESULTS_DIR}/validation_*.json | head -1)

        log "Latest validation: $(basename $latest)"

        # Use jq if available to parse JSON
        if command -v jq &> /dev/null; then
            log ""
            log "Key Metrics:"
            jq -r '.metrics | "  L1 Precision: \(.l1_precision)%\n  L2.5 Top-1: \(.l25_top1_alignment)%\n  Suggestion Coverage: \(.suggestion_coverage)%\n  P50 Latency: \(.p50_latency_seconds)s\n  P95 Latency: \(.p95_latency_seconds)s"' "$latest" | tee -a "${LOG_FILE}"
        fi
    fi

    log "✓ Metrics aggregation complete"
}

# Main test loop
run_test_loop() {
    log_section "Starting 6-Hour Autonomous Test"
    log "Configuration:"
    log "  Cycles: $CYCLES"
    log "  Cycle Duration: $CYCLE_DURATION seconds"
    log "  Test Emails per Cycle: $TEST_EMAIL_COUNT"
    log "  Run ID: $RUN_ID"
    log "  Log File: $LOG_FILE"

    # Check environment
    check_env

    # Start workers once
    start_workers

    # Main loop
    for cycle in $(seq 1 $CYCLES); do
        log_section "CYCLE $cycle/$CYCLES"

        # Step 1: Sample data
        if ! sample_data $cycle $CYCLES; then
            log "⚠ Skipping cycle due to sampling failure"
            continue
        fi

        # Step 2: Generate test emails
        if ! generate_emails $cycle $CYCLES; then
            log "⚠ Skipping cycle due to email generation failure"
            continue
        fi

        # Step 3: Wait for processing
        wait_for_processing $cycle $CYCLES

        # Step 4: Validate results
        if ! validate_results $cycle $CYCLES; then
            log "⚠ Validation failed, continuing..."
        fi

        # Step 5: Health check
        if ! check_worker_health; then
            log "⚠ Worker health issue detected"

            # Attempt restart
            log "Attempting to restart workers..."
            stop_workers
            sleep 10
            start_workers
        fi

        # Wait for remainder of cycle
        local elapsed=$((CYCLE_DURATION - 300))  # Subtract processing wait time
        if [ $elapsed -gt 0 ]; then
            log "Waiting ${elapsed}s until next cycle..."
            sleep $elapsed
        fi
    done

    # Cleanup
    stop_workers

    # Final aggregation
    aggregate_metrics

    log_section "Autonomous Test Complete"
    log "Results saved to: ${RESULTS_DIR}/"
    log "Log file: ${LOG_FILE}"
}

# Trap for cleanup
trap 'log "Interrupted! Cleaning up..."; stop_workers; exit 1' INT TERM

# Run
run_test_loop
