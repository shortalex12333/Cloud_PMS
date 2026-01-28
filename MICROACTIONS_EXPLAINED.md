# Microactions Explained

**Deep dive into the microaction concept**

**Purpose:** Understand what microactions are and why we use them
**Audience:** Engineers new to the system
**Reading time:** 20 minutes

---

## 🎯 What Is a Microaction?

**Simple definition:**
A microaction is a user-triggered mutation with:
1. **Natural language detection** ("create a work order" → `create_work_order`)
2. **Contextual awareness** (knows yacht_id, user_id, equipment_id automatically)
3. **Guard rails at all layers** (frontend, backend, database validation)
4. **Audit trail required** (every mutation logged to pms_audit_log)

**Example:**
```typescript
// User types: "create a work order for the generator"
// ↓ GPT-4o-mini detects action
// ↓ Button appears: "Create Work Order"
// ↓ User clicks, fills form, submits
// ↓ Backend calls:

executeAction(
  'create_work_order',  // ← Microaction ID
  {
    yacht_id: '...',    // ← Automatic from JWT
    user_id: '...'      // ← Automatic from JWT
  },
  {
    title: 'Replace generator oil filter',  // ← User input
    equipment_id: '...'                      // ← From context
  }
)

// ↓ Handler validates, writes to DB, creates audit log
// ↓ Returns: {"status": "success", "work_order_id": "..."}
```

---

## ❓ Why Not Just REST APIs?

### Traditional REST Approach

**REST API:**
```javascript
// POST /api/work-orders
fetch('https://api.example.com/api/work-orders', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer token',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    yacht_id: '...',      // ← User must provide
    title: 'Oil change',
    equipment_id: '...',
    created_by: '...'     // ← User must provide
  })
})
```

**Problems:**
1. ❌ User must manually provide yacht_id (error-prone)
2. ❌ No natural language connection
3. ❌ Audit logging is optional (often forgotten)
4. ❌ Resource-based (`/work-orders`) not intent-based
5. ❌ No context flow from previous interaction

### Microaction Approach

**Microaction:**
```javascript
// POST /v1/actions/execute
executeAction(
  'create_work_order',  // ← Intent clear
  {
    yacht_id: '...',    // ← Automatic (from JWT)
    user_id: '...'      // ← Automatic (from JWT)
  },
  {
    title: 'Oil change',
    equipment_id: '...'  // ← Pre-filled from "generator" mention
  }
)
```

**Benefits:**
1. ✅ yacht_id automatic (from JWT, can't forget)
2. ✅ Natural language aligned ("create a work order" → create_work_order)
3. ✅ Audit logging enforced (compliance requirement)
4. ✅ Intent-based (what user wants to do)
5. ✅ Context flows from conversation

---

## 📊 The 64 Microactions

### Why 64?

**Each microaction represents ONE distinct user intent:**
- `create_work_order` - New WO from scratch
- `create_work_order_from_fault` - WO linked to existing fault
- `mark_work_order_complete` - State transition (planned → completed)
- `update_work_order` - Edit existing WO

**These are different intents!** Not "CRUD on work_orders resource"

### Action Clusters

**Actions are organized into 12 clusters:**

1. **FIX_SOMETHING** (9 actions)
   - report_fault, acknowledge_fault, diagnose_fault
   - create_work_order_from_fault, assign_fault_to_equipment
   - add_fault_note, update_fault, resolve_fault, close_fault

2. **DO_MAINTENANCE** (12 actions)
   - create_work_order, update_work_order, assign_work_order
   - start_work_order, mark_work_order_complete, cancel_work_order
   - add_work_order_note, link_part_to_work_order, attach_document_to_work_order
   - create_pm_schedule, update_pm_schedule, generate_work_orders_from_schedule

3. **MANAGE_EQUIPMENT** (8 actions)
   - add_equipment, update_equipment, decommission_equipment
   - add_equipment_note, flag_equipment_attention, unflag_equipment_attention
   - view_equipment_history, bulk_import_equipment

4. **INVENTORY_PARTS** (10 actions)
   - add_part, update_part, adjust_part_quantity
   - order_part, receive_part_order, transfer_part
   - add_part_note, search_parts, view_parts_low_stock
   - create_parts_order

5. **HANDOVER** (4 actions)
   - create_handover_item, mark_handover_complete
   - view_handover_list, export_handover_report

6. **COMPLIANCE** (5 actions)
   - create_inspection, complete_inspection
   - create_certificate, renew_certificate, view_compliance_status

7. **DOCUMENTS** (6 actions)
   - upload_document, update_document_metadata
   - search_documents, download_document, delete_document
   - link_document_to_entity

8. **PURCHASING** (4 actions)
   - create_purchase_order, approve_purchase_order
   - receive_purchase_order, cancel_purchase_order

9. **CHECKLISTS** (3 actions)
   - create_checklist, complete_checklist_item, view_checklist

10. **SHIPYARD** (2 actions)
    - create_shipyard_project, update_shipyard_project

11. **FLEET** (2 actions)
    - view_fleet_overview, export_fleet_report

12. **SYSTEM_UTILITY** (3 actions)
    - export_data, import_data, generate_report

**Total: 64 microactions** (some clusters have more than listed above)

### Full Registry

**See:** `tests/fixtures/microaction_registry.ts` for complete list

---

## 🏗️ Microaction Anatomy

### Components of a Microaction

**Every microaction has:**

1. **Action ID** (string)
   ```typescript
   "create_work_order"
   ```

2. **Label** (human-readable)
   ```typescript
   "Create Work Order"
   ```

3. **Cluster** (categorization)
   ```typescript
   "DO_MAINTENANCE"
   ```

4. **Mutation Type** (impact level)
   ```typescript
   "MUTATE_MEDIUM"  // READ | MUTATE_LOW | MUTATE_MEDIUM | MUTATE_HIGH
   ```

5. **Aliases** (alternative names)
   ```typescript
   ["create_wo", "new_work_order", "add_work_order"]
   ```

6. **Required Context** (from JWT or situation)
   ```typescript
   {
     yacht_id: "uuid",  // From JWT
     user_id: "uuid"    // From JWT
   }
   ```

7. **Required Payload** (user must provide)
   ```typescript
   {
     title: "string"  // Required
   }
   ```

8. **Optional Payload** (user can provide)
   ```typescript
   {
     description: "string",
     priority: "routine" | "critical" | "emergency",
     equipment_id: "uuid"
   }
   ```

9. **Handler Function** (Python code)
   ```python
   # In p0_actions_routes.py
   elif action in ("create_work_order", "create_wo"):
       # Validation
       # Transformation
       # Database write
       # Audit log
       # Return response
   ```

10. **Form Fields** (UI definition)
    ```typescript
    [
      {name: "title", type: "text", required: true},
      {name: "description", type: "textarea", required: false},
      {name: "priority", type: "select", options: [...]}
    ]
    ```

---

## 🔄 Microaction Lifecycle

### Phase 1: Detection

**User types natural language query:**
```
"create a work order for the generator"
```

**GPT-4o-mini analyzes:**
```json
{
  "detected_action": "create_work_order",
  "confidence": 0.95,
  "extracted_entities": {
    "equipment_mention": "generator"
  }
}
```

**Frontend shows button:**
```
[✓ Create Work Order]
```

### Phase 2: Context Gathering

**When user clicks button:**

1. **From JWT:**
   - yacht_id (which yacht)
   - user_id (who is doing this)
   - role (permissions)

2. **From Situation:**
   - equipment_id (if viewing equipment)
   - fault_id (if viewing fault)
   - work_order_id (if editing WO)

3. **From Query:**
   - "generator" mention → search equipment for generator → pre-fill equipment_id

**Result: Pre-filled form**
```
Title: [_________________]
Description: [_________________]
Priority: [Routine ▼]
Equipment: [Main Generator ▼]  ← Pre-filled!
```

### Phase 3: Validation (Frontend)

**User fills form, clicks submit:**

```typescript
// Frontend validates
if (!formData.title || formData.title.trim() === '') {
  setError('title', 'Title is required');
  return;  // Don't submit
}

if (formData.title.length > 200) {
  setError('title', 'Title too long (max 200 chars)');
  return;
}

// If valid, proceed to execute
```

### Phase 4: Execution (Backend)

**API call:**
```javascript
POST /v1/actions/execute
{
  "action": "create_work_order",
  "context": {
    "yacht_id": "...",
    "user_id": "..."
  },
  "payload": {
    "title": "Replace generator oil filter",
    "priority": "routine",
    "equipment_id": "..."
  }
}
```

**Handler validates:**
```python
# 1. Auth check
if not user_id:
    raise HTTPException(401, "Unauthorized")

# 2. Yacht access check
if yacht_id not in user_allowed_yachts:
    raise HTTPException(403, "Access denied")

# 3. Required fields
if not payload.get("title"):
    raise HTTPException(400, "title is required")

# 4. Entity existence
if payload.get("equipment_id"):
    equipment = db.table("pms_equipment").select("id").eq("id", equipment_id).execute()
    if not equipment.data:
        raise HTTPException(404, "Equipment not found")
```

**Handler transforms:**
```python
# Map priority
priority_map = {"normal": "routine", "low": "routine", "high": "critical"}
priority = priority_map.get(payload.get("priority"), "routine")

# Build data
wo_data = {
    "yacht_id": yacht_id,
    "title": payload["title"],
    "status": "planned",  # Hardcoded
    "priority": priority,
    "created_by": user_id,
    "created_at": datetime.now(timezone.utc).isoformat()
}
```

**Handler writes:**
```python
# Write to database
result = db_client.table("pms_work_orders").insert(wo_data).execute()
wo_id = result.data[0]["id"]

# Write to audit log (if implemented)
audit_entry = {
    "action": "create_work_order",
    "entity_type": "work_order",
    "entity_id": wo_id,
    "user_id": user_id,
    "new_values": wo_data,
    ...
}
db_client.table("pms_audit_log").insert(audit_entry).execute()
```

**Handler returns:**
```python
return {
    "status": "success",
    "work_order_id": wo_id,
    "message": "Work order created"
}
```

### Phase 5: Confirmation (Frontend)

**Frontend receives response:**
```typescript
if (response.status === 'success') {
  toast.success('Work order created');
  closeModal();
  refreshData();
} else {
  toast.error(response.message);
}
```

---

## 🎨 Microaction Design Patterns

### Pattern 1: Create Entity

**Examples:** create_work_order, create_equipment, create_part

**Flow:**
1. User types query → Action detected
2. User clicks button → Empty form opens
3. User fills ALL fields → Submits
4. Backend validates → Creates entity
5. Audit log created → Success returned

**Database:**
- INSERT into main table
- INSERT into audit log
- Return new entity ID

### Pattern 2: Create Linked Entity

**Examples:** create_work_order_from_fault, add_equipment_note

**Flow:**
1. User viewing entity A (e.g., Fault F-123)
2. User clicks "Create Work Order" → Form opens with pre-filled context
3. fault_id = F-123 (hidden, immutable)
4. equipment_id pre-filled from fault
5. User fills remaining fields → Submits
6. Backend validates → Creates WO linked to fault
7. Updates fault.work_order_id → Success

**Database:**
- INSERT into main table (with foreign key)
- UPDATE parent table (if needed)
- INSERT into audit log

### Pattern 3: Update Entity

**Examples:** update_work_order, update_equipment, update_fault

**Flow:**
1. User viewing entity → Clicks "Edit"
2. Form opens with CURRENT values pre-filled
3. User edits fields → Submits
4. Backend validates → Updates entity
5. Audit log created (old_values + new_values) → Success

**Database:**
- UPDATE main table
- INSERT into audit log (with old_values, new_values)

### Pattern 4: State Transition

**Examples:** mark_work_order_complete, acknowledge_fault, start_work_order

**Flow:**
1. User viewing entity → Clicks "Mark Complete"
2. Confirmation modal (minimal form, optional notes)
3. User confirms → Submits
4. Backend validates → Updates status + metadata
5. Audit log created → Success

**Database:**
- UPDATE status field
- UPDATE related fields (completed_at, completed_by)
- INSERT into audit log

### Pattern 5: Add Child Entity

**Examples:** add_work_order_note, add_fault_note, add_equipment_note

**Flow:**
1. User viewing parent entity
2. User types in inline note input
3. User presses Enter → Submits
4. Backend validates → Inserts note
5. Note appears in thread immediately

**Database:**
- INSERT into notes table (with parent_id foreign key)
- INSERT into audit log (optional for notes)

### Pattern 6: Delete Entity (Soft)

**Examples:** delete_work_order, delete_equipment, delete_fault

**Flow:**
1. User viewing entity → Clicks "⋮" menu → Delete
2. Confirmation modal with deletion reason
3. User confirms → Submits
4. Backend validates → Soft deletes entity
5. Audit log created → Success

**Database:**
- UPDATE deleted_at, deleted_by, deletion_reason
- INSERT into audit log

---

## 🔍 Microaction vs REST Comparison

| Aspect | REST API | Microaction |
|--------|----------|-------------|
| **Endpoint** | `/api/work-orders` | `/v1/actions/execute` |
| **Method** | POST/PUT/DELETE per resource | Always POST |
| **Intent** | Resource-based (CRUD) | Intent-based (action) |
| **Context** | User provides yacht_id | Automatic from JWT |
| **Validation** | Per endpoint | Per action handler |
| **Audit** | Optional | Required (compliance) |
| **NL Mapping** | None | Direct ("create WO" → create_work_order) |
| **Discoverability** | OpenAPI/Swagger | Registry + NL detection |
| **Versioning** | /v1/api/work-orders | Action version in handler |

**Example comparison:**

**REST:**
```javascript
// Create
POST /api/work-orders
{yacht_id, title, ...}

// Update
PUT /api/work-orders/123
{title, ...}

// Delete
DELETE /api/work-orders/123

// Complete
PUT /api/work-orders/123/complete
{notes}
```

**Microactions:**
```javascript
// Create
POST /v1/actions/execute
{action: "create_work_order", context: {yacht_id}, payload: {title}}

// Update
POST /v1/actions/execute
{action: "update_work_order", context: {yacht_id}, payload: {work_order_id, title}}

// Delete
POST /v1/actions/execute
{action: "delete_work_order", context: {yacht_id}, payload: {work_order_id, reason}}

// Complete
POST /v1/actions/execute
{action: "mark_work_order_complete", context: {yacht_id}, payload: {work_order_id, notes}}
```

**Why microactions win for this use case:**
- Natural language: "mark work order complete" → `mark_work_order_complete`
- Context flows: yacht_id automatic, equipment_id from situation
- Audit enforced: Can't forget to log
- Intent clear: Action name = user intent

---

## 🧪 Testing Microactions

### What to Test

**For each microaction, test:**

1. **Success path**
   - Valid input → 200 response
   - Database row created/updated
   - Audit log entry created
   - Response contains entity ID

2. **Validation errors**
   - Missing required field → 400
   - Invalid enum value → 400
   - Field too long → 400

3. **Entity not found**
   - Invalid entity reference → 404

4. **Authorization**
   - No JWT → 401
   - Wrong yacht_id → 403

5. **Database constraints**
   - RLS prevents cross-yacht access
   - Soft delete prevents hard deletes

**See:** TESTING_STANDARDS.md for complete criteria

---

## 📊 Microaction Statistics

**Current state:**
- Total microactions: 64
- Verified: 1/64 (create_work_order)
- Handlers implemented: 81 (includes aliases)
- Average handler length: ~50 lines
- Total handler code: ~4,160 lines

**Clusters:**
- Largest cluster: DO_MAINTENANCE (12 actions)
- Smallest cluster: SHIPYARD (2 actions)

**Types:**
- READ actions: ~20 (view_*, export_*, search_*)
- MUTATE_LOW: ~15 (add_note, flag_attention, etc.)
- MUTATE_MEDIUM: ~25 (create, update, assign, etc.)
- MUTATE_HIGH: ~4 (delete, decommission, bulk operations)

---

## 🎯 Design Principles

**Every microaction must:**

1. ✅ Have a clear single intent
   - Good: `mark_work_order_complete`
   - Bad: `update_work_order_status` (vague)

2. ✅ Map to natural language
   - Good: "mark work order complete" → `mark_work_order_complete`
   - Bad: `wo_status_updater_v2` (not natural)

3. ✅ Use automatic context
   - yacht_id from JWT
   - user_id from JWT
   - entity_id from situation (when viewing entity)

4. ✅ Validate at all layers
   - Frontend: UX feedback
   - Backend: Guard rails
   - Database: RLS + constraints

5. ✅ Create audit trail
   - All mutations logged
   - old_values + new_values captured
   - WHO + WHEN + WHAT recorded

6. ✅ Return consistent response
   ```json
   {
     "status": "success" | "error",
     "entity_id": "uuid",  // If created/updated
     "message": "Human readable message",
     "error_code": "ERROR_CODE"  // If error
   }
   ```

---

## 🚀 Adding a New Microaction

**Checklist:**

1. **Define action**
   ```typescript
   // In tests/fixtures/microaction_registry.ts
   {
     action: "new_action_name",
     label: "New Action Name",
     cluster: "CLUSTER_NAME",
     mutationType: "MUTATE_MEDIUM"
   }
   ```

2. **Add handler**
   ```python
   # In apps/api/routes/p0_actions_routes.py
   elif action == "new_action_name":
       # Validation
       # Transformation
       # Database write
       # Audit log
       # Return response
   ```

3. **Document in frameworks**
   - DATABASE_RELATIONSHIPS.md (if new table)
   - CUSTOMER_JOURNEY_FRAMEWORK.md (UI journey)

4. **Create verification file**
   ```bash
   cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_new_action_name.md
   ```

5. **Write tests**
   - Mutation proof test
   - NL query tests
   - E2E journey test

6. **Verify**
   - All 215 checkpoints
   - Update MUTATION_PROOFS.md

---

## 📚 Related Documentation

- **ARCHITECTURE.md** - Overall system architecture
- **SITUATIONS_EXPLAINED.md** - How context flows from situations
- **DATABASE_RELATIONSHIPS.md** - What tables microactions write to
- **CUSTOMER_JOURNEY_FRAMEWORK.md** - How users trigger microactions

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team
**Microaction Count:** 64 (and growing)
