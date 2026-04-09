# Entity Lens: Shopping List

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)
**Gold Standard Reference**: `fault_lens_v5_FINAL.md`

---

# BLOCKERS

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ✅ | None | - | Shopping List Lens is fully shippable |

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution
```sql
public.get_user_yacht_id()  -- Canonical function
```

## HoD Check Function
```sql
is_hod(user_id, yacht_id)  -- Used for approval permissions
```

## Audit `entity_type` Convention
| Value | Table |
|-------|-------|
| `shopping_list_item` | pms_shopping_list_items |
| `shopping_list_history` | pms_shopping_list_state_history |

---

# PART 1: DATABASE SCHEMA

## Table: `pms_shopping_list_items`

**Production DB Columns** (45 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `part_id` | uuid | YES | CONTEXT | FK → pms_parts (if existing part) |
| `part_name` | text | NOT NULL | REQUIRED | Name of part/item needed |
| `part_number` | text | YES | OPTIONAL | Part number |
| `manufacturer` | text | YES | OPTIONAL | Manufacturer name |
| `is_candidate_part` | boolean | NOT NULL | BACKEND_AUTO | True if not in parts catalog. Default: false |
| `quantity_requested` | numeric | NOT NULL | REQUIRED | Amount requested |
| `quantity_approved` | numeric | YES | CONTEXT | HoD approved amount |
| `quantity_ordered` | numeric | YES | CONTEXT | Amount placed on order |
| `quantity_received` | numeric | YES | BACKEND_AUTO | Amount received. Default: 0 |
| `quantity_installed` | numeric | YES | BACKEND_AUTO | Amount installed. Default: 0 |
| `unit` | text | YES | OPTIONAL | Unit of measure |
| `preferred_supplier` | text | YES | OPTIONAL | Suggested supplier |
| `estimated_unit_price` | numeric | YES | OPTIONAL | Estimated cost |
| `status` | text | NOT NULL | BACKEND_AUTO | Current workflow state. Default: 'candidate' |
| `source_type` | text | NOT NULL | REQUIRED | Origin of request |
| `source_work_order_id` | uuid | YES | CONTEXT | FK → pms_work_orders (if from WO) |
| `source_receiving_id` | uuid | YES | CONTEXT | FK → pms_receiving_events (if from receiving) |
| `source_notes` | text | YES | OPTIONAL | Additional source context |
| `order_id` | uuid | YES | CONTEXT | FK → pms_orders (when ordered) |
| `order_line_number` | integer | YES | BACKEND_AUTO | Line number on order |
| `approved_by` | uuid | YES | BACKEND_AUTO | Who approved |
| `approved_at` | timestamp | YES | BACKEND_AUTO | When approved |
| `approval_notes` | text | YES | OPTIONAL | Approval comments |
| `rejected_by` | uuid | YES | BACKEND_AUTO | Who rejected |
| `rejected_at` | timestamp | YES | BACKEND_AUTO | When rejected |
| `rejection_reason` | text | YES | CONTEXT | Why rejected |
| `rejection_notes` | text | YES | OPTIONAL | Rejection details |
| `fulfilled_at` | timestamp | YES | BACKEND_AUTO | When fully received |
| `installed_at` | timestamp | YES | BACKEND_AUTO | When installed |
| `installed_to_equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment |
| `urgency` | text | YES | OPTIONAL | Priority level |
| `required_by_date` | date | YES | OPTIONAL | Deadline |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_by` | uuid | YES | BACKEND_AUTO | Last modifier |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |
| `deleted_at` | timestamp | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who deleted |
| `deletion_reason` | text | YES | OPTIONAL | Why deleted |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `candidate_promoted_to_part_id` | uuid | YES | BACKEND_AUTO | FK → pms_parts (if promoted) |
| `promoted_by` | uuid | YES | BACKEND_AUTO | Who promoted |
| `promoted_at` | timestamp | YES | BACKEND_AUTO | When promoted |

**Row Count**: 34

---

## Status Values (State Machine)

```sql
CHECK (status = ANY (ARRAY[
    'candidate',           -- Initial state, awaiting review
    'under_review',        -- Being reviewed by HoD
    'approved',            -- Approved for ordering
    'ordered',             -- Placed on purchase order
    'partially_fulfilled', -- Some items received
    'fulfilled',           -- All items received
    'installed'            -- Installed on equipment
]))
```

**State Transitions**:
```
candidate → under_review → approved → ordered → partially_fulfilled → fulfilled → installed
                        ↘ rejected (terminal)
```

---

## Source Type Values

```sql
CHECK (source_type = ANY (ARRAY[
    'inventory_low',       -- Auto-generated from low stock
    'inventory_oos',       -- Auto-generated from out of stock
    'work_order_usage',    -- Generated from WO part consumption
    'receiving_missing',   -- From receiving discrepancy
    'receiving_damaged',   -- From receiving damaged goods
    'manual_add'           -- Manually added by user
]))
```

---

## Urgency Values

```sql
CHECK (urgency = ANY (ARRAY['low', 'normal', 'high', 'critical']))
```

---

## Table: `pms_shopping_list_state_history`

**Production DB Columns** (13 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `shopping_list_item_id` | uuid | NOT NULL | CONTEXT | FK → pms_shopping_list_items |
| `previous_state` | text | YES | BACKEND_AUTO | State before change |
| `new_state` | text | NOT NULL | BACKEND_AUTO | State after change |
| `transition_reason` | text | YES | OPTIONAL | Why state changed |
| `transition_notes` | text | YES | OPTIONAL | Additional notes |
| `changed_by` | uuid | NOT NULL | BACKEND_AUTO | Who made change |
| `changed_at` | timestamp | NOT NULL | BACKEND_AUTO | When changed |
| `related_order_id` | uuid | YES | CONTEXT | FK → pms_orders |
| `related_receiving_event_id` | uuid | YES | CONTEXT | FK → pms_receiving_events |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |

**Row Count**: 36

**Purpose**: Audit trail of all state changes. Auto-populated by trigger `trg_log_shopping_list_state_change`.

---

# PART 2: MICRO-ACTIONS

## Action 1: `create_shopping_list_item`

**Purpose**: Add new item to shopping list

**Allowed Roles**: All Crew (TIER 1+)

**Tables Written**:
- `pms_shopping_list_items` (INSERT)
- `pms_shopping_list_state_history` (INSERT via trigger)
- `pms_audit_log` (INSERT)

**RLS Constraint**: Can only create with `status = 'candidate'` and `created_by = auth.uid()`

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `part_name` | REQUIRED | User input |
| `quantity_requested` | REQUIRED | User input |
| `source_type` | REQUIRED | Context (default: 'manual_add') |
| `part_id` | OPTIONAL | User selects existing part |
| `part_number` | OPTIONAL | User input or from part |
| `manufacturer` | OPTIONAL | User input or from part |
| `urgency` | OPTIONAL | User dropdown |
| `required_by_date` | OPTIONAL | User date picker |
| `source_work_order_id` | CONTEXT | If from WO |
| `source_notes` | OPTIONAL | User input |
| `is_candidate_part` | BACKEND_AUTO | true if part_id IS NULL |

---

## Action 2: `approve_shopping_list_item`

**Purpose**: HoD approves item for ordering

**Allowed Roles**: HoD only (captain, chief_engineer, purser, etc.)

**Tables Written**:
- `pms_shopping_list_items` (UPDATE status, approved_by, approved_at, quantity_approved)
- `pms_shopping_list_state_history` (INSERT via trigger)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `quantity_approved` | REQUIRED | User input (may differ from requested) |
| `approval_notes` | OPTIONAL | User input |

**Real SQL**:
```sql
UPDATE pms_shopping_list_items
SET
    status = 'approved',
    quantity_approved = :quantity_approved,
    approved_by = auth.uid(),
    approved_at = NOW(),
    approval_notes = :approval_notes,
    updated_by = auth.uid(),
    updated_at = NOW()
WHERE id = :item_id
  AND yacht_id = public.get_user_yacht_id()
  AND status IN ('candidate', 'under_review')
  AND deleted_at IS NULL;
```

---

## Action 3: `reject_shopping_list_item`

**Purpose**: HoD rejects item

**Allowed Roles**: HoD only

**Tables Written**:
- `pms_shopping_list_items` (UPDATE status, rejected_by, rejected_at, rejection_reason)
- `pms_shopping_list_state_history` (INSERT via trigger)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `rejection_reason` | REQUIRED | User input |
| `rejection_notes` | OPTIONAL | User input |

---

## Action 4: `promote_candidate_to_part`

**Purpose**: Add candidate item to parts catalog

**Allowed Roles**: Engineers (chief_engineer, eto, manager)

**Tables Written**:
- `pms_parts` (INSERT - new part created)
- `pms_shopping_list_items` (UPDATE candidate_promoted_to_part_id, promoted_by, promoted_at)
- `pms_audit_log` (INSERT)

**Business Rules**:
- Only items with `is_candidate_part = true`
- Creates new part in pms_parts with initial quantity = 0
- Links shopping list item to new part

---

## Action 5: `view_item_history`

**Purpose**: Show state change timeline

**Allowed Roles**: All Crew (read-only)

**Tables Read**: `pms_shopping_list_state_history`

**Real SQL**:
```sql
SELECT
    h.previous_state,
    h.new_state,
    h.transition_reason,
    h.changed_at,
    (SELECT name FROM auth_users_profiles WHERE id = h.changed_by) AS changed_by_name,
    h.related_order_id,
    h.related_receiving_event_id
FROM pms_shopping_list_state_history h
WHERE h.shopping_list_item_id = :item_id
  AND h.yacht_id = public.get_user_yacht_id()
ORDER BY h.changed_at DESC;
```

---

## Action 6: `link_to_work_order` (Escape Hatch)

**Purpose**: Navigate to source work order

**Allowed Roles**: All Crew (read-only)

**Tables Read**: `pms_work_orders`

---

# PART 3: RLS POLICIES

## ACTUAL DEPLOYED

```sql
-- 1. SELECT: All authenticated users can view
CREATE POLICY "Users can view shopping list items for their yacht" ON pms_shopping_list_items
    FOR SELECT TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- 2. INSERT: All users can create (with constraints)
CREATE POLICY "Users can create shopping list items" ON pms_shopping_list_items
    FOR INSERT TO authenticated
    WITH CHECK (
        (yacht_id = get_user_yacht_id())
        AND (created_by = auth.uid())
        AND (status = 'candidate')
    );

-- 3. UPDATE: HoD only
CREATE POLICY "HOD can update shopping list items" ON pms_shopping_list_items
    FOR UPDATE TO authenticated
    USING (
        (yacht_id = get_user_yacht_id())
        AND is_hod(auth.uid(), yacht_id)
    )
    WITH CHECK (yacht_id = get_user_yacht_id());

-- 4. Service role bypass
CREATE POLICY "Service role has full access to shopping list" ON pms_shopping_list_items
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
```

**RLS Status**: ✅ CANONICAL

---

## Triggers

| Trigger | Event | Function | Purpose |
|---------|-------|----------|---------|
| `trg_enforce_shopping_list_edit_rules` | BEFORE UPDATE | enforce_shopping_list_edit_rules() | Enforces state machine rules |
| `trg_log_shopping_list_state_change` | AFTER INSERT/UPDATE | log_shopping_list_state_change() | Auto-logs state history |

---

# PART 4: QUERY PATTERNS

## Scenario 1: "Items awaiting approval"

```sql
SELECT
    s.id,
    s.part_name,
    s.part_number,
    s.quantity_requested,
    s.urgency,
    s.required_by_date,
    s.source_type,
    s.created_at,
    (SELECT name FROM auth_users_profiles WHERE id = s.created_by) AS requested_by
FROM pms_shopping_list_items s
WHERE s.status IN ('candidate', 'under_review')
  AND s.yacht_id = public.get_user_yacht_id()
  AND s.deleted_at IS NULL
ORDER BY
    CASE s.urgency
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'normal' THEN 3
        ELSE 4
    END,
    s.required_by_date NULLS LAST,
    s.created_at DESC;
```

## Scenario 2: "Items on order"

```sql
SELECT
    s.id,
    s.part_name,
    s.quantity_ordered,
    s.quantity_received,
    o.po_number,
    o.status AS order_status,
    o.supplier_id
FROM pms_shopping_list_items s
LEFT JOIN pms_orders o ON s.order_id = o.id
WHERE s.status = 'ordered'
  AND s.yacht_id = public.get_user_yacht_id()
  AND s.deleted_at IS NULL
ORDER BY s.updated_at DESC;
```

---

# PART 5: SUMMARY

## Shopping List Lens Actions (Final)

| Action | Tables Written | Signature | RLS Tier |
|--------|---------------|-----------|----------|
| `create_shopping_list_item` | pms_shopping_list_items, history, audit | No | All Crew |
| `approve_shopping_list_item` | pms_shopping_list_items, history, audit | No | HoD Only |
| `reject_shopping_list_item` | pms_shopping_list_items, history, audit | No | HoD Only |
| `promote_candidate_to_part` | pms_parts, pms_shopping_list_items, audit | No | Engineers |
| `view_item_history` | None (read) | No | All Crew |

## Escape Hatches

| From Shopping List | To Lens | Trigger |
|--------------------|---------|---------|
| link_to_work_order | Work Order Lens | Click source WO |
| view_part_details | Part Lens | Click linked part |
| view_receiving | Receiving Lens | Click receiving event |

## Key Invariants

1. **Items start as 'candidate'** - INSERT enforces initial status
2. **State transitions logged** - Automatic via trigger
3. **HoD approval required** - UPDATE restricted to HoD role
4. **Candidate promotion** - Creates new part in catalog
5. **Soft delete pattern** - Uses deleted_at

---

**END OF SHOPPING LIST LENS v1 FINAL**
