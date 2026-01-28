# Customer Journey Framework

**Purpose:** Document HOW users interact with CelesteOS - from query → action → confirmation
**Date Created:** 2026-01-22
**Scope:** All 64 microactions
**Status:** Living document - update as UX evolves

---

## Why This Document Exists

**Problem:** Testing actions in isolation (direct API calls) misses the reality of how users actually trigger them.

**Solution:** Document the complete customer journey:
1. What query does the user type?
2. What appears on screen?
3. What buttons/forms do they see?
4. What happens when they click?
5. What validation occurs?
6. What confirmation do they get?
7. What are the variants/edge cases?

**Use This To:**
- Design realistic E2E tests
- Understand guard rails and validation
- Test natural language query detection
- Verify error messages users actually see
- Identify gaps in UX flows

---

## CelesteOS UI Architecture

### Single Surface Paradigm

**URL:** `/app` (only one page)
**Layout:**
```
┌─────────────────────────────────────────────────┐
│                                                 │
│         [Spotlight Search Bar]                  │
│         ▼ Action Buttons (if NL detected)      │
│         ▼ Search Results (if query typed)      │
│                                                 │
│                                   ┌───────────┐ │
│                                   │  Context  │ │
│                                   │   Panel   │ │
│                                   │  (slides  │ │
│                                   │   from    │ │
│                                   │  right)   │ │
│                                   └───────────┘ │
└─────────────────────────────────────────────────┘
```

**Components:**
1. **SpotlightSearch** - Always visible, centered
2. **ContextPanel** - Slides from right when entity selected
3. **Action Modals** - Pop over screen for confirmations

**No navigation** - State-based panels, no URL changes

---

## The Standard Action Flow

### Phase 1: Query Input

**User types natural language query:**
```
User: "create a work order for the generator"
```

**What happens:**
1. User types into SpotlightSearch input
2. On `Enter` or 500ms debounce
3. Frontend calls `POST /search`
4. GPT-4o-mini extracts intent

### Phase 2: Action Detection

**Backend `/search` endpoint:**
```
POST https://pipeline-core.int.celeste7.ai/search
Headers: Authorization: Bearer {JWT}
Body: {"query": "create a work order for the generator"}

Response:
{
  "actions": [
    {
      "action": "create_work_order",
      "label": "Create Work Order",
      "description": "Create a new work order",
      "pre_filled_context": {
        "equipment_id": null  // User must select
      },
      "form_fields": [
        {
          "name": "title",
          "label": "Title",
          "type": "text",
          "required": true,
          "placeholder": "e.g., Replace generator oil filter"
        },
        {
          "name": "description",
          "label": "Description",
          "type": "textarea",
          "required": false
        },
        {
          "name": "priority",
          "label": "Priority",
          "type": "select",
          "options": ["routine", "critical", "emergency"],
          "default": "routine"
        }
      ]
    }
  ],
  "results": [...]  // Search results also shown
}
```

### Phase 3: Action Buttons Appear

**UI renders action buttons BELOW search bar:**
```
┌────────────────────────────────────────┐
│  [🔍 create a work order for the...  │
├────────────────────────────────────────┤
│  ✅ Create Work Order                 │ ← Button
│  📄 View Work Orders                   │ ← Button (maybe)
├────────────────────────────────────────┤
│  Search Results:                       │
│  - Main Generator (Equipment)          │
│  - WO-1234 Generator Service           │
└────────────────────────────────────────┘
```

**Implementation:**
```tsx
{actions.map(action => (
  <button
    onClick={() => handleActionClick(action)}
    className="action-button"
  >
    {action.label}
  </button>
))}
```

### Phase 4: User Clicks Action Button

**What happens:**
1. `onClick` handler fires
2. If `form_fields` exist → Open modal with form
3. If no form fields → Execute immediately (rare)

### Phase 5: Modal Opens with Form

**Modal UI:**
```
┌────────────────────────────────────────┐
│  Create Work Order                  [X]│
├────────────────────────────────────────┤
│                                        │
│  Equipment: [Select Equipment ▼]      │ ← Dropdown
│                                        │
│  Title: [____________________]         │ ← Text input
│         Required                       │
│                                        │
│  Description:                          │
│  [___________________________]         │ ← Textarea
│  [___________________________]         │
│  [___________________________]         │
│                                        │
│  Priority: [Routine ▼]                │ ← Select
│                                        │
│  [Cancel]          [Create Work Order] │ ← Buttons
└────────────────────────────────────────┘
```

**Validation Rules:**
- ✅ Title required (red border if empty)
- ✅ Equipment optional (but recommended)
- ⚠️ Frontend validates BEFORE calling backend

### Phase 6: User Fills Form and Clicks Submit

**Form submission:**
```tsx
const handleSubmit = async () => {
  // 1. Validate required fields
  if (!formData.title) {
    toast.error('Title is required');
    return;
  }

  // 2. Call action client
  const result = await executeAction(
    'create_work_order',
    {
      yacht_id: user.yachtId,
      user_id: user.id
    },
    {
      title: formData.title,
      description: formData.description,
      priority: formData.priority,
      equipment_id: formData.equipment_id
    }
  );

  // 3. Handle result
  if (result.status === 'success') {
    toast.success('Work order created');
    closeModal();
    refreshData();
  } else {
    toast.error(result.message || 'Failed to create work order');
  }
};
```

### Phase 7: Backend Executes Action

**API Call:**
```
POST https://pipeline-core.int.celeste7.ai/v1/actions/execute
Headers:
  Authorization: Bearer {JWT}
  Content-Type: application/json
Body:
{
  "action": "create_work_order",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
  },
  "payload": {
    "title": "Replace generator oil filter",
    "description": "Oil filter clogged, replace with CAT-1R0739",
    "priority": "routine",
    "equipment_id": "550a46bf-a10b-42fb-9ba0-64f4c0c57c6c"
  }
}
```

**Backend Handler (p0_actions_routes.py:1325):**
```python
elif action in ("create_work_order", "create_wo"):
    # Validate
    if not payload.get("title"):
        raise HTTPException(status_code=400, detail="title is required")

    # Map priority
    priority_map = {"normal": "routine", "low": "routine", ...}
    priority = priority_map.get(payload.get("priority", "routine"), "routine")

    # Insert to DB
    wo_data = {
        "yacht_id": yacht_id,
        "equipment_id": payload.get("equipment_id"),
        "title": payload.get("title"),
        "description": payload.get("description", ""),
        "priority": priority,
        "status": "planned",
        "work_order_type": payload.get("work_order_type", "corrective"),
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()

    # Return result
    if wo_result.data:
        return {
            "status": "success",
            "work_order_id": wo_result.data[0]["id"],
            "message": "Work order created"
        }
    else:
        return {
            "status": "error",
            "error_code": "INSERT_FAILED",
            "message": "Failed to create work order"
        }
```

### Phase 8: Success Confirmation

**Frontend receives response:**
```json
{
  "status": "success",
  "work_order_id": "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
  "message": "Work order created"
}
```

**UI shows toast notification:**
```
┌────────────────────────────────┐
│ ✅ Work order created          │
└────────────────────────────────┘
```

**Modal closes, user returns to search surface**

---

## Query Variants

### create_work_order Action

**55+ natural language variants that should trigger this action:**

#### Direct Explicit
1. "create a work order"
2. "create work order"
3. "new work order"
4. "add a work order"
5. "make a work order"

#### Equipment-Specific
6. "create work order for main engine"
7. "create wo for generator"
8. "new work order for HVAC"
9. "make work order for starboard engine"

#### Task-Specific
10. "create work order to replace oil filter"
11. "create work order for oil change"
12. "schedule generator maintenance"
13. "plan engine service"

#### Fault-Related
14. "create work order from fault F-123"
15. "make work order for reported fault"
16. "convert fault to work order"

#### Abbreviated
17. "create wo"
18. "new wo"
19. "add wo"

#### Conversational
20. "I need to create a work order"
21. "Can you create a work order?"
22. "Please create a new work order"
23. "Help me create a work order"

#### Time-Based
24. "create work order for next week"
25. "schedule work order for Monday"
26. "create overdue work order"

#### Priority-Based
27. "create urgent work order"
28. "create emergency work order"
29. "create routine maintenance work order"

#### Type-Based
30. "create preventive maintenance work order"
31. "create corrective work order"
32. "create inspection work order"

#### Misspellings
33. "create work oder"
34. "create workorder"
35. "crate work order"

**And 20+ more variants...**

**Test Coverage Required:**
- ✅ At least 10 variants tested per action
- ✅ Edge cases (misspellings, abbreviations)
- ✅ Context variants (equipment, time, priority)

---

## Guard Rails and Validation

### Frontend Validation

**Before calling backend:**
```tsx
// 1. Required field validation
if (!formData.title || formData.title.trim().length === 0) {
  setErrors({...errors, title: 'Title is required'});
  return false;
}

// 2. Length validation
if (formData.title.length > 200) {
  setErrors({...errors, title: 'Title too long (max 200 chars)'});
  return false;
}

// 3. Enum validation
if (!['routine', 'critical', 'emergency'].includes(formData.priority)) {
  setErrors({...errors, priority: 'Invalid priority'});
  return false;
}
```

**Visual Feedback:**
- 🔴 Red border on invalid fields
- ⚠️ Error message below field
- 🚫 Submit button disabled until valid

### Backend Validation

**Handler checks (p0_actions_routes.py):**
```python
# 1. Authentication
if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")

# 2. Yacht access
if yacht_id not in user_context.get("allowed_yachts", []):
    raise HTTPException(status_code=403, detail="Access denied")

# 3. Required fields
if not payload.get("title"):
    raise HTTPException(status_code=400, detail="title is required")

# 4. Entity existence (if equipment_id provided)
if payload.get("equipment_id"):
    equipment = db_client.table("pms_equipment")\
        .select("id")\
        .eq("id", payload["equipment_id"])\
        .eq("yacht_id", yacht_id)\
        .execute()
    if not equipment.data:
        raise HTTPException(status_code=404, detail="Equipment not found")
```

**Error Responses:**
```json
// 400 Bad Request
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "title is required",
  "details": {"field": "title"}
}

// 404 Not Found
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Equipment not found",
  "details": {"equipment_id": "..."}
}

// 401 Unauthorized
{
  "status": "error",
  "error_code": "UNAUTHORIZED",
  "message": "Authentication required"
}

// 403 Forbidden
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "message": "Access denied to this yacht"
}
```

### Database Constraints

**RLS Policies:**
```sql
-- All queries filtered by yacht_id
CREATE POLICY "yacht_isolation" ON pms_work_orders
FOR ALL
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**Implication:** Even if backend sends wrong yacht_id, DB will reject query

**Soft Delete Protection:**
```sql
-- Hard deletes blocked
CREATE POLICY "prevent_hard_deletes" ON pms_work_orders
FOR DELETE
USING (false);
```

**Implication:** Must use `UPDATE ... SET deleted_at = NOW()` pattern

---

## Action Journey Templates

### Template 1: Create Entity (No Pre-Context)

**Examples:** create_work_order, create_equipment, create_part

**Flow:**
1. User types query → "create a work order"
2. `/search` detects action → Returns action button
3. User clicks button → Modal opens with EMPTY form
4. User fills ALL fields → Submits
5. Backend validates → Creates entity
6. Success toast → Modal closes

**Form Fields:**
- All fields start empty
- User must provide ALL required data
- No pre-filled context from query

### Template 2: Create Entity (With Pre-Context)

**Examples:** create_work_order_from_fault, add_equipment_note

**Flow:**
1. User is viewing entity (e.g., Fault F-123 in ContextPanel)
2. User clicks "Create Work Order" button in panel
3. Modal opens with PRE-FILLED context:
   - `fault_id` = F-123 (hidden, immutable)
   - `equipment_id` = Equipment from fault (pre-filled)
   - `title` = Suggested from fault title (editable)
4. User edits/confirms → Submits
5. Backend validates → Creates linked entity
6. Success toast → ContextPanel refreshes to show new WO

**Form Fields:**
- Some fields pre-filled from context
- User can edit most fields
- Some fields locked (e.g., fault_id)

### Template 3: Update Entity

**Examples:** update_work_order, update_equipment, edit_fault

**Flow:**
1. User viewing entity in ContextPanel
2. User clicks "Edit" button
3. Modal opens with CURRENT values pre-filled
4. User edits fields → Submits
5. Backend validates → Updates entity
6. Success toast → ContextPanel refreshes

**Form Fields:**
- All fields pre-filled with current values
- User modifies only what they want to change
- Submit sends ONLY changed fields (or all fields, depending on action)

### Template 4: State Transition

**Examples:** mark_work_order_complete, acknowledge_fault, start_work_order

**Flow:**
1. User viewing entity in ContextPanel
2. User clicks "Mark Complete" button
3. Confirmation modal opens (minimal form):
   - "Are you sure?"
   - Optional: "Completion notes" textarea
4. User confirms → Submits
5. Backend validates → Updates `status` + adds metadata
6. Success toast → ContextPanel refreshes

**Form Fields:**
- Minimal or none (just confirmation)
- Optional notes field
- Action is destructive/irreversible (use confirmation)

### Template 5: Add Child Entity

**Examples:** add_work_order_note, add_fault_note, add_equipment_note

**Flow:**
1. User viewing parent entity in ContextPanel
2. User scrolls to "Notes" section
3. User types in inline note input
4. User presses Enter or clicks "Add Note"
5. Backend validates → Inserts note
6. Note appears in thread immediately (optimistic UI)

**Form Fields:**
- Inline input (not modal)
- Just one field (note_text)
- Parent context automatic (work_order_id from panel)

### Template 6: Delete Entity (Soft Delete)

**Examples:** delete_work_order, delete_equipment, delete_fault

**Flow:**
1. User viewing entity in ContextPanel
2. User clicks "⋮" menu → "Delete"
3. Confirmation modal:
   - "Are you sure you want to delete this work order?"
   - Deletion reason: [dropdown or textarea]
4. User confirms → Submits
5. Backend validates → Sets `deleted_at`, `deleted_by`, `deletion_reason`
6. Success toast → ContextPanel closes (entity gone)

**Form Fields:**
- Confirmation checkbox or button
- Deletion reason (required for audit)
- Irreversible warning

---

## Context Panel Actions

**The ContextPanel is where most actions are triggered from.**

**Example: Work Order Detail Panel**
```
┌──────────────────────────────────────┐
│  WO-1234: Main Engine Oil Change     │ ← Title
│  Status: Open                         │ ← Status badge
├──────────────────────────────────────┤
│  Equipment: Main Engine               │
│  Priority: Routine                    │
│  Created: 2026-01-20 by John Smith    │
├──────────────────────────────────────┤
│  [✅ Mark Complete]  [✏️ Edit]        │ ← Action buttons
│  [👤 Assign]  [🗑️ Delete]            │
├──────────────────────────────────────┤
│  Description:                         │
│  Replace engine oil and filter...     │
├──────────────────────────────────────┤
│  Notes (3):                           │
│  - Started work at 10:00 AM           │
│  - Oil drained, filter replaced       │
│  - Awaiting delivery of new oil       │
│                                       │
│  [Add note...]                        │ ← Inline input
├──────────────────────────────────────┤
│  Parts (2):                           │
│  - Oil Filter CAT-1R0739 (qty: 1)     │
│  - Engine Oil 15W-40 (qty: 45L)       │
│                                       │
│  [+ Link Part]                        │ ← Action button
└──────────────────────────────────────┘
```

**Actions Available in Panel:**
1. Mark Complete → `mark_work_order_complete`
2. Edit → `update_work_order`
3. Assign → `assign_work_order`
4. Delete → `delete_work_order`
5. Add Note → `add_work_order_note`
6. Link Part → `link_part_to_work_order`

**Each button triggers the appropriate journey template**

---

## Error Journey Variants

### Scenario 1: Missing Required Field

**User Action:** Submits form without title

**Frontend:**
- ❌ Shows error: "Title is required"
- 🔴 Red border on title field
- 🚫 Form NOT submitted to backend

**No backend call made**

### Scenario 2: Invalid Entity Reference

**User Action:** Creates WO with non-existent equipment_id

**Frontend:** ✅ Passes validation (equipment_id is UUID)

**Backend:**
```python
# Check equipment exists
equipment = db_client.table("pms_equipment")\
    .select("id")\
    .eq("id", equipment_id)\
    .eq("yacht_id", yacht_id)\
    .execute()

if not equipment.data:
    raise HTTPException(status_code=404, detail="Equipment not found")
```

**Response:** 404
```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Equipment not found"
}
```

**Frontend:**
- ❌ Toast: "Equipment not found"
- ⚠️ Form stays open
- User can fix and retry

### Scenario 3: Unauthorized Access

**User Action:** User tries to access wrong yacht's data

**Frontend:** JWT contains `yacht_id` = A

**Backend:** Request contains `yacht_id` = B

```python
# Validate yacht access
if yacht_id not in user_context.get("allowed_yachts", []):
    raise HTTPException(status_code=403, detail="Access denied")
```

**Response:** 403
```json
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "message": "Access denied to this yacht"
}
```

**Frontend:**
- ❌ Toast: "Access denied"
- 🚫 Redirect to login (session invalid)

### Scenario 4: Database Insert Failure

**User Action:** Valid request, but DB insertion fails (rare)

**Backend:**
```python
wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()

if not wo_result.data:
    # Database rejected insert (constraint violation, etc.)
    return {
        "status": "error",
        "error_code": "INSERT_FAILED",
        "message": "Failed to create work order"
    }
```

**Response:** 200 (not HTTP error, but status: error)
```json
{
  "status": "error",
  "error_code": "INSERT_FAILED",
  "message": "Failed to create work order"
}
```

**Frontend:**
- ❌ Toast: "Failed to create work order"
- ⚠️ Form stays open
- User can retry
- Developers get alerted (Sentry)

---

## Mobile vs Desktop Journeys

### Desktop (Current Focus)

**Layout:**
- Full ContextPanel slides from right
- Modal dialogs overlay screen
- Keyboard shortcuts (Enter to submit, Esc to close)

### Mobile (Future)

**Layout:**
- ContextPanel becomes bottom sheet
- Modals become full-screen overlays
- Touch-optimized buttons (larger hit areas)

**Same API calls** - only UI rendering differs

---

## Testing Implications

### E2E Tests Must Simulate Full Journey

**❌ INSUFFICIENT:**
```typescript
// Just calling API
await fetch('/v1/actions/execute', {
  method: 'POST',
  body: JSON.stringify({action: 'create_work_order', ...})
});
```

**✅ COMPLETE:**
```typescript
// 1. Type query
await page.fill('[data-testid="spotlight-input"]', 'create a work order');
await page.press('[data-testid="spotlight-input"]', 'Enter');

// 2. Wait for action button
await page.waitForSelector('button:has-text("Create Work Order")');

// 3. Click action button
await page.click('button:has-text("Create Work Order")');

// 4. Wait for modal
await page.waitForSelector('[data-testid="action-modal"]');

// 5. Fill form
await page.fill('[name="title"]', 'Test Work Order');
await page.selectOption('[name="priority"]', 'routine');

// 6. Submit
await page.click('button:has-text("Create Work Order")');

// 7. Wait for success toast
await page.waitForSelector('.toast:has-text("Work order created")');

// 8. Verify database mutation
const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('title', 'Test Work Order')
  .single();

expect(data).toBeTruthy();
expect(data.priority).toBe('routine');
```

**This tests:**
- ✅ NL query detection
- ✅ Action button rendering
- ✅ Modal form display
- ✅ Frontend validation
- ✅ API call
- ✅ Backend validation
- ✅ Database mutation
- ✅ Success feedback

---

## Query Detection Test Matrix

**For each action, test:**

| Category | Example Query | Expected Behavior |
|----------|--------------|-------------------|
| Explicit | "create work order" | ✅ Detects action, shows button |
| Implicit | "I need to schedule maintenance" | ✅ Detects action, shows button |
| Equipment context | "create wo for generator" | ✅ Detects action + pre-fills equipment |
| Misspelling | "crate work oder" | ✅ Still detects (fuzzy match) |
| Abbreviation | "new wo" | ✅ Detects (wo = work order) |
| Multi-action | "create work order and assign to John" | ✅ Detects multiple actions |
| Ambiguous | "work order" | ⚠️ Shows search results, maybe action |
| Unrelated | "what's the weather?" | ❌ No action, just search |

**Coverage Target:** 10+ variants per action

---

## Documentation for Each Action

**For each of the 64 actions, document:**

### 1. Query Variants (10+ examples)
- Direct: "create work order"
- Contextual: "create wo for main engine"
- Conversational: "I need to create a work order"
- Misspellings: "crate work oder"

### 2. UI Journey
- Where does button appear? (Search results, ContextPanel, both)
- What modal/form opens?
- What fields are shown?
- What's pre-filled vs empty?

### 3. Form Fields
```typescript
{
  "title": {
    "type": "text",
    "required": true,
    "maxLength": 200,
    "validation": "Non-empty string",
    "placeholder": "e.g., Replace oil filter"
  },
  "priority": {
    "type": "select",
    "required": false,
    "default": "routine",
    "options": ["routine", "critical", "emergency"]
  }
}
```

### 4. Guard Rails
- Frontend validation rules
- Backend validation rules
- Database constraints
- RLS policies

### 5. Success Flow
- What response is returned?
- What toast message appears?
- What data refreshes?
- Where does user end up?

### 6. Error Flows
- 400: Missing required field → Error message + form stays open
- 404: Invalid entity → Error message + form stays open
- 401: Not authenticated → Redirect to login
- 403: Wrong yacht → Error message
- 500: Server error → Error message + retry button

### 7. Database Mutations
- What table(s) are written to?
- What columns are modified?
- What audit log entry is created?

---

## Next Steps

**To complete this framework:**

1. **For each action** (prioritize high-value first):
   - Document 10+ query variants
   - Screenshot the UI journey (or describe in detail)
   - List all form fields with types/validation
   - Document guard rails at each layer
   - Map error codes to user messages

2. **Create test files:**
   - `tests/e2e/journey_create_work_order.spec.ts`
   - Test full journey, not just API calls
   - Use Playwright to simulate real user

3. **Update as UX evolves:**
   - If modal design changes → Update screenshots
   - If validation changes → Update guard rails
   - If new fields added → Update form schema

---

## Quick Reference: Action → Journey Type

| Action | Template | Context Source | Form Complexity |
|--------|----------|----------------|-----------------|
| create_work_order | Create Entity (No Pre-Context) | None | Medium (5 fields) |
| create_work_order_from_fault | Create Entity (With Pre-Context) | Fault in ContextPanel | Low (2 fields, rest pre-filled) |
| update_work_order | Update Entity | WO in ContextPanel | Medium (5 fields, all pre-filled) |
| mark_work_order_complete | State Transition | WO in ContextPanel | Low (1 field: notes) |
| add_work_order_note | Add Child Entity | WO in ContextPanel | Minimal (inline input) |
| delete_work_order | Delete Entity | WO in ContextPanel | Confirmation only |
| assign_work_order | Update Entity | WO in ContextPanel | Low (1 field: assignee) |
| start_work_order | State Transition | WO in ContextPanel | Confirmation only |
| cancel_work_order | State Transition | WO in ContextPanel | Low (1 field: reason) |

**Similar patterns apply to faults, equipment, parts, etc.**

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Coverage:** 1/64 actions documented in detail (create_work_order)
**Next:** Document remaining 63 actions
