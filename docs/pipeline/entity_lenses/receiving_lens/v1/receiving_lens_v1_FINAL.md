# Entity Lens: Receiving

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)
**Gold Standard Reference**: `fault_lens_v5_FINAL.md`

---

# BLOCKERS

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| ✅ | None | - | Receiving Lens is fully shippable |

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution
```sql
public.get_user_yacht_id()  -- Canonical function
```

## HoD Check Function
```sql
is_hod(user_id, yacht_id)  -- Used for lock/unlock permissions
```

## Audit `entity_type` Convention
| Value | Table |
|-------|-------|
| `receiving_event` | pms_receiving_events |
| `receiving_line_item` | pms_receiving_line_items |

---

# PART 1: DATABASE SCHEMA

## Table: `pms_receiving_events`

**Production DB Columns** (21 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry |
| `receiving_number` | text | NOT NULL | BACKEND_AUTO | Auto-generated: RCV-{YYYY}-{NNNN} |
| `order_id` | uuid | YES | CONTEXT | FK → pms_orders (if from PO) |
| `received_at` | timestamp | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `received_by` | uuid | NOT NULL | BACKEND_AUTO | auth.uid() |
| `location` | text | YES | OPTIONAL | Where items received |
| `status` | text | NOT NULL | BACKEND_AUTO | Current state. Default: 'in_progress' |
| `delivery_method` | text | YES | OPTIONAL | How delivered |
| `tracking_number` | text | YES | OPTIONAL | Carrier tracking |
| `notes` | text | YES | OPTIONAL | General notes |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_by` | uuid | YES | BACKEND_AUTO | Last modifier |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |
| `deleted_at` | timestamp | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who deleted |
| `deletion_reason` | text | YES | OPTIONAL | Why deleted |
| `is_locked` | boolean | NOT NULL | BACKEND_AUTO | Default: false. Locks after completion |
| `receiving_session_id` | uuid | YES | CONTEXT | FK → pms_receiving_sessions |
| `was_camera_initiated` | boolean | YES | BACKEND_AUTO | Default: false. True if started via camera/OCR |

**Row Count**: 3

---

## Status Values

```sql
CHECK (status = ANY (ARRAY[
    'in_progress',  -- Receiving ongoing
    'completed',    -- All items processed
    'partial',      -- Some items received, others pending
    'discrepancy'   -- Issues detected (missing, damaged, wrong items)
]))
```

---

## Table: `pms_receiving_line_items`

**Production DB Columns** (37 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `receiving_event_id` | uuid | NOT NULL | CONTEXT | FK → pms_receiving_events |
| `shopping_list_item_id` | uuid | YES | CONTEXT | FK → pms_shopping_list_items |
| `part_id` | uuid | YES | CONTEXT | FK → pms_parts |
| `part_name` | text | NOT NULL | REQUIRED | Part name |
| `part_number` | text | YES | OPTIONAL | Part number |
| `manufacturer` | text | YES | OPTIONAL | Manufacturer |
| `quantity_expected` | numeric | YES | CONTEXT | Expected from order |
| `quantity_received` | numeric | NOT NULL | REQUIRED | Actual count |
| `quantity_accepted` | numeric | NOT NULL | REQUIRED | Accepted amount |
| `quantity_rejected` | numeric | YES | BACKEND_AUTO | Rejected amount. Default: 0 |
| `unit` | text | YES | OPTIONAL | Unit of measure |
| `disposition` | text | NOT NULL | REQUIRED | Line item status |
| `disposition_notes` | text | YES | OPTIONAL | Notes about disposition |
| `installed_immediately` | boolean | YES | OPTIONAL | Default: false |
| `installed_to_equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment |
| `installed_to_work_order_id` | uuid | YES | CONTEXT | FK → pms_work_orders |
| `installed_at` | timestamp | YES | BACKEND_AUTO | When installed |
| `installed_by` | uuid | YES | BACKEND_AUTO | Who installed |
| `unit_price` | numeric | YES | OPTIONAL | Price per unit |
| `line_total` | numeric | YES | BACKEND_AUTO | Calculated total |
| `serial_numbers` | text[] | YES | OPTIONAL | For serialized items |
| `batch_lot_number` | text | YES | OPTIONAL | For batch tracking |
| `expiration_date` | date | YES | OPTIONAL | For perishable items |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp | NOT NULL | BACKEND_AUTO | NOW() |
| `updated_by` | uuid | YES | BACKEND_AUTO | Last modifier |
| `updated_at` | timestamp | NOT NULL | BACKEND_AUTO | Trigger |
| `verified_by` | uuid | YES | BACKEND_AUTO | Who verified |
| `verified_at` | timestamp | YES | BACKEND_AUTO | When verified |
| `is_verified` | boolean | NOT NULL | BACKEND_AUTO | Default: false |
| `received_by` | uuid | YES | BACKEND_AUTO | Who received this line |
| `draft_line_id` | uuid | YES | CONTEXT | FK → pms_receiving_draft_lines |
| `verification_notes` | text | YES | OPTIONAL | Verification comments |
| `human_verified_at` | timestamp | YES | BACKEND_AUTO | Human verification time |
| `human_verified_by` | uuid | YES | BACKEND_AUTO | Who did human verification |

**Row Count**: 3

---

## Disposition Values

```sql
CHECK (disposition = ANY (ARRAY[
    'accepted',           -- Fully accepted
    'accepted_with_notes', -- Accepted but notes added
    'rejected',           -- Fully rejected
    'partial_accept',     -- Partially accepted
    'missing',            -- Expected but not received
    'extra',              -- Not expected, received anyway
    'incorrect'           -- Wrong item received
]))
```

---

# PART 2: MICRO-ACTIONS

## Action 1: `start_receiving_event`

**Purpose**: Begin new receiving session

**Allowed Roles**: All Crew (authenticated)

**Tables Written**:
- `pms_receiving_events` (INSERT)
- `pms_audit_log` (INSERT)

**RLS Constraint**: `received_by = auth.uid()`

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `order_id` | OPTIONAL | User selects PO |
| `location` | OPTIONAL | User input |
| `delivery_method` | OPTIONAL | User dropdown |
| `tracking_number` | OPTIONAL | User input |
| `notes` | OPTIONAL | User input |
| `receiving_number` | BACKEND_AUTO | Auto-generated |
| `received_by` | BACKEND_AUTO | auth.uid() |
| `status` | BACKEND_AUTO | 'in_progress' |

---

## Action 2: `add_line_item`

**Purpose**: Add received item to event

**Allowed Roles**: Receiver (owner) or HoD

**Tables Written**:
- `pms_receiving_line_items` (INSERT)
- `pms_audit_log` (INSERT)

**RLS Constraint**: Event must not be locked

**Field Classification**:

| Field | Classification | Source |
|-------|----------------|--------|
| `part_name` | REQUIRED | User input or from shopping list |
| `quantity_received` | REQUIRED | User count |
| `quantity_accepted` | REQUIRED | User decision |
| `disposition` | REQUIRED | User dropdown |
| `part_id` | OPTIONAL | Auto-match or user select |
| `shopping_list_item_id` | OPTIONAL | Link to shopping list |
| `serial_numbers` | OPTIONAL | User input |
| `installed_immediately` | OPTIONAL | User checkbox |
| `installed_to_equipment_id` | CONTEXT | If immediately installed |

**Real SQL**:
```sql
INSERT INTO pms_receiving_line_items (
    id, yacht_id, receiving_event_id, part_id, shopping_list_item_id,
    part_name, part_number, manufacturer,
    quantity_expected, quantity_received, quantity_accepted, quantity_rejected,
    unit, disposition, disposition_notes,
    installed_immediately, installed_to_equipment_id,
    metadata, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :receiving_event_id,
    :part_id,
    :shopping_list_item_id,
    :part_name,
    :part_number,
    :manufacturer,
    :quantity_expected,
    :quantity_received,
    :quantity_accepted,
    GREATEST(0, :quantity_received - :quantity_accepted),
    :unit,
    :disposition,
    :disposition_notes,
    COALESCE(:installed_immediately, false),
    :installed_to_equipment_id,
    jsonb_build_object('session_id', :session_id),
    NOW(),
    NOW()
)
RETURNING id;
```

---

## Action 3: `complete_receiving_event`

**Purpose**: Finalize receiving and update inventory

**Allowed Roles**: Receiver (owner) or HoD

**Tables Written**:
- `pms_receiving_events` (UPDATE status, is_locked)
- `pms_parts` (UPDATE quantity_on_hand for accepted items)
- `pms_shopping_list_items` (UPDATE quantity_received, status)
- `pms_audit_log` (INSERT)

**Business Rules**:
- Sets `is_locked = true` (prevents further edits)
- Updates part quantities for accepted items
- Updates shopping list item status to 'fulfilled' or 'partially_fulfilled'
- Calculates event status based on line dispositions

**Trigger**: `trg_auto_lock_receiving_event` enforces lock on completion

---

## Action 4: `report_discrepancy`

**Purpose**: Flag receiving event with issues

**Allowed Roles**: All Crew

**Tables Written**:
- `pms_receiving_events` (UPDATE status = 'discrepancy')
- `pms_shopping_list_items` (INSERT for missing/damaged items)
- `pms_audit_log` (INSERT)

**Business Rules**:
- Auto-creates shopping list items for missing items (source_type = 'receiving_missing')
- Auto-creates shopping list items for damaged items (source_type = 'receiving_damaged')

---

## Action 5: `verify_line_item`

**Purpose**: Verify line item was correctly processed

**Allowed Roles**: HoD only (second pair of eyes)

**Tables Written**:
- `pms_receiving_line_items` (UPDATE is_verified, verified_by, verified_at)
- `pms_audit_log` (INSERT)

---

## Action 6: `view_receiving_photos` (Escape Hatch)

**Purpose**: View attached photos/documents

**Allowed Roles**: All Crew (read-only)

**Tables Read**: `pms_receiving_attachments`

---

# PART 3: RLS POLICIES

## Table: `pms_receiving_events`

### ACTUAL DEPLOYED

```sql
-- 1. SELECT: All users can view their yacht's events
CREATE POLICY "Users can view receiving events for their yacht" ON pms_receiving_events
    FOR SELECT TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- 2. INSERT: Authenticated users can create
CREATE POLICY "Authorized users can create receiving events" ON pms_receiving_events
    FOR INSERT TO authenticated
    WITH CHECK (
        (yacht_id = get_user_yacht_id())
        AND (received_by = auth.uid())
    );

-- 3. UPDATE: Owner can update (if not locked) or HoD can update
CREATE POLICY "Receiver can update own receiving event" ON pms_receiving_events
    FOR UPDATE TO authenticated
    USING (
        (yacht_id = get_user_yacht_id())
        AND (
            ((received_by = auth.uid()) AND (is_locked = false))
            OR is_hod(auth.uid(), yacht_id)
        )
    )
    WITH CHECK (yacht_id = get_user_yacht_id());

-- 4. Service role bypass
CREATE POLICY "Service role has full access to receiving events" ON pms_receiving_events
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);
```

**RLS Status**: ✅ CANONICAL

---

## Triggers

| Trigger | Event | Function | Purpose |
|---------|-------|----------|---------|
| `trg_auto_lock_receiving_event` | BEFORE UPDATE | auto_lock_receiving_event() | Auto-locks when completed |

---

# PART 4: QUERY PATTERNS

## Scenario 1: "Recent receiving events"

```sql
SELECT
    r.id,
    r.receiving_number,
    r.received_at,
    r.status,
    r.location,
    r.is_locked,
    (SELECT name FROM auth_users_profiles WHERE id = r.received_by) AS received_by_name,
    o.po_number,
    (SELECT COUNT(*) FROM pms_receiving_line_items li WHERE li.receiving_event_id = r.id) AS line_count,
    (SELECT COUNT(*) FROM pms_receiving_line_items li
     WHERE li.receiving_event_id = r.id
     AND li.disposition NOT IN ('accepted', 'accepted_with_notes')) AS discrepancy_count
FROM pms_receiving_events r
LEFT JOIN pms_orders o ON r.order_id = o.id
WHERE r.yacht_id = public.get_user_yacht_id()
  AND r.deleted_at IS NULL
ORDER BY r.received_at DESC
LIMIT 20;
```

## Scenario 2: "Line items for receiving RCV-2026-0003"

```sql
SELECT
    li.id,
    li.part_name,
    li.part_number,
    li.quantity_expected,
    li.quantity_received,
    li.quantity_accepted,
    li.disposition,
    li.is_verified,
    li.installed_immediately,
    p.quantity_on_hand AS current_stock,
    (SELECT name FROM auth_users_profiles WHERE id = li.received_by) AS received_by_name
FROM pms_receiving_line_items li
LEFT JOIN pms_parts p ON li.part_id = p.id
WHERE li.receiving_event_id = :event_id
  AND li.yacht_id = public.get_user_yacht_id()
ORDER BY li.created_at;
```

## Scenario 3: "Items with discrepancies"

```sql
SELECT
    r.receiving_number,
    r.received_at,
    li.part_name,
    li.quantity_expected,
    li.quantity_received,
    li.disposition,
    li.disposition_notes
FROM pms_receiving_line_items li
JOIN pms_receiving_events r ON li.receiving_event_id = r.id
WHERE li.disposition NOT IN ('accepted', 'accepted_with_notes')
  AND li.yacht_id = public.get_user_yacht_id()
ORDER BY r.received_at DESC;
```

---

# PART 5: SUMMARY

## Receiving Lens Actions (Final)

| Action | Tables Written | Signature | RLS Tier |
|--------|---------------|-----------|----------|
| `start_receiving_event` | pms_receiving_events, audit | No | All Crew |
| `add_line_item` | pms_receiving_line_items, audit | No | Receiver/HoD |
| `complete_receiving_event` | events, parts, shopping_list, audit | No | Receiver/HoD |
| `report_discrepancy` | events, shopping_list, audit | No | All Crew |
| `verify_line_item` | pms_receiving_line_items, audit | No | HoD Only |
| `view_receiving_photos` | None (read) | No | All Crew |

## Escape Hatches

| From Receiving | To Lens | Trigger |
|----------------|---------|---------|
| view_part_details | Part Lens | Click linked part |
| view_shopping_list_item | Shopping List Lens | Click shopping list item |
| view_purchase_order | (Future) PO Lens | Click linked order |

## Key Invariants

1. **Event owned by receiver** - INSERT enforces `received_by = auth.uid()`
2. **Lock on completion** - Prevents edits after completion
3. **Inventory auto-update** - Accepted quantities update pms_parts
4. **Discrepancy auto-shopping** - Missing/damaged items auto-add to shopping list
5. **Soft delete pattern** - Uses deleted_at

---

**END OF RECEIVING LENS v1 FINAL**
