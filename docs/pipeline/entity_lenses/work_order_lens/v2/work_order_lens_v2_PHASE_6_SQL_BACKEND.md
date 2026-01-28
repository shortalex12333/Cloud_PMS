# Work Order Lens v2 - PHASE 6: SQL & Backend Mapping

**Status**: COMPLETE
**Created**: 2026-01-24

---

## 6.1 Query Patterns

### List Work Orders (Default)

**Intent**: List all active WOs for yacht
**Handler**: `work_order_handlers.list_work_orders`

```sql
SELECT
    wo.id,
    wo.wo_number,
    wo.title,
    wo.type,
    wo.priority,
    wo.status,
    wo.due_date,
    wo.assigned_to,
    e.name as equipment_name,
    u.full_name as assigned_to_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
LEFT JOIN auth_users_profiles u ON wo.assigned_to = u.id
WHERE wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY
    CASE wo.priority
        WHEN 'emergency' THEN 1
        WHEN 'critical' THEN 2
        WHEN 'important' THEN 3
        WHEN 'routine' THEN 4
    END,
    wo.due_date NULLS LAST;
```

### Single WO Detail

**Intent**: Get full details for one WO
**Handler**: `work_order_handlers.get_work_order`

```sql
SELECT
    wo.*,
    e.name as equipment_name,
    e.location as equipment_location,
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

### WO by Number

**Intent**: Lookup by WO number
**Handler**: `work_order_handlers.get_work_order_by_number`

```sql
SELECT wo.*
FROM pms_work_orders wo
WHERE wo.wo_number = $1
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL;
```

### My Assigned WOs

**Intent**: "my work orders"
**Handler**: `work_order_handlers.list_my_work_orders`

```sql
SELECT wo.*, e.name as equipment_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE wo.assigned_to = auth.uid()
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.status NOT IN ('completed', 'cancelled')
AND wo.deleted_at IS NULL
ORDER BY wo.priority DESC, wo.due_date ASC;
```

### Overdue WOs

**Intent**: "overdue work orders"
**Handler**: `work_order_handlers.list_overdue_work_orders`

```sql
SELECT
    wo.*,
    (CURRENT_DATE - wo.due_date) as days_overdue,
    e.name as equipment_name
FROM pms_work_orders wo
LEFT JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE wo.yacht_id = public.get_user_yacht_id()
AND wo.due_date < CURRENT_DATE
AND wo.status NOT IN ('completed', 'cancelled')
AND wo.deleted_at IS NULL
ORDER BY wo.due_date ASC;
```

### WOs for Equipment

**Intent**: "work orders for [equipment]"
**Handler**: `work_order_handlers.list_work_orders_for_equipment`

```sql
SELECT wo.*
FROM pms_work_orders wo
JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE e.name ILIKE '%' || $1 || '%'
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC;
```

### WO for Fault

**Intent**: "work order for [fault]"
**Handler**: `work_order_handlers.get_work_order_for_fault`

```sql
SELECT wo.*
FROM pms_work_orders wo
JOIN pms_faults f ON wo.fault_id = f.id
WHERE f.title ILIKE '%' || $1 || '%'
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL;
```

---

## 6.2 Action SQL Mapping

### Action 1: Create Work Order

**Handler**: `work_order_handlers.create_work_order`
**RLS**: INSERT policy (canonical)

```sql
-- Step 1: Generate WO number
SELECT public.generate_wo_number(public.get_user_yacht_id()) AS wo_number;

-- Step 2: Insert
INSERT INTO pms_work_orders (
    id, yacht_id, wo_number, title, description,
    type, priority, status, equipment_id, fault_id,
    assigned_to, due_date, created_at, created_by, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    $wo_number,
    $title,
    $description,
    COALESCE($type, 'scheduled'),
    COALESCE($priority, 'routine'),
    'planned',
    $equipment_id,
    $fault_id,
    $assigned_to,
    $due_date,
    NOW(),
    auth.uid(),
    NOW()
) RETURNING id, wo_number;
```

### Action 2: Update Work Order

**Handler**: `work_order_handlers.update_work_order`
**RLS**: UPDATE policy (canonical + role)

```sql
UPDATE pms_work_orders
SET
    title = COALESCE($title, title),
    description = COALESCE($description, description),
    type = COALESCE($type, type),
    priority = COALESCE($priority, priority),
    equipment_id = COALESCE($equipment_id, equipment_id),
    assigned_to = COALESCE($assigned_to, assigned_to),
    due_date = COALESCE($due_date, due_date),
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
AND status NOT IN ('completed', 'cancelled')
RETURNING id, wo_number;
```

### Action 3: Complete Work Order

**Handler**: `work_order_handlers.complete_work_order`
**RLS**: UPDATE policy (canonical + role)
**BLOCKED BY**: B2, B3, B4

```sql
-- Step 1: Validate checklist
SELECT COUNT(*) as incomplete
FROM pms_work_order_checklist
WHERE work_order_id = $work_order_id
AND is_required = true
AND is_completed = false;

-- Step 2: Update WO
UPDATE pms_work_orders
SET
    status = 'completed',
    completed_at = NOW(),
    completed_by = auth.uid(),
    completion_notes = $completion_notes,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND status IN ('planned', 'in_progress')
AND deleted_at IS NULL
RETURNING id, wo_number, fault_id, equipment_id;

-- Step 3: Insert history
INSERT INTO pms_work_order_history (
    id, yacht_id, work_order_id, equipment_id,
    completed_by, completed_at, notes, hours_logged,
    status_on_completion, parts_used, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    $work_order_id,
    $equipment_id,
    auth.uid(),
    NOW(),
    $completion_notes,
    $hours_logged,
    'completed',
    $parts_used_json,
    NOW()
);

-- Step 4: Record part usage (for each part)
INSERT INTO pms_part_usage (
    id, yacht_id, part_id, quantity, work_order_id,
    equipment_id, usage_reason, used_by, used_at
) VALUES (
    uuid_generate_v4(),
    public.get_user_yacht_id(),
    $part_id,
    $quantity,
    $work_order_id,
    $equipment_id,
    'work_order',
    auth.uid(),
    NOW()
);

-- Step 5: Deduct inventory
SELECT public.deduct_part_inventory($part_id, $quantity, $work_order_id);
```

### Action 4: Add Note

**Handler**: `work_order_handlers.add_note`
**RLS**: INSERT policy
**BLOCKED BY**: B1

```sql
INSERT INTO pms_work_order_notes (
    id, work_order_id, note_text, note_type,
    created_by, created_at
) VALUES (
    uuid_generate_v4(),
    $work_order_id,
    $note_text,
    COALESCE($note_type, 'general'),
    auth.uid(),
    NOW()
) RETURNING id;
```

### Action 5: Reassign Work Order

**Handler**: `work_order_handlers.reassign_work_order`
**RLS**: UPDATE policy (canonical + HoD role)
**Signature**: REQUIRED

```sql
-- Step 1: Validate new assignee
SELECT id, full_name, role
FROM auth_users_profiles
WHERE id = $new_assignee_id
AND yacht_id = public.get_user_yacht_id();

-- Step 2: Get old value
SELECT assigned_to FROM pms_work_orders
WHERE id = $work_order_id;

-- Step 3: Update
UPDATE pms_work_orders
SET
    assigned_to = $new_assignee_id,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND status NOT IN ('completed', 'cancelled')
AND deleted_at IS NULL
RETURNING id, wo_number;

-- Step 4: Audit log (via service role)
INSERT INTO pms_audit_log (
    id, yacht_id, action, entity_type, entity_id,
    user_id, signature, old_values, new_values, created_at
) VALUES (
    uuid_generate_v4(),
    public.get_user_yacht_id(),
    'reassigned',
    'work_order',
    $work_order_id,
    auth.uid(),
    $signature,
    jsonb_build_object('assigned_to', $old_assignee_id),
    jsonb_build_object('assigned_to', $new_assignee_id),
    NOW()
);
```

### Action 6: Archive Work Order

**Handler**: `work_order_handlers.archive_work_order`
**RLS**: UPDATE policy (canonical + HoD role)
**Signature**: REQUIRED
**BLOCKED BY**: B4

```sql
-- Step 1: Get current state
SELECT status, fault_id FROM pms_work_orders
WHERE id = $work_order_id;

-- Step 2: Archive
UPDATE pms_work_orders
SET
    status = 'cancelled',
    deleted_at = NOW(),
    deleted_by = auth.uid(),
    deletion_reason = $deletion_reason,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING id, wo_number, fault_id;

-- Step 3: Audit log (via service role)
INSERT INTO pms_audit_log (
    id, yacht_id, action, entity_type, entity_id,
    user_id, signature, old_values, new_values, created_at
) VALUES (
    uuid_generate_v4(),
    public.get_user_yacht_id(),
    'archived',
    'work_order',
    $work_order_id,
    auth.uid(),
    $signature,
    jsonb_build_object('status', $old_status, 'deleted_at', NULL),
    jsonb_build_object('status', 'cancelled', 'deletion_reason', $deletion_reason),
    NOW()
);
```

---

## 6.3 Checklist Operations

### Get Checklist Items

```sql
SELECT c.*
FROM pms_work_order_checklist c
WHERE c.work_order_id = $work_order_id
AND c.yacht_id = public.get_user_yacht_id()
AND c.deleted_at IS NULL
ORDER BY c.sequence;
```

### Complete Checklist Item

```sql
UPDATE pms_work_order_checklist
SET
    is_completed = true,
    completed_at = NOW(),
    completed_by = auth.uid(),
    completion_notes = $completion_notes,
    measurement_value = $measurement_value,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $checklist_item_id
AND yacht_id = public.get_user_yacht_id()
RETURNING id;
```

---

## 6.4 Notes Operations

### Get Notes for WO

**BLOCKED BY**: B1 (cross-yacht leakage)

```sql
SELECT n.*, u.full_name as created_by_name
FROM pms_work_order_notes n
LEFT JOIN auth_users_profiles u ON n.created_by = u.id
WHERE n.work_order_id = $work_order_id
ORDER BY n.created_at DESC;
```

---

## 6.5 Parts Operations

### Get Parts for WO

**BLOCKED BY**: B2 (cross-yacht leakage)

```sql
SELECT wop.*, p.name as part_name, p.part_number
FROM pms_work_order_parts wop
JOIN pms_parts p ON wop.part_id = p.id
WHERE wop.work_order_id = $work_order_id
AND wop.deleted_at IS NULL;
```

### Add Part to WO

```sql
INSERT INTO pms_work_order_parts (
    id, work_order_id, part_id, quantity, notes, created_at
) VALUES (
    gen_random_uuid(),
    $work_order_id,
    $part_id,
    $quantity,
    $notes,
    NOW()
)
ON CONFLICT (work_order_id, part_id)
DO UPDATE SET
    quantity = pms_work_order_parts.quantity + EXCLUDED.quantity,
    updated_at = NOW()
RETURNING id;
```

---

## 6.6 History Operations

### Get WO History

```sql
SELECT h.*, u.full_name as completed_by_name
FROM pms_work_order_history h
LEFT JOIN auth_users_profiles u ON h.completed_by = u.id
WHERE h.work_order_id = $work_order_id
AND h.yacht_id = public.get_user_yacht_id()
ORDER BY h.completed_at DESC;
```

---

## 6.7 Canonical Functions

| Function | Signature | Verified |
|----------|-----------|----------|
| `get_user_yacht_id()` | () → uuid | ✅ |
| `get_user_role()` | () → text | ✅ |
| `is_manager()` | () → boolean | ✅ |
| `generate_wo_number(uuid)` | (yacht_id) → text | ✅ |
| `deduct_part_inventory(uuid, int, uuid)` | (part_id, qty, wo_id) → void | ✅ |

---

## 6.8 Handler Files

| Handler | Location | Actions |
|---------|----------|---------|
| `work_order_handlers.py` | apps/api/handlers/ | All 6 actions |
| `action_registry.py` | apps/api/actions/ | Action registration |
| `intent_parser.py` | apps/api/ | Intent detection |

---

## PHASE 6 GATE: COMPLETE

| Check | Status |
|-------|--------|
| All query patterns documented | ✅ |
| All action SQL documented | ✅ |
| Canonical functions verified | ✅ |
| Handler files identified | ✅ |
| Blockers linked to specific operations | ✅ |

**Proceeding to Phase 7: RLS Matrix**
