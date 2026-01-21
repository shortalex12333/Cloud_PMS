# E006: PHASE 5 - HANDLER DATA FLOW VERIFICATION

**Date:** 2026-01-21
**Phase:** 5 - Handler Data Flow
**Auditor:** Claude B
**Status:** ISSUES FOUND

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Silent Audit Log Failures | 4 | 🟡 MEDIUM |
| Missing Entity Ownership Validation | 3 | 🟡 MEDIUM |
| Storage Path Without Yacht Check | 1 | 🟠 HIGH |

---

## Architecture Overview

The action system follows a 10-step validation pipeline:

```
Request → JWT Validation → Tenant Lookup → Yacht Isolation Check →
Role Validation → Param Merge → Field Validation → Schema Validation →
Handler Dispatch → Audit Log → Response
```

**Files Audited:**
- `apps/api/action_router/router.py` (408 lines)
- `apps/api/action_router/validators/yacht_validator.py` (62 lines)
- `apps/api/action_router/dispatchers/internal_dispatcher.py` (2034 lines)
- `apps/api/action_router/registry.py` (600+ lines)

---

## ✅ VERIFIED: Router-Level Validation Pipeline

**Location:** `router.py:65-391`

The router correctly enforces:
1. ✅ JWT validation (step 1)
2. ✅ Tenant lookup from MASTER DB (step 1.5)
3. ✅ Action existence check (step 2)
4. ✅ Yacht isolation validation (step 3)
5. ✅ Role permission check (step 4)
6. ✅ Required field validation (step 6)
7. ✅ Schema validation (step 7)
8. ✅ Error logging before all HTTPExceptions
9. ✅ Success logging with duration_ms

**Yacht Isolation Check:**
```python
# yacht_validator.py:47-55
if context_yacht_id != user_yacht_id:
    return ValidationResult.failure(
        error_code="yacht_mismatch",
        message=f"Access denied: User yacht ({user_yacht_id}) does not match requested yacht ({context_yacht_id})",
    )
```

---

## 🟠 HIGH: Storage Path Without Yacht Validation

### Location
**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Function:** `open_document()`
**Lines:** 195-221

### Code
```python
async def open_document(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a signed URL for a document.

    Required params:
        - storage_path: str (path in Supabase storage)
    """
    supabase = get_supabase_client()

    result = supabase.storage.from_("documents").create_signed_url(
        params["storage_path"],  # NO YACHT_ID VALIDATION
        expires_in=3600,
    )
```

### Registry Definition
```python
# registry.py:195-204
"open_document": ActionDefinition(
    ...
    required_fields=["storage_path"],  # NO yacht_id REQUIRED
    ...
)
```

### Impact
- User can request signed URL for ANY path in documents bucket
- No verification that path belongs to user's yacht
- Storage paths typically include yacht_id prefix (e.g., `{yacht_id}/file.pdf`)
- Attacker needs to know/guess path, but no server-side enforcement

### Attack Vector
```bash
# User authenticated to yacht_A
curl -X POST ".../v1/actions/execute" \
  -d '{
    "action": "open_document",
    "context": {"yacht_id": "yacht_A"},
    "payload": {"storage_path": "yacht_B/sensitive_document.pdf"}
  }'
# Result: Returns signed URL for yacht_B's document
```

### Recommended Fix
```python
async def open_document(params: Dict[str, Any]) -> Dict[str, Any]:
    yacht_id = params["yacht_id"]  # Now required
    storage_path = params["storage_path"]

    # Verify path starts with user's yacht_id
    if not storage_path.startswith(f"{yacht_id}/"):
        raise ValueError("Access denied: Document does not belong to your yacht")

    result = supabase.storage.from_("documents").create_signed_url(...)
```

---

## 🟡 MEDIUM: Missing Entity Ownership Validation

### Issue 1: `add_note` Handler

**Location:** `internal_dispatcher.py:85-112`

**Problem:** Inserts note with `equipment_id` without verifying equipment belongs to yacht.

```python
async def add_note(params: Dict[str, Any]) -> Dict[str, Any]:
    result = supabase.table("notes").insert({
        "yacht_id": params["yacht_id"],
        "equipment_id": params["equipment_id"],  # NOT VERIFIED
        ...
    }).execute()
```

**Compare with correct pattern:**
```python
# add_note_to_work_order (lines 129-131) - CORRECT
wo_result = supabase.table("pms_work_orders").select(...).eq(
    "id", params["work_order_id"]
).eq("yacht_id", params["yacht_id"]).execute()  # VERIFIES OWNERSHIP

if not wo_result.data:
    raise ValueError("...not found or access denied")
```

### Issue 2: `report_fault` Handler

**Location:** `internal_dispatcher.py:537-572`

**Problem:** Inserts fault with `equipment_id` without verifying equipment belongs to yacht.

```python
async def report_fault(params: Dict[str, Any]) -> Dict[str, Any]:
    fault_data = {
        "yacht_id": params["yacht_id"],
        "equipment_id": params["equipment_id"],  # NOT VERIFIED
        ...
    }
    result = supabase.table("pms_faults").insert(fault_data).execute()
```

### Issue 3: `add_to_handover` Handler

**Location:** `internal_dispatcher.py:339-417`

**Problem:** Inserts handover item with `entity_id` without verifying entity belongs to yacht.

```python
handover_entry = {
    "yacht_id": params["yacht_id"],
    "entity_id": params.get("entity_id"),  # NOT VERIFIED
    ...
}
```

### Impact
- Data integrity issue (not data disclosure)
- User can create notes/faults/handover items referencing entity UUIDs from other yachts
- Records have user's yacht_id so won't appear for other yacht
- Requires knowing foreign entity UUIDs

### Recommended Fix Pattern
```python
# Before INSERT, verify entity belongs to yacht
eq_result = supabase.table("pms_equipment").select("id").eq(
    "id", params["equipment_id"]
).eq("yacht_id", params["yacht_id"]).execute()

if not eq_result.data:
    raise ValueError(f"Equipment {params['equipment_id']} not found or access denied")

# Then proceed with INSERT
```

---

## 🟡 MEDIUM: Silent Audit Log Failures

### Locations (4 instances)

| Line | Function | Pattern |
|------|----------|---------|
| 326-327 | `update_equipment_status` | `except Exception: pass` |
| 405-406 | `add_to_handover` | `except Exception: pass` |
| 468-469 | `delete_document` | `except Exception: pass` |
| 521-522 | `delete_shopping_item` | `except Exception: pass` |

### Code Pattern
```python
# Create audit log
try:
    supabase.table("pms_audit_log").insert({...}).execute()
except Exception:
    pass  # Don't fail if audit log fails
```

### Impact
- Audit log failures are silently swallowed
- No way to detect if audit logging is broken
- Operations succeed but audit trail is incomplete
- Could mask database permission or connectivity issues

### Recommended Fix
```python
try:
    supabase.table("pms_audit_log").insert({...}).execute()
except Exception as e:
    logger.warning(f"Audit log failed for {action}: {e}")
    # Optionally: emit metric for monitoring
```

---

## ✅ VERIFIED: Proper yacht_id Validation Patterns

The following handlers correctly verify entity ownership:

| Handler | Line | Pattern |
|---------|------|---------|
| `add_note_to_work_order` | 129-131 | SELECT + yacht_id filter |
| `close_work_order` | 181-183 | UPDATE + yacht_id filter |
| `edit_handover_section` | 237-239, 256 | SELECT + UPDATE + yacht_id filter |
| `update_equipment_status` | 282-284, 307-309 | SELECT + UPDATE + yacht_id filter |
| `delete_document` | 433-435, 451 | SELECT + UPDATE + yacht_id filter |
| `delete_shopping_item` | 491-493, 505-507 | SELECT + DELETE + yacht_id filter |
| `close_fault` | 590 | UPDATE + yacht_id filter |

---

## ✅ VERIFIED: Exception Handling at Router Level

**Location:** `router.py:291-390`

Exceptions are properly categorized and logged:

| Exception Type | HTTP Status | Error Code |
|----------------|-------------|------------|
| `ValueError` | 400 | handler_validation_error |
| `Exception` (handler) | 502 | handler_execution_error |
| `Exception` (catch-all) | 500 | internal_server_error |

All exceptions are logged before raising HTTPException.

---

## Recommendations

### P1 Priority (Should Fix)

1. **open_document path validation**
   - Add yacht_id to required_fields
   - Validate storage_path starts with yacht_id prefix

2. **Entity ownership validation** for:
   - `add_note` - verify equipment_id belongs to yacht
   - `report_fault` - verify equipment_id belongs to yacht
   - `add_to_handover` - verify entity_id belongs to yacht

### P2 Priority (Should Address)

3. **Silent audit failures**
   - Replace `pass` with `logger.warning()`
   - Consider adding metrics for audit log failure rate

---

## Test Commands

### Test 1: Cross-Yacht Document Access
```bash
# Authenticated as yacht_A user
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $YACHT_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open_document",
    "context": {"yacht_id": "yacht_A_id"},
    "payload": {"storage_path": "yacht_B_id/confidential.pdf"}
  }'

# Expected with bug: 200 OK with signed URL for yacht_B's document
# Expected fixed: 400 Bad Request "Document does not belong to your yacht"
```

### Test 2: Cross-Yacht Equipment Reference
```bash
# Authenticated as yacht_A user, using equipment_id from yacht_B
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $YACHT_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_note",
    "context": {"yacht_id": "yacht_A_id"},
    "payload": {"equipment_id": "yacht_B_equipment_uuid", "note_text": "test"}
  }'

# Expected with bug: 200 OK, note created with foreign equipment_id
# Expected fixed: 400 Bad Request "Equipment not found or access denied"
```

---

**Evidence File:** E006_PHASE5_HANDLER_FLOW.md
**Created:** 2026-01-21
**Auditor:** Claude B
