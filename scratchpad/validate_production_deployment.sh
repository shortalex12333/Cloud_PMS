#!/bin/bash
# Production Validation for Commit 772337c
# Tests entity extraction improvements across 4 lenses

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="https://pipeline-core.int.celeste7.ai/webhook/search"
JWT="${JWT_TOKEN:-}"

if [ -z "$JWT" ]; then
    echo -e "${RED}Error: JWT_TOKEN environment variable not set${NC}"
    echo "Usage: JWT_TOKEN=your_token_here ./validate_production_deployment.sh"
    exit 1
fi

echo "=================================="
echo "Production Deployment Validation"
echo "Commit: 772337c"
echo "Date: 2026-02-02"
echo "=================================="
echo ""

# Test function
test_query() {
    local lens=$1
    local query=$2
    local expected_entity=$3

    echo -e "${YELLOW}Testing $lens:${NC} \"$query\""

    response=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $JWT" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"limit\": 3}")

    # Check if entity was extracted
    if echo "$response" | jq -e ".entities[] | select(.type==\"$expected_entity\")" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC} - $expected_entity entity extracted"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} - $expected_entity entity NOT found"
        echo "Response entities:"
        echo "$response" | jq '.entities'
        return 1
    fi
}

# Test function for results
test_results() {
    local lens=$1
    local query=$2
    local expected_source=$3

    echo -e "${YELLOW}Testing $lens Results:${NC} \"$query\""

    response=$(curl -s -X POST "$API_URL" \
        -H "Authorization: Bearer $JWT" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\", \"limit\": 3}")

    result_count=$(echo "$response" | jq '.results | length')

    if [ "$result_count" -gt 0 ]; then
        echo -e "${GREEN}✅ PASS${NC} - $result_count results returned"

        # Check source table if specified
        if [ -n "$expected_source" ]; then
            source_table=$(echo "$response" | jq -r '.results[0].source_table // empty')
            if [ "$source_table" = "$expected_source" ]; then
                echo -e "${GREEN}✅ PASS${NC} - Results from correct table: $source_table"
            else
                echo -e "${YELLOW}⚠️  WARNING${NC} - Source table: $source_table (expected: $expected_source)"
            fi
        fi
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} - No results returned"
        echo "Response:"
        echo "$response" | jq '.error // empty'
        return 1
    fi
}

passed=0
failed=0

echo "=================================="
echo "1. Parts Lens - Manufacturer Search"
echo "=================================="
echo ""

if test_query "Parts Lens" "Racor" "part"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

if test_results "Parts Lens" "Racor" "pms_parts"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

if test_query "Parts Lens" "Caterpillar" "part"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=================================="
echo "2. Shopping List Lens"
echo "=================================="
echo ""

if test_query "Shopping List" "pending shopping list items" "shopping_list"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=================================="
echo "3. Document Lens"
echo "=================================="
echo ""

if test_query "Document Lens" "DNV-123456 loadline certificate" "document"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

if test_query "Document Lens" "IMO-9876543" "document"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=================================="
echo "4. Crew Lens"
echo "=================================="
echo ""

if test_query "Crew Lens" "critical warnings" "crew"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

if test_query "Crew Lens" "non-compliant rest" "crew"; then
    ((passed++))
else
    ((failed++))
fi
echo ""

echo "=================================="
echo "Validation Summary"
echo "=================================="
echo ""
echo "Total Tests: $((passed + failed))"
echo -e "${GREEN}Passed: $passed${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: $failed${NC}"
else
    echo -e "${GREEN}Failed: 0${NC}"
fi
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ ALL VALIDATIONS PASSED${NC}"
    echo "Deployment 772337c is working correctly in production"
    exit 0
else
    echo -e "${RED}❌ SOME VALIDATIONS FAILED${NC}"
    echo "Please investigate failed tests"
    exit 1
fi
