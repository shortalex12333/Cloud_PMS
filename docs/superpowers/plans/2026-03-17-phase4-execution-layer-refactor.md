# Phase 4: Execution Layer Refactor

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the lower half of the elif chain in `p0_actions_routes.py` (lines 2491–end, ~5,000 lines) with a dispatch table and per-domain handler files, baking in `resolve_entity_context()` at the dispatcher level.

**Architecture:** Strangler fig migration. The dispatcher gains a `HANDLERS` dict and `resolve_entity_context()` on day one, with zero behavior change — all actions still fall through to the existing elif chain until explicitly migrated. Each task migrates one domain cluster from lines 2491–end, moves the logic to a handler file, and verifies with E2E. After all clusters are migrated, only lines 2491–end are deleted. Lines 1192–2490 (fault, part lens, complex WO actions) are **explicitly out of scope** — they will be Phase 5. Zero frontend changes in this phase.

**Tech Stack:** Python 3.9, FastAPI, Supabase Python client, pytest + pytest-asyncio (unit), Playwright E2E (shard verification).

---

## Critical orientation — read before starting any task

`p0_actions_routes.py` has this structure inside `execute_action`:

```
Line 727:   JWT validation
Line 741:   Tenant resolution
Line 782:   Yacht isolation
Line 809:   Role check (registry)
Line 850:   REQUIRED_FIELDS validation dict
Line 990:   Required field enforcement
Line 1011:  Input sanitisation
Line 1057:  FAULT_LENS_ROLES dict + check
Line 1111:  FAULT_LENS_ROLES enforcement
Line 1136:  PART_LENS_SIGNED_ROLES dict + check
Line 1162:  WORK_ORDER_LENS_ROLES dict + check
Line 1188:  ← INSERTION POINT for resolve_entity_context + HANDLERS dispatch
Line 1189:  # Route to handler based on action name
Line 1190:  try:
Line 1192:    if action == "create_work_order_from_fault":   ← PHASE 5 territory (do not touch)
              ...fault actions, part lens actions, complex WO actions...
Line 2491:    elif action in ("update_work_order", "update_wo"):  ← PHASE 4 starts here
              ...actions being migrated in this plan...
Line ~6350:   else: unknown action error  ← keep this
```

**Do NOT modify or delete anything between lines 1192 and 2490.** That block is in scope for Phase 5.

**`REQUIRED_FIELDS`, `FAULT_LENS_ROLES`, `PART_LENS_SIGNED_ROLES`, `WORK_ORDER_LENS_ROLES` dicts** all stay in the dispatcher permanently. They are not part of the elif chain.

---

## File Structure

```
apps/api/
  routes/
    p0_actions_routes.py           ← MODIFY: insert dispatch scaffold at line 1188; delete lines 2491–end in Task 6
    handlers/
      __init__.py                  ← CREATE: merges all domain HANDLERS dicts
      ledger_utils.py              ← CREATE: extract build_ledger_event here (avoids circular import)
      work_order_handler.py        ← CREATE: 11 elif groups
      purchase_order_handler.py    ← CREATE: 4 elif groups
      receiving_handler.py         ← CREATE: 3 elif groups
      crew_handler.py              ← CREATE: 3 elif groups
      hours_of_rest_handler.py     ← CREATE: 2 elif groups (HoR + monthly signoffs)
      certificate_handler.py       ← CREATE: 2 elif groups (lines 2872–2882 AND 5714–5777)
      document_handler.py          ← CREATE: 1 elif group
      handover_handler.py          ← CREATE: 1 elif group
      shopping_handler.py          ← CREATE: 2 elif groups
      pm_handler.py                ← CREATE: 1 elif group
  tests/
    handlers/
      __init__.py                  ← CREATE: empty
      test_work_order_handler.py   ← CREATE
      test_purchase_order_handler.py ← CREATE
      test_receiving_handler.py    ← CREATE
```

**Handler function contract (identical for all handlers):**

```python
async def action_name(
    payload: dict,          # request.payload — from client
    context: dict,          # resolve_entity_context() output — entity_id already mapped to domain key
    yacht_id: str,          # server-resolved, yacht isolation already validated
    user_id: str,           # from JWT, validated by dispatcher
    user_context: dict,     # {role, tenant_key_alias, department}
    db_client: Client,      # pre-constructed by dispatcher — do NOT call get_tenant_supabase_client inside handlers
) -> dict:                  # always {"status": "success"|"error", ...}
```

---

## Cluster → Handler file mapping (Phase 4 scope only — lines 2491–end)

| Handler file | Elif line ranges | Action names (canonical + aliases) |
|---|---|---|
| `work_order_handler.py` | 2492–2842, 6277–6318 | update_work_order (update_wo), assign_work_order (assign_wo), close_work_order (complete_work_order), add_wo_hours (log_work_hours), add_wo_part (add_part_to_wo), add_wo_note (add_note_to_wo), start_work_order (begin_wo), cancel_work_order (cancel_wo), create_work_order (create_wo), view_work_order_detail (view_work_order, get_work_order), create_work_order_for_equipment |
| `purchase_order_handler.py` | 6153–6276 | submit_purchase_order, approve_purchase_order, mark_po_received, cancel_purchase_order |
| `receiving_handler.py` | 6066–6152 | submit_receiving_for_review, edit_receiving, create_receiving, attach_receiving_image_with_comment |
| `crew_handler.py` | 5942–6013 | create_crew_template, apply_crew_template, list_crew_templates, list_crew_warnings, acknowledge_warning, dismiss_warning |
| `hours_of_rest_handler.py` | 5853–5941 | get_hours_of_rest, upsert_hours_of_rest, get_monthly_signoff, list_monthly_signoffs, create_monthly_signoff, sign_monthly_signoff |
| `certificate_handler.py` | **2872–2882 AND 5714–5777** | add_certificate, renew_certificate, add_service_contract, record_contract_claim, create_vessel_certificate, create_crew_certificate |
| `document_handler.py` | 6014–6065 | upload_document, update_document, delete_document + remaining document actions |
| `handover_handler.py` | 2863–2871 | create_handover, acknowledge_handover, update_handover, delete_handover, filter_handover |
| `shopping_handler.py` | 5778–5852, 6318–6350 | create_shopping_list_item, approve_shopping_list_item, mark_shopping_list_ordered |
| `pm_handler.py` | 2855–2862 | create_pm_schedule, record_pm_completion, defer_pm_task, update_pm_schedule, view_pm_due_list |

> **Note on certificate handler:** There are two separate elif blocks for certificates: lines 2872–2882 (add_certificate, renew_certificate, add_service_contract, record_contract_claim) and lines 5714–5777 (create_vessel_certificate, create_crew_certificate). Both must go into a single `certificate_handler.py`. Read both blocks before implementing.

> **Note on receiving handler:** The elif block at line 6114 for `create_receiving` dispatches through an `internal_dispatcher` helper. Read that call site carefully before implementing — you are calling the same helper, not reimplementing its logic.

---

## Task 1: Dispatch scaffold + resolve_entity_context (strangler fig, zero behavior change)

**Files:**
- Modify: `apps/api/routes/p0_actions_routes.py` (two insertions: module-level function, one dispatch block at line 1188)
- Create: `apps/api/routes/handlers/__init__.py`
- Create: `apps/api/routes/handlers/ledger_utils.py`

### Step 1a — Read the insertion point region

- [ ] **Read lines 1180–1200 to see the exact insertion point:**

```bash
sed -n '1180,1200p' apps/api/routes/p0_actions_routes.py
```

You will see the end of the `WORK_ORDER_LENS_ROLES` check closing at line 1187, followed by `# Route to handler based on action name` at line 1189 and `try:` at line 1190. The insertion goes between line 1187 and line 1189.

### Step 1b — Extract build_ledger_event to avoid circular imports

Handler files need `build_ledger_event` (currently defined at line 57 of `p0_actions_routes.py`). Importing it back from `p0_actions_routes.py` inside a handler creates a circular import: `p0_actions_routes` → `handlers/__init__` → `work_order_handler` → `p0_actions_routes`. Instead, move it to a shared utility.

- [ ] **Read `build_ledger_event` (lines 57–130 approx) in full:**

```bash
sed -n '57,135p' apps/api/routes/p0_actions_routes.py
```

- [ ] **Create `apps/api/routes/handlers/ledger_utils.py`** — copy the function verbatim:

```python
"""
Ledger helper — shared by dispatcher and all handler files.
Extracted from p0_actions_routes.py to avoid circular imports.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional


def build_ledger_event(
    yacht_id: str,
    user_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    user_role: str = None,
    # ... copy exact signature from p0_actions_routes.py line 57 ...
) -> dict:
    # ... copy body verbatim ...
```

- [ ] **Update `p0_actions_routes.py` to import from the new location** — replace the function definition with an import:

```python
# Ledger helper (moved to handlers/ledger_utils.py — imported here for backward compat)
from routes.handlers.ledger_utils import build_ledger_event
```

- [ ] **Verify the API still starts after this change:**

```bash
cd apps/api && python3 -c "from pipeline_service import app; print('Import OK')"
```

### Step 1c — Add resolve_entity_context module-level function

- [ ] **Insert `resolve_entity_context()` as a module-level function** in `p0_actions_routes.py`, above the `execute_action` route (around line 710, before the `@router.post("/execute")` decorator):

```python
# ---------------------------------------------------------------------------
# ENTITY CONTEXT NORMALISATION (Phase 4)
# Maps generic entity_id → domain-specific keys based on action name.
# useEntityLens surfaces always send entity_id; standalone forms send
# domain keys (equipment_id, fault_id, etc.) directly.
# Uses setdefault — if the domain key is already present it is NOT overwritten.
# ---------------------------------------------------------------------------

_EQUIPMENT_ACTIONS = frozenset({
    "create_work_order_for_equipment", "update_equipment_status",
    "flag_equipment_attention", "add_equipment_note",
    "show_manual_section", "view_equipment_details",
    "view_equipment_history", "view_equipment_parts",
    "view_linked_faults", "view_equipment_manual",
    "view_fault_history", "view_work_order_history",
    "suggest_parts",
})

_FAULT_ACTIONS = frozenset({
    "close_fault", "diagnose_fault", "acknowledge_fault", "resolve_fault",
    "reopen_fault", "mark_fault_false_alarm", "create_work_order_from_fault",
    "update_fault", "add_fault_photo", "view_fault_detail",
    "add_fault_note", "report_fault",
})

_WORK_ORDER_ACTIONS = frozenset({
    "update_work_order", "update_wo", "assign_work_order", "assign_wo",
    "close_work_order", "complete_work_order", "add_wo_hours", "log_work_hours",
    "add_wo_part", "add_part_to_wo", "add_wo_note", "add_note_to_wo",
    "start_work_order", "begin_wo", "cancel_work_order", "cancel_wo",
    "view_work_order_detail", "view_work_order", "get_work_order",
    "add_work_order_photo", "mark_work_order_complete",
    "add_note_to_work_order", "add_part_to_work_order",
    "reassign_work_order", "archive_work_order",
})

_PART_ACTIONS = frozenset({
    "consume_part", "receive_part", "transfer_part", "adjust_stock_quantity",
    "write_off_part", "add_to_shopping_list", "view_part_stock",
    "view_part_location", "view_part_usage", "view_linked_equipment",
    "view_part_details", "check_stock_level", "log_part_usage",
})


def resolve_entity_context(action: str, context: dict) -> dict:
    """
    Normalise incoming context so handlers receive domain-specific keys.

    Callers from useEntityLens surfaces send `entity_id`.
    Callers from standalone forms send `equipment_id`, `fault_id`, etc. directly.
    After this function, both paths produce the same context shape for handlers.

    Uses setdefault — existing domain keys are never overwritten.
    """
    ctx = dict(context)
    entity_id = ctx.get("entity_id")

    if entity_id:
        if action in _EQUIPMENT_ACTIONS:
            ctx.setdefault("equipment_id", entity_id)
        elif action in _FAULT_ACTIONS:
            ctx.setdefault("fault_id", entity_id)
        elif action in _WORK_ORDER_ACTIONS:
            ctx.setdefault("work_order_id", entity_id)
        elif action in _PART_ACTIONS:
            ctx.setdefault("part_id", entity_id)

    return ctx
```

### Step 1d — Add the dispatch block and HANDLERS import

- [ ] **At the top of `p0_actions_routes.py` (module-level imports), add:**

```python
from routes.handlers import HANDLERS as _ACTION_HANDLERS
```

> This import is safe at module level because `handlers/__init__.py` starts with `HANDLERS: dict = {}` (empty). No circular import.

- [ ] **Insert the dispatch block at line 1188** — between the closing of `WORK_ORDER_LENS_ROLES` check and the `# Route to handler` comment.

Find the exact location with:
```bash
grep -n "Route to handler based on action name" apps/api/routes/p0_actions_routes.py
```

Insert before that line:

```python
    # ========================================================================
    # ENTITY CONTEXT NORMALISATION + HANDLER DISPATCH (Phase 4)
    # resolve_entity_context maps entity_id → domain key once for all handlers.
    # Registered handlers return here. Unregistered actions fall through to the
    # legacy try/elif chain below. Delete the chain only after all actions migrated.
    # ========================================================================
    resolved_context = resolve_entity_context(action, request.context)

    if action in _ACTION_HANDLERS:
        tenant_alias = user_context.get("tenant_key_alias", "")
        db_client = get_tenant_supabase_client(tenant_alias)
        return await _ACTION_HANDLERS[action](
            payload=payload,
            context=resolved_context,
            yacht_id=yacht_id,
            user_id=user_id,
            user_context=user_context,
            db_client=db_client,
        )

    # Legacy elif chain — handles all actions not yet migrated to HANDLERS
```

### Step 1e — Create handlers/__init__.py (empty registry)

- [ ] **Create `apps/api/routes/handlers/__init__.py`:**

```python
# handlers/__init__.py
#
# Merges all domain handler registries into a single HANDLERS dict.
# The dispatcher imports this at module level.
#
# Activation pattern: each task uncomments its import + adds to HANDLERS.
# The uncomment IS the deployment gate — if the handler file has bugs,
# the import fails at startup (safe, visible failure).
#
# Current state: HANDLERS is empty — all actions fall through to legacy elif chain.

# from .work_order_handler import HANDLERS as WO_HANDLERS       # activate in Task 2
# from .purchase_order_handler import HANDLERS as PO_HANDLERS   # activate in Task 3
# from .receiving_handler import HANDLERS as REC_HANDLERS        # activate in Task 3
# from .crew_handler import HANDLERS as CREW_HANDLERS            # activate in Task 4
# from .hours_of_rest_handler import HANDLERS as HOR_HANDLERS    # activate in Task 4
# from .certificate_handler import HANDLERS as CERT_HANDLERS     # activate in Task 5
# from .document_handler import HANDLERS as DOC_HANDLERS         # activate in Task 5
# from .handover_handler import HANDLERS as HAND_HANDLERS        # activate in Task 5
# from .shopping_handler import HANDLERS as SHOP_HANDLERS        # activate in Task 5
# from .pm_handler import HANDLERS as PM_HANDLERS                # activate in Task 5

HANDLERS: dict = {}
```

### Step 1f — Verify scaffold: zero behavior change

- [ ] **Unit test — resolve_entity_context covers all four domain mappings:**

```bash
cd apps/api && python3 -c "
from routes.p0_actions_routes import resolve_entity_context

# equipment
ctx = resolve_entity_context('create_work_order_for_equipment', {'entity_id': 'eq-1', 'yacht_id': 'y'})
assert ctx['equipment_id'] == 'eq-1', f'FAIL: {ctx}'

# fault
ctx2 = resolve_entity_context('close_fault', {'entity_id': 'f-2', 'yacht_id': 'y'})
assert ctx2['fault_id'] == 'f-2', f'FAIL: {ctx2}'

# work order
ctx3 = resolve_entity_context('update_work_order', {'entity_id': 'wo-3', 'yacht_id': 'y'})
assert ctx3['work_order_id'] == 'wo-3', f'FAIL: {ctx3}'

# setdefault — existing domain key not overwritten
ctx4 = resolve_entity_context('close_fault', {'entity_id': 'x', 'fault_id': 'real', 'yacht_id': 'y'})
assert ctx4['fault_id'] == 'real', f'FAIL setdefault: {ctx4}'

# unknown action — entity_id left as-is
ctx5 = resolve_entity_context('unknown_action', {'entity_id': 'z', 'yacht_id': 'y'})
assert 'equipment_id' not in ctx5, f'FAIL unknown: {ctx5}'

print('All resolve_entity_context assertions passed')
"
```

- [ ] **API starts cleanly:**

```bash
cd apps/api && python3 -c "from pipeline_service import app; print('Import OK')"
```

Expected: `Import OK` with no errors.

- [ ] **HANDLERS is empty — confirming zero behavior change:**

```bash
cd apps/api && python3 -c "
from routes.handlers import HANDLERS
assert len(HANDLERS) == 0, f'Expected empty, got {len(HANDLERS)} entries'
print('HANDLERS is empty — all actions fall through to legacy chain. OK')
"
```

- [ ] **Commit:**

```bash
git add apps/api/routes/p0_actions_routes.py \
        apps/api/routes/handlers/__init__.py \
        apps/api/routes/handlers/ledger_utils.py
git commit -m "feat(phase4): add dispatch scaffold, resolve_entity_context, extract build_ledger_event

Strangler fig: HANDLERS is empty, all actions fall through to legacy elif.
resolve_entity_context() normalises entity_id → domain keys at dispatcher level.
build_ledger_event moved to handlers/ledger_utils.py to avoid future circular imports.
Zero behavior change — existing E2E suite unaffected.

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Task 2: Migrate work order handlers

**Files:**
- Create: `apps/api/routes/handlers/work_order_handler.py`
- Create: `apps/api/tests/handlers/__init__.py` (empty)
- Create: `apps/api/tests/handlers/test_work_order_handler.py`
- Modify: `apps/api/routes/handlers/__init__.py` (uncomment WO import)
- Modify: `apps/api/routes/p0_actions_routes.py` (delete lines 2492–2842 and 6277–6318 after tests pass)

**Context for the implementer:**
Work order elif blocks are in two separate ranges:
- Lines 2492–2842: update_work_order, assign_work_order, close_work_order, add_wo_hours, add_wo_part, add_wo_note, start_work_order, cancel_work_order, create_work_order, view_work_order_detail
- Lines 6277–6318: create_work_order_for_equipment

Read all of them before writing a single line. Copy logic verbatim — do not rewrite. The handler receives `db_client` already constructed; do NOT call `get_tenant_supabase_client` inside the handler functions. Import `build_ledger_event` from `routes.handlers.ledger_utils`.

- [ ] **Read all WO elif blocks:**

```bash
sed -n '2492,2843p' apps/api/routes/p0_actions_routes.py
sed -n '6277,6320p' apps/api/routes/p0_actions_routes.py
```

- [ ] **Create `apps/api/tests/handlers/__init__.py`** (empty file).

- [ ] **Write `apps/api/tests/handlers/test_work_order_handler.py` — failing tests first:**

```python
# tests/handlers/test_work_order_handler.py
import pytest
from unittest.mock import MagicMock

# Will fail until handler file exists
from routes.handlers.work_order_handler import HANDLERS


def make_db(rows=None):
    """Stub Supabase client — returns rows on any .execute() call."""
    db = MagicMock()
    rows = rows or [{"id": "wo-1"}]
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    db.table.return_value.insert.return_value.execute.return_value.data = rows
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = rows
    return db


def base_ctx(yacht_id="y-1"):
    return {"yacht_id": yacht_id}


def base_uc():
    return {"role": "captain", "tenant_key_alias": "y85fe1119", "department": "engineering"}


@pytest.mark.asyncio
async def test_update_work_order():
    result = await HANDLERS["update_work_order"](
        payload={"work_order_id": "wo-1", "title": "New"},
        context=base_ctx(), yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=make_db(),
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_update_wo_alias_same_function():
    assert HANDLERS["update_wo"] is HANDLERS["update_work_order"]


@pytest.mark.asyncio
async def test_create_work_order_for_equipment_success():
    db = make_db([{"id": "new-wo"}])
    result = await HANDLERS["create_work_order_for_equipment"](
        payload={"type": "corrective", "priority": "routine"},
        context={"yacht_id": "y-1", "equipment_id": "eq-1"},
        yacht_id="y-1", user_id="u-1",
        user_context=base_uc(), db_client=db,
    )
    assert result["status"] == "success"
    assert "work_order_id" in result


@pytest.mark.asyncio
async def test_create_work_order_for_equipment_missing_equipment_id():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await HANDLERS["create_work_order_for_equipment"](
            payload={"type": "corrective", "priority": "routine"},
            context={"yacht_id": "y-1"},  # no equipment_id
            yacht_id="y-1", user_id="u-1",
            user_context=base_uc(), db_client=make_db(),
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_all_aliases_registered():
    aliases = ["update_wo", "assign_wo", "complete_work_order", "log_work_hours",
               "add_part_to_wo", "add_note_to_wo", "begin_wo", "cancel_wo",
               "create_wo", "view_work_order", "get_work_order"]
    for alias in aliases:
        assert alias in HANDLERS, f"Alias '{alias}' not in HANDLERS"
```

- [ ] **Run tests — confirm they fail:**

```bash
cd apps/api && python3 -m pytest tests/handlers/test_work_order_handler.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'routes.handlers.work_order_handler'`

- [ ] **Create `apps/api/routes/handlers/work_order_handler.py`:**

Structure (follow exactly):

```python
"""
Work Order Action Handlers

Migrated from p0_actions_routes.py elif blocks:
  - Lines 2492–2842 (update, assign, close, hours, parts, notes, start, cancel, create, view)
  - Lines 6277–6318 (create_work_order_for_equipment)

Handler contract: see handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
Import build_ledger_event from routes.handlers.ledger_utils, not from p0_actions_routes.
"""
from datetime import datetime, timezone
import uuid as uuid_module
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


async def update_work_order(payload, context, yacht_id, user_id, user_context, db_client: Client) -> dict:
    # Copy body verbatim from lines 2496–2514
    ...


async def assign_work_order(payload, context, yacht_id, user_id, user_context, db_client: Client) -> dict:
    # Copy body verbatim from lines 2520–2542
    ...


# ... one function per elif block ...


async def create_work_order_for_equipment(payload, context, yacht_id, user_id, user_context, db_client: Client) -> dict:
    # context.get("equipment_id") is guaranteed by resolve_entity_context if entity_id was sent
    equipment_id = payload.get("equipment_id") or context.get("equipment_id")
    if not equipment_id:
        raise HTTPException(status_code=400, detail="equipment_id is required")
    # Copy remaining body verbatim from lines 6283–6316
    ...


HANDLERS: dict = {
    "update_work_order":               update_work_order,
    "update_wo":                       update_work_order,
    "assign_work_order":               assign_work_order,
    "assign_wo":                       assign_work_order,
    "close_work_order":                close_work_order,
    "complete_work_order":             close_work_order,
    "add_wo_hours":                    add_wo_hours,
    "log_work_hours":                  add_wo_hours,
    "add_wo_part":                     add_wo_part,
    "add_part_to_wo":                  add_wo_part,
    "add_wo_note":                     add_wo_note,
    "add_note_to_wo":                  add_wo_note,
    "start_work_order":                start_work_order,
    "begin_wo":                        start_work_order,
    "cancel_work_order":               cancel_work_order,
    "cancel_wo":                       cancel_work_order,
    "create_work_order":               create_work_order,
    "create_wo":                       create_work_order,
    "view_work_order_detail":          view_work_order_detail,
    "view_work_order":                 view_work_order_detail,
    "get_work_order":                  view_work_order_detail,
    "create_work_order_for_equipment": create_work_order_for_equipment,
}
```

- [ ] **Run unit tests — all pass:**

```bash
cd apps/api && python3 -m pytest tests/handlers/test_work_order_handler.py -v
```

Expected: all PASS.

- [ ] **Activate in `__init__.py`:**

```python
from .work_order_handler import HANDLERS as WO_HANDLERS

HANDLERS: dict = {**WO_HANDLERS}
```

- [ ] **API starts cleanly:**

```bash
cd apps/api && python3 -c "from pipeline_service import app; print('Import OK')"
```

- [ ] **Run E2E shards for work orders:**

```bash
cd apps/web && npx playwright test \
  e2e/shard-39-wo-equipment/ \
  e2e/shard-41-wo-extended/ \
  e2e/shard-34-lens-actions/work-order-actions-full.spec.ts \
  --reporter=list 2>&1 | tail -20
```

Expected: same pass count as pre-Phase 4 baseline. Any new failures = logic error in migration. Fix before proceeding.

- [ ] **Delete the WO elif blocks** (lines 2492–2842 and 6277–6318). HANDLERS now intercepts these before reaching the chain.

- [ ] **Re-run E2E to confirm deletion didn't break anything:**

```bash
cd apps/web && npx playwright test e2e/shard-39-wo-equipment/ e2e/shard-41-wo-extended/ --reporter=list 2>&1 | tail -10
```

- [ ] **Commit:**

```bash
git add apps/api/routes/handlers/work_order_handler.py \
        apps/api/routes/handlers/__init__.py \
        apps/api/routes/p0_actions_routes.py \
        apps/api/tests/handlers/__init__.py \
        apps/api/tests/handlers/test_work_order_handler.py
git commit -m "feat(phase4): migrate work order handlers to dispatch table

Moves 11 elif blocks from p0_actions_routes.py into work_order_handler.py.
resolve_entity_context guarantees equipment_id for create_work_order_for_equipment.

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Task 3: Migrate purchase order + receiving handlers

**Files:**
- Create: `apps/api/routes/handlers/purchase_order_handler.py`
- Create: `apps/api/routes/handlers/receiving_handler.py`
- Create: `apps/api/tests/handlers/test_purchase_order_handler.py`
- Create: `apps/api/tests/handlers/test_receiving_handler.py`
- Modify: `apps/api/routes/handlers/__init__.py`
- Modify: `apps/api/routes/p0_actions_routes.py` (delete lines 6066–6276 after tests pass)

**Context for the implementer:**
PO blocks: lines 6153–6276. Receiving blocks: lines 6066–6152. Same migration process as Task 2.

**Important for receiving:** The elif block at line 6114 for `create_receiving` calls an `internal_dispatcher`. Read that call site:

```bash
sed -n '6114,6155p' apps/api/routes/p0_actions_routes.py
```

You are calling the same `internal_dispatcher` from your handler function — do not re-implement its logic. The `internal_dispatcher` is defined earlier in `p0_actions_routes.py`; you will need to import it:

```python
from routes.p0_actions_routes import internal_dispatcher
```

- [ ] **Read both block ranges:**

```bash
sed -n '6066,6280p' apps/api/routes/p0_actions_routes.py
```

- [ ] **Write failing tests.** Minimum coverage:
  - Success case per handler function
  - All canonical names in HANDLERS (no aliases for PO/receiving — they have none)
  - Missing required field → 400

- [ ] **Run tests — confirm fail. Implement. Run tests — confirm pass.**

- [ ] **Activate in `__init__.py`:**

```python
from .work_order_handler import HANDLERS as WO_HANDLERS
from .purchase_order_handler import HANDLERS as PO_HANDLERS
from .receiving_handler import HANDLERS as REC_HANDLERS

HANDLERS: dict = {**WO_HANDLERS, **PO_HANDLERS, **REC_HANDLERS}
```

- [ ] **Run E2E shards:**

```bash
cd apps/web && npx playwright test e2e/shard-45-receiving-po/ e2e/shard-40-purchase-handover/ --reporter=list 2>&1 | tail -10
```

- [ ] **Delete lines 6066–6276. Re-run E2E. Commit:**

```bash
git commit -m "feat(phase4): migrate purchase order and receiving handlers

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Task 4: Migrate crew + hours-of-rest handlers

**Files:**
- Create: `apps/api/routes/handlers/crew_handler.py`
- Create: `apps/api/routes/handlers/hours_of_rest_handler.py`
- Modify: `apps/api/routes/handlers/__init__.py`
- Modify: `apps/api/routes/p0_actions_routes.py` (delete lines 5853–6013)

**Context for the implementer:**
HoR blocks: lines 5853–5941 (get_hours_of_rest, upsert_hours_of_rest, get_monthly_signoff, list_monthly_signoffs, create_monthly_signoff, sign_monthly_signoff). Crew blocks: lines 5942–6013.

Before implementing HoR handlers, check if there is a pre-existing `apps/api/handlers/hours_of_rest_handlers.py` that the elif blocks delegate to:

```bash
ls apps/api/handlers/ 2>/dev/null
sed -n '5853,5942p' apps/api/routes/p0_actions_routes.py
```

If the elif block is a thin wrapper calling an existing handler function, your handler function should call the same underlying function — not re-implement it.

- [ ] **Read blocks. Write failing tests. Implement. Run tests. Activate. Run E2E:**

```bash
cd apps/web && npx playwright test e2e/shard-37-hours-of-rest/ --reporter=list 2>&1 | tail -10
```

- [ ] **Delete lines 5853–6013. Re-run E2E. Commit:**

```bash
git commit -m "feat(phase4): migrate crew and hours-of-rest handlers

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Task 5: Migrate remaining handlers (certificates, documents, handover, shopping, PM)

**Files:**
- Create: `apps/api/routes/handlers/certificate_handler.py`
- Create: `apps/api/routes/handlers/document_handler.py`
- Create: `apps/api/routes/handlers/handover_handler.py`
- Create: `apps/api/routes/handlers/shopping_handler.py`
- Create: `apps/api/routes/handlers/pm_handler.py`
- Modify: `apps/api/routes/handlers/__init__.py`
- Modify: `apps/api/routes/p0_actions_routes.py`

**Context for the implementer:**

Certificate blocks are in TWO locations — both go into one handler file:
- Lines 2872–2882: add_certificate, renew_certificate, add_service_contract, record_contract_claim
- Lines 5714–5777: create_vessel_certificate, create_crew_certificate

```bash
sed -n '2855,2895p' apps/api/routes/p0_actions_routes.py   # PM + certificate block 1
sed -n '5714,5780p' apps/api/routes/p0_actions_routes.py   # certificate block 2
sed -n '5778,5855p' apps/api/routes/p0_actions_routes.py   # shopping blocks
sed -n '6014,6070p' apps/api/routes/p0_actions_routes.py   # document block
sed -n '6318,6400p' apps/api/routes/p0_actions_routes.py   # shopping block 2 + end
```

Read the handover block too:
```bash
sed -n '2863,2875p' apps/api/routes/p0_actions_routes.py
```

- [ ] **Read all blocks. Write failing tests per handler file. Implement. Run tests. Activate all in `__init__.py`:**

```python
from .work_order_handler import HANDLERS as WO_HANDLERS
from .purchase_order_handler import HANDLERS as PO_HANDLERS
from .receiving_handler import HANDLERS as REC_HANDLERS
from .crew_handler import HANDLERS as CREW_HANDLERS
from .hours_of_rest_handler import HANDLERS as HOR_HANDLERS
from .certificate_handler import HANDLERS as CERT_HANDLERS
from .document_handler import HANDLERS as DOC_HANDLERS
from .handover_handler import HANDLERS as HAND_HANDLERS
from .shopping_handler import HANDLERS as SHOP_HANDLERS
from .pm_handler import HANDLERS as PM_HANDLERS

HANDLERS: dict = {
    **WO_HANDLERS,
    **PO_HANDLERS,
    **REC_HANDLERS,
    **CREW_HANDLERS,
    **HOR_HANDLERS,
    **CERT_HANDLERS,
    **DOC_HANDLERS,
    **HAND_HANDLERS,
    **SHOP_HANDLERS,
    **PM_HANDLERS,
}
```

- [ ] **Run E2E shards for all affected domains:**

```bash
cd apps/web && npx playwright test \
  e2e/shard-43-docs-certs/ \
  e2e/shard-44-parts-shopping/ \
  e2e/shard-40-purchase-handover/ \
  e2e/shard-47-handover-misc/ \
  e2e/shard-33-lens-actions/ \
  e2e/shard-34-lens-actions/ \
  --reporter=list 2>&1 | tail -20
```

- [ ] **Delete the migrated elif blocks** (lines for PM, handover, certificate-1, certificate-2, shopping, HoR, crew, document). Delete each group after confirming its E2E shard still passes.

- [ ] **Commit:**

```bash
git commit -m "feat(phase4): migrate remaining handlers (certs, docs, handover, shopping, PM)

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Task 6: Delete the legacy elif chain (lines 2491–end)

**Files:**
- Modify: `apps/api/routes/p0_actions_routes.py` (delete what remains between line 2491 and the final `else:`)

By this point, Tasks 2–5 have deleted all the blocks they migrated. What should remain in the chain (if anything) is only whatever was NOT in the cluster map. This task verifies nothing was missed and deletes the now-empty skeleton.

### Step 6a — Verify all Phase 4 actions are in HANDLERS

- [ ] **Run coverage check:**

```bash
cd apps/api && python3 -c "
from routes.handlers import HANDLERS

# All canonical names from lines 2491–end (Phase 4 scope only)
PHASE4_ACTIONS = {
    # Work orders (2492–2842, 6277–6318, full)
    'update_work_order', 'update_wo', 'assign_work_order', 'assign_wo',
    'close_work_order', 'complete_work_order', 'add_wo_hours', 'log_work_hours',
    'add_wo_part', 'add_part_to_wo', 'add_wo_note', 'add_note_to_wo',
    'start_work_order', 'begin_wo', 'cancel_work_order', 'cancel_wo',
    'create_work_order', 'create_wo', 'view_work_order_detail', 'view_work_order',
    'get_work_order', 'create_work_order_for_equipment',
    'list_work_orders', 'add_parts_to_work_order', 'add_work_order_photo',
    'view_work_order_history', 'view_work_order_checklist', 'promote_candidate_to_part',
    # Worklist
    'add_worklist_task', 'update_worklist_progress', 'export_worklist', 'view_worklist',
    # PM (2855–2862)
    'create_pm_schedule', 'record_pm_completion', 'defer_pm_task',
    'update_pm_schedule', 'view_pm_due_list',
    # Handover (full — 5 BLOCKED + 6 inline/delegate)
    'create_handover', 'acknowledge_handover', 'update_handover',
    'delete_handover', 'filter_handover',
    'add_to_handover', 'add_document_to_handover', 'add_predictive_insight_to_handover',
    'edit_handover_section', 'export_handover', 'regenerate_handover_summary',
    # Certificate block 1 (2872–2882)
    'add_certificate', 'renew_certificate', 'add_service_contract', 'record_contract_claim',
    # Certificate block 2 (5714–5777, full — 5 delegate actions)
    'create_vessel_certificate', 'create_crew_certificate',
    'update_certificate', 'link_document_to_certificate', 'supersede_certificate',
    # Shopping (5778–5852, 6318+, full)
    'create_shopping_list_item', 'approve_shopping_list_item', 'mark_shopping_list_ordered',
    'reject_shopping_list_item', 'delete_shopping_item', 'view_shopping_list_history',
    # HoR (5853–5941, full)
    'get_hours_of_rest', 'upsert_hours_of_rest', 'update_hours_of_rest',
    'view_hours_of_rest', 'export_hours_of_rest',
    'get_monthly_signoff', 'list_monthly_signoffs', 'create_monthly_signoff', 'sign_monthly_signoff',
    # Crew (5942–6013)
    'create_crew_template', 'apply_crew_template', 'list_crew_templates',
    'list_crew_warnings', 'acknowledge_warning', 'dismiss_warning',
    # Document (6014–6065, full)
    'upload_document', 'update_document', 'delete_document',
    'list_documents', 'get_document_url', 'add_document_tags',
    'view_document_section', 'view_related_documents',
    # Receiving (partial — create_receiving and attach_receiving_image_with_comment
    # use internal_dispatcher with different contract; remain in legacy chain)
    'submit_receiving_for_review', 'edit_receiving',
    # Purchase order (6153–6276)
    'submit_purchase_order', 'approve_purchase_order', 'mark_po_received', 'cancel_purchase_order',
}

missing = PHASE4_ACTIONS - set(HANDLERS.keys())
if missing:
    print(f'MISSING from HANDLERS — do not proceed: {sorted(missing)}')
else:
    print(f'All {len(PHASE4_ACTIONS)} Phase 4 actions registered. HANDLERS total: {len(HANDLERS)}.')
"
```

Expected: `All N Phase 4 actions registered.` — zero missing.

### Step 6b — Verify lines 1192–2490 are untouched (Phase 5 territory)

- [ ] **Confirm the Phase 5 chain is intact:**

```bash
grep -n "create_work_order_from_fault\|report_fault\|close_fault\|consume_part\|write_off_part" \
  apps/api/routes/p0_actions_routes.py | head -10
```

Expected: all these actions still appear at their original lines (1192–2490). If any are missing, STOP — they were accidentally deleted and must be restored from git.

### Step 6c — Run full E2E suite

- [ ] **Run all shards:**

```bash
cd apps/web && npx playwright test \
  --project=shard-33-lens-actions \
  --project=shard-34-lens-actions \
  --project=shard-35-shopping-parts \
  --project=shard-36-work-orders \
  --project=shard-37-purchase-orders \
  --project=shard-38-receiving \
  --project=shard-39-crew \
  --project=shard-40-hours-of-rest \
  --project=shard-41-certificates \
  --project=shard-42-documents \
  --project=shard-43-handover \
  --project=shard-44-pm-tasks \
  --project=shard-45-shopping \
  --project=shard-46-hor-extended \
  --project=shard-47-misc \
  --reporter=list 2>&1 | tail -30
```

All shards must pass at the same rate as before Phase 4 began.

### Step 6d — Delete the empty elif skeleton

At this point, lines 2491–end consist of:
- The `elif action in (...)` lines (headers)
- The handler bodies (already deleted by Tasks 2–5)
- Comment blocks
- The final `else: unknown action error`

Delete only the empty skeleton (lines 2491 to the `else:` block). Keep the `else:` block — it handles actions not yet in HANDLERS (Phase 5 territory still uses it).

- [ ] **Verify `p0_actions_routes.py` line count dropped significantly:**

```bash
wc -l apps/api/routes/p0_actions_routes.py
```

Expected: under 2,600 lines (down from 7,560; the remaining ~2,300 lines are the preamble + security checks + Phase 5 chain).

### Step 6e — Final verification

- [ ] **API starts:**

```bash
cd apps/api && python3 -c "from pipeline_service import app; print('Import OK')"
```

- [ ] **Final full E2E run.**

- [ ] **Commit:**

```bash
git commit -m "feat(phase4): delete migrated elif skeleton — Phase 4 complete

p0_actions_routes.py reduced from 7,560 to ~2,500 lines.
Lines 1192–2490 (fault, part lens, complex WO) preserved for Phase 5.
All Phase 4 actions now live in routes/handlers/ as typed, testable functions.

Co-Authored-By: ruflo <ruv@ruv.net>"
```

---

## Verification Checklist (after all 6 tasks)

1. `wc -l apps/api/routes/p0_actions_routes.py` → under 2,600
2. All unit tests pass: `python3 -m pytest apps/api/tests/handlers/ -v`
3. Full E2E suite passes at same rate as pre-Phase 4
4. `python3 -c "from pipeline_service import app; print('OK')"` → OK
5. `resolve_entity_context` unit assertions pass
6. Lines 1192–2490 (Phase 5 territory) still present and intact
7. No `build_ledger_event` defined in `p0_actions_routes.py` — imported from `handlers/ledger_utils.py`

---

## Explicitly out of scope

- **Lines 1192–2490** — fault, part lens, complex WO actions. These are Phase 5.
- **Frontend changes** — `useEntityLens.executeAction` and `useActionHandler.executeAction` remain as-is. Phase 5.
- **`registry.py`** — not modified.
- **`action_router/`** — not modified.
- **JWT validation, yacht isolation, role checks, `REQUIRED_FIELDS`, `FAULT_LENS_ROLES`, `PART_LENS_SIGNED_ROLES`, `WORK_ORDER_LENS_ROLES`** — all stay in the dispatcher, none of these are touched.
