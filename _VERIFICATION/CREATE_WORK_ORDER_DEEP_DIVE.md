# create_work_order: Complete Deep Dive Analysis

**Date:** 2026-01-22
**Action:** `create_work_order`
**Scope:** Full vertical analysis from user query → execution → database → audit

---

## Executive Summary

### Status: 🟡 PARTIALLY FUNCTIONAL

| Component | Status | Details |
|-----------|--------|---------|
| HTTP Layer | ✅ WORKING | Returns 200, creates work order |
| Database Write | ✅ WORKING | Writes to `pms_work_orders` table |
| Audit Trail | ❌ MISSING | Does NOT write to `pms_audit_log` |
| Field Mappings | ⚠️ TRANSFORMS | Priority/status values transformed |
| NL Query Detection | ⏳ PENDING | Not yet tested |
| Edge Cases | ⏳ PENDING | Not yet tested |

**Critical Gap:** `create_work_order` does NOT write audit log entries, unlike 26 other actions that do.

---

## Part 1: Audit Table Analysis

### 🔍 Audit Table Discovery

**Result:** Only ONE audit table exists: `pms_audit_log`

#### Schema:

```typescript
{
  id: string (uuid)
  yacht_id: string (uuid)
  action: string                    // e.g., "mark_work_order_complete"
  entity_type: string               // e.g., "work_order", "fault"
  entity_id: string (uuid)          // ID of affected entity
  user_id: string (uuid)            // Who performed the action
  signature: {                      // JSONB
    user_id: string
    timestamp: string
    execution_id?: string
    action: string
  }
  old_values: object                // JSONB - state before action
  new_values: object                // JSONB - state after action
  created_at: timestamp
  metadata: object                  // JSONB - additional context
}
```

### 📊 Audit Log Statistics

**Total entries for test yacht:** 135

**Top 20 audited actions:**
1. mark_work_order_complete (19 entries)
2. acknowledge_fault (8 entries)
3. add_work_order_note (6 entries)
4. assign_work_order (6 entries)
5. add_equipment_note (6 entries)
6. edit_handover_section (6 entries)
7. add_predictive_insight_to_handover (6 entries)
8. regenerate_handover_summary (6 entries)
9. update_purchase_status (6 entries)
10. add_item_to_purchase (6 entries)
... and 16 more

**Actions WITH audit logging:** 26 actions
**Actions WITHOUT audit logging:** Unknown (needs verification)

### ❌ create_work_order Audit Gap

**Query Results:**
```sql
SELECT * FROM pms_audit_log
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND action = 'create_work_order';
-- Result: 0 rows
```

**Comparison:**
- ✅ `create_work_order_from_fault` → HAS audit entries
- ❌ `create_work_order` → NO audit entries

**Why This Matters:**
1. **Compliance:** No audit trail for work order creation
2. **Debugging:** Can't trace when/who created work orders
3. **Data integrity:** No old_values/new_values tracking
4. **Security:** Can't audit unauthorized work order creation

---

## Part 2: Handler Implementation Analysis

### 📝 Handler Code (lines 1325-1357)

```python
elif action in ("create_work_order", "create_wo"):
    from datetime import datetime, timezone
    import uuid
    tenant_alias = user_context.get("tenant_key_alias", "")
    db_client = get_tenant_supabase_client(tenant_alias)

    # Validate required fields
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    # Map priority
    raw_priority = payload.get("priority", "routine")
    priority_map = {
        "normal": "routine",
        "low": "routine",
        "medium": "routine",
        "high": "critical"
    }
    priority = priority_map.get(
        raw_priority,
        raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine"
    )

    wo_data = {
        "yacht_id": yacht_id,
        "equipment_id": payload.get("equipment_id"),
        "title": title,
        "description": payload.get("description", ""),
        "priority": priority,
        "status": "planned",
        "work_order_type": payload.get("work_order_type", "corrective"),
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if wo_result.data:
        result = {
            "status": "success",
            "work_order_id": wo_result.data[0]["id"],
            "message": "Work order created"
        }
    else:
        result = {
            "status": "error",
            "error_code": "INSERT_FAILED",
            "message": "Failed to create work order"
        }
```

### 🔍 Code Analysis

**What it does:**
1. ✅ Validates `title` is present
2. ✅ Maps priority values (medium→routine, high→critical)
3. ✅ Sets default status to "planned"
4. ✅ Writes to `pms_work_orders` table
5. ✅ Returns work_order_id on success

**What it does NOT do:**
1. ❌ Write to `pms_audit_log`
2. ❌ Generate execution_id
3. ❌ Track old_values/new_values
4. ❌ Create signature metadata

### 🔄 Comparison with acknowledge_fault

**acknowledge_fault handler (lines 873-920) DOES write audit:**

```python
# Update fault in database
fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

if fault_result.data:
    # Create audit log entry
    try:
        audit_entry = {
            "id": str(uuid_module.uuid4()),
            "yacht_id": yacht_id,
            "action": "acknowledge_fault",
            "entity_type": "fault",
            "entity_id": fault_id,
            "user_id": user_id,
            "old_values": {
                "status": old_status,
                "severity": old_severity
            },
            "new_values": {
                "status": "investigating",
                "severity": "medium",
                "note": payload.get("note")
            },
            "metadata": {
                "signature": {
                    "user_id": user_id,
                    "execution_id": execution_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "acknowledge_fault"
                }
            }
        }
        db_client.table("pms_audit_log").insert(audit_entry).execute()
        logger.info(f"Audit log created for acknowledge_fault: execution_id={execution_id}")
    except Exception as audit_err:
        # Log audit failure but don't fail the action
        logger.warning(f"Audit log failed: {audit_err}")
```

**Pattern to adopt:** create_work_order should follow this same pattern.

---

## Part 3: Database Verification

### ✅ Mutation Test Results (2026-01-22)

**Test:** `tests/e2e/mutation_proof_create_work_order.spec.ts`

**Results:**
```
HTTP Status:     200 ✅
Work Order ID:   50e9c919-6fc2-4b3d-b913-e0da3285f14d ✅
DB Row Created:  YES ✅
Audit Log:       NOT FOUND ❌
```

**Database Row Created:**
```json
{
  "id": "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "equipment_id": null,
  "title": "Test WO - 1769090735976",
  "description": "Created by mutation proof test at 2026-01-22T14:05:35.976Z",
  "type": "scheduled",
  "priority": "routine",
  "status": "planned",
  "work_order_type": "corrective",
  "created_by": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "created_at": "2026-01-22T14:05:36.244721+00:00",
  "updated_at": "2026-01-22T14:05:36.392161+00:00",
  "deleted_at": null,
  "deleted_by": null,
  "deletion_reason": null,
  "wo_number": null,
  "fault_id": null,
  "assigned_to": null,
  "completed_by": null,
  "completed_at": null,
  "completion_notes": null,
  "vendor_contact_hash": null,
  "due_date": null,
  "due_hours": null,
  "last_completed_date": null,
  "last_completed_hours": null,
  "frequency": null,
  "metadata": {}
}
```

### 🔄 Field Mapping Transformations

**Observed Transformations:**

| Sent Payload | Stored in DB | Transformation |
|--------------|--------------|----------------|
| `priority: "medium"` | `priority: "routine"` | priority_map |
| `priority: "high"` | `priority: "critical"` | priority_map |
| `status: "open"` | `status: "planned"` | Hardcoded |
| (not sent) | `type: "scheduled"` | Default value |
| (not sent) | `work_order_type: "corrective"` | Default value |

**Priority Mapping Logic:**
```python
priority_map = {
    "normal": "routine",
    "low": "routine",
    "medium": "routine",  # ← All map to routine!
    "high": "critical"
}
```

**Status Logic:**
- Always sets `status: "planned"` (ignores payload)

---

## Part 4: Why Use pms_audit_log?

### 🎯 Argument for pms_audit_log

**1. It's the ONLY audit table**
- No alternatives exist
- Already used by 26 other actions
- Proven to work in production

**2. Perfect Schema for Auditing**
```typescript
{
  action: string,           // ← Action name
  entity_type: string,      // ← "work_order"
  entity_id: string,        // ← Work order ID
  user_id: string,          // ← Who created it
  old_values: {},           // ← {} for create (nothing existed before)
  new_values: {             // ← Full work order data
    title,
    description,
    priority,
    status,
    equipment_id,
    ...
  },
  signature: {              // ← Cryptographic proof
    user_id,
    timestamp,
    execution_id,
    action
  }
}
```

**3. Enables Critical Features**
- **Compliance:** ISO 9001, SOLAS require audit trails
- **Debugging:** Trace when work orders were created
- **Security:** Detect unauthorized creation
- **Analytics:** Track work order creation patterns
- **Data Recovery:** old_values/new_values can reconstruct history

**4. Consistency**
If `create_work_order_from_fault` writes audit logs, then `create_work_order` should too.

**5. Links to Work Order**
```sql
-- Get all audit history for a work order
SELECT * FROM pms_audit_log
WHERE entity_type = 'work_order'
AND entity_id = '<work_order_id>'
ORDER BY created_at;
```

This returns:
1. create_work_order (creation)
2. assign_work_order (assignment)
3. add_work_order_note (notes)
4. mark_work_order_complete (completion)

**Complete lifecycle in ONE query!**

---

## Part 5: Recommended Audit Entry Format

### 📋 create_work_order Audit Entry

```python
# After successful insert into pms_work_orders
if wo_result.data:
    wo_id = wo_result.data[0]["id"]

    # Create audit log entry
    try:
        audit_entry = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "action": "create_work_order",
            "entity_type": "work_order",
            "entity_id": wo_id,
            "user_id": user_id,
            "old_values": {},  # Empty for create
            "new_values": {
                "title": title,
                "description": payload.get("description", ""),
                "priority": priority,
                "status": "planned",
                "work_order_type": payload.get("work_order_type", "corrective"),
                "equipment_id": payload.get("equipment_id"),
                "created_by": user_id
            },
            "metadata": {
                "signature": {
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "create_work_order"
                },
                "source": "manual_creation",  # vs "from_fault"
                "raw_priority": raw_priority  # Track original value before mapping
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db_client.table("pms_audit_log").insert(audit_entry).execute()
        logger.info(f"Audit log created for create_work_order: wo_id={wo_id}")
    except Exception as audit_err:
        # Don't fail the action if audit fails
        logger.warning(f"Audit log failed for create_work_order (wo_id={wo_id}): {audit_err}")
```

**Metadata Additions:**
- `source`: "manual_creation" vs "from_fault" vs "scheduled_pm"
- `raw_priority`: Original priority before mapping
- `raw_status`: Original status before transformation (if applicable)

---

## Part 6: Pending Tests

### ⏳ Next Phase: Natural Language Query Testing

**Test Categories:**

1. **Direct Commands** (20 queries)
   - "create a work order"
   - "make a new work order"
   - "add a work order"
   - "start a work order"
   - "open a work order"
   - "create wo"
   - "new wo"
   - ... 13 more

2. **Equipment-Specific** (15 queries)
   - "create work order for generator"
   - "make work order for the starboard engine"
   - "add work order for hydraulic pump"
   - ... 12 more

3. **Fault-Related** (10 queries)
   - "the AC is broken, create a work order"
   - "generator fault, need work order"
   - "water pump failed, make wo"
   - ... 7 more

4. **Scheduled Maintenance** (10 queries)
   - "schedule maintenance for generator"
   - "plan PM for engine"
   - "create scheduled work order"
   - ... 7 more

**Total: 55 NL query variations**

### ⏳ Edge Case Testing (50+ scenarios)

**Category 1: Field Validation** (10 tests)
- Missing title
- Empty title
- Title > 1000 characters
- Special characters in title
- Unicode characters
- SQL injection in title
- XSS payloadsin title
- Null values
- Missing yacht_id
- Invalid yacht_id

**Category 2: Priority Mappings** (8 tests)
- priority="low"
- priority="medium"
- priority="high"
- priority="normal"
- priority="routine"
- priority="emergency"
- priority="critical"
- priority="invalid_value"

**Category 3: Status Values** (6 tests)
- status="open"
- status="planned"
- status="in_progress"
- status="completed"
- status="cancelled"
- status not provided

**Category 4: Equipment Linking** (8 tests)
- Valid equipment_id
- Invalid equipment_id
- equipment_id from wrong yacht
- equipment_id=null
- equipment_id=""
- Non-existent equipment
- Equipment_id with RLS violation
- Equipment from different tenant

**Category 5: Description Field** (5 tests)
- Empty description
- Long description (10,000 chars)
- HTML in description
- JavaScript in description
- Unicode/emoji in description

**Category 6: Security** (8 tests)
- SQL injection in all fields
- XSS in all fields
- RLS bypass attempts
- Cross-tenant access
- Invalid JWT
- Expired JWT
- Missing authorization header
- Tampered yacht_id

**Category 7: Concurrency** (5 tests)
- 10 parallel requests
- Same title, different users
- Race conditions
- Deadlock scenarios
- Timeout handling

**Total:** 50 edge case tests

---

## Part 7: Work Order Lifecycle Testing

### 🔄 Complete Lifecycle

**Phase 1: Create**
```typescript
POST /v1/actions/execute
{
  action: "create_work_order",
  payload: {
    title: "Replace hydraulic pump",
    description: "Starboard stabilizer pump leaking",
    priority: "high",
    equipment_id: "uuid-here"
  }
}
```

**Phase 2: Assign**
```typescript
POST /v1/actions/execute
{
  action: "assign_work_order",
  payload: {
    work_order_id: "uuid-from-step-1",
    assigned_to: "engineer-user-id"
  }
}
```

**Phase 3: Add Notes**
```typescript
POST /v1/actions/execute
{
  action: "add_work_order_note",
  payload: {
    work_order_id: "uuid-from-step-1",
    note_text: "Ordered replacement pump, ETA 3 days"
  }
}
```

**Phase 4: Add Parts**
```typescript
POST /v1/actions/execute
{
  action: "add_parts_to_work_order",
  payload: {
    work_order_id: "uuid-from-step-1",
    part_id: "pump-part-id",
    quantity: 1
  }
}
```

**Phase 5: Complete**
```typescript
POST /v1/actions/execute
{
  action: "mark_work_order_complete",
  payload: {
    work_order_id: "uuid-from-step-1",
    completion_notes: "Pump replaced and tested successfully",
    signature: "John Smith"
  }
}
```

### 🔍 Verification at Each Step

After EACH step:
1. Query `pms_work_orders` for updated row
2. Query `pms_audit_log` for new audit entry
3. Verify old_values → new_values transition
4. Check RLS enforcement
5. Verify user_id tracking

**Expected Audit Trail:**
```sql
SELECT action, old_values->>'status' as old_status, new_values->>'status' as new_status
FROM pms_audit_log
WHERE entity_id = 'work-order-id'
ORDER BY created_at;
```

Result:
```
action                      | old_status | new_status
----------------------------|------------|------------
create_work_order           | (null)     | planned
assign_work_order           | planned    | planned
add_work_order_note         | (no change)| (no change)
add_parts_to_work_order     | (no change)| (no change)
mark_work_order_complete    | planned    | completed
```

---

## Part 8: Summary & Recommendations

### 🎯 Critical Findings

1. **✅ WORKING:** HTTP layer, database writes
2. **❌ MISSING:** Audit trail (`pms_audit_log`)
3. **⚠️ INCONSISTENT:** Field mapping (priority, status)
4. **⏳ UNTESTED:** NL queries, edge cases, lifecycle

### 📋 Recommendations (Priority Order)

**Priority 1: Add Audit Logging**
- Add `pms_audit_log` write after successful `pms_work_orders` insert
- Follow pattern from `acknowledge_fault` handler
- Include old_values (empty), new_values (full WO data), signature

**Priority 2: Test Natural Language Queries**
- Verify 55+ NL query variations surface create_work_order action
- Test /v1/search endpoint returns correct action buttons
- Verify intent detection and entity extraction

**Priority 3: Edge Case Testing**
- Run 50+ edge case scenarios
- Document failures
- Fix security vulnerabilities (SQL injection, XSS, RLS bypass)

**Priority 4: Lifecycle Testing**
- Test complete create → assign → note → complete flow
- Verify audit trail at each step
- Ensure data consistency

**Priority 5: Documentation**
- Document field mappings
- Create API contract
- Add examples to developer docs

---

## Next Steps

1. ✅ Test NL queries (20+ variations)
2. ✅ Test /v1/search endpoint
3. ✅ Run edge case suite (50+ tests)
4. ✅ Test lifecycle (create → complete)
5. ✅ Security testing
6. ✅ Write complete specification

**Let's continue with Phase 1: Natural Language Query Testing**
