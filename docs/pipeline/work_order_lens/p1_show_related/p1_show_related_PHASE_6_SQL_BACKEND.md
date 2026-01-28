# Work Order Lens P1: Show Related — PHASE 6: SQL BACKEND

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Define the **exact SQL queries** and **backend implementation** for Show Related feature.

---

## Query Implementation

### Query 1: Related Parts (FK Join)

```sql
-- Get parts linked to work order via pms_work_order_parts
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
ORDER BY p.name ASC
LIMIT 10;
```

**Indexes Used:**
- `pms_work_order_parts(work_order_id, yacht_id)`
- `pms_parts(id)`

---

### Query 2: Related Manuals (via Equipment)

```sql
-- Get manuals linked to same equipment as work order
SELECT
  d.id AS entity_id,
  'manual' AS entity_type,
  d.title,
  e.name AS subtitle,
  ARRAY['FK:equipment']::TEXT[] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE wo.id = :work_order_id
  AND d.doc_type = 'manual'
  AND wo.yacht_id = :yacht_id
  AND d.yacht_id = :yacht_id
ORDER BY d.title ASC
LIMIT 10;
```

**Indexes Used:**
- `pms_work_orders(id, yacht_id)`
- `pms_equipment(id)`
- `pms_documents(equipment_id, doc_type, yacht_id)`

---

### Query 3: Previous Work Orders (Same Equipment)

```sql
-- Get other work orders on same equipment
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
ORDER BY wo2.created_at DESC
LIMIT 10;
```

**Indexes Used:**
- `pms_work_orders(equipment_id, yacht_id, deleted_at)`

---

### Query 4: Related Handovers (via Equipment)

```sql
-- Get handovers linked to same equipment
SELECT
  d.id AS entity_id,
  'handover' AS entity_type,
  d.title,
  e.name AS subtitle,
  ARRAY['FK:equipment']::TEXT[] AS match_reasons,
  90 AS weight
FROM pms_work_orders wo
JOIN pms_equipment e ON e.id = wo.equipment_id
JOIN pms_documents d ON d.equipment_id = e.id
WHERE wo.id = :work_order_id
  AND d.doc_type = 'handover'
  AND wo.yacht_id = :yacht_id
  AND d.yacht_id = :yacht_id
ORDER BY d.created_at DESC
LIMIT 10;
```

**Indexes Used:** Same as Query 2

---

### Query 5: Related Attachments (FK Join)

```sql
-- Get attachments directly linked to work order
SELECT
  d.id AS entity_id,
  'attachment' AS entity_type,
  d.title,
  COALESCE(d.mime_type, 'unknown') AS subtitle,
  ARRAY['FK:wo_attachment']::TEXT[] AS match_reasons,
  100 AS weight
FROM pms_work_order_attachments woa
JOIN pms_documents d ON d.id = woa.document_id
WHERE woa.work_order_id = :work_order_id
  AND woa.yacht_id = :yacht_id
ORDER BY woa.created_at DESC
LIMIT 10;
```

**Indexes Used:**
- `pms_work_order_attachments(work_order_id, yacht_id)`
- `pms_documents(id)`

---

### Query 6: Explicit Links (User-Created)

```sql
-- Get manually added links
SELECT
  el.target_entity_id AS entity_id,
  el.target_entity_type AS entity_type,
  COALESCE(el.note, 'Manually linked') AS title,
  TO_CHAR(el.created_at, 'YYYY-MM-DD') AS subtitle,
  ARRAY['explicit_link']::TEXT[] AS match_reasons,
  70 AS weight
FROM pms_entity_links el
WHERE el.source_entity_type = 'work_order'
  AND el.source_entity_id = :work_order_id
  AND el.yacht_id = :yacht_id
ORDER BY el.created_at DESC;
```

**Indexes Used:**
- `pms_entity_links(source_entity_type, source_entity_id, yacht_id)`

---

## Handler Implementation (Python)

### list_related() Method

```python
async def list_related(self, yacht_id: str, entity_type: str, entity_id: str, user_id: str) -> Dict:
    # 1. Validate entity_type
    if entity_type != "work_order":
        raise HTTPException(400, detail="Invalid entity_type. Only 'work_order' supported.")

    # 2. Verify work order exists
    try:
        wo = self.db.table("pms_work_orders") \
            .select("id,equipment_id,fault_id") \
            .eq("id", entity_id) \
            .eq("yacht_id", yacht_id) \
            .single() \
            .execute()
    except Exception as e:
        if "PGRST116" in str(e) or "0 rows" in str(e):
            raise HTTPException(404, detail="Work order not found")
        raise

    # 3. Execute queries in parallel (or sequentially if simple)
    parts = await self._query_related_parts(entity_id, yacht_id)
    attachments = await self._query_related_attachments(entity_id, yacht_id)
    explicit_links = await self._query_explicit_links(entity_id, yacht_id)

    # Only query equipment-based if equipment_id exists
    manuals = []
    handovers = []
    previous_work = []
    if wo.data.get("equipment_id"):
        manuals = await self._query_related_manuals(entity_id, yacht_id)
        handovers = await self._query_related_handovers(entity_id, yacht_id)
        previous_work = await self._query_previous_work(entity_id, yacht_id)

    # 4. Merge explicit links into respective groups
    merged = self._merge_explicit_links(
        parts, manuals, previous_work, handovers, attachments, explicit_links
    )

    # 5. Build response groups
    groups = [
        self._build_group("parts", "Parts", merged["parts"]),
        self._build_group("manuals", "Manuals", merged["manuals"]),
        self._build_group("previous_work", "Previous Work Orders", merged["previous_work"]),
        self._build_group("handovers", "Handovers", merged["handovers"]),
        self._build_group("attachments", "Attachments", merged["attachments"]),
    ]

    # 6. Check if user can add links (HOD or manager)
    add_enabled = await self._is_hod_or_manager(user_id, yacht_id)

    return {
        "status": "success",
        "groups": groups,
        "add_related_enabled": add_enabled,
        "missing_signals": []
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

async def _build_group(self, group_key: str, label: str, items: List[Dict]) -> Dict:
    """Build a group object for response."""
    return {
        "group_key": group_key,
        "label": label,
        "count": len(items),
        "items": items
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
    """Check if user is HOD or manager."""
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
```

---

## add_entity_link() Method

```python
async def add_entity_link(
    self, yacht_id, source_entity_type, source_entity_id,
    target_entity_type, target_entity_id, link_type, note, user_id
) -> Dict:
    # 1. Validate entity types
    valid_types = ["work_order", "part", "manual", "handover", "attachment", "equipment"]
    if source_entity_type not in valid_types or target_entity_type not in valid_types:
        raise HTTPException(400, detail="Invalid entity type")

    # 2. Verify source entity exists
    source_table = self._get_table_for_entity_type(source_entity_type)
    try:
        source = self.db.table(source_table).select("id").eq("id", source_entity_id).eq("yacht_id", yacht_id).single().execute()
    except:
        raise HTTPException(404, detail="Source entity not found")

    # 3. Verify target entity exists
    target_table = self._get_table_for_entity_type(target_entity_type)
    try:
        target = self.db.table(target_table).select("id").eq("id", target_entity_id).eq("yacht_id", yacht_id).single().execute()
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

## Next Phase

**PHASE 7: RLS MATRIX** - Verify all RLS policies for related queries.

---

**SQL BACKEND STATUS:** ✅ DEFINED
