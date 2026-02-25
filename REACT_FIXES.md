# React Runtime Fixes - Escape Key & Entity ID

## Issue Analysis

**Escape Key Handler:**
- ✅ Code is deployed: `data-visible` attribute exists in DOM
- ❌ Runtime fails: Escape key press doesn't hide panel
- **Root Cause**: Event listener dependency on `hideContext` which changes reference when `emailPanel.visible` changes, potentially causing stale closures or timing issues

**Entity ID Routing:**
- ✅ Code correctly maps `object_id → id` in useCelesteSearch (line 596, 742)
- ✅ SpotlightSearch uses `result.id` (line 208)
- ❌ Runtime fails: entityId is null in context panel
- **Root Cause**: Potential timing issue or state update not propagating

## Fixes

### Fix 1: ContextPanel.tsx - Stabilize hideContext with useRef

Replace lines 100-115 with:

```typescript
// Handle ESC key to close panel
// Use ref to avoid stale closure issues with hideContext
const hideContextRef = useRef(hideContext);
useEffect(() => {
  hideContextRef.current = hideContext;
}, [hideContext]);

useEffect(() => {
  if (!visible) return;

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      console.log('[ContextPanel] 🔑 Escape pressed, closing panel');
      e.preventDefault();
      e.stopPropagation();
      hideContextRef.current();
    }
  };

  // Use document instead of window to ensure global capture
  document.addEventListener('keydown', handleKeyDown, true);
  console.log('[ContextPanel] ✅ Escape listener attached');

  return () => {
    document.removeEventListener('keydown', handleKeyDown, true);
    console.log('[ContextPanel] ❌ Escape listener removed');
  };
}, [visible]); // Only depend on visible, not hideContext
```

### Fix 2: SurfaceContext.tsx - Stabilize hideContext callback

Replace lines 130-133 with:

```typescript
// Hide context panel
const hideContext = useCallback(() => {
  console.log('[SurfaceContext] 🚪 hideContext called');
  setContextPanel((prev) => {
    console.log('[SurfaceContext] Panel state before:', prev);
    return { visible: false, expanded: false };
  });
  setState((prevState) => {
    const newState = emailPanel.visible ? 'email-present' : 'search-dominant';
    console.log('[SurfaceContext] State transition:', prevState, '→', newState);
    return newState;
  });
}, []); // Remove emailPanel.visible from deps to stabilize reference
```

### Fix 3: SpotlightSearch.tsx - Defensive entity ID handling

Replace lines 557-559 with:

```typescript
if (surfaceContext) {
  const entityId = result.id;

  if (!entityId) {
    console.error('[SpotlightSearch] ❌ Missing entity ID for result:', result);
    return;
  }

  console.log('[SpotlightSearch] 📍 Opening in ContextPanel:', {
    entityType,
    entityId,
    resultId: result.id,
    hasMetadata: !!contextMetadata
  });

  surfaceContext.showContext(entityType, entityId, contextMetadata);
```

## Testing Commands

```bash
# Rebuild
cd apps/web && npm run build

# Test Escape key fix
npx playwright test e2e/shard-8-workorders/workorders.spec.ts -g "Escape key" --reporter=list

# Test entity ID fix
npx playwright test e2e/shard-10-parts/parts.spec.ts -g "entity" --reporter=list
```
