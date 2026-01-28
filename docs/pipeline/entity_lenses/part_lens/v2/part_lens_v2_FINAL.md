# Entity Lens: Part (Inventory & Stock Management)

**Version**: v2 FINAL
**Status**: READY FOR IMPLEMENTATION
**Date**: 2026-01-27
**Gold Standard Reference**: `certificate_lens_v2_FINAL.md`
**Operating Procedure**: `LENS_BUILDER_OPERATING_PROCEDURE.md`

---

# EXECUTIVE SUMMARY

The Part Lens governs all operations for inventory parts, stock management, consumption tracking, and procurement workflows on board a yacht.

## Key Metrics

| Metric | Value |
|--------|-------|
| Primary Tables | 5 (pms_parts, pms_inventory_stock, pms_inventory_transactions, pms_part_usage, pms_shopping_list_items) |
| Actions Registered | 8 mutations + READ handlers |
| Scenarios Documented | 10 |
| Average Step Reduction | 50% |
| Blockers | 4 (B1: transactions RLS, B2: part_usage RLS review, B3: signature schema, B4: shopping_list INSERT RLS) |
| Migrations Ready | 3 |

## Core User Value

- **Breakdown Response**: Find part + location in <30 seconds during emergency
- **Proactive Maintenance**: Pre-check parts availability before scheduled service
- **Inventory Accuracy**: Real-time stock with audit trail for every change
- **Procurement Flow**: Low stock → shopping list → order → receive → stock updated

---

# BLOCKERS

| ID | Description | Severity | Status | Resolution |
|----|-------------|----------|--------|------------|
| **B1** | `pms_inventory_transactions` has RLS DISABLED | CRITICAL | Migration Ready | Deploy 20260127_001_fix_inventory_transactions_rls.sql |
| **B2** | `pms_part_usage` RLS policies undocumented | HIGH | Needs Review | Extract and verify current policies |
| **B3** | Large adjustment signature payload schema undefined | MEDIUM | Design Ready | See APPENDIX: SIGNATURE PAYLOAD SCHEMA |
| **B4** | `pms_shopping_list_items` INSERT policy scope unclear | MEDIUM | Needs Review | Verify all crew can add items |

**Note**: All part mutation actions require B1 resolved. Service role bypasses RLS automatically.

---

# PART 0: CANONICAL HELPERS

## Yacht ID Resolution

```sql
public.get_user_yacht_id()
-- Returns UUID of current user's yacht
-- SECURITY DEFINER, STABLE
-- Source: auth_users_profiles WHERE id = auth.uid() AND is_active = true
```

## Role Check Helpers

```sql
-- For engineer-level operations:
public.get_user_role()
-- Returns TEXT: captain, chief_engineer, eto, deckhand, etc.

-- For HOD-level operations (recommended for write gates):
public.is_hod(auth.uid(), public.get_user_yacht_id())
-- Returns BOOLEAN: true if user is captain, chief_engineer, chief_officer, purser, or manager

-- For manager-only operations:
public.is_manager()
-- Returns BOOLEAN: true if user has manager role
```

**Best Practice**: Use `is_hod()` and `is_manager()` in RLS policies for clarity.

## Audit Entity Types

| Value | Table |
|-------|-------|
| `part` | pms_parts |
| `inventory_stock` | pms_inventory_stock |
| `inventory_transaction` | pms_inventory_transactions |
| `part_usage` | pms_part_usage |
| `shopping_list_item` | pms_shopping_list_items |

## Signature Invariant

```sql
-- Non-signature action:
pms_audit_log.signature = '{}'::jsonb

-- Signed action (large stock adjustment):
pms_audit_log.signature = :signature_payload::jsonb
```

**NEVER** NULL. See APPENDIX: SIGNATURE PAYLOAD SCHEMA for structure.

---

# PART 1: DATABASE SCHEMA (DB TRUTH)

## Table: `pms_parts` (19 columns)

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
| `unit` | text | YES | OPTIONAL | Unit of measure. Default: 'ea' |
| `location` | text | YES | OPTIONAL | Primary storage location |
| `last_counted_at` | timestamptz | YES | BACKEND_AUTO | Last physical count date |
| `last_counted_by` | uuid | YES | BACKEND_AUTO | Who performed last count |
| `search_embedding` | vector(1536) | YES | BACKEND_AUTO | For semantic search |
| `embedding_text` | text | YES | BACKEND_AUTO | Text used for embedding |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data. Default: '{}' |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | Trigger: update_updated_at |

**Row Count**: 538
**RLS Status**: ✅ ENABLED

### Unit Values (CHECK Constraint)

```sql
CHECK ((unit = ANY (ARRAY[
    'ea', 'kg', 'g', 'L', 'mL', 'm', 'cm', 'mm', 'ft', 'in',
    'm2', 'm3', 'gal', 'qt', 'pt', 'oz', 'lb',
    'box', 'set', 'pair', 'roll', 'sheet'
])) OR (unit IS NULL))
```

---

## Table: `pms_inventory_stock` (16 columns)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `part_id` | uuid | NOT NULL | CONTEXT | FK → pms_parts(id) |
| `location` | text | YES | OPTIONAL | Storage location name |
| `quantity` | integer | NOT NULL | REQUIRED | Stock at this location. Default: 0 |
| `min_quantity` | integer | YES | OPTIONAL | Location-specific minimum |
| `max_quantity` | integer | YES | OPTIONAL | Location-specific maximum |
| `reorder_quantity` | integer | YES | OPTIONAL | Suggested reorder amount |
| `last_counted_at` | timestamptz | YES | BACKEND_AUTO | Last count date |
| `metadata` | jsonb | YES | BACKEND_AUTO | Additional data |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | Default: NOW() |
| `updated_at` | timestamptz | NOT NULL | BACKEND_AUTO | Trigger |
| `updated_by` | uuid | YES | BACKEND_AUTO | Last modifier |
| `deleted_at` | timestamptz | YES | BACKEND_AUTO | Soft delete |
| `deleted_by` | uuid | YES | BACKEND_AUTO | Who deleted |
| `deletion_reason` | text | YES | OPTIONAL | Why deleted |

**Row Count**: 282
**RLS Status**: ✅ ENABLED
**Purpose**: Track stock at multiple locations per part (Engine Room: 5, Forward Store: 10)

---

## Table: `pms_inventory_transactions` (9 columns)

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
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | When change occurred |

**Row Count**: 0 (not yet used in production)
**RLS Status**: ❌ DISABLED - **BLOCKER B1**

### Transaction Types

| Type | Description | Quantity Change |
|------|-------------|-----------------|
| `received` | Stock added from receiving | + |
| `consumed` | Stock used for work order | - |
| `adjusted` | Manual count adjustment | +/- |
| `transferred_out` | Moved to another location | - |
| `transferred_in` | Received from another location | + |
| `returned` | Returned to supplier | - |

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

**Row Count**: TBD
**RLS Status**: ⚠️ NEEDS REVIEW - **BLOCKER B2**

**IMPORTANT - Column Name Corrections:**
- Use `quantity` (NOT `quantity_used`)
- Use `used_by` (NOT `created_by`)

---

## Table: `pms_shopping_list_items` (44 columns - key fields)

| Column | PostgreSQL Type | Nullable | Classification | Notes |
|--------|-----------------|----------|----------------|-------|
| `id` | uuid | NOT NULL | BACKEND_AUTO | PK |
| `yacht_id` | uuid | NOT NULL | BACKEND_AUTO | FK |
| `part_id` | uuid | YES | CONTEXT | FK → pms_parts(id), NULL for candidate parts |
| `part_name` | text | NOT NULL | REQUIRED | Part name (denormalized) |
| `part_number` | text | YES | OPTIONAL | Part number |
| `manufacturer` | text | YES | OPTIONAL | Manufacturer |
| `quantity_requested` | numeric | NOT NULL | REQUIRED | Quantity to order |
| `unit` | text | YES | OPTIONAL | Unit of measure |
| `urgency` | text | YES | OPTIONAL | Priority level |
| `status` | text | NOT NULL | BACKEND_AUTO | pending/approved/ordered/received/cancelled |
| `source_type` | text | NOT NULL | REQUIRED | manual/low_stock/work_order |
| `source_work_order_id` | uuid | YES | CONTEXT | If created from WO |
| `created_by` | uuid | NOT NULL | BACKEND_AUTO | Who created |
| `created_at` | timestamptz | NOT NULL | BACKEND_AUTO | When created |
| `is_candidate_part` | boolean | NOT NULL | BACKEND_AUTO | True if part doesn't exist in pms_parts |
| `approved_by` | uuid | YES | BACKEND_AUTO | Who approved |
| `approved_at` | timestamptz | YES | BACKEND_AUTO | When approved |

**Row Count**: TBD
**RLS Status**: ⚠️ NEEDS REVIEW - **BLOCKER B4**

---

## Table: `pms_equipment_parts_bom` (Related)

Links parts to equipment (Bill of Materials).

| Column | PostgreSQL Type | Purpose |
|--------|-----------------|---------|
| `id` | uuid | PK |
| `yacht_id` | uuid | FK |
| `equipment_id` | uuid | Which equipment |
| `part_id` | uuid | Which part |
| `quantity_required` | integer | How many needed |
| `notes` | text | Installation notes |

**Row Count**: 15

---

# PART 2: MICRO-ACTIONS WITH FIELD CLASSIFICATION

> **ACTION ACTIVATION DOCTRINE**: Actions are NOT visible on search results lists. When a part becomes the **focused entity**, its context actions become available.

## Action Summary

| # | Action | Tables Written | Signature | Status |
|---|--------|---------------|-----------|--------|
| 1 | `record_part_consumption` | part_usage, parts, inv_transactions, audit | NO | ⚠️ B1/B2 |
| 2 | `adjust_stock_quantity` | parts, inv_transactions, audit | CONDITIONAL | ⚠️ B1/B3 |
| 3 | `add_to_shopping_list` | shopping_list_items, audit | NO | ⚠️ B4 |
| 4 | `receive_parts` | parts, inv_stock, inv_transactions, receiving, audit | NO | ⚠️ B1 |
| 5 | `transfer_parts` | inv_stock (x2), inv_transactions (x2), audit | NO | ⚠️ B1 |
| 6 | `create_part` | parts, audit | NO | ✅ READY |
| 7 | `view_part_history` | None (read) | NO | ✅ READY |
| 8 | `view_compatible_equipment` | None (read) | NO | ✅ READY |

## Role Permissions Matrix

| Role | View | Consume | Add to List | Receive | Adjust (small) | Adjust (large) | Create | Delete |
|------|------|---------|-------------|---------|----------------|----------------|--------|--------|
| crew | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| deckhand | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| steward | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| bosun | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| eto | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| chief_engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (signed) | ✅ | ❌ |
| captain | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (signed) | ✅ | ✅ |
| manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (signed) | ✅ | ✅ |

---

## Action 1: `record_part_consumption`

**Purpose**: Record part usage for a work order or equipment maintenance

**Allowed Roles**: deckhand, bosun, eto, chief_engineer, captain, manager

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
| `quantity` | pms_part_usage.quantity | REQUIRED | User input |
| `usage_reason` | pms_part_usage.usage_reason | REQUIRED | User input or default |
| `notes` | pms_part_usage.notes | OPTIONAL | User input |
| `used_at` | pms_part_usage.used_at | BACKEND_AUTO | NOW() |
| `used_by` | pms_part_usage.used_by | BACKEND_AUTO | auth.uid() |

**Business Rules**:
- Cannot consume more than `quantity_on_hand`
- Work order must be in `planned` or `in_progress` status
- Updates both `pms_part_usage` AND `pms_parts.quantity_on_hand`

**Error Responses**:
| Condition | HTTP Status | Error Code |
|-----------|-------------|------------|
| quantity > quantity_on_hand | 400 | `insufficient_stock` |
| work_order not found | 404 | `work_order_not_found` |
| work_order.status not in [planned, in_progress] | 400 | `work_order_invalid_status` |
| part not found | 404 | `part_not_found` |

---

## Action 2: `adjust_stock_quantity`

**Purpose**: Manual stock count adjustment after physical inventory

**Allowed Roles**: eto, chief_engineer, captain, manager

**Signature Required**: YES if |new - old| > (old * 0.5) OR new = 0

**Tables Written**:
- `pms_parts` (UPDATE quantity_on_hand, last_counted_at, last_counted_by)
- `pms_inventory_transactions` (INSERT)
- `pms_audit_log` (INSERT with signature if large adjustment)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | - | CONTEXT | From focused part |
| `new_quantity` | pms_parts.quantity_on_hand | REQUIRED | User input |
| `reason` | pms_audit_log.metadata | REQUIRED | User input |
| `location` | pms_inventory_stock.location | OPTIONAL | If multi-location |
| `counted_at` | pms_parts.last_counted_at | BACKEND_AUTO | NOW() |
| `counted_by` | pms_parts.last_counted_by | BACKEND_AUTO | auth.uid() |
| `signature` | pms_audit_log.signature | CONDITIONAL | Required if large adjustment |

**Signature Threshold Logic**:
```python
old_qty = current_quantity_on_hand
new_qty = request.new_quantity
change_pct = abs(new_qty - old_qty) / max(old_qty, 1)

requires_signature = change_pct > 0.5 or new_qty == 0
```

---

## Action 3: `add_to_shopping_list`

**Purpose**: Add part to shopping/reorder list

**Allowed Roles**: deckhand, steward, bosun, eto, chief_engineer, captain, manager, purser

**Tables Written**:
- `pms_shopping_list_items` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | pms_shopping_list_items.part_id | CONTEXT | From focused part |
| `quantity_requested` | pms_shopping_list_items.quantity_requested | REQUIRED | User input |
| `urgency` | pms_shopping_list_items.urgency | OPTIONAL | User dropdown |
| `notes` | pms_shopping_list_items.source_notes | OPTIONAL | User input |
| `source_type` | pms_shopping_list_items.source_type | BACKEND_AUTO | 'manual' |
| `created_by` | pms_shopping_list_items.created_by | BACKEND_AUTO | auth.uid() |

---

## Action 4: `receive_parts`

**Purpose**: Process incoming parts delivery, update stock

**Allowed Roles**: deckhand, bosun, eto, chief_engineer, captain, manager

**Tables Written**:
- `pms_receiving_events` (INSERT or UPDATE)
- `pms_receiving_line_items` (INSERT)
- `pms_parts` (UPDATE quantity_on_hand)
- `pms_inventory_stock` (UPDATE or INSERT)
- `pms_inventory_transactions` (INSERT per item)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `items` | - | REQUIRED | Array of line items |
| `items[].part_id` | pms_receiving_line_items.part_id | CONTEXT | Matched or created part |
| `items[].quantity_received` | pms_receiving_line_items.quantity_received | REQUIRED | User input |
| `items[].storage_location` | pms_inventory_stock.location | OPTIONAL | User input |
| `purchase_order_id` | pms_receiving_events.order_id | OPTIONAL | If matched to PO |

---

## Action 5: `transfer_parts`

**Purpose**: Move stock between locations

**Allowed Roles**: bosun, eto, chief_engineer, captain, manager

**Tables Written**:
- `pms_inventory_stock` (UPDATE x2 - source and destination)
- `pms_inventory_transactions` (INSERT x2 - out and in)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `part_id` | - | CONTEXT | From focused part |
| `from_location` | pms_inventory_stock.location | REQUIRED | User select |
| `to_location` | pms_inventory_stock.location | REQUIRED | User input |
| `quantity` | - | REQUIRED | User input |

**Business Rules**:
- Cannot transfer more than available at source location
- Creates destination stock record if doesn't exist

---

## Action 6: `create_part`

**Purpose**: Add new part to inventory

**Allowed Roles**: eto, chief_engineer, captain, manager

**Tables Written**:
- `pms_parts` (INSERT)
- `pms_audit_log` (INSERT)

**Field Classification**:

| Field | Table.Column | Classification | Source |
|-------|--------------|----------------|--------|
| `name` | pms_parts.name | REQUIRED | User input |
| `part_number` | pms_parts.part_number | OPTIONAL | User input |
| `manufacturer` | pms_parts.manufacturer | OPTIONAL | User input |
| `category` | pms_parts.category | OPTIONAL | User dropdown |
| `initial_quantity` | pms_parts.quantity_on_hand | OPTIONAL | User input, default 0 |
| `minimum_quantity` | pms_parts.minimum_quantity | OPTIONAL | User input |
| `unit` | pms_parts.unit | OPTIONAL | User dropdown, default 'ea' |
| `location` | pms_parts.location | OPTIONAL | User input |

---

# PART 2B: ACTION ROUTER REGISTRATION

All part mutations are executed via the Action Router at `/v1/actions/execute`.

## Registered Actions

```python
# apps/api/action_router/registry.py

"record_part_consumption": ActionDefinition(
    action_id="record_part_consumption",
    label="Use Part for Work Order",
    endpoint="/v1/parts/consume",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
    required_fields=["part_id", "work_order_id", "quantity"],
    domain="parts",
    variant=ActionVariant.MUTATE,
    search_keywords=["use", "used", "consume", "for work order", "part usage"],
),

"adjust_stock_quantity": ActionDefinition(
    action_id="adjust_stock_quantity",
    label="Adjust Stock Count",
    endpoint="/v1/parts/adjust-stock",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["eto", "chief_engineer", "captain", "manager"],
    required_fields=["part_id", "new_quantity", "reason"],
    domain="parts",
    variant=ActionVariant.MUTATE,  # Changes to SIGNED dynamically
    search_keywords=["count", "adjust", "inventory", "physical count", "stock"],
),

"add_to_shopping_list": ActionDefinition(
    action_id="add_to_shopping_list",
    label="Add to Shopping List",
    endpoint="/v1/shopping-list/add",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "steward", "bosun", "eto", "chief_engineer", "captain", "manager", "purser"],
    required_fields=["part_id", "quantity_requested"],
    domain="parts",
    variant=ActionVariant.MUTATE,
    search_keywords=["order", "buy", "shopping", "reorder", "purchase"],
),

"receive_parts": ActionDefinition(
    action_id="receive_parts",
    label="Receive Parts Delivery",
    endpoint="/v1/receiving/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["deckhand", "bosun", "eto", "chief_engineer", "captain", "manager"],
    required_fields=["items"],
    domain="parts",
    variant=ActionVariant.MUTATE,
    search_keywords=["receive", "received", "delivery", "arrived", "dhl"],
),

"transfer_parts": ActionDefinition(
    action_id="transfer_parts",
    label="Transfer Between Locations",
    endpoint="/v1/parts/transfer",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["bosun", "eto", "chief_engineer", "captain", "manager"],
    required_fields=["part_id", "from_location", "to_location", "quantity"],
    domain="parts",
    variant=ActionVariant.MUTATE,
    search_keywords=["transfer", "move", "relocate"],
),

"create_part": ActionDefinition(
    action_id="create_part",
    label="Add New Part",
    endpoint="/v1/parts/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["eto", "chief_engineer", "captain", "manager"],
    required_fields=["name"],
    domain="parts",
    variant=ActionVariant.MUTATE,
    search_keywords=["new part", "add part", "create part"],
),

"view_part_history": ActionDefinition(
    action_id="view_part_history",
    label="View Usage History",
    endpoint="/v1/parts/{part_id}/history",
    handler_type=HandlerType.INTERNAL,
    method="GET",
    allowed_roles=["*"],  # All authenticated
    required_fields=["part_id"],
    domain="parts",
    variant=ActionVariant.READ,
    search_keywords=["history", "usage", "used when", "audit"],
),

"view_compatible_equipment": ActionDefinition(
    action_id="view_compatible_equipment",
    label="View Compatible Equipment",
    endpoint="/v1/parts/{part_id}/equipment",
    handler_type=HandlerType.INTERNAL,
    method="GET",
    allowed_roles=["*"],  # All authenticated
    required_fields=["part_id"],
    domain="parts",
    variant=ActionVariant.READ,
    search_keywords=["equipment", "compatible", "fits", "bom"],
),
```

## Request Contract

```json
{
  "action": "record_part_consumption",
  "context": {
    "yacht_id": "uuid",
    "part_id": "uuid"
  },
  "payload": {
    "work_order_id": "uuid",
    "quantity": 2,
    "usage_reason": "Scheduled maintenance",
    "notes": "Replaced during 500-hour service"
  }
}
```

## Role Mapping (Registry → RLS)

| Registry Role | RLS Implementation | DB Roles |
|---------------|-------------------|----------|
| Engineers | `get_user_role() IN (...)` | eto, chief_engineer |
| Deck Crew | `get_user_role() IN (...)` | deckhand, bosun |
| HOD | `is_hod()` | chief_engineer, captain, manager, purser |
| Manager | `is_manager()` | manager |

---

# PART 3: KEY SQL PATTERNS

## Record Part Consumption

```sql
BEGIN;

-- 1. Verify stock available
SELECT quantity_on_hand INTO :current_qty
FROM pms_parts
WHERE id = :part_id AND yacht_id = public.get_user_yacht_id();

IF :quantity > :current_qty THEN
    RAISE EXCEPTION 'Insufficient stock: requested %, available %', :quantity, :current_qty
    USING ERRCODE = 'P0001';
END IF;

-- 2. Verify work order is valid
SELECT status INTO :wo_status
FROM pms_work_orders
WHERE id = :work_order_id AND yacht_id = public.get_user_yacht_id();

IF :wo_status IS NULL THEN
    RAISE EXCEPTION 'Work order not found' USING ERRCODE = 'P0002';
END IF;

IF :wo_status NOT IN ('planned', 'in_progress') THEN
    RAISE EXCEPTION 'Work order must be planned or in_progress, got %', :wo_status
    USING ERRCODE = 'P0003';
END IF;

-- 3. Insert usage record
INSERT INTO pms_part_usage (
    id, yacht_id, part_id, work_order_id,
    quantity, usage_reason, notes, used_at, used_by, metadata
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :part_id,
    :work_order_id,
    :quantity,
    COALESCE(:usage_reason, 'Work order consumption'),
    :notes,
    NOW(),
    auth.uid(),
    jsonb_build_object('session_id', :session_id)
)
RETURNING id INTO :usage_id;

-- 4. Update part quantity
UPDATE pms_parts
SET
    quantity_on_hand = quantity_on_hand - :quantity,
    updated_at = NOW()
WHERE id = :part_id
  AND yacht_id = public.get_user_yacht_id();

-- 5. Transaction record
INSERT INTO pms_inventory_transactions (
    id, yacht_id, stock_id, transaction_type,
    quantity_change, quantity_before, quantity_after,
    user_id, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    NULL,  -- No specific stock location
    'consumed',
    -:quantity,
    :current_qty,
    :current_qty - :quantity,
    auth.uid(),
    NOW()
);

-- 6. Audit log
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
    jsonb_build_object('quantity_on_hand', :current_qty - :quantity, 'usage_id', :usage_id),
    '{}'::jsonb,
    jsonb_build_object('work_order_id', :work_order_id, 'quantity', :quantity),
    NOW()
);

COMMIT;
```

## Adjust Stock Quantity (with Signature Logic)

```sql
BEGIN;

-- 1. Get current quantity
SELECT quantity_on_hand INTO :old_quantity
FROM pms_parts
WHERE id = :part_id AND yacht_id = public.get_user_yacht_id();

-- 2. Calculate if signature required
:change_pct := ABS(:new_quantity - :old_quantity)::float / GREATEST(:old_quantity, 1);
:requires_signature := :change_pct > 0.5 OR :new_quantity = 0;

-- 3. Validate signature if required
IF :requires_signature AND (:signature IS NULL OR :signature = '{}'::jsonb) THEN
    RAISE EXCEPTION 'Large adjustment requires signature' USING ERRCODE = 'P0004';
END IF;

-- 4. Update part master
UPDATE pms_parts
SET
    quantity_on_hand = :new_quantity,
    last_counted_at = NOW(),
    last_counted_by = auth.uid(),
    updated_at = NOW()
WHERE id = :part_id
  AND yacht_id = public.get_user_yacht_id();

-- 5. Insert transaction record
INSERT INTO pms_inventory_transactions (
    id, yacht_id, stock_id, transaction_type,
    quantity_change, quantity_before, quantity_after,
    user_id, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    NULL,
    'adjusted',
    :new_quantity - :old_quantity,
    :old_quantity,
    :new_quantity,
    auth.uid(),
    NOW()
);

-- 6. Audit log with conditional signature
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
    CASE WHEN :requires_signature THEN :signature ELSE '{}'::jsonb END,
    jsonb_build_object('reason', :reason, 'change_pct', :change_pct),
    NOW()
);

COMMIT;
```

## Low Stock Query

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

## Part History Query (for Ledger View)

```sql
SELECT
    al.created_at,
    al.action,
    al.user_id,
    (SELECT name FROM auth_users_profiles WHERE id = al.user_id) AS actor_name,
    (SELECT role FROM auth_users_roles WHERE user_id = al.user_id AND is_active = true LIMIT 1) AS actor_role,
    al.old_values,
    al.new_values,
    CASE WHEN al.signature = '{}'::jsonb THEN false ELSE true END AS is_signed,
    al.metadata
FROM pms_audit_log al
WHERE al.entity_type = 'part'
  AND al.entity_id = :part_id
  AND al.yacht_id = public.get_user_yacht_id()
ORDER BY al.created_at DESC
LIMIT 50;
```

---

# PART 4: RLS POLICIES

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

**RLS**: ❌ DISABLED - **BLOCKER B1**

### PROPOSED (Migration Required)

```sql
-- Migration: 20260127_001_fix_inventory_transactions_rls.sql
ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

-- SELECT: All authenticated can view transactions
CREATE POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Engineers and deck crew can insert
CREATE POLICY "engineers_insert_transactions" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY[
            'chief_engineer'::text, 'eto'::text, 'deckhand'::text, 'bosun'::text,
            'captain'::text, 'manager'::text
        ])
    );

-- Service role bypass
CREATE POLICY "service_role_full_access_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);
```

---

## Table: `pms_part_usage`

### PROPOSED (Needs Verification)

```sql
-- SELECT: All authenticated
CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Deck crew and engineers
CREATE POLICY "crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND get_user_role() = ANY (ARRAY[
            'deckhand'::text, 'bosun'::text, 'eto'::text,
            'chief_engineer'::text, 'captain'::text, 'manager'::text
        ])
    );
```

---

# PART 5: SCENARIOS

## Scenario 1: Emergency Part Lookup During Breakdown

**Actor**: Chief Engineer
**Context**: Generator failure, guests on board, high stress
**Trigger**: "cat fuel filter" or "gen 2 filter"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Go to inventory system | Type "cat fuel filter" |
| 2 | Navigate to parts module | See result with stock + location |
| 3 | Search by part number | Tap to focus |
| 4 | Find part in list | See "Engine Room Store - Shelf B2" |
| 5 | Check stock level | See "3 units available" |
| 6 | Note location | [Use for WO] button visible |
| 7 | Walk to location | - |

**Steps**: 7 → 3 (**57% reduction**)

**Ledger Entry**:
```json
{
  "action": "view_part",
  "entity_type": "part",
  "payload_snapshot": {
    "search_query": "cat fuel filter",
    "result_count": 1,
    "time_to_find_ms": 1200
  }
}
```

---

## Scenario 2: Pre-Service Parts Check

**Actor**: ETO
**Context**: Planning 500-hour service for tomorrow
**Trigger**: "parts for ME1 service"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open maintenance schedule | Type "ME1 500 hour parts" |
| 2 | Find the task | See BOM with stock status |
| 3 | Open equipment record | Color-coded availability |
| 4 | Find linked parts | Single view shows all |
| 5 | Check each part's stock | - |
| 6 | Create shopping list for missing | [Order Missing Parts] button |
| 7 | Submit order request | One-tap action |

**Steps**: 7 → 3 (**57% reduction**)

---

## Scenario 3: Record Part Usage for Work Order

**Actor**: Deckhand
**Context**: Just replaced impeller, work order open
**Trigger**: "used impeller for WO-2026-0045"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open work order | Type "used impeller WO-0045" |
| 2 | Navigate to parts tab | System detects consumption intent |
| 3 | Search for part | Pre-fills part + WO |
| 4 | Select part | Confirm quantity (default: 1) |
| 5 | Enter quantity | Submit |
| 6 | Save | Stock auto-decremented |
| 7 | Verify stock updated | Ledger entry created |

**Steps**: 7 → 3 (**57% reduction**)

---

## Scenario 4: Receiving Parts Delivery

**Actor**: Bosun
**Context**: DHL delivery just arrived
**Trigger**: Camera scan or "receive parts"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Find PO in system | [📷 Scan Packing Slip] |
| 2 | Open PO | System OCRs and matches |
| 3 | Enter each line item | Shows matched items |
| 4 | Match to part records | Confirm matches |
| 5 | Update quantities | One-tap commit |
| 6 | Assign locations | Stock updated |
| 7 | Close receiving | Ledger entry per item |

**Steps**: 7 → 4 (**43% reduction**)

---

## Scenario 5: Monthly Inventory Audit

**Actor**: Purser
**Context**: End of month, walking through stores
**Trigger**: "inventory count engine room"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Print inventory list | Type "count engine room store" |
| 2 | Walk through store | See list filtered by location |
| 3 | Count each item | Tap item → enter actual count |
| 4 | Note discrepancies | System highlights differences |
| 5 | Return to computer | Adjustments applied in real-time |
| 6 | Enter adjustments | Reasons required for variances |
| 7 | Save and verify | Audit trail automatic |

**Steps**: 7 → 4 (**43% reduction**)

---

## Scenario 6: Low Stock Alert Response

**Actor**: Chief Engineer
**Context**: Received notification on phone
**Trigger**: Notification tap

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | See email/check system | Tap notification |
| 2 | Search for part | Goes directly to part |
| 3 | Verify stock level | Stock shown + minimum |
| 4 | Decide quantity to order | Suggested quantity shown |
| 5 | Navigate to shopping list | [Add to Shopping List] |
| 6 | Add item | Pre-filled from CTA payload |
| 7 | Set priority | One-tap submit |

**Steps**: 7 → 3 (**57% reduction**)

---

## Scenario 7: Find Where a Part Is Stored

**Actor**: Any crew
**Context**: Need to find a specific filter
**Trigger**: "where is impeller for watermaker"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open parts system | Type query |
| 2 | Search | See result with location |
| 3 | Find part | Location: "Forward Store - Rack 3" |
| 4 | Check location field | Stock: "2 units" |
| 5 | - | Multi-location breakdown if applicable |

**Steps**: 4 → 2 (**50% reduction**)

---

## Scenario 8: View Part Usage History

**Actor**: Captain
**Context**: Reviewing maintenance costs
**Trigger**: "show usage history for oil filter"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open reports module | Type "oil filter history" |
| 2 | Navigate to parts | Focus on part |
| 3 | Find usage report | [View History] action |
| 4 | Filter by part | See usage ledger |
| 5 | Export/review | Each use linked to WO |

**Steps**: 5 → 3 (**40% reduction**)

---

## Scenario 9: Create New Part (Not in System)

**Actor**: ETO
**Context**: Found a filter in stores not in database
**Trigger**: "add new part"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open parts module | Type "add new part" |
| 2 | Click "New Part" | [Create Part] action |
| 3 | Enter name | Fill name, part number, manufacturer |
| 4 | Enter part number | Enter initial stock + location |
| 5 | Enter manufacturer | Submit |
| 6 | Set category | Part created with audit trail |
| 7 | Enter initial stock | - |
| 8 | Save | - |

**Steps**: 8 → 4 (**50% reduction**)

---

## Scenario 10: Transfer Parts Between Locations

**Actor**: Bosun
**Context**: Moving spare impellers from forward store to engine room
**Trigger**: "transfer 2 impellers to engine room"

| Step | Traditional | Celeste |
|------|-------------|---------|
| 1 | Open inventory | Type "transfer impeller" |
| 2 | Find part | Detect transfer intent |
| 3 | Find source location stock | Select part |
| 4 | Reduce source quantity | Enter: from, to, qty |
| 5 | Find destination record | Submit |
| 6 | Increase destination quantity | Both locations updated |
| 7 | Verify both updated | Single transaction, single audit |

**Steps**: 7 → 4 (**43% reduction**)

---

## Scenarios Summary

| # | Scenario | Steps Saved |
|---|----------|-------------|
| 1 | Emergency Part Lookup | 57% |
| 2 | Pre-Service Parts Check | 57% |
| 3 | Record Part Usage | 57% |
| 4 | Receiving Parts Delivery | 43% |
| 5 | Monthly Inventory Audit | 43% |
| 6 | Low Stock Alert Response | 57% |
| 7 | Find Where Part Is Stored | 50% |
| 8 | View Part Usage History | 40% |
| 9 | Create New Part | 50% |
| 10 | Transfer Parts Between Locations | 43% |

**Average**: 50% step reduction

---

# PART 6: ESCAPE HATCHES

| From Part | To Lens | Trigger |
|-----------|---------|---------|
| view_compatible_equipment | Equipment Lens | Focus on equipment from list |
| view_part_history | Work Order Lens | Click WO number in history |
| record_part_consumption | Work Order Lens | Click WO to view details |
| add_to_shopping_list | Shopping List Lens | Navigate to shopping list |
| receive_parts | Receiving Lens | View full receiving event |

---

# PART 7: MIGRATIONS

## Required (P0)

1. `20260127_001_fix_inventory_transactions_rls.sql` - Enable RLS + policies
2. `20260127_002_verify_part_usage_rls.sql` - Verify/fix part_usage policies

## Recommended (P1)

3. `20260127_003_part_indexes.sql` - Performance indexes (low stock, category, manufacturer)

## Optional (P2)

4. `20260127_004_shopping_list_insert_rls.sql` - Verify all crew can add items

---

# PART 8: DEPLOYMENT CHECKLIST

## Pre-Deploy

- [ ] Backup database
- [ ] Verify `get_user_yacht_id()` deployed
- [ ] Verify `get_user_role()` deployed
- [ ] Test migrations on staging

## Deploy Order

1. [ ] 20260127_001 (transactions RLS)
2. [ ] 20260127_002 (part_usage RLS verification)
3. [ ] 20260127_003 (indexes - optional)

## Post-Deploy Verification

### 1. RLS Enabled Check

```sql
SELECT relname, relrowsecurity FROM pg_class
WHERE relname IN ('pms_parts', 'pms_inventory_stock', 'pms_inventory_transactions', 'pms_part_usage');
-- All should show TRUE
```

### 2. Part Policies Check

```sql
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('pms_parts', 'pms_inventory_stock', 'pms_inventory_transactions', 'pms_part_usage')
ORDER BY tablename, policyname;
-- Should show policies for each table
```

### 3. Yacht Isolation Test

```sql
-- As user from Yacht A, verify cannot see Yacht B's parts
SELECT COUNT(*) FROM pms_parts WHERE yacht_id = 'yacht-b-uuid';
-- Should return 0
```

## REST Acceptance Tests

### Engineer Can Record Consumption

```http
POST /v1/actions/execute
Authorization: Bearer <engineer_jwt>
Content-Type: application/json

{
  "action": "record_part_consumption",
  "context": {"yacht_id": "uuid", "part_id": "uuid"},
  "payload": {
    "work_order_id": "uuid",
    "quantity": 1
  }
}
-- Expect: 200 OK (Engineer)
-- Expect: 403 Forbidden (Crew)
```

### Deckhand Cannot Adjust Stock

```http
POST /v1/actions/execute
Authorization: Bearer <deckhand_jwt>
Content-Type: application/json

{
  "action": "adjust_stock_quantity",
  "context": {"yacht_id": "uuid", "part_id": "uuid"},
  "payload": {
    "new_quantity": 10,
    "reason": "Count correction"
  }
}
-- Expect: 403 Forbidden
```

### Large Adjustment Requires Signature

```http
POST /v1/actions/execute
Authorization: Bearer <chief_engineer_jwt>
Content-Type: application/json

{
  "action": "adjust_stock_quantity",
  "context": {"yacht_id": "uuid", "part_id": "uuid"},
  "payload": {
    "new_quantity": 0,
    "reason": "All units damaged"
  }
}
-- Expect: 400 Bad Request (missing signature)
```

---

# APPENDIX: SIGNATURE PAYLOAD SCHEMA

For large stock adjustments (>50% change or zero-out), a signature is required.

```json
{
  "user_id": "uuid",
  "role_at_signing": "chief_engineer",
  "signature_type": "stock_adjustment",
  "reason": "Physical count found damaged units",
  "old_quantity": 10,
  "new_quantity": 2,
  "change_percentage": 0.8,
  "signed_at": "2026-01-27T14:30:00Z",
  "signature_hash": "sha256:base64..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | uuid | YES | User performing the signed action |
| `role_at_signing` | text | YES | User's role at the moment of signing |
| `signature_type` | text | YES | `stock_adjustment` |
| `reason` | text | YES | Why the adjustment was made |
| `old_quantity` | integer | YES | Previous stock level |
| `new_quantity` | integer | YES | New stock level |
| `change_percentage` | float | YES | Calculated change percentage |
| `signed_at` | timestamptz | YES | Timestamp of signature |
| `signature_hash` | text | YES | Hash of the signed payload |

**Note**: For non-signed actions, `signature = '{}'::jsonb` (empty object, never NULL).

---

# APPENDIX: LEDGER NOTIFICATION PATTERNS

## When to Notify (Deterministic Triggers)

| Trigger | Notify Roles | Level | CTA Action |
|---------|--------------|-------|------------|
| `quantity_on_hand <= minimum_quantity` | chief_engineer, purser | warning | `add_to_shopping_list` |
| `quantity_on_hand = 0` | chief_engineer, captain | critical | `add_to_shopping_list` |
| Shopping list item pending >24h | purser | info | `approve_shopping_item` |
| Received parts not put away >4h | bosun | info | `assign_storage_location` |
| Large adjustment without proper signature | manager | warning | `review_adjustment` |

## Notification Payload Example

```json
{
  "user_id": "chief_engineer_uuid",
  "topic": "low_stock",
  "source": "part",
  "source_id": "part-uuid",
  "title": "Low Stock: CAT Fuel Filter 1R-0751",
  "body": "Only 1 unit remaining. Minimum is 2.",
  "level": "warning",
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "part-uuid",
    "quantity_requested": 3
  },
  "send_after": "2026-01-27T10:00:00Z"
}
```

## Idempotency Key

```sql
UNIQUE (user_id, source, source_id, topic, date_trunc('day', send_after))
```

This prevents duplicate notifications per day for the same part/topic.

---

# APPENDIX: ERROR MAPPING

| Condition | HTTP Status | Error Code | User Message |
|-----------|-------------|------------|--------------|
| Part not found | 404 | `part_not_found` | "Part not found" |
| Work order not found | 404 | `work_order_not_found` | "Work order not found" |
| Insufficient stock | 400 | `insufficient_stock` | "Not enough stock: requested X, available Y" |
| Work order wrong status | 400 | `work_order_invalid_status` | "Work order must be planned or in progress" |
| Large adjustment needs signature | 400 | `signature_required` | "Large adjustments require signature" |
| Invalid quantity (negative) | 400 | `invalid_quantity` | "Quantity cannot be negative" |
| Location not found | 404 | `location_not_found` | "Storage location not found" |
| Cross-yacht access | 403 | `forbidden` | "Access denied" |

**Rule**: Client errors are 400/404. Never 500 for expected validation failures.

---

# APPENDIX: CONTEXT-AWARE ACTION PRIORITY

## When User is Working on a Fault/Work Order

If the user has an active work order focused:

| Priority | Action | Shown? |
|----------|--------|--------|
| 1 | `record_part_consumption` | ✅ Prominent |
| 2 | `view_compatible_equipment` | ✅ Secondary |
| 3 | `check_stock` | ✅ Secondary |
| LOW | `add_to_shopping_list` | ⚪ Available but de-emphasized |
| HIDE | `adjust_stock_quantity` | ❌ Not relevant |

## When User is in Administrative Mode

| Priority | Action | Shown? |
|----------|--------|--------|
| 1 | `view_low_stock_report` | ✅ Prominent |
| 2 | `add_to_shopping_list` | ✅ Prominent |
| 3 | `adjust_stock_quantity` | ✅ Available |
| LOW | `record_part_consumption` | ⚪ Available but de-emphasized |

---

**END OF PART LENS v2 FINAL**
