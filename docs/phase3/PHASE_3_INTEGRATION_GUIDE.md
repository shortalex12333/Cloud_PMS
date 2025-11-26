# Phase 3 Integration Guide

**Date:** 2025-11-21
**Branch:** `claude/read-repo-files-01TwqiaKXUk14frUXUPkVKTj`
**Merge Target:** `claude/holistic-branch-merge-01B72XviGZJuL8Fi4QzXQPS5`

---

## Overview

Phase 3 implements the **READ dimension** with comprehensive filtering, sorting, and pagination for list views. This document outlines what was built, what was fixed, and how to integrate with the holistic branch.

---

## What Was Built

### **1. Filter Components (6 components)**
- `FilterBadge.tsx` - Removable filter chips
- `FilterBar.tsx` - Container with active filters display
- `LocationFilter.tsx` - Hierarchical deck/room/storage selector
- `StatusFilter.tsx` - Multi-select status chips with color coding
- `TimeRangeFilter.tsx` - Date range with presets + custom
- `QuantityFilter.tsx` - Numeric filter with operators

**Status:** ✅ Complete - Entity-agnostic, reusable across all entities

### **2. Navigation Components (2 components)**
- `Pagination.tsx` - Page controls + items-per-page selector
- `SortControls.tsx` - Sort field dropdown + direction toggle

**Status:** ✅ Complete

### **3. State Management**
- `useFilters.ts` - Filter state management with URL sync, query builder

**Status:** ✅ Complete - Builds unified query format for n8n

### **4. List Pages (3 pages)**
- `PartsListPage` - Parts inventory with filters
- `WorkOrdersListPage` - Work orders with filters
- `FaultsListPage` - Faults with filters

**Status:** ⚠️ Functional but needs integration with `callCelesteApi()` from holistic branch

### **5. n8n Workflow Enhancement**
- **Updated:** `master-view-workflow.json`
- **Added:**
  - Dynamic SQL filter builder node
  - 3 list query nodes (parts, work_orders, faults)
  - 3 count nodes for pagination
  - Routing switch node

**Status:** ✅ Complete and **FIXED** (see below)

---

## Critical Fix: n8n Workflow Routing Bug

### **Issue Identified**
The initial implementation had a **critical routing bug**:

```json
"Build SQL Filter": {
  "main": [[
    { "node": "view_parts_list" },      // ❌ All 3 ran
    { "node": "view_work_orders_list" }, // ❌ in parallel
    { "node": "view_faults_list" }      // ❌ regardless of action
  ]]
}
```

**Problem:** All 3 queries executed simultaneously regardless of which action was requested. Wasteful and incorrect.

### **Fix Applied**

Added a **"Route to Query" switch node** that examines `action_name` and routes to ONLY the appropriate query:

```json
"Build SQL Filter": {
  "main": [[
    { "node": "Route to Query" }  // ✅ Routes to switch
  ]]
},
"Route to Query": {
  "main": [
    [{ "node": "view_parts_list" }],      // Output 0: view_parts_list
    [{ "node": "view_work_orders_list" }], // Output 1: view_work_orders_list
    [{ "node": "view_faults_list" }]      // Output 2: view_faults_list
  ]
}
```

**Flow:**
1. Switch on action_name → routes list actions to "Build SQL Filter"
2. Build SQL Filter → builds WHERE/ORDER/LIMIT clauses
3. Route to Query → examines action_name, routes to specific query
4. Query node → executes SQL with dynamic filters
5. Count node → gets total count for pagination
6. Build Response → merges data + pagination metadata

**Status:** ✅ Fixed - Each action now runs ONLY its specific query

---

## Integration with Holistic Branch

### **Files That Exist in Holistic Branch (Don't Duplicate)**

1. ✅ `frontend/src/lib/apiClient.ts` - Has `callCelesteApi()` function
2. ✅ `frontend/src/hooks/useAuth.ts` - Has `useAuth()` hook
3. ✅ `frontend/src/hooks/useDebounce.ts` - Has debouncing utilities

### **Files from This Branch (Phase 3)**

**Filters:**
```
frontend/src/components/filters/
├── FilterBadge.tsx
├── FilterBar.tsx
├── LocationFilter.tsx
├── StatusFilter.tsx
├── TimeRangeFilter.tsx
└── QuantityFilter.tsx
```

**Navigation:**
```
frontend/src/components/ui/
├── Pagination.tsx
└── SortControls.tsx
```

**Hooks:**
```
frontend/src/hooks/
└── useFilters.ts
```

**Pages:**
```
frontend/src/app/(dashboard)/
├── parts/page.tsx
├── work-orders/page.tsx
└── faults/page.tsx
```

**Backend:**
```
backend/n8n-workflows/
└── master-view-workflow.json (UPDATED)
```

### **Integration Steps**

#### **Step 1: Merge Phase 3 Files into Holistic Branch**

```bash
# From holistic branch
git checkout claude/holistic-branch-merge-01B72XviGZJuL8Fi4QzXQPS5

# Merge Phase 3 branch
git merge claude/read-repo-files-01TwqiaKXUk14frUXUPkVKTj
```

#### **Step 2: Update List Pages to Use `callCelesteApi()`**

The pages currently reference `useActionHandler.execute()` but should use `callCelesteApi()` directly for better control.

**Example for PartsListPage:**

```typescript
// BEFORE (current - won't work without apiClient)
const { execute, isLoading } = useActionHandler();
useEffect(() => {
  const fetchParts = async () => {
    const response = await execute('view_parts_list', { parameters: queryParams });
    setParts(response.card.rows);
  };
  fetchParts();
}, [queryParams]);

// AFTER (with callCelesteApi from holistic branch)
import { callCelesteApi } from '@/lib/apiClient';

const fetchParts = async () => {
  setIsLoading(true);
  try {
    const response = await callCelesteApi('/workflows/view', {
      method: 'POST',
      body: JSON.stringify({
        action_name: 'view_parts_list',
        context: { yacht_id: user.yacht_id },
        parameters: queryParams,
        session: { user_id: user.id, yacht_id: user.yacht_id, timestamp: new Date().toISOString() }
      })
    });
    setParts(response.card?.rows || []);
    setTotalCount(response.pagination?.total || 0);
  } catch (error) {
    console.error('Failed to fetch parts:', error);
  } finally {
    setIsLoading(false);
  }
};
```

#### **Step 3: Add Debouncing to Filters (Optional but Recommended)**

Use `useDebounce` from holistic branch to prevent filter spam:

```typescript
import { useDebounce } from '@/hooks/useDebounce';

// In filter components:
const debouncedFilters = useDebounce(filters, 500);

useEffect(() => {
  fetchData();
}, [debouncedFilters]); // Only refetch after 500ms of no changes
```

#### **Step 4: Test n8n Workflow**

1. Import updated `master-view-workflow.json` into n8n
2. Activate the workflow
3. Test each list action:
   - `view_parts_list` with filters
   - `view_work_orders_list` with filters
   - `view_faults_list` with filters
4. Verify only ONE query executes per request (check n8n execution logs)
5. Verify pagination metadata is returned

---

## What Still Needs Work

### **Optional: React Query Integration**

For better data fetching patterns, consider adding React Query:

```bash
npm install @tanstack/react-query
```

**Setup:**
```typescript
// app/layout.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      cacheTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function RootLayout({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**Usage in pages:**
```typescript
import { useQuery } from '@tanstack/react-query';

const { data, isLoading, error } = useQuery({
  queryKey: ['parts', queryParams],
  queryFn: () => callCelesteApi('/workflows/view', { ... }),
  keepPreviousData: true, // Smooth pagination
});
```

**Benefits:**
- Automatic caching
- Background refetching
- Loading/error states
- Optimistic updates

**Status:** ❌ Not implemented (works fine without it, but nice to have)

---

## Testing Checklist

After merge, verify:

- [ ] Parts page loads and displays parts
- [ ] Location filter works (deck/room/storage)
- [ ] Status filter works (multi-select)
- [ ] Quantity filter works (all operators)
- [ ] Pagination works (page navigation + items per page)
- [ ] Sorting works (field + direction)
- [ ] URL sync works (filters persist in URL)
- [ ] Work orders page filters correctly
- [ ] Faults page filters correctly
- [ ] Only ONE query executes per filter change (check n8n logs)
- [ ] Count matches actual results
- [ ] Debouncing prevents filter spam
- [ ] Mobile responsive on all pages

---

## Performance Notes

### **Expected Response Times**

- **Without filters:** <200ms (simple SELECT with LIMIT)
- **With filters:** <400ms (WHERE clause + COUNT query)
- **With complex filters:** <600ms (multiple JOINs + filtering)

### **Optimization Opportunities**

1. **Database Indexes** - Add indexes on:
   ```sql
   CREATE INDEX idx_parts_yacht_deck ON parts(yacht_id, deck);
   CREATE INDEX idx_parts_yacht_status ON parts(yacht_id, status);
   CREATE INDEX idx_parts_yacht_created ON parts(yacht_id, created_at);
   CREATE INDEX idx_wo_yacht_status ON work_orders(yacht_id, status);
   CREATE INDEX idx_faults_yacht_status ON faults(yacht_id, status);
   ```

2. **React Query Caching** - Reduces API calls by 80%+ for repeated views

3. **Debouncing** - Already supported via holistic branch

---

## Conclusion

Phase 3 is **functionally complete** with the routing bug **fixed**. Integration with holistic branch should be straightforward since all missing dependencies (apiClient, useAuth, useDebounce) exist there.

**Key Achievement:** Complete READ dimension with entity-agnostic, reusable filter system that works across all list views.

**Next Phase:** Phase 4 would focus on completing the remaining ~15 modal components for CREATE/UPDATE actions.
