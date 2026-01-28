# Work Order Lens P1: Show Related — PHASE 1: SCOPE

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Feature Overview

**Problem:** Engineers need to see all related entities (parts, manuals, previous work, handovers, attachments) when working on a work order, but this context is scattered across multiple tables and relationships.

**Solution:** Deterministic "Show Related" feature that aggregates related entities via FK joins and explicit links, with clear match reasons for each result.

**User Value:**
- Faster troubleshooting (see previous work on same equipment)
- Complete parts context (see all parts used for this WO)
- Document discovery (find manuals/handovers related to equipment)
- Audit trail (know why each item is related)

---

## Entity Groups (5 Groups)

### 1. Parts
**Source:** `pms_work_order_parts` → `pms_parts`
**Match Reasons:**
- `FK:wo_part` - Part is linked to this work order via work_order_parts join table
- `explicit_link` - Manually added via "Add Related"

### 2. Manuals
**Source:** `pms_documents` where `doc_type = 'manual'`
**Match Reasons:**
- `FK:equipment` - Manual is linked to the same equipment as this WO
- `explicit_link` - Manually added

### 3. Previous Work
**Source:** `pms_work_orders` (other WOs)
**Match Reasons:**
- `same_equipment` - WO on the same equipment_id
- `same_fault` - WO created from the same fault_id
- `explicit_link` - Manually added

### 4. Handovers
**Source:** `pms_documents` where `doc_type = 'handover'`
**Match Reasons:**
- `FK:equipment` - Handover mentions the same equipment
- `mentions:WO-123` - Handover description mentions this WO number (optional, Phase 2)
- `explicit_link` - Manually added

### 5. Attachments
**Source:** `pms_work_order_attachments` → `pms_documents`
**Match Reasons:**
- `FK:wo_attachment` - Attachment is linked to this work order
- `explicit_link` - Manually added

---

## Actions

### Action 1: view_related_entities (READ)

**Purpose:** Retrieve all related entities for a given entity (initially work orders only)

**Signature:**
```python
{
  "action": "view_related_entities",
  "context": {"yacht_id": "uuid"},
  "payload": {
    "entity_type": "work_order",  # Required: "work_order" (extensible to others)
    "entity_id": "uuid"            # Required: Work order ID
  }
}
```

**Response:**
```python
{
  "status": "success",
  "groups": [
    {
      "group_key": "parts",
      "label": "Parts",
      "count": 3,
      "items": [
        {
          "entity_type": "part",
          "entity_id": "uuid",
          "title": "MTU Oil Filter",
          "subtitle": "Part #: 12345-ABC",
          "match_reasons": ["FK:wo_part"],
          "open_action": "focus"  # Frontend action hint
        }
      ]
    },
    {
      "group_key": "previous_work",
      "label": "Previous Work Orders",
      "count": 2,
      "items": [...]
    }
  ],
  "add_related_enabled": true,  # HOD/manager only
  "missing_signals": []          # Optional: hints for frontend
}
```

**Registry:**
- `domain`: "work_orders"
- `variant`: READ
- `allowed_roles`: ["crew", "chief_engineer", "chief_officer", "captain", "manager"]
- `required_fields`: ["yacht_id", "entity_type", "entity_id"]
- `search_keywords`: ["related", "context", "parts", "manuals", "previous", "attachments", "handovers"]

### Action 2: add_entity_link (MUTATE)

**Purpose:** Explicitly link two entities (HOD/manager only)

**Signature:**
```python
{
  "action": "add_entity_link",
  "context": {"yacht_id": "uuid"},
  "payload": {
    "source_entity_type": "work_order",  # Required
    "source_entity_id": "uuid",          # Required
    "target_entity_type": "manual",      # Required: "part", "manual", "work_order", "handover", "attachment"
    "target_entity_id": "uuid",          # Required
    "link_type": "explicit",             # Default: "explicit"
    "note": "Added for reference"        # Optional
  }
}
```

**Response:**
```python
{
  "status": "success",
  "link_id": "uuid",
  "created_at": "2026-01-28T12:00:00Z"
}
```

**Registry:**
- `domain`: "work_orders"
- `variant`: MUTATE
- `allowed_roles`: ["chief_engineer", "chief_officer", "captain", "manager"]
- `required_fields`: ["yacht_id", "source_entity_type", "source_entity_id", "target_entity_type", "target_entity_id", "link_type"]
- `search_keywords`: ["add", "link", "related", "reference", "evidence"]

---

## Endpoints

### GET /v1/related

**Query Params:**
- `entity_type` (required): "work_order"
- `entity_id` (required): UUID

**Headers:**
- `Authorization`: Bearer JWT
- `X-Yacht-ID`: UUID (or extracted from JWT)

**Response:** See `view_related_entities` response above

**Error Codes:**
- 400: Invalid entity_type or missing params
- 403: Forbidden (wrong yacht or role)
- 404: Entity not found
- 500: Unexpected error (should not happen; map to 4xx)

### POST /v1/related/add

**Body:**
```json
{
  "yacht_id": "uuid",
  "source_entity_type": "work_order",
  "source_entity_id": "uuid",
  "target_entity_type": "manual",
  "target_entity_id": "uuid",
  "link_type": "explicit",
  "note": "Optional context"
}
```

**Response:** See `add_entity_link` response above

**Error Codes:**
- 400: Invalid entity types or missing required fields
- 403: Forbidden (crew or wrong yacht)
- 404: Source or target entity not found
- 409: Link already exists (duplicate)
- 500: Unexpected error (should not happen)

---

## Role Matrix

| Action | Crew | HOD (chief_engineer/chief_officer) | Captain | Manager |
|--------|------|-------------------------------------|---------|---------|
| view_related_entities | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 200 |
| add_entity_link | ❌ 403 | ✅ 200 | ✅ 200 | ✅ 200 |

---

## Data Flow

### View Related (GET)

```
User clicks "Show Related" on WO detail
  ↓
Frontend: GET /v1/related?entity_type=work_order&entity_id={id}
  ↓
Backend: list_related(yacht_id, entity_type, entity_id)
  ↓
1. FK Joins (high priority):
   - pms_work_order_parts → pms_parts
   - pms_work_orders → pms_equipment → pms_documents (manuals)
   - pms_work_orders → pms_fault → pms_work_orders (previous work)
   - pms_work_order_attachments → pms_documents
  ↓
2. Explicit Links (medium priority):
   - pms_entity_links where source_entity_id = {id}
  ↓
3. Merge & Rank:
   - Group by entity_type
   - Sort by match_reason weight (FK > explicit > mentions)
   - Limit to top 10 per group
  ↓
4. Build Response:
   - groups[] with items[], match_reasons[], counts
   - add_related_enabled = is_hod() or is_manager()
  ↓
Frontend: Render groups with reason chips
```

### Add Link (POST)

```
User clicks "Add Related" → selects entity
  ↓
Frontend: POST /v1/related/add {source, target, link_type}
  ↓
Backend: add_entity_link(yacht_id, ...)
  ↓
1. Validate: source and target exist, same yacht
2. Check: RLS policy (HOD/manager only)
3. Insert: pms_entity_links row
4. Audit: pms_audit_log entry (signature: {})
  ↓
Frontend: Refresh related view
```

---

## Non-Functional Requirements

### Performance
- P95 latency <500ms for GET `/v1/related`
- Limit results to top 10 per group (prevent unbounded queries)
- Use indexed FK columns (entity_id, yacht_id)

### Security
- All queries scoped to `yacht_id = get_user_yacht_id()`
- RLS policies enforced on all tables
- No presigned URLs for storage (metadata only)
- Role gating via action registry + RLS

### Reliability
- Zero 500 errors (all client errors → 4xx)
- Deterministic results (no randomness)
- Idempotent operations (GET, POST with duplicate check)

---

## Out of Scope (Future Phases)

- Full-text search across WO descriptions
- Similarity scoring beyond deterministic FK joins
- Automatic link suggestions (ML/AI)
- Cross-yacht entity discovery
- File content analysis (OCR, PDF parsing)

---

## Next Phase

**PHASE 2: DB TRUTH** - Map exact FK relationships, table schemas, and RLS policies.

---

**SCOPE STATUS:** ✅ DEFINED
