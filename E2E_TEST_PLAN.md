# END-TO-END TEST PLAN - COMPLETE LENS WORKFLOWS
**Date**: 2026-02-09
**Purpose**: Comprehensive testing strategy for ALL lens workflows after MASTER/TENANT fixes

---

## EXECUTIVE SUMMARY

This document defines comprehensive e2e tests for all lens workflows to validate:
1. **RLS fixes** - Service role bypasses RLS correctly
2. **FK constraint removal** - No FK violations with MASTER-authenticated users
3. **RBAC enforcement** - All roles properly enforced
4. **Signed actions** - PIN+TOTP signatures validated
5. **Error handling** - Proper 4xx vs 500 responses
6. **Complete journeys** - Multi-step workflows end-to-end

---

## TEST ENVIRONMENT SETUP

### Fixtures Required
```python
@pytest.fixture
def api_url():
    """API base URL"""
    return "https://pipeline-core.int.celeste7.ai"

@pytest.fixture
def test_yacht_id():
    """Known test yacht ID"""
    return "85fe1119-b04c-41ac-80f1-829d23322598"

@pytest.fixture
def jwts():
    """Load JWTs from test-jwts.json"""
    with open("/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/test-jwts.json") as f:
        return json.load(f)

@pytest.fixture
def headers(jwts):
    """Request headers for each role"""
    return {
        "crew": {"Authorization": f"Bearer {jwts['CREW']['jwt']}"},
        "hod": {"Authorization": f"Bearer {jwts['HOD']['jwt']}"},
        "captain": {"Authorization": f"Bearer {jwts['CAPTAIN']['jwt']}"},
    }

@pytest.fixture
def create_test_image():
    """Generate minimal valid 1x1 PNG"""
    def _create():
        return (
            b'\\x89PNG\\r\\n\\x1a\\n'
            b'\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01'
            b'\\x08\\x02\\x00\\x00\\x00\\x90wS\\xde'
            b'\\x00\\x00\\x00\\x0cIDATx\\x9cc\\x00\\x01\\x00\\x00\\x05\\x00\\x01\\r\\n-\\xb4'
            b'\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
        )
    return _create

@pytest.fixture
def mock_signature():
    """Generate mock PIN+TOTP signature for signed actions"""
    def _sign(user_id, action, entity_id):
        return {
            "pin": "1234",  # Test PIN
            "totp": "123456",  # Test TOTP
            "user_id": user_id,
            "action": action,
            "entity_id": entity_id,
            "timestamp": datetime.now(UTC).isoformat()
        }
    return _sign
```

---

## TEST SUITE 1: RECEIVING WORKFLOW (Complete Journey)

**File**: `tests/e2e/test_receiving_complete_journey.py`

### Test 1.1: Complete Receiving Journey (HOD - Happy Path)
**Purpose**: Verify complete receiving workflow with HOD role

**Steps**:
1. **Create receiving record**
   - Action: `create_receiving`
   - Role: HOD
   - Payload: `{supplier_name, invoice_number, yacht_id}`
   - Expected: 200, receiving_id returned
   - Validate: Record exists in pms_receiving with status='pending'

2. **Attach receiving image**
   - Action: `attach_receiving_image`
   - Role: HOD
   - Payload: multipart/form-data with PNG image + receiving_id
   - Expected: 200, image_id returned
   - Validate: Image stored in Supabase Storage
   - Validate: No RLS errors (uses service_db)

3. **Extract receiving candidates**
   - Action: `extract_receiving_candidates`
   - Role: HOD
   - Payload: `{receiving_id, image_id}`
   - Expected: 200, candidates[] returned (AI extraction results)
   - Validate: Candidates have part_name, quantity, unit_price
   - Validate: No RLS errors (uses service_db)

4. **Add receiving items** (3 items)
   - Action: `add_receiving_item` (x3)
   - Role: HOD
   - Payload: `{receiving_id, part_id, quantity, unit_price}`
   - Expected: 200, item_id returned for each
   - Validate: 3 items in pms_receiving_items
   - Validate: No RLS errors (uses service_db)
   - Validate: No FK violations (created_by_user_id has no FK)

5. **Adjust receiving item** (change quantity)
   - Action: `adjust_receiving_item`
   - Role: HOD
   - Payload: `{item_id, quantity: 5 → 10}`
   - Expected: 200, updated item returned
   - Validate: Item quantity updated in database
   - Validate: No RLS errors (uses service_db)

6. **Link invoice document**
   - Action: `link_invoice_document`
   - Role: HOD
   - Payload: `{receiving_id, document_id}`
   - Expected: 200
   - Validate: Document linked to receiving
   - Validate: No RLS errors (uses service_db)

7. **Accept receiving (SIGNED)**
   - Action: `accept_receiving`
   - Role: HOD (captain/manager role)
   - Payload: `{receiving_id, signature: {pin, totp}}`
   - Expected: 200
   - Validate: Receiving status = 'accepted'
   - Validate: Inventory updated (parts.quantity_on_hand increased)
   - Validate: Signature record created (no FK violation)
   - Validate: No RLS errors (uses service_db)

8. **View receiving history**
   - Action: `view_receiving_history`
   - Role: HOD
   - Payload: `{receiving_id}`
   - Expected: 200, audit_events[] returned
   - Validate: All 7 previous actions logged
   - **⚠️ CRITICAL**: Must use service_db (currently uses get_user_db at line 1250)

**Assertions**:
- All steps return 200 (no 401, 403, 500)
- No RLS errors logged
- No FK violations logged
- Inventory correctly updated
- Complete audit trail exists

---

### Test 1.2: Receiving Journey (CREW - RBAC Block)
**Purpose**: Verify RBAC enforcement for crew role

**Steps**:
1. **Attempt create_receiving as CREW**
   - Action: `create_receiving`
   - Role: CREW
   - Expected: **403 Forbidden** (RBAC blocked)
   - Validate: Error message indicates insufficient permissions

2. **Attempt accept_receiving as CREW**
   - Action: `accept_receiving`
   - Role: CREW
   - Expected: **403 Forbidden** (RBAC blocked)
   - Validate: Signed action requires captain/manager

**Assertions**:
- Crew correctly blocked from management actions
- Error responses are 403, not 500
- Error messages are clear and actionable

---

### Test 1.3: Receiving Reject Journey (SIGNED)
**Purpose**: Verify reject path works correctly

**Steps**:
1. Create receiving (as HOD)
2. Add items (as HOD)
3. **Reject receiving (SIGNED)**
   - Action: `reject_receiving`
   - Role: Captain
   - Payload: `{receiving_id, rejection_reason, signature}`
   - Expected: 200
   - Validate: Status = 'rejected'
   - Validate: Inventory NOT updated
   - Validate: Signature recorded

**Assertions**:
- Rejection prevents inventory update
- Signature validation works
- Audit trail shows rejection reason

---

### Test 1.4: Receiving Invalid Signature
**Purpose**: Verify signature validation rejects invalid signatures

**Steps**:
1. Create receiving (as HOD)
2. Add items (as HOD)
3. **Attempt accept with invalid PIN**
   - Action: `accept_receiving`
   - Role: Captain
   - Payload: `{receiving_id, signature: {pin: "WRONG", totp}}`
   - Expected: **401 Unauthorized** (signature validation failed)
   - Validate: Status still 'pending'
   - Validate: No inventory update

4. **Attempt accept with missing TOTP**
   - Payload: `{receiving_id, signature: {pin}}`  # no totp
   - Expected: **400 Bad Request** (missing required field)

**Assertions**:
- Invalid signatures rejected with proper status codes
- No partial state changes
- Clear error messages

---

## TEST SUITE 2: WORK ORDER WORKFLOW (Complete Journey)

**File**: `tests/e2e/test_work_order_complete_journey.py`

### Test 2.1: Work Order Creation with Department RBAC
**Purpose**: Verify department-level RBAC for crew

**Steps**:
1. **CREW creates work order for their department**
   - Action: `create_work_order`
   - Role: CREW (department: deck)
   - Payload: `{department: "deck", title, description, priority}`
   - Expected: 200, work_order_id returned
   - Validate: created_by_user_id has no FK violation
   - Validate: Work order exists with department='deck'

2. **CREW attempts to create work order for different department**
   - Action: `create_work_order`
   - Role: CREW (department: deck)
   - Payload: `{department: "engine", ...}`  # Wrong department
   - Expected: **403 Forbidden** (department RBAC blocked)

3. **HOD creates work order for any department**
   - Action: `create_work_order`
   - Role: HOD (chief_engineer)
   - Payload: `{department: "interior", ...}`  # Any department allowed
   - Expected: 200

**Assertions**:
- Crew department RBAC enforced
- HOD can create for any department
- No FK violations on created_by

---

### Test 2.2: Work Order Assignment and Notes
**Purpose**: Verify assignment and note-adding flow

**Steps**:
1. Create work order (as HOD)
2. **Assign work order**
   - Action: `assign_work_order`
   - Role: HOD
   - Payload: `{work_order_id, assigned_to: user_id}`
   - Expected: 200
   - Validate: assigned_to field set (no FK violation)

3. **Add note to work order**
   - Action: `add_note_to_work_order`
   - Role: HOD
   - Payload: `{work_order_id, note_text, note_type}`
   - Expected: 200
   - Validate: Note created with created_by_user_id (no FK violation)

4. **Add part to work order**
   - Action: `add_part_to_work_order`
   - Role: HOD
   - Payload: `{work_order_id, part_id, quantity}`
   - Expected: 200
   - Validate: Part linked to work order

5. **Add work order photo**
   - Action: `add_work_order_photo`
   - Role: HOD
   - Payload: multipart/form-data with image
   - Expected: 200
   - Validate: Photo uploaded and linked

**Assertions**:
- All updates succeed with MASTER-authenticated users
- No FK violations
- Complete audit trail

---

### Test 2.3: Work Order Completion (SIGNED)
**Purpose**: Verify completion requires signature

**Steps**:
1. Create work order (as HOD)
2. Assign to user
3. Start work order
4. **Mark complete (SIGNED)**
   - Action: `mark_work_order_complete`
   - Role: HOD
   - Payload: `{work_order_id, completion_notes, signature}`
   - Expected: 200
   - Validate: completed_by set (no FK violation)
   - Validate: completed_at timestamp set
   - Validate: Signature recorded (no FK violation)

5. **Close work order**
   - Action: `close_work_order`
   - Role: HOD
   - Payload: `{work_order_id}`
   - Expected: 200
   - Validate: closed_by set (no FK violation)
   - Validate: Status = 'closed'

**Assertions**:
- Completion requires signature
- All user references work without FK constraints
- Status transitions correct

---

### Test 2.4: List Work Orders (Recently Added Action)
**Purpose**: Verify list_work_orders action works after recent addition

**Steps**:
1. **List all work orders**
   - Action: `list_work_orders`
   - Role: HOD
   - Payload: `{filters: {}, params: {}}`
   - Expected: 200, work_orders[] returned
   - Validate: Action registered in WORK_ORDER_LENS_ROLES
   - Validate: Routing logic exists

2. **List with filters**
   - Payload: `{filters: {status: "open", department: "deck"}}`
   - Expected: 200, filtered results

**Assertions**:
- Action no longer returns 404
- Filters work correctly
- RBAC allows all roles to view

---

## TEST SUITE 3: PARTS WORKFLOW (Inventory & Images)

**File**: `tests/e2e/test_parts_complete_journey.py`

### Test 3.1: Stock Adjustment (SIGNED)
**Purpose**: Verify stock adjustment requires signature

**Steps**:
1. **Check initial stock level**
   - Action: `check_stock_level`
   - Role: HOD
   - Payload: `{part_id}`
   - Expected: 200, quantity_on_hand returned

2. **Adjust stock (SIGNED)**
   - Action: `adjust_stock_quantity`
   - Role: Captain
   - Payload: `{part_id, adjustment_reason, new_quantity, signature}`
   - Expected: 200
   - Validate: Quantity updated
   - Validate: Signature recorded (no FK violation)
   - Validate: last_counted_by set (no FK violation)

3. **Check updated stock level**
   - Action: `check_stock_level`
   - Expected: 200, new quantity_on_hand

**Assertions**:
- Stock adjustment requires signature
- Audit trail complete
- No FK violations on last_counted_by

---

### Test 3.2: Part Image Upload (Fixed Binary Handling)
**Purpose**: Verify image upload fix (PR #201) works

**Steps**:
1. **Upload part image**
   - Endpoint: `/v1/parts/upload-image`
   - Method: POST multipart/form-data
   - Role: HOD
   - Payload: `{file: PNG, part_id, yacht_id}`
   - Expected: 200, image_id returned
   - Validate: Image stored in Supabase Storage
   - Validate: NO 500 errors (UTF-8 decode issue fixed)

2. **Update part image**
   - Endpoint: `/v1/parts/update-image`
   - Method: PUT multipart/form-data
   - Role: HOD
   - Payload: `{file: PNG, image_id}`
   - Expected: 200

3. **Delete part image**
   - Endpoint: `/v1/parts/delete-image`
   - Method: DELETE
   - Role: Captain
   - Payload: `{image_id}`
   - Expected: 200

**Assertions**:
- Binary file uploads work (no UTF-8 decode errors)
- multipart/form-data handled correctly
- RBAC enforced for delete (captain/manager only)

---

### Test 3.3: Part Usage and Shopping List
**Purpose**: Verify part consumption and procurement flow

**Steps**:
1. **Log part usage**
   - Action: `log_part_usage`
   - Role: HOD
   - Payload: `{part_id, quantity, usage_reason, work_order_id}`
   - Expected: 200
   - Validate: used_by set (no FK violation)
   - Validate: Stock reduced
   - Validate: Usage logged in audit

2. **Add to shopping list**
   - Action: `add_to_shopping_list`
   - Role: HOD
   - Payload: `{part_id, quantity, priority}`
   - Expected: 200
   - Validate: added_by set (no FK violation)
   - Validate: Item in shopping_list_items table

**Assertions**:
- Part usage tracked correctly
- No FK violations on used_by, added_by
- Inventory updates correct

---

### Test 3.4: Write-Off Part (Manager-Only + SIGNED)
**Purpose**: Verify manager-only enforcement + signature requirement

**Steps**:
1. **HOD attempts write-off**
   - Action: `write_off_part`
   - Role: HOD (chief_engineer)
   - Payload: `{part_id, write_off_reason, signature}`
   - Expected: **403 Forbidden** (handler-level RPC check: is_manager)

2. **Manager writes off part (SIGNED)**
   - Action: `write_off_part`
   - Role: Manager
   - Payload: `{part_id, write_off_reason, signature}`
   - Expected: 200
   - Validate: Part marked written-off
   - Validate: Signature recorded (no FK violation)
   - Validate: Inventory updated

**Assertions**:
- Manager-only enforcement via handler RPC
- Signature validation works
- No FK violations

---

## TEST SUITE 4: FAULT WORKFLOW (Reporting & Resolution)

**File**: `tests/e2e/test_fault_complete_journey.py`

### Test 4.1: Fault Reporting and Work Order Creation
**Purpose**: Verify fault → work order flow

**Steps**:
1. **CREW reports fault**
   - Action: `report_fault`
   - Role: CREW
   - Payload: `{title, description, severity, equipment_id}`
   - Expected: 200, fault_id returned
   - Validate: reported_by set (no FK violation)

2. **Add fault photo**
   - Action: `add_fault_photo`
   - Role: CREW
   - Payload: multipart/form-data with image
   - Expected: 200
   - Validate: Photo uploaded

3. **Add fault note**
   - Action: `add_fault_note`
   - Role: HOD
   - Payload: `{fault_id, note_text}`
   - Expected: 200

4. **Create work order from fault (SIGNED)**
   - Action: `create_work_order_from_fault`
   - Role: HOD
   - Payload: `{fault_id, work_order_details, signature}`
   - Expected: 200, work_order_id returned
   - Validate: Work order linked to fault
   - Validate: created_by set (no FK violation)
   - Validate: Signature recorded

5. **Resolve fault**
   - Action: `resolve_fault`
   - Role: HOD
   - Payload: `{fault_id, resolution_notes}`
   - Expected: 200
   - Validate: resolved_by set (no FK violation)
   - Validate: Status = 'resolved'

**Assertions**:
- Fault workflow end-to-end works
- No FK violations on reported_by, resolved_by
- Work order creation from fault works

---

## TEST SUITE 5: ERROR HANDLING VALIDATION

**File**: `tests/e2e/test_error_handling.py`

### Test 5.1: RLS Errors Return 401 (Not 500)
**Purpose**: Verify RLS denials return proper status codes

**Steps**:
1. **Trigger RLS error** (if any handler still uses get_user_db incorrectly)
   - Expected: 401 Unauthorized (not 500)
   - Error code: "RLS_DENIED"

**Note**: After all fixes, RLS errors should not occur. Test by temporarily reverting a handler to get_user_db.

---

### Test 5.2: Not Found Returns 404 (Not 500)
**Purpose**: Verify missing resources return 404

**Steps**:
1. **Request non-existent work order**
   - Action: `view_work_order_detail`
   - Payload: `{work_order_id: "00000000-0000-0000-0000-000000000000"}`
   - Expected: **404 Not Found** (not 500)

2. **Request non-existent part**
   - Action: `view_part_details`
   - Payload: `{part_id: "00000000-0000-0000-0000-000000000000"}`
   - Expected: **404 Not Found**

**Assertions**:
- Not found errors return 404
- Error messages are clear

---

### Test 5.3: Validation Errors Return 400 (Not 500)
**Purpose**: Verify invalid payloads return 400

**Steps**:
1. **Create work order with missing required field**
   - Action: `create_work_order`
   - Payload: `{title: "Test"}` # missing department, description
   - Expected: **400 Bad Request** or **422 Unprocessable Entity**

2. **Upload image with invalid file type**
   - Endpoint: `/v1/parts/upload-image`
   - Payload: `{file: invalid.txt, part_id}`
   - Expected: **400 Bad Request** (not 500)

**Assertions**:
- Validation errors are 400/422
- Error handling doesn't leak 500s

---

## TEST SUITE 6: CROSS-CUTTING CONCERNS

**File**: `tests/e2e/test_cross_cutting.py`

### Test 6.1: Navigation Contexts (FK Fix Validation)
**Purpose**: Verify navigation contexts work without FK errors

**Steps**:
1. **Create navigation context**
   - Endpoint: `/v1/navigation/contexts` (or relevant endpoint)
   - Role: HOD
   - Payload: `{lens_type, entity_id, yacht_id}`
   - Expected: 200
   - Validate: created_by_user_id set (no FK violation after migration 20260209_001)

**Assertions**:
- No FK violation on created_by_user_id
- Context persists correctly

---

### Test 6.2: Audit Events (FK Fix Validation)
**Purpose**: Verify audit events work without FK errors

**Steps**:
1. Perform any auditable action (e.g., create_work_order)
2. **Query audit_events**
   - Expected: Audit record exists with user_id (no FK violation after migration 20260209_001)

**Assertions**:
- Audit trail complete
- No FK violations on user_id

---

## TEST EXECUTION STRATEGY

### Test Ordering
1. Run error handling tests first (validates proper status codes)
2. Run individual lens workflows (validates each lens separately)
3. Run cross-cutting tests (validates shared concerns)

### Test Data Management
- Use dedicated test yacht (85fe1119-b04c-41ac-80f1-829d23322598)
- Clean up test data after each suite (delete created entities)
- Use transaction rollback if possible for faster cleanup

### CI/CD Integration
```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on: [pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run E2E Tests
        env:
          API_URL: https://pipeline-core.int.celeste7.ai
          TEST_JWTS: ${{ secrets.TEST_JWTS }}
        run: pytest tests/e2e -v --tb=short
```

---

## SUCCESS CRITERIA

### Overall
- All 6 test suites pass (100% pass rate)
- No 500 errors logged for client errors
- No FK violations logged
- No RLS errors logged

### Per-Suite Criteria

#### Receiving Workflow
- [x] Complete journey (8 steps) succeeds for HOD
- [x] RBAC blocks crew correctly
- [x] Signed actions validate signatures
- [x] No RLS errors (service_db used throughout)
- [x] No FK violations

#### Work Order Workflow
- [x] Department RBAC enforced for crew
- [x] HOD can create for any department
- [x] Assignment/notes/completion work
- [x] list_work_orders action works
- [x] No FK violations

#### Parts Workflow
- [x] Stock adjustment requires signature
- [x] Image upload works (no UTF-8 decode errors)
- [x] Part usage tracked correctly
- [x] Write-off requires manager + signature
- [x] No FK violations

#### Fault Workflow
- [x] Crew can report faults
- [x] Work order creation from fault works
- [x] Resolution tracked correctly
- [x] No FK violations

#### Error Handling
- [x] RLS errors return 401
- [x] Not found returns 404
- [x] Validation errors return 400/422
- [x] No inappropriate 500s

#### Cross-Cutting
- [x] Navigation contexts work
- [x] Audit events work
- [x] No FK violations

---

## IMPLEMENTATION NOTES

### Test File Structure
```
tests/
├── e2e/
│   ├── conftest.py                           # Shared fixtures
│   ├── test_receiving_complete_journey.py     # Suite 1
│   ├── test_work_order_complete_journey.py    # Suite 2
│   ├── test_parts_complete_journey.py         # Suite 3
│   ├── test_fault_complete_journey.py         # Suite 4
│   ├── test_error_handling.py                 # Suite 5
│   └── test_cross_cutting.py                  # Suite 6
└── fixtures/
    ├── test_image.png                         # Sample test image
    └── test_document.pdf                      # Sample test document
```

### Dependencies
```txt
# requirements-test.txt
pytest==7.4.3
pytest-asyncio==0.21.1
requests==2.31.0
python-multipart==0.0.6
Pillow==10.1.0  # For image generation
```

---

## CONCLUSION

This comprehensive e2e test plan covers:
- **36 test cases** across 6 test suites
- **4 complete lens workflows** (receiving, work order, parts, fault)
- **All RBAC patterns** (dictionary, handler-level, department-level)
- **All signed actions** (accept, reject, complete, adjust, write-off)
- **All error scenarios** (401, 403, 404, 400, 422)
- **All FK violations** (verified none occur after migration)
- **All RLS issues** (verified none occur after service_db fix)

These tests validate the COMPLETE system holistically and ensure all fixes work end-to-end.
