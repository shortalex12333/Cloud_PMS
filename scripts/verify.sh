#!/bin/bash

# verify.sh - Main verification automation script
# Usage: ./scripts/verify.sh [action_name]

set -e

ACTION=$1

if [ -z "$ACTION" ]; then
  echo "❌ Error: Action name required"
  echo "Usage: ./scripts/verify.sh [action_name]"
  echo "Example: ./scripts/verify.sh create_work_order"
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 Verification System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Action: $ACTION"
echo ""

# Load context
CONTEXT_FILE=".verification_context"
if [ ! -f "$CONTEXT_FILE" ]; then
  echo "{\"phase\":\"1\",\"actions_verified\":0,\"current_action\":\"$ACTION\"}" > $CONTEXT_FILE
fi

# Find handler
echo "🔍 Finding handler..."
HANDLER_LINE=$(grep -n "action == \"$ACTION\"" apps/api/routes/p0_actions_routes.py | head -1 | cut -d: -f1)

if [ -z "$HANDLER_LINE" ]; then
  echo "❌ Handler not found in p0_actions_routes.py"
  echo "   Searched for: action == \"$ACTION\""
  exit 1
fi

echo "✅ Handler found at line: $HANDLER_LINE"

# Find test
echo ""
echo "🔍 Finding test..."
TEST_FILE=$(find tests/e2e -name "*${ACTION}*.spec.ts" 2>/dev/null | head -1)

if [ -z "$TEST_FILE" ]; then
  echo "⚠️  Test not found for: $ACTION"
  echo "   Expected: tests/e2e/*${ACTION}*.spec.ts"
  TEST_STATUS="NOT_FOUND"
else
  echo "✅ Test found: $TEST_FILE"
  TEST_STATUS="FOUND"
fi

# Create verification file from template
echo ""
echo "📝 Creating verification file..."
VERIFY_FILE="_VERIFICATION/verify_${ACTION}.md"

if [ -f "$VERIFY_FILE" ]; then
  echo "⚠️  Verification file already exists: $VERIFY_FILE"
  echo "   Remove it first if you want to regenerate"
else
  # Copy template and pre-fill
  cp QUICK_VERIFY_TEMPLATE.md "$VERIFY_FILE"

  # Replace placeholders
  sed -i '' "s/\[ACTION_NAME\]/$ACTION/g" "$VERIFY_FILE"
  sed -i '' "s/\[HANDLER_LINE\]/$HANDLER_LINE/g" "$VERIFY_FILE"
  sed -i '' "s|\[TEST_FILE\]|$TEST_FILE|g" "$VERIFY_FILE"

  echo "✅ Verification file created: $VERIFY_FILE"
fi

# Run test if found
if [ "$TEST_STATUS" = "FOUND" ]; then
  echo ""
  echo "🧪 Running test..."
  echo ""

  if npx playwright test "$TEST_FILE" --reporter=list 2>&1 | tee /tmp/test_output.txt; then
    TEST_RESULT="PASS"
    echo ""
    echo "✅ Test PASSED"
  else
    TEST_RESULT="FAIL"
    echo ""
    echo "❌ Test FAILED"
    echo "   (This is OK - we're observing, not fixing)"
  fi

  # Extract response for template
  # (Would parse test output here in real implementation)
fi

# Update context
echo ""
echo "💾 Updating context..."
ACTIONS_VERIFIED=$(grep -c "Status: ✅ Verified" _VERIFICATION/verify_*.md 2>/dev/null || echo 0)
cat > $CONTEXT_FILE << EOF
{
  "phase": "1",
  "actions_verified": $ACTIONS_VERIFIED,
  "current_action": "$ACTION",
  "last_test_result": "$TEST_RESULT",
  "last_handler_line": $HANDLER_LINE
}
EOF

# Update dashboard
./scripts/update_dashboard.sh

echo "✅ Context updated"

# Show next steps
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open verification file:"
echo "   $VERIFY_FILE"
echo ""
echo "2. Fill in the 6 proofs (show actual query results)"
echo ""
echo "3. Document gaps found"
echo ""
echo "4. When done, run:"
echo "   ./scripts/next_action.sh"
echo ""
echo "⏱️  Timer: 60 minutes (set your own timer)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
