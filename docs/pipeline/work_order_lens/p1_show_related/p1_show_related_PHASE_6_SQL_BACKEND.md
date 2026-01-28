# Work Order Lens P1: Show Related — PHASE 6: SQL BACKEND

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Define the **exact SQL queries** and **backend implementation** for Show Related feature.

---

## Database Truth (Schema Clarifications)

**Canonical Tables (Confirmed in PHASE_2):**

1. **pms_work_order_notes** - Canonical source for all work order notes
2. **doc_metadata** - ONLY canonical source for attachments, photos, manuals, handovers
   - ⚠️ **pms_work_order_attachments does NOT exist** - do not reference this table in code/tests
3. **handover_exports** - Exists but is EMPTY in production (Week-1 queries will return zero results)

**Hidden FKs (Optional in V1):**
- `doc_metadata.equipment_ids[]` - Array of equipment UUIDs
- `doc_metadata.metadata.part_ids[]` - JSONB array of part references

**V1 Decision:** Hidden FK support is OPTIONAL. If arrays are present but not indexed, surface `missing_signals: ["no_equipment_array_index"]` and skip JSONB scans to avoid performance issues.

**Limitations to Call Out:**
- Handover queries may return empty groups with `missing_signals: ["handover_exports_empty"]`
- JSONB/array FK queries gated behind index existence check
- doc_metadata RLS may hide some titles depending on tenant configuration

---

## Query Implementation

### Query 1: Related Parts (FK Join)

```sql
-- Get parts linked to work order via pms_work_order_parts
-- Sort: Recent usage first (wop.created_at DESC), then by part_number
SELECT
  p.id AS entity_id,
  'part' AS entity_type,
  p.name AS title,
  'Part #: ' || COALESCE(p.part_number, 'N/A') AS subtitle,
  ARRAY['FK:wo_part']::TEXT[] AS match_reasons,
  100 AS weight
FROM pms_work_order_parts wop
JOIN pms_parts p ON p.id = wop.part_id
WHERE wop.work_order_id = :work_order_id
  AND wop.yacht_id = :yacht_id
  AND wop.deleted_at IS NULL
  AND p.yacht_id = :yacht_id  -- Explicit yacht filter on join table
ORDER BY wop.created_at DESC, p.part_number ASC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:**
- `pms_work_order_parts(work_order_id, yacht_id)`
- `pms_parts(id)`

---

### Query 2: Related Manuals (via Equipment)

```sql
-- Get manuals linked to same equipment as work order via doc_metadata
-- Sort: Last updated DESC, then title ASC
SELECT
  d.id AS entity_id,
  'manual' AS entity_type,
  d.filename AS title,
  e.name AS subtitle,
  ARRAY['FK:equipment']::TEXT[] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN doc_metadata d ON d.equipment_ids @> ARRAY[e.id]::uuid[]
WHERE wo.id = :work_order_id
  AND d.doc_type = 'manual'
  AND wo.yacht_id = :yacht_id
  AND e.yacht_id = :yacht_id
  AND d.yacht_id = :yacht_id
  AND d.deleted_at IS NULL
ORDER BY d.updated_at DESC, d.filename ASC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:**
- `pms_work_orders(id, yacht_id)`
- `pms_equipment(id)`
- `doc_metadata(equipment_ids)` - GIN index (optional, see Migration 2)

**⚠️ V1 Note:** If `equipment_ids[]` GIN index does not exist, skip this query and add `missing_signals: ["no_equipment_array_index"]` to response.

---

### Query 3: Previous Work Orders (Same Equipment)

```sql
-- Get other work orders on same equipment
-- Sort: Last activity DESC (fallback to completed_at, then created_at)
SELECT
  wo2.id AS entity_id,
  'work_order' AS entity_type,
  wo2.number || ': ' || wo2.title AS title,
  TO_CHAR(wo2.created_at, 'YYYY-MM-DD') AS subtitle,
  ARRAY['same_equipment']::TEXT[] AS match_reasons,
  80 AS weight
FROM pms_work_orders wo1
JOIN pms_work_orders wo2 ON wo2.equipment_id = wo1.equipment_id
WHERE wo1.id = :work_order_id
  AND wo2.id != :work_order_id
  AND wo2.deleted_at IS NULL
  AND wo1.yacht_id = :yacht_id
  AND wo2.yacht_id = :yacht_id
ORDER BY
  COALESCE(wo2.last_activity_at, wo2.completed_at, wo2.created_at) DESC NULLS LAST,
  wo2.created_at DESC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:**
- `pms_work_orders(equipment_id, yacht_id, deleted_at)`

---

### Query 4: Related Handovers (via Equipment)

**⚠️ V1 Note:** `handover_exports` exists but is EMPTY in production. This query will return zero results until handover data is populated. Include `missing_signals: ["handover_exports_empty"]` in response.

```sql
-- Get handovers linked to same equipment via doc_metadata
-- Sort: Created at DESC (most recent handovers first)
SELECT
  d.id AS entity_id,
  'handover' AS entity_type,
  d.filename AS title,
  e.name AS subtitle,
  ARRAY['FK:equipment']::TEXT[] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN doc_metadata d ON d.equipment_ids @> ARRAY[e.id]::uuid[]
WHERE wo.id = :work_order_id
  AND d.doc_type = 'handover'
  AND wo.yacht_id = :yacht_id
  AND e.yacht_id = :yacht_id
  AND d.yacht_id = :yacht_id
  AND d.deleted_at IS NULL
ORDER BY d.created_at DESC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:** Same as Query 2 (doc_metadata equipment_ids GIN - optional)

---

### Query 5: Related Attachments (FK Join)

**⚠️ Schema Truth:** `pms_work_order_attachments` does NOT exist. Use `doc_metadata` with JSONB metadata filter.

```sql
-- Get attachments directly linked to work order via doc_metadata
-- Sort: Uploaded at DESC (most recent uploads first)
SELECT
  d.id AS entity_id,
  'attachment' AS entity_type,
  d.filename AS title,
  COALESCE(d.mime_type, 'unknown') AS subtitle,
  ARRAY['FK:wo_attachment']::TEXT[] AS match_reasons,
  100 AS weight
FROM doc_metadata d
WHERE d.metadata @> jsonb_build_object('entity_type', 'work_order', 'entity_id', :work_order_id)
  AND d.yacht_id = :yacht_id
  AND d.deleted_at IS NULL
ORDER BY d.uploaded_at DESC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:**
- `doc_metadata(metadata)` - GIN jsonb_path_ops (optional, see Migration 2)

**⚠️ V1 Note:** If `metadata` GIN index does not exist, skip this query and add `missing_signals: ["no_metadata_jsonb_index"]` to response.

---

### Query 6: Explicit Links (User-Created)

```sql
-- Get manually added links (HOD/manager created)
-- Sort: Created at DESC (most recent links first)
SELECT
  el.target_entity_id AS entity_id,
  el.target_entity_type AS entity_type,
  COALESCE(el.note, 'Manually linked') AS title,
  TO_CHAR(el.created_at, 'YYYY-MM-DD') AS subtitle,
  ARRAY['explicit_link:' || el.link_type]::TEXT[] AS match_reasons,
  70 AS weight
FROM pms_entity_links el
WHERE el.source_entity_type = 'work_order'
  AND el.source_entity_id = :work_order_id
  AND el.yacht_id = :yacht_id
ORDER BY el.created_at DESC
LIMIT :limit;  -- Default 20, max 50
```

**Indexes Used:**
- `pms_entity_links(source_entity_type, source_entity_id, yacht_id)` (created in Migration 3)

---

## Handler Implementation (Python)

### list_related() Method

```python
async def list_related(
    self, yacht_id: str, entity_type: str, entity_id: str,
    user_id: str, limit: int = 20
) -> Dict:
    # 1. Validate entity_type
    if entity_type not in ["work_order", "equipment", "part"]:
        raise HTTPException(400, detail="Invalid entity_type")

    # 2. Validate limit (default 20, max 50)
    if limit <= 0:
        raise HTTPException(400, detail="limit must be > 0")
    if limit > 50:
        raise HTTPException(400, detail="limit cannot exceed 50")

    # 3. Verify work order exists (and cross-yacht check)
    try:
        wo = self.db.table("pms_work_orders") \
            .select("id,equipment_id,fault_id") \
            .eq("id", entity_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .single() \
            .execute()
    except Exception as e:
        if "PGRST116" in str(e) or "0 rows" in str(e):
            # Return 404 for both not found AND cross-yacht (privacy)
            raise HTTPException(404, detail="Work order not found")
        raise

    # 4. Check for optional features (indexes, data availability)
    missing_signals = []
    has_equipment_array_index = await self._check_gin_index_exists("doc_metadata", "equipment_ids")
    has_metadata_jsonb_index = await self._check_gin_index_exists("doc_metadata", "metadata")

    # 5. Execute queries (with limit and conditional execution)
    parts = await self._query_related_parts(entity_id, yacht_id, limit)
    explicit_links = await self._query_explicit_links(entity_id, yacht_id, limit)

    # Conditionally query based on index availability
    manuals = []
    handovers = []
    attachments = []
    previous_work = []

    if wo.data.get("equipment_id"):
        if has_equipment_array_index:
            manuals = await self._query_related_manuals(entity_id, yacht_id, limit)
            handovers = await self._query_related_handovers(entity_id, yacht_id, limit)
        else:
            missing_signals.append("no_equipment_array_index")

        previous_work = await self._query_previous_work(entity_id, yacht_id, limit)

    if has_metadata_jsonb_index:
        attachments = await self._query_related_attachments(entity_id, yacht_id, limit)
    else:
        missing_signals.append("no_metadata_jsonb_index")

    # Mark handovers as potentially empty
    if len(handovers) == 0:
        missing_signals.append("handover_exports_empty")

    # 6. Merge explicit links into respective groups
    merged = self._merge_explicit_links(
        parts, manuals, previous_work, handovers, attachments, explicit_links
    )

    # 7. Apply hard cap on total items (performance guardrail)
    total_items = sum(len(items) for items in merged.values())
    if total_items > 100:
        # Truncate proportionally to maintain distribution
        merged = self._truncate_to_total_cap(merged, max_total=100)
        missing_signals.append("total_items_capped_at_100")

    # 8. Build response groups with metadata
    groups = [
        self._build_group("parts", "Parts", merged["parts"], limit),
        self._build_group("manuals", "Manuals", merged["manuals"], limit),
        self._build_group("previous_work", "Previous Work Orders", merged["previous_work"], limit),
        self._build_group("handovers", "Handovers", merged["handovers"], limit),
        self._build_group("attachments", "Attachments", merged["attachments"], limit),
    ]

    # 9. Check if user can add links (HOD, chief, captain, manager)
    add_enabled = await self._is_hod_or_manager(user_id, yacht_id)

    # 10. Count groups with items
    group_counts = {g["group_key"]: g["count"] for g in groups if g["count"] > 0}

    return {
        "status": "success",
        "groups": groups,
        "add_related_enabled": add_enabled,  # Explicit in every response
        "group_counts": group_counts,  # Summary for logging/analytics
        "missing_signals": missing_signals,
        "metadata": {
            "limit_per_group": limit,
            "total_items": sum(g["count"] for g in groups)
        }
    }
```

### Helper Methods

```python
async def _query_related_parts(self, work_order_id: str, yacht_id: str) -> List[Dict]:
    """Query parts linked to work order."""
    result = self.db.rpc("get_related_parts", {
        "p_work_order_id": work_order_id,
        "p_yacht_id": yacht_id
    }).execute()
    return result.data or []

async def _build_group(self, group_key: str, label: str, items: List[Dict], limit: int) -> Dict:
    """Build a group object for response with metadata."""
    return {
        "group_key": group_key,
        "label": label,
        "count": len(items),
        "items": items,
        "limit": limit,
        "has_more": False  # V1: Always false (pagination Week 2+)
    }

async def _merge_explicit_links(self, parts, manuals, previous_work, handovers, attachments, explicit_links):
    """Merge explicit links into appropriate groups based on target_entity_type."""
    for link in explicit_links:
        target_type = link["entity_type"]
        if target_type == "part":
            parts.append(link)
        elif target_type == "manual":
            manuals.append(link)
        elif target_type == "work_order":
            previous_work.append(link)
        elif target_type == "handover":
            handovers.append(link)
        elif target_type == "attachment":
            attachments.append(link)

    # Deduplicate by entity_id, merge match_reasons
    return {
        "parts": self._deduplicate(parts),
        "manuals": self._deduplicate(manuals),
        "previous_work": self._deduplicate(previous_work),
        "handovers": self._deduplicate(handovers),
        "attachments": self._deduplicate(attachments),
    }

async def _deduplicate(self, items: List[Dict]) -> List[Dict]:
    """Deduplicate items by entity_id, merging match_reasons."""
    seen = {}
    for item in items:
        eid = item["entity_id"]
        if eid in seen:
            # Merge match_reasons
            seen[eid]["match_reasons"] = list(set(seen[eid]["match_reasons"] + item["match_reasons"]))
            # Keep highest weight
            seen[eid]["weight"] = max(seen[eid]["weight"], item["weight"])
        else:
            seen[eid] = item
    return list(seen.values())

async def _is_hod_or_manager(self, user_id: str, yacht_id: str) -> bool:
    """Check if user is HOD or manager (can add entity links)."""
    result = self.db.table("auth_users_roles") \
        .select("role") \
        .eq("user_id", user_id) \
        .eq("yacht_id", yacht_id) \
        .eq("is_active", True) \
        .execute()

    if not result.data:
        return False

    role = result.data[0]["role"]
    return role in ["chief_engineer", "chief_officer", "captain", "manager"]

async def _check_gin_index_exists(self, table_name: str, column_name: str) -> bool:
    """
    Check if GIN index exists on table column.
    Performance guardrail: Only run JSONB/array queries if indexed.
    """
    result = self.db.rpc("check_gin_index", {
        "p_table_name": table_name,
        "p_column_name": column_name
    }).execute()
    return result.data[0]["exists"] if result.data else False

async def _truncate_to_total_cap(self, merged: Dict[str, List], max_total: int) -> Dict[str, List]:
    """
    Performance guardrail: Hard cap total items across all groups.
    Truncates proportionally to maintain distribution.
    """
    total_items = sum(len(items) for items in merged.values())
    if total_items <= max_total:
        return merged

    # Calculate proportion for each group
    ratio = max_total / total_items
    truncated = {}
    for key, items in merged.items():
        new_limit = max(1, int(len(items) * ratio))  # At least 1 item if group has any
        truncated[key] = items[:new_limit]

    return truncated
```

---

## add_entity_link() Method

```python
async def add_entity_link(
    self, yacht_id, source_entity_type, source_entity_id,
    target_entity_type, target_entity_id, link_type, note, user_id
) -> Dict:
    # 1. Validate entity types
    valid_types = ["work_order", "part", "manual", "handover", "attachment", "equipment", "fault"]
    if source_entity_type not in valid_types or target_entity_type not in valid_types:
        raise HTTPException(400, detail="Invalid entity type")

    # 2. Validate link_type enum
    valid_link_types = ["related", "reference", "evidence", "manual"]
    if link_type not in valid_link_types:
        raise HTTPException(400, detail=f"Invalid link_type. Must be one of: {', '.join(valid_link_types)}")

    # 3. Prevent self-links
    if source_entity_type == target_entity_type and source_entity_id == target_entity_id:
        raise HTTPException(400, detail="Cannot create link to self (source == target)")

    # 4. Validate note length
    if note and len(note) > 500:
        raise HTTPException(400, detail="Note cannot exceed 500 characters")

    # 5. Verify source entity exists (and cross-yacht check via yacht_id filter)
    source_table = self._get_table_for_entity_type(source_entity_type)
    try:
        source = self.db.table(source_table) \
            .select("id") \
            .eq("id", source_entity_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .single() \
            .execute()
    except:
        # Return 404 for both not found AND cross-yacht (privacy)
        raise HTTPException(404, detail="Source entity not found")

    # 6. Verify target entity exists (and cross-yacht check)
    target_table = self._get_table_for_entity_type(target_entity_type)
    try:
        target = self.db.table(target_table) \
            .select("id") \
            .eq("id", target_entity_id) \
            .eq("yacht_id", yacht_id) \
            .is_("deleted_at", "null") \
            .single() \
            .execute()
    except:
        raise HTTPException(404, detail="Target entity not found")

    # 4. Check for duplicate
    existing = self.db.table("pms_entity_links").select("id").match({
        "yacht_id": yacht_id,
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type,
        "target_entity_id": target_entity_id,
        "link_type": link_type
    }).execute()

    if existing.data:
        raise HTTPException(409, detail="Link already exists")

    # 5. Insert link
    link = self.db.table("pms_entity_links").insert({
        "yacht_id": yacht_id,
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type,
        "target_entity_id": target_entity_id,
        "link_type": link_type,
        "note": note,
        "created_by": user_id
    }).execute()

    link_id = link.data[0]["id"]

    # 6. Audit log
    await self._write_audit_log(yacht_id, user_id, "add_entity_link", link_id, {
        "source_entity_type": source_entity_type,
        "source_entity_id": source_entity_id,
        "target_entity_type": target_entity_type,
        "target_entity_id": target_entity_id
    })

    return {
        "status": "success",
        "link_id": link_id,
        "created_at": link.data[0]["created_at"]
    }
```

---

## Optional: Database Functions (Performance)

If queries are complex, create Postgres functions:

```sql
CREATE OR REPLACE FUNCTION public.get_related_parts(
  p_work_order_id UUID,
  p_yacht_id UUID
)
RETURNS TABLE (
  entity_id UUID,
  entity_type TEXT,
  title TEXT,
  subtitle TEXT,
  match_reasons TEXT[],
  weight INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.id,
    'part'::TEXT,
    p.name,
    'Part #: ' || COALESCE(p.part_number, 'N/A'),
    ARRAY['FK:wo_part']::TEXT[],
    100
  FROM pms_work_order_parts wop
  JOIN pms_parts p ON p.id = wop.part_id
  WHERE wop.work_order_id = p_work_order_id
    AND wop.yacht_id = p_yacht_id
  ORDER BY p.name ASC
  LIMIT 10;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
```

**Decision:** Only create DB functions if Python queries >500ms. Prefer app-level logic for flexibility.

---

## Performance Guardrails

**Hard Caps (Prevent Worst-Case Payloads):**

1. **Per-Group Limit:** Default 20, max 50 per group
   - Enforce 400 if `limit > 50` or `limit <= 0`

2. **Total Items Cap:** Max 100 items across all groups
   - If total exceeds 100, truncate proportionally
   - Add `missing_signals: ["total_items_capped_at_100"]`

3. **JSONB/Array Queries:** Only execute if GIN indexes exist
   - Check index existence before running `equipment_ids @>` or `metadata @>` queries
   - If index missing, skip query and add `missing_signals: ["no_equipment_array_index"]`

4. **No Unindexed Scans:** Gate all JSONB queries behind feature flag
   - See Migration 2 for optional GIN index definitions
   - EXPLAIN-driven: Only enable after profiling shows need

**Rationale:** Prevent accidental load spikes from missing indexes or unbounded queries.

---

## Caching Strategy

**3-Tier Caching:**

1. **In-Request Memoization** (dedupe within single request)
   - Merge explicit links with FK results
   - Deduplicate by entity_id, merge match_reasons

2. **Redis Cache** (60-120s TTL)
   - Key: `related:v1:{yacht_id}:{entity_type}:{entity_id}:{limit}`
   - Invalidate on `add_entity_link` (source entity only)
   - Never cache across `yacht_id` boundaries

3. **Materialized Views** (Optional, Week 2+)
   - Pre-compute FK relationships for hot paths
   - Refresh on UPDATE triggers

**Logging Fields (Structured):**
```json
{
  "timestamp": "2026-01-28T10:15:30Z",
  "action": "view_related_entities",
  "yacht_id": "uuid",
  "entity_type": "work_order",
  "entity_id": "uuid",
  "user_id": "uuid",
  "group_counts": {"parts": 5, "manuals": 2, "previous_work": 8},
  "ms_per_layer": {"parts_ms": 45, "manuals_ms": 32, "previous_work_ms": 78},
  "total_ms": 228,
  "cache_hit": false,
  "missing_signals": ["handover_exports_empty"]
}
```

**⚠️ Security:** Mask sensitive text (note contents, titles) in logs. Only log yacht_id, entity_id, and counts.

---

## Next Phase

**PHASE 7: RLS MATRIX** - Verify all RLS policies for related queries.

---

**SQL BACKEND STATUS:** ✅ DEFINED (with DB truth clarifications, sort orders, guardrails)
