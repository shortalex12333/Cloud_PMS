# RLS, Role Security, Ledger & Frontend Audit Trail — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce role-based access on every action button; write every mutation AND read event to `ledger_events` with full 4-dimension security stamping; surface a functional audit history on all 7 lens pages with clickthrough navigation to the source entity.

**Architecture:** Four independent layers: (1) role enforcement inside each `elif` block in `p0_actions_routes.py` before any DB write, (2) **centralised ledger middleware** in the action router that writes every mutation automatically — not per-handler, (3) read beacon fired by frontend when any entity page or document is opened, (4) role-scoped timeline endpoint driving `HistorySection` on each lens page with deep-link navigation per entry.

**Strategic context:** The ledger is the commercial asset. Celeste PMS is the vehicle to collect operational data across yachts. The ledger must hold up in a court of law — exact timestamps, role-stamped, tamper-evident (SHA-256 proof hash), maximum metadata richness. This data is the foundation of a future B2B insurance brokerage platform.

**Tech Stack:** Python/FastAPI (backend), PostgreSQL RLS (database), React/Next.js + TypeScript (frontend), Supabase JS client, `useQuery` (TanStack Query).

---

## Architecture Addendum: Ledger as Insurance-Grade Audit System

### The Four Security Dimensions

Every ledger write MUST stamp all four dimensions. Missing any one breaks role-scoped queries, the insurance audit chain, and court-of-law evidentiary completeness.

| Dimension | Source | Enforced at | Purpose |
|---|---|---|---|
| `yacht_id` | JWT claim `app_metadata.yacht_id` | Route → DB RLS | Tenant isolation — every query scoped to one yacht |
| `user_id` | JWT `sub` | Route JWT decode | WHO acted — immutable at write time, even if profile changes later |
| `user_role` | JWT `app_metadata.role` | Role gate checks | WHAT they were authorised to do at that exact moment |
| `department` | JWT `app_metadata.department` | Ledger write + scope query | HoD scope filtering — which crew belong to this HoD's view |

These four are extracted once at the top of every action handler and passed explicitly to every ledger write. They are never inferred from DB lookups or re-derived.

### Full `ledger_events` Schema

```sql
-- Confirm or alter this matches your actual table
CREATE TABLE public.ledger_events (
    id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    -- Four mandatory security dimensions
    yacht_id        uuid        NOT NULL,
    user_id         uuid        NOT NULL,
    user_role       text        NOT NULL,   -- role AT TIME of action (snapshot)
    department      text,                   -- from JWT, for HoD scope queries
    actor_name      text,                   -- display name snapshot (for insurance reports)
    -- Event identity
    event_category  text        NOT NULL,   -- 'write' | 'read' | 'admin'
    event_type      text        NOT NULL,   -- 'create' | 'update' | 'delete' | 'approval' | 'view' | etc.
    action          text        NOT NULL,   -- exact action name e.g. 'approve_purchase_order'
    -- Entity being acted on
    entity_type     text        NOT NULL,   -- 'work_order' | 'fault' | 'equipment' | 'part' | etc.
    entity_id       uuid        NOT NULL,   -- UUID of the entity — used for clickthrough navigation
    -- Audit payload
    change_summary  text,                   -- human-readable description
    metadata        jsonb       DEFAULT '{}', -- maximum richness: page numbers, scroll pos, field diffs
    proof_hash      text        NOT NULL,   -- SHA-256 of (yacht_id+user_id+event_type+entity_type+entity_id+timestamp)
    source_context  text        DEFAULT 'microaction', -- 'microaction' | 'bulk' | 'system' | 'read_beacon'
    -- Timing
    created_at      timestamptz DEFAULT now() NOT NULL
);

-- Indexes for role-scoped timeline queries
CREATE INDEX idx_ledger_self   ON ledger_events (yacht_id, user_id, created_at DESC);
CREATE INDEX idx_ledger_dept   ON ledger_events (yacht_id, department, created_at DESC);
CREATE INDEX idx_ledger_all    ON ledger_events (yacht_id, created_at DESC);
CREATE INDEX idx_ledger_entity ON ledger_events (yacht_id, entity_type, entity_id, created_at DESC);
```

### Clickthrough Navigation Contract

Every ledger row in the UI is clickable. Clicking it opens the source entity at the exact state the user was viewing. This requires `entity_type + entity_id` to be stored correctly.

| `entity_type` value | Frontend route constructed | Notes |
|---|---|---|
| `work_order` | `/work-orders/{entity_id}` | |
| `fault` | `/faults/{entity_id}` | |
| `equipment` | `/equipment/{entity_id}` | |
| `part` | `/inventory/{entity_id}` | |
| `shopping_list_item` | `/shopping-list/{entity_id}` | entity_id = item UUID |
| `receiving` | `/receiving/{entity_id}` | |
| `purchase_order` | `/purchasing/{entity_id}` | |
| `document` | `/documents/{entity_id}` | |
| `certificate` | `/certificates/{entity_id}` | |
| `manual_page` | `/documents/{entity_id}?page={metadata.page}` | page stored in metadata |

The `metadata` JSONB field carries the richest contextual snapshot:

```json
{
  "page": 12,                         // document page viewed
  "last_cached_page": 12,             // last page before close
  "section": "maintenance_schedule",  // section label if known
  "field_diffs": {"status": ["open", "in_progress"]},  // for update events
  "scroll_pct": 68,                   // scroll position as % (for future use)
  "duration_seconds": 142             // time spent on entity (for insurance risk scoring)
}
```

Metadata fields are optional and best-effort. Backend actions write `field_diffs`. Frontend read beacons write `page`, `last_cached_page`, `scroll_pct`, `duration_seconds`.

### Ledger Views by Role

| Role | Scope | Endpoint parameter | What they see |
|---|---|---|---|
| `crew` | Self only | `scope=self` | Only their own `user_id` events |
| `chief_engineer`, `manager` | Their department + self | `scope=department` | All events where `department` matches theirs |
| `captain` | All crew on yacht | `scope=all` | Every `yacht_id`-scoped event |

The scope is derived server-side from the JWT role — never trusted from the client.

```python
# In the timeline endpoint
if user_role == "captain":
    query = query  # all events for this yacht_id
elif user_role in ("chief_engineer", "manager"):
    query = query.eq("department", user_department)
else:
    query = query.eq("user_id", user_id)  # crew: self only
```

### Per-Lens Security Context Flow

How the four dimensions enter and flow through each lens:

| Lens | All-roles actions | HOD-only actions | Role gate location | Ledger stamps |
|---|---|---|---|---|
| **Work Order** | create, update, start, add_note, add_part | assign_work_order, close_work_order | Inside `elif` body in `p0_actions_routes.py` | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Fault** | report_fault, add_fault_note, add_fault_photo | acknowledge_fault, close_fault, reopen_fault, mark_fault_false_alarm, diagnose_fault | Inside `elif` body | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Equipment** | update_running_hours, add_equipment_note, log_contractor, link_document | update_equipment, set_equipment_status | Inside `elif` body | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Part / Inventory** | consume_part, receive_part, transfer_part, add_to_shopping_list | adjust_stock_quantity (+ signature), write_off_part (+ signature), order_part | Inside `elif` body | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Receiving** | ALL actions including accept/reject | None | No role gate — verify no accidental restriction | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Shopping List** | create, update, mark_received | approve, reject, promote_to_part, mark_ordered | Inside `elif` body | yacht_id ✓ user_id ✓ role ✓ department ✓ |
| **Purchase Order** | create, update, add_item, submit | approve, mark_received, cancel | Inside `elif` body (see Task 1) | yacht_id ✓ user_id ✓ role ✓ department ✓ |

### Read Events: Maximum Data Collection

Frontend must fire a read beacon to `/v1/ledger/read-event` (POST, fire-and-forget) when:
- Any entity detail page is opened
- Any document/manual is opened (include page number)
- Any modal or panel displaying entity data is opened

Payload:
```json
{
  "entity_type": "work_order",
  "entity_id": "uuid",
  "event_type": "view",
  "metadata": { "page": null, "scroll_pct": 0 }
}
```

The beacon endpoint extracts all four security dimensions from the JWT and writes to `ledger_events` with `event_category: "read"`.

> **Court-of-law rationale:** "User opened document X at 09:03AM on page 12" is as admissible as "User approved PO Y." Read events prove awareness — a crew member cannot claim ignorance of a safety document they opened 14 times.

### DB Trigger Safety Net (Future Mandatory Milestone)

Application-layer writes are sufficient for MVP. In a future milestone, add a Supabase DB trigger on every `pms_*` table that writes a minimal fallback row to `ledger_events` on INSERT/UPDATE/DELETE if no corresponding application-layer event exists within the same transaction. This ensures:
- Evidence even if the API crashes mid-write
- Tamper detection (two independent records must agree)
- Insurance-grade immutability

Mark this as a separate work item — do NOT block MVP on it.

### UX Note: MVP Priority

**Do not style or polish the history/ledger UI in this milestone.** The requirement is: information is **organised, true, and functional**. Hierarchy, cascading disclosure, and visual polish are a separate styling pass. What matters now is that the correct data is present, the clickthrough navigation works, and the scope filtering returns the right records.

---

## Chunk 1: Role Security — Add Missing ROLES Dicts and Enforcement

### Gap Audit

| Action group | Current state | Risk | Canonical role (lens DATA.md) |
|---|---|---|---|
| `approve_purchase_order`, `mark_po_received`, `cancel_purchase_order` | No role check | Any crew can approve/cancel POs | HOD only: `chief_engineer`, `captain`, `manager` |
| `submit_purchase_order` | No role check | Low risk | ALL roles |
| `edit_receiving`, `submit_receiving_for_review`, `accept_receiving`, `reject_receiving` | No role check | **Not a gap** — lens-05 DATA.md: ALL roles allowed | ALL roles — no restriction needed |
| `create_work_order_for_equipment` | No role check | **Not a gap** — lens-01 DATA.md: ALL roles can create WOs | ALL roles — no restriction needed |
| `mark_shopping_list_ordered` | No role check | Any crew can mark items ordered | HOD only: `chief_engineer`, `captain`, `manager` |

> **Canonical role reference:** `docs/superpowers/LENS_TRUTH_SHEET.md`. HOD = `chief_engineer`, `captain`, `manager` — does NOT include `chief_officer`. PO gating is in `apps/api/action_router/action_gating.py` (not registry.py).

---

### Task 1: Add PURCHASE_ORDER_ROLES dict and enforcement

**File:** `apps/api/routes/p0_actions_routes.py`

Locate the four PO handlers (lines 6099–6197). Add a ROLES dict and check BEFORE the DB write.

**Files:**
- Modify: `apps/api/routes/p0_actions_routes.py:6099`

- [ ] **Step 1: Find the four PO elif blocks**

Open `apps/api/routes/p0_actions_routes.py`. Search for each of these four action names:
```bash
grep -n '"submit_purchase_order"\|"approve_purchase_order"\|"mark_po_received"\|"cancel_purchase_order"' \
  apps/api/routes/p0_actions_routes.py | grep "elif"
```
Note the line numbers for each `elif action in (...)` block.

- [ ] **Step 2: Add role check as FIRST LINES inside each elif body**

> **CRITICAL**: Do NOT add a standalone `if` block before the `elif` chain — that breaks the chain for authorized users (Python skips elif when the preceding if matched). Instead, insert the role check as the FIRST statement INSIDE each `elif` body.

For `submit_purchase_order` — ALL roles, no restriction needed. Skip.

For each of the three HOD-only actions, insert at the very start of the `elif` body (before any DB access):

```python
elif action in ("approve_purchase_order",):
    # Role check — HOD only (canonical: lens-12 DATA.md)
    _po_hod = ["chief_engineer", "captain", "manager"]
    if user_role not in _po_hod:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not permitted to perform 'approve_purchase_order'",
            "required_roles": _po_hod,
        })
    # ... rest of existing approve_purchase_order code follows unchanged ...

elif action in ("mark_po_received",):
    # Role check — HOD only (canonical: lens-12 DATA.md)
    _po_hod = ["chief_engineer", "captain", "manager"]
    if user_role not in _po_hod:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not permitted to perform 'mark_po_received'",
            "required_roles": _po_hod,
        })
    # ... rest of existing mark_po_received code follows unchanged ...

elif action in ("cancel_purchase_order",):
    # Role check — HOD only (canonical: lens-12 DATA.md)
    _po_hod = ["chief_engineer", "captain", "manager"]
    if user_role not in _po_hod:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not permitted to perform 'cancel_purchase_order'",
            "required_roles": _po_hod,
        })
    # ... rest of existing cancel_purchase_order code follows unchanged ...
```

- [ ] **Step 3: Verify `user_role` variable is available at this point in the code**

Search for where `user_role` is set:
```bash
grep -n "user_role = " apps/api/routes/p0_actions_routes.py | head -5
```
Expected output: a line like `user_role = user_context.get("role")` near the top of the handler. If it's not set, add `user_role = user_context.get("role", "")` at the top of the function.

- [ ] **Step 4: Test enforcement with a crew-role token**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
# This should return 403 if token's role is "crew"
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve_purchase_order","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"purchase_order_id":"00000000-0000-0000-0000-000000000000"}}' | python3 -m json.tool
```

Expected: `{"error_code": "FORBIDDEN", ...}` or 403. If the test token is captain, expect 404 (PO not found), which proves the role check passed through.

- [ ] **Step 5: docker cp and restart**

```bash
docker cp apps/api/routes/p0_actions_routes.py celeste-api:/app/routes/p0_actions_routes.py
docker restart celeste-api
sleep 5 && curl -s http://localhost:8000/health
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes/p0_actions_routes.py
git commit -m "feat: add PURCHASE_ORDER_ROLES enforcement for PO action buttons"
```

---

### Task 2: Verify receiving handlers have no accidental restriction

**Canonical source:** `docs/superpowers/agents/lens-05/DATA.md` — ALL roles can perform ALL receiving actions (edit, submit for review, accept, reject, create). **No role restriction should be added.**

This task is a verification-only step to confirm no existing code accidentally restricts receiving actions.

- [ ] **Step 1: Confirm no role check exists in receiving handler paths**

```bash
grep -n "FORBIDDEN\|role.*not.*in\|403" apps/api/routes/p0_actions_routes.py | \
  grep -i "receiv" | head -10
grep -rn "FORBIDDEN\|role.*not.*in\|403" apps/api/action_router/dispatchers/internal_dispatcher.py | head -10
```

Expected: no matches touching receiving action paths. If any exist, remove them.

- [ ] **Step 2: Smoke-test accepting a receiving record as a crew-role token**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"accept_receiving","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"receiving_id":"00000000-0000-0000-0000-000000000000"}}' | python3 -m json.tool
```

Expected: `404` or a domain error (receiving not found) — NOT `403`. A 403 here means an accidental restriction is in place; if so, remove it.

- [ ] **Step 3: Commit (only if a restriction was found and removed)**

```bash
git add apps/api/routes/p0_actions_routes.py
git commit -m "fix: remove accidental role restriction on receiving actions (all roles allowed per lens-05)"
```

---

### Task 3: Add role enforcement for mark_shopping_list_ordered

Per canonical role docs:
- `create_work_order_for_equipment` — **ALL roles** (lens-01 DATA.md) — no restriction needed, skip.
- `mark_shopping_list_ordered` — **HOD only**: `chief_engineer`, `captain`, `manager` (lens-09 DATA.md). `chief_officer` is NOT in HOD.

**Files:**
- Modify: `apps/api/routes/p0_actions_routes.py`

- [ ] **Step 1: Find the mark_shopping_list_ordered elif block**

```bash
grep -n '"mark_shopping_list_ordered"' apps/api/routes/p0_actions_routes.py | grep "elif"
```

Note the line number of the `elif action in ("mark_shopping_list_ordered",):` block.

- [ ] **Step 2: Add role check as FIRST LINES inside the elif body**

> **CRITICAL**: Insert the role check INSIDE the `elif` body — NOT as a standalone `if` before it. A standalone `if` before the `elif` makes the `elif` body unreachable for authorized users.

```python
elif action in ("mark_shopping_list_ordered",):
    # Role check — HOD only (canonical: lens-09 DATA.md; chief_officer is NOT HOD)
    _sl_hod = ["chief_engineer", "captain", "manager"]
    if user_role not in _sl_hod:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not permitted to mark shopping list items ordered",
            "required_roles": _sl_hod,
        })
    # ... rest of existing mark_shopping_list_ordered code follows unchanged ...
```

- [ ] **Step 3: Test that crew role gets 403, captain gets 404 (not found)**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"action":"mark_shopping_list_ordered","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"item_id":"00000000-0000-0000-0000-000000000000"}}' | python3 -m json.tool
```

With a crew token: expect `{"error_code": "FORBIDDEN"}`. With a captain token: expect a domain error (item not found), NOT 403.

- [ ] **Step 4: docker cp, restart, verify health**

```bash
docker cp apps/api/routes/p0_actions_routes.py celeste-api:/app/routes/p0_actions_routes.py
docker restart celeste-api && sleep 5 && curl -s http://localhost:8000/health
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/routes/p0_actions_routes.py
git commit -m "feat: add HOD role enforcement for mark_shopping_list_ordered (chief_engineer/captain/manager)"
```

---

## Chunk 2: Ledger Completeness

### Architecture: Centralised Middleware (not per-handler)

**Do NOT add ledger writes to individual handlers one-by-one.** The correct approach is a single post-action write in `p0_actions_routes.py` after the action executes successfully. This gives 100% mutation coverage automatically — including any future actions — without relying on every developer remembering to instrument each handler.

The only handlers that still need direct ledger writes are those that go through `internal_dispatcher` without passing through `p0_actions_routes.py` (verify this is actually the case before adding anything).

---

### Task 4: Fix `event_timestamp` bug in ledger_routes.py

**File:** `apps/api/routes/ledger_routes.py`

- [ ] **Step 1: Find and fix the ordering bug**

```bash
grep -n "event_timestamp" apps/api/routes/ledger_routes.py
```

Expected: one line with `.order("event_timestamp", desc=True)`. Change it:

```python
# BEFORE:
).order("event_timestamp", desc=True).limit(limit).execute()
# AFTER:
).order("created_at", desc=True).limit(limit).execute()
```

- [ ] **Step 2: Test the endpoint returns events without 500**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
WO_ID=$(docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('pms_work_orders').select('id').limit(1).execute()
print(r.data[0]['id'] if r.data else '')
")
curl -s "http://localhost:8000/v1/ledger/events/by-entity/work_order/$WO_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -20
```

Expected: `{"success": true, "events": [...]}`.

- [ ] **Step 3: docker cp and commit**

```bash
docker cp apps/api/routes/ledger_routes.py celeste-api:/app/routes/ledger_routes.py
docker restart celeste-api && sleep 5
git add apps/api/routes/ledger_routes.py
git commit -m "fix: ledger by-entity endpoint order by created_at (was event_timestamp)"
```

---

### Task 5: Add centralised ledger middleware to p0_actions_routes.py

Every action goes through `p0_actions_routes.py`. Add a single ledger write AFTER the action response is built. This captures ALL mutations with zero per-handler work.

**File:** `apps/api/routes/p0_actions_routes.py`

- [ ] **Step 1: Find where action responses are built and returned**

```bash
grep -n "return.*response\|return.*result\|JSONResponse\|builder.build" \
  apps/api/routes/p0_actions_routes.py | tail -30
```

Locate the final response assembly point — typically at the end of the main `execute_action` handler function, after all `elif action in (...)` branches have run.

- [ ] **Step 2: Confirm the four security dimensions are available at that point**

```bash
grep -n "user_id\|user_role\|yacht_id\|department" apps/api/routes/p0_actions_routes.py | head -20
```

All four should be set near the top of the handler from the JWT decode. If `department` is missing, add:
```python
user_department = user_context.get("department") or user_context.get("app_metadata", {}).get("department", "")
```

- [ ] **Step 3: Extend the existing `build_ledger_event()` function (lines 57–105) — do NOT create a new helper**

`build_ledger_event()` already exists and handles proof_hash. Extend its signature to accept the 3 new columns that were just added to the schema. Add them as optional keyword args with defaults of `None`:

```python
# BEFORE (line 64–66):
    user_role: str = None,
    change_summary: str = None,
    metadata: dict = None
# AFTER:
    user_role: str = None,
    change_summary: str = None,
    metadata: dict = None,
    department: str = None,
    actor_name: str = None,
    event_category: str = "write"
```

In the function body, after the `if change_summary:` block (around line 91), add:
```python
    if department:
        event_data["department"] = department
    if actor_name:
        event_data["actor_name"] = actor_name
    event_data["event_category"] = event_category or "write"
```

Then add the entity map and call-site — after the function definition:

```python
# Entity ID field name per action — maps action name → payload key holding the entity UUID
_ACTION_ENTITY_MAP = {
    # Work Orders
    "start_work_order":       ("work_order", "work_order_id"),
    "complete_work_order":    ("work_order", "work_order_id"),
    "close_work_order":       ("work_order", "work_order_id"),
    "assign_work_order":      ("work_order", "work_order_id"),
    "add_note_to_work_order": ("work_order", "work_order_id"),
    "add_part_to_work_order": ("work_order", "work_order_id"),
    # Faults
    "report_fault":           ("fault", "fault_id"),
    "acknowledge_fault":      ("fault", "fault_id"),
    "close_fault":            ("fault", "fault_id"),
    "diagnose_fault":         ("fault", "fault_id"),
    "reopen_fault":           ("fault", "fault_id"),
    "add_fault_note":         ("fault", "fault_id"),
    # Equipment
    "update_equipment_status": ("equipment", "equipment_id"),
    "add_equipment_note":      ("equipment", "equipment_id"),
    "update_running_hours":    ("equipment", "equipment_id"),
    # Parts / Inventory
    "log_part_usage":          ("part", "part_id"),
    "adjust_stock_quantity":   ("part", "part_id"),
    "write_off_part":          ("part", "part_id"),
    # Shopping List
    "create_shopping_list_item":  ("shopping_list_item", "item_id"),
    "approve_shopping_list_item": ("shopping_list_item", "item_id"),
    "reject_shopping_list_item":  ("shopping_list_item", "item_id"),
    "mark_shopping_list_ordered": ("shopping_list_item", "item_id"),
    # Receiving
    "edit_receiving":              ("receiving", "receiving_id"),
    "submit_receiving_for_review": ("receiving", "receiving_id"),
    "accept_receiving":            ("receiving", "receiving_id"),
    "reject_receiving":            ("receiving", "receiving_id"),
    # Purchase Orders
    "submit_purchase_order":   ("purchase_order", "purchase_order_id"),
    "approve_purchase_order":  ("purchase_order", "purchase_order_id"),
    "mark_po_received":        ("purchase_order", "purchase_order_id"),
    "cancel_purchase_order":   ("purchase_order", "purchase_order_id"),
}

def _write_ledger_event(
    db,
    action: str,
    payload: dict,
    yacht_id: str,
    user_id: str,
    user_role: str,
    user_department: str,
    actor_name: str,
    change_summary: str = "",
) -> None:
    """
    Write one ledger_events row after a successful action.
    Non-fatal — logs warning on failure, never raises.
    All four security dimensions are stamped (yacht_id, user_id, user_role, department).
    """
    try:
        entity_type, entity_key = _ACTION_ENTITY_MAP.get(action, ("unknown", None))
        entity_id = str(payload.get(entity_key, "")) if entity_key else ""

        # Determine event_type from action name
        if any(w in action for w in ("create", "report", "add", "log")):
            event_type = "create"
        elif any(w in action for w in ("approve", "accept")):
            event_type = "approval"
        elif any(w in action for w in ("reject", "cancel", "close", "write_off")):
            event_type = "rejection"
        elif any(w in action for w in ("complete", "start", "submit")):
            event_type = "status_change"
        else:
            event_type = "update"

        now_iso = _ledger_dt.utcnow().isoformat()
        ev = {
            "yacht_id":     str(yacht_id),
            "user_id":      str(user_id),
            "user_role":    user_role,
            "department":   user_department,
            "actor_name":   actor_name,
            "event_category": "write",
            "event_type":   event_type,
            "action":       action,
            "entity_type":  entity_type,
            "entity_id":    entity_id or "00000000-0000-0000-0000-000000000000",
            "change_summary": change_summary or action.replace("_", " ").title(),
            "source_context": "microaction",
            "metadata":     {},
            "proof_hash":   _ledger_hl.sha256(
                (_ledger_json.dumps(
                    {k: str(ev_k) for k, ev_k in [
                        ("yacht_id", yacht_id), ("user_id", user_id),
                        ("event_type", event_type), ("entity_type", entity_type),
                        ("entity_id", entity_id), ("action", action),
                    ]}, sort_keys=True
                ) + now_iso).encode()
            ).hexdigest(),
        }
        db.table("ledger_events").insert(ev).execute()
    except Exception as _le:
        import logging
        logging.getLogger(__name__).warning(f"[Ledger] Non-fatal write failed for {action}: {_le}")
```

- [ ] **Step 4: Call `_write_ledger_event` after every successful action response**

Locate the response return point (from Step 1). Wrap the section after the action runs but before returning so that on success the ledger is written:

```python
# After action handler runs and response_data is built:
if response_data.get("status") == "success" or response_data.get("success") is True:
    _write_ledger_event(
        db=db,
        action=action,
        payload=payload,
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=user_role,
        user_department=user_department,
        actor_name=user_context.get("full_name") or user_context.get("email", ""),
        change_summary=response_data.get("message", ""),
    )
return JSONResponse(content=response_data)
```

- [ ] **Step 5: Test — run any action and verify ledger row appears**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
PART_ID="f7913ad1-6832-4169-b816-4538c8b7a417"

# Run create_shopping_list_item
RESP=$(curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"action\":\"create_shopping_list_item\",\"context\":{\"yacht_id\":\"$YACHT_ID\",\"part_id\":\"$PART_ID\"},\"payload\":{\"part_id\":\"$PART_ID\",\"source_type\":\"manual_add\"}}")
echo $RESP | python3 -m json.tool

# Check ledger — most recent row should have action = create_shopping_list_item
docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('ledger_events').select('action,entity_type,user_role,department,actor_name,created_at') \
    .eq('yacht_id','$YACHT_ID').order('created_at', desc=True).limit(3).execute()
for row in r.data: print(row)
"
```

**TWO SOURCES VERIFIED**: API `success:true` + `ledger_events` row with correct `action`, `user_role`, `department`, `actor_name`.

- [ ] **Step 6: Run a second action (approve_purchase_order as captain) — verify both dimensions**

```bash
# This proves the centralised write captures HOD actions too, without any per-handler code
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"action\":\"approve_purchase_order\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"purchase_order_id\":\"00000000-0000-0000-0000-000000000000\"}}" | python3 -m json.tool
# Even a 404 result means the middleware ran — check that a ledger row was NOT written on failure
docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('ledger_events').select('action,created_at').eq('action','approve_purchase_order') \
    .order('created_at', desc=True).limit(1).execute()
print('Ledger row on failure (should be empty):', r.data)
"
```

Expected: empty list — confirms ledger only writes on success.

- [ ] **Step 7: docker cp and commit**

```bash
docker cp apps/api/routes/p0_actions_routes.py celeste-api:/app/routes/p0_actions_routes.py
docker restart celeste-api && sleep 5 && curl -s http://localhost:8000/health
git add apps/api/routes/p0_actions_routes.py
git commit -m "feat: add centralised ledger middleware to p0_actions_routes — all mutations captured"
```

---

### Task 6: Add read beacon endpoint + role-scoped timeline endpoint

Two new endpoints are needed:

1. `POST /v1/ledger/read-event` — receives a frontend beacon when a user opens an entity page or document. Writes `event_category: "read"` to `ledger_events`.
2. `GET /v1/ledger/timeline` — returns the user's scoped timeline (self/department/all based on their role).

**File:** `apps/api/routes/ledger_routes.py`

- [ ] **Step 1: Add the read-event endpoint**

```python
@router.post("/read-event")
async def record_read_event(
    request: Request,
    user_context: dict = Depends(get_current_user),
    db=Depends(get_tenant_db),
):
    """
    Frontend beacon: called fire-and-forget when a user opens an entity page or document.
    Writes event_category='read' to ledger_events.
    """
    body = await request.json()
    entity_type = body.get("entity_type", "unknown")
    entity_id   = body.get("entity_id", "")
    metadata    = body.get("metadata", {})   # page, scroll_pct, duration_seconds, etc.

    yacht_id    = user_context.get("yacht_id")
    user_id     = user_context.get("sub")
    user_role   = user_context.get("role", "")
    department  = user_context.get("department", "")
    actor_name  = user_context.get("full_name") or user_context.get("email", "")

    if not yacht_id or not entity_id:
        return {"success": False, "error": "yacht_id and entity_id required"}

    try:
        import hashlib, json
        from datetime import datetime
        now_iso = datetime.utcnow().isoformat()
        ev = {
            "yacht_id":       str(yacht_id),
            "user_id":        str(user_id),
            "user_role":      user_role,
            "department":     department,
            "actor_name":     actor_name,
            "event_category": "read",
            "event_type":     "view",
            "action":         f"view_{entity_type}",
            "entity_type":    entity_type,
            "entity_id":      str(entity_id),
            "change_summary": f"Opened {entity_type.replace('_', ' ')}",
            "source_context": "read_beacon",
            "metadata":       metadata,
            "proof_hash":     hashlib.sha256(
                (json.dumps({"yacht_id": str(yacht_id), "user_id": str(user_id),
                    "event_type": "view", "entity_type": entity_type,
                    "entity_id": str(entity_id), "action": f"view_{entity_type}"},
                    sort_keys=True) + now_iso).encode()
            ).hexdigest(),
        }
        db.table("ledger_events").insert(ev).execute()
        return {"success": True}
    except Exception as e:
        logger.warning(f"[Ledger] Read beacon failed: {e}")
        return {"success": False}
```

- [ ] **Step 2: Add the role-scoped timeline endpoint**

```python
@router.get("/timeline")
async def get_ledger_timeline(
    limit: int = 50,
    offset: int = 0,
    event_category: Optional[str] = None,   # 'read' | 'write' | 'admin' | None (all)
    user_context: dict = Depends(get_current_user),
    db=Depends(get_tenant_db),
):
    """
    Role-scoped timeline:
      - captain  → sees all crew events on the yacht
      - HoD      → sees their department's events
      - crew     → sees only their own events
    """
    yacht_id   = user_context.get("yacht_id")
    user_id    = user_context.get("sub")
    user_role  = user_context.get("role", "")
    department = user_context.get("department", "")

    query = db.table("ledger_events") \
        .select("id, action, entity_type, entity_id, event_category, event_type, change_summary, "
                "user_role, department, actor_name, metadata, created_at") \
        .eq("yacht_id", str(yacht_id))

    # Apply role scope — MVP: role-based, not department-based
    # department column exists for future use but JWT does not yet carry it
    # TODO: replace HoD scope with .eq("department", department) when JWT carries department
    if user_role == "captain":
        pass  # all events for this yacht
    elif user_role in ("chief_engineer", "manager"):
        pass  # MVP: HoD sees all yacht events (same as captain); refine with department in next milestone
    else:
        query = query.eq("user_id", str(user_id))  # crew: self only

    if event_category:
        query = query.eq("event_category", event_category)

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"success": True, "events": result.data, "total": len(result.data)}
```

- [ ] **Step 3: Test read beacon**

```bash
TOKEN=$(cat /tmp/jwt_token.txt)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
WO_ID=$(docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('pms_work_orders').select('id').limit(1).execute()
print(r.data[0]['id'] if r.data else '')
")

curl -s -X POST http://localhost:8000/v1/ledger/read-event \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"entity_type\":\"work_order\",\"entity_id\":\"$WO_ID\",\"metadata\":{\"scroll_pct\":0}}" | python3 -m json.tool

# Verify DB row
docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('ledger_events').select('action,event_category,entity_type,metadata,created_at') \
    .eq('entity_id','$WO_ID').eq('event_category','read').order('created_at',desc=True).limit(1).execute()
print(r.data)
"
```

Expected: `{"success": true}` from API + DB row `{'action': 'view_work_order', 'event_category': 'read', ...}`.

- [ ] **Step 4: Test timeline — crew scope**

```bash
# Crew token → should only see own events
curl -s "http://localhost:8000/v1/ledger/timeline?limit=10" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -30
```

Expected: events list where all `user_id` values match the token's `sub`.

- [ ] **Step 5: docker cp and commit**

```bash
docker cp apps/api/routes/ledger_routes.py celeste-api:/app/routes/ledger_routes.py
docker restart celeste-api && sleep 5 && curl -s http://localhost:8000/health
git add apps/api/routes/ledger_routes.py
git commit -m "feat: add read-event beacon endpoint and role-scoped timeline to ledger_routes"
```

---

## Chunk 3: Frontend Audit Trail — Wire HistorySection to All 7 Lens Pages

> **MVP UX priority:** Do NOT style or polish this UI. The requirement is that the information is **organised, true, and functional**. Hierarchy, colours, icons, and visual polish are a separate pass. What matters: correct data, clickthrough navigation works, scope filtering returns the right records.

### What exists

- `HistorySection` component: `apps/web/src/components/lens/sections/HistorySection.tsx`
  - Props: `history: AuditLogEntry[]` (needs `id, action, actor, actor_id, timestamp, description`)
- Backend endpoint: `GET /v1/ledger/events/by-entity/{entity_type}/{entity_id}` (fixed in Task 4)
  - Returns: `{ success, events: [{yacht_id, user_id, actor_name, event_type, entity_type, entity_id, action, change_summary, created_at, metadata, ...}] }`
- New: `POST /v1/ledger/read-event` — frontend fires this when a lens page loads (Task 6)
- `actor_name` is now stored at write time (from Task 5 middleware) — use it directly. Fall back to `user_id.slice(0, 8)` only if blank.

### Entity type mapping

| Lens page | URL | Entity type for ledger |
|---|---|---|
| Work Orders | `/work-orders/[id]` | `work_order` |
| Faults | `/faults/[id]` | `fault` |
| Equipment | `/equipment/[id]` | `equipment` |
| Inventory / Parts | `/inventory/[id]` | `part` |
| Shopping List | `/shopping-list/[id]` | `shopping_list_item` — **verify**: the `[id]` in the URL must be an item UUID, not a list-level UUID. Task 5 writes `entity_id: item_id`. If the page routes by a parent list ID, the history query will return no results. Confirm in `shopping-list/[id]/page.tsx` before implementing. |
| Receiving | `/receiving/[id]` | `receiving` |
| Purchasing | `/purchasing/[id]` | `purchase_order` |

---

### Task 7: Create `useEntityLedger` hook and `useReadBeacon` hook

**Files:**
- Create: `apps/web/src/hooks/useEntityLedger.ts`
- Create: `apps/web/src/hooks/useReadBeacon.ts`

`useEntityLedger` fetches ledger events for a single entity and transforms them into `AuditLogEntry[]` with clickthrough navigation info. `useReadBeacon` fires the read event once when a page mounts.

- [ ] **Step 1: Write `useEntityLedger.ts`**

```typescript
// apps/web/src/hooks/useEntityLedger.ts
'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import type { AuditLogEntry } from '@/components/lens/sections/HistorySection';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Clickthrough navigation: entity_type → frontend route prefix
const ENTITY_ROUTES: Record<string, string> = {
  work_order:         '/work-orders',
  fault:              '/faults',
  equipment:          '/equipment',
  part:               '/inventory',
  shopping_list_item: '/shopping-list',
  receiving:          '/receiving',
  purchase_order:     '/purchasing',
  document:           '/documents',
  certificate:        '/certificates',
};

function buildNavigationUrl(entityType: string, entityId: string, metadata: Record<string, unknown>): string {
  const base = ENTITY_ROUTES[entityType];
  if (!base || !entityId) return '';
  let url = `${base}/${entityId}`;
  // For documents/manuals: append page param if available
  if (metadata?.page) url += `?page=${metadata.page}`;
  return url;
}

async function fetchEntityLedger(
  entityType: string,
  entityId: string,
  token: string
): Promise<AuditLogEntry[]> {
  const res = await fetch(
    `${API_BASE}/v1/ledger/events/by-entity/${entityType}/${entityId}?limit=50`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) return [];
  const json = await res.json();
  return (json.events || []).map((ev: Record<string, unknown>) => {
    const metadata = (ev.metadata as Record<string, unknown>) || {};
    return {
      id: (ev.id as string) || String(Math.random()),
      action: (ev.action as string) || 'unknown',
      // Use actor_name snapshot stored at write time; fall back to truncated user_id
      actor: (ev.actor_name as string) || (ev.user_id as string)?.slice(0, 8) || 'system',
      actor_id: ev.user_id as string,
      timestamp: (ev.created_at as string) || new Date().toISOString(),
      description: ev.change_summary as string | undefined,
      details: metadata,
      // Clickthrough: URL to open when user clicks this ledger entry
      navigation_url: buildNavigationUrl(
        ev.entity_type as string,
        ev.entity_id as string,
        metadata
      ),
    };
  });
}

/**
 * useEntityLedger — fetch audit history for a single entity.
 * Each entry includes navigation_url for clickthrough to the source entity.
 *
 * @param entityType  'work_order' | 'fault' | 'equipment' | 'part' |
 *                    'shopping_list_item' | 'receiving' | 'purchase_order'
 * @param entityId    UUID of the entity
 */
export function useEntityLedger(entityType: string, entityId: string | undefined) {
  const { session } = useAuth();
  const token = session?.access_token;

  return useQuery({
    queryKey: ['entity-ledger', entityType, entityId],
    queryFn: () => fetchEntityLedger(entityType, entityId!, token!),
    enabled: !!entityId && !!token,
    staleTime: 30_000,
    retry: 1,
  });
}
```

- [ ] **Step 2: Write `useReadBeacon.ts`**

```typescript
// apps/web/src/hooks/useReadBeacon.ts
'use client';

import * as React from 'react';
import { useAuth } from '@/hooks/useAuth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * useReadBeacon — fires a non-blocking read event to the ledger when a user opens an entity.
 * Call once per detail page mount. Never delays page load (fire-and-forget).
 *
 * @param entityType  e.g. 'work_order'
 * @param entityId    UUID — only fires when truthy
 * @param metadata    Optional: { page, scroll_pct, duration_seconds }
 */
export function useReadBeacon(
  entityType: string,
  entityId: string | undefined,
  metadata?: Record<string, unknown>
) {
  const { session } = useAuth();
  const token = session?.access_token;

  React.useEffect(() => {
    if (!entityId || !token) return;
    // Fire-and-forget — never await, never block render
    fetch(`${API_BASE}/v1/ledger/read-event`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId, metadata: metadata ?? {} }),
    }).catch(() => { /* intentionally silent */ });
  }, [entityType, entityId, token]); // re-fires if entity changes (navigating between items)
}
```

- [ ] **Step 3: Verify `AuditLogEntry` type includes `navigation_url`**

```bash
grep -n "navigation_url\|AuditLogEntry" apps/web/src/components/lens/sections/HistorySection.tsx
```

If `navigation_url` is not in the interface, add it:
```typescript
export interface AuditLogEntry {
  id: string;
  action: string;
  actor: string;
  actor_id?: string;
  timestamp: string;
  description?: string;
  details?: Record<string, unknown>;
  navigation_url?: string;   // ADD: clickthrough target — opens source entity
}
```

- [ ] **Step 4: Update `HistorySection` to render clickable entries**

Each entry in `HistorySection` should be clickable when `navigation_url` is present. MVP: wrap the entry in a `<button onClick={() => router.push(entry.navigation_url)}>` or an `<a href={entry.navigation_url}>`. No styling required beyond functionality.

```tsx
// Inside HistorySection, for each entry:
{entry.navigation_url ? (
  <a href={entry.navigation_url} className="block hover:underline">
    <span>{formatTime(entry.timestamp)}</span> — <span>{entry.actor}</span>{' '}
    <span>{entry.description || entry.action}</span>
  </a>
) : (
  <div>
    <span>{formatTime(entry.timestamp)}</span> — <span>{entry.actor}</span>{' '}
    <span>{entry.description || entry.action}</span>
  </div>
)}
```

- [ ] **Step 5: Verify exports and commit**

```bash
grep "HistorySection\|useEntityLedger\|useReadBeacon" \
  apps/web/src/components/lens/sections/index.ts \
  apps/web/src/hooks/index.ts 2>/dev/null | head -10
```

Add any missing exports. Then:

```bash
git add apps/web/src/hooks/useEntityLedger.ts \
        apps/web/src/hooks/useReadBeacon.ts \
        apps/web/src/components/lens/sections/HistorySection.tsx
git commit -m "feat: add useEntityLedger + useReadBeacon hooks with clickthrough navigation"
```
```

- [ ] **Step 2: Verify `AuditLogEntry` is exported from `HistorySection.tsx`**

```bash
grep -n "export.*AuditLogEntry\|export interface AuditLogEntry" \
  apps/web/src/components/lens/sections/HistorySection.tsx
```

Expected: `export interface AuditLogEntry {`. If not exported, add `export` keyword.

- [ ] **Step 3: Verify `HistorySection` is exported from sections index**

```bash
grep "HistorySection" apps/web/src/components/lens/sections/index.ts
```

If not present, add: `export { HistorySection } from './HistorySection';`

- [ ] **Step 4: Commit the hook**

```bash
git add apps/web/src/hooks/useEntityLedger.ts apps/web/src/components/lens/sections/HistorySection.tsx apps/web/src/components/lens/sections/index.ts
git commit -m "feat: add useEntityLedger hook for per-entity audit trail fetch"
```

---

### Task 8: Wire HistorySection into each of the 7 lens pages

The pattern is the same for all 7 pages. Below is the complete work-orders example; subsequent pages follow identically with only the `entityType` string changing.

**Files to modify:**
- `apps/web/src/app/work-orders/[id]/page.tsx`
- `apps/web/src/app/faults/[id]/page.tsx`
- `apps/web/src/app/equipment/[id]/page.tsx`
- `apps/web/src/app/inventory/[id]/page.tsx`
- `apps/web/src/app/shopping-list/[id]/page.tsx`
- `apps/web/src/app/receiving/[id]/page.tsx`
- `apps/web/src/app/purchasing/[id]/page.tsx`

---

#### 8a: Work Orders page

- [ ] **Step 1: Open `apps/web/src/app/work-orders/[id]/page.tsx`**

The `WorkOrderContent` component renders the main body. It already renders `AttachmentsSection` and `RelatedEntitiesSection`. Add `HistorySection` at the bottom of the rendered content.

- [ ] **Step 2: Add imports to `work-orders/[id]/page.tsx`**

Add to the existing import from `'@/components/lens/sections'`:
```typescript
// BEFORE:
import { AttachmentsSection, RelatedEntitiesSection, ... } from '@/components/lens/sections';
// AFTER:
import { AttachmentsSection, RelatedEntitiesSection, HistorySection, ... } from '@/components/lens/sections';
```

Add hook imports:
```typescript
import { useEntityLedger } from '@/hooks/useEntityLedger';
import { useReadBeacon } from '@/hooks/useReadBeacon';
```

- [ ] **Step 3: Add hook calls inside `WorkOrderContent` (where `workOrderId` is available)**

```typescript
// Fetch ledger history for this entity
const { data: history = [] } = useEntityLedger('work_order', workOrderId);

// Fire read beacon once on mount (court-of-law: records that this user opened this entity)
useReadBeacon('work_order', workOrderId);
```

- [ ] **Step 4: Render `HistorySection` at the bottom of the JSX return**

```tsx
{/* Activity History — MVP: functional, not styled */}
{history.length > 0 && (
  <HistorySection history={history} pageSize={20} />
)}
```

- [ ] **Step 5: Build check**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | grep -i "work-orders" | head -10
```

Expected: no TypeScript errors related to work-orders page.

---

#### 8b–8g: Repeat for remaining 6 pages

Apply the **exact same pattern** (Steps 1–5) for:

| Page | Component with entity ID var | entityType string |
|---|---|---|
| `faults/[id]/page.tsx` | `FaultContent` / `faultId` | `'fault'` |
| `equipment/[id]/page.tsx` | `EquipmentContent` / `equipmentId` | `'equipment'` |
| `inventory/[id]/page.tsx` | content component / `partId` | `'part'` |
| `shopping-list/[id]/page.tsx` | content component / `shoppingListId` | `'shopping_list_item'` |
| `receiving/[id]/page.tsx` | `ReceivingContent` / `receivingId` | `'receiving'` |
| `purchasing/[id]/page.tsx` | content component / `purchaseOrderId` | `'purchase_order'` |

For each page:
- [ ] Add `HistorySection` to the section import
- [ ] Add `useEntityLedger` and `useReadBeacon` imports
- [ ] Add `useEntityLedger('entity_type', entityId)` and `useReadBeacon('entity_type', entityId)` hook calls
- [ ] Render `{history.length > 0 && <HistorySection history={history} />}` at bottom of content

- [ ] **Step: Full TypeScript build check after all 7 pages**

```bash
cd apps/web && npx tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step: Commit**

```bash
git add apps/web/src/app/work-orders/[id]/page.tsx \
        apps/web/src/app/faults/[id]/page.tsx \
        apps/web/src/app/equipment/[id]/page.tsx \
        apps/web/src/app/inventory/[id]/page.tsx \
        apps/web/src/app/shopping-list/[id]/page.tsx \
        apps/web/src/app/receiving/[id]/page.tsx \
        apps/web/src/app/purchasing/[id]/page.tsx
git commit -m "feat: wire HistorySection to all 7 lens pages via useEntityLedger hook"
```

---

### Task 9: End-to-end frontend verification (Docker)

- [ ] **Step 1: Rebuild the web container with the frontend changes**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
docker compose build celeste-web
docker compose up -d celeste-web
```

- [ ] **Step 2: Perform an action that writes a ledger event**

E.g., call `start_work_order` via the API:
```bash
TOKEN=$(cat /tmp/jwt_token.txt)
WO_ID=$(docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('pms_work_orders').select('id').eq('status','planned').limit(1).execute()
print(r.data[0]['id'] if r.data else '')
")
curl -s -X POST http://localhost:8000/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"action\":\"start_work_order\",\"context\":{\"yacht_id\":\"85fe1119-b04c-41ac-80f1-829d23322598\"},\"payload\":{\"work_order_id\":\"$WO_ID\"}}" | python3 -m json.tool
```

- [ ] **Step 3: Verify ledger event exists for that work order**

```bash
docker exec celeste-api python3 -c "
import os; from supabase import create_client
c = create_client(os.environ['yTEST_YACHT_001_SUPABASE_URL'], os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY'])
r = c.table('ledger_events').select('id,action,created_at').eq('entity_id','$WO_ID').order('created_at', desc=True).limit(5).execute()
for row in r.data: print(row)
"
```

Expected: at least one row with `action: 'start_work_order'`.

- [ ] **Step 4: Open the work order detail page in browser**

Navigate to: `http://localhost:3000/work-orders/<WO_ID>`

Verify the **Activity History** section appears at the bottom of the page with the `start_work_order` entry visible.

**TWO SOURCES VERIFIED**: DB has ledger event + page renders it on screen.

- [ ] **Step 5: Commit final verification**

If any fixes were needed during E2E, commit them now.

---

## Chunk 4: RLS Upgrade Migration

> **Note:** This chunk is defense-in-depth. The API uses service role keys which bypass RLS. This is still important for: direct DB access via Supabase dashboard, any future client-side queries, and multi-yacht enforcement at the DB layer.

### What exists vs what's needed

| Table | Current RLS function | Target |
|---|---|---|
| `pms_work_orders` | `get_user_yacht_id()` — single yacht only | `has_yacht_access()` |
| `pms_work_order_notes` | `get_user_yacht_id()` | `has_yacht_access()` |
| `pms_faults` | `get_user_yacht_id()` | `has_yacht_access()` |
| `pms_parts` | `get_user_yacht_id()` | `has_yacht_access()` |
| `pms_equipment` | `has_yacht_access()` ✅ | Already done (Migration 12) |
| `pms_shopping_list_items` | `get_user_yacht_id()` | `has_yacht_access()` |
| `pms_receiving` | MISSING — no RLS | `has_yacht_access()` |
| `pms_purchase_orders` | MISSING — no RLS | `has_yacht_access()` |
| `ledger_events` | MISSING | `has_yacht_access()` |

### Task 10: Write and apply Migration 13

**File:** `database/migrations/13_upgrade_rls_has_yacht_access.sql` (new file)

- [ ] **Step 1: Verify `has_yacht_access()` function exists in the tenant DB**

```bash
docker exec celeste-api python3 -c "
import os; from supabase import create_client
url = os.environ['yTEST_YACHT_001_SUPABASE_URL']
key = os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY']
c = create_client(url, key)
# Call the function with a known yacht_id
r = c.rpc('has_yacht_access', {'target_yacht_id': '85fe1119-b04c-41ac-80f1-829d23322598'}).execute()
print('has_yacht_access exists:', r.data)
"
```

Expected: `True` or `False` (not an error). If it errors, `has_yacht_access()` is not deployed yet — you must deploy Migration 12 first (see `database/migrations/12_fix_multi_yacht_rls.sql`).

- [ ] **Step 2: Write the migration file**

```sql
-- Migration 13: Upgrade remaining PMS tables to has_yacht_access() RLS
-- Date: 2026-03-13
-- Prerequisite: Migration 12 (has_yacht_access function must exist)

-- ================================================================
-- HELPER: Template macro for each table
-- Drops old get_user_yacht_id() policies, creates has_yacht_access() policies
-- ================================================================

DO $$
DECLARE
  tbl text;
  tbls text[] := ARRAY[
    'pms_work_orders',
    'pms_work_order_notes',
    'pms_work_order_parts',
    'pms_faults',
    'pms_parts',
    'pms_part_usage',
    'pms_handover',
    'pms_shopping_list_items'
  ];
BEGIN
  FOREACH tbl IN ARRAY tbls
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', tbl);

    -- Drop old policies (any name pattern)
    EXECUTE format('DROP POLICY IF EXISTS "%s_select_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_insert_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_update_yacht_scope" ON public.%I', tbl, tbl);
    EXECUTE format('DROP POLICY IF EXISTS "%s_delete_yacht_scope" ON public.%I', tbl, tbl);
    -- Also drop any legacy name variants
    EXECUTE format('DROP POLICY IF EXISTS "Users can view %s on their yacht" ON public.%I', tbl, tbl);

    -- Create new policies using has_yacht_access()
    EXECUTE format(
      'CREATE POLICY "%s_select_yacht_scope" ON public.%I FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_insert_yacht_scope" ON public.%I FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_update_yacht_scope" ON public.%I FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );
    EXECUTE format(
      'CREATE POLICY "%s_delete_yacht_scope" ON public.%I FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id))',
      tbl, tbl
    );

    -- Add immutability trigger
    EXECUTE format('DROP TRIGGER IF EXISTS trg_prevent_yacht_id_change ON public.%I', tbl);
    EXECUTE format(
      'CREATE TRIGGER trg_prevent_yacht_id_change BEFORE UPDATE ON public.%I FOR EACH ROW EXECUTE FUNCTION public.prevent_yacht_id_change()',
      tbl
    );

    RAISE NOTICE 'Upgraded RLS for: %', tbl;
  END LOOP;
END $$;

-- ================================================================
-- Tables that need RLS added from scratch
-- ================================================================

-- pms_receiving
ALTER TABLE public.pms_receiving ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_receiving FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pms_receiving_select_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_insert_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_update_yacht_scope" ON public.pms_receiving;
DROP POLICY IF EXISTS "pms_receiving_delete_yacht_scope" ON public.pms_receiving;

CREATE POLICY "pms_receiving_select_yacht_scope" ON public.pms_receiving
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_insert_yacht_scope" ON public.pms_receiving
  FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_update_yacht_scope" ON public.pms_receiving
  FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_receiving_delete_yacht_scope" ON public.pms_receiving
  FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id));

-- pms_purchase_orders
ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_purchase_orders FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pms_purchase_orders_select_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_insert_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_update_yacht_scope" ON public.pms_purchase_orders;
DROP POLICY IF EXISTS "pms_purchase_orders_delete_yacht_scope" ON public.pms_purchase_orders;

CREATE POLICY "pms_purchase_orders_select_yacht_scope" ON public.pms_purchase_orders
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_insert_yacht_scope" ON public.pms_purchase_orders
  FOR INSERT TO authenticated WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_update_yacht_scope" ON public.pms_purchase_orders
  FOR UPDATE TO authenticated USING (public.has_yacht_access(yacht_id)) WITH CHECK (public.has_yacht_access(yacht_id));
CREATE POLICY "pms_purchase_orders_delete_yacht_scope" ON public.pms_purchase_orders
  FOR DELETE TO authenticated USING (public.has_yacht_access(yacht_id));

-- ledger_events (read-only for authenticated, inserts via service role only)
ALTER TABLE public.ledger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ledger_events_select_yacht_scope" ON public.ledger_events;
DROP POLICY IF EXISTS "ledger_events_insert_service_only" ON public.ledger_events;

CREATE POLICY "ledger_events_select_yacht_scope" ON public.ledger_events
  FOR SELECT TO authenticated USING (public.has_yacht_access(yacht_id));
-- Inserts only via service_role (API writes):
CREATE POLICY "ledger_events_insert_service_only" ON public.ledger_events
  FOR INSERT TO service_role WITH CHECK (true);
```

- [ ] **Step 2b: Check that `prevent_yacht_id_change()` function exists before using it**

```bash
docker exec celeste-api python3 -c "
import os; from supabase import create_client
url = os.environ['yTEST_YACHT_001_SUPABASE_URL']
key = os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY']
c = create_client(url, key)
# pg_proc query via rpc won't work directly; use a try/catch on a dummy trigger
print('Checking prevent_yacht_id_change exists...')
" 2>&1
```

In the Supabase SQL Editor for the tenant project, run this preflight check:
```sql
SELECT proname FROM pg_proc WHERE proname = 'prevent_yacht_id_change';
```

- If the function exists: proceed with migration as written.
- If the function does NOT exist: remove all `EXECUTE format('CREATE TRIGGER trg_prevent_yacht_id_change ...')` lines from the migration before applying, or deploy Migration 12 first (`database/migrations/12_fix_multi_yacht_rls.sql`).

- [ ] **Step 3: Apply the migration via Supabase SQL Editor**

> **Why SQL Editor, not psql:** The API container (`celeste-api`) does not have `psql` installed and does not expose `DATABASE_URL` as a connection string. Supabase migrations are applied directly through the Supabase dashboard.

1. Open the tenant Supabase project in your browser (use the URL from `yTEST_YACHT_001_SUPABASE_URL` env var)
2. Navigate to **SQL Editor** (left sidebar)
3. Click **New query**
4. Copy the full contents of `database/migrations/13_upgrade_rls_has_yacht_access.sql`
5. Paste into the editor and click **Run**

Expected output in the results pane: multiple `NOTICE: Upgraded RLS for: pms_work_orders` etc. lines, no red errors.

- [ ] **Step 4: Verify RLS is active — test that a non-yacht user can't read records**

```bash
docker exec celeste-api python3 -c "
import os; from supabase import create_client
# Use a JWT that has no yacht access — we can't easily do this with service key
# Instead, verify the policies exist via pg_policies
url = os.environ['yTEST_YACHT_001_SUPABASE_URL']
key = os.environ['yTEST_YACHT_001_SUPABASE_SERVICE_KEY']
c = create_client(url, key)
# Verify policies created
r = c.rpc('check_rls_policies', {}).execute() if False else None
# Simpler: query pg_policies via raw SQL would need psql
print('Migration applied — verify via Supabase dashboard > Authentication > Policies')
"
```

Verify in Supabase dashboard that the 8 tables now show `has_yacht_access` policies.

- [ ] **Step 5: Commit**

```bash
git add database/migrations/13_upgrade_rls_has_yacht_access.sql
git commit -m "feat: upgrade all PMS tables to has_yacht_access() RLS (migration 13)"
```

---

## Final Verification Checklist

Run after all chunks complete:

**Role Security**
- [ ] `approve_purchase_order` with `crew` role token → 403
- [ ] `cancel_purchase_order` with `crew` role token → 403
- [ ] `mark_shopping_list_ordered` with `crew` role token → 403
- [ ] `accept_receiving` with `crew` role token → NOT 403 (ALL roles — lens-05)

**Ledger Write Completeness (four dimensions)**
- [ ] Any action via `/v1/actions/execute` → `ledger_events` row has `yacht_id`, `user_id`, `user_role`, `department`, `actor_name` all populated
- [ ] Ledger row only written on `success: true` — NOT on 403/404 failures
- [ ] `GET /v1/ledger/events/by-entity/work_order/<id>` returns events ordered by `created_at` descending, no 500

**Read Beacon**
- [ ] `POST /v1/ledger/read-event` for a work order → `event_category: "read"` row in `ledger_events`
- [ ] Opening any lens page fires the read beacon (check network tab or DB row)

**Timeline Scope**
- [ ] `GET /v1/ledger/timeline` with crew token → events contain only that user's `user_id`
- [ ] With captain token → events from multiple users on the same yacht

**Frontend**
- [ ] All 7 lens pages show Activity History section with at least one entry
- [ ] Clicking a history entry navigates to the correct entity route
- [ ] No styling required — verify data is present and links work

**RLS**
- [ ] Supabase dashboard shows `has_yacht_access` policies on all 9 tables

**Two-source rule**
- [ ] Every verification above checks both API response AND direct DB query

---

## Summary of Files Changed

| File | Change type | Chunk |
|---|---|---|
| `apps/api/routes/p0_actions_routes.py` | Add PURCHASE_ORDER_ROLES, RECEIVING_ROLES, equipment/SL checks | 1 |
| `apps/api/handlers/shopping_list_handlers.py` | Add ledger_events writes to 3 handler methods | 2 |
| `apps/api/routes/ledger_routes.py` | Fix event_timestamp → created_at bug | 2 |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Add ledger writes to accept/reject receiving wrappers | 2 |
| `apps/web/src/hooks/useEntityLedger.ts` | New file — fetch entity history | 3 |
| `apps/web/src/app/work-orders/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/faults/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/equipment/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/inventory/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/shopping-list/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/receiving/[id]/page.tsx` | Add HistorySection | 3 |
| `apps/web/src/app/purchasing/[id]/page.tsx` | Add HistorySection | 3 |
| `database/migrations/13_upgrade_rls_has_yacht_access.sql` | New file — RLS upgrade migration | 4 |
