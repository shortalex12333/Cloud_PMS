# REPOSITORY ORIENTATION: STEP 3 - GUARD RAILS & SAFETY

**Date:** 2026-01-22
**Purpose:** Document guard rail structure and enforcement (no assumptions)
**Status:** Truth documented

---

## GUARD RAIL TAXONOMY (Conceptual G0-G3)

**Note:** The codebase does NOT use "G0", "G1", "G2", "G3" labels. These are conceptual categories for understanding the gating system.

| Guard Rail | Description | Definition Location | Enforcement Location | Status |
|------------|-------------|---------------------|----------------------|--------|
| **G0: Always Allowed** | No restrictions | `triggers.roles: 'any'`, no status/condition checks | Not enforced (open access) | ✅ Conceptually correct |
| **G1: Role-Based** | Restricted by user role | `triggers.roles: ['chief_engineer', 'captain']` | `action_router/validators/role_validator.py` | ⚠️ Enforced for 64 registry actions, unknown for 18 undocumented |
| **G2: Status-Based** | Restricted by entity status | `triggers.status: ['open', 'diagnosed']` | Handler logic + frontend action offering | ⚠️ Partially enforced (frontend only?) |
| **G3: Multi-Condition** | Complex business rules | `triggers.conditions: [{...}]` | Handler logic | ⚠️ Not enforced centrally |

---

## G0: ALWAYS ALLOWED (No Restrictions)

### Definition

Actions that can be executed by **any role** at **any time** without **status or condition checks**.

**Registry pattern:**
```typescript
triggers: {
  roles: 'any',
  // No status restrictions
  // No conditions
}
```

### Examples from Registry

| Action ID | Side Effect | Description |
|-----------|-------------|-------------|
| `diagnose_fault` | read_only | Auto-runs when fault card appears |
| `add_fault_note` | mutation_light | Anyone can add notes to faults |
| `add_equipment_note` | mutation_light | Anyone can add notes to equipment |
| `view_fault_history` | read_only | Anyone can view fault history |
| `record_voice_note` | mutation_light | Anyone can record voice notes |

### Enforcement

**Location:** None (no enforcement needed)

**Risk:** Low for read_only actions. Medium for mutation_light actions (audit logging required).

**Violations:** None found (G0 is "no restrictions" by definition).

---

## G1: ROLE-BASED ACCESS CONTROL

### Definition

Actions restricted to specific user roles (e.g., HOD roles, engineer roles).

**Registry pattern:**
```typescript
triggers: {
  roles: ['chief_engineer', 'eto', 'captain', 'manager', 'admin'],
  // HOD_ROLES defined in registry
}
```

### Role Hierarchy (from microaction_registry.ts:132-134)

**HOD_ROLES (Head of Department):**
- `chief_engineer`
- `eto` (Electrical Technical Officer)
- `captain`
- `manager`
- `admin`

**ENGINEER_ROLES:**
- `engineer`
- `2nd_engineer`
- `chief_engineer`
- `eto`

**ALL_ROLES:**
- `member`, `crew`, `engineer`, `2nd_engineer`, `eto`, `chief_engineer`, `chief_officer`, `captain`, `manager`, `admin`

### Examples from Registry

| Action ID | Allowed Roles | Side Effect | Why Restricted? |
|-----------|---------------|-------------|-----------------|
| `create_work_order_from_fault` | HOD_ROLES | mutation_heavy | Only supervisors can create work orders |
| `approve_purchase` | HOD_ROLES | mutation_heavy | Financial approval authority |
| `assign_work_order` | HOD_ROLES | mutation_light | Work assignment authority |
| `mark_work_order_complete` | ENGINEER_ROLES | mutation_heavy | Technical sign-off authority |
| `tag_for_survey` | HOD_ROLES | mutation_light | Compliance/regulatory authority |

### Enforcement

**Location:** `apps/api/action_router/validators/role_validator.py`

**Function:** `validate_role_permission(user_context, allowed_roles, action_id)`

**Logic:**
1. Extract `user_role` from JWT context
2. Check if `user_role in allowed_roles`
3. Return `ValidationResult.failure(error_code="permission_denied")` if not authorized

**Code excerpt (role_validator.py:38-47):**
```python
# Check if user's role is in allowed list
if user_role not in allowed_roles:
    return ValidationResult.failure(
        error_code="permission_denied",
        message=f"Role '{user_role}' is not authorized to perform action '{action_id}'",
        details={
            "user_role": user_role,
            "allowed_roles": allowed_roles,
            "action_id": action_id,
        },
    )
```

### Violations

**64 registry actions:** ✅ Role restrictions documented and enforced

**18 undocumented actions:** ❌ Unknown if role restrictions enforced

| Action ID | Risk | Reason |
|-----------|------|--------|
| `report_fault` | HIGH | Fault creation should be role-restricted (prevents spam) |
| `delete_document` | HIGH | Data deletion should be HOD-only |
| `update_equipment_status` | HIGH | Equipment status changes should be engineer-only |
| `acknowledge_fault` | MEDIUM | Fault lifecycle should be role-restricted |
| `resolve_fault` | MEDIUM | Fault resolution should be engineer-only |
| `close_fault` | MEDIUM | Fault closure should be HOD-only |

**Next Step:** Audit handler code for 18 undocumented actions to determine if role checks exist.

---

## G2: STATUS-BASED TRIGGERING

### Definition

Actions that can only be executed when entity is in specific states.

**Registry pattern:**
```typescript
triggers: {
  status: ['diagnosed', 'acknowledged', 'open'],
  roles: 'any',
}
```

### Examples from Registry

| Action ID | Required Status | Side Effect | Why Status-Gated? |
|-----------|-----------------|-------------|-------------------|
| `create_work_order_from_fault` | ['diagnosed', 'acknowledged', 'open'] | mutation_heavy | Can't create WO for undiagnosed fault |
| `suggest_parts` | ['diagnosed'] | read_only | Parts suggestion requires diagnosis first |
| `mark_work_order_complete` | ['in_progress', 'assigned'] | mutation_heavy | Can't complete WO that hasn't started |
| `diagnose_fault` | ['reported', 'acknowledged', 'open'] | read_only | Can't diagnose already-diagnosed fault |

### Enforcement

**Location:** ⚠️ **NOT ENFORCED CENTRALLY**

**Current enforcement:**
1. **Frontend action offering** - Actions only shown if entity status matches
2. **Handler validation** - Some handlers check status, but not consistently

**Code pattern (expected but not verified):**
```python
# Example: create_work_order_from_fault handler
fault = db.query(...).first()
if fault.status not in ['diagnosed', 'acknowledged', 'open']:
    raise HTTPException(status_code=400, detail="Fault must be diagnosed first")
```

**Problem:** No central validation layer for status checks.

### Violations

**Known risks:**
1. ❌ Status checks not enforced in `action_router` validators
2. ❌ Handlers may skip status validation
3. ❌ API can be called directly, bypassing frontend gating

**Example violation scenario:**
```http
POST /v1/actions/execute
{
  "action": "create_work_order_from_fault",
  "payload": {"fault_id": "xxx"}  # Fault status = "closed"
}
```

**Expected:** HTTP 400 "Fault must be diagnosed first"

**Actual:** ❌ Unknown (depends on handler implementation)

**Next Step:** Audit all mutation_heavy handlers to verify status checks.

---

## G3: MULTI-CONDITION GATING

### Definition

Actions with complex business logic conditions beyond role/status.

**Registry pattern:**
```typescript
triggers: {
  roles: 'any',
  conditions: [
    {
      name: 'equipment_identified',
      type: 'entity_field',
      check: 'equipment_id',
      expected: 'not_null',
    },
  ],
}
```

### Condition Types (from microaction_registry.ts:50-59)

| Condition Type | Description | Example |
|----------------|-------------|---------|
| `entity_field` | Check field on current entity | `equipment_id` must not be null |
| `related_query` | Query related tables | Check if equipment has active maintenance contract |
| `user_context` | Check user metadata | User must have specific certification |

### Examples from Registry

| Action ID | Condition | Why Needed? |
|-----------|-----------|-------------|
| `show_manual_section` | `equipment_id != null` | Can't show manual without knowing equipment |
| `suggest_parts` | `ai_diagnosis.is_known == true` | Only suggest parts for known faults |
| (Others TBD from full registry review) | | |

### Enforcement

**Location:** ⚠️ **NOT ENFORCED CENTRALLY**

**Current enforcement:**
1. **Frontend action offering** - Actions only shown if conditions met
2. **Handler validation** - Handlers implement business logic checks

**Problem:** No central validation layer for complex conditions.

### Violations

**Known risks:**
1. ❌ Conditions not enforced in `action_router` validators
2. ❌ Handlers may skip condition checks
3. ❌ API can be called directly, bypassing frontend gating

**Next Step:** Audit handlers to verify condition enforcement.

---

## SECURITY INVARIANTS (Cross-Cutting Guards)

These are enforced for **ALL actions** regardless of G0-G3 classification.

### I4: JWT Validation MUST Succeed Before DB Access

**Location:** `apps/api/action_router/validators/jwt_validator.py`

**Function:** `validate_jwt(token) -> ValidationResult`

**Logic:**
1. Extract token from `Authorization` header
2. Remove `Bearer ` prefix
3. Try MASTER_SUPABASE_JWT_SECRET first, then TENANT_SUPABASE_JWT_SECRET
4. Decode JWT with HS256 algorithm
5. Verify expiration (`verify_exp=True`)
6. Extract user context: `user_id`, `yacht_id`, `role`, `email`
7. Return `ValidationResult.success(context={...})`

**Code excerpt (jwt_validator.py:66-71):**
```python
payload = jwt.decode(
    token,
    secret,
    algorithms=["HS256"],
    options={"verify_exp": True, "verify_aud": False},
)
```

**Enforcement:** ✅ All routes in `p0_actions_routes.py` call `validate_jwt()` first

**Violations:** None found. JWT validation is enforced.

---

### I5: Yacht Isolation MUST Be Enforced

**Location:** `apps/api/action_router/validators/yacht_validator.py`

**Function:** `validate_yacht_isolation(context, user_context) -> ValidationResult`

**Logic:**
1. Extract `context_yacht_id` from action payload
2. Extract `user_yacht_id` from JWT context
3. Verify both exist (not None)
4. Verify `context_yacht_id == user_yacht_id`
5. Return `ValidationResult.failure(error_code="yacht_mismatch")` if mismatch

**Code excerpt (yacht_validator.py:47-55):**
```python
# Verify yacht_id match
if context_yacht_id != user_yacht_id:
    return ValidationResult.failure(
        error_code="yacht_mismatch",
        message=f"Access denied: User yacht ({user_yacht_id}) does not match requested yacht ({context_yacht_id})",
        details={
            "user_yacht_id": user_yacht_id,
            "requested_yacht_id": context_yacht_id,
        },
    )
```

**Enforcement:** ✅ Routes call `validate_yacht_isolation()` after JWT validation

**Example (p0_actions_routes.py:264-267):**
```python
# Validate yacht isolation
yacht_result = validate_yacht_isolation(request.context, user_context)
if not yacht_result.valid:
    raise HTTPException(status_code=403, detail=yacht_result.error.message)
```

**Violations:** ⚠️ **RLS NOT TESTED** (0/64 actions have RLS tests)

**Risk:** Unknown if RLS policies in database actually enforce isolation. Application-level checks exist, but database-level isolation unverified.

**Next Step:** Write RLS tests for 5 critical actions (report_fault, create_work_order_from_fault, log_part_usage, upload_document, delete_document).

---

### I1: Row-Level Security (RLS) Enforces Yacht Isolation

**Location:** `database/migrations/01_core_tables_v2_secure.sql`

**Pattern (expected):**
```sql
CREATE POLICY "Yacht isolation" ON pms_equipment
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**Enforcement:** ⚠️ **NOT TESTED**

**Known status (from MATURITY_ASSESSMENT.md):**
- RLS policies exist on all tables (from migration files)
- 0/64 actions have RLS tests
- Unknown if policies are correct
- Unknown if `app.current_yacht_id` session variable is set correctly

**Violations:** ❌ RLS not tested = CRITICAL SECURITY RISK

**Next Step:** Create `tests/contracts/rls-proof/` tests for mutation_heavy actions.

---

### I3: No Mutation Without Auditability

**Definition:** Every INSERT/UPDATE/DELETE MUST create audit log entry.

**Expected Pattern:**
```python
# Mutation
db.insert('pms_work_orders', {...})

# Audit log
db.insert('audit_log', {
    'action': 'create_work_order',
    'entity_type': 'work_order',
    'entity_id': work_order_id,
    'user_id': user_id,
    'yacht_id': yacht_id,
    'changes': {...},
})
```

**Enforcement:** ⚠️ **NOT ENFORCED**

**Known status (from MATURITY_ASSESSMENT.md):**
- Only 4/64 actions have audit logging
- 60/64 actions violate I3
- No central audit middleware

**Violations:** ❌ I3 VIOLATED BY 60/64 ACTIONS

**Impact:** Compliance violations (ISO 9001, SOLAS), no audit trail, no forensics.

**Next Step:** Add audit logging to all 56 mutation actions (heavy + light).

---

## VALIDATION FLOW (How Guards Are Applied)

### Request Flow for Mutation Actions

```
1. Request arrives: POST /v1/actions/execute
   ↓
2. JWT Validation (I4)
   validate_jwt(authorization_header)
   → Extract: user_id, yacht_id, role, email
   → FAIL: HTTP 401 "Invalid token"
   ↓
3. Yacht Isolation (I5)
   validate_yacht_isolation(payload.context, jwt_context)
   → Compare: payload.yacht_id == jwt.yacht_id
   → FAIL: HTTP 403 "yacht_mismatch"
   ↓
4. Role-Based Access (G1)
   validate_role_permission(jwt_context, action.allowed_roles, action_id)
   → Check: jwt.role in action.triggers.roles
   → FAIL: HTTP 403 "permission_denied"
   ↓
5. Handler Logic (G2, G3)
   ⚠️ NOT CENTRALIZED
   - Status checks (G2): if entity.status not in allowed_statuses → HTTP 400
   - Condition checks (G3): if not meets_business_rule() → HTTP 400
   ↓
6. Database Mutation
   ⚠️ RLS NOT TESTED (I1)
   - RLS policies should filter by yacht_id
   - Unknown if actually enforced
   ↓
7. Audit Logging (I3)
   ⚠️ MISSING FOR 60/64 ACTIONS
   - Should insert audit_log entry
   - Most handlers skip this
   ↓
8. Response
   HTTP 200 {"status": "success", ...}
```

### Gaps in Validation Flow

| Step | Guard Rail | Enforcement | Status |
|------|------------|-------------|--------|
| 2 | JWT Validation (I4) | `jwt_validator.py` | ✅ Enforced |
| 3 | Yacht Isolation (I5) | `yacht_validator.py` | ✅ Application-level enforced |
| 4 | Role-Based Access (G1) | `role_validator.py` | ⚠️ Enforced for 64 actions, unknown for 18 |
| 5 | Status Checks (G2) | Handler logic | ❌ Not centralized |
| 5 | Condition Checks (G3) | Handler logic | ❌ Not centralized |
| 6 | RLS (I1) | Database policies | ❌ Not tested |
| 7 | Audit Logging (I3) | Handler logic | ❌ Missing for 60/64 actions |

---

## VALIDATION BYPASS RISKS

### Risk 1: Status Checks Not Enforced (G2)

**Scenario:** API called directly, bypassing frontend status gating.

**Example:**
```bash
curl -X POST /v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -d '{"action": "mark_work_order_complete", "payload": {"work_order_id": "xxx"}}'
# Work order status = "pending" (not "in_progress")
```

**Expected:** HTTP 400 "Work order must be in progress"

**Actual:** ❌ Unknown (depends on handler implementation)

**Mitigation:** Add central status validation in `action_router`.

---

### Risk 2: Condition Checks Not Enforced (G3)

**Scenario:** API called with missing preconditions.

**Example:**
```bash
curl -X POST /v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -d '{"action": "show_manual_section", "payload": {"fault_id": "xxx"}}'
# Fault has equipment_id = null (no equipment identified)
```

**Expected:** HTTP 400 "Equipment must be identified"

**Actual:** ❌ Unknown (depends on handler implementation)

**Mitigation:** Add central condition validation in `action_router`.

---

### Risk 3: RLS Bypass (I1)

**Scenario:** Application-level yacht isolation fails, RLS doesn't catch it.

**Example:**
```python
# Handler accidentally uses service role key (bypasses RLS)
supabase_admin = create_client(url, service_role_key)
supabase_admin.from_('pms_faults').insert({...})  # RLS BYPASSED
```

**Expected:** RLS blocks cross-yacht write

**Actual:** ❌ Unknown (RLS not tested)

**Mitigation:** Write RLS contract tests for all mutation_heavy actions.

---

### Risk 4: No Audit Logging (I3)

**Scenario:** Mutation succeeds but no audit trail.

**Example:**
```bash
# User deletes critical equipment document
curl -X POST /v1/actions/execute \
  -d '{"action": "delete_document", "payload": {"document_id": "xxx"}}'
# Returns HTTP 200, document deleted
# But: No audit_log entry created
```

**Impact:** No forensics, no compliance, no accountability.

**Mitigation:** Add audit logging to all 56 mutation actions.

---

## GUARD RAIL VIOLATIONS SUMMARY

| Violation | Severity | Count | Impact |
|-----------|----------|-------|--------|
| **G1: Role checks unknown for 18 actions** | HIGH | 18 | Possible authorization bypass |
| **G2: Status checks not centralized** | HIGH | ~40 | Can execute actions out of order |
| **G3: Condition checks not centralized** | MEDIUM | ~10 | Can execute actions without preconditions |
| **I1: RLS not tested** | CRITICAL | 64 | Cross-yacht data leaks possible |
| **I3: No audit logging** | CRITICAL | 60 | Compliance violations, no forensics |

---

## RECOMMENDATIONS

### Immediate (Day 1)

1. **Audit 18 undocumented actions for role checks** (2 hours)
   - Read handler code
   - Document which actions enforce role restrictions
   - Add to registry

2. **Write RLS tests for 5 critical actions** (1 hour)
   - `report_fault`, `create_work_order_from_fault`, `log_part_usage`, `upload_document`, `delete_document`
   - Test: User A creates entity → User B (different yacht) queries → Verify no access

### Week 1 (40 hours)

1. **Add audit logging to 60 actions** (8.5 hours)
   - Create `audit_logger.py` utility
   - Add to all mutation handlers

2. **Centralize status validation (G2)** (4 hours)
   - Create `status_validator.py`
   - Load status rules from registry
   - Enforce in `action_router`

3. **Centralize condition validation (G3)** (4 hours)
   - Create `condition_validator.py`
   - Load conditions from registry
   - Enforce in `action_router`

4. **Write RLS tests for all mutation_heavy actions** (8 hours)
   - 24 mutation_heavy actions
   - 20 minutes each

---

## SUMMARY: WHERE GUARD RAILS ARE

**Defined (Registry):**
- ✅ G0: `roles: 'any'` (always allowed)
- ✅ G1: `roles: [...]` (role-based)
- ✅ G2: `status: [...]` (status-based)
- ✅ G3: `conditions: [...]` (multi-condition)

**Enforced (Code):**
- ✅ I4: JWT validation (`jwt_validator.py`) - ALL actions
- ✅ I5: Yacht isolation (`yacht_validator.py`) - ALL actions
- ⚠️ G1: Role-based access (`role_validator.py`) - 64 actions, unknown for 18
- ❌ G2: Status checks (handler logic) - NOT centralized
- ❌ G3: Condition checks (handler logic) - NOT centralized
- ❌ I1: RLS (database policies) - NOT tested
- ❌ I3: Audit logging (handler logic) - MISSING for 60/64 actions

**Gap:**
- 18 actions with unknown role enforcement
- 40 actions with no central status validation
- 10 actions with no central condition validation
- 64 actions with no RLS tests
- 60 actions with no audit logging

**Truth:**
- JWT and yacht isolation are enforced (application-level)
- Role-based access is enforced for documented actions
- Status and condition checks are NOT centralized
- RLS is NOT tested (database-level isolation unknown)
- Audit logging is NOT enforced (compliance violation)

---

**Next:** STEP 4 - Current implementation status (percentage by cluster)

**Status:** STEP 3 complete. Guard rails documented.
