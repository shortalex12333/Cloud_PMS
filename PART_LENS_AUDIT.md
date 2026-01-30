# Part Lens - Pre-Migration Audit

**Date**: 2026-01-30
**Scope**: Part Lens only (template for other engineers)
**Status**: 🔵 PHASE 0 - Conflict Detection

---

## Part Lens Entity Inventory

### Current Entity Mappings (capability_composer.py)

From `ENTITY_TO_SEARCH_COLUMN` dictionary:

```python
# Part-related entities
"PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
"PART_NAME": ("part_by_part_number_or_name", "name"),
"MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),
"LOCATION": ("inventory_by_location", "location"),           # AMBIGUOUS!
"STOCK_QUERY": ("inventory_by_location", "name"),
```

**Total Part Lens Entities**: 5

---

## Conflicts Detected

### 1. Ambiguous Entity Name: `LOCATION`

**Problem**: "LOCATION" is too generic

**Used By**:
- Part Lens: Inventory storage location
- Equipment Lens: Equipment installation location
- Crew Lens: Crew member location/station

**Resolution**: Rename to be lens-specific

**Before**:
```python
"LOCATION": ("inventory_by_location", "location")
```

**After**:
```python
"PART_STORAGE_LOCATION": ("inventory_by_storage_location", "storage_location")
```

**Impact**:
- Update entity extraction patterns
- Update capability method name
- Update tests
- Update frontend if it references "LOCATION"

---

### 2. Ambiguous Entity Name: `STOCK_QUERY`

**Problem**: "STOCK_QUERY" is too vague - what does "name" search for in inventory context?

**Resolution**: Rename to clarify purpose

**Before**:
```python
"STOCK_QUERY": ("inventory_by_location", "name")
```

**After**:
```python
"INVENTORY_BY_PART_NAME": ("inventory_by_part_name", "part_name")
```

**Rationale**: Searching inventory by part name, not by query

---

### 3. Capability Name Mismatch

**Current Capability Names**:
- `part_by_part_number_or_name` - Good (clear)
- `inventory_by_location` - Should be `inventory_by_storage_location` (align with renamed entity)

---

## Part Lens Tables (from part_lens_v2_FINAL.md)

### Primary Tables
1. **pms_parts**: Core part data (part_number, name, manufacturer, category)
2. **pms_inventory_stock**: Stock levels by storage location
3. **pms_inventory_transactions**: Receive, consume, transfer, adjust history
4. **pms_part_usage**: Part-to-equipment relationships
5. **pms_shopping_list_items**: Procurement requests

### Missing Capabilities

**Currently Mapped**:
- ✅ Parts search by part_number/name/manufacturer
- ✅ Inventory search by storage location

**Missing (Need to Add)**:
- ❌ Shopping list search by part
- ❌ Transaction history search
- ❌ Part usage search (which equipment uses this part)
- ❌ Parts by category/subcategory
- ❌ Low stock alerts (on_hand below min_quantity)

---

## Entity Extraction Patterns (module_b_entity_extractor.py)

### Part-Related Entity Types

From `HARD_ENTITY_TYPES`:
- ✅ `part` - Specific replacement components
- ✅ `equipment` - Known equipment types (overlaps with Equipment Lens!)
- ✅ `brand` - Manufacturers (Part Lens uses for manufacturer search)
- ✅ `model` - Product identifiers (overlaps with Equipment Lens!)

From `SOFT_ENTITY_TYPES`:
- ⚠️ `system` - Broad category (not Part Lens specific)
- ⚠️ `location` - Spatial reference (overlaps - needs namespacing!)

### Extraction Gaps

**Extracted but Not Mapped**:
- `part` entity type extracted, but no direct mapping (uses PART_NAME instead)
- `brand` entity type extracted, maps to MANUFACTURER (inconsistent naming)

**Resolution**: Align entity extraction types with capability mappings

**Proposed Alignment**:
```python
# In part_capabilities.py
"PART": ("part_by_part_number_or_name", "name"),           # NEW
"PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
"PART_NAME": ("part_by_part_number_or_name", "name"),      # Keep for backward compat
"MANUFACTURER": ("part_by_manufacturer", "manufacturer"),
"PART_BRAND": ("part_by_manufacturer", "manufacturer"),    # Alias for 'brand' entity type
"PART_STORAGE_LOCATION": ("inventory_by_storage_location", "storage_location"),
"PART_CATEGORY": ("part_by_category", "category"),         # NEW
"PART_SUBCATEGORY": ("part_by_category", "subcategory"),   # NEW
```

---

## Intent Taxonomy (intent_parser.py)

### Part Lens Related Intents

From `control_inventory` category:
- ✅ `view_part_stock` - "How many oil filters do we have?"
- ✅ `add_part` - "Add a new part to inventory"
- ✅ `order_part` - "Order 2 MTU fuel filters"
- ✅ `view_part_location` - "Where is the impeller stored?"
- ✅ `view_part_usage` - "How many have we used?"
- ✅ `log_part_usage` - "Log that I used 2 filters"
- ✅ `edit_part_quantity` - "Update stock to 5"
- ✅ `scan_part_barcode` - "Scan this barcode"
- ✅ `view_linked_equipment` - "What equipment uses this part?"

**Total**: 9 intents

### Intent-to-Action Mapping

Check if all intents have corresponding actions in action router:

| Intent | Action in Registry | Status |
|--------|-------------------|--------|
| view_part_stock | view_part_details | ✅ Mapped |
| add_part | create_part | ✅ Mapped |
| order_part | add_to_shopping_list | ✅ Mapped |
| view_part_location | view_part_details | ✅ Mapped |
| view_part_usage | view_part_details | ✅ Mapped |
| log_part_usage | consume_part | ✅ Mapped |
| edit_part_quantity | adjust_stock_quantity | ✅ Mapped |
| scan_part_barcode | - | ❌ Missing action! |
| view_linked_equipment | view_part_details | ✅ Mapped |

**Gap Identified**: `scan_part_barcode` intent has no action in registry

**Resolution**: Either:
- Add `scan_part_barcode` action to registry
- Remove intent (barcode scanning may be future feature)

---

## Query Intents (graphrag_query.py)

### Part Lens Query Intent

```python
class QueryIntent(str, Enum):
    FIND_PART = "find_part"
    # ... others
```

**Keywords that trigger FIND_PART**:
```python
"find_part": QueryIntent.FIND_PART,
"check_stock": QueryIntent.FIND_PART,
"order_parts": QueryIntent.FIND_PART,
```

**Currently**: Intent-based search is SILOED (only searches pms_parts)

**Issue**: If intent = FIND_PART → only searches pms_parts table

**Missing Comprehensive Search**: Should also search:
- pms_inventory_stock (for stock levels)
- pms_shopping_list_items (for pending orders)
- pms_part_usage (for equipment associations)

---

## Action Registry (action_router/registry.py)

### Part Lens Actions

From registry:

| Action ID | Variant | Allowed Roles | Status |
|-----------|---------|---------------|--------|
| view_part_details | READ | all | ✅ Active |
| create_part | MUTATE | chief_engineer+ | ✅ Active |
| receive_part | MUTATE | chief_engineer+ | ✅ Active |
| consume_part | MUTATE | chief_engineer+ | ✅ Active |
| transfer_part | MUTATE | chief_engineer+ | ✅ Active |
| adjust_stock_quantity | SIGNED | captain, manager | ✅ Active |
| write_off_part | SIGNED | captain, manager | ✅ Active |
| add_to_shopping_list | MUTATE | chief_engineer+ | ✅ Active |
| generate_part_labels | READ | all | ✅ Active |
| request_label_output | MUTATE | chief_engineer+ | ✅ Active |

**Total**: 10 actions

### Stock-Based Action Filtering

**Current Logic** (from part_routes.py lines 335-368):

```python
is_out_of_stock = stock_info["on_hand"] == 0

# Filter actions based on stock state
for action in get_actions_for_domain("parts", role):
    if is_out_of_stock and action.action_id in ["consume_part", "transfer_part", "write_off_part"]:
        continue  # Can't consume/transfer/write-off if no stock
```

**This logic belongs in Microactions module!**

---

## Proposed Part Lens Structure

### 1. Entity Mappings (part_capabilities.py)

```python
def get_entity_mappings(self) -> List[CapabilityMapping]:
    return [
        # Core part search
        CapabilityMapping(
            entity_type="PART_NUMBER",
            capability_name="part_by_part_number_or_name",
            table_name="pms_parts",
            search_column="part_number",
            result_type="part",
            priority=3,  # High priority for exact part numbers
        ),
        CapabilityMapping(
            entity_type="PART_NAME",
            capability_name="part_by_part_number_or_name",
            table_name="pms_parts",
            search_column="name",
            result_type="part",
            priority=2,
        ),
        CapabilityMapping(
            entity_type="PART",  # Align with extraction
            capability_name="part_by_part_number_or_name",
            table_name="pms_parts",
            search_column="name",
            result_type="part",
            priority=2,
        ),

        # Manufacturer search
        CapabilityMapping(
            entity_type="MANUFACTURER",
            capability_name="part_by_manufacturer",
            table_name="pms_parts",
            search_column="manufacturer",
            result_type="part",
            priority=1,
        ),
        CapabilityMapping(
            entity_type="PART_BRAND",  # Alias for 'brand' entity type
            capability_name="part_by_manufacturer",
            table_name="pms_parts",
            search_column="manufacturer",
            result_type="part",
            priority=1,
        ),

        # Inventory search
        CapabilityMapping(
            entity_type="PART_STORAGE_LOCATION",  # Renamed from LOCATION
            capability_name="inventory_by_storage_location",
            table_name="pms_inventory_stock",
            search_column="storage_location",
            result_type="inventory_stock",
            priority=1,
        ),

        # Category search (NEW)
        CapabilityMapping(
            entity_type="PART_CATEGORY",
            capability_name="part_by_category",
            table_name="pms_parts",
            search_column="category",
            result_type="part",
            priority=1,
        ),
        CapabilityMapping(
            entity_type="PART_SUBCATEGORY",
            capability_name="part_by_category",
            table_name="pms_parts",
            search_column="subcategory",
            result_type="part",
            priority=1,
        ),

        # Shopping list search (NEW)
        CapabilityMapping(
            entity_type="SHOPPING_LIST_ITEM",
            capability_name="shopping_list_by_part",
            table_name="pms_shopping_list_items",
            search_column="part_name",
            result_type="shopping_list_item",
            priority=1,
        ),

        # Part usage search (NEW)
        CapabilityMapping(
            entity_type="PART_EQUIPMENT_USAGE",
            capability_name="part_usage_by_equipment",
            table_name="pms_part_usage",
            search_column="equipment_name",
            result_type="part_usage",
            priority=1,
        ),
    ]
```

### 2. Capabilities to Implement

**Existing (Migrate)**:
- ✅ `part_by_part_number_or_name`
- ✅ `part_by_manufacturer`
- ✅ `inventory_by_storage_location` (renamed from inventory_by_location)

**New**:
- ❌ `part_by_category`
- ❌ `shopping_list_by_part`
- ❌ `part_usage_by_equipment`
- ❌ `part_transactions_history`
- ❌ `parts_low_stock`

### 3. Microactions to Implement

**Stock-Based Filtering**:
```python
if on_hand == 0:
    # Hide: consume_part, transfer_part, write_off_part
if on_hand <= min_quantity:
    # Boost priority: add_to_shopping_list
```

**Role-Based Filtering**:
```python
if role not in ["captain", "manager"]:
    # Hide: adjust_stock_quantity, write_off_part (SIGNED actions)
```

**Intent-Based Prioritization**:
```python
if query_intent == "receive_part":
    # Boost priority: receive_part action
    # Show prefill modal automatically
```

---

## Migration Checklist

### Phase 0: Audit ✅
- [x] Identify Part Lens entities
- [x] Detect ambiguous names (LOCATION, STOCK_QUERY)
- [x] Map intents to actions
- [x] Identify missing capabilities
- [x] Document conflicts

### Phase 0: Conflict Resolution
- [ ] Rename `LOCATION` → `PART_STORAGE_LOCATION`
- [ ] Rename `STOCK_QUERY` → `INVENTORY_BY_PART_NAME`
- [ ] Decide on `scan_part_barcode` intent (keep or remove)
- [ ] Add missing entity extraction patterns
- [ ] Update entity extraction to align with capability names

### Phase 1: Base Infrastructure
- [ ] Create `apps/api/prepare/base_capability.py`
- [ ] Create `apps/api/prepare/capability_registry.py`
- [ ] Create `apps/api/microactions/base_microaction.py`
- [ ] Create `apps/api/microactions/microaction_registry.py`
- [ ] Add startup validation
- [ ] Test empty registries

### Phase 2: Part Lens Implementation
- [ ] Create `apps/api/prepare/capabilities/part_capabilities.py`
  - [ ] Migrate existing capabilities
  - [ ] Add new capabilities (category, shopping list, usage)
  - [ ] Add validation
- [ ] Create `apps/api/microactions/lens_microactions/part_microactions.py`
  - [ ] Implement stock-based filtering
  - [ ] Implement role-based filtering
  - [ ] Implement intent prioritization
  - [ ] Implement prefill data logic
- [ ] Update `apps/api/graphrag_query.py`
  - [ ] Integrate capability registry
  - [ ] Integrate microaction registry
  - [ ] Add comprehensive search for FIND_PART intent

### Phase 3: Testing
- [ ] Unit tests for `part_capabilities.py`
- [ ] Unit tests for `part_microactions.py`
- [ ] Integration tests for registry auto-discovery
- [ ] E2E tests (existing tests should still pass)
- [ ] Test stock-based filtering (on_hand = 0 scenarios)
- [ ] Test role-based filtering (crew, chief_engineer, captain)
- [ ] Test intent prioritization ("receive engine oil filter")

### Phase 4: Documentation
- [ ] Document Part Lens implementation as template
- [ ] Create "How to Add Your Lens" guide for other engineers
- [ ] Update entity extraction patterns documentation
- [ ] Update API documentation with new endpoints

---

## Summary

**Conflicts Found**: 2
- Ambiguous entity name: `LOCATION`
- Ambiguous entity name: `STOCK_QUERY`

**Missing Capabilities**: 5
- `part_by_category`
- `shopping_list_by_part`
- `part_usage_by_equipment`
- `part_transactions_history`
- `parts_low_stock`

**Extraction Gaps**: 2
- `part` entity type not mapped directly
- `brand` entity type inconsistently named

**Ready to Proceed**: After renaming conflicts

---

**Next Step**: Resolve conflicts, then implement Phase 1 base infrastructure.
