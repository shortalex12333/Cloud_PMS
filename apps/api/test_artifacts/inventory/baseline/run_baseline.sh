#!/bin/bash
set -e

# Load tokens
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

BASE_URL="https://pipeline-core.int.celeste7.ai"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "=== Baseline Repro: Inventory Lens Queries ==="
echo "API: $BASE_URL"
echo "Yacht: $YACHT_ID"
echo

# Query 1: parts low in stock
echo "Query 1: parts low in stock"
echo "  Crew..."
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"parts low in stock"}' | jq . > crew_low_stock.json

echo "  HOD..."
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"parts low in stock"}' | jq . > hod_low_stock.json

# Query 2: oil filters
echo "Query 2: oil filters"
echo "  Crew..."
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"oil filters"}' | jq . > crew_oil_filters.json

echo "  HOD..."
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"oil filters"}' | jq . > hod_oil_filters.json

# Query 3: spare parts for main engine
echo "Query 3: spare parts for main engine"
echo "  Crew..."
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"spare parts for main engine"}' | jq . > crew_spare_parts.json

echo "  HOD..."
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  "$BASE_URL/v2/search" \
  -d '{"query":"spare parts for main engine"}' | jq . > hod_spare_parts.json

echo
echo "=== Baseline captured ==="
ls -lh *.json
