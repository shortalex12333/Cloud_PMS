# Inventory Item Lens - Phase 2: DB Truth

**Status**: Draft v1
**Last Updated**: 2026-01-27
**Author**: Full Stack Engineer
**Schema Source**: Production Database (database_schema.txt, 2026-01-27)

---

## 1. Primary Table: `pms_parts`

### 1.1 Schema Definition

| Column | Type | Nullable | Default | Classification | Notes |
|--------|------|----------|---------|----------------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | **BACKEND_AUTO** | PK |
| `yacht_id` | UUID | NOT NULL | - | **BACKEND_AUTO** | FK → yachts, from get_user_yacht_id() |
| `name` | TEXT | NOT NULL | - | **REQUIRED** | Display name |
| `part_number` | TEXT | YES | NULL | **OPTIONAL** | OEM/internal part number |
| `manufacturer` | TEXT | YES | NULL | **OPTIONAL** | Manufacturer name |
| `description` | TEXT | YES | NULL | **OPTIONAL** | Long-form description |
| `category` | TEXT | YES | NULL | **OPTIONAL** | Part category/type |
| `model_compatibility` | JSONB | YES | NULL | **OPTIONAL** | Array of compatible models |
| `quantity_on_hand` | INTEGER | NOT NULL | 0 | **REQUIRED** | Current stock level |
| `minimum_quantity` | INTEGER | YES | NULL | **OPTIONAL** | Reorder threshold |
| `unit` | TEXT | YES | NULL | **OPTIONAL** | Unit of measure (ea, L, box) |
| `location` | TEXT | YES | NULL | **OPTIONAL** | Physical storage location |
| `last_counted_at` | TIMESTAMPTZ | YES | NULL | **BACKEND_AUTO** | Set by update_stock_count |
| `last_counted_by` | UUID | YES | NULL | **BACKEND_AUTO** | Set by update_stock_count |
| `search_embedding` | VECTOR(1536) | YES | NULL | **BACKEND_AUTO** | Vector for RAG |
| `embedding_text` | TEXT | YES | NULL | **BACKEND_AUTO** | Text for embedding generation |
| `metadata` | JSONB | YES | '{}' | **OPTIONAL** | Extensible fields |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() | **BACKEND_AUTO** | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | NOW() | **BACKEND_AUTO** | |

### 1.2 Metadata JSONB Structure

```json
{
  "unit_cost": 125.50,
  "currency": "USD",
  "supplier": "Marine Parts Inc.",
  "supplier_part_number": "MPI-OF-1234",
  "supplier_contact": "orders@marineparts.com",
  "department": "engineering",
  "order_no": "PO-2026-001",
  "lead_time_days": 14,
  "system_used_on": "Main Engine",
  "equipment_used_on": ["Generator 1", "Generator 2"],
  "notes": "Keep minimum 5 in stock during charter season"
}
```

### 1.3 Constraints

| Constraint | Type | Definition |
|------------|------|------------|
| `pms_parts_pkey` | PRIMARY KEY | `(id)` |
| `pms_parts_yacht_id_fkey` | FOREIGN KEY | `yacht_id REFERENCES yachts(id)` |

### 1.4 Indexes (Verified/Assumed)

| Index | Columns | Type | Notes |
|-------|---------|------|-------|
| `pms_parts_pkey` | `id` | PRIMARY | Auto |
| `idx_pms_parts_yacht_id` | `yacht_id` | BTREE | RLS performance |
| `idx_pms_parts_part_number` | `yacht_id, part_number` | BTREE | Search |
| `idx_pms_parts_embedding` | `search_embedding` | IVFFlat | Vector search |

### 1.5 RLS Status

- **RLS**: ENABLED
- **Policies**: See Phase 7

### 1.6 MISSING (Blockers)

| Column | Required For | Migration Priority |
|--------|--------------|-------------------|
| `deleted_at` | archive_part | **HIGH** |
| `deleted_by` | archive_part | **HIGH** |
| `deletion_reason` | archive_part | **HIGH** |

---

## 2. Related Table: `pms_part_usage`

### 2.1 Schema Definition

| Column | Type | Nullable | Default | Classification | Notes |
|--------|------|----------|---------|----------------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | **BACKEND_AUTO** | PK |
| `yacht_id` | UUID | NOT NULL | - | **BACKEND_AUTO** | FK → yachts |
| `part_id` | UUID | NOT NULL | - | **CONTEXT** | FK → pms_parts, from lens focus |
| `quantity` | INTEGER | NOT NULL | - | **REQUIRED** | Amount consumed |
| `work_order_id` | UUID | YES | NULL | **CONTEXT** | FK → pms_work_orders, if from WO context |
| `equipment_id` | UUID | YES | NULL | **CONTEXT** | FK → pms_equipment, from entity extraction |
| `usage_reason` | TEXT | YES | NULL | **OPTIONAL** | work_order, maintenance, emergency, testing, other |
| `notes` | TEXT | YES | NULL | **OPTIONAL** | Free text |
| `used_by` | UUID | NOT NULL | - | **BACKEND_AUTO** | From auth.uid() |
| `used_at` | TIMESTAMPTZ | NOT NULL | NOW() | **BACKEND_AUTO** | Timestamp |
| `metadata` | JSONB | YES | '{}' | **BACKEND_AUTO** | Extensible |

### 2.2 Constraints

| Constraint | Type | Definition |
|------------|------|------------|
| `pms_part_usage_pkey` | PRIMARY KEY | `(id)` |
| `pms_part_usage_part_id_fkey` | FOREIGN KEY | `part_id REFERENCES pms_parts(id)` |
| `pms_part_usage_work_order_id_fkey` | FOREIGN KEY | `work_order_id REFERENCES pms_work_orders(id)` |
| `pms_part_usage_equipment_id_fkey` | FOREIGN KEY | `equipment_id REFERENCES pms_equipment(id)` |

### 2.3 Indexes

| Index | Columns | Type |
|-------|---------|------|
| `pms_part_usage_pkey` | `id` | PRIMARY |
| `idx_pms_part_usage_part_id` | `part_id, used_at DESC` | BTREE |
| `idx_pms_part_usage_work_order_id` | `work_order_id` | BTREE |
| `idx_pms_part_usage_yacht_id` | `yacht_id` | BTREE |

---

## 3. Related Table: `pms_shopping_list_items`

### 3.1 Schema Definition (45+ columns - key subset)

| Column | Type | Nullable | Default | Classification | Notes |
|--------|------|----------|---------|----------------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | **BACKEND_AUTO** | PK |
| `yacht_id` | UUID | NOT NULL | - | **BACKEND_AUTO** | |
| `part_id` | UUID | YES | NULL | **CONTEXT** | FK → pms_parts, NULL for candidates |
| `part_name` | TEXT | NOT NULL | - | **BACKEND_AUTO** | Denormalized from part |
| `part_number` | TEXT | YES | NULL | **BACKEND_AUTO** | Denormalized |
| `manufacturer` | TEXT | YES | NULL | **BACKEND_AUTO** | Denormalized |
| `is_candidate_part` | BOOLEAN | NOT NULL | false | **BACKEND_AUTO** | True if part doesn't exist |
| `quantity_requested` | NUMERIC | NOT NULL | - | **REQUIRED** | User specifies |
| `quantity_approved` | NUMERIC | YES | NULL | **BACKEND_AUTO** | Set by HoD |
| `quantity_ordered` | NUMERIC | YES | NULL | **BACKEND_AUTO** | Set when PO created |
| `quantity_received` | NUMERIC | YES | NULL | **BACKEND_AUTO** | Set during receiving |
| `unit` | TEXT | YES | NULL | **BACKEND_AUTO** | Denormalized |
| `preferred_supplier` | TEXT | YES | NULL | **OPTIONAL** | User can specify |
| `estimated_unit_price` | NUMERIC | YES | NULL | **OPTIONAL** | User estimate |
| `status` | TEXT | NOT NULL | 'pending' | **BACKEND_AUTO** | pending/approved/ordered/fulfilled/cancelled |
| `source_type` | TEXT | NOT NULL | - | **BACKEND_AUTO** | inventory_low/work_order/manual |
| `source_work_order_id` | UUID | YES | NULL | **CONTEXT** | FK → pms_work_orders |
| `source_notes` | TEXT | YES | NULL | **OPTIONAL** | |
| `urgency` | TEXT | YES | 'normal' | **OPTIONAL** | normal/high/critical |
| `required_by_date` | DATE | YES | NULL | **OPTIONAL** | |
| `created_by` | UUID | NOT NULL | - | **BACKEND_AUTO** | From auth.uid() |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() | **BACKEND_AUTO** | |
| `approved_by` | UUID | YES | NULL | **BACKEND_AUTO** | HoD who approved |
| `approved_at` | TIMESTAMPTZ | YES | NULL | **BACKEND_AUTO** | |
| `deleted_at` | TIMESTAMPTZ | YES | NULL | **BACKEND_AUTO** | Soft delete |
| `deleted_by` | UUID | YES | NULL | **BACKEND_AUTO** | |
| `deletion_reason` | TEXT | YES | NULL | **BACKEND_AUTO** | |

### 3.2 Status State Machine

```
pending → approved → ordered → partially_fulfilled → fulfilled
    │         │
    └→ cancelled (any state except fulfilled)
```

### 3.3 Merge Logic

When adding to shopping list for a part that already has a pending item:
```sql
-- Check for existing pending item
SELECT id, quantity_requested FROM pms_shopping_list_items
WHERE part_id = $part_id
  AND yacht_id = $yacht_id
  AND status = 'pending'
  AND deleted_at IS NULL;

-- If exists: UPDATE quantity
-- If not: INSERT new row
```

---

## 4. Related Table: `pms_work_order_parts`

### 4.1 Schema Definition

| Column | Type | Nullable | Default | Classification | Notes |
|--------|------|----------|---------|----------------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | **BACKEND_AUTO** | PK |
| `work_order_id` | UUID | NOT NULL | - | FK → pms_work_orders | |
| `part_id` | UUID | NOT NULL | - | FK → pms_parts | |
| `quantity` | INTEGER | NOT NULL | - | Amount needed | |
| `notes` | TEXT | YES | NULL | | |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() | | |
| `updated_at` | TIMESTAMPTZ | YES | NULL | | |
| `deleted_at` | TIMESTAMPTZ | YES | NULL | Soft delete | |
| `deleted_by` | UUID | YES | NULL | | |

### 4.2 Important Note

**NO UNIQUE constraint on (work_order_id, part_id)** - Consumables can be added multiple times to same work order.

---

## 5. Audit Table: `pms_audit_log`

### 5.1 Schema Definition

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | PK |
| `yacht_id` | UUID | NOT NULL | - | |
| `entity_type` | TEXT | NOT NULL | - | 'part', 'part_usage', 'shopping_list_item' |
| `entity_id` | UUID | NOT NULL | - | |
| `action` | TEXT | NOT NULL | - | Action ID |
| `user_id` | UUID | NOT NULL | - | |
| `old_values` | JSONB | YES | NULL | Before state |
| `new_values` | JSONB | NOT NULL | - | After state |
| `signature` | JSONB | NOT NULL | '{}' | **INVARIANT**: {} for non-signed, JSON for signed |
| `metadata` | JSONB | YES | NULL | session_id, ip_address, etc. |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() | |

### 5.2 Signature Invariant

```sql
-- Non-signed actions (log_part_usage, add_to_shopping_list, etc.)
signature = '{}'::jsonb

-- Signed actions (archive_part)
signature = '{
  "signer_id": "uuid",
  "signer_role": "chief_engineer",
  "signed_at": "2026-01-27T10:00:00Z",
  "signature_hash": "sha256-...",
  "reason": "Part obsolete - replaced by new model"
}'::jsonb
```

---

## 6. Field Classification Summary by Action

### 6.1 `log_part_usage`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists, not archived |
| `quantity` | **REQUIRED** | User input | > 0, integer |
| `work_order_id` | **CONTEXT** | From navigation context or dropdown | FK exists if provided |
| `equipment_id` | **CONTEXT** | From entity extraction or dropdown | FK exists if provided |
| `usage_reason` | **OPTIONAL** | Dropdown | Enum: work_order/maintenance/emergency/testing/other |
| `notes` | **OPTIONAL** | Text input | Max 2000 chars |
| `used_by` | **BACKEND_AUTO** | auth.uid() | - |
| `used_at` | **BACKEND_AUTO** | NOW() | - |
| `yacht_id` | **BACKEND_AUTO** | get_user_yacht_id() | - |

### 6.2 `add_to_shopping_list`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists |
| `quantity_requested` | **REQUIRED** | User input (prefill: min - current) | > 0 |
| `urgency` | **OPTIONAL** | Dropdown (prefill based on stock) | Enum: normal/high/critical |
| `source_work_order_id` | **CONTEXT** | From navigation context or dropdown | FK exists if provided |
| `source_notes` | **OPTIONAL** | Text input | Max 2000 chars |
| `required_by_date` | **OPTIONAL** | Date picker | >= today |
| `preferred_supplier` | **OPTIONAL** | Text input | - |
| `estimated_unit_price` | **OPTIONAL** | Number input | >= 0 |
| `status` | **BACKEND_AUTO** | 'pending' | - |
| `source_type` | **BACKEND_AUTO** | Based on Stock Risk | 'inventory_low' or 'manual' |
| `part_name` | **BACKEND_AUTO** | From pms_parts | - |
| `part_number` | **BACKEND_AUTO** | From pms_parts | - |
| `manufacturer` | **BACKEND_AUTO** | From pms_parts | - |
| `unit` | **BACKEND_AUTO** | From pms_parts | - |
| `created_by` | **BACKEND_AUTO** | auth.uid() | - |
| `yacht_id` | **BACKEND_AUTO** | get_user_yacht_id() | - |

### 6.3 `update_stock_count`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists |
| `new_quantity` | **REQUIRED** | User input | >= 0, integer |
| `adjustment_reason` | **REQUIRED** | Dropdown | Enum: physical_count/correction/receiving/transfer |
| `notes` | **OPTIONAL** | Text input | Max 2000 chars |
| `last_counted_at` | **BACKEND_AUTO** | NOW() | - |
| `last_counted_by` | **BACKEND_AUTO** | auth.uid() | - |

### 6.4 `edit_part_details`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists |
| `name` | **REQUIRED** | Text input | NOT NULL, not empty |
| `part_number` | **OPTIONAL** | Text input | - |
| `manufacturer` | **OPTIONAL** | Text input | - |
| `description` | **OPTIONAL** | Text area | Max 5000 chars |
| `category` | **OPTIONAL** | Dropdown/text | - |
| `minimum_quantity` | **OPTIONAL** | Number input | >= 0 |
| `unit` | **OPTIONAL** | Dropdown | - |
| `location` | **OPTIONAL** | Text input | - |
| `metadata` | **OPTIONAL** | Structured form | Valid JSON |

### 6.5 `attach_document`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists |
| `file` | **REQUIRED** | File upload | Max 50MB, allowed types |
| `document_type` | **OPTIONAL** | Dropdown | spec_sheet/datasheet/manual/other |
| `notes` | **OPTIONAL** | Text input | Max 2000 chars |
| `yacht_id` | **BACKEND_AUTO** | get_user_yacht_id() | - |
| `storage_path` | **BACKEND_AUTO** | {yacht_id}/parts/{part_id}/{filename} | - |
| `uploaded_by` | **BACKEND_AUTO** | auth.uid() | - |

### 6.6 `archive_part`

| Field | Classification | Source | Validation |
|-------|----------------|--------|------------|
| `part_id` | **CONTEXT** | From lens focus | FK exists, not already archived |
| `deletion_reason` | **REQUIRED** | Text input | NOT NULL, min 10 chars |
| `signature` | **REQUIRED** | Signature capture widget | Valid signature data |
| `deleted_at` | **BACKEND_AUTO** | NOW() | - |
| `deleted_by` | **BACKEND_AUTO** | auth.uid() | - |

---

## 7. Storage Configuration

### 7.1 Bucket: `documents`

```python
ACTION_STORAGE_CONFIG["attach_document"] = {
    "bucket": "documents",
    "path_template": "{yacht_id}/parts/{part_id}/{filename}",
    "writable_prefixes": ["{yacht_id}/parts/"],
    "max_file_size_mb": 50,
    "allowed_mime_types": [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    "confirmation_required": False,
}
```

---

## 8. Database Functions Required

### 8.1 `deduct_part_inventory()` - TO BE CREATED

```sql
CREATE OR REPLACE FUNCTION deduct_part_inventory(
    p_yacht_id UUID,
    p_part_id UUID,
    p_quantity INTEGER,
    p_work_order_id UUID DEFAULT NULL,
    p_equipment_id UUID DEFAULT NULL,
    p_usage_reason TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL,
    p_used_by UUID DEFAULT NULL
) RETURNS TABLE(
    success BOOLEAN,
    usage_id UUID,
    new_quantity INTEGER,
    error_code TEXT
) AS $$
DECLARE
    v_current_qty INTEGER;
    v_usage_id UUID;
BEGIN
    -- Row lock to prevent concurrent updates
    SELECT quantity_on_hand INTO v_current_qty
    FROM pms_parts
    WHERE id = p_part_id
      AND yacht_id = p_yacht_id
      AND deleted_at IS NULL  -- When soft delete added
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL::UUID, NULL::INTEGER, 'PART_NOT_FOUND'::TEXT;
        RETURN;
    END IF;

    -- Allow negative stock (with warning in UI), don't block
    -- User requested: "0.001% chance this will ever occur"

    -- Deduct stock
    UPDATE pms_parts
    SET quantity_on_hand = quantity_on_hand - p_quantity,
        updated_at = NOW()
    WHERE id = p_part_id;

    -- Insert usage record
    INSERT INTO pms_part_usage (
        yacht_id, part_id, quantity, work_order_id, equipment_id,
        usage_reason, notes, used_by, used_at
    ) VALUES (
        p_yacht_id, p_part_id, p_quantity, p_work_order_id, p_equipment_id,
        p_usage_reason, p_notes, COALESCE(p_used_by, auth.uid()), NOW()
    ) RETURNING id INTO v_usage_id;

    RETURN QUERY SELECT
        TRUE,
        v_usage_id,
        v_current_qty - p_quantity,
        NULL::TEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 9. Verification Checklist

| Item | Status | Notes |
|------|--------|-------|
| pms_parts schema matches production | ✅ | Verified against database_schema.txt |
| pms_part_usage schema matches production | ✅ | Verified |
| pms_shopping_list_items schema matches production | ✅ | Verified |
| pms_audit_log has signature column | ✅ | JSONB, NOT NULL |
| RLS enabled on all tables | ✅ | Verified |
| Soft delete columns on pms_parts | ❌ | **BLOCKER** - Migration required |
| deduct_part_inventory function exists | ❌ | **BLOCKER** - Creation required |

---

**STOP. Phase 2 complete. Proceed to Phase 3: Entity Graph.**
