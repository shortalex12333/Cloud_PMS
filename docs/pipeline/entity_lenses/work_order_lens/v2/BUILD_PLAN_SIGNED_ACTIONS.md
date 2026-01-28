# Work Order Lens - Build Plan: Signed Actions & Storage Isolation

**Branch**: `work-order/signed-actions-storage`
**Status**: P0 COMPLETE - P1 QUEUED
**Created**: 2026-01-27
**Updated**: 2026-01-27

---

## 0. P0 COMPLETION SUMMARY

### Completed P0 Tasks

| Task | Status | Files |
|------|--------|-------|
| Signed Actions Registry | ✅ DONE | `registry.py` - duplicates removed, roles corrected |
| Signed Actions Visibility by Role | ✅ DONE | `reassign` for HOD+captain+manager; `archive` for captain+manager only |
| view_my_work_orders READ action | ✅ DONE | `registry.py`, `list_handlers.py`, `p0_actions_routes.py` |
| My Work Orders Handler | ✅ DONE | Deterministic sorting by group (overdue/critical/time_consuming/other) |
| My Work Orders Route | ✅ DONE | `GET /work-orders/list-my` |
| Storage Options for WO Photos | ✅ VERIFIED | bucket=`pms-work-order-photos`, confirmation_required=true |
| Docker Tests | ✅ DONE | `tests/docker/run_work_orders_action_list_tests.py` (10 assertions) |
| Staging CI Tests | ✅ DONE | `tests/ci/staging_work_orders_acceptance.py` (12 tests including signed flows) |
| Migrations 104/105/106 | ✅ APPLIED | SLA columns, pms_entity_links, v_my_work_orders_summary |

### Key Changes Made

1. **Registry** (`apps/api/action_router/registry.py`):
   - Removed duplicate `reassign_work_order` and `archive_work_order` definitions
   - Added `view_my_work_orders` action (variant=READ, all roles)
   - Corrected role lists: `reassign` includes `chief_officer`; `archive` is captain+manager only

2. **Handler** (`apps/api/handlers/list_handlers.py`):
   - Added `list_my_work_orders()` method with deterministic sorting per group
   - Groups: overdue, critical, time_consuming, other
   - Sorting rules match spec (days_overdue desc, criticality_rank asc, etc.)

3. **Route** (`apps/api/routes/p0_actions_routes.py`):
   - Added `GET /work-orders/list-my` endpoint
   - Removed duplicate reassign/archive handlers (unreachable code)

4. **Tests**:
   - Docker: 10 assertions for role visibility, storage options, variant=SIGNED
   - Staging CI: 12 tests including HOD reassign→200, CREW reassign→403, Captain archive→200, HOD archive→403, signature JSON verification

---

## 1. CURRENT STATE (Verified)

### Tenant DB (TENANT_1)

| Component | Status | Notes |
|-----------|--------|-------|
| Cascade trigger (`trg_wo_status_cascade_to_fault`) | ✅ DEPLOYED | WO completed → Fault resolved |
| SLA columns (due_at, criticality_rank, etc.) | ✅ DEPLOYED | Migration 104 |
| `pms_entity_links` table | ✅ DEPLOYED | Migration 105 |
| `v_my_work_orders_summary` view | ✅ DEPLOYED | Migration 106 |
| RLS on entity_links | ✅ DEPLOYED | HOD/Manager can insert/delete |

### Registry (apps/api/action_router/registry.py)

| Action | Status | Variant | Roles |
|--------|--------|---------|-------|
| `reassign_work_order` | ✅ REGISTERED | SIGNED | chief_engineer, chief_officer, captain, manager |
| `archive_work_order` | ✅ REGISTERED | SIGNED | captain, manager |
| `add_work_order_photo` | ✅ REGISTERED | MUTATE | crew, eto, engineer, chief_engineer, captain, manager |

### Execute Routing (apps/api/routes/p0_actions_routes.py)

| Action | Status | Signature Required |
|--------|--------|-------------------|
| `create_work_order_from_fault` | ✅ WIRED | YES |
| `reassign_work_order` | ✅ WIRED | YES |
| `archive_work_order` | ✅ WIRED | YES |

---

## 2. REMAINING TASKS

### 2.1 Action Registry Parity

**Goal**: Verify action visibility per role

| Task | File | Status |
|------|------|--------|
| Assert `reassign_work_order` appears for HOD | tests/docker/run_work_orders_action_list_tests.py | TODO |
| Assert `reassign_work_order` NOT for crew | tests/docker/run_work_orders_action_list_tests.py | TODO |
| Assert `archive_work_order` appears for captain/manager | tests/docker/run_work_orders_action_list_tests.py | TODO |
| Assert `archive_work_order` NOT for crew/engineer | tests/docker/run_work_orders_action_list_tests.py | TODO |
| Verify search_keywords cover: reassign/assign/owner/handover; archive/cancel/remove | registry.py | TODO |

### 2.2 "My Work Orders" Read Action

**Goal**: Return grouped WOs (overdue/critical/time_consuming/other)

```python
# New action in registry.py
"view_my_work_orders": ActionDefinition(
    action_id="view_my_work_orders",
    label="My Work Orders",
    endpoint="/v1/work-orders/list-my",
    handler_type=HandlerType.INTERNAL,
    method="GET",
    allowed_roles=["crew", "eto", "engineer", "chief_engineer", "chief_officer", "captain", "manager"],
    required_fields=["yacht_id"],
    domain="work_orders",
    variant=ActionVariant.READ,
    search_keywords=["my", "work", "orders", "assigned", "overdue", "critical"],
)
```

**Handler** (`work_order_mutation_handlers.py`):
```python
async def list_my_work_orders(self, yacht_id: str, user_id: str) -> Dict:
    """
    Return grouped work orders from v_my_work_orders_summary.
    Groups: overdue, critical, time_consuming, other
    """
    result = self.db.rpc(
        "get_my_work_orders_summary",
        {"p_yacht_id": yacht_id, "p_user_id": user_id}
    ).execute()

    # Group by group_key
    grouped = {"overdue": [], "critical": [], "time_consuming": [], "other": []}
    for wo in result.data:
        grouped[wo["group_key"]].append(wo)

    return {
        "status": "success",
        "groups": grouped,
        "total_count": len(result.data),
    }
```

### 2.3 Show Related Endpoint

**Goal**: Return related entities for a focused WO

**Read Endpoint** (`GET /v1/work-orders/{id}/related`):
```json
{
  "entity_type": "work_order",
  "entity_id": "uuid",
  "groups": {
    "parts": [{"id": "...", "name": "...", "match_reason": "linked_part"}],
    "manuals": [{"id": "...", "title": "...", "match_reason": "equipment_manual"}],
    "previous_work": [{"id": "...", "wo_number": "...", "match_reason": "same_equipment"}],
    "handovers": [{"id": "...", "title": "...", "match_reason": "mentioned_equipment"}],
    "attachments": [{"id": "...", "filename": "...", "match_reason": "wo_attachment"}]
  },
  "add_related_enabled": true,
  "missing_signals": []
}
```

**Write Endpoint** (`POST /v1/entity-links/add`):
- Input: `source_entity_type`, `source_entity_id`, `target_entity_type`, `target_entity_id`, `link_type`, `note`
- Role gate: HOD/Manager only (RLS enforced)
- Returns: `{ "status": "success", "link_id": "uuid" }`

### 2.4 Notifications v1

**Tables Required**:
- `pms_notifications` (exists per earlier migrations)
- `pms_user_notification_prefs` (optional)

**Generator**:
```python
async def generate_wo_notifications(yacht_id: str):
    """
    Project v_my_work_orders_summary and upsert notifications.
    Idempotency key: (user_id, source, source_id, topic, date_bucket)
    """
    # Get overdue/critical WOs
    overdue_wos = await get_overdue_work_orders(yacht_id)

    for wo in overdue_wos:
        await upsert_notification(
            user_id=wo["assigned_to"],
            source="work_order",
            source_id=wo["id"],
            topic="overdue",
            date_bucket=date.today().isoformat(),
            title=f"Overdue: {wo['title']}",
            cta_action_id="view_work_order_detail",
            cta_payload={"work_order_id": wo["id"]},
        )
```

**API**:
- `GET /v1/notifications` - List for current user (RLS: yacht_id + user_id)
- `POST /v1/notifications/{id}/read` - Mark as read
- `POST /v1/notifications/{id}/dismiss` - Dismiss

---

## 3. ACCEPTANCE TESTS

### 3.1 Docker Fast Loop

**File**: `tests/docker/run_work_orders_action_list_tests.py`

```python
def test_reassign_visible_for_hod():
    """HOD sees reassign_work_order in action list"""
    response = get_actions(role="chief_engineer", domain="work_orders")
    action_ids = [a["action_id"] for a in response["actions"]]
    assert "reassign_work_order" in action_ids

def test_reassign_hidden_for_crew():
    """Crew does NOT see reassign_work_order"""
    response = get_actions(role="crew", domain="work_orders")
    action_ids = [a["action_id"] for a in response["actions"]]
    assert "reassign_work_order" not in action_ids

def test_archive_visible_for_captain():
    """Captain sees archive_work_order"""
    response = get_actions(role="captain", domain="work_orders")
    action_ids = [a["action_id"] for a in response["actions"]]
    assert "archive_work_order" in action_ids

def test_archive_hidden_for_engineer():
    """Engineer does NOT see archive_work_order"""
    response = get_actions(role="engineer", domain="work_orders")
    action_ids = [a["action_id"] for a in response["actions"]]
    assert "archive_work_order" not in action_ids

def test_photo_has_storage_options():
    """add_work_order_photo returns storage_options with correct bucket"""
    response = get_actions(role="engineer", domain="work_orders")
    photo_action = next((a for a in response["actions"] if a["action_id"] == "add_work_order_photo"), None)
    assert photo_action is not None
    assert photo_action.get("storage_options", {}).get("bucket") == "pms-work-order-photos"
```

### 3.2 Staging CI

**File**: `tests/ci/staging_work_orders_acceptance.py`

```python
def test_reassign_wo_hod_success():
    """HOD can reassign work order with valid signature"""
    jwt = login_as("hod")
    response = execute_action(
        jwt,
        action="reassign_work_order",
        payload={
            "work_order_id": TEST_WO_ID,
            "new_assignee_id": TEST_CREW_ID,
            "reason": "Workload balancing",
            "signature": {
                "signed_at": datetime.utcnow().isoformat(),
                "user_id": HOD_USER_ID,
                "role_at_signing": "chief_engineer",
                "signature_type": "digital",
                "signature_hash": "sha256:..."
            }
        }
    )
    assert response.status_code == 200

def test_reassign_wo_crew_forbidden():
    """Crew cannot reassign work order"""
    jwt = login_as("crew")
    response = execute_action(jwt, action="reassign_work_order", payload={...})
    assert response.status_code == 403

def test_archive_wo_captain_success():
    """Captain can archive work order with signature"""
    jwt = login_as("captain")
    response = execute_action(
        jwt,
        action="archive_work_order",
        payload={
            "work_order_id": TEST_WO_ID,
            "deletion_reason": "Duplicate entry",
            "signature": {...}
        }
    )
    assert response.status_code == 200

    # Verify ledger has signature JSON
    audit = get_audit_log(entity_id=TEST_WO_ID, action="archive_work_order")
    assert audit["signature"] != {}
    assert "signed_at" in audit["signature"]

def test_cascade_wo_completion_resolves_fault():
    """Completing WO with linked fault triggers cascade"""
    # Create WO with fault_id
    wo = create_wo_with_fault(fault_id=TEST_FAULT_ID)

    # Complete the WO
    complete_wo(wo["id"])

    # Verify fault status changed
    fault = get_fault(TEST_FAULT_ID)
    assert fault["status"] == "resolved"

def test_no_500_errors():
    """All negative cases return 4xx, never 500"""
    # Missing signature
    response = execute_action(jwt, action="reassign_work_order", payload={"work_order_id": "..."})
    assert response.status_code == 400  # Not 500

    # Invalid work_order_id
    response = execute_action(jwt, action="archive_work_order", payload={"work_order_id": "invalid-uuid", ...})
    assert response.status_code == 400  # Not 500
```

### 3.3 My Work Orders Tests

**File**: `tests/ci/staging_my_work_orders_tests.py`

```python
def test_my_work_orders_grouping():
    """Verify deterministic grouping"""
    # Seed data: 1 overdue, 1 critical, 1 time_consuming
    seed_test_work_orders()

    response = get_my_work_orders(jwt)

    assert len(response["groups"]["overdue"]) == 1
    assert len(response["groups"]["critical"]) == 1
    assert len(response["groups"]["time_consuming"]) == 1

def test_my_work_orders_stable_sort():
    """Verify stable sort across requests"""
    response1 = get_my_work_orders(jwt)
    response2 = get_my_work_orders(jwt)

    # Order should be identical
    assert response1["groups"]["overdue"] == response2["groups"]["overdue"]
```

---

## 4. GUARDRAILS

### Role Strings (Exact)

| Logical Role | Exact Strings |
|--------------|---------------|
| HOD | `chief_engineer`, `chief_officer`, `captain`, `purser` |
| Manager | `manager` |
| Engineer | `engineer`, `eto` |
| Crew | `crew` |

**Never use**: "HOD+", "Engineer+", "Manager+" in code

### Signature Payload (Canonical Keys)

```json
{
  "signed_at": "2026-01-27T10:30:00Z",
  "user_id": "uuid",
  "role_at_signing": "chief_engineer",
  "signature_type": "digital",
  "signature_hash": "sha256:abc123..."
}
```

### Audit Log

| Action Type | signature Column |
|-------------|------------------|
| Non-signed (MUTATE) | `{}` (empty JSON, NOT NULL) |
| Signed (SIGNED) | Full signature JSON |

### Storage Isolation

| Action | Bucket | Path |
|--------|--------|------|
| `add_work_order_photo` | `pms-work-order-photos` | `{yacht_id}/work_orders/{work_order_id}/{filename}` |

---

## 5. FILES TO CREATE/MODIFY

### New Files

| File | Purpose |
|------|---------|
| `apps/api/handlers/my_work_orders_handler.py` | Handler for view_my_work_orders |
| `apps/api/handlers/show_related_handler.py` | Handler for Show Related read/write |
| `apps/api/handlers/notifications_handler.py` | Notifications list/read/dismiss |
| `tests/docker/run_work_orders_action_list_tests.py` | Docker fast-loop tests |
| `tests/ci/staging_my_work_orders_tests.py` | My Work Orders acceptance tests |

### Modified Files

| File | Changes |
|------|---------|
| `apps/api/action_router/registry.py` | Add `view_my_work_orders`, `view_related_entities`, `add_entity_link` |
| `apps/api/routes/p0_actions_routes.py` | Wire new endpoints |
| `tests/ci/staging_work_orders_acceptance.py` | Add signed action tests |

---

## 6. IMPLEMENTATION ORDER

1. **Phase 1: Verify Registry** (1 PR)
   - Confirm signed actions visible/hidden per role
   - Add search_keywords if missing
   - Add storage_options to photo action

2. **Phase 2: My Work Orders** (1 PR)
   - Add `view_my_work_orders` action
   - Create handler using `v_my_work_orders_summary`
   - Wire route

3. **Phase 3: Show Related** (1 PR)
   - Add read endpoint (FK joins)
   - Add write endpoint (pms_entity_links)
   - RLS enforced

4. **Phase 4: Notifications v1** (1 PR)
   - Generator for overdue/critical WOs
   - API: list/read/dismiss
   - CTA payload for ActionModal

5. **Phase 5: Acceptance Tests** (1 PR)
   - Docker fast-loop tests
   - Staging CI tests
   - My Work Orders tests

---

## 7. VERIFICATION CHECKLIST

### P0 (Complete)

| Check | Status |
|-------|--------|
| Cascade trigger deployed | ✅ |
| SLA columns added | ✅ |
| pms_entity_links created | ✅ |
| v_my_work_orders_summary created | ✅ |
| reassign_work_order registered (correct roles) | ✅ |
| archive_work_order registered (captain+manager only) | ✅ |
| view_my_work_orders registered | ✅ |
| Execute routing wired | ✅ |
| Docker tests written | ✅ |
| Staging CI tests updated | ✅ |
| My Work Orders endpoint | ✅ |
| Storage options verified (pms-work-order-photos) | ✅ |

### P1 (Queued)

| Check | Status |
|-------|--------|
| Show Related read endpoint | TODO |
| Show Related write endpoint | TODO |
| Notifications v1 list API | TODO |
| Notifications v1 read/dismiss | TODO |
| Notifications generator (overdue WO) | TODO |

---

## 8. NEXT STEPS (P1)

1. **Show Related (Read + Write)**
   - Read: `GET /v1/work-orders/{id}/related` - FK joins for deterministic retrieval
   - Write: `POST /v1/entity-links/add` - Insert into pms_entity_links (HOD/manager RLS)
   - See: `docs/pipeline/work_order_lens/SHOW_RELATED.md`

2. **Notifications v1 (In-App Only)**
   - List: `GET /v1/notifications` - RLS-gated by user
   - Mark read: `POST /v1/notifications/{id}/read`
   - Dismiss: `POST /v1/notifications/{id}/dismiss`
   - Generator: Daily idempotent projection from v_my_work_orders_summary for overdue WOs

---

**END OF BUILD PLAN**
