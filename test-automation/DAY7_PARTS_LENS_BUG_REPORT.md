# Day 7: Parts Lens Click Bug - Root Cause & Fix

**Date:** 2026-02-11
**Status:** 🔴 CRITICAL BUG IDENTIFIED
**Impact:** Parts Lens completely broken - clicking parts does nothing useful

---

## The Problem

**User Experience:**
```
User searches "oil filter"
→ Results appear
→ User clicks a part
→ ❌ EITHER: Navigation breaks single surface
→ ❌ OR: Nothing visible happens
→ ❌ Result: User cannot view part details
```

---

## Root Cause Analysis

### The Bug Location
**File:** `apps/web/src/components/spotlight/SpotlightSearch.tsx`
**Lines:** 393-407

```typescript
const handleResultOpen = useCallback(async (result: SpotlightResult) => {
  const entityType = mapResultTypeToEntityType(result.type);

  // ❌ BUG: Tries to navigate to full page
  const routeMap: Record<EntityType, string> = {
    'part': `/parts/${result.id}`,  // WRONG!
    'equipment': `/equipment/${result.id}`,
    'document': `/documents/${result.id}`,
    // ...
  };

  const targetRoute = routeMap[entityType];

  if (targetRoute) {
    router.push(targetRoute);  // ❌ Breaks single surface!
  }
}, []);
```

### Why This Is Wrong

**Your Vision:**
- **Single surface design** - everything on `/` (no fragmented URLs)
- No navigation, no page changes
- ContextPanel slides from right for details

**Current Code:**
- Tries to navigate to `/parts/${id}` (breaks single surface)
- Uses full-page view designed for external deep links
- Completely contradicts the architecture

### The Confusion

The `/parts/[id]` page EXISTS but was created for a **different purpose**:

```typescript
/**
 * PURPOSE: Full-page lens for part/inventory entities
 * accessed via handover export links
 *
 * HANDOVER EXPORT FLOW:
 * 1. User clicks link in PDF: https://app.celeste7.ai/open?t=<TOKEN>
 * 2. Resolves token
 * 3. Redirects to /parts/{id}
 * 4. Full page renders
 *
 * Created: 2026-02-05
 */
```

**This page is for EXTERNAL links only**, not internal Spotlight clicks!

---

## The Correct Architecture (Already Exists!)

### ✅ Infrastructure is Already Built

**1. SurfaceContext has `showContext()` method:**
```typescript
// apps/web/src/contexts/SurfaceContext.tsx:107-113
const showContext = useCallback(
  (entityType: string, entityId: string, data?: Record<string, unknown>) => {
    setContextPanel({
      visible: true,
      entityType,
      entityId,
      entityData: data,
    });
  }, []
);
```

**2. ContextPanel knows how to render parts:**
```typescript
// apps/web/src/app/app/ContextPanel.tsx:192-220
case 'part':
case 'inventory':
  const partData = {
    id: entityId,
    part_name: data.name || data.part_name || 'Part',
    part_number: data.part_number || '',
    stock_quantity: data.quantity_on_hand || data.stock_quantity || 0,
    min_stock_level: data.minimum_quantity || data.min_stock_level || 0,
    location: data.location || 'Unknown',
    // ... more fields
  };

  const partActions = getPartActions(user?.role || 'crew');

  return (
    <div data-testid="context-panel-part-card">
      <PartCard
        part={partData}
        entityType={entityType}
        actions={partActions}
      />
    </div>
  );
```

**3. PartCard component renders correctly:**
- Shows part name, part number
- Shows stock quantity with LOW STOCK warnings
- Shows location, supplier, cost
- Shows action buttons filtered by role

**Everything is there!** Just needs to be connected.

---

## The Fix

### Change 1: Use `showContext()` instead of navigation

**File:** `apps/web/src/components/spotlight/SpotlightSearch.tsx:379-407`

**Current (WRONG):**
```typescript
const handleResultOpen = useCallback(async (result: SpotlightResult) => {
  const entityType = mapResultTypeToEntityType(result.type);
  const domain = mapEntityTypeToDomain(entityType);

  // Special handling for email threads
  if (entityType === 'email_thread' && surfaceContext) {
    const threadId = result.metadata?.thread_id || result.id;
    surfaceContext.showEmail({ threadId, folder: 'inbox' });
    return;
  }

  // ❌ BUG: Navigate to full page
  const routeMap: Record<EntityType, string> = {
    'work_order': `/work-orders/${result.id}`,
    'part': `/parts/${result.id}`,
    'equipment': `/equipment/${result.id}`,
    'document': `/documents/${result.id}`,
    'fault': `/faults/${result.id}`,
    'inventory': `/inventory/${result.id}`,
    'email_thread': `/email/${result.id}`,
  };

  const targetRoute = routeMap[entityType];

  if (targetRoute) {
    router.push(targetRoute);  // ❌ WRONG!
    onClose?.();
  } else {
    // Fallback to situation view...
  }
}, []);
```

**Fixed (CORRECT):**
```typescript
const handleResultOpen = useCallback(async (result: SpotlightResult) => {
  const entityType = mapResultTypeToEntityType(result.type);

  // Special handling for email threads (already correct)
  if (entityType === 'email_thread' && surfaceContext) {
    const threadId = result.metadata?.thread_id || result.id;
    surfaceContext.showEmail({ threadId, folder: 'inbox' });
    return;
  }

  // ✅ FIX: Use showContext() for all other entity types
  if (surfaceContext) {
    surfaceContext.showContext(
      entityType,
      result.id,
      result.metadata  // Pass full metadata for detail view
    );
    // Don't call onClose() - keep search visible
  } else {
    console.warn('[SpotlightSearch] SurfaceContext not available');
  }
}, [surfaceContext, mapResultTypeToEntityType]);
```

### Change 2: Keep `/parts/[id]` for external deep links only

**No changes needed** - this page is correct for its purpose (handover exports).

**Add a check** to distinguish internal vs external navigation:
```typescript
// apps/web/src/app/parts/[id]/page.tsx

export default function PartDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();

  // Check if this is internal navigation (should use ContextPanel instead)
  useEffect(() => {
    const isInternalNavigation = document.referrer.includes('app.celeste7.ai');

    if (isInternalNavigation) {
      console.warn('[PartDetailPage] Internal navigation detected - should use ContextPanel!');
      // Redirect back to home with context panel
      router.push('/');
      // TODO: Open context panel programmatically
    }
  }, [router]);

  // ... rest of page for external deep links
}
```

---

## Testing the Fix

### Test 1: Click Part from Search
```
1. User types "oil filter" in search
2. Results appear
3. User clicks first result
4. ✅ ContextPanel slides open from right
5. ✅ Part details displayed in panel
6. ✅ URL stays at / (single surface maintained)
7. ✅ Search bar still visible
8. ✅ Action buttons shown (filtered by role)
```

### Test 2: External Deep Link
```
1. User clicks link in handover PDF: /open?t=<token>
2. Token resolves to part ID
3. ✅ Navigates to /parts/{id}
4. ✅ Full page view renders
5. ✅ Back button available
6. ✅ Works for users without session
```

### Test 3: RBAC Enforcement
```
Captain clicks part:
✅ Sees actions: View Details, Check Stock, Log Usage

Crew clicks part:
✅ Sees actions: View Details, Check Stock only
```

---

## Impact Assessment

### Current State (Broken):
- ❌ Users cannot view part details from search
- ❌ Parts Lens is completely non-functional
- ❌ Violates single surface architecture
- ❌ Breaks user flow: "search → click → view details"

### After Fix:
- ✅ Users can click part → ContextPanel opens
- ✅ Single surface maintained (no navigation)
- ✅ Full part details visible with actions
- ✅ External deep links still work
- ✅ Architecture matches vision

### Severity
**CRITICAL** - This is a **blocker for production**:
1. Core user journey is broken (search → view part)
2. Makes Parts Lens completely unusable
3. No workaround available for users

---

## Related Issues

### Same Bug Affects Other Entity Types

The navigation approach is used for ALL entity types:
- ❌ `/work-orders/${id}` - should use ContextPanel
- ❌ `/equipment/${id}` - should use ContextPanel
- ❌ `/faults/${id}` - should use ContextPanel
- ❌ `/documents/${id}` - might be correct (needs review)

**All should be fixed** to use `showContext()` for consistency.

---

## Implementation Checklist

### Immediate Fix (Parts Lens):
- [ ] Update `SpotlightSearch.tsx` handleResultOpen to use `showContext()`
- [ ] Test part click → ContextPanel opens
- [ ] Test part details display correctly
- [ ] Test action buttons work
- [ ] Test RBAC filtering (Captain vs Crew)

### Extended Fix (All Lenses):
- [ ] Update work orders to use ContextPanel
- [ ] Update equipment to use ContextPanel
- [ ] Update faults to use ContextPanel
- [ ] Document which pages are for external deep links only
- [ ] Add internal navigation guards to full-page views

### Testing:
- [ ] E2E test: Search → Click → ContextPanel opens
- [ ] E2E test: URL stays at `/` (no navigation)
- [ ] E2E test: External deep links still work
- [ ] E2E test: All entity types open in ContextPanel

---

## Estimated Effort

**Fix Time:** 30 minutes
- Change 10 lines in `SpotlightSearch.tsx`
- Test locally

**Testing Time:** 1 hour
- Test all entity types
- Test RBAC
- Test external deep links

**Total:** 1.5 hours to fix critical blocker

---

## Summary

**What's Broken:**
- Clicking part tries to navigate to `/parts/${id}`
- Breaks single surface design
- Makes Parts Lens unusable

**Why It's Broken:**
- Code uses `router.push()` for navigation
- Should use `showContext()` for ContextPanel
- Full-page routes are for external deep links only

**What Exists:**
- ✅ `showContext()` method in SurfaceContext
- ✅ ContextPanel renders PartCard correctly
- ✅ All infrastructure is built

**The Fix:**
- Replace `router.push(targetRoute)`
- With `showContext(entityType, entityId, metadata)`
- 10 lines of code change

**Impact:**
- CRITICAL blocker for production
- Fixes core user journey (search → view details)
- Enables Parts Lens functionality

---

**Recommendation:** Fix this IMMEDIATELY before any other testing. Without this, users cannot use the Parts Lens at all.
