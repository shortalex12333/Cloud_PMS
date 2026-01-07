# Phase 5: Backend Implementation Blueprint

**Version:** 1.0
**Date:** 2025-11-21
**Branch:** `claude/read-repo-files-01TwqiaKXUk14frUXUPkVKTj`
**Purpose:** Definitive backend specification for n8n workflow and SQL implementation

---

## Overview

This document defines the global rules, standards, and responsibilities for implementing backend logic for all 67 CelesteOS micro-actions.

**Separation of Concerns:**
- **Frontend:** Already built (15/67 modals complete, 52 pending)
- **Backend Engineer:** Implements n8n workflows + SQL based on THIS specification
- **This Document:** The contract between frontend and backend

---

## Global Backend Responsibilities

### 1. Request Processing
All actions arrive via unified payload:
```json
{
  "action_name": "edit_work_order_details",
  "context": {
    "work_order_id": "uuid-123",
    "yacht_id": "uuid-456"
  },
  "parameters": {
    "title": "New title",
    "priority": "high"
  },
  "session": {
    "user_id": "uuid-789",
    "yacht_id": "uuid-456",
    "role": "CHIEF_ENGINEER"
  }
}
```

### 2. Response Format
All actions return unified response:
```json
{
  "success": true,
  "card_type": "work_order",
  "card": {
    "id": "uuid-123",
    "title": "New title",
    "status": "in_progress",
    "micro_actions": [...]
  },
  "metadata": {
    "action_executed": "edit_work_order_details",
    "timestamp": "2025-11-21T12:00:00Z"
  }
}
```

Or error:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Work order not found",
    "field": "work_order_id"
  }
}
```

---

## Global Rules

### Transaction Management

**Rule:** All mutation actions (CREATE, UPDATE, LINK) MUST use transactions.

**Pattern:**
1. BEGIN TRANSACTION
2. Validate inputs
3. Execute main operation (INSERT/UPDATE)
4. Write audit log (if required)
5. Send notifications (if required)
6. COMMIT TRANSACTION
7. On error: ROLLBACK, return error response

**Example (pseudo-SQL):**
```sql
BEGIN;
  -- Step 1: Validate
  SELECT id FROM work_orders WHERE id = $1 AND yacht_id = $2;
  IF NOT FOUND THEN ROLLBACK; RETURN error;

  -- Step 2: Update
  UPDATE work_orders SET title = $3 WHERE id = $1;

  -- Step 3: Audit
  INSERT INTO audit_logs (...) VALUES (...);
COMMIT;
```

---

### Row Level Security (RLS)

**Rule:** ALL queries MUST filter by `yacht_id` from session.

**Why:** Multi-tenancy - prevent yacht A from seeing yacht B's data.

**Pattern:**
```sql
-- ✅ GOOD
SELECT * FROM work_orders
WHERE id = $1 AND yacht_id = $session_yacht_id;

-- ❌ BAD
SELECT * FROM work_orders WHERE id = $1;
```

**Enforcement:** Every table has `yacht_id` column. Every query filters on it.

---

### Soft Delete vs Hard Delete

**Rule:** Use soft delete for user-generated content. Use hard delete for system data only.

| Entity Type | Delete Strategy | Table Column |
|-------------|----------------|--------------|
| Notes | Soft delete | `deleted = true, deleted_at, deleted_by` |
| Photos/Attachments | Soft delete | `deleted = true` |
| Work Orders (draft) | Soft delete | `deleted = true` |
| Work Orders (completed) | No delete (archive only) | - |
| Faults | No delete (archive only) | - |
| Equipment | No delete (archive only) | - |
| Parts | No delete | - |
| Session tokens | Hard delete | - |
| Temporary data | Hard delete | - |

**Pattern for soft delete:**
```sql
UPDATE notes
SET deleted = true,
    deleted_at = NOW(),
    deleted_by = $session_user_id
WHERE id = $1 AND yacht_id = $session_yacht_id;
```

**Undo window:** 5 minutes - keep deleted items queryable with `deleted = true AND deleted_at > NOW() - INTERVAL '5 minutes'`

---

### Audit Logging

**Rule:** All mutation_heavy and audit-sensitive actions MUST log to `audit_logs` table.

#### Severity Levels

| Severity | When to Use | Examples |
|----------|-------------|----------|
| **LOW** | Read-only actions with context | View sensitive data, export reports |
| **MEDIUM** | Standard mutations | Edit work order, log part usage, complete task |
| **HIGH** | Critical changes, financial data | Edit invoice amount, delete records, change serial numbers |

#### Audit Log Schema
```sql
TABLE audit_logs (
  id UUID PRIMARY KEY,
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  action_name TEXT NOT NULL,
  severity TEXT NOT NULL, -- 'LOW' | 'MEDIUM' | 'HIGH'
  entity_type TEXT NOT NULL, -- 'work_order' | 'part' | 'fault' | etc.
  entity_id UUID,
  before_state JSONB, -- Old values
  after_state JSONB,  -- New values
  reason TEXT, -- Required for HIGH severity
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

#### When to Audit

| Action Side Effect | Audit Required? | Severity |
|-------------------|-----------------|----------|
| read_only | Optional (only if sensitive) | LOW |
| mutation_light | Required | MEDIUM |
| mutation_heavy | Required | MEDIUM or HIGH |

#### Required Fields by Severity

**MEDIUM Severity:**
- user_id, yacht_id, action_name, entity_type, entity_id, timestamp
- before_state, after_state (JSON diff)

**HIGH Severity:**
- All MEDIUM fields +
- `reason` (required, min 15 characters)
- Management notification (if threshold exceeded)

**Pattern:**
```sql
INSERT INTO audit_logs (
  yacht_id, user_id, action_name, severity,
  entity_type, entity_id,
  before_state, after_state, reason, timestamp
) VALUES (
  $session_yacht_id,
  $session_user_id,
  'edit_invoice_amount',
  'HIGH',
  'purchase',
  $purchase_id,
  '{"amount": 1250.00}'::jsonb,
  '{"amount": 1320.00}'::jsonb,
  $reason,
  NOW()
);
```

---

### Email Notifications

**Rule:** HIGH severity actions with threshold violations MUST send email notifications.

#### Notification Triggers

| Action | Threshold | Recipients |
|--------|-----------|------------|
| edit_invoice_amount | >$500 OR >10% change | Management team |
| edit_equipment_details (serial_number) | Any change | Management + HOD |
| delete_item (completed WO) | Any attempt | HOD |
| approve_purchase | >$5,000 | Management |

**Pattern (n8n):**
```
IF (change_amount > 500 OR percent_change > 0.1) THEN
  Send Email Node:
    To: management@yacht.com
    Subject: "Invoice Amount Changed - Requires Review"
    Body: Template with details
END IF
```

---

### Permissions & Role-Based Access Control (RBAC)

**Rule:** Check `session.role` before executing mutation actions.

#### Role Hierarchy
```
OWNER > CAPTAIN > CHIEF_ENGINEER > HOD > ENGINEER > DECKHAND > CREW
```

#### Permission Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| **Own Only** | User can only modify their own items | Edit own notes |
| **Department** | User can modify items in their department | CHIEF can edit all engineering WOs |
| **HOD+** | Head of Department and above | Approve purchases |
| **Management** | Captain and Owner only | Edit critical equipment details |
| **Public** | All authenticated users | View equipment details |

**Permission Check (pseudo-code):**
```javascript
// Check if user has permission
function checkPermission(action, entity, session) {
  const permissions = {
    'edit_work_order_details': ['CHIEF_ENGINEER', 'ETO', 'ENGINEER'],
    'approve_purchase': ['CAPTAIN', 'OWNER', 'CHIEF_ENGINEER'],
    'edit_invoice_amount': ['CAPTAIN', 'OWNER', 'HOD']
  };

  if (!permissions[action].includes(session.role)) {
    return error("Insufficient permissions");
  }

  // Additional checks: own items only
  if (entity.created_by !== session.user_id && session.role === 'CREW') {
    return error("Can only edit own items");
  }
}
```

---

### Validation Rules

#### Input Validation

**Rule:** Validate ALL inputs before executing SQL.

**Checks:**
1. **Required fields:** Reject if missing
2. **Type validation:** UUID format, number ranges, enum values
3. **Length validation:** String min/max, array sizes
4. **Business rules:** Status transitions, stock availability

**Pattern:**
```javascript
// Example validation for edit_work_order_details
const schema = {
  work_order_id: { type: 'uuid', required: true },
  title: { type: 'string', minLength: 5, maxLength: 200 },
  priority: { type: 'enum', values: ['low', 'medium', 'high', 'urgent'] },
  due_date: { type: 'date', minValue: 'today' }
};

validate(input, schema);
if (errors) return { success: false, error: errors };
```

#### Business Rule Validation

**Examples:**
- Cannot edit completed/cancelled work orders
- Cannot log part usage if stock is 0
- Cannot close fault without resolution notes
- Cannot approve own purchase request
- Cannot change invoice amount without reason

**Pattern:**
```sql
-- Check business rule before update
SELECT status FROM work_orders WHERE id = $1;
IF status IN ('completed', 'cancelled') THEN
  RETURN error('Cannot edit closed work order');
END IF;
```

---

### State Transitions

**Rule:** Document allowed state transitions for stateful entities.

#### Work Order States
```
draft → pending_approval → approved → in_progress → completed
                                    ↓
                                  cancelled
```

**Allowed transitions:**
- draft → pending_approval (on submit)
- pending_approval → approved (HOD action)
- pending_approval → draft (reject)
- approved → in_progress (start work)
- in_progress → completed (mark complete)
- Any → cancelled (cancel action)

**Forbidden:**
- completed → in_progress (cannot reopen without special action)
- cancelled → approved (cannot uncancelled)

#### Fault States
```
open → in_progress → resolved → closed
  ↓                              ↑
  └────────── reopened ──────────┘
```

**Allowed:**
- open → in_progress (assign WO)
- in_progress → resolved (fix applied)
- resolved → closed (verified)
- closed → open (reopen with reason)

---

### Error Handling

**Rule:** Return user-friendly error messages, log technical details.

#### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Work order not found or does not belong to your yacht",
    "field": "work_order_id",
    "details": {} // Optional technical details
  }
}
```

#### Standard Error Codes

| Code | HTTP Status | Use Case |
|------|-------------|----------|
| VALIDATION_ERROR | 400 | Invalid input format |
| NOT_FOUND | 404 | Entity doesn't exist |
| FORBIDDEN | 403 | Insufficient permissions |
| CONFLICT | 409 | Business rule violation (can't edit closed WO) |
| INSUFFICIENT_STOCK | 409 | Not enough parts available |
| SERVER_ERROR | 500 | Unexpected database error |

**Pattern:**
```javascript
try {
  // Execute operation
} catch (error) {
  // Log technical error
  console.error('[edit_work_order_details]', error);

  // Return user-friendly message
  return {
    success: false,
    error: {
      code: 'SERVER_ERROR',
      message: 'Unable to update work order. Please try again.'
    }
  };
}
```

---

### Idempotency

**Rule:** Mutation actions should be idempotent where possible.

**Why:** Network failures may cause retries. Duplicate operations should not corrupt data.

**Strategies:**
1. **Unique constraints:** Prevent duplicate inserts
2. **Conditional updates:** Only update if state allows
3. **Idempotency keys:** Accept `idempotency_key` in request, store in operations table

**Example:**
```sql
-- Use ON CONFLICT for idempotency
INSERT INTO notes (id, work_order_id, text, created_by)
VALUES ($1, $2, $3, $4)
ON CONFLICT (id) DO NOTHING;
```

---

### Performance Considerations

#### Query Optimization

**Rule:** Index all foreign keys and commonly filtered columns.

**Required Indexes:**
```sql
-- Foreign keys (for joins)
CREATE INDEX idx_work_orders_yacht_id ON work_orders(yacht_id);
CREATE INDEX idx_work_orders_equipment_id ON work_orders(equipment_id);

-- Status filters (for WHERE clauses)
CREATE INDEX idx_work_orders_status ON work_orders(status);

-- Composite for common queries
CREATE INDEX idx_work_orders_yacht_status ON work_orders(yacht_id, status);

-- Timestamps for sorting
CREATE INDEX idx_work_orders_created_at ON work_orders(created_at DESC);
```

#### N+1 Query Prevention

**Rule:** Use JOINs or batch queries, not loops.

**❌ BAD:**
```javascript
// For each work order, query parts separately
for (wo of work_orders) {
  const parts = await query('SELECT * FROM parts WHERE work_order_id = $1', wo.id);
}
```

**✅ GOOD:**
```sql
-- Single query with JOIN
SELECT wo.*, p.*
FROM work_orders wo
LEFT JOIN work_order_parts wop ON wo.id = wop.work_order_id
LEFT JOIN parts p ON wop.part_id = p.id
WHERE wo.yacht_id = $1;
```

#### Pagination

**Rule:** All list actions MUST support pagination.

**Parameters:**
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

**Response includes:**
```json
{
  "success": true,
  "cards": [...],
  "pagination": {
    "total": 245,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

### Database Schema Conventions

#### Table Naming
- Plural nouns: `work_orders`, `parts`, `faults`
- Join tables: `entity1_entity2` (e.g., `work_order_parts`)

#### Column Naming
- Snake_case: `created_at`, `assigned_to`, `min_stock_level`
- Booleans: `is_deleted`, `requires_approval`, `quality_check_passed`
- Foreign keys: `{entity}_id` (e.g., `equipment_id`, `yacht_id`)

#### Common Columns (all tables)
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
yacht_id UUID NOT NULL,
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW(),
deleted BOOLEAN DEFAULT FALSE,
deleted_at TIMESTAMPTZ,
deleted_by UUID
```

#### Audit Columns (mutable tables)
```sql
created_by UUID NOT NULL,
updated_by UUID,
version INT DEFAULT 1  -- Optimistic locking
```

---

### Data Types

#### Standard Types

| Use Case | PostgreSQL Type | Example |
|----------|----------------|---------|
| IDs | UUID | `id UUID PRIMARY KEY` |
| Timestamps | TIMESTAMPTZ | `created_at TIMESTAMPTZ` |
| Money | NUMERIC(10,2) | `unit_cost NUMERIC(10,2)` |
| Text (short) | VARCHAR(255) | `title VARCHAR(255)` |
| Text (long) | TEXT | `description TEXT` |
| Enums | TEXT + CHECK | `status TEXT CHECK (status IN ('open', 'closed'))` |
| JSON | JSONB | `metadata JSONB` |
| Booleans | BOOLEAN | `is_active BOOLEAN` |

#### Enums as TEXT with CHECK

**Pattern:**
```sql
CREATE TABLE work_orders (
  id UUID PRIMARY KEY,
  status TEXT NOT NULL
    CHECK (status IN ('draft', 'pending_approval', 'approved', 'in_progress', 'completed', 'cancelled')),
  priority TEXT NOT NULL
    CHECK (priority IN ('low', 'medium', 'high', 'urgent'))
);
```

**Why TEXT over ENUM type:** Easier to add new values without migrations.

---

### Testing Requirements

#### For Each Action, Backend Must Test:

**Success Cases (2-3):**
- Happy path with valid data
- Edge cases (empty optional fields, max limits)
- Idempotency (retry same request)

**Failure Cases (2-3):**
- Invalid input (wrong type, missing required)
- Not found (entity doesn't exist)
- Forbidden (wrong role, wrong yacht)
- Business rule violation (can't edit closed WO)
- Insufficient stock / conflicts

**Example Test Suite:**
```
edit_work_order_details:
  ✅ Edit title and priority on open WO → success
  ✅ Edit with minimal changes → success, audit log shows diff
  ✅ Retry same edit (idempotency) → success, no duplicate audit
  ❌ Edit completed WO → error "Cannot edit closed work order"
  ❌ Invalid work_order_id → error "Work order not found"
  ❌ User from different yacht → error "Forbidden"
  ❌ User with insufficient role → error "Insufficient permissions"
```

---

## Workflow Archetypes

All 67 actions map to 6 workflow types:

| Archetype | n8n Workflow | Actions | Pattern |
|-----------|--------------|---------|---------|
| **VIEW** | master-view-workflow.json | 29 | SELECT queries, no mutation |
| **CREATE** | master-create-workflow.json | 10 | INSERT queries + audit |
| **UPDATE** | master-update-workflow.json | 15 | UPDATE queries + audit |
| **LINKING** | master-linking-workflow.json | 8 | INSERT into join tables |
| **EXPORT** | master-export-workflow.json | 4 | Generate PDF/Excel files |
| **RAG** | master-rag-workflow.json | 1 | Vector search + AI streaming |

**Routing:** Switch node examines `action_name`, routes to appropriate SQL node.

---

## Implementation Checklist

For each action, backend engineer must:

- [ ] Read action spec from `docs/actions/ACTION_BACKEND_SPEC.md`
- [ ] Identify workflow archetype (VIEW/CREATE/UPDATE/LINKING/EXPORT/RAG)
- [ ] Open corresponding n8n workflow JSON
- [ ] Add Switch case for `action_name`
- [ ] Add SQL node with queries (following transaction rules)
- [ ] Add validation node (check inputs, permissions)
- [ ] Add audit log node (if required)
- [ ] Add notification node (if threshold triggered)
- [ ] Test all success cases
- [ ] Test all failure cases
- [ ] Document any deviations from spec

---

## Documentation Structure

```
docs/
├── PHASE_5_BACKEND_BLUEPRINT.md (this file)
├── actions/
│   ├── ACTION_BACKEND_SPEC.md (67 action specs)
│   └── ACTION_TO_TABLE_MAP.md (table mapping)
└── phase4/
    └── PHASE_4_PROGRESS_TRACKER.md (frontend status)
```

---

## Next Steps

1. ✅ Read this blueprint (global rules)
2. ⏭️ Read `docs/actions/ACTION_BACKEND_SPEC.md` for detailed action specs
3. ⏭️ Reference `docs/actions/ACTION_TO_TABLE_MAP.md` for table relationships
4. ⏭️ Implement n8n workflows + SQL following specs
5. ⏭️ Test each action thoroughly
6. ⏭️ Deploy to staging environment

---

**Last Updated:** 2025-11-21
**Author:** Frontend Team
**For:** Backend Implementation Team
