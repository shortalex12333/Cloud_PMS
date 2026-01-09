#!/bin/bash

###############################################################################
# P0 Actions Quick Test Script
###############################################################################
#
# Prerequisites:
# 1. FastAPI server running on http://localhost:8000
# 2. Valid JWT token
# 3. Valid yacht_id, user_id, and test entity IDs
#
# Usage:
#   ./test_p0_actions.sh
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8000"
JWT_TOKEN="${JWT_TOKEN:-}"
YACHT_ID="${YACHT_ID:-}"
USER_ID="${USER_ID:-}"

# Test entity IDs (replace with actual values from your database)
EQUIPMENT_ID="${EQUIPMENT_ID:-}"
FAULT_ID="${FAULT_ID:-}"
PART_ID="${PART_ID:-}"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo "============================================================================="
    echo "$1"
    echo "============================================================================="
    echo ""
}

print_test() {
    echo -e "${YELLOW}Testing:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
}

print_error() {
    echo -e "${RED}❌ FAIL:${NC} $1"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check if server is running
    if curl -s "$API_URL/v1/actions/health" > /dev/null 2>&1; then
        print_success "FastAPI server is running"
    else
        print_error "FastAPI server is not accessible at $API_URL"
        echo "Please start the server with: cd apps/api && uvicorn pipeline_service:app --port 8000"
        exit 1
    fi

    # Check environment variables
    if [ -z "$JWT_TOKEN" ]; then
        print_error "JWT_TOKEN not set"
        echo "Please set: export JWT_TOKEN='your_jwt_token_here'"
        exit 1
    fi

    if [ -z "$YACHT_ID" ]; then
        print_error "YACHT_ID not set"
        echo "Please set: export YACHT_ID='your_yacht_uuid_here'"
        exit 1
    fi

    if [ -z "$USER_ID" ]; then
        print_error "USER_ID not set"
        echo "Please set: export USER_ID='your_user_uuid_here'"
        exit 1
    fi

    print_success "All environment variables set"
}

###############################################################################
# Test Functions
###############################################################################

test_health_check() {
    print_header "Test 0: Health Check"
    print_test "GET $API_URL/v1/actions/health"

    response=$(curl -s "$API_URL/v1/actions/health")
    status=$(echo "$response" | jq -r '.status')
    handlers_loaded=$(echo "$response" | jq -r '.handlers_loaded')

    if [ "$status" = "healthy" ] && [ "$handlers_loaded" = "4" ]; then
        print_success "Health check passed - All 4 handlers loaded"
        echo "$response" | jq .
    else
        print_error "Health check failed - Status: $status, Handlers: $handlers_loaded"
        echo "$response" | jq .
        exit 1
    fi
}

test_show_manual_section() {
    print_header "Test 1: show_manual_section (READ)"

    if [ -z "$EQUIPMENT_ID" ]; then
        print_error "EQUIPMENT_ID not set - skipping test"
        return
    fi

    print_test "POST $API_URL/v1/actions/execute"

    response=$(curl -s -X POST "$API_URL/v1/actions/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -d '{
            "action": "show_manual_section",
            "context": {
                "yacht_id": "'"$YACHT_ID"'",
                "user_id": "'"$USER_ID"'",
                "role": "engineer"
            },
            "payload": {
                "equipment_id": "'"$EQUIPMENT_ID"'"
            }
        }')

    status=$(echo "$response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        print_success "show_manual_section executed successfully"
        echo "$response" | jq '.result | {equipment: .equipment.name, sections_count: (.sections | length)}'
    else
        print_error "show_manual_section failed"
        echo "$response" | jq .
    fi
}

test_check_stock_level() {
    print_header "Test 2: check_stock_level (READ)"

    if [ -z "$PART_ID" ]; then
        print_error "PART_ID not set - skipping test"
        return
    fi

    print_test "POST $API_URL/v1/actions/execute"

    response=$(curl -s -X POST "$API_URL/v1/actions/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -d '{
            "action": "check_stock_level",
            "context": {
                "yacht_id": "'"$YACHT_ID"'",
                "user_id": "'"$USER_ID"'",
                "role": "engineer"
            },
            "payload": {
                "part_id": "'"$PART_ID"'"
            }
        }')

    status=$(echo "$response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        print_success "check_stock_level executed successfully"
        echo "$response" | jq '.result | {part: .part.name, stock: .current_stock, status: .stock_status}'
    else
        print_error "check_stock_level failed"
        echo "$response" | jq .
    fi
}

test_create_work_order_prefill() {
    print_header "Test 3a: create_work_order_from_fault - Prefill"

    if [ -z "$FAULT_ID" ]; then
        print_error "FAULT_ID not set - skipping test"
        return 1
    fi

    print_test "GET $API_URL/v1/actions/create_work_order_from_fault/prefill?fault_id=$FAULT_ID"

    response=$(curl -s -X GET \
        "$API_URL/v1/actions/create_work_order_from_fault/prefill?fault_id=$FAULT_ID" \
        -H "Authorization: Bearer $JWT_TOKEN")

    status=$(echo "$response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        print_success "Prefill executed successfully"
        echo "$response" | jq '.prefill_data | {title, equipment_name, priority}'
        return 0
    else
        print_error "Prefill failed"
        echo "$response" | jq .
        return 1
    fi
}

test_create_work_order_execute() {
    print_header "Test 3b: create_work_order_from_fault - Execute"

    if [ -z "$FAULT_ID" ]; then
        print_error "FAULT_ID not set - skipping test"
        return
    fi

    # Generate signature
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    signature=$(echo -n "$USER_ID:create_work_order_from_fault:$timestamp" | base64)

    print_test "POST $API_URL/v1/actions/execute"

    response=$(curl -s -X POST "$API_URL/v1/actions/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -d '{
            "action": "create_work_order_from_fault",
            "context": {
                "yacht_id": "'"$YACHT_ID"'",
                "user_id": "'"$USER_ID"'",
                "role": "chief_engineer"
            },
            "payload": {
                "fault_id": "'"$FAULT_ID"'",
                "title": "Test WO from Script",
                "priority": "high",
                "description": "Test work order created by automated script",
                "signature": {
                    "user_id": "'"$USER_ID"'",
                    "action": "create_work_order_from_fault",
                    "timestamp": "'"$timestamp"'",
                    "signature": "'"$signature"'"
                }
            }
        }')

    status=$(echo "$response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        print_success "Work order created successfully"
        WO_ID=$(echo "$response" | jq -r '.result.work_order.id')
        WO_NUMBER=$(echo "$response" | jq -r '.result.work_order.number')
        echo "Created: $WO_NUMBER (ID: $WO_ID)"
        echo "$response" | jq '.result.work_order | {number, title, status, priority}'

        # Export for subsequent tests
        export CREATED_WO_ID="$WO_ID"
    else
        print_error "Work order creation failed"
        echo "$response" | jq .
    fi
}

test_add_note() {
    print_header "Test 4: add_note_to_work_order"

    local wo_id="${CREATED_WO_ID:-}"

    if [ -z "$wo_id" ]; then
        print_error "No work order ID available - skipping test"
        echo "Run test_create_work_order_execute first"
        return
    fi

    print_test "POST $API_URL/v1/actions/execute"

    response=$(curl -s -X POST "$API_URL/v1/actions/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -d '{
            "action": "add_note_to_work_order",
            "context": {
                "yacht_id": "'"$YACHT_ID"'",
                "user_id": "'"$USER_ID"'",
                "role": "engineer"
            },
            "payload": {
                "work_order_id": "'"$wo_id"'",
                "note_text": "Test note added by automated script. Investigation in progress.",
                "note_type": "progress"
            }
        }')

    status=$(echo "$response" | jq -r '.status')

    if [ "$status" = "success" ]; then
        print_success "Note added successfully"
        echo "$response" | jq '.result.note | {note_type, created_by_name, created_at}'
    else
        print_error "Failed to add note"
        echo "$response" | jq .
    fi
}

test_authentication() {
    print_header "Security Test: Authentication"

    print_test "Testing invalid JWT token"

    response=$(curl -s -X POST "$API_URL/v1/actions/execute" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer invalid_token_12345" \
        -d '{
            "action": "check_stock_level",
            "context": {"yacht_id": "'"$YACHT_ID"'", "user_id": "'"$USER_ID"'"},
            "payload": {"part_id": "'"$PART_ID"'"}
        }')

    # Check for 401 status in response
    if echo "$response" | grep -q "detail"; then
        print_success "Invalid token correctly rejected"
    else
        print_error "Authentication bypass detected!"
        echo "$response"
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    echo "============================================================================="
    echo "                P0 Actions End-to-End Test Suite"
    echo "============================================================================="
    echo ""
    echo "API URL: $API_URL"
    echo "Yacht ID: ${YACHT_ID:0:8}..."
    echo "User ID: ${USER_ID:0:8}..."
    echo ""

    # Run prerequisites check
    check_prerequisites

    # Run tests
    test_health_check
    test_show_manual_section
    test_check_stock_level

    # MUTATE actions
    if test_create_work_order_prefill; then
        test_create_work_order_execute
        test_add_note
    fi

    # Security tests
    test_authentication

    # Summary
    print_header "Test Suite Complete"
    echo "Review results above for any failures"
    echo ""
    echo "For full testing guide, see: P0_ACTIONS_TEST_GUIDE.md"
    echo ""
}

# Run main function
main "$@"
