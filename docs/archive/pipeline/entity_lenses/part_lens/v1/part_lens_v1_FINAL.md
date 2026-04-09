# Entity Lens: Part (& Inventory)

**Status**: v1 - PRODUCTION READY
**Last Updated**: 2026-01-25
**Schema Source**: Production Supabase Database (db_truth_snapshot.md)
**Operating Procedure**: `LENS_BUILDER_OPERATING_PROCEDURE.md`
**Gold Standard Reference**: `fault_lens_v5_FINAL.md`

---

# BLOCKERS (must resolve before lens is shippable)

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| **B1** | `pms_inventory_transactions` has RLS DISABLED | Transaction history visible to all | Deploy RLS migration |

> **NOTE**: Parts and inventory stock tables use canonical RLS. Only the transaction history table is missing RLS.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution

**Deployed function** (canonical):

```sql
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_users_profiles
  WHERE id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;
```

---

## Audit `entity_type` Convention

| Value | Table |
|-------|-------|
| `part` | pms_parts |
| `inventory_stock` | pms_inventory_stock |
| `inventory_transaction` | pms_inventory_transactions |

---

## Signature Invariant

`pms_audit_log.signature` is **NOT NULL**. Convention:

| Scenario | Value |
|----------|-------|
| Non-signature action | `'{}'::jsonb` (empty object) |
| Stock adjustment (requires sign-off) | Full signature payload |

---

# PART 1: EXACT DATABASE SCHEMA

## Table: `pms_parts`

**Production DB Columns** (19 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, gen_random_uuid() |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `name` | text | NOT NULL | REQUIRED | Part name/description |
| `part_number` | text | YES | OPTIONAL | Manufacturer part number |
| `manufacturer` | text | YES | OPTIONAL | OEM name |
| `description` | text | YES | OPTIONAL | Long-form details |
| `category` | text | YES | OPTIONAL | Part category (filters, belts, etc.) |
| `model_compatibility` | jsonb | YES | OPTIONAL | Compatible equipment models. Default: '[]' |
| `quantity_on_hand` | integer | NOT NULL | BACKEND_AUTO | Current stock level. Default: 0 |
| `minimum_quantity` | integer | YES | OPTIONAL | Reorder threshold. Default: 0 |
| `unit` | text | YES | OPTIONAL | Unit of measure (ea, kg, L, etc.). Default: 'ea' |
| `location` | text | YES | OPTIONAL | Primary storage location |
| `last_counted_at` | timestamp with time zone | YES | BACKEND_AUTO | Last physical count date |
| `last_counted_by` | uuid | YES | BACKEND_AUTO | Who performed last count |
| `search_embedding` | vector | YES | BACKEND_AUTO | For semantic search |
| `embedding_text` | text | YES | BACKEND_AUTO | Text used for embedding |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data. Default: '{}' |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Trigger: update_updated_at |

**Row Count**: 538

---

## Unit Values (CHECK Constraint)

```sql
CHECK ((unit = ANY (ARRAY[
    'ea', 'kg', 'g', 'L', 'mL', 'm', 'cm', 'mm', 'ft', 'in',
    'm2', 'm3', 'gal', 'qt', 'pt', 'oz', 'lb',
    'box', 'set', 'pair', 'roll', 'sheet'
])) OR (unit IS NULL))
```

| Unit | Description |
|------|-------------|
| `ea` | Each (default) |
| `kg`, `g`, `lb`, `oz` | Weight units |
| `L`, `mL`, `gal`, `qt`, `pt` | Volume units |
| `m`, `cm`, `mm`, `ft`, `in` | Length units |
| `m2`, `m3` | Area/volume units |
| `box`, `set`, `pair`, `roll`, `sheet` | Package units |

---

## Indexes (Production)

| Index | Columns | Purpose |
|-------|---------|---------|
| `parts_pkey` | id | Primary key |
| `idx_parts_yacht_id` | yacht_id | Yacht isolation |
| `idx_parts_part_number` | part_number | Lookup by part number |
| `idx_parts_manufacturer` | yacht_id, manufacturer | Filter by manufacturer |
| `idx_parts_category` | category | Filter by category |
| `idx_pms_parts_low_stock` | yacht_id, quantity_on_hand, minimum_quantity (WHERE qty <= min) | Low stock alerts |
| `idx_pms_parts_embedding` | search_embedding (ivfflat) | Semantic search |

---

## Triggers

| Trigger | Event | Function | Purpose |
|---------|-------|----------|---------|
| `trg_prevent_embedding_overwrite` | BEFORE UPDATE | prevent_embedding_overwrite() | Prevents accidental embedding loss |

---

## Table: `pms_inventory_stock`

**Production DB Columns** (16 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `part_id` | uuid | NOT NULL | CONTEXT | FK → pms_parts(id) |
| `location` | text | YES | OPTIONAL | Storage location |
| `quantity` | integer | NOT NULL | REQUIRED | Stock quantity at this location. Default: 0 |
| `min_quantity` | integer | YES | OPTIONAL | Location-specific minimum |
| `max_quantity` | integer | YES | OPTIONAL | Location-specific maximum |
| `reorder_quantity` | integer | YES | OPTIONAL | Suggested reorder amount |
| `last_counted_at` | timestamp with time zone | YES | BACKEND_AUTO | Last count date |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | Trigger |
| `updated_by` | uuid | YES | BACKEND_AUTO | Last modifier |
| `deleted_at` | timestamp with time zone | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who deleted |
| `deletion_reason` | text | YES | OPTIONAL | Why deleted |

**Row Count**: 282

**Purpose**: Tracks stock at multiple locations per part. Allows:
- Engine Room: 5 units of Filter X
- Forward Store: 10 units of Filter X
- Total quantity syncs back to pms_parts.quantity_on_hand

---

## Table: `pms_inventory_transactions`

**Production DB Columns** (9 total):

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `stock_id` | uuid | NOT NULL | CONTEXT | FK → pms_inventory_stock(id) |
| `transaction_type` | text | NOT NULL | REQUIRED | Type of movement |
| `quantity_change` | integer | NOT NULL | REQUIRED | +/- change amount |
| `quantity_before` | integer | NOT NULL | BACKEND_AUTO | Prior quantity |
| `quantity_after` | integer | NOT NULL | BACKEND_AUTO | New quantity |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | Who made change |
| `created_at` | timestamp with time zone | NOT NULL | BACKEND_AUTO | When change occurred |

**Row Count**: 0 (not yet used in production)

**RLS**: ❌ DISABLED - **SECURITY GAP**

**Transaction Types** (application-defined):
- `received` - Stock added from receiving
- `consumed` - Stock used for work order
- `adjusted` - Manual count adjustment
- `transferred` - Moved between locations
- `returned` - Returned to supplier

---

## Table: `pms_equipment_parts_bom` (Related)

Links parts to equipment (Bill of Materials). Already documented in Equipment Lens.

| Column | Purpose |
|--------|---------|
| equipment_id | Which equipment |
| part_id | Which part |
| quantity_required | How many needed |

**Row Count**: 15

---

# PART 2: MICRO-ACTIONS WITH FIELD CLASSIFICATION

> **ACTION ACTIVATION DOCTRINE**: Actions are NOT visible on search results lists. When a part becomes the **focused entity**, its context actions become available.

---

## Action 1: `adjust_stock_quantity`

**Purpose**: Manual stock count adjustment

**Allowed Roles**: Engineers (chief_engineer, eto, deck, interior)

**Tables Written**:
- `pms_parts` (UPDATE quantity_on_hand)
- `pms_inventory_stock` (UPDATE quantity) - if location-based
- `pms_inventory_transactions` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | - | CONTEXT | From focused part |
| `new_quantity` | pms_parts.quantity_on_hand | REQUIRED | User input |
| `adjustment_reason` | pms_audit_log.metadata | REQUIRED | User input |
| `location` | pms_inventory_stock.location | OPTIONAL | If multi-location tracking |
| `counted_at` | pms_parts.last_counted_at | BACKEND_AUTO | NOW() |
| `counted_by` | pms_parts.last_counted_by | BACKEND_AUTO | auth.uid() |

**Business Rules**:
- Adjustment reason is REQUIRED (audit trail)
- Large adjustments (>50% change) may require signature
- Creates transaction record for history

**Real SQL**:
```sql
BEGIN;

-- 1. Calculate change
SELECT quantity_on_hand INTO :old_quantity
FROM pms_parts
WHERE id = :part_id AND yacht_id = public.get_user_yacht_id();

-- 2. Update part master
UPDATE pms_parts
SET
    quantity_on_hand = :new_quantity,
    last_counted_at = NOW(),
    last_counted_by = auth.uid(),
    updated_at = NOW()
WHERE id = :part_id
  AND yacht_id = public.get_user_yacht_id();

-- 3. Insert transaction record
INSERT INTO pms_inventory_transactions (
    id, yacht_id, stock_id, transaction_type,
    quantity_change, quantity_before, quantity_after,
    user_id, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :stock_id,                           -- NULL if no location tracking
    'adjusted',
    :new_quantity - :old_quantity,       -- Change amount
    :old_quantity,
    :new_quantity,
    auth.uid(),
    NOW()
);

-- 4. Audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'part',
    :part_id,
    'adjust_stock_quantity',
    auth.uid(),
    jsonb_build_object('quantity_on_hand', :old_quantity),
    jsonb_build_object('quantity_on_hand', :new_quantity),
    CASE
        WHEN ABS(:new_quantity - :old_quantity) > (:old_quantity * 0.5)
        THEN :signature_payload::jsonb     -- Large adjustment requires signature
        ELSE '{}'::jsonb
    END,
    jsonb_build_object('reason', :adjustment_reason, 'session_id', :session_id),
    NOW()
);

COMMIT;
```

**Ledger UI Event**:
```json
{
  "event": "stock_adjusted",
  "message": "Oil Filter 12345 adjusted from 5 to 8 units",
  "entity_type": "part",
  "entity_id": "part_uuid",
  "user_name": "John Smith",
  "timestamp": "2026-01-25T11:00:00Z",
  "metadata": {"reason": "Physical count correction"}
}
```

---

## Action 2: `record_part_consumption`

**Purpose**: Record part usage for a work order

**Allowed Roles**: Engineers (chief_engineer, eto, deck, interior)

**Tables Written**:
- `pms_part_usage` (INSERT)
- `pms_parts` (UPDATE quantity_on_hand)
- `pms_inventory_transactions` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | pms_part_usage.part_id | CONTEXT | From focused part |
| `work_order_id` | pms_part_usage.work_order_id | REQUIRED | User selects WO |
| `quantity_used` | pms_part_usage.quantity_used | REQUIRED | User input |
| `usage_notes` | pms_part_usage.notes | OPTIONAL | User input |

**Business Rules**:
- Cannot consume more than quantity_on_hand
- Work order must be in 'in_progress' or 'planned' status
- Updates both pms_part_usage AND pms_parts.quantity_on_hand

**Real SQL**:
```sql
BEGIN;

-- 1. Verify stock available
SELECT quantity_on_hand INTO :current_qty
FROM pms_parts
WHERE id = :part_id AND yacht_id = public.get_user_yacht_id();

IF :quantity_used > :current_qty THEN
    RAISE EXCEPTION 'Insufficient stock: requested %, available %', :quantity_used, :current_qty;
END IF;

-- 2. Insert usage record
INSERT INTO pms_part_usage (
    id, yacht_id, work_order_id, part_id,
    quantity_used, notes, metadata, created_by, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :work_order_id,
    :part_id,
    :quantity_used,
    :usage_notes,
    jsonb_build_object('session_id', :session_id),
    auth.uid(),
    NOW()
)
RETURNING id INTO :usage_id;

-- 3. Update part quantity
UPDATE pms_parts
SET
    quantity_on_hand = quantity_on_hand - :quantity_used,
    updated_at = NOW()
WHERE id = :part_id
  AND yacht_id = public.get_user_yacht_id();

-- 4. Transaction record
INSERT INTO pms_inventory_transactions (
    id, yacht_id, stock_id, transaction_type,
    quantity_change, quantity_before, quantity_after,
    user_id, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    NULL,
    'consumed',
    -:quantity_used,
    :current_qty,
    :current_qty - :quantity_used,
    auth.uid(),
    NOW()
);

-- 5. Audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action, user_id,
    old_values, new_values, signature, metadata, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'part',
    :part_id,
    'record_part_consumption',
    auth.uid(),
    jsonb_build_object('quantity_on_hand', :current_qty),
    jsonb_build_object('quantity_on_hand', :current_qty - :quantity_used, 'usage_id', :usage_id),
    '{}'::jsonb,
    jsonb_build_object('work_order_id', :work_order_id, 'quantity_used', :quantity_used),
    NOW()
);

COMMIT;
```

---

## Action 3: `add_to_shopping_list`

**Purpose**: Create shopping list item for reorder

**Allowed Roles**: All Crew (TIER 1+)

**Tables Written**:
- `pms_shopping_list_items` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | pms_shopping_list_items.part_id | CONTEXT | From focused part |
| `quantity_requested` | pms_shopping_list_items.quantity | REQUIRED | User input |
| `priority` | pms_shopping_list_items.priority | OPTIONAL | User dropdown |
| `notes` | pms_shopping_list_items.notes | OPTIONAL | User input |
| `source_type` | pms_shopping_list_items.source_type | BACKEND_AUTO | 'manual_add' |

**Real SQL**:
```sql
INSERT INTO pms_shopping_list_items (
    id, yacht_id, part_id, quantity, priority,
    notes, source_type, requested_by, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :part_id,
    :quantity_requested,
    COALESCE(:priority, 'normal'),
    :notes,
    'manual_add',
    auth.uid(),
    NOW()
)
RETURNING id;
```

---

## Action 4: `view_part_usage_history`

**Purpose**: Show consumption history (escape hatch)

**Allowed Roles**: All Crew (read-only)

**Tables Written**: None (read-only)

**Tables Read**:
- `pms_part_usage`
- `pms_work_orders` (for WO details)

**Real SQL**:
```sql
SELECT
    pu.id,
    pu.quantity_used,
    pu.notes,
    pu.created_at,
    wo.wo_number,
    wo.title AS work_order_title,
    (SELECT name FROM auth_users_profiles WHERE id = pu.created_by) AS used_by_name
FROM pms_part_usage pu
JOIN pms_work_orders wo ON pu.work_order_id = wo.id
WHERE pu.part_id = :part_id
  AND pu.yacht_id = public.get_user_yacht_id()
ORDER BY pu.created_at DESC
LIMIT 50;
```

---

## Action 5: `view_compatible_equipment`

**Purpose**: Show equipment this part works with (escape hatch to Equipment Lens)

**Allowed Roles**: All Crew (read-only)

**Tables Written**: None (read-only)

**Tables Read**:
- `pms_equipment_parts_bom`
- `pms_equipment`

**Real SQL**:
```sql
SELECT
    e.id AS equipment_id,
    e.name AS equipment_name,
    e.code AS equipment_code,
    e.location,
    e.status,
    bom.quantity_required,
    bom.notes AS bom_notes
FROM pms_equipment_parts_bom bom
JOIN pms_equipment e ON bom.equipment_id = e.id
WHERE bom.part_id = :part_id
  AND bom.yacht_id = public.get_user_yacht_id()
  AND e.deleted_at IS NULL
ORDER BY e.name;
```

---

## Action 6: `add_part_note`

**Purpose**: Add observation/note to part record

**Allowed Roles**: All Crew (TIER 1+)

**Tables Written**:
- `pms_notes` (INSERT with part_id)
- `pms_audit_log` (INSERT)

Similar pattern to Equipment Lens `add_equipment_note`.

---

# PART 3: LOW STOCK DETECTION

## Automatic Detection

Parts with `quantity_on_hand <= minimum_quantity` are flagged as low stock.

**Index for Performance**:
```sql
CREATE INDEX idx_pms_parts_low_stock ON public.pms_parts
    USING btree (yacht_id, quantity_on_hand, minimum_quantity)
    WHERE (quantity_on_hand <= minimum_quantity);
```

**Query for Low Stock Parts**:
```sql
SELECT
    id,
    name,
    part_number,
    quantity_on_hand,
    minimum_quantity,
    unit,
    location
FROM pms_parts
WHERE quantity_on_hand <= minimum_quantity
  AND minimum_quantity > 0
  AND yacht_id = public.get_user_yacht_id()
ORDER BY (minimum_quantity - quantity_on_hand) DESC;  -- Most critical first
```

## Shopping List Auto-Generation

When stock drops below minimum, system can auto-create shopping list item:

```sql
-- Auto-create shopping list item for low stock
INSERT INTO pms_shopping_list_items (
    id, yacht_id, part_id, quantity, priority,
    source_type, metadata, created_at
)
SELECT
    gen_random_uuid(),
    p.yacht_id,
    p.id,
    p.minimum_quantity - p.quantity_on_hand,  -- Suggested order qty
    'normal',
    'inventory_low',                          -- Auto-generated source
    jsonb_build_object('auto_generated', true, 'trigger', 'low_stock'),
    NOW()
FROM pms_parts p
WHERE p.quantity_on_hand < p.minimum_quantity
  AND p.minimum_quantity > 0
  AND p.yacht_id = public.get_user_yacht_id()
  AND NOT EXISTS (
      SELECT 1 FROM pms_shopping_list_items sli
      WHERE sli.part_id = p.id
      AND sli.status NOT IN ('received', 'cancelled')
  );
```

---

# PART 4: SEMANTIC SEARCH

## Vector Embedding

Parts support semantic search via `search_embedding` (pgvector).

**Embedding Generation** (handled by backend):
```sql
-- embedding_text = CONCAT(name, ' ', COALESCE(part_number, ''), ' ', COALESCE(manufacturer, ''), ' ', COALESCE(description, ''))
UPDATE pms_parts
SET
    embedding_text = :computed_text,
    search_embedding = :embedding_vector  -- From OpenAI/Anthropic embedding API
WHERE id = :part_id;
```

**Semantic Search Query**:
```sql
SELECT
    id,
    name,
    part_number,
    manufacturer,
    quantity_on_hand,
    1 - (search_embedding <=> :query_embedding) AS similarity
FROM pms_parts
WHERE yacht_id = public.get_user_yacht_id()
  AND search_embedding IS NOT NULL
ORDER BY search_embedding <=> :query_embedding
LIMIT 10;
```

**Trigger Protection**: `trg_prevent_embedding_overwrite` prevents accidental embedding loss during normal updates.

---

# PART 5: RLS POLICIES

## Table: `pms_parts`

### ACTUAL DEPLOYED

```sql
-- 1. SELECT: All users can view parts
CREATE POLICY "Users can view parts" ON pms_parts
    FOR SELECT TO public
    USING (yacht_id = get_user_yacht_id());

-- 2. ALL: Engineers can manage parts
CREATE POLICY "Engineers can manage parts" ON pms_parts
    FOR ALL TO public
    USING (
        (yacht_id = get_user_yacht_id())
        AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'manager'::text]))
    );

-- 3. Service role bypass
CREATE POLICY "Service role full access parts" ON pms_parts
    FOR ALL TO service_role
    USING (true);
```

**RLS Status**: ✅ CANONICAL

---

## Table: `pms_inventory_stock`

### ACTUAL DEPLOYED

```sql
-- 1. SELECT: All users can view stock
CREATE POLICY "Users can view stock levels" ON pms_inventory_stock
    FOR SELECT TO public
    USING (yacht_id = get_user_yacht_id());

-- 2. ALL: Engineers can manage stock
CREATE POLICY "Engineers can manage stock" ON pms_inventory_stock
    FOR ALL TO public
    USING (
        (yacht_id = get_user_yacht_id())
        AND (get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text]))
    );

-- 3. Service role bypass
CREATE POLICY "Service role full access inventory_stock" ON pms_inventory_stock
    FOR ALL TO service_role
    USING (true);
```

**RLS Status**: ✅ CANONICAL

---

## Table: `pms_inventory_transactions`

### ACTUAL DEPLOYED

**RLS**: ❌ DISABLED - **SECURITY GAP**

### PROPOSED (Migration Required)

```sql
-- Migration: 20260125_005_fix_inventory_transactions_rls.sql
ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "engineers_insert_transactions" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY['chief_engineer'::text, 'eto'::text, 'deck'::text, 'interior'::text])
    );

CREATE POLICY "service_role_full_access_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);
```

---

## Role Hierarchy for Part Lens

```
TIER 1 (All Crew):
  - deckhand, steward, chef, etc.
  - Can: VIEW parts, ADD notes, ADD to shopping list

TIER 2 (Engineers + Operators):
  - engineer, eto, deck, interior
  - Can: TIER 1 + ADJUST stock, RECORD consumption

TIER 3 (HoD + Captain):
  - captain, chief_engineer, manager
  - Can: TIER 2 + MANAGE all part data
```

---

# PART 6: QUERY PATTERNS

## Scenario 1: "Show me filter part 12345"

```sql
SELECT
    p.id,
    p.name,
    p.part_number,
    p.manufacturer,
    p.description,
    p.category,
    p.quantity_on_hand,
    p.minimum_quantity,
    p.unit,
    p.location,
    p.last_counted_at,
    -- Equipment compatibility
    (SELECT json_agg(json_build_object(
        'equipment_id', e.id,
        'equipment_name', e.name,
        'quantity_required', bom.quantity_required
    ))
    FROM pms_equipment_parts_bom bom
    JOIN pms_equipment e ON bom.equipment_id = e.id
    WHERE bom.part_id = p.id
    AND e.deleted_at IS NULL) AS compatible_equipment,
    -- Low stock warning
    CASE WHEN p.quantity_on_hand <= p.minimum_quantity THEN true ELSE false END AS is_low_stock
FROM pms_parts p
WHERE p.id = :part_id
  AND p.yacht_id = public.get_user_yacht_id();
```

---

## Scenario 2: "Parts for Generator #1"

```sql
SELECT
    p.id,
    p.name,
    p.part_number,
    p.manufacturer,
    p.quantity_on_hand,
    p.minimum_quantity,
    bom.quantity_required,
    CASE WHEN p.quantity_on_hand < bom.quantity_required THEN true ELSE false END AS needs_reorder
FROM pms_equipment_parts_bom bom
JOIN pms_parts p ON bom.part_id = p.id
WHERE bom.equipment_id = :equipment_id
  AND bom.yacht_id = public.get_user_yacht_id()
ORDER BY p.name;
```

---

## Scenario 3: "Low stock parts"

```sql
SELECT
    p.id,
    p.name,
    p.part_number,
    p.quantity_on_hand,
    p.minimum_quantity,
    p.unit,
    p.location,
    (p.minimum_quantity - p.quantity_on_hand) AS shortage,
    -- Check if already on shopping list
    EXISTS (
        SELECT 1 FROM pms_shopping_list_items sli
        WHERE sli.part_id = p.id
        AND sli.status NOT IN ('received', 'cancelled')
    ) AS on_shopping_list
FROM pms_parts p
WHERE p.quantity_on_hand <= p.minimum_quantity
  AND p.minimum_quantity > 0
  AND p.yacht_id = public.get_user_yacht_id()
ORDER BY shortage DESC;
```

---

## Scenario 4: "Parts used on work order WO-2026-0045"

```sql
SELECT
    p.id,
    p.name,
    p.part_number,
    pu.quantity_used,
    pu.notes,
    pu.created_at AS used_at,
    (SELECT name FROM auth_users_profiles WHERE id = pu.created_by) AS used_by
FROM pms_part_usage pu
JOIN pms_parts p ON pu.part_id = p.id
WHERE pu.work_order_id = :work_order_id
  AND pu.yacht_id = public.get_user_yacht_id()
ORDER BY pu.created_at DESC;
```

---

# PART 7: GAPS & MIGRATION STATUS

## Security Gap (Blocker)

| Gap | Table | Migration | Status |
|-----|-------|-----------|--------|
| RLS Disabled | pms_inventory_transactions | 20260125_005_fix_inventory_transactions_rls.sql | **REQUIRED** |

## Confirmed Present

| Feature | Table | Column/Index | Status |
|---------|-------|--------------|--------|
| Stock tracking | pms_parts | quantity_on_hand, minimum_quantity | ✅ |
| Unit tracking | pms_parts | unit (CHECK constraint) | ✅ |
| Location tracking | pms_parts, pms_inventory_stock | location | ✅ |
| Count audit | pms_parts | last_counted_at, last_counted_by | ✅ |
| Semantic search | pms_parts | search_embedding (vector) | ✅ |
| Low stock index | pms_parts | idx_pms_parts_low_stock | ✅ |
| BOM linking | pms_equipment_parts_bom | equipment_id, part_id | ✅ |
| RLS canonical | pms_parts, pms_inventory_stock | get_user_yacht_id() | ✅ |

---

# PART 8: SUMMARY

## Part Lens Actions (Final)

| Action | Tables Written | Signature | RLS Tier |
|--------|---------------|-----------|----------|
| `adjust_stock_quantity` | pms_parts, pms_inventory_transactions, pms_audit_log | Large adjustments | Engineers |
| `record_part_consumption` | pms_part_usage, pms_parts, pms_inventory_transactions, pms_audit_log | No | Engineers |
| `add_to_shopping_list` | pms_shopping_list_items, pms_audit_log | No | All Crew |
| `view_part_usage_history` | None (read) | No | All Crew |
| `view_compatible_equipment` | None (read) | No | All Crew |
| `add_part_note` | pms_notes, pms_audit_log | No | All Crew |

## Escape Hatches

| From Part | To Lens | Trigger |
|-----------|---------|---------|
| view_compatible_equipment | Equipment Lens | Focus on equipment from list |
| view_part_usage_history | Work Order Lens | Click WO number |
| add_to_shopping_list | Shopping List Lens | Navigate to shopping list |

## Key Invariants

1. **Parts always belong to yacht** via `yacht_id = get_user_yacht_id()`
2. **Stock changes create transaction records** in `pms_inventory_transactions`
3. **Low stock auto-detected** via `quantity_on_hand <= minimum_quantity`
4. **Consumption linked to work orders** via `pms_part_usage`
5. **Equipment compatibility via BOM** in `pms_equipment_parts_bom`
6. **Semantic search supported** via `search_embedding` vector column

---

**END OF PART LENS v1 FINAL**
