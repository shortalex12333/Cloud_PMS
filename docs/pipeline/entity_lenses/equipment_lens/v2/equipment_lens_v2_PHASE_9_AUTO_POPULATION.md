# Equipment Lens v2 - PHASE 9: AUTO-POPULATION & ACTION SURFACING

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 9 defines how Equipment Lens actions are:
1. **Surfaced** - How action buttons appear based on user queries
2. **Auto-populated** - How fields are pre-filled from context
3. **Executed** - Two-phase prepare/commit pattern where needed

This follows guidance from `docs/pipeline/q&a2.md`.

---

## PART 1: ACTION SURFACING

### How Users Request Actions

| User Query | Intent | Action Surfaced |
|------------|--------|-----------------|
| "create work order" | Explicit action | `create_work_order_for_equipment` button |
| "mark gen 2 failed" | Explicit action + entity | `update_equipment_status` with equipment pre-filled |
| "add note to watermaker" | Explicit action + entity | `add_equipment_note` with equipment pre-filled |
| "main engine overheating" | Entity search | Results first, then actions on focus |
| "equipment needing attention" | Entity filter | Results, then actions on focus |

### Surfacing Behavior (from Q&A)

**Rule**: Action buttons appear **alongside results** in SuggestedActions section. No pre-search bypass.

```
User Query: "create work order"
    ↓
Entity Extraction: (no entities)
Intent Parser: action_intent detected
    ↓
Search Orchestrator: RetrievalPlan (may be empty if pure action query)
    ↓
PARALLEL:
  - Entity Results: [] (empty)
  - Action Suggestions: [create_work_order_for_equipment, ...]
    ↓
Frontend Renders:
  ┌─────────────────────────────────────────────┐
  │  SUGGESTED ACTIONS                          │
  │  [Create Work Order] [Report Fault] ...     │
  ├─────────────────────────────────────────────┤
  │  No results found for "create work order"   │
  └─────────────────────────────────────────────┘
```

### Action Search Keywords (Registry)

Each Equipment Lens action needs strong `search_keywords` for explicit matching:

```python
# update_equipment_status
search_keywords=[
    "status", "update", "mark", "change",
    "failed", "operational", "degraded", "maintenance",
    "broken", "working", "down", "up", "fix"
]

# add_equipment_note
search_keywords=[
    "note", "log", "record", "observation",
    "comment", "remark", "entry", "write"
]

# attach_file_to_equipment
search_keywords=[
    "photo", "picture", "upload", "attach",
    "document", "image", "file", "camera", "snap"
]

# create_work_order_for_equipment
search_keywords=[
    "work order", "wo", "job", "task",
    "maintenance", "repair", "fix", "service",
    "create wo", "new job", "raise wo"
]

# decommission_equipment
search_keywords=[
    "decommission", "remove", "retire", "dispose",
    "scrap", "end of life", "decom"
]
```

---

## PART 2: ENTITY EXTRACTION ADDITIONS

### New Entity Type: `status`

Add to extraction pipeline for equipment status keywords:

**File**: `apps/api/extraction/patterns/equipment_patterns.py` (or equivalent)

```python
STATUS_PATTERNS = {
    "operational": ["operational", "working", "running", "ok", "good", "up"],
    "degraded": ["degraded", "reduced", "partial", "limited", "struggling"],
    "failed": ["failed", "broken", "down", "dead", "not working", "kaput"],
    "maintenance": ["maintenance", "service", "servicing", "under repair"],
}

# Regex pattern for extraction
STATUS_REGEX = r"\b(operational|working|running|failed|broken|down|degraded|maintenance|servicing)\b"
```

### Entity Extraction Output

For query "mark gen 2 failed":

```json
{
  "entities": {
    "equipment": [
      {"text": "gen 2", "confidence": 0.95, "source": "regex"}
    ],
    "status": [
      {"text": "failed", "confidence": 0.90, "source": "regex"}
    ]
  },
  "entities_provenance": {
    "equipment": [{"text": "gen 2", "source": "regex", "confidence": 0.95, "span": [5, 10]}],
    "status": [{"text": "failed", "source": "regex", "confidence": 0.90, "span": [11, 17]}]
  }
}
```

---

## PART 3: FIELD METADATA SPECIFICATION

### Registry Extension

Add `field_metadata` to each ActionDefinition:

```python
from dataclasses import dataclass
from typing import Dict, Optional, Literal

@dataclass
class FieldSpec:
    classification: Literal["REQUIRED", "OPTIONAL", "BACKEND_AUTO", "CONTEXT"]
    auto_populate_from: Optional[str] = None  # Entity type or special source
    lookup_required: bool = False  # True if needs DB lookup (e.g., name → UUID)
    default_value: Optional[str] = None  # Default if not extracted

# Example for update_equipment_status
field_metadata: Dict[str, FieldSpec] = {
    "equipment_id": FieldSpec(
        classification="CONTEXT",
        auto_populate_from="equipment",  # From extracted entity
        lookup_required=True,  # Need to resolve name → UUID
    ),
    "status": FieldSpec(
        classification="REQUIRED",
        auto_populate_from="status",  # From extracted entity
        lookup_required=False,  # Direct value
    ),
    "attention_reason": FieldSpec(
        classification="OPTIONAL",
        auto_populate_from="query_text",  # Use full query as default
        lookup_required=False,
    ),
    "clear_attention": FieldSpec(
        classification="OPTIONAL",
        auto_populate_from=None,
        default_value="false",
    ),
    "yacht_id": FieldSpec(
        classification="BACKEND_AUTO",
        auto_populate_from="auth_context",
        lookup_required=False,
    ),
}
```

### Field Metadata for All Equipment Actions

#### `update_equipment_status`

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | equipment entity | YES (name→UUID) |
| `status` | REQUIRED | status entity | NO |
| `attention_reason` | OPTIONAL | query_text | NO |
| `clear_attention` | OPTIONAL | - | NO (default: false) |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

#### `add_equipment_note`

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | equipment entity | YES |
| `text` | REQUIRED | query_text (residual) | NO |
| `note_type` | OPTIONAL | - | NO (default: observation) |
| `requires_ack` | OPTIONAL | - | NO (default: false) |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

#### `attach_file_to_equipment`

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | equipment entity | YES |
| `file` | REQUIRED | - | NO (user upload) |
| `description` | OPTIONAL | query_text | NO |
| `tags` | OPTIONAL | - | NO |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

#### `create_work_order_for_equipment`

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | equipment entity | YES |
| `title` | REQUIRED | query_text | NO |
| `description` | OPTIONAL | query_text (expanded) | NO |
| `type` | REQUIRED | - | NO (user selects) |
| `priority` | REQUIRED | - | NO (user selects) |
| `assigned_to` | OPTIONAL | - | NO |
| `due_date` | OPTIONAL | - | NO |
| `fault_severity` | CONTEXT | - | NO (appears if type=corrective) |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

#### `link_part_to_equipment`

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | focused equipment | YES |
| `part_id` | REQUIRED | part entity | YES |
| `quantity_required` | OPTIONAL | - | NO (default: 1) |
| `notes` | OPTIONAL | - | NO |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

#### `decommission_equipment` (SIGNED)

| Field | Classification | Auto-populate From | Lookup |
|-------|----------------|-------------------|--------|
| `equipment_id` | CONTEXT | focused equipment | YES |
| `reason` | REQUIRED | - | NO (user enters) |
| `replacement_equipment_id` | OPTIONAL | - | YES |
| `signature` | REQUIRED | - | NO (user signs) |
| `yacht_id` | BACKEND_AUTO | auth_context | NO |

---

## PART 4: PREPARE/EXECUTE FLOW

### Single-Phase Actions (Most Equipment Actions)

For simple mutations, use single-phase:

```
User clicks action button
    ↓
Frontend sends: POST /v1/actions/execute
{
  "action": "update_equipment_status",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid",  // From focus or lookup
    "extracted_entities": { "status": "failed" }
  },
  "payload": {
    "status": "failed",
    "attention_reason": "Alternator bearing failure"
  }
}
    ↓
Backend:
  1. Validate JWT + yacht isolation
  2. Validate role (engineer+)
  3. Validate equipment_id exists and belongs to yacht
  4. Execute mutation
  5. Write audit log
  6. Trigger notifications (if applicable)
  7. Return result
```

**Single-phase actions**:
- `update_equipment_status`
- `add_equipment_note`
- `attach_file_to_equipment`
- `flag_equipment_attention`
- `link_part_to_equipment`

### Two-Phase Actions (Complex Mutations)

For actions with cascades or complex prefill:

#### `create_work_order_for_equipment`

**Phase 1: Prepare (READ)**

```
POST /v1/actions/prepare
{
  "action": "create_work_order_for_equipment",
  "context": {
    "yacht_id": "uuid",
    "equipment_id": "uuid",
    "extracted_entities": {
      "equipment": "main engine",
      "symptom": "overheating"
    },
    "query_text": "main engine overheating"
  }
}
    ↓
Response (mutation_preview):
{
  "success": true,
  "mutation_preview": {
    "proposed_payload": {
      "equipment_id": "uuid",
      "equipment_name": "Main Engine #1",  // For display
      "title": "main engine overheating",
      "description": "main engine overheating",
      "type": null,  // User must select
      "priority": null,  // User must select
      "fault_severity": null  // Appears if type=corrective
    },
    "required_fields": ["title", "type", "priority"],
    "optional_fields": ["description", "assigned_to", "due_date"],
    "conditional_fields": {
      "fault_severity": {
        "show_when": "type IN ('corrective', 'breakdown')"
      }
    },
    "warnings": [],  // e.g., "Equipment already has 3 open WOs"
    "duplicate_check": {
      "similar_wos": []  // Recent WOs for this equipment
    }
  }
}
```

**Phase 2: Commit (MUTATE)**

```
POST /v1/actions/execute
{
  "action": "create_work_order_for_equipment",
  "context": { "yacht_id": "uuid", "equipment_id": "uuid" },
  "payload": {
    "title": "Main Engine #1 overheating - investigate",
    "description": "Reported overheating during passage. Check coolant levels and thermostat.",
    "type": "corrective",
    "priority": "critical",
    "fault_severity": "high"
  }
}
    ↓
Backend:
  1. Re-validate all fields
  2. Create work order
  3. Create fault (because type=corrective)
  4. Write audit log for both
  5. Trigger notifications
  6. Return result with available_actions
```

#### `decommission_equipment` (SIGNED, Two-Phase)

**Phase 1: Prepare**

```
POST /v1/actions/prepare
{
  "action": "decommission_equipment",
  "context": { "yacht_id": "uuid", "equipment_id": "uuid" }
}
    ↓
Response:
{
  "mutation_preview": {
    "proposed_payload": {
      "equipment_id": "uuid",
      "equipment_name": "Watermaker #1",
      "current_status": "failed",
      "active_faults": 0,
      "open_work_orders": 0,
      "last_activity": "2025-12-01"
    },
    "required_fields": ["reason", "signature"],
    "warnings": [
      "This action is PERMANENT and cannot be reversed",
      "Equipment has 15 historical work orders that will remain linked"
    ],
    "signature_required": true
  }
}
```

**Phase 2: Commit (SIGNED)**

Requires full signature payload.

---

## PART 5: EQUIPMENT LOOKUP RESOLUTION

### Name-to-UUID Resolution

When user types "gen 2" or "main engine", system must resolve to UUID:

```python
async def resolve_equipment(
    equipment_text: str,
    yacht_id: UUID,
    db: AsyncSession
) -> Optional[EquipmentMatch]:
    """
    Resolve equipment name/code to UUID.
    Yacht-scoped, returns best match with confidence.
    """
    # Try exact code match first
    result = await db.execute(
        select(Equipment)
        .where(Equipment.yacht_id == yacht_id)
        .where(Equipment.deleted_at.is_(None))
        .where(func.lower(Equipment.code) == equipment_text.lower())
    )
    exact = result.scalar_one_or_none()
    if exact:
        return EquipmentMatch(
            id=exact.id,
            name=exact.name,
            code=exact.code,
            confidence=1.0,
            match_type="exact_code"
        )

    # Try fuzzy name match
    result = await db.execute(
        select(Equipment)
        .where(Equipment.yacht_id == yacht_id)
        .where(Equipment.deleted_at.is_(None))
        .where(func.lower(Equipment.name).contains(equipment_text.lower()))
        .limit(5)
    )
    matches = result.scalars().all()

    if len(matches) == 1:
        return EquipmentMatch(
            id=matches[0].id,
            name=matches[0].name,
            code=matches[0].code,
            confidence=0.9,
            match_type="fuzzy_name"
        )
    elif len(matches) > 1:
        # Multiple matches - return candidates for user selection
        return EquipmentMatchAmbiguous(
            candidates=[
                {"id": m.id, "name": m.name, "code": m.code}
                for m in matches
            ],
            confidence=0.5,
            match_type="ambiguous"
        )

    return None  # No match
```

### Resolution Flow in Prepare

```python
async def prepare_equipment_action(
    action_id: str,
    context: Dict,
    extracted_entities: Dict,
    db: AsyncSession
) -> MutationPreview:
    yacht_id = context["yacht_id"]

    # Resolve equipment from entities
    equipment_entity = extracted_entities.get("equipment", [{}])[0]
    equipment_text = equipment_entity.get("text")

    equipment_match = None
    if equipment_text:
        equipment_match = await resolve_equipment(equipment_text, yacht_id, db)

    # Build preview
    proposed_payload = {}

    if equipment_match:
        if isinstance(equipment_match, EquipmentMatchAmbiguous):
            # Multiple matches - user must select
            return MutationPreview(
                proposed_payload={},
                disambiguation_required=True,
                candidates=equipment_match.candidates,
                message=f"Multiple equipment found for '{equipment_text}'. Please select one."
            )
        else:
            proposed_payload["equipment_id"] = str(equipment_match.id)
            proposed_payload["equipment_name"] = equipment_match.name

    # Continue with other field population...
    return MutationPreview(
        proposed_payload=proposed_payload,
        required_fields=get_required_fields(action_id),
        ...
    )
```

---

## PART 6: CONTEXT CARRYOVER

### Frontend State (useCelesteSearch)

```typescript
// apps/web/src/hooks/useCelesteSearch.ts

interface SearchContext {
  query_text: string;
  extracted_entities: Record<string, EntityMatch[]>;
  focused_entity_type?: string;
  focused_entity_id?: string;
  orchestration_result?: OrchestrationResult;
}

// When user clicks an action, pass full context
const executeAction = async (actionId: string, payload: any) => {
  const response = await actionClient.execute({
    action: actionId,
    context: {
      yacht_id: user.yacht_id,
      query_text: searchContext.query_text,
      extracted_entities: searchContext.extracted_entities,
      focused_entity_id: searchContext.focused_entity_id,
      focused_entity_type: searchContext.focused_entity_type,
    },
    payload,
  });
  return response;
};
```

### Backend Uses Context for Prefill

```python
# In prepare handler
query_text = context.get("query_text", "")
extracted_entities = context.get("extracted_entities", {})

# Auto-populate title from query
proposed_payload["title"] = query_text

# Auto-populate description from query (expanded)
proposed_payload["description"] = query_text

# Auto-populate status from extracted entity
status_entities = extracted_entities.get("status", [])
if status_entities:
    proposed_payload["status"] = normalize_status(status_entities[0]["text"])
```

---

## PART 7: RESPONSE WITH AVAILABLE ACTIONS

### Action Chaining

After successful execution, return next available actions:

```python
# In handler, after successful mutation
return ActionResponseEnvelope(
    success=True,
    action_id="update_equipment_status",
    entity_id=str(equipment_id),
    entity_type="equipment",
    data={
        "old_status": old_status,
        "new_status": new_status,
        "attention_flag": attention_flag
    },
    available_actions=[
        {
            "action_id": "add_equipment_note",
            "label": "Add Note",
            "variant": "MUTATE",
            "context": {
                "equipment_id": str(equipment_id),
                "yacht_id": str(yacht_id)
            }
        },
        {
            "action_id": "create_work_order_for_equipment",
            "label": "Create Work Order",
            "variant": "MUTATE",
            "context": {
                "equipment_id": str(equipment_id),
                "yacht_id": str(yacht_id)
            }
        },
        {
            "action_id": "attach_file_to_equipment",
            "label": "Attach Photo",
            "variant": "MUTATE",
            "context": {
                "equipment_id": str(equipment_id),
                "yacht_id": str(yacht_id)
            }
        }
    ]
)
```

Frontend renders these as buttons for seamless workflow continuation.

---

## PART 8: ERROR HANDLING IN PREPARE/EXECUTE

### Prepare Errors (400, not 500)

| Condition | HTTP | Response |
|-----------|------|----------|
| Equipment text not found | 200 | `{ disambiguation_required: true, candidates: [] }` |
| Multiple equipment matches | 200 | `{ disambiguation_required: true, candidates: [...] }` |
| Equipment not in yacht | 404 | `{ error: "equipment_not_found" }` |
| Invalid extracted entity | 400 | `{ error: "invalid_entity", field: "status" }` |

### Execute Errors (400/404, never 500)

| Condition | HTTP | Response |
|-----------|------|----------|
| Missing required field | 400 | `{ error: "missing_field", field: "status" }` |
| Invalid field value | 400 | `{ error: "invalid_value", field: "status" }` |
| Equipment not found | 404 | `{ error: "equipment_not_found" }` |
| Cross-yacht access | 404 | `{ error: "equipment_not_found" }` (don't reveal) |
| Role not permitted | 403 | `{ error: "permission_denied" }` |
| Terminal state | 400 | `{ error: "invalid_state_transition" }` |
| Missing signature | 400 | `{ error: "signature_required" }` |

---

## PART 9: IMPLEMENTATION CHECKLIST

### Backend Changes

1. **Registry** (`apps/api/action_router/registry.py`)
   - [ ] Add `field_metadata` to ActionDefinition class
   - [ ] Add field specs for all Equipment actions
   - [ ] Update `search_keywords` for explicit action matching

2. **Entity Extraction** (`apps/api/extraction/`)
   - [ ] Add `status` entity type patterns
   - [ ] Add equipment status keywords to gazetteer

3. **Handlers** (`apps/api/handlers/equipment_handlers.py`)
   - [ ] Implement prepare handlers for two-phase actions
   - [ ] Implement execute handlers with re-validation
   - [ ] Add equipment resolution logic
   - [ ] Return `available_actions` in responses

4. **Dispatcher** (`apps/api/action_router/dispatchers/internal_dispatcher.py`)
   - [ ] Wire Equipment handlers

5. **Routes** (`apps/api/routes/p0_actions_routes.py`)
   - [ ] Add prepare endpoint for Equipment actions (if not generic)

### Frontend Changes

1. **useCelesteSearch** (`apps/web/src/hooks/useCelesteSearch.ts`)
   - [ ] Store and pass `query_text` and `extracted_entities` in context

2. **SuggestedActions** (`apps/web/src/components/SuggestedActions.tsx`)
   - [ ] Render Equipment action buttons

3. **ActionModal** (`apps/web/src/components/actions/ActionModal.tsx`)
   - [ ] Handle disambiguation UI (multiple equipment matches)
   - [ ] Render conditional fields (fault_severity when type=corrective)
   - [ ] Show prepare warnings

### Tests

1. **Docker RLS Tests** (`tests/docker/run_equipment_rls_tests.py`)
   - [ ] Test auto-population with extracted entities
   - [ ] Test disambiguation flow
   - [ ] Test prepare → execute flow

2. **Staging CI** (`tests/ci/staging_equipment_acceptance.py`)
   - [ ] Test explicit action queries
   - [ ] Test context carryover

---

## SUMMARY

| Aspect | Equipment Lens Implementation |
|--------|------------------------------|
| Action Surfacing | Via `search_keywords` in registry; alongside results |
| Auto-population | `field_metadata` in registry; resolved in prepare |
| Entity Extraction | Add `status` entity type for equipment status |
| Two-phase Actions | `create_work_order_for_equipment`, `decommission_equipment` |
| Single-phase Actions | All others (status, note, attach, link, flag) |
| Context Carryover | Frontend passes `query_text` + `extracted_entities` |
| Equipment Resolution | Name/code → UUID via yacht-scoped lookup |
| Disambiguation | Return candidates when multiple matches |
| Action Chaining | Return `available_actions` after success |
| Error Handling | 400/404 for client errors; never 500 |

---

**END OF PHASE 9**
