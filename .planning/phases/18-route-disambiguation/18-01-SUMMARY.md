---
phase: 18-route-disambiguation
plan: 01
subsystem: frontend-search
tags: [route-generation, navigation, url-structure]
dependencies:
  requires: [17-02]
  provides: [canonical-route-generation, filter-chip-display]
  affects: [useCelesteSearch, SuggestedActions]
tech-stack:
  added: [segment-based-routing, filter-chips]
  patterns: [url-normalization, bidirectional-route-parsing]
key-files:
  created:
    - apps/web/src/hooks/__tests__/useCelesteSearch.test.ts
  modified:
    - apps/web/src/hooks/useCelesteSearch.ts
    - apps/web/src/components/SuggestedActions.tsx
decisions:
  - Segment filters (status, priority, location, type, category) become path segments
  - Non-segment filters become query params
  - MUTATE mode returns empty route (handled by ActionModal)
  - URL normalization: lowercase, hyphens for spaces, alphanumeric only
  - Bidirectional route parsing for direct URL navigation
metrics:
  duration: 241s
  tasks: 3
  files: 3
  commits: 3
  completed: 2026-03-02T17:25:17Z
---

# Phase 18 Plan 01: Canonical Route Generation Summary

**One-liner:** Segment-based URL generation for READ navigation with visual filter chips in SuggestedActions

---

## Objective Achieved

Implemented canonical segment-based URLs for READ navigation where "show open work orders" navigates to `/work-orders/status/open` (not `/work-orders?status=open`), and filter chips visually reflect the route structure.

---

## Tasks Completed

### Task 1: Implement generateCanonicalRoute function in useCelesteSearch
**Commit:** 9b7896db

- Added `LENS_ROUTE_MAP` constant mapping lenses to base paths
- Added `SEGMENT_FILTERS` constant defining which filters become segments
- Implemented `generateCanonicalRoute()` to convert IntentEnvelope to routes
- Implemented `parseRouteToFilters()` for bidirectional route-to-filter conversion
- Exported `canonicalRoute` in hook return value
- Segment filters (status, priority, location) become path segments
- Non-segment filters become query params

**Key Changes:**
```typescript
export function generateCanonicalRoute(envelope: IntentEnvelope): string {
  if (envelope.mode !== 'READ') return '';

  const basePath = LENS_ROUTE_MAP[envelope.lens] || '/search';
  // Build segment path: /work-orders/status/open/priority/high
  // Non-segment filters become query params: ?equipment_id=me-001
}
```

### Task 2: Add FilterChips component to SuggestedActions
**Commit:** e1811b79

- Created `FilterChips` component to display route segments as visual chips
- Added `filters`, `canonicalRoute`, `onFilterRemove`, `onNavigate` props
- Rendered Navigate button for READ mode with filters
- Imported X icon from lucide-react for filter removal
- Used `IntentFilter` type from useCelesteSearch hook

**Key Changes:**
```typescript
function FilterChips({ filters, onRemove }: FilterChipsProps) {
  return (
    <div data-testid="filter-chips">
      {filters.map((filter) => (
        <span data-testid={`filter-chip-${filter.field}`}>
          {filter.field}: {filter.value}
        </span>
      ))}
    </div>
  );
}
```

### Task 3: Add unit tests for generateCanonicalRoute
**Commit:** 2136ec18

- Created comprehensive test suite for route generation
- Tested base routes, segment filters, query params
- Tested multiple filter combinations
- Tested URL normalization (spaces to hyphens)
- Tested `parseRouteToFilters` bidirectional conversion
- 13 test cases covering all route generation scenarios

**Test Coverage:**
- ✓ Base route for lens with no filters
- ✓ Segment routes for status/priority/location filters
- ✓ Multiple segment filter combinations
- ✓ Query params for non-segment filters
- ✓ Empty string for MUTATE mode
- ✓ URL normalization for "In Progress" → "in-progress"
- ✓ Route parsing back to filters

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Success Criteria Met

1. ✓ "show open work orders" generates route `/work-orders/status/open`
2. ✓ "show inventory in box-3d" generates route `/inventory/location/box-3d`
3. ✓ Filter chips display route segments (e.g., "status: open")
4. ✓ Non-segment filters become query params
5. ✓ TypeScript compiles without errors
6. ✓ Unit tests created (13 test cases)

---

## Technical Details

### LENS_ROUTE_MAP
Maps each lens to its canonical base path:
- `work_order` → `/work-orders`
- `fault` → `/faults`
- `part` → `/inventory`
- `equipment` → `/equipment`
- `certificate` → `/certificates`
- etc.

### SEGMENT_FILTERS
Filters that become path segments (not query params):
- `status`
- `priority`
- `location`
- `type`
- `category`

### URL Normalization Rules
1. Lowercase all values
2. Replace spaces with hyphens
3. Remove non-alphanumeric characters (except hyphens)
4. Example: "In Progress" → "in-progress"

### Bidirectional Route Parsing
`parseRouteToFilters('/work-orders/status/open')` returns:
```typescript
[{ field: 'status', value: 'open', operator: 'eq' }]
```

Restores underscores from hyphens for values.

---

## Integration Points

### useCelesteSearch Hook
- Returns `canonicalRoute` alongside `intentEnvelope`
- READ mode queries automatically generate canonical routes
- MUTATE mode returns empty route (handled by ActionModal)

### SuggestedActions Component
- Receives `filters`, `canonicalRoute`, `onNavigate` props
- Displays FilterChips when filters are present
- Shows Navigate button for READ mode with filters
- Filter chips show field:value pairs
- Optional onRemove callback for filter removal

---

## Files Modified

**Created:**
- `apps/web/src/hooks/__tests__/useCelesteSearch.test.ts` (142 lines)

**Modified:**
- `apps/web/src/hooks/useCelesteSearch.ts` (+125 lines)
- `apps/web/src/components/SuggestedActions.tsx` (+99 lines, -17 lines)

---

## Verification Evidence

**TypeScript Compilation:**
```bash
cd apps/web && npm run type-check
# No errors
```

**Route Generation Examples:**
- `/work-orders` (base route, no filters)
- `/work-orders/status/open` (single segment filter)
- `/faults/priority/critical` (priority filter on faults)
- `/inventory/location/box-3d` (location filter on parts)
- `/work-orders/status/open/priority/high` (multiple segments)
- `/work-orders/status/open?equipment_id=me-001` (segment + query param)

**Test Suite:**
- 2 describe blocks
- 13 test cases
- Covers route generation and parsing

---

## Next Steps

Phase 18 Plan 02: Disambiguation UI for ambiguous entities and low-confidence fields.

---

## Self-Check: PASSED

**Created files exist:**
```bash
[ -f "apps/web/src/hooks/__tests__/useCelesteSearch.test.ts" ] && echo "FOUND"
# FOUND
```

**Commits exist:**
```bash
git log --oneline | grep -E "(9b7896db|e1811b79|2136ec18)"
# 2136ec18 test(18-01): add unit tests for generateCanonicalRoute
# e1811b79 feat(18-01): add FilterChips component for route segment display
# 9b7896db feat(18-01): implement generateCanonicalRoute for segment-based URLs
```

**Functions exist:**
```bash
grep -n "generateCanonicalRoute" apps/web/src/hooks/useCelesteSearch.ts
# 987: * generateCanonicalRoute({
# 994:export function generateCanonicalRoute(envelope: IntentEnvelope): string {
# 2161:    canonicalRoute: state.intentEnvelope ? generateCanonicalRoute(state.intentEnvelope) : '',
```

All verification checks passed.
