# 1-Week Autonomous Security Fix Plan

**Start Date**: 2026-02-10
**Target**: 164/164 failure mode tests passing (currently 80/164 = 49%)
**Scope**: Fix RBAC, RLS, Validation, Entity Checks across ALL action handlers

---

## Current State

```
VULNERABILITIES CONFIRMED:
├── RBAC NOT ENFORCED (P0) - Any role can do any action
├── RLS NOT ENFORCED (P0) - Cross-yacht data access possible
├── VALIDATION MISSING (P0) - Invalid data accepted
├── ENTITY CHECKS MISSING (P1) - Operations on non-existent items succeed
└── STATE MACHINE BROKEN (P1) - Invalid transitions allowed

AFFECTED DOMAINS:
├── Shopping List (6/33 = 18%)
├── Inventory (14/28 = 50%)
├── Equipment (18/36 = 50%)
├── Faults (15/35 = 43%)
└── Search (27/32 = 84%)
```

---

## Architecture Analysis

### Root Cause Location

All actions flow through:
```
Request → /v1/actions/execute → Action Router → Dispatcher → Handler
```

**Key Files**:
```
apps/api/
├── routes/p0_actions_routes.py          # Main router (5000+ lines)
├── action_router/
│   ├── registry.py                      # Action definitions with allowed_roles
│   ├── dispatchers/
│   │   └── internal_dispatcher.py       # Dispatches to handlers
│   └── middleware/                      # WHERE FIXES GO
├── handlers/
│   ├── inventory_handlers.py            # Inventory actions
│   ├── shopping_list_handlers.py        # Shopping list actions
│   ├── equipment_handlers.py            # Equipment actions
│   ├── fault_handlers.py                # Fault actions
│   └── ...
└── utils/
    └── validation.py                    # Input validation utilities
```

### Fix Strategy

**ONE middleware fix = ALL domains fixed**

Instead of fixing each handler individually (131 actions), add middleware that:
1. Checks RBAC before dispatch
2. Validates yacht_id ownership
3. Validates input schemas
4. Checks entity existence

---

## Day-by-Day Execution Plan

### DAY 1 (Monday): RBAC Middleware

**Goal**: CREW cannot perform HOD-only actions

**Files to Create/Modify**:
```
apps/api/action_router/middleware/rbac_middleware.py (NEW)
apps/api/action_router/dispatcher.py (MODIFY)
```

**Implementation**:
```python
# apps/api/action_router/middleware/rbac_middleware.py

from typing import Dict, Any
from ..registry import ACTION_REGISTRY

class RBACError(Exception):
    def __init__(self, role: str, action: str):
        self.code = "FORBIDDEN"
        self.message = f"Role '{role}' is not authorized to perform action '{action}'"

def check_rbac(user_role: str, action: str) -> None:
    """Check if user role is allowed to perform action."""
    action_def = ACTION_REGISTRY.get(action)
    if not action_def:
        raise ValueError(f"Unknown action: {action}")

    allowed_roles = action_def.allowed_roles
    if user_role.lower() not in [r.lower() for r in allowed_roles]:
        raise RBACError(user_role, action)
```

**Integration Point** (p0_actions_routes.py):
```python
# Add at start of execute_action endpoint
from action_router.middleware.rbac_middleware import check_rbac, RBACError

@router.post("/v1/actions/execute")
async def execute_action(request: ActionRequest):
    try:
        # Get user role from JWT
        user_role = get_user_role(request.context.user_id)

        # RBAC CHECK - NEW
        check_rbac(user_role, request.action)

        # Continue to dispatch...
    except RBACError as e:
        return {"success": False, "code": e.code, "message": e.message}
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts --grep "RBAC|403|FORBIDDEN"
```

**Success Criteria**:
- [ ] CREW cannot approve_shopping_list_item → 403
- [ ] CREW cannot reject_shopping_list_item → 403
- [ ] CREW cannot decommission_equipment → 403
- [ ] CREW cannot close_fault → 403
- [ ] CREW cannot diagnose_fault → 403
- [ ] HOD CAN still perform these actions → 200

**Expected Test Delta**: +15 tests passing

---

### DAY 2 (Tuesday): RLS/Yacht Isolation Middleware

**Goal**: Users cannot access data from other yachts

**Files to Create/Modify**:
```
apps/api/action_router/middleware/rls_middleware.py (NEW)
apps/api/utils/yacht_validator.py (NEW)
```

**Implementation**:
```python
# apps/api/action_router/middleware/rls_middleware.py

from supabase import Client

class RLSError(Exception):
    def __init__(self, entity_type: str, entity_id: str):
        self.code = "NOT_FOUND"  # Don't reveal existence
        self.message = f"{entity_type} not found: {entity_id}"

async def validate_entity_yacht(
    db: Client,
    entity_type: str,
    entity_id: str,
    user_yacht_id: str
) -> bool:
    """Verify entity belongs to user's yacht."""

    table_map = {
        "shopping_list_item": "shopping_list",
        "part": "pms_parts",
        "equipment": "pms_equipment",
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
    }

    table = table_map.get(entity_type)
    if not table:
        return True  # Unknown entity type, skip check

    result = db.table(table).select("yacht_id").eq("id", entity_id).single().execute()

    if not result.data:
        raise RLSError(entity_type, entity_id)

    if result.data["yacht_id"] != user_yacht_id:
        raise RLSError(entity_type, entity_id)

    return True
```

**Integration** - Extract entity IDs from payload:
```python
# apps/api/action_router/middleware/rls_middleware.py

ENTITY_ID_FIELDS = {
    "item_id": "shopping_list_item",
    "part_id": "part",
    "equipment_id": "equipment",
    "fault_id": "fault",
    "work_order_id": "work_order",
}

async def check_rls(db: Client, payload: dict, user_yacht_id: str) -> None:
    """Check all entity IDs in payload belong to user's yacht."""
    for field, entity_type in ENTITY_ID_FIELDS.items():
        if field in payload and payload[field]:
            await validate_entity_yacht(db, entity_type, payload[field], user_yacht_id)
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts --grep "cross-yacht|RLS|Cross-Yacht"
```

**Success Criteria**:
- [ ] Cross-yacht item_id → 404 NOT_FOUND
- [ ] Cross-yacht part_id → 404 NOT_FOUND
- [ ] Cross-yacht equipment_id → 404 NOT_FOUND
- [ ] Cross-yacht fault_id → 404 NOT_FOUND
- [ ] Same-yacht entities → Still accessible

**Expected Test Delta**: +20 tests passing

---

### DAY 3 (Wednesday): Input Validation Middleware

**Goal**: Reject invalid UUIDs, negative numbers, invalid enums, empty required fields

**Files to Create/Modify**:
```
apps/api/action_router/middleware/validation_middleware.py (NEW)
apps/api/action_router/schemas/ (NEW directory)
apps/api/action_router/schemas/shopping_list.py
apps/api/action_router/schemas/inventory.py
apps/api/action_router/schemas/equipment.py
apps/api/action_router/schemas/faults.py
```

**Implementation**:
```python
# apps/api/action_router/middleware/validation_middleware.py

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, validator, Field

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

class ValidationError(Exception):
    def __init__(self, field: str, message: str, code: str = "VALIDATION_FAILED"):
        self.code = code
        self.field = field
        self.message = message

def validate_uuid(value: str, field_name: str) -> str:
    if not value or not UUID_REGEX.match(str(value)):
        raise ValidationError(field_name, f"Invalid UUID format for {field_name}", "VALIDATION_FAILED")
    return value

def validate_positive_int(value: int, field_name: str) -> int:
    if value is None or value <= 0:
        raise ValidationError(field_name, f"{field_name} must be greater than 0", "MISSING_REQUIRED_FIELD")
    return value

def validate_enum(value: str, allowed: List[str], field_name: str) -> str:
    if value not in allowed:
        raise ValidationError(field_name, f"Invalid {field_name}. Must be one of: {', '.join(allowed)}", "VALIDATION_FAILED")
    return value

def validate_required_string(value: str, field_name: str) -> str:
    if not value or not str(value).strip():
        raise ValidationError(field_name, f"{field_name} is required", "MISSING_REQUIRED_FIELD")
    return value
```

**Schema Example**:
```python
# apps/api/action_router/schemas/shopping_list.py

from pydantic import BaseModel, validator
from typing import Optional
from ..middleware.validation_middleware import *

VALID_URGENCY = ["low", "normal", "high", "critical"]
VALID_SOURCE_TYPES = ["manual_add", "work_order", "pm_schedule", "conversation"]

class CreateShoppingListItemSchema(BaseModel):
    part_name: str
    quantity_requested: int
    urgency: str
    source_type: str
    manufacturer: Optional[str] = None
    notes: Optional[str] = None

    @validator('part_name')
    def validate_part_name(cls, v):
        return validate_required_string(v, 'part_name')

    @validator('quantity_requested')
    def validate_quantity(cls, v):
        return validate_positive_int(v, 'quantity_requested')

    @validator('urgency')
    def validate_urgency(cls, v):
        return validate_enum(v, VALID_URGENCY, 'urgency')

    @validator('source_type')
    def validate_source_type(cls, v):
        return validate_enum(v, VALID_SOURCE_TYPES, 'source_type')

class ApproveShoppingListItemSchema(BaseModel):
    item_id: str
    quantity_approved: int

    @validator('item_id')
    def validate_item_id(cls, v):
        return validate_uuid(v, 'item_id')

    @validator('quantity_approved')
    def validate_quantity(cls, v):
        return validate_positive_int(v, 'quantity_approved')
```

**Schema Registry**:
```python
# apps/api/action_router/schemas/__init__.py

from .shopping_list import *
from .inventory import *
from .equipment import *
from .faults import *

ACTION_SCHEMAS = {
    "create_shopping_list_item": CreateShoppingListItemSchema,
    "approve_shopping_list_item": ApproveShoppingListItemSchema,
    "reject_shopping_list_item": RejectShoppingListItemSchema,
    # ... all 131 actions
}

def validate_payload(action: str, payload: dict) -> dict:
    schema = ACTION_SCHEMAS.get(action)
    if schema:
        return schema(**payload).dict()
    return payload  # No schema defined, pass through
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts --grep "Invalid|Negative|Missing|Empty|Null"
```

**Success Criteria**:
- [ ] Invalid UUID → 400 VALIDATION_FAILED
- [ ] Negative quantity → 400 VALIDATION_FAILED
- [ ] Zero quantity → 400 MISSING_REQUIRED_FIELD
- [ ] Empty part_name → 400 MISSING_REQUIRED_FIELD
- [ ] Invalid urgency → 400 VALIDATION_FAILED
- [ ] Invalid source_type → 400 VALIDATION_FAILED

**Expected Test Delta**: +25 tests passing

---

### DAY 4 (Thursday): Entity Existence Checks

**Goal**: Operations on non-existent entities return 404

**Files to Modify**:
```
apps/api/action_router/middleware/rls_middleware.py (EXTEND)
```

**Implementation** - The RLS middleware already queries the database, so entity existence is checked implicitly. Just need to ensure proper error handling:

```python
# apps/api/action_router/middleware/rls_middleware.py

async def validate_entity_exists(
    db: Client,
    entity_type: str,
    entity_id: str,
    user_yacht_id: str
) -> dict:
    """Verify entity exists and belongs to user's yacht. Return entity data."""

    table_map = {
        "shopping_list_item": ("shopping_list", "id"),
        "part": ("pms_parts", "id"),
        "equipment": ("pms_equipment", "id"),
        "fault": ("pms_faults", "id"),
        "work_order": ("pms_work_orders", "id"),
    }

    if entity_type not in table_map:
        return None

    table, id_field = table_map[entity_type]

    result = db.table(table).select("*").eq(id_field, entity_id).single().execute()

    if not result.data:
        raise EntityNotFoundError(entity_type, entity_id)

    if result.data.get("yacht_id") != user_yacht_id:
        raise EntityNotFoundError(entity_type, entity_id)  # Don't reveal existence

    return result.data
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts --grep "non-existent|NOT_FOUND|404"
```

**Success Criteria**:
- [ ] Approve non-existent item → 404 NOT_FOUND
- [ ] Reject non-existent item → 404 NOT_FOUND
- [ ] Update non-existent equipment → 404 NOT_FOUND
- [ ] Close non-existent fault → 404 NOT_FOUND
- [ ] View history of non-existent item → 404 NOT_FOUND

**Expected Test Delta**: +15 tests passing

---

### DAY 5 (Friday): State Machine Validation

**Goal**: Invalid state transitions return INVALID_STATE_TRANSITION

**Files to Create**:
```
apps/api/action_router/middleware/state_machine.py (NEW)
```

**Implementation**:
```python
# apps/api/action_router/middleware/state_machine.py

from typing import Dict, List, Set

class InvalidStateTransitionError(Exception):
    def __init__(self, current_status: str, action: str):
        self.code = "INVALID_STATE_TRANSITION"
        self.message = f"Cannot perform '{action}' on item with status '{current_status}'"

# Valid transitions per domain
SHOPPING_LIST_TRANSITIONS = {
    "candidate": {"approve", "reject"},
    "approved": {"promote"},
    "rejected": set(),  # Terminal state
    "promoted": set(),  # Terminal state
}

FAULT_TRANSITIONS = {
    "open": {"acknowledge", "mark_false_alarm"},
    "acknowledged": {"diagnose", "close", "mark_false_alarm"},
    "diagnosed": {"close"},
    "closed": {"reopen"},
    "false_alarm": set(),  # Terminal
}

EQUIPMENT_TRANSITIONS = {
    "operational": {"decommission", "archive", "flag_attention"},
    "attention_required": {"decommission", "archive", "clear_attention"},
    "decommissioned": set(),  # Terminal
    "archived": {"restore"},
}

def validate_state_transition(
    domain: str,
    current_status: str,
    action: str
) -> None:
    """Validate state transition is allowed."""

    transitions = {
        "shopping_list": SHOPPING_LIST_TRANSITIONS,
        "fault": FAULT_TRANSITIONS,
        "equipment": EQUIPMENT_TRANSITIONS,
    }.get(domain, {})

    allowed_actions = transitions.get(current_status, set())

    # Extract action verb (approve_shopping_list_item → approve)
    action_verb = action.split("_")[0]

    if allowed_actions and action_verb not in allowed_actions:
        raise InvalidStateTransitionError(current_status, action)
```

**Integration**:
```python
# In action handler, after fetching entity:
entity = await validate_entity_exists(db, "shopping_list_item", item_id, yacht_id)
validate_state_transition("shopping_list", entity["status"], action)
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts --grep "state|transition|rejected|approved|double"
```

**Success Criteria**:
- [ ] Approve rejected item → 400 INVALID_STATE_TRANSITION
- [ ] Reject approved item → 400 INVALID_STATE_TRANSITION
- [ ] Promote non-approved item → 400 INVALID_STATE_TRANSITION
- [ ] Close non-acknowledged fault → 400 INVALID_STATE_TRANSITION
- [ ] Reopen non-closed fault → 400 INVALID_STATE_TRANSITION

**Expected Test Delta**: +10 tests passing

---

### DAY 6 (Saturday): Integration & Error Handling

**Goal**: Wire all middleware together, standardize error responses

**Files to Create/Modify**:
```
apps/api/action_router/middleware/__init__.py (NEW)
apps/api/action_router/execute.py (MODIFY or NEW)
apps/api/utils/error_responses.py (NEW)
```

**Unified Middleware Pipeline**:
```python
# apps/api/action_router/middleware/__init__.py

from .rbac_middleware import check_rbac, RBACError
from .rls_middleware import check_rls, validate_entity_exists, RLSError, EntityNotFoundError
from .validation_middleware import validate_payload, ValidationError
from .state_machine import validate_state_transition, InvalidStateTransitionError

class MiddlewarePipeline:
    """Execute all middleware checks in order."""

    async def execute(
        self,
        db: Client,
        action: str,
        payload: dict,
        context: dict
    ) -> dict:
        """Run all middleware. Raises on failure."""

        user_id = context.get("user_id")
        yacht_id = context.get("yacht_id")

        # 1. RBAC Check
        user_role = await self.get_user_role(db, user_id)
        check_rbac(user_role, action)

        # 2. Validate payload schema
        validated_payload = validate_payload(action, payload)

        # 3. RLS Check - verify all entity IDs belong to user's yacht
        await check_rls(db, validated_payload, yacht_id)

        # 4. Entity existence check (also fetches entity for state check)
        entity = await self.fetch_primary_entity(db, action, validated_payload, yacht_id)

        # 5. State machine check
        if entity:
            domain = self.get_domain(action)
            validate_state_transition(domain, entity.get("status"), action)

        return validated_payload

    async def get_user_role(self, db: Client, user_id: str) -> str:
        result = db.table("user_accounts").select("role").eq("id", user_id).single().execute()
        return result.data.get("role", "crew") if result.data else "crew"

    def get_domain(self, action: str) -> str:
        if "shopping_list" in action:
            return "shopping_list"
        if "fault" in action:
            return "fault"
        if "equipment" in action:
            return "equipment"
        if "work_order" in action:
            return "work_order"
        return "unknown"
```

**Standardized Error Responses**:
```python
# apps/api/utils/error_responses.py

from fastapi.responses import JSONResponse

def error_response(code: str, message: str, status_code: int = 400) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code,
            "message": message
        }
    )

ERROR_STATUS_CODES = {
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "VALIDATION_FAILED": 400,
    "MISSING_REQUIRED_FIELD": 400,
    "INVALID_STATE_TRANSITION": 400,
    "UNAUTHORIZED": 401,
}

def handle_middleware_error(error: Exception) -> JSONResponse:
    """Convert middleware exceptions to API responses."""
    if hasattr(error, 'code'):
        status = ERROR_STATUS_CODES.get(error.code, 400)
        return error_response(error.code, str(error.message), status)
    return error_response("INTERNAL_ERROR", str(error), 500)
```

**Test Command**:
```bash
npx playwright test tests/e2e/*-failure-modes.spec.ts
```

**Success Criteria**:
- [ ] All error codes match expected format
- [ ] No 500 errors for client errors
- [ ] Consistent response structure

**Expected Test Delta**: +5 tests passing (error format fixes)

---

### DAY 7 (Sunday): Full Test Suite & Documentation

**Goal**: 164/164 tests passing, document all changes

**Morning: Run Full Test Suite**
```bash
# Run all failure mode tests
npx playwright test tests/e2e/*-failure-modes.spec.ts --reporter=html

# Run comprehensive tests to ensure no regressions
npx playwright test tests/e2e/shopping-list-lens-comprehensive.spec.ts
```

**Expected Final Results**:
```
Feature          | Before | After  | Delta
-----------------|--------|--------|-------
Shopping List    | 6/33   | 33/33  | +27
Inventory        | 14/28  | 28/28  | +14
Search           | 27/32  | 32/32  | +5
Equipment        | 18/36  | 36/36  | +18
Faults           | 15/35  | 35/35  | +20
-----------------|--------|--------|-------
TOTAL            | 80/164 | 164/164| +84
```

**Afternoon: Documentation**

Create `SECURITY_FIX_CHANGELOG.md`:
```markdown
# Security Fix Changelog

## Week of 2026-02-10

### RBAC Enforcement
- Added `rbac_middleware.py` - checks user role against action registry
- All 131 actions now enforce role restrictions
- CREW blocked from HOD-only actions

### RLS Enforcement
- Added `rls_middleware.py` - validates yacht ownership
- Cross-yacht entity access now returns 404
- No data leakage between tenants

### Input Validation
- Added Pydantic schemas for all action payloads
- UUID format validation
- Positive integer validation
- Enum validation (urgency, source_type, severity, status)
- Required field validation

### Entity Existence Checks
- All operations verify entity exists before proceeding
- Non-existent entities return 404 NOT_FOUND

### State Machine Validation
- Added transition rules for Shopping List, Faults, Equipment
- Invalid transitions return INVALID_STATE_TRANSITION
- Idempotent operations handled gracefully

### Files Changed
- apps/api/action_router/middleware/rbac_middleware.py (NEW)
- apps/api/action_router/middleware/rls_middleware.py (NEW)
- apps/api/action_router/middleware/validation_middleware.py (NEW)
- apps/api/action_router/middleware/state_machine.py (NEW)
- apps/api/action_router/middleware/__init__.py (NEW)
- apps/api/action_router/schemas/*.py (NEW)
- apps/api/routes/p0_actions_routes.py (MODIFIED)
- apps/api/utils/error_responses.py (NEW)
```

---

## Test Verification Pipeline

### After Each Fix

```bash
#!/bin/bash
# scripts/verify_security_fixes.sh

echo "=== Running Security Fix Verification ==="

# 1. Run failure mode tests
echo "Running failure mode tests..."
npx playwright test tests/e2e/*-failure-modes.spec.ts --reporter=list

# 2. Run comprehensive tests (regression check)
echo "Running comprehensive tests..."
npx playwright test tests/e2e/shopping-list-lens-comprehensive.spec.ts --reporter=list

# 3. Summary
echo "=== Test Summary ==="
npx playwright test tests/e2e/*-failure-modes.spec.ts --reporter=json | jq '.suites[] | {name: .title, passed: ([.specs[] | select(.ok)] | length), failed: ([.specs[] | select(.ok | not)] | length)}'
```

### Success Definition

| Metric | Target | Current |
|--------|--------|---------|
| Failure mode tests | 164/164 (100%) | 80/164 (49%) |
| Comprehensive tests | 36/36 (100%) | 36/36 (100%) |
| No 500 errors | 0 | Multiple |
| RBAC enforced | All 131 actions | 0 actions |
| RLS enforced | All entities | 0 entities |

### Failure Definition

- Any 500 error on client input = FAIL
- Any RBAC bypass = FAIL
- Any cross-yacht data access = FAIL
- Any invalid state transition allowed = FAIL
- Regression in comprehensive tests = FAIL

---

## File Changes Summary

### New Files (8)
```
apps/api/action_router/middleware/
├── __init__.py
├── rbac_middleware.py
├── rls_middleware.py
├── validation_middleware.py
└── state_machine.py

apps/api/action_router/schemas/
├── __init__.py
├── shopping_list.py
├── inventory.py
├── equipment.py
└── faults.py

apps/api/utils/
└── error_responses.py
```

### Modified Files (2)
```
apps/api/routes/p0_actions_routes.py
apps/api/action_router/registry.py (if needed)
```

---

## Rollback Plan

If fixes cause production issues:

```bash
# Revert middleware integration
git revert HEAD~1  # or specific commit

# Disable middleware (quick fix)
# In p0_actions_routes.py, comment out:
# middleware_result = await middleware.execute(...)
```

---

## Daily Checklist

### Each Day
- [ ] Run `npx playwright test tests/e2e/*-failure-modes.spec.ts`
- [ ] Check no regressions in comprehensive tests
- [ ] Commit changes with descriptive message
- [ ] Update progress in this document

### End of Week
- [ ] All 164 failure mode tests passing
- [ ] All 36 comprehensive tests passing
- [ ] No 500 errors in test suite
- [ ] Documentation complete
- [ ] Code reviewed and merged

---

## Progress Tracking

| Day | Focus | Tests Before | Tests After | Status |
|-----|-------|--------------|-------------|--------|
| 1 | RBAC | 80/164 | TBD | ⏳ |
| 2 | RLS | TBD | TBD | ⏳ |
| 3 | Validation | TBD | TBD | ⏳ |
| 4 | Entity Checks | TBD | TBD | ⏳ |
| 5 | State Machine | TBD | TBD | ⏳ |
| 6 | Integration | TBD | TBD | ⏳ |
| 7 | Final Testing | TBD | 164/164 | ⏳ |

---

## Autonomous Execution Protocol

I will:
1. Read the relevant handler/router files
2. Implement the middleware as specified
3. Run the test suite locally
4. Fix any issues until tests pass
5. Move to next day's task
6. Repeat until 164/164

No user interaction needed unless:
- Database schema changes required
- Deployment needed
- Credentials/access issues

---

**Plan Created**: 2026-02-10
**Estimated Completion**: 2026-02-17
**Target**: 164/164 tests passing (100%)
