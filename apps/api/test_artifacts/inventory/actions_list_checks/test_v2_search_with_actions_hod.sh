#!/bin/bash
# Test POST /v2/search to verify context + actions are included (HOD role)

API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Testing POST /v2/search with HOD (chief_engineer) role (parts query)"
echo "=========================================================================="
echo "Query: 'parts low in stock'"
echo

curl -sS -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  "$API_URL/v2/search" \
  -d '{"query_text":"parts low in stock"}' | jq '{
    success,
    total_count,
    context: .context,
    actions: .actions | map({
      action_id,
      label,
      variant
    })
  }'

echo
echo "Expected:"
echo "- success: true"
echo "- context.domain: \"parts\""
echo "- context.intent: \"READ\""
echo "- context.mode: \"hybrid\""
echo "- actions: 8 items (HOD gets READ + MUTATE actions)"
echo "  - check_stock_level (READ)"
echo "  - log_part_usage (MUTATE)"
echo "  - consume_part (MUTATE)"
echo "  - receive_part (MUTATE)"
echo "  - transfer_part (MUTATE)"
echo "  - view_part_details (READ)"
echo "  - generate_part_labels (MUTATE)"
echo "  - request_label_output (MUTATE)"
