#!/bin/bash
# Parity verification: Test all 3 search endpoints with same queries
# Verify parts routing, context, and actions are consistent

OUTPUT_DIR="/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity"
API_URL="${API_URL:-https://pipeline-core.int.celeste7.ai}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# Test queries
QUERIES=("parts low in stock" "oil filters" "spare parts inventory")
ROLES=("crew" "hod")

echo "=========================================================================="
echo "SEARCH ENDPOINT PARITY VERIFICATION"
echo "Testing /v1/search, /v2/search, and /search with same queries"
echo "=========================================================================="
echo

for role in "${ROLES[@]}"; do
  if [ "$role" == "crew" ]; then
    JWT="$CREW_JWT"
  else
    JWT="$HOD_JWT"
  fi

  for query in "${QUERIES[@]}"; do
    # Sanitize query for filename
    filename=$(echo "$query" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    echo "Testing: role=$role, query=\"$query\""
    echo "----------------------------------------------------------------------"

    # Test /v1/search
    echo "  /v1/search..."
    curl -sS -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      "$API_URL/v1/search" \
      -d "{\"query\":\"$query\"}" \
      > "$OUTPUT_DIR/v1_${role}_${filename}.json"

    # Test /v2/search
    echo "  /v2/search..."
    curl -sS -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      -H "X-Yacht-ID: $YACHT_ID" \
      "$API_URL/v2/search" \
      -d "{\"query_text\":\"$query\"}" \
      > "$OUTPUT_DIR/v2_${role}_${filename}.json"

    # Test /search (fusion)
    echo "  /search..."
    curl -sS -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      "$API_URL/search" \
      -d "{\"query\":\"$query\",\"limit\":20}" \
      > "$OUTPUT_DIR/fusion_${role}_${filename}.json"

    echo "  ✓ Done"
    echo
  done
done

echo "=========================================================================="
echo "ANALYZING PARITY"
echo "=========================================================================="
echo

# Analyze context presence
echo "Context metadata presence:"
echo "-------------------------"
for role in "${ROLES[@]}"; do
  for query in "${QUERIES[@]}"; do
    filename=$(echo "$query" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    v1_context=$(jq -r '.context.domain // "MISSING"' "$OUTPUT_DIR/v1_${role}_${filename}.json" 2>/dev/null)
    v2_context=$(jq -r '.context.domain // "MISSING"' "$OUTPUT_DIR/v2_${role}_${filename}.json" 2>/dev/null)
    fusion_context=$(jq -r '.context.domain // "MISSING"' "$OUTPUT_DIR/fusion_${role}_${filename}.json" 2>/dev/null)

    echo "$role | $query:"
    echo "  /v1/search context.domain: $v1_context"
    echo "  /v2/search context.domain: $v2_context"
    echo "  /search context.domain: $fusion_context"
  done
done
echo

# Analyze actions presence
echo "Actions array presence:"
echo "----------------------"
for role in "${ROLES[@]}"; do
  for query in "${QUERIES[@]}"; do
    filename=$(echo "$query" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    v1_actions=$(jq -r '.actions // [] | length' "$OUTPUT_DIR/v1_${role}_${filename}.json" 2>/dev/null)
    v2_actions=$(jq -r '.actions // [] | length' "$OUTPUT_DIR/v2_${role}_${filename}.json" 2>/dev/null)
    fusion_actions=$(jq -r '.actions // [] | length' "$OUTPUT_DIR/fusion_${role}_${filename}.json" 2>/dev/null)

    echo "$role | $query:"
    echo "  /v1/search actions count: $v1_actions"
    echo "  /v2/search actions count: $v2_actions"
    echo "  /search actions count: $fusion_actions"
  done
done
echo

# Analyze result types
echo "Result types (first result):"
echo "---------------------------"
for role in "${ROLES[@]}"; do
  for query in "${QUERIES[@]}"; do
    filename=$(echo "$query" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    v1_type=$(jq -r '.cards[0].type // .results[0].domain // "NONE"' "$OUTPUT_DIR/v1_${role}_${filename}.json" 2>/dev/null)
    v2_type=$(jq -r '.results[0].domain // "NONE"' "$OUTPUT_DIR/v2_${role}_${filename}.json" 2>/dev/null)
    fusion_type=$(jq -r '.results[0].object_type // "NONE"' "$OUTPUT_DIR/fusion_${role}_${filename}.json" 2>/dev/null)

    echo "$role | $query:"
    echo "  /v1/search first result type: $v1_type"
    echo "  /v2/search first result domain: $v2_type"
    echo "  /search first result object_type: $fusion_type"
  done
done
echo

echo "=========================================================================="
echo "PARITY TEST COMPLETE"
echo "All response files saved to:"
echo "  $OUTPUT_DIR/"
echo "=========================================================================="
