# CelesteOS - Generic Prefill Engine

This package provides the core infrastructure for Celeste's two-phase mutation system:

1. **`/prepare`** endpoint: Extracts entities → applies field_metadata → returns preview
2. **`/commit`** endpoint: Validates preview → executes mutation → returns result

## Architecture

```
┌──────────────┐
│ NLP Query    │ "create urgent work order for main engine overheating"
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Entity Extractor │ → {equipment: "main engine", symptom: "overheating", priority: "urgent"}
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Prefill Engine   │ → Applies field_metadata rules
│                  │   - Auto-populate from entities
│                  │   - Yacht-scoped lookups (equipment_id)
│                  │   - Compose templates ("{equipment} - {symptom}")
│                  │   - Value mapping ("urgent" → "critical")
│                  │   - Default values ("medium" for priority)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Mutation Preview │ → {equipment_id: "uuid-...", title: "main engine - overheating", ...}
│                  │   + missing_required: []
│                  │   + warnings: []
│                  │   + dropdown_options: {}
└──────────────────┘
```

## Files

### `field_metadata.py`
Defines the `FieldMetadata` schema for auto-population rules.

**Key properties:**
- `classification`: REQUIRED, OPTIONAL, BACKEND_AUTO, CONTEXT
- `auto_populate_from`: Entity type to extract (equipment, symptom, query_text, etc.)
- `compose_template`: Template for composing values (`"{equipment} - {symptom}"`)
- `lookup_required`: Whether to resolve entity name to UUID via DB lookup
- `value_map`: Dict for translating extracted values to canonical form
- `default`: Default value if entity not extracted

### `lookup_functions.py`
Yacht-scoped entity lookup functions for resolving names to UUIDs.

**Functions:**
- `lookup_equipment_by_name()`: Resolve equipment name → UUID
- `lookup_fault_by_symptom()`: Resolve symptom → fault UUID
- `lookup_part_by_name()`: Resolve part name → UUID
- `lookup_work_order_by_number()`: Resolve WO number → UUID

**Lookup behavior:**
- 0 matches: Returns `LookupResult(success=True, count=0, value=None)`
- 1 match: Returns `LookupResult(success=True, count=1, value=<uuid>)`
- 2+ matches: Returns `LookupResult(success=True, count=N, options=[{id, name, ...}])`

### `prefill_engine.py`
Core mutation preview builder.

**Main function:** `build_mutation_preview()`

**Process:**
1. For each field in field_metadata:
   - If `auto_populate_from`: Extract entity value
   - If `compose_template`: Compose value from multiple entities
   - If `value_map`: Translate value to canonical form
   - If `lookup_required`: Query DB for UUID (returns dropdown if ambiguous)
   - If `classification == BACKEND_AUTO`: Generate system value (uuid, timestamp)
2. Identify missing REQUIRED fields
3. Generate warnings for ambiguous/missing entities
4. Return mutation preview + metadata

### `prefill_examples.py`
Real-world examples showing field_metadata configurations for:
- Create Work Order
- Create Fault Report
- Reorder Part
- Update Equipment Status
- Assign Work Order

## Usage

### 1. Define Field Metadata

```python
from common.field_metadata import FieldMetadata

field_metadata = {
    "equipment_id": FieldMetadata(
        name="equipment_id",
        classification="REQUIRED",
        auto_populate_from="equipment",
        lookup_required=True,
    ),
    "title": FieldMetadata(
        name="title",
        classification="BACKEND_AUTO",
        auto_populate_from="equipment",
        compose_template="{equipment} - {symptom}",
    ),
    "priority": FieldMetadata(
        name="priority",
        classification="OPTIONAL",
        value_map={"urgent": "critical", "asap": "critical"},
        default="medium",
    ),
}
```

### 2. Build Mutation Preview

```python
from common.prefill_engine import build_mutation_preview

preview = await build_mutation_preview(
    query_text="create urgent work order for main engine overheating",
    extracted_entities={
        "equipment": "main engine",
        "symptom": "overheating",
        "priority": "urgent",
    },
    field_metadata=field_metadata,
    yacht_id="abc-123",
    supabase_client=client,
    user_id="user-456",
)
```

### 3. Handle Result

```python
if preview["ready_to_commit"]:
    # All required fields populated - ready for /commit
    return {
        "preview": preview["mutation_preview"],
        "ready_to_commit": True,
    }
else:
    # Show form with pre-filled values and missing/ambiguous fields
    return {
        "preview": preview["mutation_preview"],
        "missing_required": preview["missing_required"],
        "warnings": preview["warnings"],
        "dropdown_options": preview["dropdown_options"],
        "ready_to_commit": False,
    }
```

## Field Classifications

### REQUIRED
Must be provided by user or auto-populated from NLP.

**Example:**
```python
"equipment_id": FieldMetadata(
    name="equipment_id",
    classification="REQUIRED",
    auto_populate_from="equipment",
    lookup_required=True,
)
```

### OPTIONAL
May be provided by user, defaults to `default` value if not.

**Example:**
```python
"priority": FieldMetadata(
    name="priority",
    classification="OPTIONAL",
    default="medium",
)
```

### BACKEND_AUTO
Auto-generated by backend (uuid, timestamp, composed values).

**Example:**
```python
"title": FieldMetadata(
    name="title",
    classification="BACKEND_AUTO",
    compose_template="{equipment} - {symptom}",
)
```

### CONTEXT
From auth/session context (yacht_id, user_id).

**Example:**
```python
"yacht_id": FieldMetadata(
    name="yacht_id",
    classification="CONTEXT",
)
```

## Auto-Population Sources

### Entity Types
- `equipment`: EQUIPMENT_NAME entity
- `symptom`: SYMPTOM entity
- `query_text`: Raw query text
- `part`: PART_NAME or PART_NUMBER entity
- `fault`: FAULT_CODE entity
- `work_order`: WORK_ORDER_ID entity
- `stock_calculation`: Computed from inventory levels

### Compose Templates
Use `{entity_type}` placeholders to compose values from multiple entities.

**Example:**
```python
compose_template="{equipment} - {symptom}"
# Input: {equipment: "main engine", symptom: "overheating"}
# Output: "main engine - overheating"
```

### Value Mapping
Translate extracted values to canonical form.

**Example:**
```python
value_map={"urgent": "critical", "asap": "critical"}
# Input: "urgent"
# Output: "critical"
```

## Yacht-Scoped Lookups

All lookups enforce RLS (Row-Level Security) by filtering on `yacht_id`.

**Single match:**
```python
result = await lookup_equipment_by_name("main engine", yacht_id, client)
# result.count = 1
# result.value = "uuid-..."
```

**Multiple matches (ambiguous):**
```python
result = await lookup_equipment_by_name("engine", yacht_id, client)
# result.count = 3
# result.options = [
#     {id: "uuid-1", name: "main engine", ...},
#     {id: "uuid-2", name: "auxiliary engine", ...},
#     {id: "uuid-3", name: "emergency engine", ...},
# ]
```

**No matches:**
```python
result = await lookup_equipment_by_name("xyz", yacht_id, client)
# result.count = 0
# result.value = None
```

## Integration with Action Router

The prefill engine is designed to work with the existing `action_router` infrastructure.

**Field metadata in action registry:**
```python
from action_router.registry import ActionDefinition, FieldMetadata

ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/execute",
    prefill_endpoint="/v1/work-orders/prepare",
    field_metadata=[
        FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
        # ... more fields
    ],
)
```

## Testing

See `prefill_examples.py` for example field_metadata configurations.

**Manual testing:**
```python
from common.prefill_engine import build_mutation_preview
from common.prefill_examples import WORK_ORDER_FIELD_METADATA

preview = await build_mutation_preview(
    query_text="create urgent work order for main engine overheating",
    extracted_entities={
        "equipment": "main engine",
        "symptom": "overheating",
        "priority": "urgent",
    },
    field_metadata=WORK_ORDER_FIELD_METADATA,
    yacht_id="abc-123",
    supabase_client=client,
    user_id="user-456",
)

assert preview["ready_to_commit"] == True
assert preview["mutation_preview"]["priority"] == "critical"  # mapped from "urgent"
```

## Next Steps

The prefill engine is now ready to use. To implement a /prepare endpoint:

1. Define field_metadata for your mutation (see `prefill_examples.py`)
2. Create `/prepare` endpoint that calls `build_mutation_preview()`
3. Create `/commit` endpoint that validates and executes the mutation
4. Update action registry with `prefill_endpoint` and `field_metadata`

**Example endpoints to implement:**
- `/v1/work-orders/prepare` + `/v1/work-orders/commit`
- `/v1/faults/prepare` + `/v1/faults/commit`
- `/v1/parts/reorder/prepare` + `/v1/parts/reorder/commit`
- `/v1/equipment/update-status/prepare` + `/v1/equipment/update-status/commit`

## Error Handling

The prefill engine returns warnings instead of errors for missing/ambiguous entities:

```python
preview = await build_mutation_preview(...)

# Check for issues
if preview["warnings"]:
    print("Warnings:", preview["warnings"])
    # ["No match found for equipment_id: 'xyz'"]

if preview["missing_required"]:
    print("Missing fields:", preview["missing_required"])
    # ["equipment_id", "title"]

if preview["dropdown_options"]:
    print("Ambiguous fields:", preview["dropdown_options"])
    # {"equipment_id": [{id: "...", name: "main engine"}, ...]}
```

This allows the frontend to show a form with:
- Pre-filled values (green checkmarks)
- Missing fields (red highlights)
- Ambiguous fields (dropdowns with options)
- Warnings (yellow alerts)
