# Entity Lens: Inventory Item

**Status**: Draft v2 - Production DB Verified
**Last Updated**: 2026-01-23
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)

---

## A) Base Entity Lens Definition

### Entity Type
**Inventory Item** (Part, Spare Part, Consumable)

**Canonical Table**: `pms_parts`

**When This Lens Activates**:
- User opens Part Detail in the same SPA. URL updates to encode state (e.g., `/parts/<uuid>` or `/?focus=part:<uuid>`) for deep-linking, refresh, and sharing. **No page reload. No second site.**
- User clicks part from search results
- User views part in "Related Parts" section
- User selects part from equipment parts list

**Celeste is one app** (apps.celeste7.ai). URL changes = browser state encoding for deep-linking, NOT navigation to another page.

**Core Purpose**: View and manage physical inventory items tracked in yacht stores.

---

## B) Schema Verification (Production DB Truth)

### Primary Table: `pms_parts`

**Source**: Production database query (2026-01-23)

**⚠️ WARNING**: Migration files DO NOT match production. Use this as source of truth.

**Columns**:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → `yachts(id)`, RLS isolation key |
| `name` | TEXT | NOT NULL | Display name |
| `part_number` | TEXT | NULL | OEM/internal part number |
| `manufacturer` | TEXT | NULL | **NOT IN MIGRATION** |
| `description` | TEXT | NULL | Long-form description |
| `category` | TEXT | NULL | Part category/type |
| `model_compatibility` | JSONB | NULL | Array of compatible models **NOT IN MIGRATION** |
| `quantity_on_hand` | INTEGER | NULL | **Stock Risk trigger** |
| `minimum_quantity` | INTEGER | NULL | **Reorder threshold** (NOT `quantity_minimum`) |
| `unit` | TEXT | NULL | Unit (ea, L, box, etc.) (NOT `unit_of_measure`) |
| `location` | TEXT | NULL | Physical location on yacht (NOT `storage_location`) |
| `last_counted_at` | TIMESTAMPTZ | NULL | **NOT IN MIGRATION** |
| `last_counted_by` | UUID | NULL | **NOT IN MIGRATION** |
| `search_embedding` | VECTOR | NULL | **NOT IN MIGRATION** - Vector embeddings |
| `embedding_text` | TEXT | NULL | **NOT IN MIGRATION** - Text for embedding generation |
| `metadata` | JSONB | NULL | Contains: unit_cost, supplier, department, order_no, lead_time_days, system_used_on, equipment_used_on |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(yacht_id → yachts), NO soft delete columns (blocker)
- **Indexes**: yacht_id, part_number (assumed - needs verification)
- **RLS**: ENABLED - policy filters by yacht_id match
- **Missing**: deleted_at, deleted_by, deletion_reason (soft delete needed for archive_part action)
- **Missing**: CHECK constraint on quantity_on_hand >= 0

---

### Related Table: `pms_shopping_list_items`

**Source**: Production database query (2026-01-23)

**⚠️ CANONICAL TABLE**: This is the FULL workflow table (45+ columns), NOT the simple `shopping_list_items` from migrations. Ignore/delete any other shopping_list tables.

**Key Columns** (abbreviated - 45 total):

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `yacht_id` | UUID | |
| `part_id` | UUID | FK → `pms_parts(id)`, NULL if candidate part |
| `part_name` | TEXT | Denormalized for candidates |
| `part_number` | TEXT | Denormalized for candidates |
| `manufacturer` | TEXT | Denormalized for candidates |
| `is_candidate_part` | BOOLEAN | True if part doesn't exist in pms_parts yet |
| `quantity_requested` | DECIMAL | |
| `quantity_approved` | DECIMAL | Set by HoD on approval |
| `quantity_ordered` | DECIMAL | Set when PO created |
| `quantity_received` | DECIMAL | Updated during receiving |
| `quantity_installed` | DECIMAL | |
| `unit` | TEXT | |
| `preferred_supplier` | TEXT | |
| `estimated_unit_price` | DECIMAL | |
| `status` | TEXT | Values: `partially_fulfilled`, `pending`, `ordered`, `fulfilled`, `cancelled` |
| `source_type` | TEXT | Values: `inventory_low`, `work_order`, `manual` |
| `source_work_order_id` | UUID | FK → `pms_work_orders(id)` |
| `order_id` | UUID | FK → purchase order |
| `approved_by` | UUID | HoD who approved |
| `approved_at` | TIMESTAMPTZ | |
| `urgency` | TEXT | Values: `normal`, `high`, `critical` |
| `required_by_date` | DATE | |
| `created_by` | UUID | |
| `created_at` | TIMESTAMPTZ | |
| `deleted_at` | TIMESTAMPTZ | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | |
| `deletion_reason` | TEXT | |
| `metadata` | JSONB | |

**Shopping List Flow**:
1. Draft → Crew creates item (`status='pending'`)
2. Approve → HoD approves (`approved_by`, `approved_at`, `status='approved'`)
3. Purchase Order → Purser creates PO (`order_id`, `status='ordered'`)
4. Receive → Parts arrive (`quantity_received`, `status='partially_fulfilled'` or `'fulfilled'`)

**Merge Behavior** (locked):
- If unapproved item exists for same part (`status='pending'`), UPDATE `quantity_requested += new_qty`
- If already approved/ordered, CREATE new line with warning: "Existing order in progress - creating additional request"

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(part_id → pms_parts), FK(source_work_order_id → pms_work_orders), FK(order_id → purchase_orders)
- **Indexes**: yacht_id + status (partial where deleted_at IS NULL)
- **RLS**: ENABLED - policy filters by yacht_id + created_by (HoD bypass)
- **Missing**: `purchase_url TEXT` column (user requested - blocker)

---

### Related Table: `pms_part_usage`

**Source**: Production database query (2026-01-23)

**Columns**:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `yacht_id` | UUID | |
| `part_id` | UUID | FK → `pms_parts(id)` |
| `quantity` | INTEGER | Amount used |
| `work_order_id` | UUID | FK → `pms_work_orders(id)` |
| `equipment_id` | UUID | FK → `pms_equipment(id)` |
| `usage_reason` | TEXT | Values: `work_order`, `maintenance`, `emergency`, `testing`, `other` |
| `notes` | TEXT | |
| `used_by` | UUID | User who logged usage |
| `used_at` | TIMESTAMPTZ | When part was used |
| `metadata` | JSONB | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(part_id → pms_parts), FK(work_order_id → pms_work_orders), FK(equipment_id → pms_equipment)
- **Indexes**: part_id + used_at DESC, work_order_id, equipment_id, yacht_id
- **RLS**: ENABLED - policy filters by yacht_id

---

### Related Table: `pms_work_order_parts`

**Source**: Production database query (2026-01-23)

**Columns**:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `work_order_id` | UUID | FK → `pms_work_orders(id)` |
| `part_id` | UUID | FK → `pms_parts(id)` |
| `quantity` | INTEGER | Amount needed (NOT split into required/used) |
| `notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |
| `deleted_at` | TIMESTAMPTZ | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(work_order_id → pms_work_orders), FK(part_id → pms_parts), **NO UNIQUE(work_order_id, part_id)** - consumables can be added multiple times
- **Indexes**: work_order_id, part_id
- **RLS**: ENABLED - policy filters by yacht_id via work_order join

---

### Yacht Rank Hierarchy

**Source**: `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/16_Roles_of_users/ranks.md`

**Command Chain**:
1. Captain (highest)
2. Staff Captain / Chief Officer
3. Second Officer
4. Third Officer
5. Safety Officer

**Heads of Department (HoD)**:
- Chief Engineer (Engineering, rank 14)
- Chief Steward/Stewardess (Interior, rank 23)
- Purser / Hotel Manager (Admin/Interior, rank 24)
- Executive Chef (Galley, rank 35)
- Chief Mate / First Officer (Deck, rank 6)
- Head of Security (Security, rank 40)

**Total Crew**: 45-60 on 125m yacht

---

## C) Role Permissions (Simple Tier Model)

### Everyone (All Crew)
- View inventory
- View usage history
- View shopping list (own requests)
- `log_part_usage`
- `add_to_shopping_list`
- `update_stock_count`
- `edit_part_details`

### Restricted
- **Approve shopping list**: HoD only (Chief Engineer, Chief Stew, Purser, Executive Chef, Chief Mate)
- **Archive part**: Captain, HoD, Purser + **SIGNATURE REQUIRED**
- **View all shopping list requests**: HoD + Purser (bypass created_by filter)

**Audit Requirement**: All mutations logged with user_id, session_id, IP address, timestamp.

---

## D) Default Display Fields (Not Actions)

**Always Visible**:
- Part name, part number, manufacturer
- Quantity on hand (with color badge: green ≥ min, yellow < min, red = 0)
- Minimum quantity (reorder threshold)
- Location (physical storage location on yacht)
- Unit of measure
- Supplier info (from metadata.supplier)
- Category
- Description
- Last counted (last_counted_at, last_counted_by)

---

## E) Inventory Micro-Actions (Exactly 6)

### 1. `log_part_usage`
- **Label**: "Log Usage"
- **Purpose**: Record consumption of parts
- **Writes to**: `pms_part_usage`, deducts from `pms_parts.quantity_on_hand`
- **Signature**: NO (audit only)
- **Modal**: `LogPartUsageModal.tsx`
- **Fields**:
  - REQUIRED: `quantity` (integer > 0), `used_by` (auto from session)
  - OPTIONAL: `work_order_id`, `equipment_id`, `usage_reason` (dropdown: work_order, maintenance, emergency, testing, other), `notes`
  - AUTOMATIC: `used_at` (NOW()), `yacht_id`, `part_id`, `metadata`

### 2. `add_to_shopping_list`
- **Label**: "Add to Shopping List"
- **Purpose**: Request reorder of part
- **Writes to**: `pms_shopping_list_items`
- **Signature**: NO (audit only)
- **Modal**: `AddToShoppingListModal.tsx`
- **Fields**:
  - REQUIRED: `quantity_requested`, `created_by` (auto from session)
  - OPTIONAL: `urgency` (dropdown: normal, high, critical), `source_notes`, `required_by_date`, `preferred_supplier`, `estimated_unit_price`
  - OPTIONAL WITH FAILSAFE: `source_work_order_id` (auto-inferred from context + dropdown failsafe), `installed_to_equipment_id` (auto-inferred from context + dropdown failsafe)
  - AUTOMATIC: `status='pending'`, `source_type='inventory_low'` or `'manual'`, `created_at`, `yacht_id`, `part_id`, `part_name`, `part_number`, `manufacturer`, `unit`
- **Merge Logic**: If unapproved item exists (`status='pending'`), UPDATE quantity. If approved/ordered, CREATE new line with warning.

### 3. `update_stock_count`
- **Label**: "Update Stock Count"
- **Purpose**: Manual inventory adjustment
- **Writes to**: `pms_parts.quantity_on_hand`, `pms_parts.last_counted_at`, `pms_parts.last_counted_by`
- **Signature**: NO (audit only)
- **Modal**: `UpdateStockCountModal.tsx`
- **Fields**:
  - REQUIRED: New quantity value, adjustment reason (dropdown: physical count, correction, receiving, transfer)
  - OPTIONAL: Notes
  - AUTOMATIC: `last_counted_at=NOW()`, `last_counted_by=user_id`

### 4. `edit_part_details`
- **Label**: "Edit Part"
- **Purpose**: Update part metadata
- **Writes to**: `pms_parts` (name, description, category, manufacturer, location, minimum_quantity, unit, metadata)
- **Signature**: NO (audit only)
- **Modal**: `EditPartModal.tsx`

### 5. `view_usage_history`
- **Label**: "View Usage History"
- **Purpose**: Show consumption timeline
- **Reads**: `pms_part_usage` WHERE `part_id = ?` ORDER BY `used_at DESC`
- **Signature**: NO (read-only)
- **Destination**: Usage history panel/modal showing: date, user, quantity, work order link, equipment link, reason, notes

### 6. `archive_part`
- **Label**: "Archive Part"
- **Purpose**: Soft delete part (30-day undo window)
- **Writes to**: `pms_parts.deleted_at`, `deleted_by`, `deletion_reason`
- **Signature**: **YES - REQUIRED**
- **Modal**: `ArchivePartModal.tsx` with signature capture
- **Permission**: Captain, HoD, Purser only
- **Undo**: Parts remain in DB for 30 days, can be restored by same roles
- **🚨 BLOCKER**: Schema has NO soft delete columns for pms_parts - requires migration (deleted_at, deleted_by, deletion_reason)

**Hard Delete**: Phase 2 only. Not in MVP.

---

## F) Related Button Contract

**Related** (top-right button in part detail):
- FK joins (work orders using this part, equipment using this part)
- Vector search seeded from entity fields only: `embedding_text`, `manufacturer`, `part_number`, `name`, `model_compatibility`
- **Never user query**. **No predictive logic**.

Examples:
- "Work Orders Using This Part" → FK join on `pms_work_order_parts.part_id`
- "Equipment Using This Part" → FK join on equipment parts list or metadata reference
- "Related Manuals" → Vector search using `embedding_text` → `documents` + `search_chunks`

---

## G) Situation Modifier: Stock Risk

### Trigger (Simple)

```sql
quantity_on_hand < minimum_quantity
AND minimum_quantity > 0
```

### UX Changes

**Color Badge**:
- **Green**: `quantity_on_hand >= minimum_quantity` (OK)
- **Yellow**: `quantity_on_hand < minimum_quantity AND quantity_on_hand > 0` (Low Stock)
- **Red**: `quantity_on_hand = 0` (Out of Stock)

**Action Reordering**:
- **BEFORE**: Log Usage (primary), Add to Shopping List (secondary)
- **AFTER**: Add to Shopping List (primary, yellow/red button), Log Usage (secondary with warning)

**Banner** (ONE only):
- Yellow/Red banner at top: "⚠️ Low stock: {qty} remaining (reorder at {min})" or "🚨 OUT OF STOCK"
- Dismissible: YES
- CTA: "Add to Shopping List" button inline

**Prefill**:
- `quantity_requested = minimum_quantity - quantity_on_hand`
- `urgency = 'critical'` if qty = 0, else `'normal'`
- `source_notes = "Auto-suggested: Stock below minimum"`

**No prediction. No urgency levels. No complex state machine.**

---

## H) Edge Cases

### 1. Multiple Shopping List Items for Same Part
- **Merge if unapproved** (`status='pending'`): UPDATE `quantity_requested += new_qty`
- **New line if approved/ordered**: CREATE new row, show warning: "Existing order in progress - creating additional request"

### 2. Archive Collision (Soft Delete)
- User A viewing part. User B archives part. User A tries action.
- Action fails with: "Part archived by {user} at {time}"
- Show "Restore Part" option for authorized roles
- 30-day undo window

---

## I) Blockers

### BLOCKER 1: No Soft Delete on pms_parts
- **Impact**: Cannot implement `archive_part` action
- **Resolution**: Add migration for `deleted_at`, `deleted_by`, `deletion_reason` to `pms_parts`
- **Scope**: Start with `pms_parts` + `pms_shopping_list_items` only. Expand to other tables in Phase 2.

### BLOCKER 2: No purchase_url Column
- **Impact**: Cannot store purchase URL for shopping list items
- **Resolution**: Add `purchase_url TEXT` column to `pms_shopping_list_items`

### BLOCKER 3: Race Conditions on Stock Deduction
- **Impact**: Concurrent usage can create negative stock
- **User Assessment**: "0.001% chance this will ever occur"
- **Resolution**: Flag for Phase 2. Low priority for MVP.

---

## J) Summary

**Entity Lens**: Inventory Item (Parts)
**Primary Table**: `pms_parts` (19 columns, production DB verified)
**Related Tables**: `pms_shopping_list_items` (45+ columns, canonical), `pms_part_usage` (11 columns), `pms_work_order_parts` (9 columns)
**Situation Modifiers**: 1 (Stock Risk - simple color coding + button promotion)
**Micro-Actions**: 6 (log_part_usage, add_to_shopping_list, update_stock_count, edit_part_details, view_usage_history, archive_part)
**Default Display Fields**: 9 (supplier info, location, last counted, etc. - NOT actions)
**Blockers**: 3 (soft delete, purchase_url, race conditions flagged for Phase 2)

**Key Principles**:
- ✅ Production DB is truth (NOT migrations)
- ✅ SPA route state (`/parts/<uuid>`) - no page reload
- ✅ Related = FK joins + vector from entity fields only (never user query)
- ✅ Shopping list merge: unapproved → update qty, approved/ordered → new line + warning
- ✅ Permissions: Everyone can mutate (with audit), HoD can approve, Captain/HoD can archive (with signature)
- ✅ Stock Risk simplified: color badge + button promotion + ONE dismissible banner
- ✅ Archive (soft delete) preferred. Hard delete = Phase 2.

---

**STOP. Awaiting review.**
