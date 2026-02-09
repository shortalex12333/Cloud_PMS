# Inventory Item Lens - Complete Implementation Guide

**Status:** Partially Implemented
**Priority:** HIGH (Inventory critical for operations)
**Estimated Effort:** 4-6 hours

---

## Current State

### ✅ Already Implemented
- [x] 2 entity types: `LOCATION`, `STOCK_QUERY`
- [x] Capability: `inventory_by_location`
- [x] Database table: `pms_parts` with stock columns
- [x] Handlers: `InventoryHandlers` with `check_stock_level`, `log_part_usage`
- [x] Actions: check_stock_level, log_part_usage, receive_part, consume_part, transfer_part
- [x] Frontend component: `PartCard.tsx`

### ❌ Missing
- [ ] Additional 7 entity types for common inventory searches
- [ ] Frontend-backend entity type alignment
- [ ] Entity type translation layer
- [ ] Stock status capability
- [ ] Recent usage capability
- [ ] E2E tests for inventory searches

---

## Implementation Plan

### Phase 1: Backend Entity Types (2 hours)

#### File 1: `apps/api/prepare/capability_composer.py`

**Location:** Line 113-137 in `ENTITY_TO_SEARCH_COLUMN` dictionary

**Add:**
```python
# EXISTING (keep these):
"LOCATION": ("inventory_by_location", "location"),
"STOCK_QUERY": ("inventory_by_location", "name"),

# NEW ADDITIONS:
"STOCK_STATUS": ("inventory_by_stock_status", "quantity_on_hand"),
"REORDER_NEEDED": ("inventory_by_stock_status", "quantity_on_hand"),
"CRITICAL_PART": ("inventory_by_location", "is_critical"),
"RECENT_USAGE": ("inventory_by_recent_usage", "used_at"),
"PART_CATEGORY": ("inventory_by_location", "category"),
"LOW_STOCK": ("inventory_by_stock_status", "quantity_on_hand"),
"OUT_OF_STOCK": ("inventory_by_stock_status", "quantity_on_hand"),
```

**Total Entity Types:** 9 (was 2, now 9)

---

#### File 2: `apps/api/execute/table_capabilities.py`

**Location 1:** Update existing `inventory_by_location` capability (line 142)

**Change:**
```python
entity_triggers=["LOCATION", "STOCK_QUERY"],  # OLD
```

**To:**
```python
entity_triggers=[
    "LOCATION",
    "STOCK_QUERY",
    "CRITICAL_PART",   # NEW
    "PART_CATEGORY",    # NEW
],
```

**Location 2:** Add new capability after `email_threads_search` (line 423)

**Add:**
```python
"inventory_by_stock_status": Capability(
    name="inventory_by_stock_status",
    description="Search inventory by stock status (low stock, out of stock, reorder needed)",
    status=CapabilityStatus.ACTIVE,
    entity_triggers=[
        "STOCK_STATUS",
        "REORDER_NEEDED",
        "LOW_STOCK",
        "OUT_OF_STOCK",
    ],
    available_actions=[
        "check_stock_level",
        "create_shopping_list_item",
        "receive_part",
        "adjust_stock_quantity",
    ],
    tables=[
        TableSpec(
            name="pms_parts",
            yacht_id_column="yacht_id",
            primary_key="id",
            searchable_columns=[
                SearchableColumn(
                    name="quantity_on_hand",
                    match_types=[MatchType.NUMERIC_RANGE],
                    description="Current stock quantity",
                    is_primary=True,
                ),
                SearchableColumn(
                    name="minimum_quantity",
                    match_types=[MatchType.NUMERIC_RANGE],
                    description="Minimum stock threshold",
                ),
                SearchableColumn(
                    name="name",
                    match_types=[MatchType.ILIKE],
                    description="Part name for filtering",
                ),
                SearchableColumn(
                    name="category",
                    match_types=[MatchType.EXACT, MatchType.ILIKE],
                    description="Part category",
                ),
            ],
            response_columns=[
                "id", "part_number", "name", "manufacturer",
                "category", "quantity_on_hand", "minimum_quantity",
                "location", "unit", "last_counted_at"
            ],
        ),
    ],
),

"inventory_by_recent_usage": Capability(
    name="inventory_by_recent_usage",
    description="Search parts by recent usage/consumption",
    status=CapabilityStatus.ACTIVE,
    entity_triggers=["RECENT_USAGE"],
    available_actions=[
        "check_stock_level",
        "view_part_details",
        "log_part_usage",
    ],
    tables=[
        TableSpec(
            name="pms_part_usage",
            yacht_id_column="yacht_id",
            primary_key="id",
            searchable_columns=[
                SearchableColumn(
                    name="used_at",
                    match_types=[MatchType.DATE_RANGE],
                    description="Date part was used",
                    is_primary=True,
                ),
                SearchableColumn(
                    name="usage_reason",
                    match_types=[MatchType.EXACT, MatchType.ILIKE],
                    description="Reason for usage",
                ),
            ],
            response_columns=[
                "id", "part_id", "quantity", "used_at", "used_by",
                "usage_reason", "work_order_id", "equipment_id", "notes"
            ],
        ),
    ],
),
```

---

#### File 3: `apps/api/pipeline_v1.py`

**Location:** Add new method after `_execute()` (around line 240)

**Add:**
```python
def _translate_entity_types_for_frontend(self, entities: List[Dict]) -> List[Dict]:
    """
    Translate Lens extraction types to frontend domain types.

    Maps backend normalized types to frontend-expected types.
    Preserves original extraction_type for debugging.
    """
    BACKEND_TO_FRONTEND = {
        # Parts & Inventory
        'PART_NUMBER': 'part',
        'PART_NAME': 'part',
        'MANUFACTURER': 'part',

        # Inventory-specific
        'LOCATION': 'inventory',
        'STOCK_QUERY': 'inventory',
        'STOCK_STATUS': 'inventory',
        'REORDER_NEEDED': 'inventory',
        'CRITICAL_PART': 'inventory',
        'RECENT_USAGE': 'inventory',
        'PART_CATEGORY': 'inventory',
        'LOW_STOCK': 'inventory',
        'OUT_OF_STOCK': 'inventory',

        # Equipment
        'EQUIPMENT_NAME': 'equipment',
        'MODEL_NUMBER': 'equipment',
        'SYSTEM_NAME': 'equipment',
        'COMPONENT_NAME': 'equipment',
        'EQUIPMENT_TYPE': 'equipment',

        # Faults
        'FAULT_CODE': 'fault',
        'SYMPTOM': 'fault',

        # Work Orders
        'WORK_ORDER_ID': 'work_order',
        'WO_NUMBER': 'work_order',

        # Documents
        'DOCUMENT_QUERY': 'document',
        'MANUAL_SEARCH': 'document',
        'PROCEDURE_SEARCH': 'document',
        'EMAIL_SUBJECT': 'email_thread',
        'EMAIL_SEARCH': 'email_thread',
    }

    for entity in entities:
        extraction_type = entity.get('type', '')
        entity['extraction_type'] = extraction_type  # Preserve for debugging
        entity['type'] = BACKEND_TO_FRONTEND.get(extraction_type, extraction_type)
        entity['display_type'] = entity['type']

    return entities
```

**Location:** In `search()` method, after entity extraction (around line 280)

**Add:**
```python
# Stage 2: Translate entity types for frontend compatibility
entities_translated = self._translate_entity_types_for_frontend(
    extracted_result.get('entities', [])
)

# Use entities_translated instead of extracted_result['entities'] in response
```

---

### Phase 2: Frontend Updates (2 hours)

#### File 1: `apps/web/src/components/cards/PartCard.tsx`

**Changes:**
1. Add `entityType` prop
2. Add `data-entity-type` attribute
3. Add `data-entity-id` attribute
4. Add last counted info display
5. Handle `quantity_on_hand` vs `stock_quantity` field names

**Updated interface:**
```typescript
interface PartCardProps {
  part: {
    id: string;
    part_name: string;
    part_number: string;
    stock_quantity: number;  // Or quantity_on_hand from backend
    min_stock_level: number; // Or minimum_quantity from backend
    location: string;
    unit_cost?: number;
    supplier?: string;
    category?: string;
    last_counted_at?: string;  // NEW
    last_counted_by?: string;  // NEW
    unit?: string;             // NEW
  };
  actions?: MicroAction[];
  entityType?: 'part' | 'inventory';  // NEW
}
```

**Updated JSX:**
```tsx
<div
  className="..."
  data-testid={entityType === 'inventory' ? 'inventory-card' : 'part-card'}
  data-entity-type={entityType}  {/* NEW */}
  data-entity-id={part.id}       {/* NEW */}
>
  {/* ... existing content ... */}

  {/* NEW: Last Counted Info */}
  {part.last_counted_at && (
    <div className="text-xs text-muted-foreground mb-2">
      <span className="font-medium">Last counted:</span>{' '}
      {new Date(part.last_counted_at).toLocaleDateString()}{' '}
      {part.last_counted_by && <span>by {part.last_counted_by}</span>}
    </div>
  )}
</div>
```

---

#### File 2: `apps/web/src/app/app/ContextPanel.tsx`

**Location 1:** Add to `entityTypeNames` object (line 27)

**Add:**
```typescript
inventory: 'Inventory',  // NEW
```

**Location 2:** Add to `renderEntityCard()` switch (line 49)

**Add:**
```typescript
case 'part':
case 'inventory':  // NEW: Handle both types
  const partData = {
    id: entityId,
    part_name: (data.name as string) || (data.part_name as string) || 'Part',
    part_number: (data.part_number as string) || '',
    stock_quantity: (data.quantity_on_hand as number) || (data.stock_quantity as number) || 0,
    min_stock_level: (data.minimum_quantity as number) || (data.min_stock_level as number) || 0,
    location: (data.location as string) || 'Unknown',
    unit_cost: data.unit_cost as number | undefined,
    supplier: data.supplier as string | undefined,
    category: data.category as string | undefined,
    last_counted_at: data.last_counted_at as string | undefined,
    last_counted_by: data.last_counted_by as string | undefined,
    unit: data.unit as string | undefined,
  };
  return (
    <div data-testid="context-panel-part-card">
      <PartCard
        part={partData}
        entityType={entityType}  // Pass through
      />
    </div>
  );
```

---

#### File 3: `apps/web/src/types/index.ts`

**Location:** EntityType union (around line 155)

**Change:**
```typescript
export type EntityType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'inventory'  // NEW
  | 'purchase_order'
  | 'supplier'
  | 'document'
  | 'email_thread';
```

---

#### File 4: `apps/web/src/components/spotlight/SpotlightSearch.tsx`

**Location:** `getEntityCategory()` function (line 305)

**Update:**
```typescript
function getEntityCategory(entityType: string): string {
  if (entityType === 'document') return 'manuals';
  if (entityType === 'equipment' || entityType === 'work_order' || entityType === 'fault')
    return 'maintenance';
  if (entityType === 'part' || entityType === 'inventory' || entityType === 'shopping_list')
    return 'inventory';  // NEW: Group inventory types
  if (entityType === 'email_thread') return 'email';
  return 'other';
}
```

---

### Phase 3: Testing (1-2 hours)

#### File: `tests/e2e/inventory/inventory_search_entity_extraction.spec.ts`

**Create new file with tests:**
1. Search by location ("Engine Room")
2. Search by stock status ("low stock parts")
3. Search for out of stock ("out of stock")
4. Search by category ("filters in inventory")
5. Backend-frontend parity validation

---

## Validation Checklist

### Backend Validation
- [ ] Add 7 new entity types to `capability_composer.py`
- [ ] Add 2 new capabilities to `table_capabilities.py`
- [ ] Add translation function to `pipeline_v1.py`
- [ ] Call translation function in search pipeline
- [ ] Run backend tests: `pytest tests/test_pipeline_endpoint.py`
- [ ] Test search API: `curl -X POST /search -d '{"query":"low stock parts"}'`
- [ ] Verify response has `type: "inventory"` not `type: "STOCK_STATUS"`

### Frontend Validation
- [ ] Update PartCard component
- [ ] Update ContextPanel component
- [ ] Update types/index.ts
- [ ] Update SpotlightSearch routing
- [ ] Run E2E tests: `npm run test:e2e -- inventory_search`
- [ ] Verify inventory cards render for "low stock" search
- [ ] Verify data-entity-type="inventory" attribute exists
- [ ] No console errors about unknown entity types

### Full Stack Validation
- [ ] Search "Engine Room" → inventory cards render
- [ ] Search "low stock" → low stock badge shows
- [ ] Search "out of stock" → out of stock indicator shows
- [ ] Backend returns `type: "inventory"`, frontend renders correctly
- [ ] Actions surface based on stock status

---

## Example Search Queries Enabled

After implementation, these queries will work:

| Query | Entity Type Extracted | Results |
|-------|----------------------|---------|
| "Engine Room" | LOCATION → inventory | Parts in Engine Room |
| "low stock parts" | LOW_STOCK → inventory | Parts below minimum |
| "out of stock" | OUT_OF_STOCK → inventory | Parts with 0 quantity |
| "critical parts inventory" | CRITICAL_PART → inventory | Critical parts only |
| "filters in inventory" | PART_CATEGORY → inventory | All filters |
| "recently used parts" | RECENT_USAGE → inventory | Parts used last 30 days |
| "reorder needed" | REORDER_NEEDED → inventory | Parts below minimum |

---

## Deployment Plan

### Step 1: Deploy Backend (no breaking changes)
```bash
git checkout -b feature/inventory-lens-complete
# Make backend changes
git add apps/api/prepare/capability_composer.py
git add apps/api/execute/table_capabilities.py
git add apps/api/pipeline_v1.py
git commit -m "Add complete Inventory Lens entity types and translation"
git push origin feature/inventory-lens-complete
# Create PR, deploy to staging
```

### Step 2: Deploy Frontend (after backend deployed)
```bash
# Make frontend changes
git add apps/web/src/components/cards/PartCard.tsx
git add apps/web/src/app/app/ContextPanel.tsx
git add apps/web/src/types/index.ts
git add apps/web/src/components/spotlight/SpotlightSearch.tsx
git commit -m "Update frontend for Inventory Lens entity types"
git push
# Merge after backend is live
```

### Step 3: E2E Tests
```bash
npm run test:e2e -- inventory_search_entity_extraction
```

---

## Impact Assessment

### Benefits
- ✅ 7 new inventory search capabilities
- ✅ Stock status searches ("low stock", "out of stock")
- ✅ Location-based inventory lookup
- ✅ Recent usage tracking
- ✅ Frontend-backend schema alignment
- ✅ Inventory cards render correctly

### Risks
- ⚠️ None - All changes are additive
- ⚠️ Translation layer preserves backward compatibility

### Performance
- ✅ No performance impact
- ✅ Queries use existing indexes on pms_parts table

---

## Files Changed Summary

**Backend (3 files):**
1. `apps/api/prepare/capability_composer.py` - +7 entity types
2. `apps/api/execute/table_capabilities.py` - +2 capabilities
3. `apps/api/pipeline_v1.py` - +translation function

**Frontend (4 files):**
1. `apps/web/src/components/cards/PartCard.tsx` - +entity type support
2. `apps/web/src/app/app/ContextPanel.tsx` - +inventory case
3. `apps/web/src/types/index.ts` - +inventory type
4. `apps/web/src/components/spotlight/SpotlightSearch.tsx` - +routing

**Tests (1 new file):**
1. `tests/e2e/inventory/inventory_search_entity_extraction.spec.ts` - NEW

**Total:** 8 files (7 changes + 1 new)

---

## Timeline

| Phase | Duration | Owner |
|-------|----------|-------|
| Backend entity types | 2 hours | Backend Team |
| Frontend updates | 2 hours | Frontend Team |
| Testing | 1-2 hours | QA Team |
| **TOTAL** | **4-6 hours** | Both teams |

---

**Status:** ✅ READY TO IMPLEMENT
**Last Updated:** 2026-01-30
**Reviewed By:** Claude Sonnet 4.5
