# Receiving Lens - Issues and Improvements

## Critical Issues

### 1. Backend Payload Verification Needed ❗

**Problem**: Frontend assumes backend returns `item_names` array in receiving results.

**Current Assumption**:
```json
{
  "metadata": {
    "item_names": ["Racor Fuel Filter Element 2040PM", "..."]
  }
}
```

**Reality Check**: The `pms_receiving` table schema doesn't have an `item_names` column. Item names are stored in `pms_receiving_items` table separately.

**Impact**:
- Item search filter will not work if backend doesn't construct item_names array
- Results will not show item preview in list view

**Fix Required**:
Backend must aggregate item descriptions from `pms_receiving_items` and include as `item_names` in search results:

```python
# In receiving_handlers.py or prepare stage
query = """
  SELECT
    r.*,
    ARRAY_AGG(i.description) as item_names
  FROM pms_receiving r
  LEFT JOIN pms_receiving_items i ON i.receiving_id = r.id
  GROUP BY r.id
"""
```

**Verification**: Test query "deliveries with fuel filter" and check if results are filtered correctly.

---

### 2. Microactions Not Registered for Receiving Lens ❗

**Problem**: Actions array may be empty if receiving_lens is not registered in MicroactionRegistry.

**Current Code** (pipeline_v1.py:879-895):
```python
def _get_lens_name_from_source_table(self, source_table: str) -> Optional[str]:
    table_to_lens = {
        'pms_parts': 'part_lens',
        'receiving': 'receiving_lens',  # <-- Is this working?
        ...
    }
```

**Impact**:
- No action buttons in ReceivingCard
- Users cannot view receiving history or accept/reject deliveries from UI

**Fix Required**:
1. Verify `receiving_lens` is registered in microaction registry
2. Verify microactions are defined for receiving entity type
3. Check logs for microaction enrichment errors

**Verification**:
```bash
# Check if receiving microactions are registered
grep -r "receiving_lens" apps/api/microactions/
```

---

### 3. View Items Not Implemented ⚠️

**Problem**: `handleViewReceivingItems` shows placeholder toast instead of actual items list.

**Current Code**:
```typescript
const handleViewReceivingItems = useCallback(async (receivingId: string) => {
  console.log('[SpotlightSearch] View items for receiving:', receivingId);
  toast.info('View items feature coming soon');  // <-- Placeholder
}, []);
```

**Impact**:
- Users cannot see line item details from search results
- "View Items" button appears but does nothing useful

**Fix Required**:
Create ItemsListModal component or expand ReceivingCard to show items inline:

```typescript
const handleViewReceivingItems = useCallback(async (receivingId: string) => {
  // Option 1: Open modal with items
  const items = await fetchReceivingItems(receivingId);
  openItemsModal(items);

  // Option 2: Open ContextPanel with items tab
  await createSituation({
    entity_type: 'receiving',
    entity_id: receivingId,
    domain: 'inventory',
    initial_state: 'ACTIVE',
    metadata: { activeTab: 'items' },
  });
}, []);
```

---

## Type Safety Issues

### 4. Loose Typing in receivingResults 🔧

**Problem**: Using `any[]` for receiving results instead of proper interface.

**Current Code**:
```typescript
const { receivingResults, otherResults } = useMemo(() => {
  const receiving: any[] = [];  // <-- any[]
  // ...
}, [results]);
```

**Impact**:
- No TypeScript autocomplete
- No compile-time error checking
- Harder to maintain

**Fix Required**:
Define proper interface in `/apps/web/src/types/receiving.ts`:

```typescript
export interface ReceivingResult {
  id: string;
  vendor_name?: string;
  vendor_reference?: string;
  status: 'draft' | 'in_review' | 'accepted' | 'rejected';
  received_date?: string;
  total?: number;
  currency?: string;
  item_names?: string[];
  linked_work_order_id?: string;
  notes?: string;
  received_by?: string;
  actions?: MicroAction[];
}
```

Then use in SpotlightSearch:
```typescript
const receiving: ReceivingResult[] = [];
```

---

### 5. Actions Type Not Defined 🔧

**Problem**: Actions are typed as `any[]` instead of proper MicroAction type.

**Current Code**:
```typescript
actions: result.metadata?.actions as any[] | undefined,
```

**Fix Required**:
```typescript
import type { MicroAction } from '@/types/actions';

actions: (result.metadata?.actions as MicroAction[] | undefined) || [],
```

---

## Error Handling

### 6. No Error Feedback on Situation Creation Failure 🔧

**Problem**: If `createSituation` fails, user gets no feedback.

**Current Code**:
```typescript
const handleReceivingClick = useCallback(async (receivingResult: any) => {
  // ...
  await createSituation({ ... });  // <-- No try/catch
}, [createSituation, ...]);
```

**Impact**:
- Silent failures confuse users
- Hard to debug issues

**Fix Required**:
```typescript
const handleReceivingClick = useCallback(async (receivingResult: any) => {
  try {
    const entityType = mapResultTypeToEntityType('receiving');
    const domain = mapEntityTypeToDomain(entityType);

    await createSituation({
      entity_type: entityType,
      entity_id: receivingResult.id,
      domain,
      initial_state: 'ACTIVE',
      metadata: { ...receivingResult },
    });
  } catch (error) {
    console.error('[SpotlightSearch] Failed to open receiving detail:', error);
    toast.error('Failed to open receiving detail', {
      description: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}, [createSituation, mapResultTypeToEntityType, mapEntityTypeToDomain]);
```

---

### 7. No Loading State for ReceivingResultsList 🔧

**Problem**: If receiving results take time to render, no loading indicator shown.

**Current Code**:
```typescript
{receivingResults.length > 0 && (
  <ReceivingResultsList ... />  // <-- Renders immediately
)}
```

**Impact**:
- Poor UX on large result sets
- Looks like results are incomplete

**Fix Required**:
Add loading prop to ReceivingResultsList:

```typescript
<ReceivingResultsList
  results={receivingResults}
  isLoading={isLoading || isStreaming}
  onResultClick={handleReceivingClick}
  onViewItems={handleViewReceivingItems}
/>
```

Then in ReceivingResultsList component, show skeleton loader when loading.

---

## Performance

### 8. Results Separation Runs on Every Render 🔧

**Problem**: useMemo dependencies might cause unnecessary re-separation.

**Current Code**:
```typescript
const { receivingResults, otherResults } = useMemo(() => {
  // Heavy separation logic
}, [results]);  // Re-runs every time results change
```

**Impact**:
- Extra work on streaming search updates
- Potential UI jank

**Fix Required**:
Optimize by checking if results actually changed:

```typescript
const { receivingResults, otherResults } = useMemo(() => {
  // Only re-compute if results array changed
  const receiving: ReceivingResult[] = [];
  const others: SpotlightResult[] = [];

  // ... separation logic ...

  return { receivingResults: receiving, otherResults: others };
}, [results]); // This is fine, but consider deep comparison if results are stable
```

Actually, this is probably fine. The memoization is already optimal.

---

## Missing Features

### 9. No Inline Quick Actions 💡

**Problem**: Users must open ContextPanel to accept/reject deliveries.

**Suggested Enhancement**:
Add quick accept/reject buttons in ReceivingResultsList for Captain/Manager role:

```typescript
// In ReceivingResultsList.tsx
{user?.role === 'Captain' || user?.role === 'Manager' ? (
  <div className="flex gap-1">
    <button
      onClick={(e) => {
        e.stopPropagation();
        onQuickAccept(result.id);
      }}
      className="px-2 py-1 text-xs bg-green-600 text-white rounded"
    >
      Accept
    </button>
    <button
      onClick={(e) => {
        e.stopPropagation();
        onQuickReject(result.id);
      }}
      className="px-2 py-1 text-xs bg-red-600 text-white rounded"
    >
      Reject
    </button>
  </div>
) : null}
```

---

### 10. No Document Preview 💡

**Problem**: ReceivingCard doesn't show attached invoices/photos.

**Suggested Enhancement**:
Show document thumbnails in ReceivingCard:

```typescript
// In ReceivingCard.tsx
{receiving.documents && receiving.documents.length > 0 && (
  <div className="mt-3">
    <p className="text-sm font-medium text-muted-foreground mb-2">
      Attached Documents ({receiving.documents.length})
    </p>
    <div className="grid grid-cols-3 gap-2">
      {receiving.documents.map((doc) => (
        <DocumentThumbnail key={doc.id} document={doc} />
      ))}
    </div>
  </div>
)}
```

---

### 11. No Status Transition History 💡

**Problem**: Users can't see receiving history timeline.

**Suggested Enhancement**:
Add timeline view showing:
- Created (draft) → In Review → Accepted
- Who performed each transition
- When transitions occurred

---

## Testing Gaps

### 12. No Automated Tests ⚠️

**Problem**: No unit or integration tests for receiving lens frontend.

**Required Tests**:

1. **Unit Tests** (`ReceivingResultsList.test.tsx`):
   ```typescript
   describe('ReceivingResultsList', () => {
     it('renders status filter chips', () => { ... });
     it('filters by status', () => { ... });
     it('filters by item name', () => { ... });
     it('calls onResultClick when result clicked', () => { ... });
   });
   ```

2. **Integration Tests** (`SpotlightSearch.test.tsx`):
   ```typescript
   describe('SpotlightSearch - Receiving Lens', () => {
     it('detects receiving results', () => { ... });
     it('separates receiving from other results', () => { ... });
     it('opens ContextPanel on click', () => { ... });
   });
   ```

3. **E2E Tests** (Playwright/Cypress):
   ```typescript
   test('search and view receiving detail', async () => {
     await page.fill('[data-testid="search-input"]', 'accepted deliveries');
     await page.click('[data-testid="receiving-result-0"]');
     await expect(page.locator('[data-testid="context-panel-receiving-card"]')).toBeVisible();
   });
   ```

---

## Documentation Gaps

### 13. No Inline Code Comments 📝

**Problem**: Complex logic has no explanatory comments.

**Example - Add Comments**:
```typescript
// Detect and separate receiving lens results from generic results
// Backend returns source_table: 'receiving' or 'pms_receiving' for receiving records
const { receivingResults, otherResults } = useMemo(() => {
  const receiving: ReceivingResult[] = [];
  const others: SpotlightResult[] = [];

  results.forEach((result) => {
    // Check if result is from receiving lens by examining source_table or type field
    const sourceTable = result.metadata?.source_table || result.type;

    if (sourceTable === 'receiving' || sourceTable === 'pms_receiving') {
      // Transform API result to ReceivingResult format for ReceivingResultsList component
      const receivingResult = {
        id: result.id,
        // Extract vendor info from metadata
        vendor_name: result.metadata?.vendor_name as string | undefined,
        // ... etc
      };
      receiving.push(receivingResult);
    } else {
      // Keep non-receiving results for generic rendering
      others.push(result);
    }
  });

  return { receivingResults: receiving, otherResults: others };
}, [results]);
```

---

## Priority Order

### 🔴 Critical (Must Fix Before Production)
1. Backend payload verification (item_names)
2. Microactions registration verification
3. Type safety (proper interfaces)

### 🟡 High Priority (Should Fix Soon)
4. View Items implementation
5. Error handling and feedback
6. Automated tests

### 🟢 Nice to Have (Future Enhancements)
7. Inline quick actions
8. Document preview
9. Status transition history
10. Performance optimizations
11. Better code comments

---

## Verification Checklist

Before marking receiving lens as production-ready:

- [ ] Backend returns item_names array in search results
- [ ] Microactions are registered and enriched for receiving results
- [ ] Status filters work correctly (All, Draft, In Review, Accepted, Rejected)
- [ ] Item search filters results by item_names
- [ ] Clicking result opens ContextPanel with ReceivingCard
- [ ] Actions buttons appear and respect role permissions (HOD+, Captain/Manager)
- [ ] Accept Receiving action works (Captain/Manager only)
- [ ] Reject Receiving action works (HOD+ only)
- [ ] View Receiving History shows full detail
- [ ] Error cases handled gracefully (no data, network error, permission denied)
- [ ] TypeScript compiles without errors
- [ ] No console errors in browser
- [ ] Works on mobile and desktop viewports
- [ ] Accessible (keyboard navigation, screen readers)
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E smoke test passes

---

**Status**: ⚠️ Integration Complete, Issues Identified

**Next Action**: Verify backend payload structure and microactions registration

**Last Updated**: 2026-02-07
