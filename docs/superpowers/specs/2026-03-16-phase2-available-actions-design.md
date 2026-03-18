# Phase 2: Universal Available Actions — Design Spec

**Date:** 2026-03-16
**Status:** Approved for implementation — v2 (post spec-review fixes)

---

## Goal

Add a populated `available_actions` array to all 12 entity GET endpoints. Each entry gives the frontend the complete contract to render an action button: visibility (role-filtered), interactability (state gate), pre-filled field values from entity context, and field schema (required/optional).

The frontend becomes a pure renderer. Zero domain logic on the client.

---

## Background

### What exists today

- **`AvailableAction` dataclass** — `apps/api/actions/action_response_schema.py`. Fields: `action_id, label, variant, icon, is_primary, requires_signature, confirmation_message, disabled, disabled_reason`. Missing: `prefill`, `required_fields`, `optional_fields`.
- **`get_available_actions_for_entity()` stub** — same file. Dead import (`from action_registry import get_registry` — module does not exist). Never called. Needs replacement.
- **`_determine_available_actions()`** — `apps/api/routes/entity_routes.py`. Hardcoded work_order state machine only. Returns `{"name", "endpoint", "requires_signature", "method"}` — wrong schema. Will be removed.
- **`FieldMetadata` + `FieldClassification`** — on each `ActionDefinition` in `registry.py`. Classification values: `REQUIRED`, `OPTIONAL`, `BACKEND_AUTO`, `CONTEXT`. Already populated on many actions. This is the source for `required_fields`/`optional_fields`.
- **`ACTION_REGISTRY`** — dict in `registry.py` keyed by `action_id`. `ACTION_REGISTRY.get(action_id)` returns an `ActionDefinition` or `None`. `get_action(action_id)` raises `KeyError` on miss — do NOT use `get_action()` in the discovery path.
- **`get_actions_for_domain(domain)`** — utility in `registry.py`. Returns `List[Dict]` (serialised action summaries, NOT `ActionDefinition` objects). Dict keys include `action_id` but NOT `field_metadata`. Use this to enumerate action_ids for a domain, then fetch each full `ActionDefinition` via `ACTION_REGISTRY.get(action_id)`.

### What does NOT change

- `p0_actions_routes.py` — execution path is untouched
- `registry.py` — no modifications; consumed read-only
- `action_response_schema.py` existing classes — additive extension only
- RLS — entity routes already use the authenticated Supabase client; no DB reads added by this feature

---

## Payload Shape

Each of the 12 entity GET endpoints gains an `available_actions` key:

```json
{
  "id": "...",
  "...existing entity fields...": "...",
  "available_actions": [
    {
      "action_id": "start_work_order",
      "label": "Start Work Order",
      "variant": "MUTATE",
      "icon": "",
      "is_primary": false,
      "requires_signature": false,
      "confirmation_message": null,
      "disabled": false,
      "disabled_reason": null,
      "prefill": {
        "work_order_id": "uuid-of-this-work-order"
      },
      "required_fields": ["notes"],
      "optional_fields": ["priority"]
    },
    {
      "action_id": "close_work_order",
      "label": "Close Work Order",
      "variant": "MUTATE",
      "icon": "",
      "is_primary": false,
      "requires_signature": false,
      "confirmation_message": null,
      "disabled": true,
      "disabled_reason": "Work order must be started first",
      "prefill": {},
      "required_fields": ["resolution"],
      "optional_fields": []
    },
    {
      "action_id": "write_off_part",
      "label": "Write Off Part",
      "variant": "SIGNED",
      "icon": "",
      "is_primary": false,
      "requires_signature": true,
      "confirmation_message": "This action requires a PIN and TOTP signature.",
      "disabled": false,
      "disabled_reason": null,
      "prefill": {"part_id": "uuid-of-this-part"},
      "required_fields": ["quantity", "reason"],
      "optional_fields": []
    }
  ]
}
```

**Field semantics:**
- `disabled: false` + `disabled_reason: null` → button active, user can submit
- `disabled: true` + `disabled_reason: "..."` → button greyed, reason shown as tooltip
- `prefill: {}` → no context values available for this action on this entity type
- `required_fields` → frontend blocks submit until all filled
- `optional_fields` → shown but not blocking
- `variant: "SIGNED"` → action requires PIN+TOTP payload; `requires_signature` will be `true`
- Fields classified `BACKEND_AUTO` or `CONTEXT` (yacht_id, user_id, created_at) are NEVER in `required_fields` or `optional_fields` — they are injected server-side by the action handler

**Role filtering:** Actions the user's role cannot execute are **omitted entirely**. No "Requires HOD role" disabled entries — role gates are invisible walls, not actionable feedback.

---

## File Structure

```
apps/api/action_router/
├── registry.py              ← UNCHANGED
├── entity_prefill.py        ← NEW: VLOOKUP table + resolver
└── entity_actions.py        ← NEW: action discovery engine

apps/api/actions/
└── action_response_schema.py  ← EXTENDED: AvailableAction + 3 fields + SIGNED variant; stub fixed

apps/api/routes/
└── entity_routes.py           ← UPDATED: 12 endpoints + _determine_available_actions() removed

apps/api/tests/
└── test_entity_actions.py     ← NEW: unit tests
```

---

## `entity_prefill.py` — Context VLOOKUP Layer

**Single responsibility:** Given `(entity_type, action_id, entity_data)`, return resolved prefill dict and field schema. Pure Python — no DB calls, no imports beyond `ACTION_REGISTRY`.

### Domain mapping

```python
ENTITY_TYPE_TO_DOMAIN = {
    "work_order":     "work_orders",
    "equipment":      "equipment",
    "fault":          "faults",
    "part":           "parts",
    "document":       "documents",
    "certificate":    "certificates",
    "receiving":      "receiving",
    "shopping_list":  "shopping_list",
    "warranty":       "warranty",
    "hours_of_rest":  "hours_of_rest",
    "purchase_order": None,      # no registry domain — get_available_actions returns []
    "handover_export": None,     # no registry domain — get_available_actions returns []
    # NOTE: handover-related actions in the registry have no domain= set and are
    # therefore unreachable via the domain path. This is intentional for Phase 2.
}
```

### Context prefill map

Static dict. Key = `(entity_type, action_id)`. Value = `{field_name: dot_path}`.
Dot paths resolve against the entity data dict fetched by the route handler.
Unmapped pairs return `{}` — this is safe and never blocks an action from appearing.

**Known gaps (intentional for Phase 2):** `shopping_list` and `hours_of_rest` entity types
have no prefill entries in this initial map. Actions for those entities will appear correctly
(role-filtered, state-gated) but with `prefill: {}`. Entries can be added incrementally
without any API contract change.

```python
from typing import Any, Dict, Tuple

CONTEXT_PREFILL_MAP: Dict[Tuple[str, str], Dict[str, str]] = {
    # Equipment context
    ("equipment", "create_work_order_for_equipment"): {
        "equipment_id": "id",
        "title": "canonical_label",
    },
    ("equipment", "report_fault"): {
        "equipment_id": "id",
        "equipment_name": "canonical_label",
    },
    ("equipment", "link_part_to_equipment"): {
        "equipment_id": "id",
    },
    ("equipment", "add_equipment_note"): {
        "equipment_id": "id",
    },
    ("equipment", "attach_file_to_equipment"): {
        "equipment_id": "id",
    },
    ("equipment", "flag_equipment_attention"): {
        "equipment_id": "id",
    },
    ("equipment", "record_equipment_hours"): {
        "equipment_id": "id",
    },

    # Fault context
    ("fault", "create_work_order_from_fault"): {
        "fault_id": "id",
        "equipment_id": "equipment_id",
        "title": "description",
    },
    ("fault", "add_fault_note"): {
        "fault_id": "id",
    },
    ("fault", "add_fault_photo"): {
        "fault_id": "id",
    },
    ("fault", "acknowledge_fault"): {
        "fault_id": "id",
    },
    ("fault", "diagnose_fault"): {
        "fault_id": "id",
    },
    ("fault", "close_fault"): {
        "fault_id": "id",
    },

    # Work order context
    ("work_order", "add_wo_note"): {
        "work_order_id": "id",
    },
    ("work_order", "add_wo_part"): {
        "work_order_id": "id",
    },
    ("work_order", "add_wo_hours"): {
        "work_order_id": "id",
    },
    ("work_order", "add_work_order_photo"): {
        "work_order_id": "id",
    },
    ("work_order", "start_work_order"): {
        "work_order_id": "id",
    },
    ("work_order", "cancel_work_order"): {
        "work_order_id": "id",
    },
    ("work_order", "close_work_order"): {
        "work_order_id": "id",
    },
    ("work_order", "assign_work_order"): {
        "work_order_id": "id",
    },
    ("work_order", "reassign_work_order"): {
        "work_order_id": "id",
    },

    # Part context
    ("part", "log_part_usage"): {
        "part_id": "id",
    },
    ("part", "transfer_part"): {
        "part_id": "id",
    },
    ("part", "adjust_stock_quantity"): {
        "part_id": "id",
    },
    ("part", "write_off_part"): {
        "part_id": "id",
    },
    ("part", "receive_part"): {
        "part_id": "id",
    },
    ("part", "consume_part"): {
        "part_id": "id",
    },

    # Certificate context
    ("certificate", "update_certificate"): {
        "certificate_id": "id",
    },
    ("certificate", "link_document_to_certificate"): {
        "certificate_id": "id",
    },
    ("certificate", "supersede_certificate"): {
        "certificate_id": "id",
    },

    # Receiving context
    ("receiving", "add_receiving_item"): {
        "receiving_id": "id",
    },
    ("receiving", "adjust_receiving_item"): {
        "receiving_id": "id",
    },
    ("receiving", "accept_receiving"): {
        "receiving_id": "id",
    },
    ("receiving", "reject_receiving"): {
        "receiving_id": "id",
    },
    ("receiving", "attach_receiving_image_with_comment"): {
        "receiving_id": "id",
    },
    ("receiving", "update_receiving_fields"): {
        "receiving_id": "id",
    },

    # Warranty context
    ("warranty", "submit_warranty_claim"): {
        "warranty_id": "id",
    },
    ("warranty", "approve_warranty_claim"): {
        "warranty_id": "id",
    },
    ("warranty", "reject_warranty_claim"): {
        "warranty_id": "id",
    },
    ("warranty", "compose_warranty_email"): {
        "warranty_id": "id",
    },

    # Document context
    ("document", "update_document"): {
        "document_id": "id",
    },
    ("document", "add_document_comment"): {
        "document_id": "id",
    },
    ("document", "add_document_tags"): {
        "document_id": "id",
    },
    ("document", "delete_document"): {
        "document_id": "id",
    },
}
```

### Public functions

```python
def resolve_prefill(entity_type: str, action_id: str, entity_data: dict) -> dict:
    """Resolve dot-paths from CONTEXT_PREFILL_MAP against entity_data."""
    mapping = CONTEXT_PREFILL_MAP.get((entity_type, action_id), {})
    result = {}
    for field_name, dot_path in mapping.items():
        value = _resolve_dot_path(entity_data, dot_path)
        if value is not None:
            result[field_name] = value
    return result


def get_field_schema(action_id: str) -> tuple[list[str], list[str]]:
    """
    Return (required_fields, optional_fields) for an action.

    Uses ACTION_REGISTRY.get() — never get_action() — to safely handle
    missing keys without raising KeyError.

    BACKEND_AUTO and CONTEXT fields are excluded (server-fills them).
    Returns ([], []) if action not found or has no field_metadata.
    """
    from action_router.registry import ACTION_REGISTRY, FieldClassification
    action_def = ACTION_REGISTRY.get(action_id)
    if not action_def or not action_def.field_metadata:
        return [], []
    required = [
        f.name for f in action_def.field_metadata
        if f.classification in ("REQUIRED", FieldClassification.REQUIRED)
    ]
    optional = [
        f.name for f in action_def.field_metadata
        if f.classification in ("OPTIONAL", FieldClassification.OPTIONAL)
    ]
    return required, optional


def _resolve_dot_path(data: dict, path: str) -> Any:
    """Resolve 'a.b.c' path against a dict. Returns None if any key missing."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current
```

---

## `entity_actions.py` — Action Discovery Engine

**Single responsibility:** Given entity type, entity data, and user role, return the full `available_actions` list. Calls into `entity_prefill` and `ACTION_REGISTRY`. No DB calls.

### Registry access pattern

`get_actions_for_domain(domain)` returns `List[Dict]` (serialised summaries, no `field_metadata`).
To get the full `ActionDefinition` with `field_metadata` and `allowed_roles`, always follow up
with `ACTION_REGISTRY.get(action_id)`:

```python
from action_router.registry import ACTION_REGISTRY, get_actions_for_domain
from action_router.entity_prefill import (
    ENTITY_TYPE_TO_DOMAIN, resolve_prefill, get_field_schema
)

def get_available_actions(
    entity_type: str,
    entity_data: dict,
    user_role: str,
) -> list[dict]:
    domain = ENTITY_TYPE_TO_DOMAIN.get(entity_type)
    if domain is None:
        return []  # purchase_order, handover_export — no registry domain

    domain_action_dicts = get_actions_for_domain(domain)  # List[Dict]

    result = []
    for action_summary in domain_action_dicts:
        action_id = action_summary["action_id"]

        # Fetch full ActionDefinition — use .get() not get_action() to avoid KeyError
        action_def = ACTION_REGISTRY.get(action_id)
        if not action_def:
            continue

        # Role filter: omit entirely if user_role not permitted
        allowed = action_def.allowed_roles or []
        if user_role not in allowed:
            continue

        # State gate: inline logic for stateful entities only
        # _apply_state_gate signature: (entity_type: str, entity_data: dict, action_id: str) -> tuple[bool, Optional[str]]
        # Returns (disabled: bool, disabled_reason: str | None)
        # disabled=False, disabled_reason=None means action is enabled
        disabled, disabled_reason = _apply_state_gate(entity_type, entity_data, action_id)

        # Prefill + field schema
        prefill = resolve_prefill(entity_type, action_id, entity_data)
        required_fields, optional_fields = get_field_schema(action_id)

        # Variant → requires_signature
        variant_str = action_def.variant.value if hasattr(action_def.variant, "value") else str(action_def.variant)
        requires_signature = (variant_str == "SIGNED")

        result.append({
            "action_id": action_id,
            "label": action_def.label,
            "variant": variant_str,          # "READ", "MUTATE", or "SIGNED"
            "icon": "",
            "is_primary": False,
            "requires_signature": requires_signature,
            "confirmation_message": None,
            "disabled": disabled,
            "disabled_reason": disabled_reason,
            "prefill": prefill,
            "required_fields": required_fields,
            "optional_fields": optional_fields,
        })

    return result
```

### `_apply_state_gate` — function skeleton

```python
_PRE_START_STATUSES = {"draft", "open", "planned"}
_ACTIVE_STATUSES = {"in_progress", "pending_parts"}
_TERMINAL_STATUSES = {"completed", "cancelled", "closed"}

_WO_PRE_START_DISABLED = {
    "close_work_order", "complete_work_order", "add_wo_hours",
    "reassign_work_order", "cancel_work_order",
}
_WO_ACTIVE_DISABLED = {"start_work_order"}
_WO_TERMINAL_DISABLED = {
    "start_work_order", "add_wo_part", "add_wo_hours",
    "log_part_usage", "add_work_order_photo", "assign_work_order",
}

_FAULT_TERMINAL_STATUSES = {"resolved", "closed"}
_FAULT_TERMINAL_DISABLED = {
    "acknowledge_fault", "diagnose_fault", "create_work_order_from_fault",
    "add_fault_photo", "close_fault",
    # reopen_fault intentionally EXCLUDED — it is the escape hatch for terminal states
    # add_fault_note intentionally EXCLUDED — notes are documentation, not mutations
}

_RECEIVING_TERMINAL_STATUSES = {"accepted", "rejected"}
_RECEIVING_TERMINAL_DISABLED = {
    "add_receiving_item", "adjust_receiving_item", "accept_receiving",
    "reject_receiving", "attach_receiving_image_with_comment", "update_receiving_fields",
}


def _apply_state_gate(
    entity_type: str,
    entity_data: dict,
    action_id: str,
) -> tuple[bool, Optional[str]]:
    """
    Returns (disabled: bool, disabled_reason: str | None).
    disabled=False, disabled_reason=None → action is enabled.
    Only work_order, fault, and receiving have state gates.
    All other entity types always return (False, None).
    """
    status = (entity_data.get("status") or "").lower()

    if entity_type == "work_order":
        if status in _PRE_START_STATUSES and action_id in _WO_PRE_START_DISABLED:
            return True, "Work order must be started first"
        if status in _ACTIVE_STATUSES and action_id in _WO_ACTIVE_DISABLED:
            return True, "Work order is already in progress"
        if status in _TERMINAL_STATUSES and action_id in _WO_TERMINAL_DISABLED:
            reason_map = {
                "completed": "Work order is completed",
                "cancelled": "Work order is cancelled",
                "closed": "Work order is closed",
            }
            return True, reason_map.get(status, "Work order is finalised")

    elif entity_type == "fault":
        if status in _FAULT_TERMINAL_STATUSES and action_id in _FAULT_TERMINAL_DISABLED:
            return True, "Fault is already resolved"

    elif entity_type == "receiving":
        if status in _RECEIVING_TERMINAL_STATUSES and action_id in _RECEIVING_TERMINAL_DISABLED:
            return True, "Receiving record is finalised"

    return False, None
```

### State gates reference (human-readable summary)

```
draft / open        → disable: close_work_order, complete_work_order, add_wo_hours,
                               reassign_work_order, cancel_work_order
                      reason: "Work order must be started first"
                      (these are pre-start states; start_work_order remains enabled)

planned             → same as draft/open (legacy status value, treated identically)

in_progress /
pending_parts       → disable: start_work_order
                      reason: "Work order is already in progress"

completed           → disable: start_work_order, add_wo_part, add_wo_hours,
                               log_part_usage, add_work_order_photo, assign_work_order
                      reason: "Work order is completed"

cancelled           → same disabled set as completed
                      reason: "Work order is cancelled"

closed              → same disabled set as completed
                      reason: "Work order is closed"
```

**fault** — reads `entity_data.get("status")`:
```
resolved / closed   → disable: acknowledge_fault, diagnose_fault,
                               create_work_order_from_fault, add_fault_photo,
                               close_fault
                      reason: "Fault is already resolved"
                      reopen_fault: ENABLED (escape hatch for terminal states)
                      add_fault_note: ENABLED (documentation, not a mutation)
```

**receiving** — reads `entity_data.get("status")`:
```
accepted / rejected → disable: add_receiving_item, adjust_receiving_item,
                               accept_receiving, reject_receiving,
                               attach_receiving_image_with_comment,
                               update_receiving_fields
                      reason: "Receiving record is finalised"
```

All other entity types (equipment, part, certificate, document, shopping_list, warranty,
hours_of_rest, purchase_order, handover_export) — no state gates, role filtering only.

---

## `action_response_schema.py` — Extension

### AvailableAction: add 3 fields + SIGNED variant

Additive only — existing callers unaffected (all new fields have defaults):

```python
@dataclass
class AvailableAction:
    action_id: str
    label: str
    variant: Literal["READ", "MUTATE", "SIGNED"]   # SIGNED added (was only READ/MUTATE)
    icon: str = ""
    is_primary: bool = False
    requires_signature: bool = False
    confirmation_message: Optional[str] = None
    disabled: bool = False
    disabled_reason: Optional[str] = None
    # --- Phase 2 additions ---
    prefill: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
```

Update `to_dict()` to include the three new fields.

### Fix broken stub

```python
def get_available_actions_for_entity(
    entity_type: str,
    entity_id: str,         # retained for backward-compat signature; NOT used for lookup
    user_role: str = "crew",
    entity_data: dict = None,
) -> List[dict]:
    """
    Wrapper for backward compatibility. entity_id is retained in signature
    only — entity_data already contains the ID. Callers passing entity_id
    alone (without entity_data) will receive an empty prefill dict.
    """
    from action_router.entity_actions import get_available_actions
    return get_available_actions(entity_type, entity_data or {}, user_role)
```

---

## `entity_routes.py` — Updates

For each of the 12 entity handlers, add at the end before `return`:

```python
from action_router.entity_actions import get_available_actions

# Inside handler, after entity_data dict is assembled:
user_role = current_user.get("role", "crew")
# get_available_actions is READ-ONLY with respect to its entity_data input —
# it never mutates the dict. Assigning the result back to response["available_actions"]
# is the only mutation; the response dict is not touched inside the call.
response["available_actions"] = get_available_actions(entity_type, response, user_role)
```

Remove `_determine_available_actions()` function entirely (currently lines 612–628).

The `work_order` endpoint state machine logic moves into `entity_actions.py`'s `_apply_state_gate()`. No parallel logic remains in `entity_routes.py`.

---

## What the Frontend Gets

**Work order in `draft` status, Captain:**
- `start_work_order` → enabled, `prefill: {work_order_id: "uuid"}`
- `add_wo_note` → enabled, `prefill: {work_order_id: "uuid"}`
- `close_work_order` → disabled, reason: "Work order must be started first"
- `add_wo_hours` → disabled, reason: "Work order must be started first"

**Work order in `in_progress` status, Captain:**
- `start_work_order` → disabled, reason: "Work order is already in progress"
- `add_wo_note` → enabled
- `add_wo_hours` → enabled
- `close_work_order` → enabled

**Fault in `resolved` status:**
- `acknowledge_fault` → disabled, reason: "Fault is already resolved"
- `close_fault` → disabled, reason: "Fault is already resolved"
- `reopen_fault` → **enabled** (escape hatch — only way out of terminal state)
- `add_fault_note` → enabled (documentation, intentionally unrestricted)
- `view_fault_detail` → enabled (READ variant, no state gate)

**Part entity, write_off_part, HOD:**
- `variant: "SIGNED"`, `requires_signature: true`, enabled, `prefill: {part_id: "uuid"}`

---

## Testing Plan

**Unit tests** — new file `apps/api/tests/test_entity_actions.py`:

```
test_role_filter_crew            crew role omits HOD-only actions
test_role_filter_hod             HOD sees full domain action list
test_state_gate_work_order_draft close_work_order disabled, start_work_order enabled
test_state_gate_work_order_in_progress  start_work_order disabled, add_wo_hours enabled
test_state_gate_work_order_completed    start_work_order + add_wo_hours both disabled
test_state_gate_fault_resolved          acknowledge_fault disabled
test_state_gate_receiving_accepted      add_receiving_item disabled
test_flat_entity_equipment              no state gates, role filter only
test_signed_variant_sets_requires_signature  write_off_part → requires_signature: true
test_prefill_resolves_entity_id         equipment.id maps to equipment_id in prefill
test_prefill_nested_dot_path            fault.equipment_id resolves correctly
test_prefill_missing_mapping_returns_empty   unmapped pair returns {}
test_field_schema_excludes_backend_auto      yacht_id not in required/optional lists
test_field_schema_no_metadata_returns_empty  action with no field_metadata → ([], [])
test_unknown_entity_type_returns_empty       purchase_order → []
test_no_keyerror_on_missing_action_id        ACTION_REGISTRY.get() used, not get_action()
```

**E2E** — extend `apps/web/e2e/shard-4-entities/entities.spec.ts`:
- Assert `available_actions` key present in work_order entity response
- Assert at least one entry has `action_id`, `label`, `disabled` fields
- Assert `disabled_reason` is string or null (not undefined)
- Assert SIGNED action (if present) has `requires_signature: true`

---

## Constraints

- `ACTION_REGISTRY.get(action_id)` — always use `.get()`, never `get_action()` (raises KeyError)
- `get_actions_for_domain(domain)` returns `List[Dict]` not `List[ActionDefinition]` — extract action_ids, then fetch ActionDefinition separately
- No new DB calls in discovery path — entity data already fetched by route handler
- `registry.py` is read-only — no modifications
- `p0_actions_routes.py` is untouched — execution path separate from discovery
- `CONTEXT_PREFILL_MAP` grows incrementally — missing entries are safe (return `{}`)
- `AvailableAction` extension is additive — existing callers unaffected (new fields have defaults)
- `handover_export` and `purchase_order` return `[]` — no registry domain exists for them
- `shopping_list` and `hours_of_rest` have no prefill entries in v1 — intentional known gap
