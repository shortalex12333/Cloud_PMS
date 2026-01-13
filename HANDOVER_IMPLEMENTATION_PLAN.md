# Handover Generation Implementation Plan

**Date:** 2026-01-11
**Objective:** Implement immediate, context-aware handover capture as specified in cluster_05_HANDOVER_COMMUNICATION

---

## Current State Analysis

### ✅ What EXISTS:

1. **Backend (Fully Implemented)**
   - `apps/api/handlers/handover_handlers.py`
     - `add_to_handover_prefill()` - Fetches entity data, generates context
     - `add_to_handover_execute()` - Creates handover entry with audit trail

2. **API Routes (Functional)**
   - `GET /v1/actions/add_to_handover/prefill?entity_type={type}&entity_id={id}`
   - `POST /v1/actions/execute` with `action=add_to_handover`

3. **Database Schema (Deployed)**
   - Table: `public.handover` (note: may be `pms_handover` depending on migration)
   - Columns: id, yacht_id, entity_type, entity_id, summary_text, category, priority, added_by, added_at
   - Indexes: yacht_id, entity, category, priority

4. **Frontend Modal (Wrong Use Case)**
   - `apps/web/src/components/modals/AddToHandoverModal.tsx`
   - **Problem:** This is for LINKING multiple entities to existing handover (Phase 4 feature)
   - **Not aligned with spec:** Should be single-item, immediate capture from entity pages

### ❌ What's MISSING:

1. **Proper Frontend Modal**
   - Need NEW component: `AddToHandoverQuickModal.tsx`
   - Single-item, pre-filled form
   - Cursor starts in Details field for user note
   - Lightweight commit (no preview)

2. **Action Integration**
   - Add "Add to Handover" to entity action menus (Fault pages, Equipment pages, etc.)
   - Update `MicroActions.tsx` handler (currently expects handover_id, which is wrong)
   - Wire to new modal component

3. **Action Offering Logic**
   - Add to action registry/offering rules
   - Should appear on: fault, equipment, work_order, document_chunk pages
   - Should also support direct query: "add to handover"

4. **Display/Briefing View**
   - Need to display handover items somewhere
   - Likely `/briefing` page or dashboard module
   - Show: recent handover items for current yacht, sorted by priority/time

---

## Implementation Plan

### Phase 1: Fix Frontend Modal (Priority: P0)

**Goal:** Create spec-compliant modal for immediate handover capture

#### 1.1: Create New Modal Component

**File:** `apps/web/src/components/modals/AddToHandoverQuickModal.tsx`

**Features:**
- Accept props: `entityType`, `entityId`, `open`, `onOpenChange`, `onSuccess`
- On mount: call `/v1/actions/add_to_handover/prefill` to get context
- Pre-fill form fields:
  - Title (read-only or editable?)
  - Category (dropdown, inferred from entity)
  - Priority (dropdown, defaults from prefill)
  - Details (textarea with pre-filled summary + cursor for user note)
- On submit: call `/v1/actions/execute` with action=add_to_handover
- Lightweight: No preview, immediate commit
- Success: Toast notification "Added to handover"

**Schema (Zod):**
```typescript
const addToHandoverQuickSchema = z.object({
  entity_type: z.enum(['fault', 'work_order', 'equipment', 'document_chunk', 'part']),
  entity_id: z.string().uuid(),
  title: z.string().min(1, "Title required"),
  category: z.enum(['ongoing_fault', 'work_in_progress', 'important_info', 'equipment_status', 'general']),
  summary_text: z.string().min(10, "Add your note (min 10 chars)").max(2000),
  priority: z.enum(['low', 'normal', 'high', 'urgent']),
});
```

**Key Design Choices:**
- **Title:** Pre-filled from entity (e.g., "Generator 2 - MTU-OVHT-01"), allow edit
- **Category:** Show dropdown but default to inferred value
- **Details:** Pre-filled summary ABOVE cursor position, user adds note BELOW
  ```
  [Pre-filled context from system]
  Coolant temp high - occurred 8 times in last 30 days.

  [Cursor starts here - user adds their note]
  ```
- **Priority:** Dropdown, defaults to inferred from severity

**API Calls:**
1. On mount: `GET /v1/actions/add_to_handover/prefill?entity_type=fault&entity_id=abc-123`
2. On submit: `POST /v1/actions/execute` with:
   ```json
   {
     "action": "add_to_handover",
     "entity_type": "fault",
     "entity_id": "abc-123",
     "summary_text": "Coolant temp high...\n\nTopped up coolant by 2L. Monitor in 2 hours.",
     "category": "ongoing_fault",
     "priority": "normal"
   }
   ```

#### 1.2: Update MicroActions Handler

**File:** `apps/web/src/components/MicroActions.tsx`

**Current code (lines 116-125):**
```typescript
case 'add_to_handover':
  // WRONG: expects handover_id in context
  if (!context.handover_id) {
    setError('No handover selected...');
    return;
  }
  await executeAction('add_to_handover', context, {});
  alert('Added to handover successfully!');
  break;
```

**Fix:**
```typescript
case 'add_to_handover':
  // Open quick modal with entity context
  // TODO: Pass modal open state via props or use global modal manager
  // For now, show a modal trigger
  const entityType = result.type; // 'fault', 'equipment', etc.
  const entityId = result.id;

  // Open AddToHandoverQuickModal
  // This requires modal state management - see Phase 1.3
  break;
```

#### 1.3: Modal State Management

**Options:**

**Option A: Local State in Parent Components**
- Each entity page (FaultCard, EquipmentCard, etc.) manages modal state
- Pass `setShowHandoverModal(true)` from action button
- Simple but repetitive

**Option B: Global Modal Manager (Recommended)**
- Create context: `ModalContext` with `openHandoverModal(entityType, entityId)`
- Centralized modal rendering
- Cleaner, reusable

**Recommendation:** Use Option B with Zustand or Context API

**Implementation:**
```typescript
// apps/web/src/contexts/ModalContext.tsx
export const ModalProvider = ({ children }) => {
  const [handoverModal, setHandoverModal] = useState({ open: false, entityType: null, entityId: null });

  const openHandoverModal = (entityType, entityId) => {
    setHandoverModal({ open: true, entityType, entityId });
  };

  return (
    <ModalContext.Provider value={{ openHandoverModal }}>
      {children}
      <AddToHandoverQuickModal
        open={handoverModal.open}
        entityType={handoverModal.entityType}
        entityId={handoverModal.entityId}
        onOpenChange={(open) => setHandoverModal({ ...handoverModal, open })}
      />
    </ModalContext.Provider>
  );
};
```

---

### Phase 2: Action Offering Integration (Priority: P0)

**Goal:** Make "Add to Handover" appear in correct contexts

#### 2.1: Add to Entity Action Menus

**Locations:**
1. **Fault Card** (`apps/web/src/components/cards/FaultCard.tsx`)
   - Add action button: "Add to Handover"
   - On click: `openHandoverModal('fault', fault.id)`

2. **Equipment Pages** (find equipment card component)
   - Same pattern

3. **Work Order Pages**
   - Same pattern

4. **Document Viewer** (`apps/web/src/components/document/DocumentViewer.tsx`)
   - Add to actions menu
   - Pass `document_chunk` as entity type

#### 2.2: Update Action Registry

**File:** Check `apps/api/actions/action_registry.py` or similar

Ensure `add_to_handover` is registered with:
- **Entry conditions:** fault, equipment, work_order, document_chunk, part
- **Context-free:** Also available from direct query
- **Priority:** P0
- **Type:** MUTATE

#### 2.3: Search Integration

**If user queries:** "add to handover" (context-free)

**Behavior:**
- Action appears in search results
- Opens modal with NO entity context
- Form fields empty (or minimal prefill)
- User manually enters title, category, details

---

### Phase 3: Display Handover Items (Priority: P1)

**Goal:** Users must be able to VIEW handover items

#### 3.1: Briefing Page Enhancement

**File:** `apps/web/src/app/briefing/BriefingContent.tsx`

**Add section: "Shift Handover"**

**Features:**
- Fetch handover items: `GET /v1/handover?yacht_id={id}&limit=20&sort=priority,added_at`
  - Note: This endpoint may not exist yet - see Phase 3.2
- Display as cards:
  - Title
  - Category badge (e.g., "Ongoing Fault", "Important Info")
  - Summary text (truncated with "Read more")
  - Priority indicator
  - Added by (name) + timestamp
  - Link to source entity (e.g., "View Fault →")
- Group by category or priority
- Filter: Show only unacknowledged (if acknowledgment feature exists)

#### 3.2: API Endpoint for Fetching Handover Items

**File:** `apps/api/routes/p0_actions_routes.py` or new `handover_routes.py`

**Add route:**
```python
@router.get("/handover")
async def get_handover_items(
    yacht_id: str,
    limit: int = 20,
    category: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    Get handover items for yacht, sorted by priority and recency
    """
    # Validate JWT
    # Query pms_handover table
    # Join with users table to get added_by name
    # Return items
```

**Response:**
```json
{
  "status": "success",
  "items": [
    {
      "id": "uuid",
      "entity_type": "fault",
      "entity_id": "fault-uuid",
      "title": "Generator 2 - MTU-OVHT-01",
      "summary_text": "Coolant temp high...\n\nTopped up coolant by 2L...",
      "category": "ongoing_fault",
      "priority": "high",
      "added_by": "John Smith",
      "added_at": "2026-01-11T14:30:00Z"
    }
  ]
}
```

#### 3.3: Handover Card Component

**File:** `apps/web/src/components/cards/HandoverCard.tsx`

**Display:**
- Category icon + badge
- Title (bold)
- Summary (truncated, expandable)
- Metadata: Priority, Added by, Timestamp
- Action: "View {entity_type}" → Navigate to source entity

---

### Phase 4: Testing & Refinements (Priority: P2)

#### 4.1: Pre-fill Logic Testing

**Scenarios:**
1. Fault → Title should be "{equipment_name} - {fault_code}"
2. Work Order → Title should be "WO-{number} - {title}"
3. Equipment → Title should be equipment name
4. Document → Title should be "Manual Reference: {doc_title}"
5. Part → Title should be "{part_name} ({part_number})"

**Verify:**
- Category inference correct
- Priority defaults sensible
- Summary text includes key context

#### 4.2: Edge Cases

1. **Duplicate handover items:** Spec says duplicates allowed, but flag them
   - Backend already checks for existing entries (line 288-293 in handler)
   - Show warning in UI: "Similar handover item exists. Add anyway?"

2. **Missing entity:** If entity deleted before handover viewed
   - Handle gracefully in display (show "Entity not found")

3. **Empty/invalid user note:** Validation enforces min 10 chars
   - Ensure error message clear

#### 4.3: User Flow Testing

**Test Full Flow:**
1. Engineer viewing fault F-2024-089
2. Clicks "Add to Handover" in actions menu
3. Modal opens, pre-filled with fault context
4. Engineer adds note: "Topped up coolant, monitor temp"
5. Clicks "Add to Handover" → Success toast
6. Modal closes
7. Navigate to `/briefing`
8. See handover item in "Shift Handover" section
9. Next shift engineer sees it immediately

---

## Database Schema Verification

### Current Schema Check:

**Migration files found:**
1. `database/migrations/02_p0_actions_tables.sql` - Uses TEXT for priority
2. `database/migrations/02_p0_actions_tables_REVISED.sql` - Uses INTEGER for priority

**Issue:** Handler code (line 297) converts priority to integer:
```python
priority_value = {"low": 1, "normal": 2, "high": 3, "urgent": 4}.get(priority, 2)
```

**But insert (line 306) uses this integer:**
```python
"priority": priority_value,  # Integer
```

**While schema expects TEXT in 02_p0_actions_tables.sql**

**Action Required:** Verify which migration has been applied to production database

**Test Query:**
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'handover'
  AND column_name = 'priority';
```

**If TEXT:** Handler code needs fix (remove integer conversion)
**If INTEGER:** Schema is correct (REVISED migration applied)

---

## Pre-fill Logic Summary

Based on `handover_handlers.py` lines 68-214:

| Entity Type      | Title Format                          | Category         | Priority Logic                |
|------------------|---------------------------------------|------------------|-------------------------------|
| fault            | "{equipment_name} - {fault_code}"     | ongoing_fault    | critical → high, else normal  |
| work_order       | "WO-{number} - {title}"               | work_in_progress | From WO priority field        |
| equipment        | "{equipment_name}"                    | equipment_status | normal (default)              |
| document_chunk   | "Manual Reference: {doc_title}"       | important_info   | normal (default)              |
| part             | "{part_name} ({part_number})"         | general          | low_stock → high, else normal |

**Summary Text:**
- Fault: Includes description + occurrence count
- Work Order: Number, title, equipment, status, description
- Equipment: Name, manufacturer, model, location, status
- Document: Manufacturer, model, text snippet (500 chars)
- Part: Name, part number, category, stock status, location

---

## File Changes Summary

### New Files:
1. `apps/web/src/components/modals/AddToHandoverQuickModal.tsx` - Main modal
2. `apps/web/src/contexts/ModalContext.tsx` - Modal state management (optional)
3. `apps/web/src/components/cards/HandoverItemCard.tsx` - Display component
4. `apps/api/routes/handover_routes.py` - Fetch handover items endpoint (if needed)

### Modified Files:
1. `apps/web/src/components/MicroActions.tsx` - Fix add_to_handover handler
2. `apps/web/src/components/cards/FaultCard.tsx` - Add action button
3. `apps/web/src/app/briefing/BriefingContent.tsx` - Display handover items
4. `apps/web/src/components/modals/index.ts` - Export new modal
5. Potentially: Equipment card, Work Order card, Document viewer (add action buttons)

### Backend Changes:
- **Likely None** - Backend handlers and routes already functional
- **Possibly:** Add GET endpoint for fetching handover items (Phase 3.2)
- **Verify:** Database schema priority column type

---

## Guardrails from Specification

**What NOT to do (from spec lines 290-302):**

- ❌ No auto-adding items based on ML/importance scores
- ❌ No forced handover at shift end
- ❌ No "suggested handover items"
- ❌ No auto-categorization using ML (simple entity-based only)
- ❌ No blocking if handover not written
- ❌ No reminders/nudges
- ❌ No auto-emailing to next shift

**Core Principle:**
> "If a human didn't add it, it's not in handover."

---

## Success Metrics

**Feature is successful when:**

1. ✅ Engineer can add to handover from fault page in <5 clicks
2. ✅ Form pre-fills correctly 100% of the time
3. ✅ User only needs to type their note (everything else auto-filled)
4. ✅ Handover items visible on /briefing page
5. ✅ Next shift sees handover items immediately
6. ✅ Audit trail records WHO added WHAT WHEN
7. ✅ Zero auto-added items (human-only)

---

## Implementation Order (Recommended)

### Sprint 1 (P0 - Core Flow):
1. Create `AddToHandoverQuickModal.tsx`
2. Add action button to `FaultCard.tsx`
3. Fix `MicroActions.tsx` handler
4. Test full flow: Fault → Add to Handover → Success

### Sprint 2 (P0 - Display):
5. Create GET endpoint for handover items
6. Add "Shift Handover" section to `/briefing`
7. Create `HandoverItemCard.tsx`
8. Test: Create handover → See in briefing

### Sprint 3 (P1 - Expansion):
9. Add action to Equipment pages
10. Add action to Work Order pages
11. Add action to Document viewer
12. Add context-free (direct query) support

### Sprint 4 (P2 - Polish):
13. Edge case handling (duplicates, missing entities)
14. User testing and refinements
15. Documentation

---

## Open Questions

1. **Database Schema:** Which priority type is in production? (TEXT or INTEGER)
2. **Modal Management:** Use Zustand, Context API, or local state?
3. **Handover Acknowledgment:** Do items get "acknowledged" or "cleared"? (Not in spec)
4. **Display Location:** Is `/briefing` the right place? Or dashboard module?
5. **Direct Query:** How should context-free "add to handover" work in search?
6. **Existing Modal:** Should `AddToHandoverModal.tsx` be renamed/repurposed or kept separate?

---

## Next Steps

1. **Verify database schema** - Check priority column type
2. **Prototype `AddToHandoverQuickModal.tsx`** - Build core modal component
3. **Test prefill endpoint** - Call `/v1/actions/add_to_handover/prefill` manually
4. **Wire to FaultCard** - Add action button as proof of concept
5. **Create GET endpoint** - If not exists, add to fetch handover items
6. **Test end-to-end** - Full flow from fault page to briefing display

---

**END OF PLAN**
