# Migration Guide: Existing FieldMetadata → Enhanced FieldMetadata

## Background

The existing `action_router.registry.FieldMetadata` class (lines 43-58 in `registry.py`) is a minimal implementation with only:
- `name`
- `classification`
- `auto_populate_from`
- `lookup_required`
- `description`
- `options`

The enhanced `common.field_metadata.FieldMetadata` adds:
- `compose_template`
- `value_map`
- `default`
- `validator`

## Migration Strategy

### Option 1: Replace Existing FieldMetadata (Recommended)

Replace the existing class in `action_router/registry.py` with an import from `common.field_metadata`:

```python
# apps/api/action_router/registry.py

# OLD (lines 43-58):
# @dataclass
# class FieldMetadata:
#     name: str
#     classification: FieldClassification
#     auto_populate_from: Optional[str] = None
#     lookup_required: bool = False
#     description: Optional[str] = None
#     options: Optional[List[str]] = None

# NEW:
from common.field_metadata import FieldMetadata  # Import enhanced version

# Rest of registry.py remains unchanged
```

**Benefits:**
- Single source of truth for FieldMetadata
- All existing code works (backward compatible)
- Enables new features (compose_template, value_map, default)
- No breaking changes

**Migration Steps:**
1. Comment out existing FieldMetadata class (lines 43-58)
2. Add import: `from common.field_metadata import FieldMetadata`
3. Verify action registry loads: `python3 -c "from action_router.registry import ACTION_REGISTRY"`
4. Run tests: `pytest apps/api/tests/`

### Option 2: Keep Both (Temporary)

Keep both classes during transition period:

```python
# apps/api/action_router/registry.py

from typing import Optional, List
from dataclasses import dataclass

# Legacy FieldMetadata for existing actions
@dataclass
class LegacyFieldMetadata:
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None
    lookup_required: bool = False
    description: Optional[str] = None
    options: Optional[List[str]] = None

# Enhanced FieldMetadata for new actions
from common.field_metadata import FieldMetadata as EnhancedFieldMetadata

# Alias for backward compatibility
FieldMetadata = LegacyFieldMetadata
```

**Benefits:**
- Zero risk during migration
- Gradual migration of actions
- Clear separation of old vs new

**Drawbacks:**
- Temporary code duplication
- Need to migrate eventually

### Option 3: Extend Existing Class

Extend the existing class with new properties:

```python
# apps/api/action_router/registry.py

@dataclass
class FieldMetadata:
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None
    lookup_required: bool = False
    description: Optional[str] = None
    options: Optional[List[str]] = None
    # NEW PROPERTIES:
    compose_template: Optional[str] = None
    value_map: Optional[Dict[str, str]] = None
    default: Optional[Any] = None
    validator: Optional[str] = None
```

**Benefits:**
- Minimal changes
- All code in one place

**Drawbacks:**
- No validation logic (from `__post_init__`)
- No LookupResult dataclass
- Need to duplicate logic from `common.field_metadata`

## Recommended Migration Path

**Phase 1: Import Enhancement (Day 1)**
```python
# action_router/registry.py
from common.field_metadata import FieldMetadata
```

**Phase 2: Update Action Registry (Day 2-7)**
Enhance field_metadata for existing actions:

```python
# Before:
field_metadata=[
    FieldMetadata(
        name="priority",
        classification="OPTIONAL",
    ),
]

# After:
field_metadata=[
    FieldMetadata(
        name="priority",
        classification="OPTIONAL",
        value_map={"urgent": "critical"},  # NEW
        default="medium",                   # NEW
    ),
]
```

**Phase 3: Implement /prepare Endpoints (Week 2+)**
Add `/prepare` endpoints for high-value mutations:
1. Create Work Order
2. Create Fault Report
3. Reorder Part

## Backward Compatibility

The enhanced FieldMetadata is **100% backward compatible**:

```python
# Old-style usage (still works)
FieldMetadata(
    name="equipment_id",
    classification="REQUIRED",
    auto_populate_from="equipment",
    lookup_required=True,
)

# New-style usage (adds features)
FieldMetadata(
    name="title",
    classification="BACKEND_AUTO",
    auto_populate_from="equipment",
    compose_template="{equipment} - {symptom}",  # NEW
)
```

All existing properties work exactly as before. New properties are **optional** and default to `None`.

## Testing Migration

```python
# Test that existing actions still work
from action_router.registry import ACTION_REGISTRY

for action_id, action in ACTION_REGISTRY.items():
    for field in action.field_metadata:
        assert hasattr(field, 'name')
        assert hasattr(field, 'classification')
        # NEW properties should exist but may be None
        assert hasattr(field, 'compose_template')
        assert hasattr(field, 'value_map')
        assert hasattr(field, 'default')
        print(f"✓ {action_id}.{field.name}")
```

## Common Enhancements

### 1. Add Value Mapping

```python
# Before:
FieldMetadata(name="priority", classification="OPTIONAL")

# After:
FieldMetadata(
    name="priority",
    classification="OPTIONAL",
    value_map={"urgent": "critical", "asap": "critical"},
    default="medium",
)
```

### 2. Add Compose Template

```python
# Before:
FieldMetadata(name="title", classification="REQUIRED")

# After:
FieldMetadata(
    name="title",
    classification="BACKEND_AUTO",  # Changed from REQUIRED
    compose_template="{equipment} - {symptom}",
    auto_populate_from="equipment",
)
```

### 3. Add Default Values

```python
# Before:
FieldMetadata(name="wo_type", classification="OPTIONAL")

# After:
FieldMetadata(
    name="wo_type",
    classification="OPTIONAL",
    default="corrective",
    options=["corrective", "preventive", "predictive", "emergency"],
)
```

## Validation After Migration

After replacing FieldMetadata, run validation:

```bash
# Check syntax
python3 -m py_compile apps/api/action_router/registry.py

# Check imports
python3 -c "from action_router.registry import ACTION_REGISTRY, FieldMetadata"

# Run tests
pytest apps/api/tests/ -v

# Check action registry loads
python3 apps/api/action_router/registry.py
```

## Rollback Plan

If issues arise, rollback is simple:

```python
# Restore original FieldMetadata
@dataclass
class FieldMetadata:
    name: str
    classification: FieldClassification
    auto_populate_from: Optional[str] = None
    lookup_required: bool = False
    description: Optional[str] = None
    options: Optional[List[str]] = None
```

No data loss - new properties are purely additive.

## Example: Migrating "create_work_order" Action

```python
# BEFORE (action_router/registry.py)
"create_work_order": ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/execute",
    field_metadata=[
        FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
        FieldMetadata(
            name="priority",
            classification="OPTIONAL",
        ),
    ],
)

# AFTER (with enhancements)
"create_work_order": ActionDefinition(
    action_id="create_work_order",
    label="Create Work Order",
    endpoint="/v1/work-orders/execute",
    prefill_endpoint="/v1/work-orders/prepare",  # NEW
    field_metadata=[
        FieldMetadata(
            name="equipment_id",
            classification="REQUIRED",
            auto_populate_from="equipment",
            lookup_required=True,
        ),
        FieldMetadata(
            name="title",
            classification="BACKEND_AUTO",
            compose_template="{equipment} - {symptom}",  # NEW
            auto_populate_from="equipment",
        ),
        FieldMetadata(
            name="priority",
            classification="OPTIONAL",
            value_map={"urgent": "critical"},  # NEW
            default="medium",                   # NEW
            options=["low", "medium", "high", "critical"],
        ),
        FieldMetadata(
            name="yacht_id",
            classification="CONTEXT",  # NEW
        ),
        FieldMetadata(
            name="created_by",
            classification="CONTEXT",  # NEW
        ),
    ],
)
```

## Timeline

**Day 1:**
- [ ] Replace FieldMetadata import in registry.py
- [ ] Run validation tests
- [ ] Verify action registry loads

**Week 1:**
- [ ] Enhance field_metadata for 5 high-priority actions
- [ ] Implement /prepare endpoint for create_work_order
- [ ] Test with real data

**Week 2:**
- [ ] Implement /prepare endpoints for 3 more mutations
- [ ] Migrate all actions to enhanced field_metadata
- [ ] Update frontend to use /prepare → /commit flow

**Week 3+:**
- [ ] Monitor performance and errors
- [ ] Add new features (fuzzy matching, caching)
- [ ] Optimize lookup queries

## Support

If issues arise during migration:
1. Check validation errors in FieldMetadata.__post_init__
2. Review INTEGRATION_EXAMPLE.md for patterns
3. Test with unit tests: `pytest apps/api/common/test_prefill_engine.py`
4. Review existing examples in prefill_examples.py

## Summary

**Recommended approach:**
- **Option 1** (Replace): Best for clean codebase
- **Phase 1**: Import enhancement (Day 1)
- **Phase 2**: Gradual enhancement of actions (Week 1-2)
- **Phase 3**: Implement /prepare endpoints (Week 2+)

**Risk:** Minimal - fully backward compatible

**Effort:** 1-2 hours for migration, 1-2 days per /prepare endpoint

**Benefits:**
- Auto-population of mutation fields
- Reduced user errors
- Better UX (pre-filled forms)
- Consistent mutation handling
