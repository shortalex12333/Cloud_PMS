# Work Order Lens P1: Show Related — PHASE 5: SCENARIOS

**Feature:** Show Related Entities for Work Orders
**Date:** 2026-01-28

---

## Purpose

Define **test scenarios** and **acceptance criteria** for Docker tests and staging CI.

---

## Test Scenarios

### Scenario 1: VIEW Related - CREW Success
**Actor:** Crew
**Action:** view_related_entities
**Expected:** 200 with groups[]

**Given:**
- Crew user authenticated
- Work order WO-001 exists with yacht_id match
- WO-001 has 2 parts linked
- WO-001 equipment has 1 manual

**When:**
```
GET /v1/related?entity_type=work_order&entity_id=WO-001
Authorization: Bearer <crew_jwt>
```

**Then:**
- Status: 200
- Response includes groups: ["parts", "manuals", "previous_work", "handovers", "attachments"]
- parts.count = 2
- parts.items[0].match_reasons = ["FK:wo_part"]
- manuals.count = 1
- manuals.items[0].match_reasons = ["FK:equipment"]
- add_related_enabled = false (crew cannot add links)

---

### Scenario 2: VIEW Related - HOD Success
**Actor:** HOD (chief_engineer)
**Action:** view_related_entities
**Expected:** 200 with groups[] and add_related_enabled=true

**Given:**
- HOD user authenticated
- Work order WO-002 exists
- WO-002 has 3 parts, 1 manual, 2 previous WOs on same equipment

**When:**
```
GET /v1/related?entity_type=work_order&entity_id=WO-002
Authorization: Bearer <hod_jwt>
```

**Then:**
- Status: 200
- parts.count = 3
- manuals.count = 1
- previous_work.count = 2
- previous_work.items[].match_reasons = ["same_equipment"]
- add_related_enabled = true (HOD can add links)

---

### Scenario 3: VIEW Related - Cross-Yacht Forbidden
**Actor:** Crew from Yacht A
**Action:** view_related_entities for WO on Yacht B
**Expected:** 404

**Given:**
- Crew user from yacht_id = A
- Work order WO-003 exists on yacht_id = B

**When:**
```
GET /v1/related?entity_type=work_order&entity_id=WO-003
Authorization: Bearer <crew_yacht_a_jwt>
```

**Then:**
- Status: 404
- Response: `{"detail": "Work order not found"}`
- No data leak from Yacht B

---

### Scenario 4: VIEW Related - Invalid Entity Type
**Actor:** HOD
**Action:** view_related_entities with entity_type="invalid"
**Expected:** 400

**When:**
```
GET /v1/related?entity_type=invalid&entity_id=some-uuid
```

**Then:**
- Status: 400
- Response: `{"detail": "Invalid entity_type. Only 'work_order' supported."}`

---

### Scenario 5: VIEW Related - Missing Entity
**Actor:** HOD
**Action:** view_related_entities for non-existent WO
**Expected:** 404

**When:**
```
GET /v1/related?entity_type=work_order&entity_id=00000000-0000-0000-0000-000000000000
```

**Then:**
- Status: 404
- Response: `{"detail": "Work order not found"}`

---

### Scenario 6: ADD Link - HOD Success
**Actor:** HOD
**Action:** add_entity_link
**Expected:** 200 with link_id

**Given:**
- HOD authenticated
- Work order WO-001 exists
- Manual MAN-001 exists
- No existing link between them

**When:**
```
POST /v1/related/add
Body: {
  "yacht_id": "yacht-uuid",
  "source_entity_type": "work_order",
  "source_entity_id": "WO-001-uuid",
  "target_entity_type": "manual",
  "target_entity_id": "MAN-001-uuid",
  "link_type": "explicit",
  "note": "Reference manual for repair"
}
```

**Then:**
- Status: 200
- Response: `{"status": "success", "link_id": "uuid", "created_at": "2026-01-28..."}`
- Link persisted in pms_entity_links
- Audit log entry created

---

### Scenario 7: ADD Link - CREW Forbidden
**Actor:** Crew
**Action:** add_entity_link
**Expected:** 403

**When:**
```
POST /v1/related/add
Authorization: Bearer <crew_jwt>
Body: {same as Scenario 6}
```

**Then:**
- Status: 403
- Response: `{"detail": "Only HOD/manager can add entity links"}`
- No link created
- No audit log entry

---

### Scenario 8: ADD Link - Duplicate
**Actor:** HOD
**Action:** add_entity_link for existing link
**Expected:** 409

**Given:**
- Link already exists: WO-001 → MAN-001 (explicit)

**When:**
```
POST /v1/related/add
Body: {source: WO-001, target: MAN-001, link_type: "explicit"}
```

**Then:**
- Status: 409
- Response: `{"detail": "Link already exists"}`
- No duplicate link created

---

### Scenario 9: ADD Link - Cross-Yacht Target
**Actor:** HOD from Yacht A
**Action:** add_entity_link with target on Yacht B
**Expected:** 404

**Given:**
- HOD on yacht_id = A
- Source WO on yacht A
- Target manual on yacht B

**When:**
```
POST /v1/related/add
Body: {source: WO-A, target: MAN-B}
```

**Then:**
- Status: 404
- Response: `{"detail": "Target entity not found"}`
- No link created (RLS blocks)

---

### Scenario 10: VIEW Related - Deterministic Results
**Actor:** HOD
**Action:** view_related_entities (called twice)
**Expected:** Identical responses

**When:**
- Call GET /v1/related?entity_type=work_order&entity_id=WO-001 (1st time)
- Wait 5 seconds
- Call GET /v1/related?entity_type=work_order&entity_id=WO-001 (2nd time)

**Then:**
- Response 1 == Response 2 (byte-for-byte identical groups, items, match_reasons)
- No randomness, no time-based variation
- Same sorting, same weights

---

## Acceptance Criteria Matrix

| Scenario | Role | Action | Expected Status | Verified By |
|----------|------|--------|----------------|-------------|
| View related (own yacht) | Crew | view_related_entities | 200 | Docker + Staging |
| View related (own yacht) | HOD | view_related_entities | 200 | Docker + Staging |
| View related (cross-yacht) | Crew | view_related_entities | 404 | Docker |
| View related (invalid type) | HOD | view_related_entities | 400 | Docker |
| View related (missing entity) | HOD | view_related_entities | 404 | Docker |
| Add link | HOD | add_entity_link | 200 | Docker + Staging |
| Add link | Crew | add_entity_link | 403 | Docker |
| Add link (duplicate) | HOD | add_entity_link | 409 | Docker |
| Add link (cross-yacht) | HOD | add_entity_link | 404 | Docker |
| Deterministic results | HOD | view_related_entities | Identical responses | Docker |

---

## Docker Test Structure

**File:** `tests/docker/run_work_orders_show_related_tests.py`

```python
def test_view_related_crew_success():
    """Scenario 1: Crew can view related entities"""

def test_view_related_hod_success():
    """Scenario 2: HOD can view related with add_enabled=true"""

def test_view_related_cross_yacht_forbidden():
    """Scenario 3: Cross-yacht returns 404"""

def test_view_related_invalid_entity_type():
    """Scenario 4: Invalid entity_type returns 400"""

def test_view_related_missing_entity():
    """Scenario 5: Missing entity returns 404"""

def test_add_link_hod_success():
    """Scenario 6: HOD can add explicit link"""

def test_add_link_crew_forbidden():
    """Scenario 7: Crew cannot add link (403)"""

def test_add_link_duplicate():
    """Scenario 8: Duplicate link returns 409"""

def test_add_link_cross_yacht_forbidden():
    """Scenario 9: Cross-yacht target returns 404"""

def test_view_related_deterministic():
    """Scenario 10: Same input → same output"""
```

---

## Staging CI Additions

**File:** `tests/ci/staging_work_orders_show_related.py`

**Tests:**
1. Real JWT authentication for crew, HOD, captain
2. View related for existing WO (count groups, verify match_reasons)
3. HOD adds explicit link (verify 200, check audit log)
4. Crew attempts to add link (verify 403)
5. Zero 500 errors across all scenarios

---

## Edge Cases

### Empty Groups
- Work order with no parts → parts.count = 0, items = []
- Still include group in response

### Equipment-less Work Order
- If equipment_id IS NULL → skip manuals/handovers queries
- previous_work group still populated (via fault or other criteria)

### Storage Metadata
- Documents in restricted storage → return metadata only
- No presigned URLs in response
- Frontend shows "View" button disabled if file_access = false

### Soft-Deleted Entities
- Filter out deleted_at IS NOT NULL
- Deleted WOs don't appear in previous_work
- Deleted parts don't appear in parts group

---

## Performance Acceptance

- P95 latency <500ms for GET /v1/related
- Max 6 DB queries per request (one per group)
- Result size <15KB JSON (50 items max)
- Zero N+1 queries

---

## Next Phase

**PHASE 6: SQL BACKEND** - Write actual SQL queries and handler code.

---

**SCENARIOS STATUS:** ✅ DEFINED
