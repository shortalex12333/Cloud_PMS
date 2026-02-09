# INVENTORY LENS - 6 HOUR LIVE TESTING SESSION

**Date**: 2026-02-09
**Deployment**: bffb436 (Vercel Preview - PR #213)
**Test Window**: 6 hours
**Scope**: Complete real-user simulation on app.celeste7.ai

---

## 🎯 TEST ENVIRONMENT

**URL**: app.celeste7.ai (ONE PAGE - no navigation)
**Commit**: bffb436 - CRITICAL FIX: useActionHandler calls /v1/actions/execute

**Test Users**:
```bash
HOD:     hod.test@alex-short.com / Password2!
CREW:    crew.test@alex-short.com / Password2!
CAPTAIN: x@alex-short.com / Password2!
Yacht:   85fe1119-b04c-41ac-80f1-829d23322598
```

**Critical Fix Applied**:
- ✅ useActionHandler now calls `/v1/actions/execute` (NOT `/workflows/*`)
- ✅ Payload format matches Action Router spec
- ✅ All action buttons should execute (no 404 errors)

---

## 📋 COMPREHENSIVE TEST PLAN

### Phase 1: HOD Journey (Elevated Role) [2 hours]

#### 1.1 Login and Navigation
- [ ] Navigate to app.celeste7.ai
- [ ] Login as hod.test@alex-short.com / Password2!
- [ ] Verify lands on /app (URL never changes)
- [ ] JWT refreshes on login
- [ ] Dashboard displays

#### 1.2 Search Functionality
- [ ] Search "fuel filter stock"
- [ ] Results appear inline (no navigation)
- [ ] Domain detected as "parts"
- [ ] 10+ results returned
- [ ] Results show: part name, stock level, location
- [ ] Low stock badges visible where applicable

#### 1.3 Open Part in ContextPanel
- [ ] Click first result
- [ ] URL stays app.celeste7.ai/app ✅
- [ ] ContextPanel slides in from right
- [ ] Part details display:
  - [ ] Part name and number
  - [ ] Current stock quantity
  - [ ] Min stock level
  - [ ] Location, bin, supplier
  - [ ] Unit cost
  - [ ] Last counted date/by

#### 1.4 Verify 4 Action Buttons (HOD)
- [ ] Button 1: "View Details" visible
- [ ] Button 2: "Check Stock" visible
- [ ] Button 3: "Usage History" visible
- [ ] Button 4: "Log Usage" visible
- [ ] All buttons enabled (not disabled)
- [ ] Proper icons displayed

#### 1.5 Execute "Check Stock" Action
- [ ] Click "Check Stock" button
- [ ] **CRITICAL**: Open browser DevTools → Network tab
- [ ] **VERIFY**: Request goes to `/v1/actions/execute` ✅
- [ ] **VERIFY**: NOT `/workflows/view` ❌
- [ ] **VERIFY**: Response status 200 (NOT 404) ✅
- [ ] Stock quantity displays (modal or inline)
- [ ] Success toast appears
- [ ] No console errors
- [ ] ContextPanel remains open

#### 1.6 Execute "View Part Details" Action
- [ ] Click "View Part Details"
- [ ] Network request to `/v1/actions/execute` ✅
- [ ] Response 200 ✅
- [ ] Full part details display
- [ ] All fields populated correctly
- [ ] No errors

#### 1.7 Execute "View Usage History" Action
- [ ] Click "Usage History"
- [ ] Network request to `/v1/actions/execute` ✅
- [ ] Response 200 ✅
- [ ] Usage records display (or "No usage" empty state)
- [ ] Shows: date, quantity, work order, logged by
- [ ] No errors

#### 1.8 Execute "Log Usage" Action - Happy Path
- [ ] Click "Log Usage" button
- [ ] Network request to `/v1/actions/execute` (or form opens first)
- [ ] **Form modal appears** ✅
- [ ] Form fields visible:
  - [ ] Quantity (number input)
  - [ ] Usage reason (text/textarea)
  - [ ] Notes (textarea, optional)
- [ ] Fill form:
  - Quantity: 1
  - Reason: "E2E test - inventory lens live verification"
  - Notes: "Testing bffb436 deployment"
- [ ] Click Submit
- [ ] Network request to `/v1/actions/execute` with action="log_part_usage"
- [ ] Response 200 ✅
- [ ] Success toast appears: "Part usage logged" ✅
- [ ] Modal closes
- [ ] **Stock quantity decrements by 1** in ContextPanel ✅
- [ ] Close ContextPanel

#### 1.9 Verify State Persistence
- [ ] Search "fuel filter stock" again
- [ ] Click same part
- [ ] **Verify stock shows new value** (decremented) ✅
- [ ] Click "Usage History"
- [ ] **New usage record appears** ✅
- [ ] Shows: just now, quantity=1, reason="E2E test..."

#### 1.10 Execute "Log Usage" - Validation Errors
- [ ] Click "Log Usage"
- [ ] Submit empty form
- [ ] **Verify error**: "Quantity required" ✅
- [ ] Enter quantity: 0
- [ ] **Verify error**: "Quantity must be greater than 0" ✅
- [ ] Enter quantity: -5
- [ ] **Verify error**: "Quantity must be positive" ✅
- [ ] Enter quantity: "abc"
- [ ] **Verify error**: "Must be a number" ✅
- [ ] Enter quantity: 1, leave reason empty
- [ ] **Verify error**: "Usage reason required" ✅

#### 1.11 Execute "Log Usage" - Insufficient Stock
- [ ] Find part with stock=2 or less
- [ ] Open in ContextPanel
- [ ] Click "Log Usage"
- [ ] Enter quantity: 100 (more than available)
- [ ] Submit
- [ ] **Verify error**: "Insufficient stock" or similar ✅
- [ ] **Verify stock unchanged** ✅

#### 1.12 Multiple Searches - Dynamic UX
- [ ] Search "engine oil"
- [ ] Results update inline (no navigation)
- [ ] URL stays app.celeste7.ai/app ✅
- [ ] Click result → ContextPanel updates with new part
- [ ] Search "spark plug"
- [ ] Results update again
- [ ] URL still app.celeste7.ai/app ✅

#### 1.13 Low Stock Warnings
- [ ] Find part with quantity < min_quantity
- [ ] Open in ContextPanel
- [ ] **Verify low stock badge** visible (orange/red) ✅
- [ ] **Verify "Order Part" button auto-suggests** ✅
- [ ] Click "Order Part"
- [ ] Verify form/action executes

#### 1.14 Zero Stock Part
- [ ] Find part with quantity = 0
- [ ] Open in ContextPanel
- [ ] **Verify "Out of Stock" badge** ✅
- [ ] **Verify "Log Usage" disabled or hidden** ✅
- [ ] **Verify "Order Part" prominent** ✅

---

### Phase 2: CREW Journey (Base Role - RBAC) [1.5 hours]

#### 2.1 Login as CREW
- [ ] Logout HOD
- [ ] Login as crew.test@alex-short.com / Password2!
- [ ] JWT refreshes
- [ ] Dashboard displays

#### 2.2 Search and Open Part
- [ ] Search "fuel filter stock"
- [ ] Results appear
- [ ] Click part → ContextPanel opens
- [ ] URL stays app.celeste7.ai/app ✅

#### 2.3 Verify 2 Action Buttons (CREW)
- [ ] Button 1: "View Details" visible ✅
- [ ] Button 2: "Check Stock" visible ✅
- [ ] **Button "Log Usage" NOT visible** ✅
- [ ] **Button "Usage History" NOT visible** ✅
- [ ] RBAC enforcement working in UI

#### 2.4 Execute "Check Stock" (Allowed)
- [ ] Click "Check Stock"
- [ ] Network request to `/v1/actions/execute`
- [ ] Response 200 ✅
- [ ] Stock displays
- [ ] No errors
- [ ] READ action works for CREW ✅

#### 2.5 Execute "View Details" (Allowed)
- [ ] Click "View Details"
- [ ] Response 200 ✅
- [ ] Details display
- [ ] Works correctly

#### 2.6 Attempt Log Usage via API (Should Fail)
- [ ] Open browser console
- [ ] Paste and run:
```javascript
fetch('/v1/actions/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'log_part_usage',
    context: { yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598' },
    payload: { part_id: 'test', quantity: 1, usage_reason: 'Should be blocked' }
  })
}).then(r => r.json()).then(console.log)
```
- [ ] **Verify response: 403 Forbidden** ✅
- [ ] **Verify error: "Permission denied" or "FORBIDDEN"** ✅
- [ ] RBAC enforced at API level ✅

---

### Phase 3: CAPTAIN Journey (All Permissions) [1 hour]

#### 3.1 Login as CAPTAIN
- [ ] Logout CREW
- [ ] Login as x@alex-short.com / Password2!
- [ ] JWT refreshes
- [ ] Dashboard displays

#### 3.2 Search and Open Part
- [ ] Search "fuel filter stock"
- [ ] Click part → ContextPanel opens

#### 3.3 Verify All Action Buttons
- [ ] All 4 buttons visible (same as HOD)
- [ ] Execute each action
- [ ] All work correctly
- [ ] No 404 errors
- [ ] CAPTAIN has full MUTATE permissions

---

### Phase 4: Edge Cases & Stress Testing [1.5 hours]

#### 4.1 Empty Queries
- [ ] Search ""
- [ ] **Verify graceful handling** (no crash) ✅
- [ ] Shows empty state or validation

#### 4.2 Invalid Queries
- [ ] Search "xyzabc123notfound999"
- [ ] **Verify "No results" message** ✅
- [ ] No crashes, no errors

#### 4.3 Special Characters
- [ ] Search "fuel & filter"
- [ ] Search "part#123"
- [ ] Search "filter (old)"
- [ ] All queries handled gracefully

#### 4.4 Unicode
- [ ] Search "αβγ filter"
- [ ] Search "部品 stock"
- [ ] Verify handles international characters

#### 4.5 Very Long Queries
- [ ] Search 500+ character string
- [ ] **Verify truncation or validation** ✅
- [ ] No crashes

#### 4.6 Rapid Searches
- [ ] Search "fuel" → immediately "oil" → immediately "filter"
- [ ] Results update correctly
- [ ] No race conditions
- [ ] UI stays responsive

#### 4.7 ContextPanel Rapid Open/Close
- [ ] Open part → Close → Open same → Close → Open different
- [ ] No memory leaks
- [ ] No stale data
- [ ] Always shows correct part

#### 4.8 Concurrent Actions
- [ ] Open part
- [ ] Click "Check Stock"
- [ ] While loading, click "Log Usage"
- [ ] Verify proper handling
- [ ] No conflicts

#### 4.9 Network Throttling
- [ ] Open DevTools → Network → Throttle to "Slow 3G"
- [ ] Search parts
- [ ] **Verify loading states** appear ✅
- [ ] **Verify spinners** show while fetching ✅
- [ ] Eventually loads correctly
- [ ] No timeouts

#### 4.10 Offline Mode
- [ ] Open DevTools → Network → Offline
- [ ] Attempt search
- [ ] **Verify error handling** ✅
- [ ] Re-enable network
- [ ] Search works again

---

### Phase 5: Console & Network Monitoring [Continuous]

**During ALL tests above, monitor**:

#### Console Errors
- [ ] No uncaught exceptions
- [ ] No 404 errors for `/workflows/*` ✅
- [ ] No type errors
- [ ] No React warnings
- [ ] Only expected logs

#### Network Requests
- [ ] All action requests go to `/v1/actions/execute` ✅
- [ ] Payload format correct: `{ action, context, payload }`
- [ ] Response format: ActionResponseEnvelope
- [ ] Status codes: 200 (success), 403 (forbidden), 400 (validation)
- [ ] NO 404 errors ✅

#### Performance
- [ ] Search results < 1 second
- [ ] ContextPanel opens < 500ms
- [ ] Action execution < 2 seconds
- [ ] No UI jank or freezing
- [ ] Smooth animations

---

## 🐛 ISSUES LOG

### Critical Issues 🔴
_[To be filled during testing]_

### High Priority Issues 🟡
_[To be filled during testing]_

### Medium Priority Issues 🟠
_[To be filled during testing]_

### Low Priority / UX Improvements 🟢
_[To be filled during testing]_

---

## 📊 METRICS TO CAPTURE

### Success Metrics
- [ ] 0 console errors ✅
- [ ] 0 requests to `/workflows/*` ✅
- [ ] 100% action execution success rate ✅
- [ ] All network requests 200/403 (no 404s) ✅
- [ ] Stock updates persist across searches ✅
- [ ] RBAC enforced (CREW blocked from MUTATE) ✅

### Performance Metrics
- [ ] Search response time: ___ ms
- [ ] ContextPanel open time: ___ ms
- [ ] Action execution time: ___ ms
- [ ] Page load time: ___ ms

### UX Metrics
- [ ] Toasts appear for all actions ✅
- [ ] Loading states visible ✅
- [ ] Error messages clear ✅
- [ ] Forms validate properly ✅

---

## ✅ COMPLETION CHECKLIST

- [ ] HOD journey complete (all 14 scenarios)
- [ ] CREW journey complete (all 6 scenarios)
- [ ] CAPTAIN journey complete (all 3 scenarios)
- [ ] Edge cases tested (all 10 scenarios)
- [ ] Console monitoring complete
- [ ] Network monitoring complete
- [ ] Metrics captured
- [ ] Issues documented
- [ ] Screenshots captured
- [ ] Final report generated

---

**Test Start Time**: [TO BE FILLED]
**Test End Time**: [TO BE FILLED]
**Total Test Duration**: 6 hours
**Tester**: Claude Code Assistant + Real Browser
**Status**: 🟡 In Progress
