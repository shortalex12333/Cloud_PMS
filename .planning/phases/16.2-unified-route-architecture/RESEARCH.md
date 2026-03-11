# Phase 16.2 Research — Unified Route Architecture

**Generated:** 2026-03-03
**Phase:** 16.2 - Unified Route Architecture

---

## Problem Statement

The current codebase has **12 fragmented route pages** totaling **~4,682 lines** of duplicated code. Each route page (`/faults/[id]`, `/work-orders/[id]`, etc.) replicates:
- Action buttons and handlers
- Permission checks
- State management
- Modal components
- Navigation callbacks
- Loading/error/not-found states

These route pages duplicate logic that already exists in the `*LensContent` components used by the SPA mode via `LensRenderer`.

## Current Architecture Analysis

### Files Involved

| Category | Files | Total LOC |
|----------|-------|-----------|
| Fragmented Routes | 12 files in `/src/app/*/[id]/page.tsx` | ~4,682 |
| LensContent Components | 13 files in `/src/components/lens/*LensContent.tsx` | ~6,500 |
| LensRenderer | 1 file `/src/components/lens/LensRenderer.tsx` | ~154 |
| Permission Hooks | 12 files `/src/hooks/use*Actions.ts` | ~4,200 |

### Fragmented Route Files (from audit)

1. `/src/app/faults/[id]/page.tsx` - 405 LOC
2. `/src/app/work-orders/[id]/page.tsx` - ~601 LOC
3. `/src/app/equipment/[id]/page.tsx` - ~426 LOC
4. `/src/app/certificates/[id]/page.tsx` - ~427 LOC
5. `/src/app/warranties/[id]/page.tsx` - ~357 LOC
6. `/src/app/hours-of-rest/[id]/page.tsx` - ~384 LOC
7. `/src/app/receiving/[id]/page.tsx` - ~383 LOC
8. `/src/app/shopping-list/[id]/page.tsx` - ~389 LOC
9. `/src/app/inventory/[id]/page.tsx` - ~245 LOC
10. `/src/app/documents/[id]/page.tsx` - ~449 LOC
11. `/src/app/purchasing/[id]/page.tsx` - ~420 LOC
12. `/src/app/handover-export/[id]/page.tsx` - ~196 LOC

### 26 Unwired Buttons (GAP-021 - fixed during Button Hardening)

These buttons were fixed during the Button Hardening Audit (2026-03-02), but the fundamental issue remains: two parallel implementations must be kept in sync.

## Target Architecture

### Key Components

1. **RouteShell** (`/src/components/lens/RouteShell.tsx`)
   - Thin wrapper component (~100 LOC)
   - Handles feature flag gating
   - Fetches entity data via react-query
   - Provides route-specific navigation callbacks
   - Delegates to existing LensContent components

2. **usePermissions** (`/src/hooks/usePermissions.ts`)
   - Unified RBAC hook (~80 LOC)
   - Reads from `lens_matrix.json`
   - Replaces 12 hardcoded permission hooks

3. **lens_matrix.json** (`/src/lib/lens_matrix.json`)
   - Single source of truth for all RBAC decisions
   - Contains per-lens: actions, role_restricted, requires_signature, requires_confirmation

### Existing Infrastructure

The `LensRenderer.tsx` already handles:
- Entity type to component mapping
- Navigation callbacks for SPA mode
- Cross-entity navigation

The spec document at `/docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md` contains:
- Full RouteShell implementation spec (lines 269-500+)
- usePermissions hook spec
- Migration checklist

## Implementation Strategy

### Phase 1: Create Core Components
1. Create `RouteShell.tsx` based on spec
2. Create `usePermissions.ts` hook
3. Create/update `lens_matrix.json`

### Phase 2: Refactor Permission Hooks
1. Update 12 permission hooks to read from lens_matrix.json
2. Keep backward compatibility initially

### Phase 3: Replace Route Pages
1. Replace each 400+ LOC route page with ~20 LOC RouteShell usage
2. Each route becomes:
   ```typescript
   export default function FaultDetailPage() {
     const params = useParams();
     return (
       <RouteShell
         entityType="fault"
         entityId={params.id as string}
         listRoute="/faults"
       />
     );
   }
   ```

### Phase 4: Cleanup
1. Remove dead code from route pages
2. Consolidate duplicate permission logic
3. Verify all buttons work via E2E tests

## Dependencies

- **LensContent components**: Must support `onBack`, `onClose`, `onNavigate`, `onRefresh` callbacks
- **Feature flags**: `isFragmentedRoutesEnabled()` already exists
- **RouteLayout**: Wrapper component already exists

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Button functionality loss | E2E tests for each lens after migration |
| Navigation behavior change | Route-specific callbacks in RouteShell |
| Permission regressions | lens_matrix.json is derived from existing hooks |
| Feature flag edge cases | Redirect logic already tested in current routes |

## Acceptance Criteria

From ROADMAP.md Phase 16.2:

1. TypeScript compiles clean with no errors
2. Feature flag OFF: all routes redirect to /app?entity=
3. Feature flag ON: all routes render LensContent with working buttons
4. No hardcoded role arrays remain in permission hooks
5. lens_matrix.json is single source of truth for RBAC
6. ~4,682 LOC reduced to ~240 LOC (-95%)

## References

- `/docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md` - Full spec (1,003 lines)
- `/docs/ON_GOING_WORK/BACKEND/LENSES/GAPS.md` - GAP-023 to GAP-026
- `/docs/ON_GOING_WORK/BACKEND/LENSES/PHASES-REMAINING.md` - Phase overview
