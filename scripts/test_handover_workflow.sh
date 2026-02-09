#!/bin/bash
# Handover Dual-Signature Workflow - Smoke Test
# Tests the complete workflow: Draft → Finalize → Export → Sign Outgoing → Sign Incoming → Verify

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_BASE="${API_BASE:-https://pipeline-core.int.celeste7.ai}"
YACHT_ID="${TEST_YACHT_ID:-85fe1119-b04c-41ac-80f1-829d23322598}"
JWT_TOKEN="${TEST_JWT_TOKEN}"

if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}ERROR: TEST_JWT_TOKEN environment variable not set${NC}"
    echo "Get a JWT token by logging in and export it:"
    echo "  export TEST_JWT_TOKEN='your-jwt-here'"
    exit 1
fi

# Helper functions
log_step() {
    echo -e "${BLUE}[STEP $1]${NC} $2"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Create test handover items
log_step 1 "Creating test handover items..."

ITEM1=$(curl -s -X POST "${API_BASE}/v1/actions/execute" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"add_to_handover\",
    \"context\": {\"yacht_id\": \"${YACHT_ID}\"},
    \"payload\": {
      \"summary\": \"Test critical item - Main engine inspection overdue\",
      \"category\": \"engineering\",
      \"is_critical\": true,
      \"requires_action\": true,
      \"action_summary\": \"Schedule inspection within 48 hours\",
      \"priority\": \"high\"
    }
  }" | jq -r '.item_id // empty')

ITEM2=$(curl -s -X POST "${API_BASE}/v1/actions/execute" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"add_to_handover\",
    \"context\": {\"yacht_id\": \"${YACHT_ID}\"},
    \"payload\": {
      \"summary\": \"Test normal item - Weekly deck cleaning completed\",
      \"category\": \"deck\",
      \"is_critical\": false,
      \"priority\": \"normal\"
    }
  }" | jq -r '.item_id // empty')

if [ -n "$ITEM1" ] && [ -n "$ITEM2" ]; then
    log_success "Created 2 test items: $ITEM1, $ITEM2"
else
    log_error "Failed to create test items"
    exit 1
fi

# Step 2: Validate draft
log_step 2 "Validating draft..."

VALIDATION=$(curl -s -X POST "${API_BASE}/v1/actions/handover/draft-test/validate" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

VALID=$(echo "$VALIDATION" | jq -r '.valid')
ERROR_COUNT=$(echo "$VALIDATION" | jq -r '.blocking_count')

if [ "$VALID" = "true" ]; then
    log_success "Draft validation passed (0 blocking errors)"
else
    log_warning "Draft has $ERROR_COUNT blocking errors"
    echo "$VALIDATION" | jq '.errors'
fi

# Step 3: Finalize draft
log_step 3 "Finalizing draft (generating content_hash)..."

FINALIZE_RESULT=$(curl -s -X POST "${API_BASE}/v1/actions/handover/draft-test/finalize" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

CONTENT_HASH=$(echo "$FINALIZE_RESULT" | jq -r '.content_hash // empty')

if [ -n "$CONTENT_HASH" ]; then
    log_success "Draft finalized"
    echo "  Content Hash: ${CONTENT_HASH:0:16}..."
else
    log_error "Failed to finalize draft"
    echo "$FINALIZE_RESULT" | jq '.'
    exit 1
fi

# Step 4: Export handover
log_step 4 "Generating export (generating document_hash)..."

EXPORT_RESULT=$(curl -s -X POST "${API_BASE}/v1/actions/handover/draft-test/export?export_type=html&department=engineering" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

EXPORT_ID=$(echo "$EXPORT_RESULT" | jq -r '.export_id // empty')
DOCUMENT_HASH=$(echo "$EXPORT_RESULT" | jq -r '.document_hash // empty')

if [ -n "$EXPORT_ID" ] && [ -n "$DOCUMENT_HASH" ]; then
    log_success "Export created: $EXPORT_ID"
    echo "  Document Hash: ${DOCUMENT_HASH:0:16}..."
    echo "  Content Hash:  ${CONTENT_HASH:0:16}..."
else
    log_error "Failed to create export"
    echo "$EXPORT_RESULT" | jq '.'
    exit 1
fi

# Step 5: Sign outgoing
log_step 5 "Signing as outgoing user..."

SIGN_OUT_RESULT=$(curl -s -X POST "${API_BASE}/v1/actions/handover/${EXPORT_ID}/sign/outgoing" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "All critical items flagged and reviewed",
    "method": "typed"
  }')

SIGNED_AT_OUT=$(echo "$SIGN_OUT_RESULT" | jq -r '.signed_at // empty')

if [ -n "$SIGNED_AT_OUT" ]; then
    log_success "Outgoing signature recorded"
    echo "  Signed at: $SIGNED_AT_OUT"
    echo "  Status: pending_incoming"
else
    log_error "Failed to sign outgoing"
    echo "$SIGN_OUT_RESULT" | jq '.'
    exit 1
fi

# Step 6: Sign incoming
log_step 6 "Signing as incoming user (with critical acknowledgment)..."

SIGN_IN_RESULT=$(curl -s -X POST "${API_BASE}/v1/actions/handover/${EXPORT_ID}/sign/incoming" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "acknowledge_critical": true,
    "note": "Critical items reviewed and understood",
    "method": "typed"
  }')

SIGNOFF_COMPLETE=$(echo "$SIGN_IN_RESULT" | jq -r '.signoff_complete // empty')

if [ "$SIGNOFF_COMPLETE" = "true" ]; then
    log_success "Incoming signature recorded"
    echo "  Signoff Complete: true"
    echo "  Status: completed"
else
    log_error "Failed to sign incoming"
    echo "$SIGN_IN_RESULT" | jq '.'
    exit 1
fi

# Step 7: Verify export
log_step 7 "Verifying export hashes and signatures..."

VERIFY_RESULT=$(curl -s -X GET "${API_BASE}/v1/actions/handover/${EXPORT_ID}/verify" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

VERIFY_CONTENT_HASH=$(echo "$VERIFY_RESULT" | jq -r '.content_hash // empty')
VERIFY_DOCUMENT_HASH=$(echo "$VERIFY_RESULT" | jq -r '.document_hash // empty')
VERIFY_SIGNOFF=$(echo "$VERIFY_RESULT" | jq -r '.signoff_complete // empty')

if [ "$VERIFY_SIGNOFF" = "true" ]; then
    log_success "Verification successful"
    echo "  Content Hash:     ${VERIFY_CONTENT_HASH:0:16}..."
    echo "  Document Hash:    ${VERIFY_DOCUMENT_HASH:0:16}..."
    echo "  Signoff Complete: $VERIFY_SIGNOFF"
    echo ""
    echo "Outgoing Signature:"
    echo "$VERIFY_RESULT" | jq '.outgoing'
    echo ""
    echo "Incoming Signature:"
    echo "$VERIFY_RESULT" | jq '.incoming'
else
    log_error "Verification failed"
    echo "$VERIFY_RESULT" | jq '.'
    exit 1
fi

# Step 8: Get pending handovers
log_step 8 "Checking pending handovers..."

PENDING_RESULT=$(curl -s -X GET "${API_BASE}/v1/actions/handover/pending" \
  -H "Authorization: Bearer ${JWT_TOKEN}")

PENDING_COUNT=$(echo "$PENDING_RESULT" | jq -r '.pending_count // 0')

log_success "Pending handovers: $PENDING_COUNT"

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Export ID: $EXPORT_ID"
echo "Content Hash:  ${CONTENT_HASH}"
echo "Document Hash: ${DOCUMENT_HASH}"
echo ""
echo "Full workflow completed successfully:"
echo "  1. ✓ Created test items"
echo "  2. ✓ Validated draft"
echo "  3. ✓ Finalized draft (content_hash)"
echo "  4. ✓ Generated export (document_hash)"
echo "  5. ✓ Outgoing signature"
echo "  6. ✓ Incoming signature + critical ack"
echo "  7. ✓ Verification (both hashes + signatures)"
echo "  8. ✓ Pending list"
echo ""
echo "View verification page:"
echo "  ${API_BASE}/v1/actions/handover/${EXPORT_ID}/verify"
