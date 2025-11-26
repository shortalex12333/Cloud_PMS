# Phase 3 Core Implementation Plan

**Version:** 1.0
**Date:** November 21, 2025
**Status:** PRE-IMPLEMENTATION PLAN
**Scope:** Phase 3 Core (Option B) - Filtering & List Views ONLY

---

## 🎯 Objectives

Build the minimal viable filtering system to enable users to **find and view** data effectively:

1. 4 generic, reusable filter components
2. Dynamic SQL query builder in VIEW workflow
3. 3 complete filtered list pages (Parts, WorkOrders, Faults)
4. Grouping + sorting capabilities
5. Pagination from day 1

**Timeline:** Estimated 2-3 days of focused work

---

## 🚧 Guard Rails (Locked In)

### What We CAN Do
✅ Create NEW files in:
- `/frontend/src/components/filters/`
- `/frontend/src/hooks/useFilters.ts`
- `/frontend/src/app/parts/page.tsx`
- `/frontend/src/app/work-orders/page.tsx`
- `/frontend/src/app/faults/page.tsx`
- `/docs/phase3/`

✅ Modify ONLY:
- `/backend/n8n-workflows/master-view-workflow.json` (add dynamic SQL)

### What We CANNOT Do
❌ Modify any Phase 1/2 existing files
❌ Touch micro-action architecture
❌ Touch handlers or workflow archetypes
❌ Touch card components
❌ Create new micro-actions or card types
❌ Change payload/response formats

### Architecture Constraints
- Must use existing unified pattern: `{ action_name, context, parameters, session }`
- Filters = frontend state → `parameters.filters` only
- No new endpoints
- No new global state systems
- Performance: <400ms, limit=50 rows, debouncing required

---

## 📐 Architecture Design

### High-Level Flow

```
User interacts with filter UI
    ↓
Filter state updates (React state)
    ↓
useFilters() hook builds query params
    ↓
executeAction('view_part_stock', {}, { parameters: { filters: {...} } })
    ↓
Action handler routes to /workflows/view (existing, unchanged)
    ↓
VIEW workflow receives filters in parameters.filters
    ↓
Dynamic SQL builder constructs WHERE clauses
    ↓
Execute query (with LIMIT, OFFSET for pagination)
    ↓
Return { success, card_type: "part_list", cards: [...], pagination: {...} }
    ↓
Frontend renders cards using EXISTING card components
```

**Key Point:** We're NOT changing the action handler or routing. We're just passing `filters` in the `parameters` field that already exists.

---

## 🧩 Component Architecture

### 1. Filter Components (Generic & Reusable)

**Location:** `frontend/src/components/filters/`

#### 1.1 LocationFilter.tsx
```typescript
interface LocationFilterProps {
  options: {
    decks: string[];
    rooms: string[];
    storages: string[];
  };
  value: {
    deck?: string;
    room?: string;
    storage?: string;
  };
  onApply: (location: LocationFilter) => void;
  onClear: () => void;
}

// Entity-agnostic - receives options from parent
export function LocationFilter({ options, value, onApply, onClear }: LocationFilterProps) {
  // Hierarchical dropdowns: Deck → Room → Storage
  // No entity logic inside - just UI
}
```

**Features:**
- Hierarchical dropdown cascade
- Clear button
- Apply button (not auto-apply to avoid excessive API calls)
- Shows current selection as badge

#### 1.2 StatusFilter.tsx
```typescript
interface StatusFilterProps {
  options: { value: string; label: string; color?: string }[];
  value: string[];
  multiSelect?: boolean;
  onApply: (statuses: string[]) => void;
  onClear: () => void;
}

// Entity-agnostic status filter
export function StatusFilter({ options, value, multiSelect = true, onApply, onClear }: StatusFilterProps) {
  // Multi-select chips or dropdown
  // No entity-specific logic
}
```

**Features:**
- Multi-select chips (e.g., "pending", "in_progress", "overdue")
- Color-coded badges
- Quick presets (optional prop)

#### 1.3 TimeRangeFilter.tsx
```typescript
interface TimeRangeFilterProps {
  value: { start: string; end: string } | null;
  presets?: { label: string; value: () => { start: Date; end: Date } }[];
  onApply: (range: { start: string; end: string }) => void;
  onClear: () => void;
}

// Generic time range picker
export function TimeRangeFilter({ value, presets, onApply, onClear }: TimeRangeFilterProps) {
  // Preset buttons: Today, This Week, Last 30 Days, Custom
  // Date pickers for custom range
}
```

**Features:**
- Preset buttons for common ranges
- Custom date picker (from/to)
- Handles timezone conversion

#### 1.4 QuantityFilter.tsx
```typescript
interface QuantityFilterProps {
  label: string;
  value: { operator: 'lt' | 'lte' | 'gt' | 'gte' | 'eq' | 'between'; value: number | [number, number] } | null;
  onApply: (filter: QuantityFilter) => void;
  onClear: () => void;
}

// Generic quantity/number filter
export function QuantityFilter({ label, value, onApply, onClear }: QuantityFilterProps) {
  // Operator selector: <, <=, >, >=, =, between
  // Number input(s)
}
```

**Features:**
- Operator dropdown
- Number input(s)
- For stock quantities, prices, hours, etc.

#### 1.5 FilterBar.tsx (Container)
```typescript
interface FilterBarProps {
  activeFilters: Record<string, any>;
  onClearAll: () => void;
  children: React.ReactNode;
}

// Container for all filters + active filter badges
export function FilterBar({ activeFilters, onClearAll, children }: FilterBarProps) {
  return (
    <div className="border rounded-lg p-4 mb-4">
      {/* Active filter badges */}
      <div className="flex gap-2 mb-3">
        {Object.entries(activeFilters).map(([key, value]) => (
          <FilterBadge key={key} label={key} value={value} onRemove={() => clearFilter(key)} />
        ))}
        {Object.keys(activeFilters).length > 0 && (
          <Button variant="ghost" size="sm" onClick={onClearAll}>Clear All</Button>
        )}
      </div>

      {/* Filter controls */}
      <div className="flex gap-2 flex-wrap">
        {children}
      </div>
    </div>
  );
}
```

---

### 2. useFilters Hook

**Location:** `frontend/src/hooks/useFilters.ts`

```typescript
interface FilterState {
  location?: { deck?: string; room?: string; storage?: string };
  status?: string[];
  timeRange?: { start: string; end: string };
  quantity?: { operator: string; value: number | [number, number] };
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export function useFilters(entityType: 'part' | 'work_order' | 'fault' | 'equipment' | 'purchase') {
  const [filters, setFilters] = useState<FilterState>({
    page: 1,
    limit: 50,
    sortBy: 'created_at',
    sortOrder: 'desc'
  });

  // Apply single filter
  const applyFilter = (filterType: keyof FilterState, value: any) => {
    setFilters(prev => ({
      ...prev,
      [filterType]: value,
      page: 1 // Reset to page 1 when filter changes
    }));
  };

  // Clear single filter
  const clearFilter = (filterType: keyof FilterState) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      delete newFilters[filterType];
      return newFilters;
    });
  };

  // Clear all filters
  const clearAllFilters = () => {
    setFilters({
      page: 1,
      limit: 50,
      sortBy: 'created_at',
      sortOrder: 'desc'
    });
  };

  // Build API parameters (matches existing unified pattern)
  const buildQueryParams = () => {
    return {
      filters: {
        location: filters.location,
        status: filters.status,
        time_range: filters.timeRange,
        quantity: filters.quantity
      },
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
      limit: filters.limit,
      offset: (filters.page! - 1) * filters.limit!
    };
  };

  return {
    filters,
    applyFilter,
    clearFilter,
    clearAllFilters,
    buildQueryParams,
    setPage: (page: number) => setFilters(prev => ({ ...prev, page })),
    setSort: (sortBy: string, sortOrder: 'asc' | 'desc') =>
      setFilters(prev => ({ ...prev, sortBy, sortOrder, page: 1 }))
  };
}
```

**Key Features:**
- Pure React state (no global state)
- Resets to page 1 when filters change
- Builds parameters in existing unified format
- Entity-type aware for default sorting

---

### 3. List Page Structure

**Location:** `frontend/src/app/parts/page.tsx` (example)

```typescript
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useActionHandler } from '@/hooks/useActionHandler';
import { useFilters } from '@/hooks/useFilters';
import { FilterBar } from '@/components/filters/FilterBar';
import { LocationFilter } from '@/components/filters/LocationFilter';
import { StatusFilter } from '@/components/filters/StatusFilter';
import { QuantityFilter } from '@/components/filters/QuantityFilter';
import { PartCard } from '@/components/cards/PartCard'; // EXISTING component - not modified
import { Pagination } from '@/components/ui/pagination';
import { SortControls } from '@/components/ui/sort-controls';

export default function PartsListPage() {
  const { executeAction } = useActionHandler();
  const { filters, applyFilter, clearFilter, clearAllFilters, buildQueryParams, setPage, setSort } = useFilters('part');

  // Fetch parts with filters
  const { data, isLoading, error } = useQuery({
    queryKey: ['parts', filters],
    queryFn: () => executeAction('view_part_stock', {}, {
      parameters: buildQueryParams()
    }),
    keepPreviousData: true // For smooth pagination
  });

  return (
    <div className="container mx-auto py-6">
      <h1 className="text-2xl font-bold mb-6">Parts Inventory</h1>

      {/* Filter Bar */}
      <FilterBar activeFilters={filters} onClearAll={clearAllFilters}>
        <LocationFilter
          options={{
            decks: ['Deck 1', 'Deck 2', 'Deck 3'],
            rooms: ['Engine Room', 'Galley', 'Storage'],
            storages: ['Locker 1', 'Box 3', 'Cabinet A']
          }}
          value={filters.location}
          onApply={(loc) => applyFilter('location', loc)}
          onClear={() => clearFilter('location')}
        />

        <StatusFilter
          options={[
            { value: 'in_stock', label: 'In Stock', color: 'green' },
            { value: 'low_stock', label: 'Low Stock', color: 'yellow' },
            { value: 'out_of_stock', label: 'Out of Stock', color: 'red' }
          ]}
          value={filters.status || []}
          onApply={(status) => applyFilter('status', status)}
          onClear={() => clearFilter('status')}
        />

        <QuantityFilter
          label="Stock Level"
          value={filters.quantity}
          onApply={(qty) => applyFilter('quantity', qty)}
          onClear={() => clearFilter('quantity')}
        />
      </FilterBar>

      {/* Sort Controls */}
      <SortControls
        sortBy={filters.sortBy}
        sortOrder={filters.sortOrder}
        options={[
          { value: 'part_name', label: 'Name' },
          { value: 'stock_quantity', label: 'Stock Level' },
          { value: 'created_at', label: 'Date Added' }
        ]}
        onSort={setSort}
      />

      {/* Results */}
      {isLoading && <div>Loading...</div>}
      {error && <div>Error loading parts</div>}

      {data?.success && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {data.cards?.map((part) => (
              <PartCard key={part.id} part={part} actions={data.micro_actions} />
            ))}
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={filters.page!}
            totalPages={Math.ceil((data.total_count || 0) / filters.limit!)}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
```

**Key Points:**
- Uses EXISTING `useActionHandler()` - not modified
- Uses EXISTING `PartCard` component - not modified
- Uses EXISTING `executeAction('view_part_stock')` - just passes filters
- React Query for caching + loading states
- `keepPreviousData: true` for smooth pagination

---

## 🔧 Backend: Dynamic SQL Builder

**Location:** `backend/n8n-workflows/master-view-workflow.json`

**Current state:** VIEW workflow has hardcoded queries

**Required change:** Add dynamic SQL builder function

### New n8n Function Node: "Build Dynamic SQL"

Insert AFTER "Switch on action_name" and BEFORE individual query nodes:

```javascript
// Build Dynamic SQL Function (n8n)
function buildDynamicSQL() {
  const actionName = $json.action_name;
  const filters = $json.parameters?.filters || {};
  const sortBy = $json.parameters?.sort_by || 'created_at';
  const sortOrder = $json.parameters?.sort_order || 'desc';
  const limit = $json.parameters?.limit || 50;
  const offset = $json.parameters?.offset || 0;

  let sql = '';
  let baseTable = '';

  // Determine base query by action
  switch(actionName) {
    case 'view_part_stock':
      baseTable = 'parts';
      sql = `SELECT * FROM parts WHERE yacht_id = '${$json.yacht_id}'`;

      // Apply location filter
      if (filters.location) {
        const loc = filters.location;
        const locationParts = [];
        if (loc.deck) locationParts.push(loc.deck);
        if (loc.room) locationParts.push(loc.room);
        if (loc.storage) locationParts.push(loc.storage);
        const locationStr = locationParts.join(', ');
        sql += ` AND location LIKE '%${locationStr}%'`;
      }

      // Apply status filter
      if (filters.status && filters.status.length > 0) {
        const statuses = filters.status.map(s => `'${s}'`).join(',');
        sql += ` AND status IN (${statuses})`;
      }

      // Apply quantity filter
      if (filters.quantity) {
        const { operator, value } = filters.quantity;
        const op = operator === 'lt' ? '<' : operator === 'lte' ? '<=' :
                   operator === 'gt' ? '>' : operator === 'gte' ? '>=' :
                   operator === 'eq' ? '=' : '=';
        if (operator === 'between' && Array.isArray(value)) {
          sql += ` AND stock_quantity BETWEEN ${value[0]} AND ${value[1]}`;
        } else {
          sql += ` AND stock_quantity ${op} ${value}`;
        }
      }
      break;

    case 'view_work_order_history':
      sql = `SELECT wo.*, e.name as equipment_name, u.name as assigned_to_name
             FROM work_orders wo
             LEFT JOIN equipment e ON e.id = wo.equipment_id
             LEFT JOIN users u ON u.id = wo.assigned_to
             WHERE wo.yacht_id = '${$json.yacht_id}'`;

      // Apply status filter
      if (filters.status && filters.status.length > 0) {
        const statuses = filters.status.map(s => `'${s}'`).join(',');
        sql += ` AND wo.status IN (${statuses})`;
      }

      // Apply time range filter
      if (filters.time_range) {
        sql += ` AND wo.created_at BETWEEN '${filters.time_range.start}' AND '${filters.time_range.end}'`;
      }
      break;

    case 'view_fault_history':
      sql = `SELECT f.*, e.name as equipment_name, u.name as reporter_name
             FROM faults f
             LEFT JOIN equipment e ON e.id = f.equipment_id
             LEFT JOIN users u ON u.id = f.created_by
             WHERE f.yacht_id = '${$json.yacht_id}'`;

      // Apply status filter
      if (filters.status && filters.status.length > 0) {
        const statuses = filters.status.map(s => `'${s}'`).join(',');
        sql += ` AND f.status IN (${statuses})`;
      }

      // Apply time range filter
      if (filters.time_range) {
        sql += ` AND f.created_at BETWEEN '${filters.time_range.start}' AND '${filters.time_range.end}'`;
      }

      // Apply equipment filter (if viewing all faults, not equipment-specific)
      if ($json.context?.equipment_id) {
        sql += ` AND f.equipment_id = '${$json.context.equipment_id}'`;
      }
      break;

    default:
      return { json: { error: 'Unsupported action for filtering' } };
  }

  // Add sorting
  sql += ` ORDER BY ${sortBy} ${sortOrder.toUpperCase()}`;

  // Add pagination
  sql += ` LIMIT ${limit} OFFSET ${offset}`;

  // Get total count (for pagination)
  const countSql = sql.replace(/SELECT .* FROM/, 'SELECT COUNT(*) as total FROM').replace(/ORDER BY.*/, '');

  return {
    json: {
      query: sql,
      countQuery: countSql,
      action_name: actionName,
      yacht_id: $json.yacht_id,
      filters: filters,
      pagination: { limit, offset }
    }
  };
}

// Execute
return buildDynamicSQL();
```

### Updated VIEW Workflow Structure

```
Webhook → Validate JWT → Check Auth → Switch on action_name
                                            ↓
                                    Build Dynamic SQL (NEW)
                                            ↓
                                    Execute Query (Postgres)
                                            ↓
                                    Execute Count Query (for pagination)
                                            ↓
                                    Build Response (with total_count)
                                            ↓
                                    Webhook Response
```

### Response Format Enhancement

Add `total_count` and `pagination` to response:

```json
{
  "success": true,
  "card_type": "part_list",
  "cards": [...],
  "total_count": 156,
  "pagination": {
    "limit": 50,
    "offset": 0,
    "current_page": 1,
    "total_pages": 4
  },
  "filters_applied": {
    "location": { "deck": "Deck 2", "storage": "Box 3" },
    "status": ["low_stock"]
  },
  "micro_actions": [...]
}
```

---

## 🎨 UI Components (New)

### Pagination Component

**Location:** `frontend/src/components/ui/pagination.tsx`

```typescript
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showFirstLast?: boolean;
}

export function Pagination({ currentPage, totalPages, onPageChange, showFirstLast = true }: PaginationProps) {
  // Render page numbers with ellipsis
  // << First | < Prev | 1 2 3 ... 10 | Next > | Last >>
}
```

### SortControls Component

**Location:** `frontend/src/components/ui/sort-controls.tsx`

```typescript
interface SortControlsProps {
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  options: { value: string; label: string }[];
  onSort: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
}

export function SortControls({ sortBy, sortOrder, options, onSort }: SortControlsProps) {
  // Dropdown for sort field + toggle for asc/desc
  // "Sort by: [Name ▼] [↓]"
}
```

---

## 📊 Performance Optimizations

### 1. Debouncing

All filter inputs must debounce before triggering API calls:

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedApplyFilter = useDebouncedCallback(
  (filterType, value) => {
    applyFilter(filterType, value);
  },
  500 // Wait 500ms after user stops typing
);
```

### 2. React Query Caching

```typescript
const { data } = useQuery({
  queryKey: ['parts', filters],
  queryFn: () => fetchParts(filters),
  staleTime: 30000, // Consider data fresh for 30 seconds
  cacheTime: 300000, // Keep in cache for 5 minutes
  keepPreviousData: true // Don't show loading on page change
});
```

### 3. SQL Optimization

- Always add `LIMIT` (default 50)
- Create indexes on filtered columns:
  ```sql
  CREATE INDEX idx_parts_location ON parts(location);
  CREATE INDEX idx_parts_status ON parts(status);
  CREATE INDEX idx_work_orders_status_created ON work_orders(status, created_at DESC);
  CREATE INDEX idx_faults_status_created ON faults(status, created_at DESC);
  ```

### 4. Count Query Optimization

Use approximate count for large tables:

```sql
-- Exact count (slow)
SELECT COUNT(*) FROM parts WHERE ...;

-- Approximate count (fast, good enough for pagination)
SELECT reltuples::bigint FROM pg_class WHERE relname = 'parts';
```

---

## 🧪 Testing Plan

### Unit Tests (Jest)
- Filter components render correctly
- useFilters hook builds correct params
- FilterBar shows active filters

### Integration Tests
1. Apply location filter → Verify API call has correct parameters
2. Change page → Verify offset calculation
3. Clear filter → Verify it's removed from API call
4. Sort + Filter combination → Verify both work together

### Performance Tests
- VIEW workflow response time < 400ms (measure with n8n logs)
- Frontend re-render count when changing filters (should be minimal)

---

## 📁 File Structure (New Files Only)

```
frontend/src/
├── components/
│   ├── filters/                    # NEW
│   │   ├── FilterBar.tsx
│   │   ├── LocationFilter.tsx
│   │   ├── StatusFilter.tsx
│   │   ├── TimeRangeFilter.tsx
│   │   ├── QuantityFilter.tsx
│   │   └── FilterBadge.tsx
│   └── ui/                         # NEW
│       ├── pagination.tsx
│       └── sort-controls.tsx
├── hooks/
│   └── useFilters.ts               # NEW
└── app/
    ├── parts/
    │   └── page.tsx                # NEW
    ├── work-orders/
    │   └── page.tsx                # NEW
    └── faults/
        └── page.tsx                # NEW

backend/n8n-workflows/
└── master-view-workflow.json       # MODIFIED (add dynamic SQL)

docs/phase3/
└── PHASE_3_CORE_IMPLEMENTATION_PLAN.md  # THIS FILE
```

---

## 📋 Implementation Checklist

### Day 1: Filter Infrastructure
- [ ] Create `FilterBar.tsx`
- [ ] Create `FilterBadge.tsx`
- [ ] Create `LocationFilter.tsx` (generic)
- [ ] Create `StatusFilter.tsx` (generic)
- [ ] Create `TimeRangeFilter.tsx` (generic)
- [ ] Create `QuantityFilter.tsx` (generic)
- [ ] Create `useFilters.ts` hook
- [ ] Create `pagination.tsx` component
- [ ] Create `sort-controls.tsx` component
- [ ] Test filter components in isolation

### Day 2: Backend Integration
- [ ] Update `master-view-workflow.json`:
  - [ ] Add "Build Dynamic SQL" function node
  - [ ] Add count query execution
  - [ ] Update response format with pagination
- [ ] Test dynamic SQL generation with sample payloads
- [ ] Verify performance (<400ms)
- [ ] Create database indexes for filtered columns

### Day 3: List Pages
- [ ] Build `app/parts/page.tsx` with all 4 filters
- [ ] Build `app/work-orders/page.tsx` with status + time filters
- [ ] Build `app/faults/page.tsx` with status + time filters
- [ ] Add sort controls to all pages
- [ ] Add pagination to all pages
- [ ] Test end-to-end filter → API → results flow
- [ ] Performance testing (debouncing, caching)

### Day 4: Polish & Documentation
- [ ] Add loading skeletons
- [ ] Add empty states ("No parts found matching filters")
- [ ] Add error states
- [ ] Mobile responsive filters (collapsible on mobile)
- [ ] Create `docs/phase3/FILTER_USAGE_GUIDE.md`
- [ ] Create `docs/phase3/VIEW_WORKFLOW_PARAMETERS.md`
- [ ] Final testing
- [ ] Commit and push

---

## 🔍 Example: Complete Filter Flow

### User Action
User opens Parts page, applies filters:
- Location: "Deck 2, Locker 5"
- Status: ["low_stock"]
- Quantity: stock < 5

### Frontend State
```typescript
{
  location: { deck: "Deck 2", storage: "Locker 5" },
  status: ["low_stock"],
  quantity: { operator: "lt", value: 5 },
  sortBy: "part_name",
  sortOrder: "asc",
  page: 1,
  limit: 50
}
```

### API Request (Built by useFilters)
```json
POST /workflows/view
{
  "action_name": "view_part_stock",
  "context": {},
  "parameters": {
    "filters": {
      "location": { "deck": "Deck 2", "storage": "Locker 5" },
      "status": ["low_stock"],
      "quantity": { "operator": "lt", "value": 5 }
    },
    "sort_by": "part_name",
    "sort_order": "asc",
    "limit": 50,
    "offset": 0
  },
  "session": { "user_id": "...", "yacht_id": "..." }
}
```

### n8n Dynamic SQL Builder Output
```sql
SELECT * FROM parts
WHERE yacht_id = 'yacht001'
  AND location LIKE '%Deck 2%' AND location LIKE '%Locker 5%'
  AND status IN ('low_stock')
  AND stock_quantity < 5
ORDER BY part_name ASC
LIMIT 50 OFFSET 0;

-- Count query (for pagination)
SELECT COUNT(*) as total FROM parts
WHERE yacht_id = 'yacht001'
  AND location LIKE '%Deck 2%' AND location LIKE '%Locker 5%'
  AND status IN ('low_stock')
  AND stock_quantity < 5;
```

### API Response
```json
{
  "success": true,
  "card_type": "part_list",
  "cards": [
    { "id": "p1", "part_name": "Hydraulic seal", "stock_quantity": 2, "location": "Deck 2, Locker 5", "status": "low_stock" },
    { "id": "p2", "part_name": "O-ring set", "stock_quantity": 3, "location": "Deck 2, Locker 5", "status": "low_stock" }
  ],
  "total_count": 8,
  "pagination": {
    "limit": 50,
    "offset": 0,
    "current_page": 1,
    "total_pages": 1
  },
  "filters_applied": {
    "location": { "deck": "Deck 2", "storage": "Locker 5" },
    "status": ["low_stock"],
    "quantity": { "operator": "lt", "value": 5 }
  },
  "micro_actions": ["order_part", "log_part_usage", "view_part_location"]
}
```

### Frontend Render
```tsx
<FilterBar activeFilters={...} />  {/* Shows 3 active filter badges */}
<SortControls sortBy="part_name" sortOrder="asc" />
<div className="grid grid-cols-3 gap-4">
  <PartCard part={...} />  {/* EXISTING component */}
  <PartCard part={...} />
</div>
<Pagination currentPage={1} totalPages={1} />
```

---

## ⚠️ Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation:**
- Only add NEW files
- Only modify `master-view-workflow.json` (add, don't replace)
- Test existing actions still work without filters
- Backwards compatibility: if no `parameters.filters`, use existing hardcoded queries

### Risk 2: Performance Degradation
**Mitigation:**
- Always use `LIMIT` (default 50)
- Debounce all filter inputs (500ms)
- Use React Query caching
- Create database indexes
- Monitor n8n execution time (<400ms requirement)

### Risk 3: SQL Injection
**Mitigation:**
- Use parameterized queries in n8n (NOT string concatenation)
- Validate filter inputs on frontend
- Sanitize all user inputs before SQL construction
- Use Supabase RLS as additional layer

### Risk 4: Scope Creep
**Mitigation:**
- Stick to 4 filters only (location, status, time, quantity)
- NO saved views
- NO dashboards
- NO trend charts
- NO RAG integration
- Focus on core filtering only

---

## 📊 Success Metrics

Phase 3 Core is successful when:

✅ **Functionality:**
- All 4 filters work on Parts page
- All 4 filters work on WorkOrders page
- Status + Time filters work on Faults page
- Pagination works (50 items per page)
- Sorting works (by name, date, status, etc.)
- Filter badges show active filters
- Clear all filters works

✅ **Performance:**
- VIEW workflow response time < 400ms (measured)
- Filter debouncing prevents excessive API calls
- React Query caching prevents redundant requests
- Page changes don't flicker (keepPreviousData)

✅ **Architecture:**
- No existing Phase 1/2 files modified (except master-view-workflow.json)
- All filters are generic and reusable
- useFilters hook is entity-agnostic
- Backwards compatible (existing actions work without filters)

✅ **Code Quality:**
- TypeScript types for all components
- No console errors or warnings
- Mobile responsive
- Follows existing code conventions

---

## 🚀 Go/No-Go Decision

**Proceed with implementation if:**
- ✅ This plan is approved
- ✅ Guard rails are clear
- ✅ No scope creep requests

**Do NOT proceed if:**
- ❌ Requirements unclear
- ❌ Scope expansion (dashboards, saved views, etc.)
- ❌ Guard rails violated (modifying existing architecture)

---

**Status:** AWAITING APPROVAL TO BEGIN CODING

**Next Step:** Upon approval, begin Day 1 implementation (filter components)
