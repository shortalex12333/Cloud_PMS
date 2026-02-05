# Handover Tables Consolidation Migration

**Date:** 2026-02-05
**Migration File:** `supabase/migrations/20260205140000_consolidate_handover_tables.sql`

---

## Summary

Consolidated 17 handover-related tables/views down to **2 tables + 1 view**.

**Before:** 17 objects (8 tables, 4 backup tables, 4 views, 1 config table)
**After:** 3 objects (2 tables, 1 view)

---

## Tables DROPPED (13 tables)

| Table | Rows Before | Reason |
|-------|-------------|--------|
| `handovers` | 3 | Parent container not needed, items are standalone |
| `pms_handover` | 0 | Merged concept into `handover_items` |
| `handover_drafts` | 1 | Simplified to just items + exports |
| `handover_signoffs` | 1 | Columns merged into `handover_exports` |
| `handover_buckets` | 8 | Hardcode 8 buckets in app code |
| `role_handover_buckets` | 46 | Use RLS instead |
| `handover_draft_items` | 0 | Never used in code |
| `handover_draft_sections` | 0 | Never used in code |
| `handover_draft_edits` | 0 | Never used in code |
| `_bkp_dash_handover_items` | ? | Backup pollution |
| `_bkp_dash_handover_records` | ? | Backup pollution |
| `_bkp_handover_entries` | ? | Backup pollution |
| `_bkp_handover_sources` | ? | Backup pollution |

---

## Views DROPPED (3 views)

| View | Reason |
|------|--------|
| `v_handover_export_items` | Replaced with simpler version |
| `v_handover_draft_complete` | Never used |
| `v_handover_signoffs` | Never used |

---

## Tables KEPT (2 tables)

### 1. `handover_items` (Draft Notes)

**Purpose:** User-submitted handover notes. Supports view/edit/delete until exported.

**Row Count:** 13 rows

#### ALL COLUMNS:

| Column | Type | Nullable | Default | Description | **NEW** |
|--------|------|----------|---------|-------------|---------|
| `id` | uuid | NO | gen_random_uuid() | Primary key | |
| `yacht_id` | uuid | NO | | Tenant isolation FK | |
| `handover_id` | uuid | **YES** | | Legacy parent ref (now nullable) | MODIFIED |
| `entity_id` | uuid | YES | | FK to source entity | |
| `entity_type` | text | YES | | fault, work_order, equipment, etc. | |
| `section` | text | YES | | Department section name | |
| `summary` | text | YES | | Item description text | |
| `priority` | integer | YES | 0 | 0=low, 1=normal, 2=high, 3=critical | |
| `status` | text | YES | | pending, acknowledged, completed | |
| `acknowledged_by` | uuid | YES | | User who acknowledged | |
| `acknowledged_at` | timestamptz | YES | | When acknowledged | |
| `acknowledgement_notes` | text | YES | | Notes on acknowledgement | |
| `metadata` | jsonb | YES | '{}' | Additional metadata | |
| `created_at` | timestamptz | YES | now() | Record creation | |
| `added_by` | uuid | YES | | User who added item | |
| `updated_at` | timestamptz | YES | | Last update timestamp | |
| `updated_by` | uuid | YES | | User who updated | |
| `deleted_at` | timestamptz | YES | | Soft delete timestamp | |
| `deleted_by` | uuid | YES | | User who deleted | |
| `deletion_reason` | text | YES | | Why deleted | |
| `source_ids` | uuid[] | YES | | Source entry references | |
| `category` | text | YES | | urgent, in_progress, completed, watch, fyi | **NEW** |
| `is_critical` | boolean | YES | false | Critical attention flag | **NEW** |
| `requires_action` | boolean | YES | false | Action needed flag | **NEW** |
| `action_summary` | text | YES | | What action is required | **NEW** |
| `risk_tags` | text[] | YES | | Safety_Critical, Compliance_Critical, etc. | **NEW** |
| `entity_url` | text | YES | | Direct URL for entity link in export | **NEW** |

#### NEW INDEXES:

| Index Name | Columns | Condition |
|------------|---------|-----------|
| `idx_handover_items_category` | `(yacht_id, category)` | `WHERE deleted_at IS NULL` |
| `idx_handover_items_critical` | `(yacht_id, is_critical)` | `WHERE is_critical = true AND deleted_at IS NULL` |
| `idx_handover_items_action` | `(yacht_id, requires_action)` | `WHERE requires_action = true AND deleted_at IS NULL` |

---

### 2. `handover_exports` (Exported + Signoff)

**Purpose:** Records of exported handover documents. Files stored in `handover-exports` bucket.

**Row Count:** 15 rows

#### ALL COLUMNS:

| Column | Type | Nullable | Default | Description | **NEW** |
|--------|------|----------|---------|-------------|---------|
| `id` | uuid | NO | gen_random_uuid() | Primary key | |
| `draft_id` | uuid | **YES** | | Legacy draft ref (now nullable) | MODIFIED |
| `yacht_id` | uuid | NO | | Tenant isolation FK | |
| `export_type` | text | NO | | pdf, html, email | |
| `storage_path` | text | YES | | Path in storage bucket | |
| `storage_bucket` | text | YES | | Bucket name (handover-exports) | |
| `file_name` | text | YES | | Generated filename | |
| `file_size_bytes` | integer | YES | | File size | |
| `exported_by_user_id` | uuid | YES | | User who exported | |
| `exported_at` | timestamptz | YES | now() | Export timestamp | |
| `recipients` | text[] | YES | | Email recipients | |
| `email_subject` | text | YES | | Email subject line | |
| `email_sent_at` | timestamptz | YES | | When email was sent | |
| `document_hash` | text | YES | | SHA256 hash for integrity | |
| `export_status` | text | YES | | pending, completed, failed | |
| `error_message` | text | YES | | Error details if failed | |
| `created_at` | timestamptz | YES | now() | Record creation | |
| `file_url` | text | YES | | Public/signed URL | |
| `department` | text | YES | | Command, Engineering, Deck, etc. | **NEW** |
| `outgoing_user_id` | uuid | YES | | Outgoing officer user ID | **NEW** |
| `outgoing_role` | text | YES | | Outgoing officer role | **NEW** |
| `outgoing_signed_at` | timestamptz | YES | | When outgoing signed | **NEW** |
| `outgoing_notes` | text | YES | | Notes from outgoing officer | **NEW** |
| `incoming_user_id` | uuid | YES | | Incoming officer user ID | **NEW** |
| `incoming_role` | text | YES | | Incoming officer role | **NEW** |
| `incoming_signed_at` | timestamptz | YES | | When incoming signed | **NEW** |
| `incoming_notes` | text | YES | | Notes from incoming officer | **NEW** |
| `incoming_acknowledged_critical` | boolean | YES | false | Confirmed critical items read | **NEW** |
| `signoff_complete` | boolean | YES | false | Both parties signed | **NEW** |

#### NEW INDEXES:

| Index Name | Columns | Condition |
|------------|---------|-----------|
| `idx_handover_exports_department` | `(yacht_id, department)` | |
| `idx_handover_exports_signoff` | `(yacht_id, signoff_complete)` | `WHERE signoff_complete = false` |

---

## View CREATED (1 view)

### `v_handover_export_items`

**Purpose:** Unified view of handover items for export pipeline.

#### COLUMNS:

| Column | Type | Source |
|--------|------|--------|
| `id` | uuid | handover_items.id |
| `yacht_id` | uuid | handover_items.yacht_id |
| `entity_type` | text | handover_items.entity_type |
| `entity_id` | uuid | handover_items.entity_id |
| `summary_text` | text | COALESCE(handover_items.summary, '') |
| `section` | text | handover_items.section |
| `category` | text | handover_items.category |
| `priority` | integer | handover_items.priority |
| `status` | text | handover_items.status |
| `is_critical` | boolean | handover_items.is_critical |
| `requires_action` | boolean | handover_items.requires_action |
| `action_summary` | text | handover_items.action_summary |
| `risk_tags` | text[] | handover_items.risk_tags |
| `entity_url` | text | handover_items.entity_url |
| `added_by` | uuid | handover_items.added_by |
| `added_at` | timestamptz | handover_items.created_at |
| `acknowledged_by` | uuid | handover_items.acknowledged_by |
| `acknowledged_at` | timestamptz | handover_items.acknowledged_at |
| `metadata` | jsonb | handover_items.metadata |
| `source_table` | text | 'handover_items' (constant) |

**Filter:** `WHERE deleted_at IS NULL`

---

## Data Migration

**Signoff data migrated:** 5 rows from `handover_signoffs` → `handover_exports`

The UPDATE statement copied signoff columns from `handover_signoffs` to matching `handover_exports` records based on `draft_id`.

---

## Hardcoded Buckets (8 values)

Since `handover_buckets` table was dropped, these 8 bucket codes should be hardcoded in application code:

```javascript
const HANDOVER_BUCKETS = [
  'Command',
  'Engineering',
  'ETO_AVIT',
  'Deck',
  'Interior',
  'Galley',
  'Security',
  'Admin_Compliance'
];
```

---

## Code Files to Update

The following files reference dropped tables and need updates:

1. **`apps/api/services/handover_export_service.py`**
   - Update to use `handover_items` instead of `v_handover_export_items` (view was recreated with same name)
   - Remove `handover_drafts` creation logic (lines 644-658)

2. **`apps/api/handlers/handover_handlers.py`**
   - Update to use `handover_items` instead of `pms_handover`

3. **`apps/web/src/lib/microactions/handlers/handover.ts`**
   - Update to use `handover_items` instead of `handovers` + `handover_items`
   - Remove `handovers` table creation logic

---

## Workflow Changes

### Before:
```
User adds item → pms_handover OR (handovers → handover_items)
                    ↓
          handover_drafts created
                    ↓
          handover_exports created → file to bucket
                    ↓
          handover_signoffs for dual sign
```

### After:
```
User adds item → handover_items
                    ↓
          handover_exports created → file to handover-exports bucket
          (signoff columns in same table)
```

---

## Storage Bucket

**Bucket Name:** `handover-exports`
**Purpose:** PDF/HTML export files
**Policies:** 2 (as shown in Supabase dashboard)

---

## Rollback

If needed, rollback by:
1. Restore tables from backup (if available)
2. Re-create dropped tables from `docs/architecture/19_handover_export/01_data_model.md`
3. Remove added columns from `handover_items` and `handover_exports`

---

## Summary Table

| Action | Count |
|--------|-------|
| Tables dropped | 13 |
| Views dropped | 3 |
| Tables modified | 2 |
| New columns added | 17 |
| New indexes created | 5 |
| Views created | 1 |
| Data rows migrated | 5 (signoffs) |

---

## F1 Search Pipeline Migration

**Purpose:** Update F1 Search indexing from deprecated `handovers` table to new `handover_items` table.

### SQL Migration for F1 Search

```sql
-- =============================================================================
-- F1 SEARCH: HANDOVER ITEMS MIGRATION
-- =============================================================================
-- Run AFTER the main handover consolidation migration

BEGIN;

-- 1. Drop old triggers on deprecated handovers table
DROP TRIGGER IF EXISTS trg_spq_handovers_insup ON handovers;
DROP TRIGGER IF EXISTS trg_spq_handovers_del ON handovers;

-- 2. Create triggers on handover_items for search index sync
CREATE OR REPLACE TRIGGER trg_spq_handover_items_insup
    AFTER INSERT OR UPDATE ON handover_items
    FOR EACH ROW EXECUTE FUNCTION spq_enqueue_change();

CREATE OR REPLACE TRIGGER trg_spq_handover_items_del
    AFTER DELETE ON handover_items
    FOR EACH ROW EXECUTE FUNCTION spq_enqueue_change();

-- 3. Clear old indexed handovers from search_index
DELETE FROM search_index WHERE object_type = 'handover';

-- 4. Update search_projection_map for new table
DELETE FROM search_projection_map WHERE domain = 'handovers';

INSERT INTO search_projection_map (domain, source_table, object_type, search_text_cols, filter_map, payload_map, enabled)
VALUES (
    'handover_items',
    'handover_items',
    'handover_item',
    ARRAY['summary', 'entity_type', 'section', 'category', 'action_summary'],
    '{"status": "status", "entity_type": "entity_type", "section": "section", "priority": "priority", "category": "category", "is_critical": "is_critical"}'::jsonb,
    '{"summary": "summary", "entity_type": "entity_type", "section": "section", "status": "status", "priority": "priority", "entity_id": "entity_id", "category": "category", "is_critical": "is_critical", "action_summary": "action_summary"}'::jsonb,
    true
)
ON CONFLICT (domain) DO UPDATE SET
    source_table = EXCLUDED.source_table,
    object_type = EXCLUDED.object_type,
    search_text_cols = EXCLUDED.search_text_cols,
    filter_map = EXCLUDED.filter_map,
    payload_map = EXCLUDED.payload_map,
    enabled = EXCLUDED.enabled;

-- 5. Backfill handover_items into search_index
INSERT INTO search_index (object_type, object_id, org_id, yacht_id, search_text, filters, payload, updated_at)
SELECT
    'handover_item'::text,
    h.id,
    h.yacht_id,  -- org_id = yacht_id in this schema
    h.yacht_id,
    CONCAT_WS(' ',
        COALESCE(h.summary, ''),
        COALESCE(h.entity_type, ''),
        COALESCE(h.section, ''),
        COALESCE(h.category, ''),
        COALESCE(h.action_summary, ''),
        'handover shift report notes'  -- Literal token for search matching
    ) AS search_text,
    jsonb_strip_nulls(jsonb_build_object(
        'status', h.status,
        'entity_type', h.entity_type,
        'section', h.section,
        'priority', h.priority,
        'category', h.category,
        'is_critical', h.is_critical
    )) AS filters,
    jsonb_strip_nulls(jsonb_build_object(
        'summary', h.summary,
        'entity_type', h.entity_type,
        'section', h.section,
        'status', h.status,
        'priority', h.priority,
        'entity_id', h.entity_id,
        'category', h.category,
        'is_critical', h.is_critical,
        'action_summary', h.action_summary
    )) AS payload,
    NOW()
FROM handover_items h
WHERE h.yacht_id IS NOT NULL
  AND h.deleted_at IS NULL
ON CONFLICT (object_type, object_id) DO UPDATE SET
    search_text = EXCLUDED.search_text,
    filters = EXCLUDED.filters,
    payload = EXCLUDED.payload,
    updated_at = NOW();

COMMIT;
```

### Verification Queries

```sql
-- Check indexed count (should match handover_items with deleted_at IS NULL)
SELECT
    (SELECT COUNT(*) FROM handover_items WHERE deleted_at IS NULL) as source_count,
    (SELECT COUNT(*) FROM search_index WHERE object_type = 'handover_item') as indexed_count;

-- Test search for handover content
SET pg_trgm.similarity_threshold = 0.15;
SELECT object_type, payload->>'summary' as summary, payload->>'category' as category
FROM search_index
WHERE object_type = 'handover_item'
  AND search_text % 'handover'
ORDER BY similarity(search_text, 'handover') DESC
LIMIT 5;

-- Verify triggers exist
SELECT tgname, relname
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
WHERE relname = 'handover_items' AND tgname LIKE 'trg_spq_%';
```

### Config File Updated

`apps/api/config/projection.yaml` - Updated mapping:

```yaml
handover_items:
  source_table: handover_items
  object_type: handover_item
  search_text:
    - field: summary
      cast: text
    - field: entity_type
      cast: text
    - field: section
      cast: text
    - field: category
      cast: text
    - field: action_summary
      cast: text
    - literal: "handover shift report notes"
  filters:
    status: status
    entity_type: entity_type
    section: section
    priority: priority
    category: category
    is_critical: is_critical
    requires_action: requires_action
  payload:
    summary: summary
    entity_type: entity_type
    entity_id: entity_id
    section: section
    status: status
    priority: priority
    category: category
    is_critical: is_critical
    requires_action: requires_action
    action_summary: action_summary
```

---

## Python Backend Code Updated

### 1. `apps/api/handlers/handover_handlers.py`

**Changes:**
- Table changed: `pms_handover` → `handover_items`
- Column changed: `summary_text` → `summary`
- Column changed: `added_at` → `created_at`
- Added new parameters: `section`, `is_critical`, `requires_action`, `action_summary`, `entity_url`
- Added new methods: `edit_handover_item_execute`, `export_handover_execute`, `regenerate_handover_summary_execute`

**New Method Signatures:**

```python
async def add_to_handover_execute(
    self,
    entity_type: str,
    entity_id: str,
    summary: str,           # Was: summary_text
    category: str,
    yacht_id: str,
    user_id: str,
    priority: str = "normal",
    section: Optional[str] = None,        # NEW
    is_critical: bool = False,            # NEW
    requires_action: bool = False,        # NEW
    action_summary: Optional[str] = None, # NEW
    entity_url: Optional[str] = None      # NEW
) -> Dict

async def edit_handover_item_execute(
    self,
    item_id: str,           # Was: handover_id + section_id
    yacht_id: str,
    user_id: str,
    summary: Optional[str] = None,
    category: Optional[str] = None,
    is_critical: Optional[bool] = None,
    requires_action: Optional[bool] = None,
    action_summary: Optional[str] = None
) -> Dict

async def export_handover_execute(
    self,
    yacht_id: str,
    user_id: str,
    department: Optional[str] = None,     # Replaces handover_id
    export_type: str = "pdf"
) -> Dict

async def regenerate_handover_summary_execute(
    self,
    yacht_id: str,
    user_id: str,
    department: Optional[str] = None      # Replaces handover_id
) -> Dict
```

### 2. `apps/api/services/handover_export_service.py`

**Changes:**
- Removed `handover_drafts` table dependency (table was dropped)
- `draft_id` in `handover_exports` is now nullable
- Updated `HandoverItem` dataclass with new fields
- Updated HTML generation to show `is_critical` and `requires_action` badges

### 3. `apps/api/config/projection.yaml`

**Changes:**
- Added `category`, `action_summary` to `search_text`
- Added `category`, `is_critical`, `requires_action` to `filters`
- Added `category`, `is_critical`, `requires_action`, `action_summary` to `payload`
- Updated `promoted_facets` section: replaced `handovers` domain with `handover_items`

---

## TypeScript Frontend Code Updated

### 1. `apps/web/src/lib/microactions/handlers/handover.ts`

- `addToHandover`: Inserts directly into `handover_items` (no parent container)
- `exportHandover`: Creates `handover_exports` record with department filter
- `editHandoverSection`: Uses `item_id` instead of `handover_id` + `section_id`
- `regenerateHandoverSummary`: Generates summary from yacht's items (no parent record)

### 2. `apps/web/src/lib/action-router/dispatchers.ts`

- `editHandoverSection`: Updated to query/update `handover_items`

---

## Test Files Updated

| File | Changes |
|------|---------|
| `tests/e2e/microactions/cluster_05_handover.spec.ts` | Complete rewrite - tests now work |
| `tests/e2e/user-flows/handover-flow.spec.ts` | Uses `handover_items`, `item_id` |
| `tests/helpers/supabase_tenant.ts` | `getHandoverItems()` uses `handover_items` |
| `tests/helpers/test-data-discovery.ts` | Discovery uses `handover_items` |
| `tests/e2e/schema_truth_map.ts` | Updated known tables list |
| `scripts/check_action_test_data.js` | Uses `handover_items` |
| `scripts/get_action_context.js` | Uses `handover_items` |

---

## Deployment Checklist

- [x] SQL migration executed in Supabase
- [x] F1 Search triggers and projection_map updated
- [x] TypeScript frontend code updated
- [x] Python backend handlers updated
- [x] Test files updated
- [ ] **Deploy Python backend (pipeline-core) to Render**
- [ ] Verify API endpoints work with new schema
