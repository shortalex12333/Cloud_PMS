# Work Order Lens: Action Buttons & Auto-Prefill

**Branch**: `work-order/action-buttons-prefill`
**Status**: PLANNING
**Author**: Claude Code
**Created**: 2026-01-27
**Updated**: 2026-01-27 (aligned with q&a2.md conventions)

---

## 1. SCOPE

### What We're Building

Two complementary features:

1. **Direct Action Buttons**: When user explicitly requests an action by name (e.g., "create work order"), render the action button in **SuggestedActions** section alongside search results. **Never bypass entity results.**

2. **Auto-Prefill (Two-Phase)**: When user focuses an entity and clicks an action:
   - **Phase 1 (Prepare)**: Backend computes `mutation_preview` with proposed payload, required fields, warnings
   - **Phase 2 (Commit)**: Re-validate, execute, write audit, return result

### Key Conventions (from q&a2.md)

| Convention | Implementation |
|------------|----------------|
| Field metadata in registry | `field_metadata` with `classification`, `auto_populate_from`, `lookup_required` |
| Two-phase pattern | Prepare (READ) → Commit (MUTATE/SIGNED) for create_work_order |
| SuggestedActions section | Buttons appear **alongside** results, not replacing |
| Error mapping | 400/404 for client errors; **never 500** |
| Ledger | `pms_audit_log.signature` NOT NULL; `{}` for non-signed |
| Entity resolution | UUIDs with labels; resolve in prepare, re-validate on execute |

### User Journey Example

```
User: "main engine overheating"
                │
                ▼
┌───────────────────────────────────────────┐
│  Search Results                           │
│  ├── Manuals (3)                         │
│  ├── Equipment (1): Main Engine          │
│  └── Faults (2)                          │
│                                           │
│  ─────── SuggestedActions ───────        │
│  [Create Work Order] [Add to Handover]   │
└───────────────────────────────────────────┘
                │
    User clicks [Create Work Order]
                │
                ▼
┌───────────────────────────────────────────┐
│  PREPARE PHASE (mutation_preview)         │
│                                           │
│  Title: [main engine - overheating    ]  │  ← auto-composed
│  Equipment: [Main Engine ▼            ]  │  ← resolved (UUID + label)
│  Description: [User reported: overheat]  │  ← from query
│  Priority: [Important ▼               ]  │  ← from symptom severity
│  Due Date: [                          ]  │  ← user fills
│                                           │
│  Warnings: [None]                         │
│                                           │
│  [Cancel]  [Create Work Order]            │
└───────────────────────────────────────────┘
                │
    User clicks [Create Work Order]
                │
                ▼
┌───────────────────────────────────────────┐
│  COMMIT PHASE                             │
│  - Re-validate all fields                 │
│  - Execute INSERT                         │
│  - Write to pms_audit_log (signature={}) │
│  - Return result                          │
└───────────────────────────────────────────┘
```

---

## 2. DB FIELD CLASSIFICATION

### 2.1 pms_work_orders (CREATE)

| Field | Classification | Source | Auto-Population Rule |
|-------|---------------|--------|---------------------|
| id | BACKEND_AUTO | `gen_random_uuid()` | Never from user |
| yacht_id | BACKEND_AUTO | `get_user_yacht_id()` | From RLS context |
| wo_number | BACKEND_AUTO | `generate_wo_number()` | Never from user |
| **title** | **REQUIRED** | User/Entity | `{equipment} - {symptom}` or user input |
| description | OPTIONAL | User/Entity | `User reported: {symptom}` + user input |
| **type** | **REQUIRED** | Default | `corrective` for fault-linked, `unplanned` otherwise |
| **priority** | **REQUIRED** | Entity/Default | Map symptom severity → priority |
| status | BACKEND_AUTO | System | Always `planned` on create |
| equipment_id | OPTIONAL | Entity resolution | Lookup from `equipment` canonical |
| fault_id | OPTIONAL | Entity resolution | Lookup from `fault_code` or context |
| assigned_to | OPTIONAL | Entity resolution | Lookup from `person` canonical |
| due_date | OPTIONAL | User input | Parse from "by Friday", "next week" |
| due_hours | OPTIONAL | User input | Running hours deadline |
| frequency | CONTEXT | N/A | Only for scheduled type |
| metadata | OPTIONAL | System | Store entity extraction context |
| created_at | BACKEND_AUTO | `NOW()` | Never from user |
| created_by | BACKEND_AUTO | `auth.uid()` | Never from user |
| updated_at | BACKEND_AUTO | `NOW()` | Never from user |

### 2.2 pms_work_order_notes (ADD NOTE)

| Field | Classification | Source | Auto-Population Rule |
|-------|---------------|--------|---------------------|
| id | BACKEND_AUTO | `gen_random_uuid()` | Never from user |
| work_order_id | **REQUIRED** | Context | From focused WO |
| **note_text** | **REQUIRED** | User input | Could prefill from query |
| note_type | OPTIONAL | Default | `general` |
| created_at | BACKEND_AUTO | `NOW()` | Never from user |
| created_by | BACKEND_AUTO | `auth.uid()` | Never from user |
| is_private | OPTIONAL | Default | `false` |

### 2.3 Reassign Work Order (SIGNED)

| Field | Classification | Source | Auto-Population Rule |
|-------|---------------|--------|---------------------|
| work_order_id | **REQUIRED** | Context | From focused WO |
| **new_assignee_id** | **REQUIRED** | User selection | Prefill dropdown with yacht crew |
| **reason** | **REQUIRED** | User input | N/A |
| **signature** | **REQUIRED** | Device | Captured on confirm |

### 2.4 Archive Work Order (SIGNED)

| Field | Classification | Source | Auto-Population Rule |
|-------|---------------|--------|---------------------|
| work_order_id | **REQUIRED** | Context | From focused WO |
| **deletion_reason** | **REQUIRED** | User input | N/A |
| **signature** | **REQUIRED** | Device | Captured on confirm |

---

## 3. REGISTRY EXTENSION

### 3.1 New Fields in ActionDefinition

Per q&a2.md Q1/Q4, use `field_metadata` structure:

```python
class FieldClassification(str, Enum):
    """Classification of action fields."""
    REQUIRED = "REQUIRED"           # Must be provided (user or auto)
    OPTIONAL = "OPTIONAL"           # Can be omitted
    BACKEND_AUTO = "BACKEND_AUTO"   # System-generated (id, timestamps, yacht_id)
    CONTEXT = "CONTEXT"             # Derived from context (e.g., frequency for scheduled)


class FieldMetadata:
    """Metadata for a single field in an action."""
    def __init__(
        self,
        classification: FieldClassification,
        auto_populate_from: str = None,       # Entity type: "equipment", "symptom", "query_text", "auth_context"
        lookup_required: bool = False,        # Needs DB resolution (equipment_id, fault_id, etc.)
        compose_template: str = None,         # For composing fields: "{equipment} - {symptom}"
        value_map: Dict[str, str] = None,     # Direct mapping: {"urgent": "critical"}
        default: Any = None,                  # Default value if not populated
    ):
        self.classification = classification
        self.auto_populate_from = auto_populate_from
        self.lookup_required = lookup_required
        self.compose_template = compose_template
        self.value_map = value_map
        self.default = default


class ActionDefinition:
    def __init__(
        self,
        # ... existing fields ...

        # NEW: Field metadata (per q&a2.md)
        field_metadata: Dict[str, FieldMetadata] = None,

        # NEW: Two-phase indicator
        two_phase: bool = False,
    ):
        # ...
        self.field_metadata = field_metadata or {}
        self.two_phase = two_phase
```

### 3.2 Field Metadata Schema

```python
field_metadata = {
    "<field_name>": FieldMetadata(
        classification=FieldClassification.REQUIRED,
        auto_populate_from="<entity_type>",      # equipment, symptom, query_text, auth_context
        lookup_required=True,                     # Needs yacht-scoped DB lookup
        compose_template="{equipment} - {symptom}", # For composing values
        value_map={"urgent": "critical"},         # Direct mapping
        default="routine",                        # Default if not populated
    )
}
```

### 3.3 Work Order Actions with Field Metadata

```python
"create_work_order": ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/create",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "eto", "engineer", "chief_engineer", "captain", "manager"],
    required_fields=["yacht_id", "title", "type", "priority"],
    domain="work_orders",
    variant=ActionVariant.MUTATE,
    search_keywords=["create", "add", "new", "work", "order", "wo", "maintenance"],

    # NEW: Two-phase pattern (prepare → commit)
    two_phase=True,

    # NEW: Field metadata (per q&a2.md)
    field_metadata={
        # BACKEND_AUTO fields (system-generated)
        "id": FieldMetadata(classification=FieldClassification.BACKEND_AUTO),
        "yacht_id": FieldMetadata(classification=FieldClassification.BACKEND_AUTO, auto_populate_from="auth_context"),
        "wo_number": FieldMetadata(classification=FieldClassification.BACKEND_AUTO),
        "status": FieldMetadata(classification=FieldClassification.BACKEND_AUTO, default="planned"),
        "created_at": FieldMetadata(classification=FieldClassification.BACKEND_AUTO),
        "created_by": FieldMetadata(classification=FieldClassification.BACKEND_AUTO, auto_populate_from="auth_context"),

        # REQUIRED fields
        "title": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="equipment,symptom",
            compose_template="{equipment} - {symptom}",
        ),
        "type": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            default="unplanned",
        ),
        "priority": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="priority_indicator",
            value_map={"urgent": "critical", "asap": "important", "emergency": "emergency"},
            default="routine",
        ),

        # OPTIONAL fields with auto-population
        "equipment_id": FieldMetadata(
            classification=FieldClassification.OPTIONAL,
            auto_populate_from="equipment",
            lookup_required=True,
        ),
        "fault_id": FieldMetadata(
            classification=FieldClassification.OPTIONAL,
            auto_populate_from="fault_code",
            lookup_required=True,
        ),
        "assigned_to": FieldMetadata(
            classification=FieldClassification.OPTIONAL,
            auto_populate_from="person",
            lookup_required=True,
        ),
        "description": FieldMetadata(
            classification=FieldClassification.OPTIONAL,
            auto_populate_from="symptom,query_text",
            compose_template="User reported: {symptom}",
        ),
        "due_date": FieldMetadata(classification=FieldClassification.OPTIONAL),
    },
),

"add_note_to_work_order": ActionDefinition(
    action_id="add_note_to_work_order",
    label="Add Note",
    endpoint="/v1/work-orders/add-note",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "eto", "engineer", "chief_engineer", "captain", "manager"],
    required_fields=["yacht_id", "work_order_id", "note_text"],
    domain="work_orders",
    variant=ActionVariant.MUTATE,
    search_keywords=["add", "note", "comment", "work", "order", "wo"],

    # Single-phase (fast capture)
    two_phase=False,

    field_metadata={
        "work_order_id": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="focused_entity",
        ),
        "note_text": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="symptom,query_text",
            compose_template="Observation: {symptom}",
        ),
        "note_type": FieldMetadata(classification=FieldClassification.OPTIONAL, default="general"),
        "is_private": FieldMetadata(classification=FieldClassification.OPTIONAL, default=False),
    },
),

"reassign_work_order": ActionDefinition(
    action_id="reassign_work_order",
    label="Reassign Work Order",
    endpoint="/v1/work-orders/reassign",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "captain", "manager"],
    required_fields=["yacht_id", "work_order_id", "new_assignee_id", "reason", "signature"],
    domain="work_orders",
    variant=ActionVariant.SIGNED,
    search_keywords=["reassign", "transfer", "handover", "work", "order", "wo", "assignee"],

    # Two-phase for signed actions
    two_phase=True,

    field_metadata={
        "work_order_id": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="focused_entity",
        ),
        "new_assignee_id": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="person",
            lookup_required=True,
        ),
        "reason": FieldMetadata(classification=FieldClassification.REQUIRED),
        "signature": FieldMetadata(classification=FieldClassification.REQUIRED),
    },
),

"archive_work_order": ActionDefinition(
    action_id="archive_work_order",
    label="Archive Work Order",
    endpoint="/v1/work-orders/archive",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["captain", "manager"],
    required_fields=["yacht_id", "work_order_id", "deletion_reason", "signature"],
    domain="work_orders",
    variant=ActionVariant.SIGNED,
    search_keywords=["archive", "delete", "remove", "close", "work", "order", "wo"],

    # Two-phase for signed actions
    two_phase=True,

    field_metadata={
        "work_order_id": FieldMetadata(
            classification=FieldClassification.REQUIRED,
            auto_populate_from="focused_entity",
        ),
        "deletion_reason": FieldMetadata(classification=FieldClassification.REQUIRED),
        "signature": FieldMetadata(classification=FieldClassification.REQUIRED),
    },
),
```

---

## 4. PIPELINE MODIFICATIONS

### 4.1 Two-Phase Pattern (per q&a2.md)

**Contract:**
- **Prepare (READ)** → Returns `mutation_preview` with proposed payload, required fields, warnings, lookup options
- **Commit (MUTATE/SIGNED)** → Re-validates, executes, writes audit, returns result

**Endpoints:**
- `POST /v1/work-orders/create/prepare` → mutation_preview
- `POST /v1/work-orders/create/commit` → execute + audit

### 4.2 New File: `apps/api/action_router/prefill_engine.py`

```python
"""
Prefill Engine - Applies field_metadata to generate mutation_preview.

Per q&a2.md:
- Prepare populates proposed_payload using field_metadata
- Execute re-validates; 400 on missing/ambiguous; never 500
- All lookups are yacht-scoped via RLS
"""

from typing import Dict, List, Any, Optional
from .registry import get_action, FieldClassification

# Lookup functions registry (yacht-scoped)
LOOKUP_FUNCTIONS = {
    "equipment": lookup_equipment_by_name,
    "fault_code": lookup_fault_by_code,
    "person": lookup_user_by_name,
}


async def build_mutation_preview(
    action_id: str,
    entities: Dict[str, Any],
    context: Dict[str, Any],
    focused_entity: Optional[Dict] = None,
) -> Dict:
    """
    Build mutation_preview for two-phase actions.

    Args:
        action_id: The action to prepare
        entities: Extracted entities from NLP pipeline
        context: Request context (yacht_id, user_id from JWT)
        focused_entity: Optional focused entity context (e.g., equipment user clicked)

    Returns:
        {
            "mutation_preview": {
                "proposed_payload": {"field": "value", ...},
                "required_fields": ["field1", "field2"],
                "warnings": ["Duplicate WO exists for this equipment"],
                "lookup_options": {"field": [{"id": "...", "label": "..."}]}
            }
        }
    """
    action = get_action(action_id)
    field_meta = action.field_metadata
    yacht_id = context["yacht_id"]

    proposed_payload = {}
    required_fields = []
    warnings = []
    lookup_options = {}

    # Process each field based on metadata
    for field_name, meta in field_meta.items():
        # Skip BACKEND_AUTO fields in preview (system handles)
        if meta.classification == FieldClassification.BACKEND_AUTO:
            continue

        # Track required fields
        if meta.classification == FieldClassification.REQUIRED:
            required_fields.append(field_name)

        # Handle auth_context auto-population
        if meta.auto_populate_from == "auth_context":
            if field_name == "yacht_id":
                proposed_payload["yacht_id"] = yacht_id
            continue

        # Handle focused_entity auto-population
        if meta.auto_populate_from == "focused_entity" and focused_entity:
            proposed_payload[field_name] = focused_entity.get("id")
            proposed_payload[f"{field_name}_label"] = focused_entity.get("name")
            continue

        # Handle entity-based auto-population
        if meta.auto_populate_from:
            entity_types = meta.auto_populate_from.split(",")
            for entity_type in entity_types:
                entity_value = entities.get(entity_type.strip())
                if not entity_value:
                    continue

                # Lookup required - resolve to UUID
                if meta.lookup_required:
                    lookup_fn = LOOKUP_FUNCTIONS.get(entity_type.strip())
                    if lookup_fn:
                        options = await lookup_fn(entity_value, yacht_id)
                        if len(options) == 1:
                            proposed_payload[field_name] = options[0]["id"]
                            proposed_payload[f"{field_name}_label"] = options[0]["label"]
                        elif len(options) > 1:
                            lookup_options[field_name] = options
                        # 0 options = leave unresolved (user fills)
                    break

                # Compose template
                elif meta.compose_template:
                    # Collect all entity values for template
                    template_values = {et.strip(): entities.get(et.strip(), "") for et in entity_types}
                    composed = meta.compose_template.format(**template_values)
                    proposed_payload[field_name] = composed.strip(" -")
                    break

                # Value mapping
                elif meta.value_map:
                    mapped = meta.value_map.get(entity_value.lower())
                    if mapped:
                        proposed_payload[field_name] = mapped
                        break

                # Direct assignment
                else:
                    proposed_payload[field_name] = entity_value
                    break

        # Apply defaults for missing fields
        if field_name not in proposed_payload and meta.default is not None:
            proposed_payload[field_name] = meta.default

    # Add warnings (e.g., duplicate check)
    if action_id == "create_work_order" and proposed_payload.get("equipment_id"):
        duplicate = await check_duplicate_wo(
            equipment_id=proposed_payload["equipment_id"],
            yacht_id=yacht_id
        )
        if duplicate:
            warnings.append(f"Active WO already exists: {duplicate['wo_number']}")

    return {
        "mutation_preview": {
            "proposed_payload": proposed_payload,
            "required_fields": required_fields,
            "warnings": warnings,
            "lookup_options": lookup_options,
        }
    }


async def lookup_equipment_by_name(name: str, yacht_id: str) -> List[Dict]:
    """
    Lookup equipment by name within yacht scope.
    Returns [{"id": uuid, "label": name}, ...]
    """
    # Query pms_equipment where name ILIKE %name% AND yacht_id = yacht_id
    pass


async def lookup_fault_by_code(code: str, yacht_id: str) -> List[Dict]:
    """Lookup fault by fault_code within yacht scope."""
    pass


async def lookup_user_by_name(name: str, yacht_id: str) -> List[Dict]:
    """Lookup crew member by name within yacht scope."""
    pass


async def check_duplicate_wo(equipment_id: str, yacht_id: str) -> Optional[Dict]:
    """Check for existing active WO on same equipment."""
    pass
```

### 4.3 Action Surfacing (per q&a2.md Q2)

**Do NOT create custom `/suggest` endpoint.** Actions are surfaced via:

1. **`GET /v1/actions/list?q=<query>&domain=work_orders`** - existing endpoint
2. **Frontend `useCelesteSearch`** stores query text in state
3. **SuggestedActions component** renders buttons alongside results

**Flow:**
```
User: "main engine overheating"
         │
         ▼
┌────────────────────────────────────┐
│  Frontend useCelesteSearch         │
│  - stores query in state           │
│  - calls /api/search (entities)    │
│  - calls /v1/actions/list?q=...    │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│  Results + SuggestedActions        │
│  (parallel, never bypass)          │
└────────────────────────────────────┘
         │
    User clicks [Create Work Order]
         │
         ▼
┌────────────────────────────────────┐
│  POST /v1/work-orders/create/prepare│
│  Body: {                           │
│    context: { yacht_id },          │
│    entities: { equipment, symptom },│
│    focused_entity: null            │
│  }                                 │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│  Response: mutation_preview        │
│  - proposed_payload                │
│  - required_fields                 │
│  - warnings                        │
│  - lookup_options                  │
└────────────────────────────────────┘
         │
    User confirms in modal
         │
         ▼
┌────────────────────────────────────┐
│  POST /v1/work-orders/create/commit│
│  Body: { payload: {...} }          │
│  - Re-validate                     │
│  - Execute INSERT                  │
│  - Audit log (signature={})        │
│  - Return result                   │
└────────────────────────────────────┘
```

### 4.4 Handler Updates: `apps/api/handlers/work_order_mutation_handlers.py`

Add prepare/commit methods:

```python
async def create_work_order_prepare(
    self,
    context: Dict,
    entities: Dict,
    focused_entity: Optional[Dict] = None,
) -> Dict:
    """
    Prepare phase for create_work_order.
    Returns mutation_preview with proposed payload.
    """
    from action_router.prefill_engine import build_mutation_preview

    return await build_mutation_preview(
        action_id="create_work_order",
        entities=entities,
        context=context,
        focused_entity=focused_entity,
    )


async def create_work_order_commit(
    self,
    payload: Dict,
    yacht_id: str,
    user_id: str,
) -> Dict:
    """
    Commit phase for create_work_order.
    Re-validates, executes, writes audit.
    """
    # Re-validate required fields
    required = ["title", "type", "priority"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")  # → 400

    # Re-validate lookups (equipment_id, fault_id must exist in yacht)
    if payload.get("equipment_id"):
        equipment = await self._validate_equipment(payload["equipment_id"], yacht_id)
        if not equipment:
            raise ValueError("Invalid equipment_id")  # → 400

    # Execute INSERT
    result = self.db.table("pms_work_orders").insert({
        "yacht_id": yacht_id,
        "title": payload["title"],
        "type": payload["type"],
        "priority": payload["priority"],
        "status": "planned",
        "equipment_id": payload.get("equipment_id"),
        "fault_id": payload.get("fault_id"),
        "assigned_to": payload.get("assigned_to"),
        "description": payload.get("description"),
        "due_date": payload.get("due_date"),
        "created_by": user_id,
    }).execute()

    work_order = result.data[0]

    # Write audit log (signature={} for non-signed)
    await self._write_audit_log(
        action="create_work_order",
        entity_type="work_order",
        entity_id=work_order["id"],
        yacht_id=yacht_id,
        user_id=user_id,
        payload=payload,
        signature={},  # NOT NULL per q&a2.md
    )

    return {
        "status": "success",
        "work_order_id": work_order["id"],
        "wo_number": work_order["wo_number"],
    }
```

---

## 5. RESPONSE STRUCTURE

### 5.1 GET /v1/actions/list Response (Existing)

```json
{
  "query": "create work order",
  "actions": [
    {
      "action_id": "create_work_order",
      "label": "Create Work Order",
      "variant": "MUTATE",
      "allowed_roles": ["crew", "eto", "engineer", "chief_engineer", "captain", "manager"],
      "match_score": 1.0,
      "two_phase": true
    },
    {
      "action_id": "add_to_handover",
      "label": "Add to Handover",
      "variant": "MUTATE",
      "match_score": 0.62,
      "two_phase": false
    }
  ],
  "total_count": 2,
  "role": "engineer"
}
```

### 5.2 POST /v1/work-orders/create/prepare Response

```json
{
  "mutation_preview": {
    "proposed_payload": {
      "title": "main engine - overheating",
      "description": "User reported: overheating",
      "type": "unplanned",
      "priority": "important",
      "equipment_id": "uuid-123",
      "equipment_id_label": "Main Engine",
      "status": "planned"
    },
    "required_fields": ["title", "type", "priority"],
    "warnings": [],
    "lookup_options": {}
  }
}
```

### 5.3 Prepare with Ambiguous Equipment

```json
{
  "mutation_preview": {
    "proposed_payload": {
      "title": "pump - leaking",
      "description": "User reported: leaking",
      "type": "unplanned",
      "priority": "routine"
    },
    "required_fields": ["title", "type", "priority"],
    "warnings": [],
    "lookup_options": {
      "equipment_id": [
        {"id": "uuid-456", "label": "Bilge Pump #1"},
        {"id": "uuid-789", "label": "Sea Water Pump"},
        {"id": "uuid-abc", "label": "Fuel Transfer Pump"}
      ]
    }
  }
}
```

### 5.4 POST /v1/work-orders/create/commit Response

**Success:**
```json
{
  "status": "success",
  "work_order_id": "uuid-new-wo",
  "wo_number": "WO-2026-0123"
}
```

**Validation Error (400):**
```json
{
  "status": "error",
  "error_code": "missing_required_fields",
  "message": "Missing required fields: ['title']",
  "action": "create_work_order"
}
```

### 5.5 Error Mapping (per q&a2.md)

| Error | HTTP Code | When |
|-------|-----------|------|
| Missing required fields | 400 | Commit without title/type/priority |
| Invalid equipment_id | 400 | UUID doesn't exist in yacht |
| Duplicate WO | 409 | Active WO exists for same equipment+fault |
| Unauthorized | 403 | Role not in allowed_roles |
| **Never 500** | - | Fix if this happens |

---

## 6. GUARDRAILS

### 6.1 Security

| Guardrail | Implementation |
|-----------|----------------|
| Yacht isolation | All lookups use `yacht_id` from JWT, not request |
| Role gating | `search_actions` already filters by role |
| Signature required | SIGNED actions require signature in execute payload |
| No cross-yacht candidates | Lookup functions MUST filter by `get_user_yacht_id()` |

### 6.2 Data Integrity

| Guardrail | Implementation |
|-----------|----------------|
| Re-validate on execute | Execute endpoint re-resolves IDs, 400 on invalid |
| No silent fallback | If lookup fails, field goes to `unresolved`, not skipped |
| Audit trail | All executions logged to `pms_audit_log` |

### 6.3 UX

| Guardrail | Implementation |
|-----------|----------------|
| Editable prefill | All prefilled values can be modified by user |
| Clear unresolved | `unresolved` array tells UI which fields need attention |
| Lookup options | Multiple matches provide dropdown options |

---

## 7. TEST SCENARIOS

### 7.1 Unit Tests

| Test | Input | Expected Output |
|------|-------|-----------------|
| Direct action match | "create work order" | `match_score: 1.0`, minimal prefill |
| Entity extraction + prefill | "main engine overheating" | equipment + symptom extracted, title composed |
| Equipment resolution | "fix generator" | equipment_id resolved or in lookup_options |
| Priority mapping | "urgent bilge pump leak" | priority: "critical" |
| Role gating | crew user + "archive work order" | action not in results |
| Yacht isolation | lookup_equipment with different yacht | empty results |

### 7.2 Integration Tests

| Test | Steps | Expected |
|------|-------|----------|
| Full flow | Query → Suggest → Prefill → Execute | WO created with correct data |
| SIGNED action | Suggest → Prefill → Execute without signature | 400 error |
| Ambiguous equipment | "pump" (multiple matches) | lookup_options populated |

---

## 8. FILES TO CREATE/MODIFY

### New Files

| File | Purpose |
|------|---------|
| `apps/api/action_router/prefill_engine.py` | `build_mutation_preview()` using field_metadata |
| `apps/api/action_router/lookup_functions.py` | Yacht-scoped entity resolution |
| `tests/unit/test_prefill_engine.py` | Unit tests for prepare logic |
| `tests/integration/test_wo_two_phase.py` | Integration tests for prepare/commit |

### Modified Files

| File | Changes |
|------|---------|
| `apps/api/action_router/registry.py` | Add `FieldMetadata`, `FieldClassification`, `field_metadata`, `two_phase` to ActionDefinition |
| `apps/api/action_router/router.py` | Add `two_phase` to `/list` response |
| `apps/api/handlers/work_order_mutation_handlers.py` | Add `create_work_order_prepare()`, `create_work_order_commit()` |
| `apps/api/routes/p0_actions_routes.py` | Wire `/v1/work-orders/create/prepare` and `/commit` endpoints |
| `apps/api/intent_parser.py` | Remove n8n references (currently routes to n8n webhooks for mutations) |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | Bridge prepare/commit handlers |

---

## 9. IMPLEMENTATION ORDER

1. **Phase 1: Registry Extension**
   - Add `FieldMetadata`, `FieldClassification` classes
   - Add `field_metadata`, `two_phase` to `ActionDefinition`
   - Update `create_work_order` action with field_metadata
   - Update `/list` response to include `two_phase`
   - No behavior change yet

2. **Phase 2: Prefill Engine**
   - Create `apps/api/action_router/prefill_engine.py`
   - Implement `build_mutation_preview()` using field_metadata
   - Create lookup function stubs

3. **Phase 3: Lookup Functions**
   - Implement `lookup_equipment_by_name()` (yacht-scoped)
   - Implement `lookup_fault_by_code()` (yacht-scoped)
   - Implement `lookup_user_by_name()` (yacht-scoped)
   - Implement `check_duplicate_wo()` (for warnings)

4. **Phase 4: Two-Phase Handlers**
   - Add `create_work_order_prepare()` to handlers
   - Add `create_work_order_commit()` to handlers
   - Wire prepare/commit routes in `p0_actions_routes.py`
   - Bridge in `internal_dispatcher.py`

5. **Phase 5: Audit Integration**
   - Ensure commit writes to `pms_audit_log`
   - `signature={}` for non-signed actions
   - Verify NOT NULL constraint

6. **Phase 6: Testing**
   - Unit tests for prefill engine
   - Integration tests for prepare → commit flow
   - Acceptance tests with real JWT
   - Test 400/404 error responses (never 500)

7. **Phase 7: Cleanup**
   - Remove n8n references from `intent_parser.py`
   - Update documentation

---

## 10. BRANCH STRATEGY

**Branch**: `work-order/action-buttons-prefill`
**Base**: `main`

### Commit Plan

```
work-order/action-buttons-prefill
    │
    ├── commit 1: Add FieldMetadata, FieldClassification to registry
    ├── commit 2: Add field_metadata to create_work_order action
    ├── commit 3: Add two_phase flag and update /list response
    ├── commit 4: Create prefill_engine.py with build_mutation_preview
    ├── commit 5: Implement yacht-scoped lookup functions
    ├── commit 6: Add create_work_order_prepare handler
    ├── commit 7: Add create_work_order_commit handler
    ├── commit 8: Wire /prepare and /commit routes
    ├── commit 9: Audit log integration (signature={})
    ├── commit 10: Unit tests for prefill engine
    ├── commit 11: Integration tests for two-phase flow
    ├── commit 12: Remove n8n references from intent_parser
    └── PR → main
```

### PR Strategy (per q&a2.md Q5)

Consider splitting into 2-3 focused PRs:

1. **PR 1: Registry + Prefill Engine** (commits 1-5)
   - Field metadata structure
   - Prefill logic
   - Lookup functions

2. **PR 2: Handlers + Routes** (commits 6-9)
   - Two-phase handlers
   - Endpoint wiring
   - Audit integration

3. **PR 3: Tests + Cleanup** (commits 10-12)
   - Unit tests
   - Integration tests
   - n8n cleanup

---

## 11. DEPENDENCIES

| Dependency | Status | Notes |
|------------|--------|-------|
| Registry exists | ✅ | `apps/api/action_router/registry.py` |
| WO handlers exist | ✅ | `apps/api/handlers/work_order_mutation_handlers.py` |
| Routes exist | ✅ | `apps/api/routes/p0_actions_routes.py` |
| pms_audit_log | ✅ | Table exists with signature NOT NULL |
| Entity extraction | ✅ | `module_b_entity_extractor.py` |
| Action search | ✅ | `search_actions()` in registry |

---

## 12. RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| Lookup returns wrong yacht's data | All lookups use `yacht_id` from JWT, never request body |
| 500 errors | Validate all inputs; use 400/404 for client errors |
| Duplicate WO created | Check in prepare phase + re-check in commit |
| n8n references break | Feature flag or staged removal |

---

**END OF PLAN**

Ready for review.
