# Work Order Lens - PHASE 6: SQL & Backend Mapping

**Status**: COMPLETE
**Created**: 2026-01-24

---

## CANONICAL PATTERNS (REQUIRED)

### Yacht Isolation
```sql
-- ALWAYS USE THIS:
public.get_user_yacht_id()

-- NEVER USE:
-- auth.user_yacht_id() (doesn't exist)
-- auth.jwt() ->> 'yacht_id' (not reliable)
-- current_setting('app.yacht_id') (not set)
```

### Signature Invariant
```sql
-- pms_audit_log.signature is NOT NULL
-- For non-signature actions:
signature = '{}'::jsonb

-- For signature-required actions:
signature = '{"signer_id": "uuid", "signed_at": "timestamp", "device_id": "text", "action_hash": "text"}'::jsonb
```

### Entity Type Values (Canonical List)
```sql
'fault', 'work_order', 'note', 'attachment', 'equipment',
'part', 'inventory_item', 'shopping_list_item', 'receiving_event'
```

---

## FUNCTIONS VERIFIED

| Function | Location | Verified |
|----------|----------|----------|
| `public.get_user_yacht_id()` | 02_p0_actions_tables_REVISED.sql:489 | ✅ EXISTS |
| `public.generate_wo_number(p_yacht_id)` | 02_p0_actions_tables_REVISED.sql:391 | ✅ EXISTS |
| `public.update_updated_at()` | 02_p0_actions_tables_REVISED.sql:615 | ✅ EXISTS |
| `cascade_wo_status_to_fault()` | CUMULATIVE_SCHEMA_MIGRATIONS.sql:334 | ⚠️ PROPOSED |
| `public.user_has_role(TEXT[])` | CUMULATIVE_SCHEMA_MIGRATIONS.sql:551 | ⚠️ PROPOSED |
| `public.deduct_part_inventory(...)` | 02_p0_actions_tables_REVISED.sql:424 | ✅ EXISTS |

---

## Action 1: Create Work Order

### SELECT Queries

```sql
-- Equipment lookup (optional, if equipment context provided)
SELECT id, name, category, status
FROM pms_equipment
WHERE yacht_id = public.get_user_yacht_id()
AND (name ILIKE $1 OR id = $2)
AND status != 'decommissioned'
LIMIT 10;

-- Fault lookup (optional, if fault context provided)
SELECT id, title, severity, equipment_id
FROM pms_faults
WHERE yacht_id = public.get_user_yacht_id()
AND status = 'open'
AND (title ILIKE $1 OR id = $2)
LIMIT 10;

-- Crew lookup (for assignment)
SELECT id, full_name, role
FROM auth_users_profiles
WHERE yacht_id = public.get_user_yacht_id()
ORDER BY full_name;
```

### INSERT Queries

```sql
-- Main work order insert
INSERT INTO pms_work_orders (
  id,
  yacht_id,
  wo_number,
  title,
  description,
  type,
  priority,
  status,
  equipment_id,
  fault_id,
  assigned_to,
  due_date,
  metadata,
  created_at,
  created_by,
  updated_at
) VALUES (
  gen_random_uuid(),
  public.get_user_yacht_id(),
  public.generate_wo_number(public.get_user_yacht_id()),
  $1,  -- title (REQUIRED)
  $2,  -- description (OPTIONAL)
  $3,  -- type (REQUIRED, enum)
  COALESCE($4, 'medium'),  -- priority (default medium)
  'open',  -- status (BACKEND_AUTO)
  $5,  -- equipment_id (OPTIONAL)
  $6,  -- fault_id (OPTIONAL)
  $7,  -- assigned_to (OPTIONAL)
  $8,  -- due_date (OPTIONAL)
  COALESCE($9, '{}'::jsonb),  -- metadata
  NOW(),
  auth.uid(),
  NOW()
)
RETURNING id, wo_number;

-- Audit log entry
INSERT INTO pms_audit_log (
  yacht_id,
  user_id,
  action,
  entity_type,
  entity_id,
  old_values,
  new_values,
  signature,
  metadata,
  created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'create_work_order',
  'work_order',
  $1,  -- new work_order.id
  NULL,  -- no old values for create
  $2,  -- new values jsonb
  '{}'::jsonb,  -- no signature required
  $3,  -- session metadata
  NOW()
);
```

### Triggers Involved
- `update_updated_at` (auto-fires on subsequent updates)

### Transaction Boundary
```sql
BEGIN;
  -- INSERT pms_work_orders
  -- INSERT pms_audit_log
COMMIT;
```

---

## Action 2: Update Work Order

### SELECT Queries

```sql
-- Get current state for optimistic locking
SELECT id, title, description, type, priority, status,
       equipment_id, assigned_to, due_date, updated_at
FROM pms_work_orders
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
FOR UPDATE;
```

### UPDATE Queries

```sql
-- Update work order (only changed fields)
UPDATE pms_work_orders
SET
  title = COALESCE($2, title),
  description = COALESCE($3, description),
  type = COALESCE($4, type),
  priority = COALESCE($5, priority),
  equipment_id = COALESCE($6, equipment_id),
  due_date = COALESCE($7, due_date),
  updated_at = NOW(),
  updated_by = auth.uid()
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING *;

-- Audit log with delta
INSERT INTO pms_audit_log (
  yacht_id,
  user_id,
  action,
  entity_type,
  entity_id,
  old_values,
  new_values,
  signature,
  created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'update_work_order',
  'work_order',
  $1,
  $2,  -- old values jsonb
  $3,  -- new values jsonb (delta only)
  '{}'::jsonb,
  NOW()
);
```

### Triggers Involved
- `update_updated_at` (BEFORE UPDATE)

### Transaction Boundary
```sql
BEGIN;
  -- SELECT FOR UPDATE (lock)
  -- UPDATE pms_work_orders
  -- INSERT pms_audit_log
COMMIT;
```

---

## Action 3: Complete Work Order

### SELECT Queries

```sql
-- Validate WO state and checklist
SELECT
  wo.*,
  (SELECT COUNT(*) FROM pms_work_order_checklist c
   WHERE c.work_order_id = wo.id
   AND c.is_required = true
   AND c.is_completed = false) as incomplete_required,
  (SELECT json_agg(json_build_object(
     'part_id', p.part_id,
     'quantity', p.quantity,
     'part_name', pt.name
   )) FROM pms_work_order_parts p
   JOIN pms_parts pt ON p.part_id = pt.id
   WHERE p.work_order_id = wo.id
   AND p.deleted_at IS NULL) as parts_to_deduct
FROM pms_work_orders wo
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
AND wo.status IN ('open', 'in_progress');
```

### UPDATE Queries

```sql
-- Complete work order
UPDATE pms_work_orders
SET
  status = 'completed',
  completed_at = NOW(),
  completed_by = auth.uid(),
  completion_notes = $2,
  updated_at = NOW(),
  updated_by = auth.uid()
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING *;

-- Deduct parts using existing function
-- For each part in parts_to_deduct:
SELECT public.deduct_part_inventory(
  public.get_user_yacht_id(),
  $1,  -- part_id
  $2,  -- quantity
  $3,  -- work_order_id
  $4,  -- equipment_id
  'work_order',  -- usage_reason
  $5,  -- notes
  auth.uid()  -- used_by
);

-- Create history record
INSERT INTO pms_work_order_history (
  id,
  work_order_id,
  yacht_id,
  equipment_id,
  status_on_completion,
  completed_at,
  completed_by,
  notes,
  parts_used,
  created_at
) VALUES (
  gen_random_uuid(),
  $1,
  public.get_user_yacht_id(),
  $2,  -- equipment_id from WO
  'completed',
  NOW(),
  auth.uid(),
  $3,  -- completion_notes
  $4,  -- parts_used jsonb
  NOW()
);

-- Audit log
INSERT INTO pms_audit_log (
  yacht_id, user_id, action, entity_type, entity_id,
  old_values, new_values, signature, created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'complete_work_order',
  'work_order',
  $1,
  $2,
  $3,
  '{}'::jsonb,
  NOW()
);
```

### Triggers Involved
- `update_updated_at` (BEFORE UPDATE)
- `trg_wo_status_cascade_to_fault` (AFTER UPDATE OF status) **[PROPOSED]**

### Cascade SQL (if trigger not deployed)
```sql
-- HYPOTHETICAL: If trigger doesn't exist, run manually
UPDATE pms_faults
SET
  status = 'resolved',
  resolved_at = NOW(),
  resolved_by = auth.uid(),
  updated_at = NOW()
WHERE id = (SELECT fault_id FROM pms_work_orders WHERE id = $1)
AND fault_id IS NOT NULL;
```

### Transaction Boundary
```sql
BEGIN;
  -- SELECT validation
  -- UPDATE pms_work_orders
  -- FOR EACH part: deduct_part_inventory()
  -- INSERT pms_work_order_history
  -- INSERT pms_audit_log
  -- (trigger cascades to pms_faults)
COMMIT;
```

---

## Action 4: Add Note

### SELECT Queries

```sql
-- Validate WO exists and is accessible
SELECT id, status, title
FROM pms_work_orders
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL;
```

### INSERT Queries

```sql
-- Insert note
INSERT INTO pms_work_order_notes (
  id,
  work_order_id,
  note_text,
  note_type,
  metadata,
  created_at,
  created_by
) VALUES (
  gen_random_uuid(),
  $1,  -- work_order_id
  $2,  -- note_text (REQUIRED)
  COALESCE($3, 'general'),  -- note_type
  COALESCE($4, '{}'::jsonb),
  NOW(),
  auth.uid()
)
RETURNING id;

-- Audit log
INSERT INTO pms_audit_log (
  yacht_id, user_id, action, entity_type, entity_id,
  new_values, signature, created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'add_work_order_note',
  'work_order',
  $1,  -- work_order_id (not note_id, for aggregation)
  jsonb_build_object('note_id', $2, 'note_text', $3),
  '{}'::jsonb,
  NOW()
);
```

### Triggers Involved
None

### Transaction Boundary
```sql
BEGIN;
  -- SELECT validation
  -- INSERT pms_work_order_notes
  -- INSERT pms_audit_log
COMMIT;
```

---

## Action 5: Reassign Work Order

### SELECT Queries

```sql
-- Validate WO and get current assignment
SELECT id, assigned_to, status
FROM pms_work_orders
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
AND status NOT IN ('completed', 'cancelled');

-- Validate new assignee
SELECT id, full_name, role
FROM auth_users_profiles
WHERE id = $2
AND yacht_id = public.get_user_yacht_id();

-- Validate current user is HoD **[PROPOSED FUNCTION]**
-- SELECT public.user_has_role(ARRAY['captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser']);
```

### UPDATE Queries

```sql
-- Reassign
UPDATE pms_work_orders
SET
  assigned_to = $2,
  updated_at = NOW(),
  updated_by = auth.uid()
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING *;

-- Audit log with SIGNATURE
INSERT INTO pms_audit_log (
  yacht_id, user_id, action, entity_type, entity_id,
  old_values, new_values, signature, created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'reassign_work_order',
  'work_order',
  $1,
  jsonb_build_object('assigned_to', $3),  -- old assignee
  jsonb_build_object('assigned_to', $2),  -- new assignee
  $4,  -- SIGNATURE PAYLOAD (required)
  NOW()
);
```

### Triggers Involved
- `update_updated_at`

### Transaction Boundary
```sql
BEGIN;
  -- Validate permissions
  -- Validate assignees
  -- UPDATE pms_work_orders
  -- INSERT pms_audit_log (with signature)
COMMIT;
```

---

## Action 6: Archive Work Order

### SELECT Queries

```sql
-- Validate WO state
SELECT
  wo.id, wo.status, wo.fault_id,
  f.status as fault_status
FROM pms_work_orders wo
LEFT JOIN pms_faults f ON wo.fault_id = f.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL;

-- Validate user role **[PROPOSED]**
-- SELECT public.user_has_role(ARRAY['captain', 'chief_engineer', 'chief_steward', 'chief_officer', 'purser']);
```

### UPDATE Queries

```sql
-- Soft delete / archive
UPDATE pms_work_orders
SET
  status = 'cancelled',
  deleted_at = NOW(),
  deleted_by = auth.uid(),
  deletion_reason = $2,  -- REQUIRED
  updated_at = NOW(),
  updated_by = auth.uid()
WHERE id = $1
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING *;

-- Cascade: Return linked fault to open **[IF TRIGGER NOT DEPLOYED]**
UPDATE pms_faults
SET
  status = 'open',
  resolved_at = NULL,
  resolved_by = NULL,
  updated_at = NOW()
WHERE id = $3  -- fault_id from WO
AND id IS NOT NULL;

-- Audit log with SIGNATURE
INSERT INTO pms_audit_log (
  yacht_id, user_id, action, entity_type, entity_id,
  old_values, new_values, signature, created_at
) VALUES (
  public.get_user_yacht_id(),
  auth.uid(),
  'archive_work_order',
  'work_order',
  $1,
  $2,  -- old state
  jsonb_build_object('status', 'cancelled', 'deleted_at', NOW(), 'deletion_reason', $3),
  $4,  -- SIGNATURE PAYLOAD (required)
  NOW()
);
```

### Triggers Involved
- `update_updated_at`
- `trg_wo_status_cascade_to_fault` **[PROPOSED]** - would handle fault cascade

### Transaction Boundary
```sql
BEGIN;
  -- Validate permissions
  -- UPDATE pms_work_orders (soft delete)
  -- UPDATE pms_faults (cascade back to open)
  -- INSERT pms_audit_log (with signature)
COMMIT;
```

---

## COMMON QUERY PATTERNS

### Work Order List Query
```sql
SELECT
  wo.id, wo.wo_number, wo.title, wo.type, wo.priority, wo.status,
  wo.due_date, wo.assigned_to, wo.created_at,
  e.name as equipment_name,
  u.full_name as assigned_to_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN auth_users_profiles u ON wo.assigned_to = u.id
WHERE wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY
  CASE wo.priority
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    WHEN 'low' THEN 4
  END,
  wo.due_date NULLS LAST;
```

### Single Work Order Detail Query
```sql
SELECT
  wo.*,
  e.name as equipment_name,
  e.category as equipment_category,
  f.title as fault_title,
  f.severity as fault_severity,
  creator.full_name as created_by_name,
  assignee.full_name as assigned_to_name,
  completer.full_name as completed_by_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN pms_faults f ON wo.fault_id = f.id
LEFT JOIN auth_users_profiles creator ON wo.created_by = creator.id
LEFT JOIN auth_users_profiles assignee ON wo.assigned_to = assignee.id
LEFT JOIN auth_users_profiles completer ON wo.completed_by = completer.id
WHERE wo.id = $1
AND wo.yacht_id = public.get_user_yacht_id();
```

### Work Order History Query
```sql
SELECT
  al.action,
  al.created_at,
  al.old_values,
  al.new_values,
  al.signature,
  u.full_name as actor_name
FROM pms_audit_log al
JOIN auth_users_profiles u ON al.user_id = u.id
WHERE al.entity_type = 'work_order'
AND al.entity_id = $1
AND al.yacht_id = public.get_user_yacht_id()
ORDER BY al.created_at DESC;
```

---

## HYPOTHETICAL SQL LABELS

| Item | Status | Notes |
|------|--------|-------|
| `cascade_wo_status_to_fault()` trigger | PROPOSED | In CUMULATIVE_MIGRATIONS, may not be deployed |
| `user_has_role()` function | PROPOSED | Needed for role checks, may not be deployed |
| Role-based RLS policies | PROPOSED | Current policies don't check roles |

---

## PHASE 6 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 6.1-6.6 SELECT queries for all actions | ✅ |
| 6.1-6.6 INSERT/UPDATE queries for all actions | ✅ |
| 6.1-6.6 Triggers identified | ✅ |
| 6.1-6.6 Functions verified (exists in snapshot) | ✅ |
| 6.7 Transaction boundaries defined | ✅ |
| 6.8 Hypothetical SQL labeled | ✅ |
| Canonical patterns used | ✅ |

**Proceeding to Phase 7: RLS & Security Matrix**
