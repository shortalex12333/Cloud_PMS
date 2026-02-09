# Phase 5: Action Execution Sanity - Summary

**Duration**: 3:30 - 4:15
**Status**: ✅ TEST SCRIPTS READY (Awaiting deployment/execution)

## Objectives

Verify that action execution endpoints:
1. Return 400/404 for invalid part_id (NOT 500)
2. Enforce role gating (crew denied MUTATE actions → 403)
3. Allow authorized roles (HOD can execute MUTATE actions → 200)
4. No server errors (500) for client mistakes

## Test Coverage

### Test 1: Invalid Part ID Handling

**Script**: `test_invalid_part_id.sh`

**Scenario**: Execute check_stock_level with non-existent part_id
```bash
POST /v1/actions/execute
{
  "action_id": "check_stock_level",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "part_id": "00000000-0000-0000-0000-000000000000"
}
```

**Expected Behavior**:
- Status code: 400 or 404 (client error)
- NOT 500 (server error)
- Error message indicates part not found

**Acceptance**:
- ✅ PASS if status = 400 or 404
- ❌ FAIL if status = 500 (server should not crash on bad client input)

### Test 2: Crew Role Gating (MUTATE Action)

**Script**: `test_crew_mutate_forbidden.sh`

**Scenario**: Crew attempts to execute log_part_usage (MUTATE action)
```bash
POST /v1/actions/execute
Authorization: Bearer <crew_jwt>

{
  "action_id": "log_part_usage",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "part_id": "12345678-1234-1234-1234-123456789012",
  "quantity_used": 1,
  "work_order_id": "12345678-1234-1234-1234-123456789012",
  "notes": "test"
}
```

**Expected Behavior**:
- Status code: 403 (forbidden)
- Error message indicates insufficient permissions
- Crew role NOT in log_part_usage.allowed_roles (requires engineer+)

**Acceptance**:
- ✅ PASS if status = 403
- ❌ FAIL if status = 200 (crew should not be able to mutate)

### Test 3: HOD Role Authorization (MUTATE Action)

**Script**: `test_hod_mutate_allowed.sh`

**Scenario**: chief_engineer (HOD) executes log_part_usage (MUTATE action)
```bash
POST /v1/actions/execute
Authorization: Bearer <hod_jwt>

{
  "action_id": "log_part_usage",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "part_id": "12345678-1234-1234-1234-123456789012",
  "quantity_used": 1,
  "work_order_id": "12345678-1234-1234-1234-123456789012",
  "notes": "test usage log"
}
```

**Expected Behavior**:
- Status code: 200 (success) if part and work order exist
- Status code: 404 (not found) if part/work order don't exist (still authorized)
- NOT 403 (HOD is in log_part_usage.allowed_roles)

**Acceptance**:
- ✅ PASS if status = 200 or 404
- ❌ FAIL if status = 403 (HOD should be authorized)

## Role Gating Contract

### log_part_usage Action

**From Action Registry** (`action_router/registry.py`):
```python
"log_part_usage": ActionDefinition(
    action_id="log_part_usage",
    label="Log Part Usage",
    endpoint="/v1/parts/log-usage",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    variant=ActionVariant.MUTATE,
    domain="parts",
)
```

**Role Authorization**:
| Role | Allowed? | Expected Status |
|------|----------|----------------|
| crew | ❌ NO | 403 |
| deckhand | ❌ NO | 403 |
| engineer | ✅ YES | 200/404 |
| chief_engineer | ✅ YES | 200/404 |
| captain | ✅ YES | 200/404 |

### Error Mapping Contract

**User's Non-Negotiables**:
> "Client errors map to 4xx; never 500 for client mistakes"

| Client Mistake | Expected Status | Example |
|----------------|----------------|---------|
| Invalid part_id | 404 | Part not found |
| Missing required field | 400 | Bad request |
| Wrong data type | 400 | Validation error |
| Insufficient permissions | 403 | Forbidden |
| Invalid yacht_id | 401/403 | Unauthorized/Forbidden |
| Invalid JWT | 401 | Unauthorized |

**Server Errors (500)** should ONLY occur for:
- Database connection failures
- Unhandled exceptions in business logic
- Infrastructure issues

## Test Scripts Created

1. **test_invalid_part_id.sh**
   - Tests error handling for non-existent part
   - Verifies 400/404 response (not 500)
   - Saves response to `invalid_part_id_response.txt`

2. **test_crew_mutate_forbidden.sh**
   - Tests role gating for crew + MUTATE action
   - Verifies 403 forbidden response
   - Saves response to `crew_mutate_response.txt`

3. **test_hod_mutate_allowed.sh**
   - Tests authorized role can execute MUTATE action
   - Verifies 200/404 response (not 403)
   - Saves response to `hod_mutate_response.txt`

4. **run_all_execution_tests.sh**
   - Comprehensive test runner
   - Executes all 3 tests in sequence
   - Displays summary with pass/fail indicators

## Execution

```bash
# Run all tests
bash test_artifacts/inventory/execution_sanity/run_all_execution_tests.sh

# Run individual tests
bash test_artifacts/inventory/execution_sanity/test_invalid_part_id.sh
bash test_artifacts/inventory/execution_sanity/test_crew_mutate_forbidden.sh
bash test_artifacts/inventory/execution_sanity/test_hod_mutate_allowed.sh
```

## Expected Output

```
==========================================================================
ACTION EXECUTION SANITY TESTS
==========================================================================

TEST 1: Invalid part_id handling
==========================================================================
Test: Execute action with invalid part_id
Action: check_stock_level
part_id: 00000000-0000-0000-0000-000000000000 (invalid)
Expected: 400 or 404 (client error), NOT 500

Status code: 404
✅ PASS: Received client error (404), not 500

TEST 2: Crew role gating (MUTATE action)
==========================================================================
Test: Crew attempts MUTATE action (log_part_usage)
Action: log_part_usage (MUTATE - requires engineer+)
Role: crew
Expected: 403 (forbidden)

Status code: 403
✅ PASS: Crew correctly forbidden from MUTATE action

TEST 3: HOD role authorization (MUTATE action)
==========================================================================
Test: HOD executes MUTATE action (log_part_usage)
Action: log_part_usage (MUTATE - requires engineer+)
Role: chief_engineer (HOD)
Expected: 200 (success) or 404 (part not found - still acceptable)

Status code: 404
✅ PASS: HOD authorized (404 means part/wo not found, not auth failure)

==========================================================================
SUMMARY
==========================================================================
Test 1: Invalid part_id → 404 ✅
Test 2: Crew + MUTATE action → 403 ✅
Test 3: HOD + MUTATE action → 404 ✅ (authorized)
==========================================================================
```

## Acceptance Criteria

✅ **Test scripts created**: 4 scripts for execution sanity testing
✅ **Invalid input handling**: Verify 400/404 for bad part_id (not 500)
✅ **Role gating enforced**: Verify crew denied MUTATE actions (403)
✅ **Authorized roles allowed**: Verify HOD can execute MUTATE actions (200/404)
⏳ **Execution results**: Pending deployment and execution

## Impact

### Security
- Role-based access control (RBAC) enforced at execution layer
- Crew cannot escalate privileges to execute MUTATE actions
- Invalid inputs don't crash server (no 500 errors)

### Reliability
- Client errors properly mapped to 4xx status codes
- Server errors (500) only for actual server failures
- Predictable error responses for debugging

### User Experience
- Clear error messages for invalid inputs
- Appropriate HTTP status codes guide client behavior
- Frontend can handle errors gracefully

## Next Phase

**Phase 6 (4:15-5:00): Docker Fast Loop**
- Run local inventory RLS suite
- Verify crew denied mutations, HOD allowed
- Verify invalid IDs map to 4xx, no 500s
- Save container logs to logs/

## Notes

⚠️ **Deployment Required**
These tests target the `/v1/actions/execute` endpoint which requires:
1. Action execution handlers deployed
2. RLS policies enforced
3. JWT validation working
4. Proper error handling middleware

The test scripts are ready but require a deployed environment to execute.
