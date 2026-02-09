# 6-Hour Comprehensive Testing Session
## Shopping List Lens - Production Validation

**Date**: 2026-02-09
**Deployment**: bffb436 (CRITICAL FIX: useActionHandler)
**App URL**: https://app.celeste7.ai
**Duration**: 6 hours
**Status**: 🟡 IN PROGRESS

---

## Test Credentials

| Role | Email | Password | User ID |
|------|-------|----------|---------|
| HOD | hod.test@alex-short.com | Password2! | TBD (from login) |
| CREW | crew.test@alex-short.com | Password2! | TBD (from login) |
| CAPTAIN | x@alex-short.com | Password2! | TBD (from login) |

**Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`

---

## Critical Fix Being Tested

**Commit**: `bffb436`

**What Changed**:
- ✅ useActionHandler now calls `/v1/actions/execute` (correct)
- ❌ Was calling `/workflows/{archetype}` (404 errors)
- ✅ Updated payload format to match Action Router spec
- ✅ All action buttons will now execute correctly

**Impact**: Without this fix, ALL action buttons in the UI would fail with 404.

---

## Testing Methodology

### Real User Login Flow
1. Navigate to https://app.celeste7.ai
2. Log in with test credentials (gets fresh JWT with auto-refresh)
3. Perform actions via UI buttons (not direct API calls)
4. JWT will auto-refresh during session
5. Verify actions execute correctly

### What We're Testing
1. ✅ Shopping List Lens (all 5 actions)
2. ✅ Action buttons work (useActionHandler fix)
3. ✅ JWT refresh during session
4. ✅ Real UI workflows
5. ✅ Database migration (is_candidate_part)

---

## Hour 1: Deployment & Initial Validation (0:00 - 1:00)

### Tasks
- [ ] Monitor Render deployment completion
- [ ] Verify app.celeste7.ai is serving bffb436
- [ ] Test login for all 3 users
- [ ] Verify JWT tokens are issued correctly
- [ ] Navigate to shopping list section

### Success Criteria
- ✅ Deployment completes without errors
- ✅ All users can log in
- ✅ JWT tokens issued and stored
- ✅ App loads without console errors

---

## Hour 2: Shopping List - Create & View (1:00 - 2:00)

### Tests

#### Test 2.1: CREW Creates Shopping List Item
**User**: crew.test@alex-short.com
**Action**: create_shopping_list_item

**Steps**:
1. Log in as CREW
2. Navigate to shopping list
3. Click "Create Item" button
4. Fill form:
   - Part Name: "Test Engine Oil Filter"
   - Quantity: 5
   - Source Type: "Inventory Low"
   - Urgency: "High"
5. Submit

**Expected**:
- ✅ Item created successfully
- ✅ Status: "candidate"
- ✅ is_candidate_part: true (database fix)
- ✅ Shows in shopping list view
- ✅ No 404 errors (useActionHandler fix working)

**Actual**: _To be filled during test_

---

#### Test 2.2: View Shopping List History
**User**: crew.test@alex-short.com
**Action**: view_shopping_list_history

**Steps**:
1. Find item created in Test 2.1
2. Click "View History" button
3. Verify history displays

**Expected**:
- ✅ History shows "Created" event
- ✅ Response uses `data.history` format
- ✅ Shows creator, timestamp

**Actual**: _To be filled during test_

---

## Hour 3: Shopping List - Approve Workflow (2:00 - 3:00)

### Tests

#### Test 3.1: HOD Approves Item
**User**: hod.test@alex-short.com
**Action**: approve_shopping_list_item

**Steps**:
1. Log in as HOD
2. Navigate to shopping list
3. Find "Test Engine Oil Filter" item
4. Click "Approve" button
5. Enter:
   - Quantity Approved: 5
   - Approval Notes: "Approved for ordering"
6. Submit

**Expected**:
- ✅ Item approved successfully
- ✅ Status transitions: candidate → under_review → approved
- ✅ State history updated (2 entries)
- ✅ Approval notes saved

**Actual**: _To be filled during test_

---

#### Test 3.2: CREW Cannot Approve (Permission Test)
**User**: crew.test@alex-short.com
**Action**: approve_shopping_list_item

**Steps**:
1. Log in as CREW
2. Try to approve an item
3. Verify permission denied

**Expected**:
- ✅ Approve button disabled OR
- ✅ 403 Forbidden error
- ✅ Error message: "Only HoD can approve"

**Actual**: _To be filled during test_

---

## Hour 4: Shopping List - Reject & Promote (3:00 - 4:00)

### Tests

#### Test 4.1: HOD Rejects Item
**User**: hod.test@alex-short.com
**Action**: reject_shopping_list_item

**Steps**:
1. Create new item as CREW
2. Log in as HOD
3. Click "Reject" button
4. Enter rejection reason: "Out of budget"
5. Submit

**Expected**:
- ✅ Item rejected successfully
- ✅ Status: "rejected" (terminal state)
- ✅ Rejection reason stored
- ✅ Cannot approve after rejection

**Actual**: _To be filled during test_

---

#### Test 4.2: Promote Candidate to Part Catalog
**User**: hod.test@alex-short.com
**Action**: promote_candidate_to_part

**Steps**:
1. Create item as CREW (ensure is_candidate_part=true)
2. Approve as HOD
3. Click "Promote to Catalog" button
4. Submit

**Expected**:
- ✅ Item promoted successfully
- ✅ Added to parts catalog
- ✅ is_candidate_part set to false
- ✅ **NO "already in catalog" error** (database fix working!)

**Actual**: _To be filled during test_

**⚠️ Critical Test**: This was broken before the migration. If this works, the fix is successful!

---

## Hour 5: Playwright E2E Automation (4:00 - 5:00)

### Run Full Test Suite

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Run shopping list comprehensive tests
npx playwright test tests/e2e/shopping-list-lens-comprehensive.spec.ts --workers=10

# Expected: 36 tests pass
```

### Tests Covered
1. CREATE: All source types, urgency levels, edge cases
2. APPROVE: Full quantity, partial quantity, permission tests
3. REJECT: With reason, permission tests, state validation
4. VIEW_HISTORY: State transitions, timeline display
5. PROMOTE: Candidate to catalog (critical fix)

**Expected Results**:
- ✅ 36/36 tests pass
- ✅ No 404 errors (useActionHandler working)
- ✅ No JWT expiration (auto-refresh working)
- ✅ All assertions match API format (test fixes applied)

**Actual**: _To be filled during test_

---

## Hour 6: Edge Cases & Stress Testing (5:00 - 6:00)

### Tests

#### Test 6.1: JWT Auto-Refresh During Long Session
**Duration**: 30 minutes

**Steps**:
1. Log in as CREW
2. Keep session active for 30 minutes
3. Perform actions periodically
4. Monitor network tab for token refresh

**Expected**:
- ✅ JWT refreshes automatically before expiration
- ✅ No "unauthorized" errors
- ✅ Actions continue to work

**Actual**: _To be filled during test_

---

#### Test 6.2: Concurrent Actions (Multiple Users)
**Users**: CREW + HOD simultaneously

**Steps**:
1. CREW creates 5 items (rapid succession)
2. HOD approves items concurrently
3. Verify no race conditions

**Expected**:
- ✅ All items created successfully
- ✅ All approvals processed
- ✅ No database conflicts
- ✅ State history correct for all

**Actual**: _To be filled during test_

---

#### Test 6.3: Edge Case Inputs

| Test | Input | Expected |
|------|-------|----------|
| Unicode | Part name: "🔧 Filtre à huile" | ✅ Accepted |
| Long string | Part name: 500 chars | ✅ Accepted |
| Special chars | Part name: "Filter (1/2\" NPT)" | ✅ Accepted |
| Decimal qty | Quantity: 2.5 liters | ✅ Accepted |
| Zero qty | Quantity: 0 | ❌ Rejected |
| Negative qty | Quantity: -5 | ❌ Rejected |

**Actual**: _To be filled during test_

---

## Test Results Summary

### Overall Status
- **Tests Planned**: TBD
- **Tests Executed**: 0 / TBD
- **Tests Passed**: 0
- **Tests Failed**: 0
- **Bugs Found**: 0
- **Critical Issues**: 0

### Key Metrics
- **useActionHandler Fix**: ⏳ Pending validation
- **is_candidate_part Fix**: ⏳ Pending validation
- **JWT Auto-Refresh**: ⏳ Pending validation
- **UI Action Buttons**: ⏳ Pending validation
- **Shopping List Actions**: 0 / 5 tested

---

## Issues Found

_To be filled during testing_

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| - | - | - | - |

---

## Deployment Validation Checklist

- [ ] Deployment completed successfully
- [ ] App loads at app.celeste7.ai
- [ ] Git commit bffb436 confirmed in production
- [ ] Console shows no critical errors
- [ ] Users can log in successfully
- [ ] JWT tokens issued correctly

---

## Shopping List Action Validation

- [ ] create_shopping_list_item - CREW can create
- [ ] approve_shopping_list_item - HOD can approve
- [ ] reject_shopping_list_item - HOD can reject
- [ ] view_shopping_list_history - History displays correctly
- [ ] promote_candidate_to_part - Promotion works (critical fix)

---

## Critical Fixes Validation

- [ ] useActionHandler calls /v1/actions/execute (not /workflows)
- [ ] Action buttons execute without 404 errors
- [ ] is_candidate_part stored correctly in database
- [ ] promote_candidate_to_part no longer shows "already in catalog"

---

## Performance & Reliability

- [ ] Actions complete in < 2 seconds
- [ ] No console errors during testing
- [ ] JWT refresh works automatically
- [ ] Concurrent operations handle correctly
- [ ] State history accurate for all actions

---

## Next Steps

After 6 hours:
1. Compile final test results
2. Document any issues found
3. Update deployment confidence level
4. Recommend production go/no-go

---

**Session Start**: _To be filled_
**Session End**: _To be filled_
**Total Duration**: 6 hours
**Tester**: Claude Opus 4.5
