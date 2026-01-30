#!/bin/bash
# =============================================================================
# Part Lens v2 - Canary Monitoring Script
# =============================================================================
# Monitors Part Lens v2 in 5% canary mode for 1 hour
# Hard gates: zero 5xx, error rate < 2%
# Tracks P50/P95/P99 latency (informational, not blocking)
#
# Usage:
#   ./scripts/ops/monitor_canary_part_lens_v2.sh [duration_minutes]
#
# Environment:
#   HOD_JWT - Required JWT token for authentication
#   API_BASE - API base URL (default: https://pipeline-core.int.celeste7.ai)
# =============================================================================

set -euo pipefail

# Configuration
API_BASE="${API_BASE:-https://pipeline-core.int.celeste7.ai}"
DURATION_MINUTES="${1:-60}"
SAMPLE_INTERVAL=30  # seconds between samples
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
PART_ID="8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3"

# HOD JWT
HOD_JWT="${HOD_JWT:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg}"

# Counters
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0
FIVE_XX_COUNT=0
FOUR_XX_COUNT=0
TWO_XX_COUNT=0

# Latency tracking
declare -a LATENCIES

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Output file
OUTPUT_FILE="docs/evidence/part_lens_v2/canary_monitoring_$(date +%Y%m%d_%H%M%S).json"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Sample Request
# =============================================================================
make_sample_request() {
    local start_time=$(date +%s%3N)

    # Randomly choose between view and consume (70% view, 30% consume)
    local rand=$((RANDOM % 100))

    if [ $rand -lt 70 ]; then
        # view_part_details
        PAYLOAD=$(cat <<EOF
{
  "action": "view_part_details",
  "context": {"yacht_id": "$YACHT_ID"},
  "payload": {"part_id": "$PART_ID"}
}
EOF
)
    else
        # consume_part (small quantity)
        PAYLOAD=$(cat <<EOF
{
  "action": "consume_part",
  "context": {"yacht_id": "$YACHT_ID"},
  "payload": {
    "part_id": "$PART_ID",
    "quantity": 1
  }
}
EOF
)
    fi

    # Make request
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute" 2>/dev/null || echo "000")

    local end_time=$(date +%s%3N)
    local latency=$((end_time - start_time))

    # Record results
    TOTAL_REQUESTS=$((TOTAL_REQUESTS + 1))
    LATENCIES+=($latency)

    # Categorize by status code
    if [ "$STATUS_CODE" -ge 200 ] && [ "$STATUS_CODE" -lt 300 ]; then
        TWO_XX_COUNT=$((TWO_XX_COUNT + 1))
        SUCCESSFUL_REQUESTS=$((SUCCESSFUL_REQUESTS + 1))
    elif [ "$STATUS_CODE" -ge 400 ] && [ "$STATUS_CODE" -lt 500 ]; then
        FOUR_XX_COUNT=$((FOUR_XX_COUNT + 1))
        # 409 is acceptable (insufficient stock), others might be errors
        if [ "$STATUS_CODE" -eq 409 ]; then
            SUCCESSFUL_REQUESTS=$((SUCCESSFUL_REQUESTS + 1))
        else
            FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
        fi
    elif [ "$STATUS_CODE" -ge 500 ] && [ "$STATUS_CODE" -lt 600 ]; then
        FIVE_XX_COUNT=$((FIVE_XX_COUNT + 1))
        FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
        log_error "5xx error detected: $STATUS_CODE"
    else
        FAILED_REQUESTS=$((FAILED_REQUESTS + 1))
    fi

    echo "$STATUS_CODE,$latency"
}

# =============================================================================
# Calculate Percentiles
# =============================================================================
calculate_percentiles() {
    local sorted=($(printf '%s\n' "${LATENCIES[@]}" | sort -n))
    local count=${#sorted[@]}

    if [ $count -eq 0 ]; then
        echo "0,0,0,0"
        return
    fi

    local p50_idx=$((count * 50 / 100))
    local p95_idx=$((count * 95 / 100))
    local p99_idx=$((count * 99 / 100))

    local p50=${sorted[$p50_idx]}
    local p95=${sorted[$p95_idx]}
    local p99=${sorted[$p99_idx]}

    # Calculate average
    local sum=0
    for latency in "${sorted[@]}"; do
        sum=$((sum + latency))
    done
    local avg=$((sum / count))

    echo "$avg,$p50,$p95,$p99"
}

# =============================================================================
# Check Gates
# =============================================================================
check_gates() {
    local error_rate=0
    if [ $TOTAL_REQUESTS -gt 0 ]; then
        error_rate=$(awk "BEGIN {printf \"%.2f\", ($FAILED_REQUESTS/$TOTAL_REQUESTS)*100}")
    fi

    local gate_pass=true

    # Hard Gate 1: Zero 5xx
    if [ $FIVE_XX_COUNT -gt 0 ]; then
        log_error "GATE FAILURE: 5xx count = $FIVE_XX_COUNT (must be 0)"
        gate_pass=false
    fi

    # Hard Gate 2: Error rate < 2%
    if (( $(echo "$error_rate > 2.0" | bc -l) )); then
        log_error "GATE FAILURE: Error rate = ${error_rate}% (must be < 2%)"
        gate_pass=false
    fi

    # Check for 5xx spike (>5 in 5 minutes)
    # TODO: Implement sliding window check

    if [ "$gate_pass" = true ]; then
        log_info "Gates: PASS (5xx=$FIVE_XX_COUNT, error_rate=${error_rate}%)"
    else
        log_error "Gates: FAIL - Canary should be rolled back"
    fi

    echo "$gate_pass"
}

# =============================================================================
# Print Status
# =============================================================================
print_status() {
    local elapsed_minutes=$1
    local percentiles=$(calculate_percentiles)
    IFS=',' read -r avg p50 p95 p99 <<< "$percentiles"

    local success_rate=0
    local error_rate=0
    if [ $TOTAL_REQUESTS -gt 0 ]; then
        success_rate=$(awk "BEGIN {printf \"%.1f\", ($SUCCESSFUL_REQUESTS/$TOTAL_REQUESTS)*100}")
        error_rate=$(awk "BEGIN {printf \"%.2f\", ($FAILED_REQUESTS/$TOTAL_REQUESTS)*100}")
    fi

    echo ""
    echo "============================================================================="
    echo "Canary Monitor - ${elapsed_minutes}/${DURATION_MINUTES} minutes"
    echo "============================================================================="
    echo "Requests:"
    echo "  Total:      $TOTAL_REQUESTS"
    echo "  2xx:        $TWO_XX_COUNT"
    echo "  4xx:        $FOUR_XX_COUNT"
    echo "  5xx:        $FIVE_XX_COUNT"
    echo ""
    echo "Success Rate: ${success_rate}%"
    echo "Error Rate:   ${error_rate}%"
    echo ""
    echo "Latency (ms):"
    echo "  Average:    $avg"
    echo "  P50:        $p50"
    echo "  P95:        $p95"
    echo "  P99:        $p99"
    echo ""
    echo "Gates:"
    echo "  5xx = 0:           $([ $FIVE_XX_COUNT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
    echo "  Error rate < 2%:   $([ $(echo "$error_rate < 2.0" | bc -l) -eq 1 ] && echo '✓ PASS' || echo '✗ FAIL')"
    echo "============================================================================="
}

# =============================================================================
# Main Monitoring Loop
# =============================================================================
main() {
    echo "============================================================================="
    echo "Part Lens v2 - Canary Monitoring"
    echo "============================================================================="
    echo "API Base:       $API_BASE"
    echo "Duration:       $DURATION_MINUTES minutes"
    echo "Sample Interval: $SAMPLE_INTERVAL seconds"
    echo "Output File:    $OUTPUT_FILE"
    echo "============================================================================="
    echo ""

    local start_time=$(date +%s)
    local end_time=$((start_time + DURATION_MINUTES * 60))

    mkdir -p "$(dirname "$OUTPUT_FILE")"

    # Monitoring loop
    while [ $(date +%s) -lt $end_time ]; do
        # Make sample request
        make_sample_request > /dev/null

        # Check gates every 5 minutes
        local elapsed=$(($(date +%s) - start_time))
        local elapsed_minutes=$((elapsed / 60))

        if [ $((elapsed % 300)) -eq 0 ] && [ $elapsed -gt 0 ]; then
            print_status $elapsed_minutes

            # Check if gates are failing
            if [ "$(check_gates)" = "false" ]; then
                log_error "Gate failure detected - consider rollback"
            fi
        fi

        sleep $SAMPLE_INTERVAL
    done

    # Final report
    print_status $DURATION_MINUTES

    # Calculate final metrics
    local percentiles=$(calculate_percentiles)
    IFS=',' read -r avg p50 p95 p99 <<< "$percentiles"

    local success_rate=$(awk "BEGIN {printf \"%.2f\", ($SUCCESSFUL_REQUESTS/$TOTAL_REQUESTS)*100}")
    local error_rate=$(awk "BEGIN {printf \"%.2f\", ($FAILED_REQUESTS/$TOTAL_REQUESTS)*100}")

    # Write JSON report
    cat > "$OUTPUT_FILE" <<EOF
{
  "canary_monitoring": "Part Lens v2",
  "duration_minutes": $DURATION_MINUTES,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "requests": {
    "total": $TOTAL_REQUESTS,
    "successful": $SUCCESSFUL_REQUESTS,
    "failed": $FAILED_REQUESTS,
    "2xx": $TWO_XX_COUNT,
    "4xx": $FOUR_XX_COUNT,
    "5xx": $FIVE_XX_COUNT
  },
  "metrics": {
    "success_rate": $success_rate,
    "error_rate": $error_rate
  },
  "latency_ms": {
    "average": $avg,
    "p50": $p50,
    "p95": $p95,
    "p99": $p99
  },
  "gates": {
    "zero_5xx": $([ $FIVE_XX_COUNT -eq 0 ] && echo 'true' || echo 'false'),
    "error_rate_below_2pct": $([ $(echo "$error_rate < 2.0" | bc -l) -eq 1 ] && echo 'true' || echo 'false'),
    "overall_pass": $([ $FIVE_XX_COUNT -eq 0 ] && [ $(echo "$error_rate < 2.0" | bc -l) -eq 1 ] && echo 'true' || echo 'false')
  }
}
EOF

    log_info "Report written to: $OUTPUT_FILE"

    # Exit status
    if [ $FIVE_XX_COUNT -eq 0 ] && [ $(echo "$error_rate < 2.0" | bc -l) -eq 1 ]; then
        echo -e "${GREEN}✓ CANARY MONITORING PASSED${NC}"
        exit 0
    else
        echo -e "${RED}✗ CANARY MONITORING FAILED - ROLLBACK RECOMMENDED${NC}"
        exit 1
    fi
}

main "$@"
