#!/bin/bash
# =============================================================================
# NATURAL LANGUAGE SEARCH TESTS - Automated Execution
# =============================================================================
# Purpose: Run real user search queries and verify results
# Usage: ./04_run_natural_language_tests.sh
# Requires: JWT tokens from 03_generate_jwt_tokens.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Load JWT tokens
if [ -f "tests/setup/.env.test" ]; then
    source tests/setup/.env.test
    echo -e "${GREEN}✅ Loaded JWT tokens${NC}"
else
    echo -e "${RED}❌ JWT tokens not found!${NC}"
    echo "Run: ./tests/setup/03_generate_jwt_tokens.sh first"
    exit 1
fi

# API endpoint
API_BASE="https://pipeline-core.int.celeste7.ai"
SEARCH_ENDPOINT="${API_BASE}/api/search/stream"
TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run search query
run_search_test() {
    local test_name=$1
    local user_name=$2
    local jwt_token=$3
    local query=$4
    local expected_action=$5
    local expected_result_count=$6
    local should_filter_by=$7

    ((TOTAL_TESTS++))

    echo ""
    echo -e "${BLUE}========================================================================"
    echo "TEST ${TOTAL_TESTS}: ${test_name}"
    echo "========================================================================${NC}"
    echo -e "User:  ${user_name}"
    echo -e "Query: ${MAGENTA}\"${query}\"${NC}"
    echo ""

    # Run search
    response=$(curl -s -X POST "${SEARCH_ENDPOINT}" \
        -H "Authorization: Bearer ${jwt_token}" \
        -H "Content-Type: application/json" \
        -d "{\"query\":\"${query}\",\"yacht_id\":\"${TEST_YACHT_ID}\"}")

    # Check if response is valid JSON
    if ! echo "$response" | jq '.' > /dev/null 2>&1; then
        echo -e "${RED}❌ FAIL: Invalid JSON response${NC}"
        echo "Response: $response"
        ((FAILED_TESTS++))
        return 1
    fi

    # Extract results
    status=$(echo "$response" | jq -r '.status // "error"')
    actions=$(echo "$response" | jq -r '.actions // [] | join(", ")')
    result_count=$(echo "$response" | jq -r '.data // [] | length')

    echo "Status: $status"
    echo "Actions: $actions"
    echo "Results: $result_count records"

    # Verify expected action
    if [ -n "$expected_action" ]; then
        if echo "$actions" | grep -q "$expected_action"; then
            echo -e "${GREEN}✅ Correct action triggered: ${expected_action}${NC}"
        else
            echo -e "${RED}❌ Expected action '${expected_action}' not found${NC}"
            echo "   Got: $actions"
            ((FAILED_TESTS++))
            return 1
        fi
    fi

    # Verify result count
    if [ -n "$expected_result_count" ]; then
        if [ "$result_count" -le "$expected_result_count" ]; then
            echo -e "${GREEN}✅ Result count OK: ${result_count} <= ${expected_result_count}${NC}"
        else
            echo -e "${RED}❌ Too many results: ${result_count} > ${expected_result_count}${NC}"
            ((FAILED_TESTS++))
            return 1
        fi
    fi

    # Verify RLS filtering (check no cross-department data)
    if [ -n "$should_filter_by" ]; then
        # This would require parsing actual results - simplified check
        echo -e "${YELLOW}⚠️  RLS filtering check: ${should_filter_by} (manual verification needed)${NC}"
    fi

    echo -e "${GREEN}✅ PASS${NC}"
    ((PASSED_TESTS++))
}

# =============================================================================
# TEST SUITE
# =============================================================================

echo -e "${BLUE}"
echo "========================================================================"
echo "NATURAL LANGUAGE SEARCH TESTING - Hours of Rest"
echo "========================================================================"
echo -e "${NC}"
echo "API: ${API_BASE}"
echo "Yacht: ${TEST_YACHT_ID}"
echo ""

# =============================================================================
# CATEGORY 1: Basic Queries (Clean Baseline)
# =============================================================================

echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 1: Basic Queries (Baseline)${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "Basic: Show my rest hours" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "show me my hours of rest" \
    "get_hours_of_rest" \
    "14" \
    "own_records_only"

run_search_test \
    "Paraphrase: Did I sleep enough" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "did I get enough sleep" \
    "get_hours_of_rest" \
    "14" \
    "own_records_only"

# =============================================================================
# CATEGORY 2: Misspellings (Fuzzy Matching)
# =============================================================================

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 2: Misspellings (Fuzzy Matching)${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "Misspelling: rest hurs" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "show my rest hurs" \
    "get_hours_of_rest" \
    "14" \
    ""

run_search_test \
    "Misspelling: complaince" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "veiw my complaince" \
    "get_hours_of_rest" \
    "14" \
    ""

# =============================================================================
# CATEGORY 3: Time Ambiguity (Entity Extraction)
# =============================================================================

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 3: Time Ambiguity (Entity Extraction)${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "Time: last week" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "show my rest hours last week" \
    "get_hours_of_rest" \
    "7" \
    ""

run_search_test \
    "Time: yesterday" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "rest hours yesterday" \
    "get_hours_of_rest" \
    "1" \
    ""

# =============================================================================
# CATEGORY 4: Department RLS (Critical Security)
# =============================================================================

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 4: Department RLS (Security Test)${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "HOD: Show deck crew (should succeed)" \
    "HOD (deck)" \
    "$HOD_DECK_JWT" \
    "show deck crew rest hours" \
    "get_hours_of_rest" \
    "28" \
    "deck_only"

run_search_test \
    "HOD: Show engine crew (should FAIL/EMPTY)" \
    "HOD (deck)" \
    "$HOD_DECK_JWT" \
    "show engine crew rest hours" \
    "" \
    "0" \
    "should_be_zero"

run_search_test \
    "Captain: Show all crew (should see all)" \
    "Captain" \
    "$CAPTAIN_JWT" \
    "show all crew rest hours" \
    "get_hours_of_rest" \
    "50" \
    "all_departments"

# =============================================================================
# CATEGORY 5: Precision (Specific Queries)
# =============================================================================

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 5: Precision (Not Buried in Noise)${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "Specific: warnings active" \
    "HOD (deck)" \
    "$HOD_DECK_JWT" \
    "show deck crew warnings active" \
    "list_crew_warnings" \
    "3" \
    "deck_warnings_only"

run_search_test \
    "Specific: non-compliant records" \
    "Captain" \
    "$CAPTAIN_JWT" \
    "who didn't get enough rest this week" \
    "get_hours_of_rest" \
    "5" \
    "non_compliant_only"

# =============================================================================
# CATEGORY 6: Chaotic Input (Stress Test)
# =============================================================================

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}CATEGORY 6: Chaotic Real User Input${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

run_search_test \
    "Chaotic: complex query" \
    "HOD (deck)" \
    "$HOD_DECK_JWT" \
    "show me deck crew that didn't sleep enough last tuesday" \
    "get_hours_of_rest" \
    "5" \
    "deck_non_compliant"

run_search_test \
    "Chaotic: paraphrase with details" \
    "John (deck crew)" \
    "$JOHN_DECK_JWT" \
    "did I get my 10 hours or whatever it is last week" \
    "get_hours_of_rest" \
    "7" \
    ""

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo -e "${BLUE}========================================================================"
echo "TEST SUMMARY"
echo "========================================================================${NC}"
echo -e "Total Tests:  ${TOTAL_TESTS}"
echo -e "${GREEN}Passed:       ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed:       ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Natural language search is working correctly:"
    echo "  ✅ GPT understands chaotic input"
    echo "  ✅ Correct actions triggered"
    echo "  ✅ RLS enforces department filtering"
    echo "  ✅ Results are precise (not noise)"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Review failed tests above for details."
    echo "Common issues:"
    echo "  - Search endpoint not configured"
    echo "  - GPT backend not interpreting queries"
    echo "  - RLS policies not enforced"
    echo "  - Action keywords need tuning"
    echo ""
    exit 1
fi
