# Prefill Engine Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CELESTE TWO-PHASE MUTATION SYSTEM                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: /prepare (PREVIEW)                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. User Query (NLP)                                                     │
│     "create urgent work order for main engine overheating"              │
│                                                                          │
│  2. Entity Extraction (extraction/entity_extractor.py)                  │
│     → {equipment: "main engine", symptom: "overheating", priority: "urgent"} │
│                                                                          │
│  3. Prefill Engine (common/prefill_engine.py)                           │
│     ┌─────────────────────────────────────────────────────────┐        │
│     │ For each field in field_metadata:                       │        │
│     │   ✓ Extract entity value (extract_entity_value)         │        │
│     │   ✓ Apply compose template (apply_compose_template)     │        │
│     │   ✓ Apply value mapping (apply_value_map)               │        │
│     │   ✓ Yacht-scoped lookup (lookup_entity)                 │        │
│     │   ✓ Generate backend values (generate_backend_auto_value)│       │
│     └─────────────────────────────────────────────────────────┘        │
│                                                                          │
│  4. Mutation Preview                                                     │
│     {                                                                    │
│       mutation_preview: {                                                │
│         equipment_id: "uuid-...",                                        │
│         title: "main engine - overheating",                              │
│         priority: "critical",  // mapped from "urgent"                   │
│         yacht_id: "abc-123",                                             │
│       },                                                                 │
│       missing_required: [],                                              │
│       warnings: [],                                                      │
│       dropdown_options: {},                                              │
│       ready_to_commit: true                                              │
│     }                                                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

                                    ▼
                            (User reviews preview)
                                    ▼

┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: /commit (EXECUTE)                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Validate Preview (validate_mutation_preview)                        │
│     - Check all REQUIRED fields present                                 │
│     - Validate enum options                                              │
│     - Verify UUIDs exist in DB                                           │
│                                                                          │
│  2. Execute Mutation (Supabase INSERT/UPDATE)                           │
│     - Apply RLS (yacht_id filtering)                                     │
│     - Insert into pms_work_orders table                                  │
│     - Return created record                                              │
│                                                                          │
│  3. Post-Mutation Actions                                                │
│     - Log to event_logs                                                  │
│     - Send notifications                                                 │
│     - Update cache                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

```
apps/api/common/
├── field_metadata.py       # FieldMetadata schema definition
│   └── FieldMetadata       # Dataclass with:
│       ├── classification  # REQUIRED, OPTIONAL, BACKEND_AUTO, CONTEXT
│       ├── auto_populate_from  # Entity type to extract
│       ├── compose_template    # Template for composing values
│       ├── lookup_required     # Whether to resolve to UUID
│       ├── value_map          # Dict for value translation
│       └── default            # Default value
│
├── lookup_functions.py     # Yacht-scoped entity lookups
│   ├── lookup_equipment_by_name()   # Equipment name → UUID
│   ├── lookup_fault_by_symptom()    # Symptom → fault UUID
│   ├── lookup_part_by_name()        # Part name → UUID
│   ├── lookup_work_order_by_number() # WO number → UUID
│   └── lookup_entity()              # Generic router
│
├── prefill_engine.py       # Core mutation preview builder
│   ├── build_mutation_preview()     # Main entry point
│   ├── extract_entity_value()       # Extract entity from NLP results
│   ├── apply_compose_template()     # Compose values from entities
│   ├── apply_value_map()            # Translate values
│   ├── generate_backend_auto_value() # Generate UUIDs, timestamps
│   └── validate_mutation_preview()  # Validate before commit
│
├── prefill_examples.py     # Real-world field_metadata examples
│   ├── WORK_ORDER_FIELD_METADATA
│   ├── FAULT_REPORT_FIELD_METADATA
│   ├── REORDER_PART_FIELD_METADATA
│   ├── UPDATE_EQUIPMENT_STATUS_FIELD_METADATA
│   └── ASSIGN_WORK_ORDER_FIELD_METADATA
│
└── test_prefill_engine.py  # Unit tests
```

## Data Flow

### 1. Field Metadata Definition (Design Time)

```python
# Define once per mutation type
WORK_ORDER_FIELD_METADATA = {
    "equipment_id": FieldMetadata(
        name="equipment_id",
        classification="REQUIRED",
        auto_populate_from="equipment",  # Extract from EQUIPMENT entity
        lookup_required=True,             # Resolve to UUID via DB lookup
    ),
    "title": FieldMetadata(
        name="title",
        classification="BACKEND_AUTO",
        compose_template="{equipment} - {symptom}",  # Compose from entities
    ),
    "priority": FieldMetadata(
        name="priority",
        classification="OPTIONAL",
        value_map={"urgent": "critical"},  # Translate values
        default="medium",                   # Default if not extracted
    ),
}
```

### 2. Entity Extraction (Runtime - Phase 1)

```python
# NLP extracts entities from user query
query = "create urgent work order for main engine overheating"

entities = extract_entities(query)
# {
#   equipment: "main engine",
#   symptom: "overheating",
#   priority: "urgent"
# }
```

### 3. Prefill Processing (Runtime - Phase 1)

```python
preview = await build_mutation_preview(
    query_text=query,
    extracted_entities=entities,
    field_metadata=WORK_ORDER_FIELD_METADATA,
    yacht_id="abc-123",
    supabase_client=client,
)

# Preview result:
# {
#   mutation_preview: {
#     equipment_id: "uuid-...",  // Looked up from "main engine"
#     title: "main engine - overheating",  // Composed
#     priority: "critical",  // Mapped from "urgent"
#     yacht_id: "abc-123",  // From context
#   },
#   missing_required: [],
#   warnings: [],
#   dropdown_options: {},
#   ready_to_commit: true
# }
```

### 4. Lookup Resolution (Runtime - Phase 1)

```python
# When lookup_required=True, engine queries DB:
result = await lookup_equipment_by_name("main engine", "yacht-123", client)

# Scenario A: Single match (auto-resolve)
# result.count = 1
# result.value = "equipment-uuid-123"
# → mutation_preview["equipment_id"] = "equipment-uuid-123"

# Scenario B: Multiple matches (dropdown)
# result.count = 3
# result.options = [{id: "...", name: "main engine"}, ...]
# → dropdown_options["equipment_id"] = [...]

# Scenario C: No matches (warning)
# result.count = 0
# → warnings.append("No match found for equipment_id: 'main engine'")
# → missing_required.append("equipment_id")
```

### 5. Value Transformation (Runtime - Phase 1)

```python
# compose_template: "{equipment} - {symptom}"
title = apply_compose_template(
    "{equipment} - {symptom}",
    {"equipment": "main engine", "symptom": "overheating"}
)
# → "main engine - overheating"

# value_map: {"urgent": "critical"}
priority = apply_value_map("urgent", {"urgent": "critical"})
# → "critical"
```

### 6. Commit Validation (Runtime - Phase 2)

```python
# Validate preview before commit
validation = validate_mutation_preview(
    mutation_preview=preview["mutation_preview"],
    field_metadata=WORK_ORDER_FIELD_METADATA
)

if validation["valid"]:
    # Execute mutation
    result = supabase.table("pms_work_orders").insert(
        preview["mutation_preview"]
    ).execute()
else:
    # Return errors to user
    return {"errors": validation["errors"]}
```

## Lookup Cache Strategy

The prefill engine caches lookups within a single preview build to avoid redundant queries:

```python
lookup_cache = {}

# First lookup for "main engine"
cache_key = "equipment:main engine"
if cache_key in lookup_cache:
    result = lookup_cache[cache_key]
else:
    result = await lookup_equipment_by_name("main engine", yacht_id, client)
    lookup_cache[cache_key] = result

# Subsequent lookups for "main engine" use cached result
# (e.g., for equipment_id and title fields)
```

## RLS Enforcement

All lookups enforce Row-Level Security (RLS) by filtering on `yacht_id`:

```python
# Equipment lookup (RLS-enforced)
response = supabase.table("pms_equipment") \
    .select("id, name, category, location") \
    .eq("yacht_id", yacht_id)  # RLS enforcement
    .ilike("name", f"%{name}%") \
    .execute()

# This ensures:
# 1. User can only see equipment from their yacht
# 2. Lookups are isolated per tenant
# 3. No cross-yacht data leakage
```

## Error Handling Strategy

The prefill engine returns **warnings** instead of **errors** to allow partial previews:

```python
# Missing entity → warning + missing_required
if not entity_value:
    warnings.append(f"No match found for {field_name}: '{entity_value}'")
    missing_required.append(field_name)

# Ambiguous entity → warning + dropdown_options
if lookup_result.count > 1:
    warnings.append(f"Ambiguous {field_name}: matched {count} items")
    dropdown_options[field_name] = lookup_result.options

# Lookup failure → warning + missing_required
if not lookup_result.success:
    warnings.append(f"Lookup failed for {field_name}: {error}")
    missing_required.append(field_name)
```

## Integration with Action Router

The prefill engine integrates with the existing action router registry:

```python
# action_router/registry.py
from common.field_metadata import FieldMetadata

ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/execute",
    prefill_endpoint="/v1/work-orders/prepare",  # NEW
    field_metadata=[  # NEW
        FieldMetadata(...),
        FieldMetadata(...),
    ],
)
```

## Performance Considerations

1. **Lookup Caching**: Cache lookups within a single preview build
2. **Parallel Lookups**: Execute multiple lookups concurrently (future optimization)
3. **Timeout**: Set timeout for DB queries (5s default in supabase client)
4. **Pagination**: Limit lookup results to 10 options for dropdowns

## Security Considerations

1. **RLS Enforcement**: All lookups filter by `yacht_id`
2. **Input Validation**: Sanitize entity values before DB queries
3. **UUID Validation**: Verify UUIDs before commit
4. **Permission Checks**: Enforce role-based access in /commit endpoint

## Future Enhancements

1. **Parallel Lookups**: Execute multiple lookups concurrently
2. **Fuzzy Matching**: Use fuzzy string matching for entity resolution
3. **Learning**: Track user corrections to improve entity extraction
4. **Caching**: Cache frequently accessed lookups (Redis)
5. **Webhooks**: Notify external systems on mutation events
6. **Audit Trail**: Log all preview/commit actions for compliance
