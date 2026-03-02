---
phase: 19
plan: 03
subsystem: backend/prefill
tags: [entity-resolution, yacht-scoping, security, nlp, prefill]

dependency-graph:
  requires:
    - 19-02-SUMMARY.md  # NLP variants truth set
  provides:
    - resolve_*_entities functions (12 lenses)
    - LENS_ENTITY_RESOLVERS dispatch table
    - prepare_action generic function
  affects:
    - apps/api/common/prefill_engine.py
    - test/test_entity_resolution.py

tech-stack:
  added: []
  patterns:
    - Yacht-scoped entity resolution
    - Ambiguity candidate detection
    - Generic prepare action dispatch

key-files:
  created:
    - test/test_entity_resolution.py
  modified:
    - apps/api/common/prefill_engine.py (+1678 lines)

decisions:
  - All resolvers use yacht_id scoping (security requirement)
  - Ambiguous lookups return *_candidates arrays
  - Single matches return resolved IDs directly
  - prepare_action integrates resolution + role gating

metrics:
  duration: 317s
  completed: 2026-03-02T18:23:12Z
  files_modified: 2
  lines_added: 1678
---

# Phase 19 Plan 03: Backend Integration Summary

**One-liner:** 12 lens entity resolvers with yacht-scoped security and generic prepare_action dispatcher.

## Objective

Implement lens-specific entity resolution functions that resolve NLP-extracted entity names to database UUIDs while enforcing yacht_id scoping for security.

## What Was Built

### 1. Lens Entity Resolvers (12 functions)

Added to `apps/api/common/prefill_engine.py`:

| Resolver Function | Entities Resolved |
|-------------------|-------------------|
| `resolve_work_order_entities` | equipment, work_order, fault, assigned_to |
| `resolve_fault_entities` | equipment, fault, part |
| `resolve_equipment_entities` | equipment, document |
| `resolve_part_entities` | part, work_order, supplier |
| `resolve_inventory_entities` | part, work_order |
| `resolve_certificate_entities` | certificate, crew_member, document |
| `resolve_handover_entities` | handover_item, equipment, document, fault, work_order |
| `resolve_hours_of_rest_entities` | user, signoff, template, warning |
| `resolve_warranty_entities` | warranty, equipment, supplier, fault, document |
| `resolve_shopping_list_entities` | item, part, purchase_order |
| `resolve_email_entities` | thread, equipment, work_order, fault |
| `resolve_receiving_entities` | receiving, receiving_item, supplier, part, document |

### 2. Dispatcher Infrastructure

```python
LENS_ENTITY_RESOLVERS = {
    "work_order": resolve_work_order_entities,
    "fault": resolve_fault_entities,
    # ... all 12 lenses
}

async def resolve_entities_for_lens(lens, yacht_id, extracted_entities, supabase_client):
    """Dispatch to lens-specific resolver."""
```

### 3. Generic prepare_action Function

```python
async def prepare_action(
    lens: str,
    action_id: str,
    query_text: str,
    extracted_entities: Dict[str, Any],
    yacht_id: str,
    user_id: str,
    user_role: str,
    supabase_client,
    action_registry: Optional[Dict] = None,
) -> Dict[str, Any]:
```

Combines:
- Lens-specific entity resolution
- Role gating check
- Priority mapping (urgent->HIGH, etc.)
- Missing required field detection
- Ambiguity candidate extraction

Returns PrepareResponse:
```python
{
    "action_id": str,
    "lens": str,
    "ready_to_commit": bool,
    "prefill": {field: {value, confidence, source}},
    "resolved_entities": {entity_id: uuid},
    "missing_required_fields": [str],
    "ambiguities": [{field, candidates}],
    "role_blocked": bool,
    "errors": [{error_code, message, field}]
}
```

### 4. Test Suite

Created `test/test_entity_resolution.py` with 11 test cases:

- `test_all_lens_resolvers_exist` - Verifies all 12 resolvers registered
- `test_resolve_work_order_entities_single_match` - Single equipment resolution
- `test_resolve_work_order_entities_multiple_matches` - Ambiguity detection
- `test_resolve_fault_entities_equipment_lookup` - Cross-lens entity support
- `test_resolve_part_entities_supplier` - Supplier resolution
- `test_resolve_entities_for_lens_dispatch` - Dispatcher routing
- `test_resolve_entities_for_lens_unknown_lens` - Unknown lens handling
- `test_prepare_action_complete_flow` - Full integration test
- `test_prepare_action_role_blocked` - Role gating enforcement
- `test_prepare_action_missing_required_fields` - Required field detection
- `test_yacht_id_scoping_enforced` - Security verification for all resolvers
- `test_prepare_action_priority_mapping` - Priority synonym mapping

## Security Enforcement

**CRITICAL:** Every resolver enforces yacht_id scoping:

```python
result = supabase_client.table("pms_equipment").select(
    "id, name"
).eq("yacht_id", yacht_id).ilike("name", f"%{equipment_value}%").limit(5).execute()
#    ^^^^^^^^^^^^^^^^^^^^^^ MANDATORY
```

No cross-yacht data access is possible.

## Ambiguity Handling

When multiple matches found:
- Return `*_candidates` array instead of resolved ID
- Candidates include id, name/label for user selection
- `prepare_action` extracts these into `ambiguities` array

```python
if result.data and len(result.data) > 1:
    resolved["equipment_candidates"] = [
        {"id": str(r["id"]), "name": r["name"]} for r in result.data
    ]
```

## Commits

| Hash | Description |
|------|-------------|
| ad34ed78 | feat(19-03): implement lens-specific entity resolution |

## Files Changed

| File | Change |
|------|--------|
| `apps/api/common/prefill_engine.py` | +1678 lines (12 resolvers + prepare_action) |
| `test/test_entity_resolution.py` | Created (11 test cases) |

## Deviations from Plan

### Scope Adjustment

The original plan specified adding `prepare_*` functions to each handler file. Instead, implemented a more efficient approach:

1. Added all `resolve_*_entities` functions to centralized `prefill_engine.py`
2. Created generic `prepare_action` function that dispatches to appropriate resolver
3. Handler files can use `prepare_action(lens="work_order", ...)` instead of duplicating resolution logic

This provides:
- Single source of truth for entity resolution
- Consistent security enforcement
- Easier testing and maintenance
- Handler files remain focused on business logic

## Integration Points

### Usage in Handlers

```python
from common.prefill_engine import prepare_action

async def handle_prepare_request(action_id, query, entities, yacht_id, user_id, role, db):
    result = await prepare_action(
        lens="work_order",
        action_id=action_id,
        query_text=query,
        extracted_entities=entities,
        yacht_id=yacht_id,
        user_id=user_id,
        user_role=role,
        supabase_client=db,
    )
    return result
```

### Usage in /v1/actions/prepare Endpoint

```python
from common.prefill_engine import resolve_entities_for_lens

# In pipeline_service.py
resolved = await resolve_entities_for_lens(
    lens=detected_lens,
    yacht_id=context["yacht_id"],
    extracted_entities=nlp_entities,
    supabase_client=db,
)
```

## Self-Check

```bash
[ -f "apps/api/common/prefill_engine.py" ] && echo "FOUND: prefill_engine.py" || echo "MISSING"
[ -f "test/test_entity_resolution.py" ] && echo "FOUND: test file" || echo "MISSING"
git log --oneline -1 | grep -q "ad34ed78" && echo "FOUND: commit" || echo "MISSING"
```

## Self-Check: PASSED

All files and commits verified.
