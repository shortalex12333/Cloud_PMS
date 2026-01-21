#!/bin/bash
#
# DIAGNOSTIC RUNNER
# =================
# Captures baseline, tracks progress, detects regressions
#
# Usage:
#   ./scripts/diagnostic_runner.sh baseline    # Save current state
#   ./scripts/diagnostic_runner.sh check       # Compare to last baseline
#   ./scripts/diagnostic_runner.sh history     # Show progress over time
#

DIAGNOSTIC_DIR="test-results/diagnostic"
HISTORY_FILE="$DIAGNOSTIC_DIR/history.jsonl"

mkdir -p "$DIAGNOSTIC_DIR"

case "$1" in
  baseline)
    echo "📊 Running diagnostic baseline..."

    # Rename latest to previous for regression comparison
    if [ -f "$DIAGNOSTIC_DIR/baseline_latest.json" ]; then
      cp "$DIAGNOSTIC_DIR/baseline_latest.json" "$DIAGNOSTIC_DIR/baseline_previous.json"
    fi

    # Run the diagnostic test
    npx playwright test diagnostic_baseline.spec.ts --project=e2e-chromium 2>&1 | tee /tmp/diagnostic_output.txt

    # Extract key metrics for history
    if [ -f "$DIAGNOSTIC_DIR/baseline_latest.json" ]; then
      TIMESTAMP=$(jq -r '.meta.timestamp' "$DIAGNOSTIC_DIR/baseline_latest.json")
      WORKING=$(jq -r '.summary.working' "$DIAGNOSTIC_DIR/baseline_latest.json")
      TOTAL=$(jq -r '.meta.total_actions' "$DIAGNOSTIC_DIR/baseline_latest.json")
      HASH=$(jq -r '.baseline_hash' "$DIAGNOSTIC_DIR/baseline_latest.json")

      # Append to history
      echo "{\"timestamp\":\"$TIMESTAMP\",\"working\":$WORKING,\"total\":$TOTAL,\"hash\":\"$HASH\"}" >> "$HISTORY_FILE"

      echo ""
      echo "✅ Baseline saved!"
      echo "   Working: $WORKING/$TOTAL"
      echo "   Hash: $HASH"
    fi
    ;;

  check)
    echo "🔄 Checking for regressions..."

    if [ ! -f "$DIAGNOSTIC_DIR/baseline_previous.json" ]; then
      echo "❌ No previous baseline found. Run 'baseline' first."
      exit 1
    fi

    # Run new diagnostic
    npx playwright test diagnostic_baseline.spec.ts --project=e2e-chromium 2>&1 | grep -E "(✓|✗|○|◐|REGRESSION|IMPROVEMENT|HEALTH)"
    ;;

  history)
    echo "📈 Progress History:"
    echo ""

    if [ ! -f "$HISTORY_FILE" ]; then
      echo "No history yet. Run 'baseline' to start tracking."
      exit 0
    fi

    echo "Timestamp                    | Working | Total | Health"
    echo "-----------------------------|---------|-------|-------"

    while IFS= read -r line; do
      TS=$(echo "$line" | jq -r '.timestamp' | cut -c1-19)
      W=$(echo "$line" | jq -r '.working')
      T=$(echo "$line" | jq -r '.total')
      PCT=$((W * 100 / T))

      printf "%-28s | %7s | %5s | %3s%%\n" "$TS" "$W" "$T" "$PCT"
    done < "$HISTORY_FILE"
    ;;

  summary)
    echo "📋 Current State Summary:"
    echo ""

    if [ ! -f "$DIAGNOSTIC_DIR/baseline_latest.json" ]; then
      echo "No baseline found. Run 'baseline' first."
      exit 1
    fi

    echo "BY CATEGORY:"
    jq -r '.summary | to_entries | .[] | "  \(.key): \(.value)"' "$DIAGNOSTIC_DIR/baseline_latest.json"

    echo ""
    echo "BY CLUSTER:"
    jq -r '.by_cluster | to_entries | .[] | "  \(.key): \(.value.working)/\(.value.total) (\(.value.coverage_percent)%)"' "$DIAGNOSTIC_DIR/baseline_latest.json"

    echo ""
    echo "FIX PRIORITIES:"
    echo "  CRITICAL: $(jq -r '.fix_priority.critical | length' "$DIAGNOSTIC_DIR/baseline_latest.json") actions"
    echo "  HIGH:     $(jq -r '.fix_priority.high | length' "$DIAGNOSTIC_DIR/baseline_latest.json") actions"
    echo "  MEDIUM:   $(jq -r '.fix_priority.medium | length' "$DIAGNOSTIC_DIR/baseline_latest.json") actions"
    echo "  LOW:      $(jq -r '.fix_priority.low | length' "$DIAGNOSTIC_DIR/baseline_latest.json") actions"
    ;;

  *)
    echo "Diagnostic Runner"
    echo ""
    echo "Usage:"
    echo "  $0 baseline   - Run diagnostic and save baseline"
    echo "  $0 check      - Run diagnostic and compare to previous"
    echo "  $0 history    - Show progress over time"
    echo "  $0 summary    - Show current state summary"
    ;;
esac
