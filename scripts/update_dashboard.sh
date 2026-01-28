#!/bin/bash

# update_dashboard.sh - Update VERIFICATION_DASHBOARD.md with current progress
# Called automatically by verify.sh and next_action.sh

set -e

DASHBOARD="VERIFICATION_DASHBOARD.md"
CONTEXT_FILE=".verification_context"

if [ ! -f "$CONTEXT_FILE" ]; then
  echo "No context file found, skipping dashboard update"
  exit 0
fi

# Extract context
PHASE=$(grep -o '"phase": *"[^"]*"' $CONTEXT_FILE | cut -d'"' -f4)
ACTIONS_VERIFIED=$(grep -o '"actions_verified": *[0-9]*' $CONTEXT_FILE | grep -o '[0-9]*')
CURRENT_ACTION=$(grep -o '"current_action": *"[^"]*"' $CONTEXT_FILE | cut -d'"' -f4)

# Get phase 1 actions
PHASE_1_ACTIONS=(
  "create_work_order"
  "assign_work_order"
  "add_note"
  "mark_fault_resolved"
  "get_work_order_details"
)

# Build action status
ACTION_STATUS=""
for action in "${PHASE_1_ACTIONS[@]}"; do
  VERIFY_FILE="_VERIFICATION/verify_${action}.md"
  if [ -f "$VERIFY_FILE" ] && grep -q "Status: ✅ Verified" "$VERIFY_FILE" 2>/dev/null; then
    ACTION_STATUS="${ACTION_STATUS}- [x] $action ✅\n"
  elif [ "$action" = "$CURRENT_ACTION" ]; then
    ACTION_STATUS="${ACTION_STATUS}- [ ] $action ⏳ (current)\n"
  else
    ACTION_STATUS="${ACTION_STATUS}- [ ] $action\n"
  fi
done

# Determine phase message
if [ "$PHASE" = "1" ]; then
  PHASE_MSG="Phase 1: Observation (Verify 5 actions)"
  NEXT_STEP="Fill in verification template for current action"
elif [ "$PHASE" = "1_COMPLETE" ]; then
  PHASE_MSG="Phase 1: Complete ✅"
  NEXT_STEP="Launch Agent 3: Pattern Analyst"
elif [ "$PHASE" = "2" ]; then
  PHASE_MSG="Phase 2: Pattern Analysis"
  NEXT_STEP="Categorize patterns in PATTERN_ANALYSIS.md"
elif [ "$PHASE" = "2_COMPLETE" ]; then
  PHASE_MSG="Phase 2: Complete ✅"
  NEXT_STEP="Launch Agent 4: Bulk Fixer"
elif [ "$PHASE" = "3" ]; then
  PHASE_MSG="Phase 3: Bulk Fixes"
  NEXT_STEP="Fix patterns in bulk"
elif [ "$PHASE" = "3_COMPLETE" ]; then
  PHASE_MSG="Phase 3: Complete ✅"
  NEXT_STEP="Verification complete! 🎉"
else
  PHASE_MSG="Unknown phase: $PHASE"
  NEXT_STEP="Check .verification_context"
fi

# Write dashboard
cat > $DASHBOARD << EOF
# Verification Dashboard

**Last updated:** $(date +"%Y-%m-%d %H:%M:%S")

---

## 📊 Current Status

**Phase:** $PHASE_MSG
**Progress:** $ACTIONS_VERIFIED/5 actions verified (Phase 1)
**Current action:** ${CURRENT_ACTION:-None}

---

## ✅ Phase 1 Actions (5 total)

$ACTION_STATUS

---

## 🎯 Next Step

$NEXT_STEP

---

## 📁 Quick Links

**Verification files:**
- [Phase 1 Findings](./_VERIFICATION/PHASE_1_FINDINGS.md)
- [Related Issues](./_VERIFICATION/RELATED_ISSUES.md)
- [Pattern Analysis](./_VERIFICATION/PATTERN_ANALYSIS.md)
- [Pattern Fixes](./_VERIFICATION/PATTERN_FIXES.md)

**Current verification:**
- [verify_${CURRENT_ACTION}.md](./_VERIFICATION/verify_${CURRENT_ACTION}.md)

**Guides:**
- [Multi-Agent Plan](./MULTI_AGENT_VERIFICATION_PLAN.md)
- [Methodology](./VERIFICATION_METHODOLOGY.md)
- [Quick Start](./QUICK_START_VERIFICATION.md)

---

## 🚀 Commands

**Start verification:**
\`\`\`bash
./scripts/verify.sh [action_name]
\`\`\`

**Advance to next action:**
\`\`\`bash
./scripts/next_action.sh
\`\`\`

**View progress:**
\`\`\`bash
cat VERIFICATION_DASHBOARD.md
\`\`\`

---

**Auto-updated by scripts/update_dashboard.sh**
EOF
