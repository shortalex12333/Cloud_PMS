#!/bin/bash
# Test local Docker container

CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Testing parts query against local container..."
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  "http://localhost:8081/v2/search" \
  -d '{"query_text":"parts low in stock"}' | jq '{success, total_count, first_result_domain: .results[0]?.domain}'
