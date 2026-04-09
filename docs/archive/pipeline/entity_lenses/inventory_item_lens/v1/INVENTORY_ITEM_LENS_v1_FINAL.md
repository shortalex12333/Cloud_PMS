# Entity Lens: Inventory Item (Parts & Stock Management)

**Version**: v1.2 GOLD
**Status**: READY FOR IMPLEMENTATION
**Date**: 2026-01-27
**Gold Standard Reference**: `certificate_lens_v2_FINAL.md`
**Operating Procedure**: `LENS_BUILDER_OPERATING_PROCEDURE.md`

---

# EXECUTIVE SUMMARY

The Inventory Item Lens governs all operations for inventory parts, stock management, consumption tracking, and procurement workflows on board a yacht.

## Key Metrics

| Metric | Value |
|--------|-------|
| Primary Tables | 5 (pms_parts, pms_part_locations, pms_inventory_transactions, pms_part_usage, pms_shopping_list_items) |
| Actions Registered | 9 mutations + READ handlers |
| Scenarios Documented | 10 |
| Average Step Reduction | 50% |
| Blockers | 0 (all resolved via migrations) |
| Migrations Ready | 8 |

## Core User Value

- **Breakdown Response**: Find part + location in <30 seconds during emergency
- **Proactive Maintenance**: Pre-check parts availability before scheduled service
- **Inventory Accuracy**: Real-time stock with audit trail for every change
- **Procurement Flow**: Low stock → shopping list → order → receive → stock updated

## Approved Design Decisions

| Decision | Resolution |
|----------|------------|
| Shopping list in v1? | **YES** - `add_to_shopping_list` included |
| Adjust direction | **Delta** with `quantity_change` (+/-) and CHECK constraint |
| Transactions append-only | **YES** - No DELETE; use `reverse_transaction` (SIGNED) |
| Deactivation policy | **YES** - `deactivate_part` replaces `delete_part`; denies mutations |
| Insufficient stock | **409 CONFLICT** - Hard block if would go negative; user must update stock first |
| Location normalization | **YES** - `pms_part_locations` with UUID FKs |
| RLS helpers | **CANONICAL** - Use `is_hod()` / `is_manager()` only; no role arrays |

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution

```sql
public.get_user_yacht_id()
-- Returns UUID of current user's yacht
-- SECURITY DEFINER, STABLE
-- Source: auth_users_profiles WHERE id = auth.uid() AND is_active = true
```

## Role Check Helpers (CANONICAL - EXPLICIT ARITY ONLY)

⚠️ **CRITICAL**: All helpers MUST use **explicit (user_id, yacht_id)** signatures to avoid PostgreSQL function ambiguity.

```sql
-- For operational crew (consume, receive, add_to_shopping_list):
public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user is deckhand, bosun, steward, eto, chief_engineer,
--                  chief_officer, captain, manager, or purser

-- For HOD-level operations (receive, transfer, adjust):
public.is_hod(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user is captain, chief_engineer, chief_officer, purser, or manager

-- For manager-only operations (write_off, reversed):
public.is_manager(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user has manager role

-- For signed operations (write_off, deactivate, large adjust):
-- Use is_hod() or is_manager() combined with signature requirement at handler level
```

**IMPORTANT**:
- Do NOT use `get_user_role() = ANY (ARRAY[...])` in RLS policies
- Do NOT use zero-arg helpers like `is_operational_crew()` - always pass explicit args
- All RLS policies MUST call helpers with `(auth.uid(), public.get_user_yacht_id())`

## Helper: is_operational_crew(user_id, yacht_id)

⚠️ **CRITICAL**: Use **explicit (user_id, yacht_id) signature** to avoid PostgreSQL function ambiguity.

For actions permitted to operational crew (consume, receive, add_to_shopping_list):

```sql
CREATE OR REPLACE FUNCTION public.is_operational_crew(
    p_user_id UUID,
    p_yacht_id UUID
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND is_active = true
          AND role IN ('deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
                       'chief_officer', 'captain', 'manager', 'purser')
    );
$$;
```

**RLS Policy Usage**: `public.is_operational_crew(auth.uid(), public.get_user_yacht_id())`

## Audit Entity Types

| Value | Table |
|-------|-------|
| `part` | pms_parts |
| `part_location` | pms_part_locations |
| `inventory_transaction` | pms_inventory_transactions |
| `part_usage` | pms_part_usage |
| `shopping_list_item` | pms_shopping_list_items |

## Signature Invariant

```sql
-- Non-signature action:
pms_audit_log.signature = '{}'::jsonb

-- Signed action (write_off, deactivate, reverse_transaction, large adjust):
pms_audit_log.signature = :signature_payload::jsonb
```

**NEVER** NULL. See APPENDIX: SIGNATURE PAYLOAD SCHEMA for structure.

---

# PART 1: DATABASE SCHEMA (DB TRUTH)

## Table: `pms_parts` (22 columns)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK, gen_random_uuid() |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id), from get_user_yacht_id() |
| `name` | text | NOT NULL | REQUIRED | Part name/description |
| `part_number` | text | YES | OPTIONAL | Manufacturer part number |
| `manufacturer` | text | YES | OPTIONAL | OEM name |
| `description` | text | YES | OPTIONAL | Long-form details |
| `category` | text | YES | OPTIONAL | Part category (filters, belts, etc.) |
| `model_compatibility` | jsonb | YES | OPTIONAL | Compatible equipment models. Default: '[]' |
| `quantity_on_hand` | integer | NOT NULL | BACKEND_AUTO | Current stock level. Default: 0 |
| `minimum_quantity` | integer | NOT NULL | OPTIONAL | Reorder threshold. Default: 0 |
| `desired_quantity` | integer | YES | OPTIONAL | Target stock level |
| `unit` | text | YES | OPTIONAL | Unit of measure. Default: 'ea' |
| `primary_location_id` | uuid | YES | OPTIONAL | FK → pms_part_locations(id) |
| `last_counted_at` | timestamptz | YES | BACKEND_AUTO | Last physical count date |
| `last_counted_by` | uuid | YES | BACKEND_AUTO | Who performed last count |
| `search_embedding` | vector(1536) | YES | BACKEND_AUTO | For semantic search |
| `embedding_text` | text | YES | BACKEND_AUTO | Text used for embedding |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data. Default: '{}' |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | Trigger: update_updated_at |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO | When deactivated |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who deactivated |
| `deletion_reason` | text | YES | OPTIONAL | Why deactivated |

**Row Count**: ~538
**RLS Status**: ENABLED

---

## Table: `pms_part_locations` (NEW - MIGRATION REQUIRED)

Normalized location storage for FK integrity and per-location stock tracking.

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yachts(id) |
| `name` | text | NOT NULL | REQUIRED | Location name (e.g., "Engine Room Store") |
| `path` | text | YES | OPTIONAL | Hierarchical path (e.g., "Deck > Forward > Store A") |
| `description` | text | YES | OPTIONAL | Location details |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `created_by` | uuid | YES | BACKEND_AUTO | Who created |

**Unique Constraint**: `(yacht_id, name)`
**RLS Status**: ENABLED

---

## Table: `pms_inventory_transactions` (Append-Only Ledger)

⚠️ **PRODUCTION REALITY**: Transactions reference **`stock_id`** (per-location stock record), NOT `part_id`.

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK → yacht_registry(id) |
| `stock_id` | uuid | NOT NULL | CONTEXT | **FK → pms_inventory_stock(id)** (TWO-TIER MODEL) |
| `part_id` | uuid | NOT NULL | CONTEXT | FK → pms_parts(id) (denormalized for querying) |
| `transaction_type` | text | NOT NULL | REQUIRED | Type of movement |
| `quantity_change` | integer | NOT NULL | REQUIRED | +/- delta (NEVER 0) |
| `quantity_before` | integer | NOT NULL | BACKEND_AUTO | Prior quantity |
| `quantity_after` | integer | NOT NULL | BACKEND_AUTO | New quantity |
| `from_location_id` | uuid | YES | CONTEXT | FK → pms_part_locations(id) for transfers |
| `to_location_id` | uuid | YES | CONTEXT | FK → pms_part_locations(id) for transfers/receives |
| `reference_type` | text | YES | CONTEXT | work_order/receiving/transfer/manual |
| `reference_id` | uuid | YES | CONTEXT | FK to source record |
| `transfer_group_id` | uuid | YES | BACKEND_AUTO | Groups paired transfer_out/transfer_in |
| `reverses_transaction_id` | uuid | YES | CONTEXT | FK for reversal entries |
| `idempotency_key` | text | YES | OPTIONAL | Client-provided, prevents duplicates |
| `usage_id` | uuid | YES | CONTEXT | FK → pms_part_usage(id) for dual-ledger correlation |
| `signature` | jsonb | YES | CONTEXT | Signature payload for write_off/reversed |
| `signed_by` | uuid | YES | CONTEXT | Who signed (manager/captain) |
| `user_id` | uuid | NOT NULL | BACKEND_AUTO | Who made change |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | When change occurred |

### Transaction Types

| Type | Description | Quantity Change | Signature |
|------|-------------|-----------------|-----------|
| `received` | Stock added from receiving | + | No |
| `consumed` | Stock used for work order | - | No |
| `adjusted` | Manual count adjustment | +/- | Conditional |
| `transferred_out` | Moved to another location | - | No |
| `transferred_in` | Received from another location | + | No |
| `write_off` | Damaged/lost parts | - | **YES** |
| `reversed` | Corrects previous transaction | +/- | **YES** |

### Constraints

```sql
CHECK (quantity_change != 0),
CHECK (transaction_type IN (
    'received', 'consumed', 'adjusted', 'transferred_out',
    'transferred_in', 'write_off', 'reversed'
)),
CHECK (quantity_after >= 0)  -- NO NEGATIVE INVENTORY
```

### Indexes

```sql
CREATE UNIQUE INDEX idx_inventory_transactions_idempotency
ON pms_inventory_transactions (yacht_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX idx_inventory_transactions_part_id
ON pms_inventory_transactions (part_id, created_at DESC);

CREATE INDEX idx_inventory_transactions_transfer_group
ON pms_inventory_transactions (transfer_group_id)
WHERE transfer_group_id IS NOT NULL;
```

**RLS Status**: ENABLED

---

## Table: `pms_part_usage` (11 columns)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `part_id` | uuid | NOT NULL | CONTEXT | FK → pms_parts(id) |
| `work_order_id` | uuid | YES | CONTEXT | FK → pms_work_orders(id) |
| `equipment_id` | uuid | YES | CONTEXT | FK → pms_equipment(id) |
| `quantity` | integer | NOT NULL | REQUIRED | Quantity used |
| `usage_reason` | text | NOT NULL | REQUIRED | Why part was used |
| `notes` | text | YES | OPTIONAL | Additional notes |
| `used_at` | timestamptz | NOT NULL | BACKEND_AUTO | When used |
| `used_by` | uuid | NOT NULL | BACKEND_AUTO | Who used it |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |

**RLS Status**: ENABLED

---

## Table: `pms_shopping_list_items` (Key fields - integer for quantities)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `part_id` | uuid | YES | CONTEXT | FK → pms_parts(id), NULL for candidates |
| `part_name` | text | NOT NULL | BACKEND_AUTO | Denormalized from part |
| `part_number` | text | YES | BACKEND_AUTO | Denormalized |
| `manufacturer` | text | YES | BACKEND_AUTO | Denormalized |
| `quantity_requested` | integer | NOT NULL | REQUIRED | Quantity to order |
| `unit` | text | YES | BACKEND_AUTO | Unit of measure |
| `urgency` | text | YES | OPTIONAL | normal/high/critical |
| `status` | text | NOT NULL | BACKEND_AUTO | pending/approved/ordered/received/cancelled |
| `source_type` | text | NOT NULL | BACKEND_AUTO | manual/low_stock/work_order |
| `source_work_order_id` | uuid | YES | CONTEXT | If created from WO |
| `source_notes` | text | YES | OPTIONAL | User notes |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | Who created |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | When created |
| `is_candidate_part` | boolean | NOT NULL | BACKEND_AUTO | True if part doesn't exist |

**Type Consistency**: All quantities are `integer`, not `numeric`.

**RLS Status**: ENABLED

---

## View: `pms_part_location_stock` (NEW - MIGRATION REQUIRED)

Per-location stock computed from transactions:

```sql
CREATE OR REPLACE VIEW pms_part_location_stock AS
SELECT
    t.yacht_id,
    t.part_id,
    COALESCE(t.to_location_id, t.from_location_id) AS location_id,
    l.name AS location_name,
    SUM(
        CASE
            WHEN t.transaction_type IN ('received', 'transferred_in', 'adjusted')
                 AND t.to_location_id IS NOT NULL THEN t.quantity_change
            WHEN t.transaction_type IN ('consumed', 'transferred_out', 'write_off')
                 AND t.from_location_id IS NOT NULL THEN t.quantity_change
            WHEN t.transaction_type = 'reversed' THEN t.quantity_change
            ELSE 0
        END
    ) AS quantity_at_location
FROM pms_inventory_transactions t
LEFT JOIN pms_part_locations l ON l.id = COALESCE(t.to_location_id, t.from_location_id)
WHERE t.yacht_id = public.get_user_yacht_id()
GROUP BY t.yacht_id, t.part_id, COALESCE(t.to_location_id, t.from_location_id), l.name
HAVING SUM(...) != 0;
```

---

# PART 2: MICRO-ACTIONS WITH FIELD METADATA

> **ACTION ACTIVATION DOCTRINE**: Actions are NOT visible on search results lists. When a part becomes the **focused entity**, its context actions become available.

## Action Summary

| # | Action | Tables Written | Signature | RLS Gate |
|---|--------|---------------|-----------|----------|
| 1 | `consume_part` | part_usage, parts, inv_transactions, audit | NO | is_operational_crew() |
| 2 | `adjust_stock_quantity` | parts, inv_transactions, audit | CONDITIONAL | is_hod() |
| 3 | `add_to_shopping_list` | shopping_list_items, audit | NO | is_operational_crew() |
| 4 | `receive_part` | parts, inv_transactions, audit | NO | is_operational_crew() |
| 5 | `transfer_part` | inv_transactions (x2), audit | NO | is_hod() |
| 6 | `write_off_part` | parts, inv_transactions, audit | **YES** | is_hod() |
| 7 | `deactivate_part` | parts, audit | **YES** | is_hod() |
| 8 | `reactivate_part` | parts, audit | **YES** | is_hod() |
| 9 | `reverse_transaction` | inv_transactions, parts, audit | **YES** | is_manager() |

## Role Permissions Matrix (Simplified via Helpers)

| Action | RLS Policy | Registry Roles | Signature |
|--------|------------|----------------|-----------|
| consume_part | is_operational_crew() | [operational crew] | No |
| adjust_stock_quantity (small) | is_hod() | [eto, chief_engineer, captain, manager] | No |
| adjust_stock_quantity (large) | is_hod() | [chief_engineer, captain, manager] | **Yes** |
| add_to_shopping_list | is_operational_crew() | [all crew] | No |
| receive_part | is_operational_crew() | [operational crew] | No |
| transfer_part | is_hod() | [bosun, eto, chief_engineer, captain, manager] | No |
| write_off_part | is_hod() | [chief_engineer, captain, manager] | **Yes** |
| deactivate_part | is_hod() | [chief_engineer, captain, manager] | **Yes** |
| reactivate_part | is_hod() | [chief_engineer, captain, manager] | **Yes** |
| reverse_transaction | is_manager() | [manager] | **Yes** |

---

## Action 1: `consume_part`

**Purpose**: Record part usage for a work order or equipment maintenance

**RLS Gate**: `is_operational_crew()`

**Tables Written**:
- `pms_part_usage` (INSERT)
- `pms_parts` (UPDATE quantity_on_hand)
- `pms_inventory_transactions` (INSERT)
- `pms_audit_log` (INSERT)

**Field Metadata**:

| Field | Classification | Auto-Populate From | Validation |
|-------|----------------|-------------------|------------|
| `part_id` | CONTEXT | lens_focus | FK exists, not deactivated |
| `work_order_id` | CONTEXT | navigation_context, query_extraction | FK exists, status in [planned, in_progress] |
| `equipment_id` | CONTEXT | query_extraction, part_equipment_link | FK exists if provided |
| `quantity` | REQUIRED | default: 1 | > 0, integer, **<= quantity_on_hand (409 if would go negative)** |
| `from_location_id` | CONTEXT | part.primary_location_id | FK exists if provided |
| `usage_reason` | REQUIRED | default='work_order' | Enum |
| `notes` | OPTIONAL | query_text | max 2000 chars |

**Insufficient Stock Policy**:
```python
if quantity > part.quantity_on_hand:
    raise HTTPException(
        status_code=409,
        detail={
            "error": "insufficient_stock",
            "message": f"Cannot consume {quantity}. Only {part.quantity_on_hand} available.",
            "current_stock": part.quantity_on_hand,
            "requested": quantity,
            "suggestion": "Update stock count if physical count differs, or add to shopping list."
        }
    )
```

If stock < minimum after consumption, trigger shopping list suggestion:
```json
{
  "warning": "low_stock_after_consumption",
  "message": "Stock will be below minimum (3). Add to shopping list?",
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "uuid",
    "quantity_requested": 5
  }
}
```

---

## Action 4: `receive_part`

**Idempotency**: Requires `idempotency_key` for duplicate prevention.

**Field Metadata**:

| Field | Classification | Auto-Populate From | Validation |
|-------|----------------|-------------------|------------|
| `part_id` | CONTEXT | lens_focus OR ocr_match | FK exists |
| `quantity_received` | REQUIRED | packing_slip_ocr | > 0, integer |
| `to_location_id` | REQUIRED | part.primary_location_id | FK exists |
| `purchase_order_id` | CONTEXT | po_match | FK exists if provided |
| `idempotency_key` | REQUIRED | client_generated | Unique per yacht within 24h |

**Idempotency Check**:
```sql
-- Before INSERT
SELECT EXISTS (
    SELECT 1 FROM pms_inventory_transactions
    WHERE yacht_id = $yacht_id
      AND idempotency_key = $idempotency_key
      AND created_at > NOW() - INTERVAL '24 hours'
);
-- If exists: return 409 duplicate_request
```

---

## Action 5: `transfer_part`

**Creates paired transactions**: One `transferred_out`, one `transferred_in`, linked by `transfer_group_id`.

**Field Metadata**:

| Field | Classification | Auto-Populate From | Validation |
|-------|----------------|-------------------|------------|
| `part_id` | CONTEXT | lens_focus | FK exists |
| `from_location_id` | REQUIRED | part.primary_location_id | FK exists, != to_location_id |
| `to_location_id` | REQUIRED | - | FK exists, != from_location_id |
| `quantity` | REQUIRED | - | > 0, <= available at from_location |

**SQL Pattern**:
```sql
BEGIN;

-- Generate transfer group ID
:transfer_group_id := gen_random_uuid();

-- 1. Insert transferred_out
INSERT INTO pms_inventory_transactions (
    id, yacht_id, part_id, transaction_type, quantity_change,
    quantity_before, quantity_after, from_location_id,
    transfer_group_id, user_id, created_at
) VALUES (
    gen_random_uuid(), $yacht_id, $part_id, 'transferred_out', -$quantity,
    $current_qty, $current_qty - $quantity, $from_location_id,
    :transfer_group_id, auth.uid(), NOW()
);

-- 2. Insert transferred_in
INSERT INTO pms_inventory_transactions (
    id, yacht_id, part_id, transaction_type, quantity_change,
    quantity_before, quantity_after, to_location_id,
    transfer_group_id, user_id, created_at
) VALUES (
    gen_random_uuid(), $yacht_id, $part_id, 'transferred_in', +$quantity,
    $current_qty - $quantity, $current_qty, $to_location_id,
    :transfer_group_id, auth.uid(), NOW()
);

-- Note: part.quantity_on_hand unchanged (internal transfer)

COMMIT;
```

---

# PART 3: RLS MATRIX (CANONICAL HELPERS ONLY)

## Table: `pms_parts`

```sql
-- 1. SELECT: All authenticated users can view parts
CREATE POLICY "crew_select_parts" ON pms_parts
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT/UPDATE: HOD only
CREATE POLICY "hod_manage_parts" ON pms_parts
    FOR ALL TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- 3. Service role bypass
CREATE POLICY "service_role_parts" ON pms_parts
    FOR ALL TO service_role
    USING (true);
```

## Table: `pms_part_locations`

```sql
-- SELECT: All authenticated
CREATE POLICY "crew_select_locations" ON pms_part_locations
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT/UPDATE: HOD only
CREATE POLICY "hod_manage_locations" ON pms_part_locations
    FOR ALL TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_locations" ON pms_part_locations
    FOR ALL TO service_role
    USING (true);
```

## Table: `pms_inventory_transactions`

```sql
ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

-- SELECT: All authenticated
CREATE POLICY "crew_select_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Operational crew (via canonical helper)
CREATE POLICY "operational_crew_insert_transactions" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

-- NO UPDATE POLICY - Append-only
-- NO DELETE POLICY - Append-only

-- Service role bypass
CREATE POLICY "service_role_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);
```

## Table: `pms_part_usage`

```sql
-- SELECT: All authenticated
CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Operational crew
CREATE POLICY "operational_crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

-- Service role bypass
CREATE POLICY "service_role_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true);
```

## Table: `pms_shopping_list_items`

```sql
-- SELECT: All crew see own + HOD sees all
CREATE POLICY "crew_select_shopping" ON pms_shopping_list_items
    FOR SELECT TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (
            created_by = auth.uid()
            OR public.is_hod(auth.uid(), public.get_user_yacht_id())
        )
    );

-- INSERT: All operational crew
CREATE POLICY "operational_crew_insert_shopping" ON pms_shopping_list_items
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

-- UPDATE: HOD only (for approval workflow)
CREATE POLICY "hod_update_shopping" ON pms_shopping_list_items
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );
```

---

# PART 4: STORAGE RLS POLICIES

## Bucket: `documents` (Part Attachments)

```sql
-- Storage policy for part documents
CREATE POLICY "yacht_part_documents_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
    );

CREATE POLICY "yacht_part_documents_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_operational_crew()
    );

CREATE POLICY "yacht_part_documents_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );
```

## Bucket: `pms-label-pdfs` (Part Labels)

```sql
-- Storage policy for generated labels
CREATE POLICY "yacht_labels_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    );

CREATE POLICY "yacht_labels_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND public.is_operational_crew()
    );
```

---

# PART 5: ACCEPTANCE MATRIX

## Roles x Actions (via Canonical Helpers)

| Action | crew | operational_crew | is_hod() | is_manager() |
|--------|------|------------------|----------|--------------|
| consume_part | 403 | 200 | 200 | 200 |
| adjust_stock_quantity (small) | 403 | 403 | 200 | 200 |
| adjust_stock_quantity (large) | 403 | 403 | 200+sig | 200+sig |
| add_to_shopping_list | 403 | 200 | 200 | 200 |
| receive_part | 403 | 200 | 200 | 200 |
| transfer_part | 403 | 403 | 200 | 200 |
| write_off_part | 403 | 403 | 200+sig | 200+sig |
| deactivate_part | 403 | 403 | 200+sig | 200+sig |
| reactivate_part | 403 | 403 | 200+sig | 200+sig |
| reverse_transaction | 403 | 403 | 403 | 200+sig |

## Edge Cases

| Condition | Expected HTTP | Error Code |
|-----------|---------------|------------|
| Part not found | 404 | part_not_found |
| Part deactivated + mutation | 409 | part_deactivated |
| Cross-yacht part access | 404 | (RLS blocks) |
| **Insufficient stock (would go negative)** | **409** | **insufficient_stock** |
| Work order wrong status | 400 | work_order_invalid_status |
| Large adjustment without signature | 400 | signature_required |
| Duplicate idempotency_key | 409 | duplicate_request |
| Transaction already reversed | 409 | already_reversed |
| Transfer from=to location | 400 | invalid_transfer |
| Quantity <= 0 | 400 | invalid_quantity |
| Location not found | 404 | location_not_found |

---

# PART 6: MIGRATIONS

## Migration 001: Enable RLS on Transactions + Add Columns

```sql
-- 20260127_001_inventory_transactions_rls_and_columns.sql

ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

-- Add new columns
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS from_location_id UUID REFERENCES pms_part_locations(id),
ADD COLUMN IF NOT EXISTS to_location_id UUID REFERENCES pms_part_locations(id),
ADD COLUMN IF NOT EXISTS transfer_group_id UUID,
ADD COLUMN IF NOT EXISTS reverses_transaction_id UUID REFERENCES pms_inventory_transactions(id),
ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- Constraints
ALTER TABLE pms_inventory_transactions
ADD CONSTRAINT check_quantity_change CHECK (quantity_change != 0),
ADD CONSTRAINT check_quantity_after_non_negative CHECK (quantity_after >= 0),
ADD CONSTRAINT check_transaction_type CHECK (
    transaction_type IN (
        'received', 'consumed', 'adjusted', 'transferred_out',
        'transferred_in', 'write_off', 'reversed'
    )
);

-- Idempotency index
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_transactions_idempotency
ON pms_inventory_transactions (yacht_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

-- Transfer group index
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_transfer_group
ON pms_inventory_transactions (transfer_group_id)
WHERE transfer_group_id IS NOT NULL;
```

## Migration 002: Create Part Locations Table

```sql
-- 20260127_002_create_part_locations.sql

CREATE TABLE IF NOT EXISTS pms_part_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id),
    name TEXT NOT NULL,
    path TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    UNIQUE (yacht_id, name)
);

ALTER TABLE pms_part_locations ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY "crew_select_locations" ON pms_part_locations
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "hod_manage_locations" ON pms_part_locations
    FOR ALL TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid(), public.get_user_yacht_id()))
    WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.is_hod(auth.uid(), public.get_user_yacht_id()));

CREATE POLICY "service_role_locations" ON pms_part_locations
    FOR ALL TO service_role
    USING (true);
```

## Migration 003: Add Soft Delete to Parts

```sql
-- 20260127_003_add_soft_delete_to_parts.sql

ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID,
ADD COLUMN IF NOT EXISTS deletion_reason TEXT,
ADD COLUMN IF NOT EXISTS primary_location_id UUID REFERENCES pms_part_locations(id),
ADD COLUMN IF NOT EXISTS desired_quantity INTEGER;

-- Index for active parts
CREATE INDEX IF NOT EXISTS idx_pms_parts_active
ON pms_parts(yacht_id) WHERE deleted_at IS NULL;
```

## Migration 004: Create is_operational_crew Helper

```sql
-- 20260127_004_create_is_operational_crew.sql

CREATE OR REPLACE FUNCTION public.is_operational_crew()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth_users_roles
        WHERE user_id = auth.uid()
          AND yacht_id = public.get_user_yacht_id()
          AND is_active = true
          AND role IN ('deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
                       'chief_officer', 'captain', 'manager', 'purser')
    );
$$;
```

## Migration 005: RLS Policies for Transactions

```sql
-- 20260127_005_transactions_rls_policies.sql

CREATE POLICY "crew_select_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "operational_crew_insert_transactions" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

CREATE POLICY "service_role_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);
```

## Migration 006: RLS Policies for Part Usage

```sql
-- 20260127_006_part_usage_rls_policies.sql

CREATE POLICY IF NOT EXISTS "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY IF NOT EXISTS "operational_crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

CREATE POLICY IF NOT EXISTS "service_role_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true);
```

## Migration 007: RLS Policies for Shopping List

```sql
-- 20260127_007_shopping_list_rls_policies.sql

CREATE POLICY IF NOT EXISTS "crew_select_shopping" ON pms_shopping_list_items
    FOR SELECT TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (created_by = auth.uid() OR public.is_hod(auth.uid(), public.get_user_yacht_id()))
    );

CREATE POLICY IF NOT EXISTS "operational_crew_insert_shopping" ON pms_shopping_list_items
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
    );

CREATE POLICY IF NOT EXISTS "hod_update_shopping" ON pms_shopping_list_items
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );
```

## Migration 008: Storage Policies

```sql
-- 20260127_008_storage_policies.sql

-- Part documents
CREATE POLICY "yacht_part_documents_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
    );

CREATE POLICY "yacht_part_documents_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_operational_crew()
    );

-- Labels
CREATE POLICY "yacht_labels_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    );

CREATE POLICY "yacht_labels_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND public.is_operational_crew()
    );
```

---

# PART 7: POST-DEPLOY VERIFICATION

## 1. RLS Enabled Check

```sql
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN (
    'pms_parts',
    'pms_part_locations',
    'pms_inventory_transactions',
    'pms_part_usage',
    'pms_shopping_list_items'
);
-- ALL should show relrowsecurity = TRUE
```

## 2. Policy Names Check

```sql
SELECT tablename, policyname, cmd FROM pg_policies
WHERE tablename IN (
    'pms_parts',
    'pms_part_locations',
    'pms_inventory_transactions',
    'pms_part_usage',
    'pms_shopping_list_items'
)
ORDER BY tablename, policyname;
```

**Expected policies per table**:
- pms_parts: crew_select_parts, hod_manage_parts, service_role_parts
- pms_part_locations: crew_select_locations, hod_manage_locations, service_role_locations
- pms_inventory_transactions: crew_select_transactions, operational_crew_insert_transactions, service_role_transactions
- pms_part_usage: crew_select_part_usage, operational_crew_insert_part_usage, service_role_part_usage
- pms_shopping_list_items: crew_select_shopping, operational_crew_insert_shopping, hod_update_shopping

## 3. Storage Policies Check

```sql
SELECT policyname, cmd FROM pg_policies
WHERE tablename = 'objects' AND schemaname = 'storage'
AND policyname LIKE 'yacht_%';
```

**Expected**:
- yacht_part_documents_select
- yacht_part_documents_insert
- yacht_labels_select
- yacht_labels_insert

## 4. Yacht Isolation Test

```sql
-- As user from Yacht A, verify cannot see Yacht B's parts
SET LOCAL "request.jwt.claims" = '{"sub": "user-yacht-a-uuid"}';
SELECT COUNT(*) FROM pms_parts WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0
```

## 5. Helper Functions Exist

```sql
SELECT proname FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_hod', 'is_manager', 'is_operational_crew')
AND pronamespace = 'public'::regnamespace;
-- Should return all 4
```

---

# APPENDIX: SIGNATURE PAYLOAD SCHEMA

```json
{
  "user_id": "uuid",
  "role_at_signing": "chief_engineer",
  "signature_type": "stock_write_off|deactivation|reversal|stock_adjustment",
  "reason": "Description of why this action is being taken",
  "old_quantity": 10,
  "new_quantity": 2,
  "signed_at": "2026-01-27T14:30:00Z",
  "signature_hash": "sha256:base64..."
}
```

**For non-signed actions**: `signature = '{}'::jsonb`

---

# APPENDIX: ERROR MAPPING

| Condition | HTTP | Error Code | User Message |
|-----------|------|------------|--------------|
| Part not found | 404 | part_not_found | Part not found |
| Part deactivated | 409 | part_deactivated | Part was deactivated. Reactivate to continue. |
| **Insufficient stock** | **409** | **insufficient_stock** | Cannot consume X. Only Y available. Update stock count first. |
| Work order not found | 404 | work_order_not_found | Work order not found |
| Work order wrong status | 400 | work_order_invalid_status | Work order must be planned or in progress |
| Signature required | 400 | signature_required | This action requires signature |
| Invalid quantity | 400 | invalid_quantity | Quantity must be greater than 0 |
| Transfer same location | 400 | invalid_transfer | From and to locations must be different |
| Location not found | 404 | location_not_found | Location not found |
| Already reversed | 409 | already_reversed | Transaction already reversed |
| Duplicate request | 409 | duplicate_request | Duplicate idempotency key |
| Cross-yacht access | 403 | forbidden | Access denied |

**Rule**: Client errors are 400/404/409. Never 500 for expected validation failures.

---

# PART 8: STRESS TESTS & SAFETY INVARIANTS

## 8.1 Atomic Non-Negative Stock (Race Condition Prevention)

⚠️ **PRODUCTION REALITY**: Use **two-tier model** with `stock_id` (per-location), NOT `part_id`.

**Problem**: Two concurrent `consume_part` calls could both read `quantity = 5` and both try to consume 5, resulting in -5 stock.

**Solution**: `SELECT FOR UPDATE` with stock check inside transaction on **pms_inventory_stock** (not pms_parts).

```sql
CREATE OR REPLACE FUNCTION public.deduct_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (
    success BOOLEAN,
    quantity_before INTEGER,
    quantity_after INTEGER,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_qty INTEGER;
    v_new_qty INTEGER;
    v_deleted_at TIMESTAMPTZ;
BEGIN
    -- Lock the stock row and get current state
    SELECT quantity, deleted_at
    INTO v_current_qty, v_deleted_at
    FROM pms_inventory_stock
    WHERE id = p_stock_id
      AND yacht_id = p_yacht_id
    FOR UPDATE;  -- Row-level lock prevents concurrent reads

    -- Check stock record exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'stock_not_found'::TEXT;
        RETURN;
    END IF;

    -- Check not deactivated
    IF v_deleted_at IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Check sufficient stock
    IF v_current_qty < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'insufficient_stock'::TEXT;
        RETURN;
    END IF;

    -- Deduct
    v_new_qty := v_current_qty - p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    RETURN QUERY SELECT TRUE, v_current_qty, v_new_qty, NULL::TEXT;
END;
$$;
```

**Usage in handler**:
```python
result = supabase.rpc("deduct_stock_inventory", {
    "p_stock_id": stock_id,  # NOT part_id!
    "p_quantity": quantity
}).execute()

if not result.data[0]["success"]:
    raise HTTPException(status_code=409, detail={"error": result.data[0]["error_code"]})
```

**Test Case**:
```python
@pytest.mark.asyncio
async def test_concurrent_consume_rejects_second():
    """Two concurrent consumes of 5 units from 5 stock: one succeeds, one fails."""
    part = await create_test_part(quantity_on_hand=5)

    # Launch two concurrent requests
    results = await asyncio.gather(
        consume_part(part.id, quantity=5, user=deckhand_a),
        consume_part(part.id, quantity=5, user=deckhand_b),
        return_exceptions=True
    )

    # Exactly one should succeed, one should get 409
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 409
    assert failures[0].detail["error"] == "insufficient_stock"

    # Verify final stock is 0, not -5
    part = await get_part(part.id)
    assert part.quantity_on_hand == 0
```

---

## 8.2 Transaction-Type RLS Gating

**Problem**: Crew should only be able to INSERT `consumed` and `received` transactions, not `write_off` or `reversed`.

**Solution**: Granular RLS with transaction_type checks.

```sql
-- Drop the generic policy
DROP POLICY IF EXISTS "operational_crew_insert_transactions" ON pms_inventory_transactions;

-- Crew can INSERT consumed/received only
CREATE POLICY "crew_insert_consume_receive" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew()
        AND transaction_type IN ('consumed', 'received', 'adjusted')
    );

-- HOD can INSERT transfers, adjustments
CREATE POLICY "hod_insert_transfers" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
        AND transaction_type IN ('transferred_out', 'transferred_in', 'write_off')
    );

-- Manager only can INSERT reversals
CREATE POLICY "manager_insert_reversals" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_manager()
        AND transaction_type = 'reversed'
    );
```

**Test Case**:
```python
@pytest.mark.asyncio
async def test_crew_cannot_insert_write_off():
    """Deckhand cannot directly insert write_off transaction."""
    part = await create_test_part(quantity_on_hand=10)

    # Attempt direct insert as deckhand (bypassing action handler)
    with pytest.raises(PostgresError) as exc:
        await supabase.table("pms_inventory_transactions").insert({
            "yacht_id": yacht_id,
            "part_id": part.id,
            "transaction_type": "write_off",  # Not allowed for crew
            "quantity_change": -5,
            "quantity_before": 10,
            "quantity_after": 5,
            "user_id": deckhand.id
        }, user=deckhand).execute()

    assert "RLS" in str(exc.value) or "denied" in str(exc.value).lower()
```

---

## 8.3 Reverse Uniqueness Constraint

**Problem**: Same transaction could be reversed multiple times if no unique constraint.

**Solution**: Partial unique index on `reverses_transaction_id`.

```sql
-- Each transaction can only be reversed once
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_transactions_reverses_unique
ON pms_inventory_transactions (reverses_transaction_id)
WHERE reverses_transaction_id IS NOT NULL;
```

**Test Case**:
```python
@pytest.mark.asyncio
async def test_double_reversal_blocked():
    """Second reversal of same transaction returns 409."""
    part = await create_test_part(quantity_on_hand=10)

    # Create and reverse a transaction
    txn = await consume_part(part.id, quantity=5, user=deckhand)
    await reverse_transaction(txn.id, reason="Error", user=manager)

    # Second reversal should fail
    with pytest.raises(HTTPException) as exc:
        await reverse_transaction(txn.id, reason="Another error", user=manager)

    assert exc.value.status_code == 409
    assert exc.value.detail["error"] == "already_reversed"
```

---

## 8.4 Soft-Delete Enforcement Trigger

**Problem**: After `deactivate_part`, mutations could still occur if handlers don't check.

**Solution**: DB-level trigger as final safety net.

```sql
CREATE OR REPLACE FUNCTION public.block_deactivated_part_mutations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Check if the part being referenced is deactivated
    IF TG_TABLE_NAME = 'pms_parts' THEN
        -- Allow UPDATE if it's the reactivation (deleted_at becoming NULL)
        IF TG_OP = 'UPDATE' AND OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
            RETURN NEW;
        END IF;

        -- Block other mutations on deactivated parts
        IF OLD.deleted_at IS NOT NULL THEN
            RAISE EXCEPTION 'Part is deactivated. Reactivate to modify.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    IF TG_TABLE_NAME = 'pms_inventory_transactions' THEN
        PERFORM 1 FROM pms_parts
        WHERE id = NEW.part_id AND deleted_at IS NOT NULL;

        IF FOUND THEN
            RAISE EXCEPTION 'Cannot create transaction for deactivated part.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    IF TG_TABLE_NAME = 'pms_part_usage' THEN
        PERFORM 1 FROM pms_parts
        WHERE id = NEW.part_id AND deleted_at IS NOT NULL;

        IF FOUND THEN
            RAISE EXCEPTION 'Cannot log usage for deactivated part.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- Apply to parts table (block updates on deactivated)
CREATE TRIGGER trg_block_deactivated_parts_update
BEFORE UPDATE ON pms_parts
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_part_mutations();

-- Apply to transactions table (block inserts for deactivated parts)
CREATE TRIGGER trg_block_deactivated_parts_transactions
BEFORE INSERT ON pms_inventory_transactions
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_part_mutations();

-- Apply to usage table (block inserts for deactivated parts)
CREATE TRIGGER trg_block_deactivated_parts_usage
BEFORE INSERT ON pms_part_usage
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_part_mutations();
```

**Test Case**:
```python
@pytest.mark.asyncio
async def test_db_trigger_blocks_deactivated_part_usage():
    """DB trigger blocks usage log even if handler check is bypassed."""
    part = await create_test_part(quantity_on_hand=10)
    await deactivate_part(part.id, reason="Obsolete", user=captain, signature=sig)

    # Direct insert bypassing handler
    with pytest.raises(PostgresError) as exc:
        await supabase.table("pms_part_usage").insert({
            "yacht_id": yacht_id,
            "part_id": part.id,
            "quantity": 1,
            "usage_reason": "test"
        }, user=service_role).execute()

    assert "deactivated" in str(exc.value).lower()
```

---

## 8.5 Location Normalization Backfill Plan

**Step 1: Extract unique locations from existing parts**
```sql
-- Run this as data migration
INSERT INTO pms_part_locations (yacht_id, name, created_at)
SELECT DISTINCT yacht_id, location, NOW()
FROM pms_parts
WHERE location IS NOT NULL
  AND location != ''
ON CONFLICT (yacht_id, name) DO NOTHING;
```

**Step 2: Populate primary_location_id**
```sql
-- Backfill FK from TEXT location
UPDATE pms_parts p
SET primary_location_id = l.id
FROM pms_part_locations l
WHERE p.location = l.name
  AND p.yacht_id = l.yacht_id
  AND p.primary_location_id IS NULL;
```

**Step 3: Verification**
```sql
-- Check for orphaned locations (parts with TEXT but no FK)
SELECT COUNT(*) AS orphaned
FROM pms_parts
WHERE location IS NOT NULL
  AND location != ''
  AND primary_location_id IS NULL;
-- Should be 0

-- Check location coverage
SELECT
    (SELECT COUNT(DISTINCT location) FROM pms_parts WHERE location IS NOT NULL) AS unique_text_locations,
    (SELECT COUNT(*) FROM pms_part_locations) AS normalized_locations;
-- Should match
```

**Step 4: Drop legacy column (after verification)**
```sql
-- Only run after all apps updated to use primary_location_id
ALTER TABLE pms_parts DROP COLUMN IF EXISTS location;
```

---

## 8.6 Dual-Ledger Consistency Check

**Problem**: `pms_parts.quantity_on_hand` must match sum of `pms_inventory_transactions.quantity_change`.

**Correlation Key**: When `consume_part` is called, it writes to BOTH:
1. `pms_part_usage` (who used what, for what reason)
2. `pms_inventory_transactions` (quantity change + before/after)

The transaction record includes `usage_id` FK pointing to the usage record for 1:1 join integrity.

```sql
-- In pms_inventory_transactions
usage_id UUID REFERENCES pms_part_usage(id) ON DELETE SET NULL
```

**1:1 Integrity Test**:
```sql
-- Find transactions without matching usage (should be 0 for 'consumed' type)
SELECT COUNT(*) FROM pms_inventory_transactions
WHERE transaction_type = 'consumed' AND usage_id IS NULL;
```

**Verification Query**:
```sql
SELECT
    p.id AS part_id,
    p.name,
    p.quantity_on_hand AS ledger_qty,
    COALESCE(SUM(t.quantity_change), 0) AS transaction_sum,
    p.quantity_on_hand - COALESCE(SUM(t.quantity_change), 0) AS drift
FROM pms_parts p
LEFT JOIN pms_inventory_transactions t ON t.part_id = p.id
WHERE p.yacht_id = $yacht_id
  AND p.deleted_at IS NULL
GROUP BY p.id
HAVING p.quantity_on_hand != COALESCE(SUM(t.quantity_change), 0);
```

**Expected**: 0 rows. Any drift indicates data integrity issue.

**Scheduled Check**:
```sql
-- Add to daily cron
CREATE OR REPLACE FUNCTION public.check_inventory_drift()
RETURNS TABLE (part_id UUID, name TEXT, ledger_qty INTEGER, transaction_sum BIGINT, drift BIGINT)
LANGUAGE sql
AS $$
    SELECT
        p.id,
        p.name,
        p.quantity_on_hand,
        COALESCE(SUM(t.quantity_change), 0),
        p.quantity_on_hand - COALESCE(SUM(t.quantity_change), 0)
    FROM pms_parts p
    LEFT JOIN pms_inventory_transactions t ON t.part_id = p.id
    WHERE p.deleted_at IS NULL
    GROUP BY p.id
    HAVING p.quantity_on_hand != COALESCE(SUM(t.quantity_change), 0);
$$;
```

---

## 8.7 Storage RLS Negative Tests

```python
@pytest.mark.asyncio
async def test_storage_cross_yacht_blocked():
    """User from Yacht A cannot read Yacht B's part documents."""
    # Upload doc as Yacht B user
    await upload_part_document(
        path=f"{yacht_b_id}/parts/{part_b_id}/spec.pdf",
        user=yacht_b_deckhand
    )

    # Try to read as Yacht A user
    with pytest.raises(StorageError) as exc:
        await download_file(
            path=f"{yacht_b_id}/parts/{part_b_id}/spec.pdf",
            user=yacht_a_deckhand
        )

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_storage_wrong_path_blocked():
    """Upload to path outside yacht prefix blocked."""
    with pytest.raises(StorageError) as exc:
        await upload_part_document(
            path=f"other-yacht-id/parts/{part_id}/evil.pdf",
            user=deckhand
        )

    assert exc.value.status_code == 403
```

---

## 8.8 Helper Function Parity Tests

```python
@pytest.mark.asyncio
async def test_is_operational_crew_includes_all_roles():
    """Verify is_operational_crew() returns true for all expected roles."""
    expected_roles = [
        'deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
        'chief_officer', 'captain', 'manager', 'purser'
    ]

    for role in expected_roles:
        user = await create_test_user(role=role)
        result = await supabase.rpc("is_operational_crew", user=user).execute()
        assert result.data is True, f"Role {role} should be operational crew"

@pytest.mark.asyncio
async def test_is_operational_crew_excludes_guest():
    """Guest role is not operational crew."""
    guest = await create_test_user(role='guest')
    result = await supabase.rpc("is_operational_crew", user=guest).execute()
    assert result.data is False
```

---

## 8.9 Type Consistency Tests

```python
@pytest.mark.asyncio
async def test_quantities_are_integers():
    """Ensure all quantity fields reject non-integer values."""
    part = await create_test_part(quantity_on_hand=10)

    # Attempt fractional consumption
    with pytest.raises(ValidationError):
        await consume_part(part.id, quantity=2.5, user=deckhand)

    # Attempt fractional shopping list request
    with pytest.raises(ValidationError):
        await add_to_shopping_list(part.id, quantity_requested=1.5, user=deckhand)
```

---

# PART 9: DOCKER ACCEPTANCE TEST MATRIX

## Test Environment Setup

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  db:
    image: supabase/postgres:15.1.0.117
    environment:
      POSTGRES_PASSWORD: postgres
    ports:
      - "54322:5432"
    volumes:
      - ./supabase/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  test-runner:
    build: ./tests
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://postgres:postgres@db:5432/postgres
      TEST_YACHT_A_ID: "00000000-0000-0000-0000-000000000001"
      TEST_YACHT_B_ID: "00000000-0000-0000-0000-000000000002"
```

## Acceptance Test Categories

| Category | Test Count | Critical |
|----------|------------|----------|
| RLS Isolation | 8 | YES |
| Concurrency | 4 | YES |
| Idempotency | 3 | YES |
| Signature Invariants | 5 | YES |
| Soft Delete | 4 | YES |
| Storage Access | 6 | YES |
| Edge Cases | 12 | NO |
| Happy Paths | 15 | NO |

## Critical Test Cases (Must Pass)

```python
# tests/test_inventory_lens_critical.py

class TestRLSIsolation:
    """All tests MUST pass - yacht data isolation."""

    async def test_parts_isolated_by_yacht(self): ...
    async def test_transactions_isolated_by_yacht(self): ...
    async def test_locations_isolated_by_yacht(self): ...
    async def test_shopping_list_isolated_by_yacht(self): ...
    async def test_cross_yacht_consume_blocked(self): ...
    async def test_cross_yacht_transfer_blocked(self): ...
    async def test_storage_cross_yacht_read_blocked(self): ...
    async def test_storage_cross_yacht_write_blocked(self): ...

class TestConcurrency:
    """Race condition prevention."""

    async def test_concurrent_consume_atomic(self): ...
    async def test_concurrent_receive_atomic(self): ...
    async def test_concurrent_transfer_atomic(self): ...
    async def test_concurrent_adjust_atomic(self): ...

class TestIdempotency:
    """Duplicate request handling."""

    async def test_duplicate_receive_returns_409(self): ...
    async def test_idempotency_key_scoped_to_yacht(self): ...
    async def test_idempotency_key_expires_after_24h(self): ...

class TestSignatureInvariants:
    """Audit log signature field never null."""

    async def test_unsigned_action_has_empty_signature(self): ...
    async def test_signed_action_has_signature_payload(self): ...
    async def test_write_off_requires_signature(self): ...
    async def test_reversal_requires_signature(self): ...
    async def test_large_adjustment_requires_signature(self): ...

class TestSoftDelete:
    """Deactivation blocks mutations."""

    async def test_consume_blocked_on_deactivated(self): ...
    async def test_receive_blocked_on_deactivated(self): ...
    async def test_reactivate_restores_mutations(self): ...
    async def test_trigger_blocks_direct_insert(self): ...

class TestStorageAccess:
    """Storage bucket RLS enforcement."""

    async def test_upload_to_own_yacht_allowed(self): ...
    async def test_upload_to_other_yacht_blocked(self): ...
    async def test_read_own_yacht_document_allowed(self): ...
    async def test_read_other_yacht_document_blocked(self): ...
    async def test_delete_requires_hod(self): ...
    async def test_path_traversal_blocked(self): ...
```

## Running Tests

```bash
# Full test suite
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Specific category
docker compose -f docker-compose.test.yml run test-runner \
    pytest tests/test_inventory_lens_critical.py::TestRLSIsolation -v

# With coverage
docker compose -f docker-compose.test.yml run test-runner \
    pytest --cov=app --cov-report=html tests/
```

---

**END OF INVENTORY ITEM LENS v1.2 GOLD**

---

# APPENDIX A: COPY-PASTEABLE MIGRATION SQL

## Production Schema Reality Check

⚠️ **CRITICAL**: Production database uses **two-tier inventory model**:
- `pms_parts` = Part catalog (master data)
- `pms_inventory_stock` = Per-location stock records (has `quantity`, `deleted_at`)
- `pms_inventory_transactions` = Transaction log (references **stock_id**, NOT part_id)
- Yacht table is `yacht_registry` (NOT `yachts`)

All handlers MUST use `stock_id` and call `deduct_stock_inventory()` / `add_stock_inventory()` atomically.

---

## Migration 1: is_operational_crew (Explicit Signature)

```sql
-- Migration: 202601271300_inventory_create_is_operational_crew.sql
-- Purpose: Create is_operational_crew helper with explicit (user_id, yacht_id) signature
-- Lens: Inventory Item Lens v1.2 GOLD

-- Drop zero-arg version if exists to prevent ambiguity
DROP FUNCTION IF EXISTS public.is_operational_crew();

-- Create explicit two-arg version
CREATE OR REPLACE FUNCTION public.is_operational_crew(
    p_user_id UUID,
    p_yacht_id UUID
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND is_active = true
          AND role IN (
              'deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
              'chief_officer', 'captain', 'manager', 'purser'
          )
    );
$$;

GRANT EXECUTE ON FUNCTION public.is_operational_crew(UUID, UUID) TO authenticated;
```

---

## Migration 2: pms_part_locations (Normalized Locations)

```sql
-- Migration: 202601271301_inventory_create_part_locations.sql
-- Purpose: Create normalized pms_part_locations table
-- Lens: Inventory Item Lens v1.2 GOLD

CREATE TABLE IF NOT EXISTS pms_part_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    path TEXT,  -- Hierarchical path: "Deck > Forward > Store A"
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,

    -- Unique location names per yacht
    CONSTRAINT uq_part_locations_yacht_name UNIQUE (yacht_id, name)
);

-- Enable RLS
ALTER TABLE pms_part_locations ENABLE ROW LEVEL SECURITY;

-- RLS POLICIES
CREATE POLICY "crew_select_locations" ON pms_part_locations
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "hod_manage_locations" ON pms_part_locations
    FOR ALL TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

CREATE POLICY "service_role_locations" ON pms_part_locations
    FOR ALL TO service_role
    USING (true);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_part_locations_yacht
ON pms_part_locations (yacht_id);
```

---

## Migration 3: Soft Delete Columns

```sql
-- Migration: 202601271302_inventory_add_soft_delete_cols.sql
-- Purpose: Add soft delete columns and primary_location_id FK to pms_parts
-- Lens: Inventory Item Lens v1.2 GOLD

-- Soft delete columns
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID,
ADD COLUMN IF NOT EXISTS deletion_reason TEXT;

-- Desired quantity (target stock level)
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS desired_quantity INTEGER;

-- FK to normalized locations
ALTER TABLE pms_parts
ADD COLUMN IF NOT EXISTS primary_location_id UUID;

-- Add FK constraint if not exists (RESTRICT prevents orphaning)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'pms_parts'
          AND constraint_type = 'FOREIGN KEY'
          AND constraint_name = 'pms_parts_primary_location_id_fkey'
    ) THEN
        ALTER TABLE pms_parts
        ADD CONSTRAINT pms_parts_primary_location_id_fkey
        FOREIGN KEY (primary_location_id)
        REFERENCES pms_part_locations(id)
        ON DELETE RESTRICT;
    END IF;
END
$$;

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_pms_parts_active
ON pms_parts (yacht_id)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pms_parts_primary_location
ON pms_parts (primary_location_id)
WHERE primary_location_id IS NOT NULL;
```

---

## Migration 4: Transaction Columns

```sql
-- Migration: 202601271303_inventory_transactions_columns.sql
-- Purpose: Add transaction tracking columns
-- Lens: Inventory Item Lens v1.2 GOLD

ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS idempotency_key TEXT,
ADD COLUMN IF NOT EXISTS signature JSONB,
ADD COLUMN IF NOT EXISTS signed_by UUID,
ADD COLUMN IF NOT EXISTS usage_id UUID,
ADD COLUMN IF NOT EXISTS reverses_transaction_id UUID;
```

---

## Migration 5: Transaction Constraints

```sql
-- Migration: 202601271304_inventory_transactions_constraints.sql
-- Purpose: Add constraints for idempotency and reversal tracking
-- Lens: Inventory Item Lens v1.2 GOLD

-- Idempotency constraint (scoped to yacht)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_inventory_transactions_idempotency'
    ) THEN
        CREATE UNIQUE INDEX idx_inventory_transactions_idempotency
        ON pms_inventory_transactions (yacht_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL;
    END IF;
END
$$;

-- Reversal reference FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'pms_inventory_transactions'
          AND constraint_name = 'pms_inventory_transactions_reverses_fkey'
    ) THEN
        ALTER TABLE pms_inventory_transactions
        ADD CONSTRAINT pms_inventory_transactions_reverses_fkey
        FOREIGN KEY (reverses_transaction_id)
        REFERENCES pms_inventory_transactions(id);
    END IF;
END
$$;

-- Usage correlation FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'pms_inventory_transactions'
          AND constraint_name = 'pms_inventory_transactions_usage_fkey'
    ) THEN
        ALTER TABLE pms_inventory_transactions
        ADD CONSTRAINT pms_inventory_transactions_usage_fkey
        FOREIGN KEY (usage_id)
        REFERENCES pms_part_usage(id);
    END IF;
END
$$;
```

---

## Migration 6: RLS Policies (Transaction-Type Gating)

```sql
-- Migration: 202601271305_inventory_rls_policies.sql
-- Purpose: Granular RLS policies with transaction-type gating
-- Lens: Inventory Item Lens v1.2 GOLD

-- TABLE: pms_inventory_transactions

-- SELECT: All authenticated crew can view transactions
CREATE POLICY "crew_select_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Operational crew can insert 'consumed' only
CREATE POLICY "crew_insert_consume" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type = 'consumed'
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- INSERT: HOD can insert received/transfer/adjust
CREATE POLICY "hod_insert_receive_transfer_adjust" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type IN ('received', 'transferred_out', 'transferred_in', 'adjusted')
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- INSERT: Manager/Captain can insert write_off/reversed (SIGNED)
CREATE POLICY "manager_insert_writeoff_reversed" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type IN ('write_off', 'reversed')
        AND public.is_manager(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);

-- NO UPDATE POLICY - Append-only ledger
-- NO DELETE POLICY - Append-only ledger

-- TABLE: pms_part_usage

CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "operational_crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

CREATE POLICY "service_role_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true);

-- NO UPDATE POLICY - Append-only ledger
-- NO DELETE POLICY - Append-only ledger

-- TABLE: pms_shopping_list_items

CREATE POLICY "crew_select_shopping" ON pms_shopping_list_items
    FOR SELECT TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (
            created_by = auth.uid()
            OR public.is_hod(auth.uid(), public.get_user_yacht_id())
        )
    );

CREATE POLICY "operational_crew_insert_shopping" ON pms_shopping_list_items
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

CREATE POLICY "hod_update_shopping" ON pms_shopping_list_items
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

CREATE POLICY "service_role_shopping" ON pms_shopping_list_items
    FOR ALL TO service_role
    USING (true);

-- NO DELETE POLICY - Use soft delete via UPDATE
```

---

## Migration 7: Storage Policies

```sql
-- Migration: 202601271306_inventory_storage_policies.sql
-- Purpose: Storage RLS policies for part documents and labels
-- Lens: Inventory Item Lens v1.2 GOLD

-- BUCKET: documents (Part Attachments)

CREATE POLICY "yacht_part_documents_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
    );

CREATE POLICY "yacht_part_documents_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

CREATE POLICY "yacht_part_documents_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'documents'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND (storage.foldername(name))[2] = 'parts'
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- BUCKET: pms-label-pdfs (Part Labels)

CREATE POLICY "yacht_labels_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    );

CREATE POLICY "yacht_labels_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'pms-label-pdfs'
        AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );
```

---

## Migration 8: Triggers & Functions (Atomic Stock Operations)

```sql
-- Migration: 202601271307_inventory_triggers_functions.sql
-- Purpose: Atomic stock deduction and soft-delete enforcement
-- Lens: Inventory Item Lens v1.2 GOLD

-- FUNCTION: deduct_stock_inventory (TWO-TIER MODEL)
CREATE OR REPLACE FUNCTION public.deduct_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (
    success BOOLEAN,
    quantity_before INTEGER,
    quantity_after INTEGER,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_qty INTEGER;
    v_new_qty INTEGER;
    v_deleted_at TIMESTAMPTZ;
BEGIN
    -- Lock the stock row and get current state
    SELECT quantity, deleted_at
    INTO v_current_qty, v_deleted_at
    FROM pms_inventory_stock
    WHERE id = p_stock_id
      AND yacht_id = p_yacht_id
    FOR UPDATE;  -- Row-level lock prevents concurrent reads

    -- Check stock record exists
    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'stock_not_found'::TEXT;
        RETURN;
    END IF;

    -- Check not deactivated
    IF v_deleted_at IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Check sufficient stock
    IF v_current_qty < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'insufficient_stock'::TEXT;
        RETURN;
    END IF;

    -- Deduct
    v_new_qty := v_current_qty - p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    RETURN QUERY SELECT TRUE, v_current_qty, v_new_qty, NULL::TEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION public.deduct_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- FUNCTION: add_stock_inventory
CREATE OR REPLACE FUNCTION public.add_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (
    success BOOLEAN,
    quantity_before INTEGER,
    quantity_after INTEGER,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_qty INTEGER;
    v_new_qty INTEGER;
    v_deleted_at TIMESTAMPTZ;
BEGIN
    -- Lock the stock row
    SELECT quantity, deleted_at
    INTO v_current_qty, v_deleted_at
    FROM pms_inventory_stock
    WHERE id = p_stock_id
      AND yacht_id = p_yacht_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'stock_not_found'::TEXT;
        RETURN;
    END IF;

    IF v_deleted_at IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Add quantity
    v_new_qty := v_current_qty + p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    RETURN QUERY SELECT TRUE, v_current_qty, v_new_qty, NULL::TEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION public.add_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- TRIGGER FUNCTION: block_deactivated_stock_mutations
CREATE OR REPLACE FUNCTION public.block_deactivated_stock_mutations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Block updates on deactivated stock (except reactivation)
    IF TG_TABLE_NAME = 'pms_inventory_stock' THEN
        IF TG_OP = 'UPDATE' THEN
            IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
                RETURN NEW;  -- Allow reactivation
            END IF;
            IF OLD.deleted_at IS NOT NULL THEN
                RAISE EXCEPTION 'Stock record is deactivated. Reactivate to modify.'
                    USING ERRCODE = '45000';
            END IF;
        END IF;
    END IF;

    -- Block transaction inserts for deactivated stock
    IF TG_TABLE_NAME = 'pms_inventory_transactions' THEN
        PERFORM 1 FROM pms_inventory_stock
        WHERE id = NEW.stock_id AND deleted_at IS NOT NULL;

        IF FOUND THEN
            RAISE EXCEPTION 'Cannot create transaction for deactivated stock.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    -- Block part_usage inserts when no active stock
    IF TG_TABLE_NAME = 'pms_part_usage' THEN
        IF NOT EXISTS (
            SELECT 1 FROM pms_inventory_stock
            WHERE part_id = NEW.part_id
              AND yacht_id = NEW.yacht_id
              AND deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'Cannot log usage - no active stock records for this part.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- Apply triggers
DROP TRIGGER IF EXISTS trg_block_deactivated_stock_update ON pms_inventory_stock;
CREATE TRIGGER trg_block_deactivated_stock_update
BEFORE UPDATE ON pms_inventory_stock
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

DROP TRIGGER IF EXISTS trg_block_deactivated_stock_transactions ON pms_inventory_transactions;
CREATE TRIGGER trg_block_deactivated_stock_transactions
BEFORE INSERT ON pms_inventory_transactions
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

DROP TRIGGER IF EXISTS trg_block_deactivated_stock_usage ON pms_part_usage;
CREATE TRIGGER trg_block_deactivated_stock_usage
BEFORE INSERT ON pms_part_usage
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

-- TRIGGER FUNCTION: block_reversal_of_reversal
CREATE OR REPLACE FUNCTION public.block_reversal_of_reversal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_original_type TEXT;
BEGIN
    IF NEW.transaction_type = 'reversed' AND NEW.reverses_transaction_id IS NOT NULL THEN
        SELECT transaction_type INTO v_original_type
        FROM pms_inventory_transactions
        WHERE id = NEW.reverses_transaction_id;

        IF v_original_type = 'reversed' THEN
            RAISE EXCEPTION 'Cannot reverse a reversal transaction.'
                USING ERRCODE = '45001';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_block_reversal_of_reversal ON pms_inventory_transactions;
CREATE TRIGGER trg_block_reversal_of_reversal
BEFORE INSERT ON pms_inventory_transactions
FOR EACH ROW
WHEN (NEW.transaction_type = 'reversed')
EXECUTE FUNCTION public.block_reversal_of_reversal();

-- FUNCTION: check_inventory_drift (Two-Tier Model)
CREATE OR REPLACE FUNCTION public.check_inventory_drift()
RETURNS TABLE (
    stock_id UUID,
    part_name TEXT,
    location TEXT,
    ledger_qty INTEGER,
    transaction_sum BIGINT,
    drift BIGINT
)
LANGUAGE sql
AS $$
    SELECT
        s.id,
        p.name,
        s.location,
        s.quantity,
        COALESCE(SUM(t.quantity_change), 0),
        s.quantity - COALESCE(SUM(t.quantity_change), 0)
    FROM pms_inventory_stock s
    JOIN pms_parts p ON p.id = s.part_id
    LEFT JOIN pms_inventory_transactions t ON t.stock_id = s.id
    WHERE s.deleted_at IS NULL
    GROUP BY s.id, p.name, s.location, s.quantity
    HAVING s.quantity != COALESCE(SUM(t.quantity_change), 0);
$$;

GRANT EXECUTE ON FUNCTION public.check_inventory_drift() TO authenticated;
```

---

## Migration 9: Backfill Locations

```sql
-- Migration: 202601271308_inventory_backfill_locations.sql
-- Purpose: Extract unique locations and link parts
-- Lens: Inventory Item Lens v1.2 GOLD

-- Extract unique location names from pms_parts.location (TEXT field)
INSERT INTO pms_part_locations (yacht_id, name, created_at)
SELECT DISTINCT yacht_id, location, NOW()
FROM pms_parts
WHERE location IS NOT NULL AND location != ''
ON CONFLICT (yacht_id, name) DO NOTHING;

-- Link parts to normalized locations
UPDATE pms_parts p
SET primary_location_id = l.id
FROM pms_part_locations l
WHERE p.location = l.name
  AND p.yacht_id = l.yacht_id
  AND p.primary_location_id IS NULL;
```

---

## Deployment Checklist

- [ ] Apply migrations 1-9 in order to staging tenant
- [ ] Run post-migration verification (see `/docs/evidence/inventory_item/00_VERIFICATION_SUMMARY.md`)
- [ ] Verify RLS enabled on all tables
- [ ] Verify helper functions have explicit (user_id, yacht_id) signatures
- [ ] Verify transaction-type RLS policies in place
- [ ] Run `check_inventory_drift()` - should return 0 rows
- [ ] Update all handlers to use `stock_id` and `deduct_stock_inventory()`/`add_stock_inventory()`
- [ ] Run Docker acceptance tests (21 critical tests)
- [ ] Run negative control tests (403/409/400 explicit codes)
- [ ] Sign off for production deployment

---

**END OF APPENDIX A - COPY-PASTEABLE MIGRATION SQL**
