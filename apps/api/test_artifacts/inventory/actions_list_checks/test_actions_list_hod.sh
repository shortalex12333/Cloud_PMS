#!/bin/bash
# Test GET /v1/actions/list with HOD role and parts domain

API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Testing GET /v1/actions/list with HOD (chief_engineer) role (parts domain)"
echo "=========================================================================="
echo

curl -sS -H "Authorization: Bearer $HOD_JWT" \
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
echo "- role: \"chief_engineer\""
echo "- total_count: 8 (READ + MUTATE actions)"
echo "- actions: check_stock_level, log_part_usage, consume_part, receive_part, transfer_part, view_part_details, generate_part_labels, request_label_output"
