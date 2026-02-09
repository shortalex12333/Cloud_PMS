#!/bin/bash
# Test GET /v1/actions/list with crew role and parts domain

API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Testing GET /v1/actions/list with CREW role (parts domain)"
echo "=========================================================================="
echo

curl -sS -H "Authorization: Bearer $CREW_JWT" \
  "$API_URL/v1/actions/list?domain=parts" | jq '{
    role,
    total_count,
    actions: .actions | map({
      action_id,
      label,
      variant,
      required_fields
    })
  }'

echo
echo "Expected:"
echo "- role: \"crew\""
echo "- total_count: 2 (only READ actions)"
echo "- actions: check_stock_level, view_part_details"
