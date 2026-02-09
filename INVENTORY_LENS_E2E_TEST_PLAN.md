# INVENTORY LENS - COMPREHENSIVE E2E TEST PLAN

**Date**: 2026-02-09
**Deployment**: Waiting for Render deploy to complete
**Test Duration**: 6 hours
**Scope**: EVERYTHING - All journeys, all edge cases, all site touchpoints

---

## 🎯 TEST OBJECTIVES

1. **Verify Complete User Journeys** (HOD and CREW roles)
2. **Test Success Paths** (happy path for all actions)
3. **Test Failure Paths** (validation errors, insufficient stock, permission denials)
4. **Test Edge Cases** (low stock, zero stock, missing data, malformed queries)
5. **Map All Site Touchpoints** (where inventory lens could/should appear)
6. **Document Every Finding** (no incremental fixes - collect everything first)

---

## 📋 TEST MATRIX

### HOD Journey Tests (Elevated Role - Full Access)

#### 1. Search → Results → Context Panel
- [ ] Query: "fuel filter stock" → parts domain detected
- [ ] Results: Verify 10+ parts returned
- [ ] Click first result → ContextPanel slides in from right
- [ ] Verify part details display: name, stock, location, supplier, cost
- [ ] Verify 4 action buttons visible: View Details, Check Stock, Usage History, Log Usage

#### 2. Check Stock Action (READ)
- [ ] Click "Check Stock" button
- [ ] Verify modal/info displays with current stock quantity
- [ ] Verify no errors in console
- [ ] Verify endpoint called: `/v1/actions/execute` with action="check_stock_level"
- [ ] Verify response includes quantity_on_hand
- [ ] Close modal → ContextPanel still visible

#### 3. View Part Details Action (READ)
- [ ] Click "View Details" button
- [ ] Verify full part card/modal displays
- [ ] Verify shows: part_number, category, manufacturer, last_counted_at, last_counted_by
- [ ] Verify no errors

#### 4. View Usage History Action (READ)
- [ ] Click "Usage History" button
- [ ] Verify displays list of past usage records
- [ ] Verify shows: date, quantity_used, work_order, logged_by
- [ ] Verify empty state if no history ("No usage recorded yet")

#### 5. Log Usage Action (MUTATE) - Success Path
- [ ] Click "Log Usage" button
- [ ] Verify form modal appears
- [ ] Form fields visible: quantity (number), usage_reason (text), notes (textarea)
- [ ] Fill: quantity=1, usage_reason="Preventive maintenance", notes="Engine oil change"
- [ ] Click Submit
- [ ] Verify success toast appears
- [ ] Verify modal closes
- [ ] Verify stock quantity decrements by 1 in ContextPanel
- [ ] Search again → verify new stock value in results
- [ ] Verify database updated (check via API call)

#### 6. Log Usage Action - Validation Failures
- [ ] Click "Log Usage"
- [ ] Submit empty form → verify error: "Quantity required"
- [ ] Enter quantity=0 → verify error: "Quantity must be greater than 0"
- [ ] Enter quantity=-5 → verify error: "Quantity must be positive"
- [ ] Enter quantity as text "abc" → verify error: "Must be a number"
- [ ] Fill quantity but leave reason empty → verify error: "Usage reason required"

#### 7. Log Usage Action - Insufficient Stock
- [ ] Find part with stock=2
- [ ] Attempt to log usage with quantity=10
- [ ] Verify error: "Insufficient stock" or "Cannot log more than available"
- [ ] Verify stock unchanged
- [ ] Verify no database update

#### 8. Log Usage Action - Zero Stock Part
- [ ] Find part with stock=0
- [ ] Attempt to log usage
- [ ] Verify "Log Usage" button disabled OR error message
- [ ] Verify suggests ordering part

#### 9. Multiple Actions in Sequence
- [ ] Check Stock → view quantity (e.g., 50)
- [ ] Log Usage → quantity=5
- [ ] Check Stock again → verify shows 45
- [ ] View Usage History → verify new record appears
- [ ] Log Usage again → quantity=3
- [ ] Check Stock → verify shows 42
- [ ] Verify all updates persist

#### 10. Search Different Queries
- [ ] "engine oil" → results appear
- [ ] "fuel filter" → results appear
- [ ] "spark plug inventory" → results appear
- [ ] "bilge pump parts" → results appear
- [ ] "hydraulic fluid stock" → results appear
- [ ] Verify all return parts domain
- [ ] Verify all show appropriate actions

### CREW Journey Tests (Base Role - READ Only)

#### 11. CREW Search → Results → Context Panel
- [ ] Login as CREW (crew.test@alex-short.com)
- [ ] Query: "fuel filter stock"
- [ ] Verify results appear
- [ ] Click part → ContextPanel opens
- [ ] Verify 2 action buttons visible: View Details, Check Stock
- [ ] Verify "Log Usage" button NOT visible
- [ ] Verify "Usage History" button NOT visible

#### 12. CREW Check Stock (Allowed)
- [ ] Click "Check Stock"
- [ ] Verify modal displays stock quantity
- [ ] Verify no errors
- [ ] Verify works correctly (READ actions allowed)

#### 13. CREW View Details (Allowed)
- [ ] Click "View Details"
- [ ] Verify part details display
- [ ] Verify no errors

#### 14. CREW Attempts Log Usage (Blocked)
- [ ] Verify "Log Usage" button not visible in UI
- [ ] Attempt direct API call: POST /v1/actions/execute with action="log_part_usage"
- [ ] Verify HTTP 403 Forbidden
- [ ] Verify error message: "Permission denied" or "Insufficient permissions"
- [ ] Verify stock unchanged

#### 15. CREW Attempts View Usage History (Blocked)
- [ ] Verify "Usage History" button not visible
- [ ] Attempt direct API call with action="view_part_usage"
- [ ] Verify HTTP 403 OR action not in allowed list
- [ ] Verify appropriate error handling

### Low Stock & Shopping List Integration

#### 16. Low Stock Warning
- [ ] Find part with quantity_on_hand < min_stock_level
- [ ] Open in ContextPanel
- [ ] Verify low stock warning badge/indicator visible
- [ ] Verify suggests reordering
- [ ] Verify "Order Part" button appears (auto-suggested)

#### 17. Zero Stock Warning
- [ ] Find part with quantity_on_hand = 0
- [ ] Open in ContextPanel
- [ ] Verify critical warning: "Out of stock"
- [ ] Verify "Log Usage" disabled/hidden
- [ ] Verify "Order Part" button prominent

#### 18. Order Part Action
- [ ] Click "Order Part" button
- [ ] Verify form appears: quantity, supplier, notes
- [ ] Fill form
- [ ] Submit
- [ ] Verify added to shopping list
- [ ] Verify success toast

### Edge Cases & Error Handling

#### 19. Malformed Queries
- [ ] Query: "xyz123abc" → verify graceful "No results" message
- [ ] Query: "" (empty) → verify validation or graceful handling
- [ ] Query: Special chars "!@#$%^" → verify no crashes
- [ ] Query: Very long string (500+ chars) → verify truncation or handling

#### 20. Missing Part Data
- [ ] Find part with null location → verify shows "Unknown" or placeholder
- [ ] Find part with null supplier → verify graceful handling
- [ ] Find part with null last_counted_at → verify shows "Never" or placeholder
- [ ] Verify no UI breaks, no console errors

#### 21. Network Failures
- [ ] Simulate slow network (throttle in DevTools)
- [ ] Verify loading states appear
- [ ] Verify spinners show while fetching
- [ ] Verify timeout handling (if applicable)

#### 22. Concurrent Actions
- [ ] Open part in ContextPanel
- [ ] Click "Log Usage" → fill form but don't submit
- [ ] Open different part in new tab
- [ ] Submit first form
- [ ] Verify correct part updated
- [ ] Verify no cross-contamination

#### 23. State Persistence
- [ ] Check stock for part A (quantity=50)
- [ ] Log usage for part A (quantity=5)
- [ ] Navigate away (close ContextPanel)
- [ ] Search again and open part A
- [ ] Verify shows updated quantity (45)
- [ ] Refresh page
- [ ] Search and open part A again
- [ ] Verify still shows 45 (persisted in database)

### Performance & UX

#### 24. Search Performance
- [ ] Time how long search takes
- [ ] Verify < 1 second for results to appear
- [ ] Verify smooth rendering (no janky scrolling)

#### 25. Context Panel Animations
- [ ] Verify smooth slide-in animation
- [ ] Verify smooth slide-out on close
- [ ] Verify backdrop dims properly
- [ ] Verify clicking outside closes panel

#### 26. Button States
- [ ] Verify buttons disabled during loading
- [ ] Verify loading spinner appears in button during action
- [ ] Verify buttons re-enable after action completes
- [ ] Verify buttons show hover states

#### 27. Toast Notifications
- [ ] Verify success toasts appear for successful actions
- [ ] Verify error toasts appear for failures
- [ ] Verify toasts auto-dismiss after ~3 seconds
- [ ] Verify toasts stack properly (multiple actions)

---

## 🗺️ SITE-WIDE INVENTORY LENS TOUCHPOINTS

### Where Should Inventory Lens Surface?

#### Current Implementation
- [x] SpotlightSearch → Query "part stock" → Results → ContextPanel

#### Should Also Appear In:

1. **Work Orders Page** (`/app/work-orders/[id]`)
   - When viewing work order details
   - "Parts Used" section should link to inventory
   - Query: "parts for work order XYZ"
   - Should show relevant parts with stock levels

2. **Equipment Details Page** (`/app/equipment/[id]`)
   - "Related Parts" section
   - Query: "parts for [equipment_name]"
   - Show parts compatible with this equipment

3. **Parts Management Page** (`/app/parts`)
   - Dedicated parts inventory page
   - Full CRUD for parts
   - List view → Click part → ContextPanel opens
   - Bulk actions: log usage for multiple parts, bulk order

4. **Shopping List / Orders Page** (`/app/orders`)
   - When creating purchase orders
   - "Add Parts" button → Search parts → Add to order
   - Show current stock for each part

5. **Handover Dashboard**
   - "Low Stock Items" section
   - Automatically surface parts below min_stock_level
   - Quick actions: order, adjust stock

6. **Maintenance Checklists**
   - When checklist requires parts
   - Link to parts inventory
   - Show if parts are available before starting task

7. **Fault Reports**
   - When reporting fault that needs parts
   - Suggest related parts
   - Check stock before creating work order

8. **Global Search**
   - Any query with "stock", "part", "inventory" keywords
   - Should trigger inventory lens

### Navigation Flow Tests

#### 28. From Work Order → Inventory Lens
- [ ] Navigate to work order details
- [ ] Click "View Parts" or similar link
- [ ] Verify opens inventory search OR ContextPanel with relevant parts
- [ ] Verify can log usage from work order context

#### 29. From Equipment → Inventory Lens
- [ ] Navigate to equipment details
- [ ] Find "Related Parts" section
- [ ] Click part → ContextPanel opens
- [ ] Verify shows parts for that equipment

#### 30. From Shopping List → Inventory Lens
- [ ] Navigate to shopping list
- [ ] Click "Add Parts" button
- [ ] Verify opens search
- [ ] Search and add part to shopping list
- [ ] Verify current stock shown

#### 31. Direct Parts URL
- [ ] Navigate to `/app/parts`
- [ ] Verify dedicated parts management interface
- [ ] Verify list view with all parts
- [ ] Verify can filter, sort, search
- [ ] Click part → ContextPanel opens

---

## 🐛 KNOWN ISSUES TO VERIFY FIXED

### Critical Issues
1. **useActionHandler calling wrong endpoint** (reported in FINAL_REPORT)
   - [ ] Verify now calls `/v1/actions/execute`
   - [ ] Verify NOT calling `/workflows/*`
   - [ ] Verify actions execute successfully

### Previous Issues
2. **Actions not surfacing** (PR #207 should have fixed)
   - [ ] Verify getPartActions() passes actions to PartCard
   - [ ] Verify HOD sees 4 actions
   - [ ] Verify CREW sees 2 actions

3. **log_part_usage not in search results** (intent-based filtering)
   - [ ] Verify this is by design
   - [ ] Verify log_part_usage only shows when part is opened (ContextPanel)
   - [ ] Verify search results don't show MUTATE actions for READ intents

---

## 📊 SUCCESS CRITERIA

### Must Have (Blocking)
- [ ] HOD can search, view, and check stock
- [ ] HOD can log usage successfully
- [ ] CREW can search and check stock
- [ ] CREW blocked from logging usage (403)
- [ ] Stock quantities update in real-time
- [ ] No 404 errors in console
- [ ] No crashes or UI breaks

### Should Have (High Priority)
- [ ] Low stock warnings appear
- [ ] Validation errors show clearly
- [ ] Insufficient stock blocked
- [ ] Forms have proper UX (labels, placeholders, validation)
- [ ] Toast notifications work
- [ ] Loading states appear

### Nice to Have (Future)
- [ ] Usage history displays
- [ ] Order part integration
- [ ] Barcode scanning
- [ ] Bulk operations
- [ ] Export inventory reports

---

## 📝 TEST EXECUTION LOG

### Test Run #1: [TIMESTAMP]

**Environment**:
- Backend: https://pipeline-core.int.celeste7.ai
- Frontend: https://app.celeste7.ai
- Commit: [deployed commit hash]

**Results**: [TO BE FILLED DURING TESTING]

---

## 🚨 ISSUES FOUND

### Critical Issues

### High Priority Issues

### Medium Priority Issues

### Low Priority / Future Enhancements

---

## 📈 METRICS

- **Total Tests**: 31 test scenarios
- **Passed**: ___ / 31
- **Failed**: ___ / 31
- **Blocked**: ___ / 31
- **Coverage**: HOD journey (15 tests), CREW journey (5 tests), Edge cases (8 tests), Site touchpoints (4 tests)

---

**Test Plan Created**: 2026-02-09
**Execution Start**: [Waiting for deployment]
**Execution End**: [+6 hours]
