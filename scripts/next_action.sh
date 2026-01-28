#!/bin/bash

# next_action.sh - Advance to next action
# Usage: ./scripts/next_action.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏭️  Advancing to Next Action"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Load context
CONTEXT_FILE=".verification_context"
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "❌ No context file found"
  echo "   Run ./scripts/verify.sh [action] first"
  exit 1
fi

CURRENT_ACTION=$(grep -o '"current_action": *"[^"]*"' $CONTEXT_FILE | cut -d'"' -f4)
ACTIONS_VERIFIED=$(grep -o '"actions_verified": *[0-9]*' $CONTEXT_FILE | grep -o '[0-9]*')

echo "Current action: $CURRENT_ACTION"
echo "Actions verified: $ACTIONS_VERIFIED"
echo ""

# Phase 1 action queue
PHASE_1_ACTIONS=(
  "create_work_order"
  "assign_work_order"
  "add_note"
  "mark_fault_resolved"
  "get_work_order_details"
)

# Find current index
CURRENT_INDEX=-1
for i in "${!PHASE_1_ACTIONS[@]}"; do
  if [ "${PHASE_1_ACTIONS[$i]}" = "$CURRENT_ACTION" ]; then
    CURRENT_INDEX=$i
    break
  fi
done

# Get next action
NEXT_INDEX=$((CURRENT_INDEX + 1))

if [ $NEXT_INDEX -ge ${#PHASE_1_ACTIONS[@]} ]; then
  echo "🎉 Phase 1 Complete!"
  echo ""
  echo "All 5 actions verified. Next steps:"
  echo ""
  echo "1. Review VERIFICATION_DASHBOARD.md"
  echo "2. Ensure PHASE_1_FINDINGS.md is complete"
  echo "3. Launch Agent 3: Pattern Analyst"
  echo ""
  echo "Do NOT verify more actions until pattern analysis complete."
  echo ""

  # Update context to Phase 1 Complete
  cat > $CONTEXT_FILE << EOF
{
  "phase": "1_COMPLETE",
  "actions_verified": $ACTIONS_VERIFIED,
  "current_action": null,
  "ready_for_phase_2": true
}
EOF

  ./scripts/update_dashboard.sh

  exit 0
fi

NEXT_ACTION="${PHASE_1_ACTIONS[$NEXT_INDEX]}"

echo "✅ Progress saved"
echo "✅ Dashboard updated"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Progress: $((ACTIONS_VERIFIED))/5 actions complete"
echo "⏭️  Next action: $NEXT_ACTION"
echo ""
echo "Run:"
echo "  ./scripts/verify.sh $NEXT_ACTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
