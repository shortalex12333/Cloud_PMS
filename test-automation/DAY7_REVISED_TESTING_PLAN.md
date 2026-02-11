# Day 7: Revised Testing Plan - User Journey Focus

**Date:** 2026-02-11
**Based On:** User clarification of vision and actual user experience

---

## Core Vision Understanding

### The Celeste Philosophy:
- **"Old software = users adapt to software. Celeste = software adapts to user"**
- No dashboards, no navigation, no learning curve
- Search bar = the entire app (like macOS Spotlight)
- Natural language queries, not keywords
- Never more than 3 actions away from completing any task

### What a "Lens" Actually Is:
- **Lens = UX domain cage/bucket for data**
- Not a "switch" users toggle
- System shows results from ALL lenses simultaneously (grouped by domain)
- Like Apple Spotlight: Applications section, Documents section, Contacts section
- Examples:
  - **Work Order Lens**: Maintenance checklists, tasks, equipment links, parts, documents
  - **Parts Lens**: Inventory items with stock, location, manuals, ordering
  - **Equipment Lens**: Machinery status, history, manuals, maintenance schedules

### NLP Query Understanding (Critical Difference):
❌ **BAD:** "oil filter" (vague - what do you want?)
✅ **GOOD:**
- "Where is the oil filter CAT?" → Intent: locate, Entity: oil filter, Manufacturer: CAT
- "How many oil filters do we have?" → Intent: check stock, Entity: oil filter
- "Oil filter operator manual" → Intent: view documentation, Entity: oil filter
- "Engine is overheating again" → Equipment: main engine, Issue: overheating, Frequency: repeated

### The "+" Button:
- Like ChatGPT/Gemini attachment button
- **Primary use:** Start receiving workflow (OCR)
- User clicks "+" → Options: Take photo, Upload image, Upload file
- Upload invoice/packing slip → OCR extracts data → Confirm → Auto-add to inventory
- **Separate from:** Attaching image to existing part (different flow)

### Result Display (Like Apple Spotlight):
When user types "oil filter CAT", system shows:
```
[PARTS]
→ CAT Oil Filter - Main Engine
  P/N: CAT-123456, Stock: 5, Location: Engine Room

→ CAT Oil Filter - Auxiliary Generator
  P/N: CAT-789012, Stock: 2, Location: Generator Room

[WORK ORDERS]
→ Replace Oil Filter - Main Engine
  Status: In Progress, Assigned: ETO

[DOCUMENTS]
→ CAT Oil Filter Installation Manual
  Section: Engine Maintenance, Page: 45

[EQUIPMENT]
→ Main Engine - Requires Oil Filter
  Next maintenance: 2026-03-15
```

All in **single column**, grouped by domain (like Apple Spotlight sections).

---

## What's Currently BROKEN (Priority Fixes)

### 🔴 CRITICAL: Parts Lens Click Does Nothing
**Current State:**
- User searches "oil filter"
- Results appear with PartCard components
- User clicks a part
- **NOTHING HAPPENS** (broken!)

**Expected:**
- User clicks part → ContextPanel slides open from right
- Detail view shows: Name, part number, stock, location, supplier, actions
- Action buttons: "Adjust Inventory", "Order Part", "View Manual", etc.

**What to Test:**
```python
# test-automation/day7_parts_lens_ux_tests.py
def test_part_click_opens_detail(page):
    search("oil filter")
    click_first_part()
    assert context_panel_is_visible()  # Currently fails
    assert detail_data_displayed()
```

### 🔴 CRITICAL: Image Upload Flow Missing
**Current State:**
- No way to upload image to part
- No image placeholder in PartCard
- No "Upload new" button in detail view
- Backend API exists (`/v1/parts/upload-image`) but no frontend UI

**Expected Flow:**
1. Search "oil filter CAT"
2. Click part → Detail view opens
3. See current image (or placeholder if none)
4. Click image → "Upload new" button appears
5. Select file → Upload → Image attached to part

**What to Build:**
- Add image display to PartCard (show thumbnail or placeholder)
- Add image section to detail view
- Add click handler on image → Show upload button
- Connect to backend `/v1/parts/upload-image` endpoint

### ⚠️ MEDIUM: Action Buttons May Not Work
**Current State:** Unknown if action buttons in detail view actually execute
**What to Test:**
- Click "Adjust Inventory" → Modal opens with form
- Fill form → Submit → Backend saves changes
- Click "Order Part" → Shopping list modal opens
- Test with different roles (Captain vs Crew) → RBAC filtering

### ⚠️ MEDIUM: "+" Button Hidden/Not Connected
**Current State:** Button exists but might be hidden or not connected to OCR backend
**OCR Backend:** https://image-processing-givq.onrender.com (Render service)
**What to Test:**
- "+" button visible in search bar
- Click "+" → Options appear: "Take Photo", "Upload Image", "Upload File"
- Upload invoice → Sends to OCR backend
- OCR extracts data → Frontend shows confirmation
- Confirm → Parts added to inventory

---

## Testing Priorities (Day 7 Focus)

### Test 1: Parts Lens Click → Detail Opens 🔴
**Status:** Running now in `day7_parts_lens_ux_tests.py`
**Expected:** FAIL (currently broken)
**Fix Required:** Add onClick handler to PartCard, open ContextPanel with detail view

### Test 2: Detail View Shows Correct Data ✅
**What to Verify:**
- Part name, part number displayed
- Stock quantity, min stock level shown
- Location (deck, room, storage) visible
- Supplier, unit cost displayed
- Last updated timestamp

### Test 3: Action Buttons Execute ⚠️
**What to Test:**
```
User clicks "Adjust Inventory"
→ Modal opens
→ Form shows: Current stock: 5, Adjustment: [input], New stock: [calculated]
→ User enters: +3
→ Submit
→ Backend updates stock to 8
→ Success toast appears
→ Detail view refreshes with new stock: 8
```

### Test 4: RBAC Enforcement ✅
**What to Test:**
```
Captain logs in
→ Searches "oil filter"
→ Clicks part
→ Sees actions: "Adjust Inventory", "Order Part", "Delete Part", "Transfer"

Crew logs in
→ Searches "oil filter"
→ Clicks part
→ Sees actions: "Order Part" only (cannot adjust/delete/transfer)
```

**Expected:** Captain sees 4+ actions, Crew sees 1-2 actions

### Test 5: Image Upload Flow 🔴
**Status:** MISSING - needs implementation
**What to Test:** After building image upload UI:
```
User searches "oil filter CAT"
→ Clicks part → Detail opens
→ Clicks image placeholder
→ "Upload new" button appears
→ Selects image file
→ Upload progress shown
→ Image attached to part
→ Thumbnail appears in PartCard
→ Full image shown in detail view
```

### Test 6: Multi-Domain Results Display ✅
**What to Test:**
```
User types "oil filter"
→ Results appear grouped by domain:

[PARTS] (2 results)
→ Oil Filter CAT
→ Oil Filter Generic

[WORK ORDERS] (1 result)
→ Replace Oil Filter - Main Engine

[DOCUMENTS] (3 results)
→ Oil Filter Manual
→ Oil Filter Installation Guide
→ Oil Filter Specifications

User can click any result
→ Opens appropriate detail view
```

### Test 7: NLP Query Understanding 🔄
**What to Test:**
```
Query: "Where is the oil filter CAT?"
→ System extracts: entity="oil filter", manufacturer="CAT", intent="locate"
→ Parts lens activates
→ Results prioritize parts with location data
→ First result shows: Location: "Engine Room, Cabinet 3, Shelf B"

Query: "How many oil filters do we have?"
→ System extracts: entity="oil filter", intent="count"
→ Parts lens activates
→ Results show stock quantities prominently
→ Total count displayed: "5 units across 2 variants"

Query: "Engine is overheating again"
→ System extracts: equipment="engine", issue="overheating", frequency="repeated"
→ Suggested actions: "Create Work Order" (pre-filled), "Add to Handover" (pre-filled)
→ User clicks "Create Work Order"
→ Form shows: Title="Engine Overheating", Equipment="Main Engine", Notes="Repeated issue"
```

---

## User Journeys to Test End-to-End

### Journey 1: Find Part and Check Stock ✅
```
1. User types: "Where is the CAT oil filter?"
2. Results show: CAT Oil Filter with location
3. User clicks result
4. Detail view opens showing:
   - Current stock: 5 units
   - Min stock: 10 units
   - Location: Engine Room, Cabinet 3, Shelf B
   - Status: LOW STOCK (red indicator)
5. User sees suggested action: "Order Part"
6. User clicks "Order Part"
7. Shopping list modal opens (pre-filled with part)
8. User enters quantity: 15
9. User submits
10. Success: "Added to shopping list"
```

### Journey 2: Add Part to Inventory (MVP) ⚠️
```
1. User types: "Add new part to box 3D"
2. System shows: "No results found" + "Add New Part" action
3. User clicks "Add New Part"
4. Modal opens with form:
   - Part name: [empty]
   - Part number: [empty]
   - Initial stock: 0
   - Min stock: 1
   - Location: [pre-filled "Box 3D" from query]
   - Supplier: [empty]
   - Category: [dropdown]
5. User fills: Name="Oil Seal", Number="OS-9876", Stock=5
6. User submits
7. Part created in database
8. Success: "Part added to inventory"
9. Search refreshes → New part appears in results
```

### Journey 3: Adjust Inventory (MVP) ⚠️
```
1. User types: "Oil filter CAT"
2. User clicks result → Detail opens
3. Current stock shown: 5 units
4. User clicks "Adjust Inventory" button
5. Modal opens:
   - Current stock: 5
   - Adjustment: [input] (+/- or absolute)
   - Reason: [dropdown: Usage, Received, Damaged, Transfer]
   - New stock: [calculated]
6. User enters: +3 (received)
7. New stock shows: 8
8. User submits
9. Backend updates: stock_quantity = 8
10. Success: "Stock updated to 8 units"
11. Detail view refreshes with new stock
```

### Journey 4: Create Work Order with Pre-Population 🔄
```
1. User types: "Engine is overheating again"
2. System extracts: equipment="main engine", issue="overheating", frequency="repeated"
3. Results show:
   - Equipment: Main Engine (with alert icon)
   - Previous work orders mentioning "overheating"
   - Suggested action: "Create Work Order" (highlighted)
4. User clicks "Create Work Order"
5. Modal opens with PRE-FILLED data:
   - Title: "Engine Overheating" ✅
   - Equipment: "Main Engine" ✅
   - Category: "Breakdown" (inferred)
   - Priority: "High" (inferred from "again")
   - Notes: "Repeated issue" ✅
   - Assigned to: [empty]
6. User adds: Assigned="ETO", Due date="Tomorrow"
7. User submits
8. Work order created in database
9. Success: "Work order created #WO-1234"
10. Work order appears in search results
```

### Journey 5: Upload Invoice via OCR (Future) 🔄
```
1. User clicks "+" button in search bar
2. Options appear: "Take Photo", "Upload Image", "Upload File"
3. User clicks "Upload File"
4. File picker opens
5. User selects: "shipment_invoice.pdf"
6. Upload starts → Progress bar
7. OCR backend processes: https://image-processing-givq.onrender.com
8. System extracts:
   - 15 parts with names, part numbers, quantities
   - Supplier: "Marine Parts Inc."
   - Date: "2026-02-10"
9. Frontend shows: "Confirm receiving these 15 parts?"
10. User reviews list → Checks all correct
11. User clicks "Confirm"
12. All 15 parts added to inventory
13. Stock quantities updated
14. Success: "15 parts received and added to inventory"
```

---

## What NOT to Test (Wasted Effort)

### ❌ Don't Test:
1. **Backend endpoints with no frontend UI** (like Day 3 image upload APIs)
2. **Isolated API calls** (test integration, not API in vacuum)
3. **Features users can't access** (if no button exists, don't test backend)
4. **Performance under load** (until basic UX works first)
5. **Edge cases** (until happy path works)

### ✅ DO Test:
1. **What users see and click** (buttons, cards, modals)
2. **Complete user journeys** (search → click → action → result)
3. **Visual feedback** (modals open, toasts appear, data updates)
4. **RBAC from user perspective** (different roles see different UI)
5. **Error handling users experience** (friendly messages, not 500 errors)

---

## Success Criteria (Day 7)

### Must Work Before Production:
1. ✅ User can search and see results (grouped by domain)
2. 🔴 User can click part → Detail view opens (CURRENTLY BROKEN - FIX THIS)
3. ✅ Detail view shows all part data correctly
4. ⚠️ Action buttons open modals and execute (NEEDS TESTING)
5. ✅ RBAC filters actions by role (NEEDS VERIFICATION)
6. 🔴 User can upload/change part image (MISSING - BUILD THIS)
7. ⚠️ "+" button visible and connected to OCR (NEEDS VERIFICATION)

### Pass Rate Target:
- **Day 7 Goal:** 85%+ of user journeys work end-to-end
- **Not:** 75% of backend APIs respond correctly
- **But:** User can complete tasks successfully

---

## Next Steps

### Immediate (Running Now):
1. ✅ Day 7 Parts Lens UX tests running (`day7_parts_lens_ux_tests.py`)
2. ⏳ Waiting for results to identify what's broken

### After Test Results:
1. **Fix critical issues:**
   - Part click → Detail view opens
   - Action buttons execute correctly
   - Image upload flow implementation
2. **Re-test user journeys** end-to-end
3. **Verify RBAC** with different roles
4. **Test "+" button** and OCR integration

### Documentation:
1. ✅ Created: `ACTUAL_USER_JOURNEY_ANALYSIS.md` (what users can/can't do)
2. ✅ Created: `DAY7_REVISED_TESTING_PLAN.md` (this document)
3. 🔄 Update: `DAY7_FINAL_REPORT.md` with actual user journey test results

---

## Summary

**Old Approach (Days 1-6):**
- Tested backend APIs in isolation
- Validated endpoints users can't access
- Missed that Parts Lens click is broken
- High pass rate on meaningless tests

**New Approach (Day 7):**
- Test what users see and click
- Validate complete journeys work
- Focus on frontend UX, not backend APIs
- Meaningful pass rate on real user tasks

**The Vision:**
- Search bar = entire app (like Spotlight)
- Natural language queries, not keywords
- System infers intent and pre-populates
- Never more than 3 actions to complete task
- No dashboards, no navigation, no learning curve

**Critical Fix Needed:**
🔴 **Part click does nothing** - This breaks the entire Parts Lens experience. FIX THIS FIRST.
