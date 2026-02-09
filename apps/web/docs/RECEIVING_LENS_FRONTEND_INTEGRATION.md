# Receiving Lens - Frontend Integration Complete

## Overview

Receiving lens results are now properly integrated into SpotlightSearch with specialized rendering, status filters, item search, and full ContextPanel support.

## Components Modified

### 1. `/apps/web/src/types/situation.ts`

**Change**: Added 'receiving' to EntityType

```typescript
export type EntityType =
  | 'document'
  | 'equipment'
  | 'part'
  | 'work_order'
  | 'fault'
  | 'location'
  | 'person'
  | 'inventory'
  | 'email_thread'
  | 'receiving';  // <-- ADDED
```

**Why**: Allows receiving entities to create proper situations and be routed through SituationRouter.

### 2. `/apps/web/src/components/spotlight/SpotlightSearch.tsx`

**Changes**:

1. **Import ReceivingResultsList**
   ```typescript
   import { ReceivingResultsList } from '@/components/receiving/ReceivingResultsList';
   ```

2. **Detect and Separate Receiving Results**
   ```typescript
   const { receivingResults, otherResults } = useMemo(() => {
     // Check source_table: 'receiving' or 'pms_receiving'
     // Transform to ReceivingResult format
     // Preserve actions from API result
   }, [results]);
   ```

3. **Updated Type Mapping**
   ```typescript
   const mapResultTypeToEntityType = useCallback((type: string): EntityType => {
     // ... existing mappings ...
     if (type.includes('receiving') || type === 'pms_receiving') return 'receiving';
     // ...
   }, []);

   const mapEntityTypeToDomain = useCallback((entityType: EntityType): SituationDomain => {
     // ... existing mappings ...
     if (entityType === 'receiving') return 'inventory';  // Receiving is inventory domain
     // ...
   }, []);
   ```

4. **Handle Receiving Result Click**
   ```typescript
   const handleReceivingClick = useCallback(async (receivingResult: any) => {
     const entityType = mapResultTypeToEntityType('receiving');
     const domain = mapEntityTypeToDomain(entityType);

     await createSituation({
       entity_type: entityType,
       entity_id: receivingResult.id,
       domain,
       initial_state: 'ACTIVE',
       metadata: { ...receivingResult, actions: receivingResult.actions || [] },
     });
   }, [createSituation, mapResultTypeToEntityType, mapEntityTypeToDomain]);
   ```

5. **Render ReceivingResultsList**
   ```typescript
   {hasResults && (
     <div className="py-1.5" data-testid="search-results">
       {/* Receiving Lens Results - Specialized rendering */}
       {receivingResults.length > 0 && (
         <div className="mb-4">
           <ReceivingResultsList
             results={receivingResults}
             onResultClick={handleReceivingClick}
             onViewItems={handleViewReceivingItems}
           />
         </div>
       )}

       {/* Other Results - Generic rendering */}
       {otherResults.map((result, index) => (
         <SpotlightResultRow ... />
       ))}
     </div>
   )}
   ```

### 3. `/apps/web/src/app/app/ContextPanel.tsx`

**Change**: Pass actions to ReceivingCard

```typescript
case 'receiving':
  const receivingData = { ... };
  return (
    <div data-testid="context-panel-receiving-card">
      <ReceivingCard
        receiving={receivingData}
        actions={data.actions as any[] | undefined}  // <-- ADDED
      />
    </div>
  );
```

**Why**: Enables action buttons in ReceivingCard detail view with role-based permissions.

## Complete Flow

### 1. User Search
```
User types: "show me accepted deliveries"
```

### 2. Backend Response
```json
{
  "results": [
    {
      "primary_id": "receiving-uuid-123",
      "type": "receiving",
      "source_table": "pms_receiving",
      "metadata": {
        "vendor_name": "Racor",
        "vendor_reference": "ACCEPT-TEST-b1679bd7",
        "status": "accepted",
        "received_date": "2026-01-28",
        "total": 1375.00,
        "currency": "USD",
        "item_names": ["Racor Fuel Filter Element 2040PM", "Racor Filter Housing Assembly 1000FH"],
        "notes": "Annual fuel system maintenance parts",
        "received_by": "Chief Engineer",
        "actions": ["view_receiving_history", "view_receiving_items"]
      }
    }
  ]
}
```

### 3. Frontend Detection
- SpotlightSearch detects `source_table: 'receiving'`
- Separates receiving results from other results
- Transforms to ReceivingResult format, preserving actions

### 4. Specialized Rendering
- ReceivingResultsList component renders with:
  - Status filter chips (All, Draft, In Review, Accepted, Rejected)
  - Item search filter (search by item_names)
  - Table with vendor, reference, status pill, date, total
  - Action buttons (View, View Items)

### 5. User Clicks Result
- `handleReceivingClick` fired
- Creates ACTIVE situation with entity_type: 'receiving'
- SituationRouter routes to ContextPanel

### 6. ContextPanel Display
- Detects entity_type: 'receiving'
- Renders ReceivingCard with:
  - Vendor name
  - Status badge with icon (Accepted, Rejected, In Review, Draft)
  - Reference number
  - Received date
  - Total amount
  - Notes
  - Action buttons (with role-based visibility)

### 7. Action Execution
- ActionButton components handle:
  - Role-based permission checks
  - Backend API calls via executeAction
  - Success/error feedback via toast
  - Context refresh after mutations

## Backend Integration Points

### Required Backend Response Fields

For receiving lens to work correctly, backend must return:

```typescript
{
  type: 'receiving' | 'pms_receiving',  // For lens detection
  primary_id: string,                    // Receiving record ID
  metadata: {
    vendor_name?: string,
    vendor_reference?: string,           // PO/invoice number
    status: 'draft' | 'in_review' | 'accepted' | 'rejected',
    received_date?: string,              // ISO date
    total?: number,
    currency?: string,
    item_names?: string[],               // For item search filter
    linked_work_order_id?: string,
    notes?: string,
    received_by?: string,
    actions?: string[],                  // MicroAction IDs
  }
}
```

### Backend Handlers

From `/apps/api/handlers/receiving_handlers.py`:

- `view_receiving_history` (READ) - All crew
- `create_receiving` (MUTATE) - HOD+ role
- `accept_receiving` (SIGNED) - Captain/Manager only
- `reject_receiving` (MUTATE) - HOD+ role
- `add_receiving_item` (MUTATE) - HOD+ role
- `attach_receiving_image_with_comment` (MUTATE) - HOD+ role

### Lens Anchors

Backend should detect receiving queries via anchors like:
- "accepted deliveries"
- "draft receiving"
- "deliveries with fuel filter"
- "receiving records in review"

## Testing

### Manual Test Flow

1. **Start web app**
   ```bash
   cd apps/web && npm run dev
   ```

2. **Open SpotlightSearch** (Cmd+K or Ctrl+K)

3. **Test queries**:
   ```
   - "show me accepted deliveries"
   - "draft receiving records"
   - "deliveries from Racor"
   - "receiving records with fuel filter"
   - "what came in on January 28th"
   ```

4. **Verify rendering**:
   - Status filter chips displayed
   - Item search filter works
   - Results show vendor, reference, status, date, total
   - Clicking result opens ContextPanel with ReceivingCard

5. **Test actions**:
   - View Delivery (opens detail)
   - View Items (shows items list)
   - Accept Receiving (Captain/Manager only)
   - Reject Receiving (HOD+ only)

### Expected Behavior

**Status Filters**:
- Clicking "Draft" filters to only draft records
- Clicking "Accepted" filters to only accepted records
- Status counts update dynamically
- "All" shows unfiltered results

**Item Search**:
- Typing "fuel filter" shows only records with items containing that text
- Case-insensitive matching
- Combines with status filter

**ContextPanel**:
- Receiving detail shows all fields
- Actions filtered by user role
- Status badge shows correct color and icon
- Dates formatted as MMM DD, YYYY
- Currency displayed correctly

## Known Limitations

1. **View Items Action**: Currently shows toast "View items feature coming soon" - needs modal/panel implementation
2. **Backend item_names**: Assumes backend constructs item_names array from pms_receiving_items - verify this is configured
3. **Actions Array**: Assumes backend enriches results with actions via MicroactionRegistry - verify receiving_lens is registered

## Next Steps

1. **Implement View Items Modal**: Show line items detail when "View Items" clicked
2. **Add Inline Actions**: Quick accept/reject buttons in results list (Captain/Manager only)
3. **Add Document Preview**: Show attached invoices/photos in ContextPanel
4. **Add Timeline**: Show receiving history (created → reviewed → accepted)
5. **Test with Real Data**: Verify with actual receiving records from database

## Files Changed

- `/apps/web/src/types/situation.ts` - Added 'receiving' EntityType
- `/apps/web/src/components/spotlight/SpotlightSearch.tsx` - Integrated ReceivingResultsList
- `/apps/web/src/app/app/ContextPanel.tsx` - Pass actions to ReceivingCard
- `/apps/web/src/components/receiving/ReceivingResultsList.tsx` - Created (previous work)
- `/apps/web/src/components/cards/ReceivingCard.tsx` - Already existed, no changes needed

## Backend Files (Reference)

- `/apps/api/handlers/receiving_handlers.py` - Receiving action handlers
- `/apps/api/pipeline_v1.py` - Lens detection and results enrichment
- `/apps/api/tests/test_receiving_lens_queries.py` - 25 ground truth tests

---

**Status**: ✅ Integration Complete - Ready for Testing

**Last Updated**: 2026-02-07
**Author**: Claude Opus 4.5
