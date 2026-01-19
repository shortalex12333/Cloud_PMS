# FIXES APPLIED - 2026-01-18

## Summary

Fixed the **yacht_id propagation issue** that was causing all search functionality to send `yacht_id: null` to the backend.

---

## Root Cause

The system had **multiple disconnected auth contexts** that didn't share yacht_id correctly:

| Component | yacht_id Source (Before) | Status |
|-----------|--------------------------|--------|
| AuthContext | Bootstrap API | ✅ Correct |
| useCelesteSearch | `getYachtId()` → user_metadata | ❌ Returns NULL |
| useSituationState | `getYachtId()` → user_metadata | ❌ Returns NULL |
| NavigationContext | Internal state → placeholders | ❌ Returns 'placeholder-yacht-id' |

The `getYachtId()` function in `authHelpers.ts` was reading from `session.user.user_metadata.yacht_id` which is **NEVER populated**. The actual yacht_id was correctly stored in `AuthContext.user.yachtId` after the bootstrap API call.

---

## Fixes Applied

### 1. useCelesteSearch.ts

**Before:**
```typescript
export function useCelesteSearch() {
  // ...
  const yachtId = await getYachtId(); // Returns NULL
}
```

**After:**
```typescript
export function useCelesteSearch(yachtId: string | null = null) {
  // yachtId passed from caller (AuthContext)
}
```

Files modified:
- `apps/web/src/hooks/useCelesteSearch.ts`
- `apps/web/src/components/spotlight/SpotlightSearch.tsx`
- `apps/web/src/components/SearchBar.tsx`

### 2. useSituationState.ts

**Before:**
```typescript
export function useSituationState() {
  let yachtId = await getYachtId(); // Returns NULL
  const effectiveYachtId = yachtId || 'bootstrap-pending'; // Placeholder
}
```

**After:**
```typescript
export function useSituationState(yachtId: string | null = null) {
  // yachtId passed from caller (AuthContext)
  if (!yachtId) {
    console.warn('Cannot create situation: yachtId not yet available');
    return;
  }
}
```

### 3. NavigationContext.tsx

**Before:**
```typescript
const yachtId = state.yachtId || 'placeholder-yacht-id'; // Placeholder
const userId = state.userId || 'placeholder-user-id';
```

**After:**
```typescript
// Sync from AuthContext
const { user } = useAuth();

useEffect(() => {
  if (user?.yachtId && user?.id) {
    setState(prev => ({
      ...prev,
      yachtId: user.yachtId,
      userId: user.id,
    }));
  }
}, [user?.yachtId, user?.id]);

// In pushViewer:
if (!yachtId || !userId) {
  console.error('Cannot create context: missing yacht_id or user_id');
  return;
}
```

### 4. AddRelatedModal.tsx

**Before:**
```typescript
const yachtId = 'placeholder-yacht-id';
const userId = 'placeholder-user-id';
```

**After:**
```typescript
const { pushRelated, yachtId, userId } = useNavigationContext();

if (!yachtId || !userId) {
  setError('Authentication required. Please log in.');
  return;
}
```

---

## Architecture After Fix

```
User Login
    │
    ├─► Supabase Auth ───────────────────────────► Session created
    │
    ├─► AuthContext.handleSession() ────────────┐
    │                                           │
    │   POST /v1/bootstrap                      │
    │       │                                   │
    │       ▼                                   │
    │   Returns: yacht_id = "85fe1119..."       │
    │       │                                   │
    │       ▼                                   │
    │   AuthContext.user.yachtId = "85fe1119..." ◄──┘
    │
    │
User Types Search Query
    │
    ├─► SpotlightSearch
    │       │
    │       ├─► useAuth() → user.yachtId
    │       │
    │       ├─► useCelesteSearch(user?.yachtId)
    │       │       │
    │       │       ▼
    │       │   Payload: { auth: { yacht_id: "85fe1119..." } }  ✅
    │       │
    │       └─► useSituationState(user?.yachtId)
    │               │
    │               ▼
    │           situation.yacht_id = "85fe1119..."  ✅
    │
    │
User Opens Document
    │
    ├─► NavigationContext
    │       │
    │       ├─► useAuth() → user.yachtId synced to state
    │       │
    │       └─► createNavigationContext({ yacht_id: "85fe1119..." })  ✅
```

---

## Verification

- TypeScript compiles without errors: `npx tsc --noEmit` ✅
- No more placeholder IDs in source: `grep -r "placeholder-yacht-id"` returns 0 matches ✅
- AuthContext is now the single source of truth for yacht_id ✅

---

## Remaining Tasks

1. **Deploy and test on production** - Verify search returns results with proper yacht_id
2. **Run E2E tests** - Verify the full flow works end-to-end
3. **Verify RLS** - Confirm users can only access their yacht's data
4. **Test cross-yacht access** - Confirm it's denied

---

## Files Changed

1. `apps/web/src/hooks/useCelesteSearch.ts`
2. `apps/web/src/hooks/useSituationState.ts`
3. `apps/web/src/contexts/NavigationContext.tsx`
4. `apps/web/src/components/context-nav/AddRelatedModal.tsx`
5. `apps/web/src/components/spotlight/SpotlightSearch.tsx`
6. `apps/web/src/components/SearchBar.tsx`
