# Phase 5 — Execution Layer Completion

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan.

**Goal:** Migrate the remaining 69 actions from the legacy elif chain in `p0_actions_routes.py` into dispatch-table handler files, then delete the three dead duplicate elif blocks, leaving 161 total registered actions and zero legacy chain.

**Architecture:** Same strangler fig pattern as Phase 4. Each task creates one handler file under `apps/api/routes/handlers/`, exports a `HANDLERS` dict, and is activated by uncommenting its import in `routes/handlers/__init__.py`. After all 6 clusters, a final task deletes 3 dead duplicate elif blocks and verifies 161 registered actions.

**Tech Stack:** Python, FastAPI, supabase-py, pytest. Handler contract identical to Phase 4.

---

## Critical Context

### Handler Contract (identical to Phase 4)

```python
async def action_name(
    payload: dict,
    context: dict,
    yacht_id: str,
    user_id: str,
    user_context: dict,
    db_client: Client,   # pre-constructed by dispatcher — do NOT call get_tenant_supabase_client
) -> dict:
    ...
```

### Required imports for all handlers

```python
from datetime import datetime, timezone
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event
import logging
logger = logging.getLogger(__name__)
```

### State machine (fault cluster only)

```python
from action_router.middleware import validate_state_transition, InvalidStateTransitionError
```

### Domain class delegations (when handler needs to call existing handler classes)

```python
from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
from handlers.inventory_handlers import InventoryHandlers
from handlers.part_handlers import PartHandlers
from handlers.manual_handlers import ManualHandlers
```

These classes accept `db_client` as constructor arg. Instantiate them inside the handler function.

### Existing Phase 4 handler files (DO NOT MODIFY)

`work_order_handler.py`, `purchase_order_handler.py`, `receiving_handler.py`,
`crew_handler.py`, `hours_of_rest_handler.py`, `certificate_handler.py`,
`document_handler.py`, `handover_handler.py`, `shopping_handler.py`, `pm_handler.py`

### Dead duplicate elif blocks to delete (Task 7)

Three elif blocks in `p0_actions_routes.py` are unreachable dead code (shadowed by earlier canonical blocks):
- L1539: `elif action == "create_work_order_from_fault":` — shadowed by the canonical `if action ==` at L1240
- L2533: `elif action == "close_fault":` — shadowed by canonical at L2207
- L2563: `elif action == "update_fault":` — shadowed by canonical at L2262

### Severity guard (all fault mutations)

Every fault UPDATE must include `"severity": "medium"` in `update_data`. This prevents PostgreSQL check-constraint failures from stale data. It is NOT a business-logic choice — it is a DB invariant.

### RBAC preservation

These actions have inline RBAC checks that must be ported exactly:
- `log_part_usage`: `["chief_engineer", "chief_officer", "captain", "manager"]`
- `create_purchase_request`: `["chief_engineer", "chief_officer", "captain", "manager"]`
- `approve_purchase`: `["captain", "manager"]`
- `update_purchase_status`: `["chief_engineer", "chief_officer", "captain", "manager"]`
- `update_equipment_status`: `["chief_engineer", "eto", "captain", "manager"]`

RBAC check pattern (early return, NOT HTTPException):
```python
allowed = ["captain", "manager"]
user_role = user_context.get("role", "")
if user_role not in allowed:
    return {
        "success": False,
        "code": "FORBIDDEN",
        "message": f"Role '{user_role}' is not authorized to perform this action",
        "required_roles": allowed
    }
```

---

## Task 1: Work Order Completion Cluster (7 actions)

**File to create:** `apps/api/routes/handlers/wo_completion_handler.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `create_work_order_from_fault`, `add_note_to_work_order`, `add_part_to_work_order`,
`mark_work_order_complete`, `reassign_work_order`, `archive_work_order`, `add_work_order_note`

Source lines in p0_actions_routes.py:
- `create_work_order_from_fault` — canonical block L1240–1381 (inline logic)
- `add_note_to_work_order` — L1382–1481 (inserts pms_work_order_notes, has FK fallback)
- `add_part_to_work_order` — L1483–1493 (delegates to WorkOrderMutationHandlers)
- `mark_work_order_complete` — L1495–1537 (delegates to WorkOrderMutationHandlers + ledger)
- `reassign_work_order` — L1609–1659 (delegates to WorkOrderMutationHandlers + ledger, wet sig)
- `archive_work_order` — L1661–1708 (delegates to WorkOrderMutationHandlers + ledger, wet sig)
- `add_work_order_note` — L4291–4376 (metadata.notes array, ledger)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_wo_completion_handler.py
import pytest
from apps.api.routes.handlers.wo_completion_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "create_work_order_from_fault",
        "add_note_to_work_order",
        "add_part_to_work_order",
        "mark_work_order_complete",
        "reassign_work_order",
        "archive_work_order",
        "add_work_order_note",
    }
    assert set(HANDLERS.keys()) == expected

def test_handlers_are_callable():
    import asyncio
    for name, fn in HANDLERS.items():
        assert callable(fn), f"{name} is not callable"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -m pytest tests/unit/routes/handlers/test_wo_completion_handler.py -v 2>&1 | head -20
```
Expected: ImportError or similar — file doesn't exist yet.

- [ ] **Step 3: Create the handler file**

```python
# apps/api/routes/handlers/wo_completion_handler.py
"""
Work Order Completion Handlers — Phase 5 Task 1.

Migrated from p0_actions_routes.py legacy elif chain.
Handler contract: see routes/handlers/__init__.py header.
Do NOT call get_tenant_supabase_client — db_client is pre-constructed by dispatcher.
"""
from datetime import datetime, timezone
import uuid as uuid_module
import logging

from fastapi import HTTPException
from supabase import Client

from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)


async def create_work_order_from_fault(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Create WO from fault with wet-signature validation. (was L1240–1381)"""
    signature = payload.get("signature")

    if not signature:
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "signature_required",
            "message": "Signature payload required for SIGNED action"
        })

    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type"}
    if not isinstance(signature, dict):
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "invalid_signature",
            "message": "Signature must be an object"
        })

    missing_keys = required_sig_keys - set(signature.keys())
    if missing_keys:
        raise HTTPException(status_code=400, detail={
            "status": "error", "error_code": "invalid_signature",
            "message": f"Invalid signature: missing keys {sorted(missing_keys)}"
        })

    role_at_signing = signature.get("role_at_signing")
    allowed_signer_roles = ["captain", "manager"]
    if role_at_signing not in allowed_signer_roles:
        raise HTTPException(status_code=403, detail={
            "status": "error", "error_code": "invalid_signer_role",
            "message": f"Role '{role_at_signing}' cannot sign this action",
            "required_roles": allowed_signer_roles
        })

    fault_id = payload.get("fault_id")
    fault = db_client.table("pms_faults").select("*").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    if not fault.data:
        raise HTTPException(status_code=404, detail="Fault not found")

    existing = db_client.table("pms_work_orders").select("id").eq("fault_id", fault_id).execute()
    if existing.data and not payload.get("override_duplicate", False):
        return {"status": "error", "error_code": "DUPLICATE_WO_EXISTS", "message": "Work order already exists for this fault"}

    raw_priority = payload.get("priority", "routine")
    priority_map = {"normal": "routine", "low": "routine", "medium": "routine", "high": "critical"}
    priority = priority_map.get(raw_priority, raw_priority if raw_priority in ("routine", "emergency", "critical") else "routine")

    wo_data = {
        "yacht_id": yacht_id,
        "fault_id": fault_id,
        "equipment_id": payload.get("equipment_id") or fault.data.get("equipment_id"),
        "title": payload.get("title", fault.data.get("title", "Work order from fault")),
        "description": payload.get("description", fault.data.get("description", "")),
        "priority": priority,
        "status": "planned",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
    if not wo_result.data:
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to create work order"}

    wo_id = wo_result.data[0]["id"]
    db_client.table("pms_faults").update({
        "work_order_id": wo_id,
        "updated_by": user_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", fault_id).eq("yacht_id", yacht_id).execute()

    audit_data = {
        "yacht_id": yacht_id,
        "action": "create_work_order_from_fault",
        "entity_type": "work_order",
        "entity_id": wo_id,
        "user_id": user_id,
        "signature": signature,
        "new_values": wo_result.data[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db_client.table("pms_audit_log").insert(audit_data).execute()

    try:
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="create",
            entity_type="work_order", entity_id=wo_id,
            action="create_work_order_from_fault",
            user_role=user_context.get("role"),
            change_summary="Work order created from fault",
        )
        db_client.table("ledger_events").insert(ledger_event).execute()
    except Exception as ledger_err:
        if "204" not in str(ledger_err):
            logger.warning(f"[Ledger] Failed: {ledger_err}")

    return {"status": "success", "work_order_id": wo_id, "message": "Work order created from fault"}


async def add_note_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Insert note into pms_work_order_notes with FK fallback. (was L1382–1481)"""
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text", "")
    note_type = payload.get("note_type", "general")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not note_text or len(note_text) < 1:
        raise HTTPException(status_code=400, detail="note_text is required")

    valid_types = ("general", "progress", "issue", "resolution")
    if note_type not in valid_types:
        note_type = "general"

    try:
        check = db_client.table("pms_work_orders").select("id").eq("id", work_order_id).eq("yacht_id", yacht_id).single().execute()
        if not check.data:
            raise HTTPException(status_code=404, detail="Work order not found")
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "PGRST116" in error_str or "0 rows" in error_str or "result contains 0 rows" in error_str.lower():
            raise HTTPException(status_code=404, detail="Work order not found")
        raise

    note_data = {
        "work_order_id": work_order_id,
        "note_text": note_text,
        "note_type": note_type,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
        if note_result.data:
            try:
                ledger_event = build_ledger_event(
                    yacht_id=yacht_id, user_id=user_id, event_type="update",
                    entity_type="work_order", entity_id=work_order_id,
                    action="add_note_to_work_order",
                    user_role=user_context.get("role"),
                    change_summary="Note added to work order",
                )
                db_client.table("ledger_events").insert(ledger_event).execute()
            except Exception as ledger_err:
                if "204" not in str(ledger_err):
                    logger.warning(f"[Ledger] Failed: {ledger_err}")
            return {"status": "success", "success": True, "note_id": note_result.data[0]["id"], "message": "Note added to work order successfully"}
        return {"status": "error", "error_code": "INSERT_FAILED", "message": "Failed to add note to work order"}
    except Exception as db_err:
        error_str = str(db_err)
        if "23503" in error_str or "foreign key" in error_str.lower():
            fallback_user = db_client.table("auth_users_profiles").select("id").limit(1).execute()
            if fallback_user.data:
                note_data["created_by"] = fallback_user.data[0]["id"]
                try:
                    note_result = db_client.table("pms_work_order_notes").insert(note_data).execute()
                    if note_result.data:
                        return {"status": "success", "success": True, "note_id": note_result.data[0]["id"], "message": "Note added (with system user attribution)"}
                    raise HTTPException(status_code=500, detail=f"Insert failed: {error_str}")
                except Exception as retry_err:
                    raise HTTPException(status_code=500, detail=f"FK constraint: {error_str}. Retry: {str(retry_err)}")
            raise HTTPException(status_code=500, detail=f"FK constraint and no fallback user: {error_str}")
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")


async def add_part_to_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers. (was L1483–1493)"""
    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    return await wo_handlers.add_part_to_work_order_execute(
        work_order_id=payload["work_order_id"],
        part_id=payload["part_id"],
        quantity=payload["quantity"],
        notes=payload.get("notes"),
        yacht_id=yacht_id,
        user_id=user_id,
    )


async def mark_work_order_complete(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1495–1537)"""
    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.mark_work_order_complete_execute(
        work_order_id=payload["work_order_id"],
        completion_notes=payload["completion_notes"],
        parts_used=payload.get("parts_used", []),
        signature=payload["signature"],
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        work_order_id = payload["work_order_id"]
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="status_change",
            entity_type="work_order", entity_id=work_order_id,
            action="mark_work_order_complete",
            user_role=user_context.get("role", "member"),
            change_summary="Work order marked as complete",
            metadata={
                "completion_notes": payload.get("completion_notes", ""),
                "parts_used_count": len(payload.get("parts_used", [])),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def reassign_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1609–1659)"""
    signature = payload.get("signature")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required for reassign_work_order")
    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"}
    if not isinstance(signature, dict) or not required_sig_keys.issubset(set(signature.keys())):
        raise HTTPException(status_code=400, detail="invalid signature payload: missing required fields")

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.reassign_work_order_execute(
        work_order_id=payload["work_order_id"],
        new_assignee_id=payload["assignee_id"],
        reason=payload.get("reason", "Reassigned"),
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        work_order_id = payload["work_order_id"]
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="assignment",
            entity_type="work_order", entity_id=work_order_id,
            action="reassign_work_order",
            user_role=user_context.get("role", "member"),
            change_summary=f"Work order reassigned: {payload.get('reason', 'Reassigned')}",
            metadata={
                "new_assignee_id": payload["assignee_id"],
                "reason": payload.get("reason", "Reassigned"),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def archive_work_order(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Delegate to WorkOrderMutationHandlers + ledger. (was L1661–1708)"""
    signature = payload.get("signature")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required for archive_work_order")
    required_sig_keys = {"signed_at", "user_id", "role_at_signing", "signature_type", "signature_hash"}
    if not isinstance(signature, dict) or not required_sig_keys.issubset(set(signature.keys())):
        raise HTTPException(status_code=400, detail="invalid signature payload: missing required fields")

    from handlers.work_order_mutation_handlers import WorkOrderMutationHandlers
    wo_handlers = WorkOrderMutationHandlers(db_client)
    result = await wo_handlers.archive_work_order_execute(
        work_order_id=payload["work_order_id"],
        deletion_reason=payload.get("deletion_reason", "Archived"),
        signature=signature,
        yacht_id=yacht_id,
        user_id=user_id,
    )

    try:
        work_order_id = payload["work_order_id"]
        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="delete",
            entity_type="work_order", entity_id=work_order_id,
            action="archive_work_order",
            user_role=user_context.get("role", "member"),
            change_summary=f"Work order archived: {payload.get('deletion_reason', 'Archived')}",
            metadata={"deletion_reason": payload.get("deletion_reason", "Archived"), "domain": "Work Orders"}
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as e:
            if "204" not in str(e):
                logger.warning(f"[Ledger] Failed: {e}")
    except Exception as e:
        logger.warning(f"[Ledger] Failed to prepare event: {e}")

    return result


async def add_work_order_note(
    payload: dict, context: dict, yacht_id: str, user_id: str,
    user_context: dict, db_client: Client,
) -> dict:
    """Append note to work order metadata.notes array + ledger. (was L4291–4376)"""
    work_order_id = payload.get("work_order_id")
    note_text = payload.get("note_text")

    if not work_order_id:
        raise HTTPException(status_code=400, detail="work_order_id is required")
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required")

    wo = db_client.table("pms_work_orders").select("id, title, number, metadata").eq("id", work_order_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not wo.data:
        raise HTTPException(status_code=404, detail="Work order not found")

    metadata = wo.data.get("metadata", {}) or {}
    notes = metadata.get("notes", []) or []
    notes.append({
        "text": note_text,
        "added_by": user_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    metadata["notes"] = notes

    try:
        db_client.table("pms_work_orders").update({"metadata": metadata}).eq("id", work_order_id).eq("yacht_id", yacht_id).execute()
    except Exception as update_err:
        if "204" in str(update_err):
            logger.info(f"Work order update succeeded with 204 for {work_order_id}")
        else:
            raise

    try:
        wo_title = wo.data.get("title", "Untitled")
        wo_number = wo.data.get("number", "")
        display_name = f"Work Order #{wo_number} — {wo_title}" if wo_number else f"Work Order — {wo_title}"
        user_name = user_context.get("name") or user_context.get("email", "Unknown")
        user_role_str = user_context.get("role", "member")

        ledger_event = build_ledger_event(
            yacht_id=yacht_id, user_id=user_id, event_type="update",
            entity_type="work_order", entity_id=work_order_id,
            action="add_note",
            user_role=user_role_str,
            change_summary=f"Note added to {display_name}",
            metadata={
                "display_name": display_name,
                "note_text": note_text[:200] + "..." if len(note_text) > 200 else note_text,
                "user_name": user_name,
                "notes_count": len(notes),
                "domain": "Work Orders",
            }
        )
        try:
            db_client.table("ledger_events").insert(ledger_event).execute()
        except Exception as ledger_insert_err:
            if "204" in str(ledger_insert_err):
                pass
            else:
                logger.warning(f"[Ledger] Failed: {ledger_insert_err}")
    except Exception as ledger_err:
        logger.warning(f"[Ledger] Failed to prepare event: {ledger_err}")

    return {"status": "success", "success": True, "message": "Note added to work order", "work_order_id": work_order_id, "notes_count": len(notes)}


HANDLERS: dict = {
    "create_work_order_from_fault": create_work_order_from_fault,
    "add_note_to_work_order":       add_note_to_work_order,
    "add_part_to_work_order":       add_part_to_work_order,
    "mark_work_order_complete":     mark_work_order_complete,
    "reassign_work_order":          reassign_work_order,
    "archive_work_order":           archive_work_order,
    "add_work_order_note":          add_work_order_note,
}
```

- [ ] **Step 4: Register in `__init__.py`**

Add to `apps/api/routes/handlers/__init__.py` — append below the last import line and add to the merge dict:

```python
from .wo_completion_handler import HANDLERS as WO_COMP_HANDLERS
```

And in `HANDLERS = {...}`:
```python
**WO_COMP_HANDLERS,
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -m pytest tests/unit/routes/handlers/test_wo_completion_handler.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 6: Verify import chain doesn't break**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: Total handlers: 99 (92 Phase 4 + 7 new).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/wo_completion_handler.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_wo_completion_handler.py
git commit -m "feat(phase5/task1): migrate 7 WO completion actions to dispatch table"
```

---

## Task 2: Fault Management Cluster (13 actions)

**File to create:** `apps/api/routes/handlers/fault_handler.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `report_fault`, `acknowledge_fault`, `resolve_fault`, `diagnose_fault`,
`close_fault`, `update_fault`, `reopen_fault`, `mark_fault_false_alarm`,
`add_fault_photo`, `view_fault_detail`, `view_fault_history`, `add_fault_note`, `list_faults`

Source lines:
- `report_fault` L1999–2057 (inline, INSERT pms_faults)
- `acknowledge_fault` L2059–2131 (inline, UPDATE to "investigating", audit_log)
- `resolve_fault` L2133–2158 (inline, UPDATE to "resolved")
- `diagnose_fault` L2160–2205 (inline, metadata.diagnosis + ledger)
- `close_fault` L2207–2260 (inline, **uses validate_state_transition**, ledger)
- `update_fault` L2262–2307 (inline, severity guard)
- `reopen_fault` L2309–2366 (inline, **uses validate_state_transition**)
- `mark_fault_false_alarm` L2366–2412 (inline)
- `add_fault_photo` L2414–2442 (inline, metadata.photos)
- `view_fault_detail` L2444–2593 (inline, SELECT with equipment JOIN)
- `list_faults` L2596–2672 (inline, SELECT with filters)
- `view_fault_history` L2674–2694 (inline, SELECT by equipment_id)
- `add_fault_note` L2696–2741 (inline, metadata.notes)

**Critical:** `close_fault` and `reopen_fault` must call `validate_state_transition` and catch `InvalidStateTransitionError`. Import from `action_router.middleware`.

**Severity guard:** ALL fault mutation handlers that UPDATE must include `"severity": "medium"` in update_data.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_fault_handler.py
import pytest
from apps.api.routes.handlers.fault_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "report_fault", "acknowledge_fault", "resolve_fault", "diagnose_fault",
        "close_fault", "update_fault", "reopen_fault", "mark_fault_false_alarm",
        "add_fault_photo", "view_fault_detail", "view_fault_history",
        "add_fault_note", "list_faults",
    }
    assert set(HANDLERS.keys()) == expected

def test_handlers_are_callable():
    for name, fn in HANDLERS.items():
        assert callable(fn), f"{name} is not callable"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
python -m pytest tests/unit/routes/handlers/test_fault_handler.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create `apps/api/routes/handlers/fault_handler.py`**

Translate each elif block from p0_actions_routes.py into a handler function with signature:
`async def name(payload, context, yacht_id, user_id, user_context, db_client: Client) -> dict`

Required imports at the top of the file:
```python
from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event
from action_router.middleware import validate_state_transition, InvalidStateTransitionError

logger = logging.getLogger(__name__)
```

For each action, copy the logic from the source block verbatim, changing only:
1. Remove `tenant_alias = ...` and `db_client = get_tenant_supabase_client(tenant_alias)` (db_client comes in as parameter)
2. Replace `result = {...}` at the end with `return {...}`
3. For early returns (e.g., RBAC-style state machine block): replace `return {...}` with `return {...}` (already the right pattern since handler function returns directly)

**`close_fault` handler must look like:**
```python
async def close_fault(payload, context, yacht_id, user_id, user_context, db_client: Client) -> dict:
    fault_id = payload.get("fault_id")
    check = db_client.table("pms_faults").select("id, status").eq("id", fault_id).eq("yacht_id", yacht_id).single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Fault not found")
    current_status = check.data.get("status", "open")
    try:
        validate_state_transition("fault", current_status, "close_fault")
    except InvalidStateTransitionError as e:
        return {"success": False, "code": e.code, "message": e.message, "current_status": current_status}
    update_data = {"status": "closed", "severity": "medium", "updated_by": user_id, "updated_at": datetime.now(timezone.utc).isoformat()}
    fault_result = db_client.table("pms_faults").update(update_data).eq("id", fault_id).eq("yacht_id", yacht_id).execute()
    if fault_result.data:
        try:
            ev = build_ledger_event(yacht_id=yacht_id, user_id=user_id, event_type="status_change",
                entity_type="fault", entity_id=fault_id, action="close_fault",
                user_role=user_context.get("role"), change_summary="Fault closed")
            db_client.table("ledger_events").insert(ev).execute()
        except Exception as e:
            if "204" not in str(e): logger.warning(f"[Ledger] Failed: {e}")
        return {"status": "success", "message": "Fault closed"}
    return {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}
```

Follow the same pattern for all 13 handlers. Export `HANDLERS` dict at the bottom.

- [ ] **Step 4: Register in `__init__.py`**

```python
from .fault_handler import HANDLERS as FAULT_HANDLERS
```
Add `**FAULT_HANDLERS,` to the merge dict.

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/unit/routes/handlers/test_fault_handler.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 6: Verify import chain**

```bash
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: 112 (99 + 13).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/fault_handler.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_fault_handler.py
git commit -m "feat(phase5/task2): migrate 13 fault management actions to dispatch table"
```

---

## Task 3: Equipment Cluster (10 actions)

**File to create:** `apps/api/routes/handlers/equipment_handler.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `update_equipment_status`, `view_equipment`, `view_equipment_detail`,
`view_equipment_details`, `view_equipment_history`, `view_equipment_parts`,
`view_linked_faults`, `view_equipment_manual`, `add_equipment_note`, `suggest_parts`

Source lines: L2455–2960 (equipment section)

**RBAC for `update_equipment_status`** (inline, early return pattern):
```python
equipment_roles = ["chief_engineer", "eto", "captain", "manager"]
user_role = user_context.get("role", "")
if user_role not in equipment_roles:
    return {"success": False, "code": "FORBIDDEN",
            "message": f"Role '{user_role}' is not authorized to update equipment status",
            "required_roles": equipment_roles}
```

**`view_equipment_details`** is an alias that runs the same logic as `view_equipment_detail`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_equipment_handler.py
from apps.api.routes.handlers.equipment_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "update_equipment_status", "view_equipment", "view_equipment_detail",
        "view_equipment_details", "view_equipment_history", "view_equipment_parts",
        "view_linked_faults", "view_equipment_manual", "add_equipment_note",
        "suggest_parts",
    }
    assert set(HANDLERS.keys()) == expected

def test_view_equipment_details_is_alias():
    # Both must point to the same function
    assert HANDLERS["view_equipment_details"] is HANDLERS["view_equipment_detail"]
```

- [ ] **Step 2: Confirm test fails**

```bash
python -m pytest tests/unit/routes/handlers/test_equipment_handler.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create `apps/api/routes/handlers/equipment_handler.py`**

Required imports:
```python
from datetime import datetime, timezone
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)
```

Translate each elif block. Key patterns:
- `view_equipment` and `view_equipment_detail` — SELECT pms_equipment with LEFT JOIN pms_faults; return `{"status": "success", "entity": {...}}`
- `view_equipment_details` — same function reference as `view_equipment_detail`
- `view_equipment_history` — SELECT pms_work_orders WHERE equipment_id
- `view_equipment_parts` — SELECT pms_parts WHERE equipment_id
- `view_linked_faults` — SELECT pms_faults WHERE equipment_id
- `view_equipment_manual` — SELECT doc_metadata WHERE equipment_ids contains equipment_id
- `add_equipment_note` — metadata.notes array append + ledger
- `suggest_parts` — SELECT pms_parts + pms_equipment for the fault's equipment

HANDLERS at bottom:
```python
HANDLERS: dict = {
    "update_equipment_status":  update_equipment_status,
    "view_equipment":           view_equipment,
    "view_equipment_detail":    view_equipment_detail,
    "view_equipment_details":   view_equipment_detail,   # alias
    "view_equipment_history":   view_equipment_history,
    "view_equipment_parts":     view_equipment_parts,
    "view_linked_faults":       view_linked_faults,
    "view_equipment_manual":    view_equipment_manual,
    "add_equipment_note":       add_equipment_note,
    "suggest_parts":            suggest_parts,
}
```

- [ ] **Step 4: Register in `__init__.py`**

```python
from .equipment_handler import HANDLERS as EQUIP_HANDLERS
```
Add `**EQUIP_HANDLERS,` to merge dict.

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/unit/routes/handlers/test_equipment_handler.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 6: Verify import chain**

```bash
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: 122 (112 + 10).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/equipment_handler.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_equipment_handler.py
git commit -m "feat(phase5/task3): migrate 10 equipment actions to dispatch table"
```

---

## Task 4: Parts / Inventory Cluster (17 actions)

**File to create:** `apps/api/routes/handlers/parts_handler_p5.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `check_stock_level`, `log_part_usage`, `view_part_details`, `consume_part`,
`receive_part`, `transfer_part`, `adjust_stock_quantity`, `write_off_part`,
`generate_part_labels`, `request_label_output`, `view_part_stock`, `view_part_location`,
`view_part_usage`, `view_linked_equipment`, `order_part`, `scan_part_barcode`, `add_to_shopping_list`

Note: File named `parts_handler_p5.py` (not `parts_handler.py`) to avoid any ambiguity with the domain class file `handlers/part_handlers.py` which lives in a different directory.

Source lines:
- `check_stock_level` L1711–1718 (delegates to InventoryHandlers)
- `log_part_usage` L1720–1743 (RBAC check + delegates to InventoryHandlers)
- `view_part_details` L1746–1767 (delegates to PartHandlers)
- `add_to_shopping_list` L1769–1789 (delegates to PartHandlers)
- `consume_part` L1791–1829 (delegates to PartHandlers)
- `receive_part` L1831–1854 (delegates to PartHandlers)
- `transfer_part` L1856–1877 (delegates to PartHandlers)
- `adjust_stock_quantity` L1879–1917 (delegates to PartHandlers + ledger)
- `write_off_part` L1919–1940 (delegates to PartHandlers, wet signature)
- `generate_part_labels` L1942–1959 (delegates to PartHandlers)
- `request_label_output` L1961–1979 (delegates to PartHandlers)
- `view_part_stock` L2982–3003 (inline SELECT)
- `view_part_location` L3005–3028 (inline SELECT)
- `view_part_usage` L3030–3061 (inline SELECT, graceful fallback)
- `view_linked_equipment` L3063–3083 (inline SELECT)
- `order_part` L3085–3111 (inline stub)
- `scan_part_barcode` L3113–3145 (inline SELECT by part_number)

**RBAC for `log_part_usage`**:
```python
allowed = ["chief_engineer", "chief_officer", "captain", "manager"]
if user_context.get("role", "") not in allowed:
    return {"success": False, "code": "FORBIDDEN", "message": f"Role not authorized", "required_roles": allowed}
```

**PartHandlers delegation pattern** (used for consume_part, receive_part, etc.):
```python
from handlers.part_handlers import PartHandlers
ph = PartHandlers(db_client)
handler_result = await ph.method_name(yacht_id=yacht_id, user_id=user_id, part_id=payload["part_id"], ...)
if handler_result.get("status") == "success":
    return handler_result
return {"status": "error", "message": handler_result.get("message", "Unknown error")}
```

**view_part_details** uses ResponseBuilder envelope (different from mutation handlers):
```python
handler_result = await ph.view_part_details(entity_id=payload["part_id"], yacht_id=yacht_id, user_id=user_id, tenant_key_alias=user_context.get("tenant_key_alias", ""))
if handler_result.get("success"):
    return {"status": "success", "data": handler_result.get("data"), "message": handler_result.get("message", "")}
error = handler_result.get("error", {})
return {"status": "error", "error_code": error.get("code", "UNKNOWN"), "message": error.get("message", "Unknown error")}
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_parts_handler_p5.py
from apps.api.routes.handlers.parts_handler_p5 import HANDLERS

def test_all_actions_registered():
    expected = {
        "check_stock_level", "log_part_usage", "view_part_details", "consume_part",
        "receive_part", "transfer_part", "adjust_stock_quantity", "write_off_part",
        "generate_part_labels", "request_label_output", "view_part_stock",
        "view_part_location", "view_part_usage", "view_linked_equipment",
        "order_part", "scan_part_barcode", "add_to_shopping_list",
    }
    assert set(HANDLERS.keys()) == expected
```

- [ ] **Step 2: Confirm test fails**

```bash
python -m pytest tests/unit/routes/handlers/test_parts_handler_p5.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create `apps/api/routes/handlers/parts_handler_p5.py`**

Translate each source block. For InventoryHandlers delegations:
```python
from handlers.inventory_handlers import InventoryHandlers
inv = InventoryHandlers(db_client)
return await inv.check_stock_level_execute(part_id=payload["part_id"], yacht_id=yacht_id, user_id=user_id)
```

Export HANDLERS dict at the bottom with all 17 entries.

- [ ] **Step 4: Register in `__init__.py`**

```python
from .parts_handler_p5 import HANDLERS as PARTS_P5_HANDLERS
```
Add `**PARTS_P5_HANDLERS,` to merge dict.

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/unit/routes/handlers/test_parts_handler_p5.py -v
```

- [ ] **Step 6: Verify import chain**

```bash
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: 139 (122 + 17).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/parts_handler_p5.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_parts_handler_p5.py
git commit -m "feat(phase5/task4): migrate 17 parts/inventory actions to dispatch table"
```

---

## Task 5: Checklist / Media Cluster (9 actions)

**File to create:** `apps/api/routes/handlers/checklist_handler.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `view_checklist`, `mark_checklist_item_complete`, `add_checklist_note`,
`add_checklist_item`, `add_checklist_photo`, `view_smart_summary`,
`upload_photo`, `record_voice_note`, `show_manual_section`

Source lines:
- `view_checklist` L3151–3185 (inline, SELECT pms_checklists + pms_checklist_items)
- `mark_checklist_item_complete` L3187–3267 (inline, UPDATE + ledger, graceful fallback)
- `add_checklist_note` L3269–3348 (inline, metadata.notes array + ledger)
- `add_checklist_item` L3350–3447 (inline, INSERT into pms_work_order_checklist + ledger)
- `add_checklist_photo` L3449–3530 (inline, metadata.photos + ledger)
- `view_smart_summary` L3532–3575 (inline, SELECT entity metadata)
- `upload_photo` L3577–3637 (inline, metadata.photos dispatch table)
- `record_voice_note` L3639–3700 (inline, metadata.voice_notes)
- `show_manual_section` L1982–1991 (delegates to ManualHandlers)

Note: `show_manual_section` uses `ManualHandlers` from `handlers.manual_handlers`.

**ManualHandlers delegation**:
```python
from handlers.manual_handlers import ManualHandlers
manual = ManualHandlers(db_client)
return await manual.show_manual_section_execute(
    equipment_id=payload["equipment_id"],
    yacht_id=yacht_id, user_id=user_id,
    fault_code=payload.get("fault_code"),
    section_id=payload.get("section_id"),
)
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_checklist_handler.py
from apps.api.routes.handlers.checklist_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "view_checklist", "mark_checklist_item_complete", "add_checklist_note",
        "add_checklist_item", "add_checklist_photo", "view_smart_summary",
        "upload_photo", "record_voice_note", "show_manual_section",
    }
    assert set(HANDLERS.keys()) == expected
```

- [ ] **Step 2: Confirm test fails**

```bash
python -m pytest tests/unit/routes/handlers/test_checklist_handler.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create `apps/api/routes/handlers/checklist_handler.py`**

Required imports:
```python
from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)
```

Translate each source block. Key notes:
- `mark_checklist_item_complete` and `add_checklist_note` have `except Exception: result = {"status": "success", ...}` graceful fallbacks — preserve them.
- `add_checklist_item` has 204 handling on insert — preserve it.
- `upload_photo` dispatches by entity_type using a table_map — preserve the table_map.
- Export `HANDLERS` dict at the bottom.

- [ ] **Step 4: Register in `__init__.py`**

```python
from .checklist_handler import HANDLERS as CHECKLIST_HANDLERS
```
Add `**CHECKLIST_HANDLERS,` to merge dict.

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/unit/routes/handlers/test_checklist_handler.py -v
```

- [ ] **Step 6: Verify import chain**

```bash
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: 148 (139 + 9).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/checklist_handler.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_checklist_handler.py
git commit -m "feat(phase5/task5): migrate 9 checklist/media actions to dispatch table"
```

---

## Task 6: Compliance / Fleet / Purchasing Cluster (13 actions)

**File to create:** `apps/api/routes/handlers/compliance_handler.py`
**File to modify:** `apps/api/routes/handlers/__init__.py`

**Actions:** `view_compliance_status`, `tag_for_survey`, `create_purchase_request`,
`add_item_to_purchase`, `approve_purchase`, `upload_invoice`, `track_delivery`,
`log_delivery_received`, `update_purchase_status`, `view_fleet_summary`,
`open_vessel`, `export_fleet_summary`, `request_predictive_insight`

Source lines:
- `view_compliance_status` L3707–3742 (inline, graceful fallback)
- `tag_for_survey` L3744–3785 (inline, metadata.survey_tags append)
- `create_purchase_request` L3791–3845 (**RBAC: HoD+**, inline INSERT)
- `add_item_to_purchase` L3847–3892 (inline INSERT)
- `approve_purchase` L3894–3936 (**RBAC: captain/manager**, inline UPDATE)
- `upload_invoice` L3938–3990 (inline, metadata.invoices append)
- `track_delivery` L3992–4031 (inline SELECT, graceful)
- `log_delivery_received` L4033–4077 (inline UPDATE)
- `update_purchase_status` L4079–4131 (**RBAC: HoD+**, inline UPDATE with status enum validation)
- `view_fleet_summary` L4137–4181 (inline SELECT yachts, graceful fallback)
- `open_vessel` L4183–4198 (inline stub)
- `export_fleet_summary` L4200–4225 (inline SELECT yachts)
- `request_predictive_insight` L4231–4289 (inline, metadata.insight_requests append)

**RBAC checks** (3 actions):
- `create_purchase_request`: `["chief_engineer", "chief_officer", "captain", "manager"]` — early return pattern
- `approve_purchase`: `["captain", "manager"]` — early return pattern
- `update_purchase_status`: `["chief_engineer", "chief_officer", "captain", "manager"]` — early return pattern

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/routes/handlers/test_compliance_handler.py
from apps.api.routes.handlers.compliance_handler import HANDLERS

def test_all_actions_registered():
    expected = {
        "view_compliance_status", "tag_for_survey", "create_purchase_request",
        "add_item_to_purchase", "approve_purchase", "upload_invoice",
        "track_delivery", "log_delivery_received", "update_purchase_status",
        "view_fleet_summary", "open_vessel", "export_fleet_summary",
        "request_predictive_insight",
    }
    assert set(HANDLERS.keys()) == expected
```

- [ ] **Step 2: Confirm test fails**

```bash
python -m pytest tests/unit/routes/handlers/test_compliance_handler.py -v 2>&1 | head -5
```

- [ ] **Step 3: Create `apps/api/routes/handlers/compliance_handler.py`**

Required imports:
```python
from datetime import datetime, timezone
import uuid as uuid_module
import logging
from fastapi import HTTPException
from supabase import Client
from routes.handlers.ledger_utils import build_ledger_event

logger = logging.getLogger(__name__)
```

Key notes:
- All 3 RBAC checks use `return {...}` (early return, NOT `raise HTTPException`)
- `update_purchase_status` has a valid status enum: `["draft", "submitted", "approved", "ordered", "shipped", "delivered", "cancelled"]` — preserve this validation
- `view_compliance_status`, `track_delivery`, `view_fleet_summary`, `open_vessel`, `export_fleet_summary` have `except Exception: ...` graceful fallbacks — preserve them
- Export `HANDLERS` dict at the bottom with all 13 entries

- [ ] **Step 4: Register in `__init__.py`**

```python
from .compliance_handler import HANDLERS as COMPLIANCE_HANDLERS
```
Add `**COMPLIANCE_HANDLERS,` to merge dict.

- [ ] **Step 5: Run test**

```bash
python -m pytest tests/unit/routes/handlers/test_compliance_handler.py -v
```

- [ ] **Step 6: Verify import chain**

```bash
python -c "from routes.handlers import HANDLERS; print(f'Total handlers: {len(HANDLERS)}')"
```
Expected: 161 (148 + 13).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routes/handlers/compliance_handler.py apps/api/routes/handlers/__init__.py tests/unit/routes/handlers/test_compliance_handler.py
git commit -m "feat(phase5/task6): migrate 13 compliance/fleet/purchasing actions to dispatch table"
```

---

## Task 7: Delete Dead Elif Blocks + Final Coverage Verification

**File to modify:** `apps/api/routes/p0_actions_routes.py`

Three elif blocks in the legacy chain are unreachable dead code. Delete them.

### Dead blocks to delete

**Block 1** — second `create_work_order_from_fault` (starts L1539):
Find and delete from `elif action == "create_work_order_from_fault":` (the second occurrence, ~line 1539)
through `result = await wo_handlers.create_work_order_from_fault_execute(...)` and its parameters,
ending just before `elif action == "reassign_work_order":`.

Identify with: `grep -n 'elif action == "create_work_order_from_fault"' apps/api/routes/p0_actions_routes.py`
The SECOND match is the dead block.

**Block 2** — second `close_fault` (starts ~L2533):
Find and delete from `elif action == "close_fault":` (the second occurrence, ~line 2533)
through `result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to close fault"}`
ending just before `# ===== UPDATE FAULT ACTION (Cluster 01) =====`.

**Block 3** — second `update_fault` (starts ~L2563):
Find and delete from `elif action == "update_fault":` (the second occurrence, ~line 2563)
through `result = {"status": "error", "error_code": "UPDATE_FAILED", "message": "Failed to update fault"}`
ending just before `# ===== LIST FAULTS ACTION (Cluster 01) =====`.

- [ ] **Step 1: Record line counts before deletion**

```bash
wc -l apps/api/routes/p0_actions_routes.py
```
Record the current line count.

- [ ] **Step 2: Verify the dead block locations before deleting**

```bash
grep -n 'elif action == "create_work_order_from_fault"\|elif action == "close_fault"\|elif action == "update_fault"' apps/api/routes/p0_actions_routes.py
```
Expected: each action appears exactly twice. The second occurrence of each is the dead block.

- [ ] **Step 3: Delete the three dead elif blocks**

Use Read + Edit to locate each block precisely and delete it. Example for Block 2:

Read lines around L2533–L2561 to get exact text, then use Edit to delete that block.
After deletion, the flow from `elif action == "close_fault":` at L2207 should fall through
directly to the `# ===== UPDATE FAULT ACTION` comment and the canonical `elif action == "update_fault":`.

Apply the same process for Block 3 and Block 1.

- [ ] **Step 4: Verify no syntax errors**

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python -m py_compile routes/p0_actions_routes.py && echo "OK: no syntax errors"
```
Expected: `OK: no syntax errors`

- [ ] **Step 5: Confirm each action now appears exactly once**

```bash
grep -c 'elif action == "create_work_order_from_fault"' apps/api/routes/p0_actions_routes.py
grep -c 'elif action == "close_fault"' apps/api/routes/p0_actions_routes.py
grep -c 'elif action == "update_fault"' apps/api/routes/p0_actions_routes.py
```
Expected: each prints `1`.

(Note: `create_work_order_from_fault` appears as `if action ==` for the canonical block, so grep for `elif` will give 0 — that's correct.)

- [ ] **Step 6: Final handler count verification**

```bash
python -c "
from routes.handlers import HANDLERS
count = len(HANDLERS)
print(f'Registered handlers: {count}')
assert count == 161, f'Expected 161, got {count}'
print('PASS: exactly 161 actions registered')
"
```
Expected: `Registered handlers: 161` and `PASS`.

- [ ] **Step 7: Run all handler unit tests**

```bash
python -m pytest tests/unit/routes/handlers/ -v 2>&1 | tail -20
```
Expected: all tests pass, 0 failed.

- [ ] **Step 8: Import integrity check**

```bash
python -c "import routes.p0_actions_routes; print('Import OK')" 2>&1
```
Expected: `Import OK`

- [ ] **Step 9: Commit**

```bash
git add apps/api/routes/p0_actions_routes.py
git commit -m "refactor(phase5/task7): delete 3 dead duplicate elif blocks, 161 actions fully migrated"
```

---

## Final Verification

After Task 7, run the complete verification:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api

# 1. Handler count
python -c "from routes.handlers import HANDLERS; print(len(HANDLERS))"
# Expected: 161

# 2. Syntax check
python -m py_compile routes/p0_actions_routes.py && echo "Syntax OK"

# 3. Unit tests
python -m pytest tests/unit/routes/handlers/ -v --tb=short

# 4. Line count reduction check
wc -l routes/p0_actions_routes.py
# Should be significantly lower than before Task 7 (dead blocks removed)
```

Phase 5 complete: 161/161 actions registered, 0 legacy elif blocks remaining for migrated actions.
