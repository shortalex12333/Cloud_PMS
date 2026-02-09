# Parts Lens - Comprehensive Frontend Test Plan
## 6-Hour Testing Window: app.celeste7.ai

**Deployment:** `bffb436` - CRITICAL frontend action handler fix
**Target:** Single-page app with dynamic UX (no URL fragments)
**Duration:** 6 hours
**Date:** 2026-02-09

---

## TEST CREDENTIALS

```
CAPTAIN: x@alex-short.com / Password2!
HOD:     hod.test@alex-short.com / Password2!
CREW:    crew.test@alex-short.com / Password2!
YACHT:   85fe1119-b04c-41ac-80f1-829d23322598
```

---

## CRITICAL CONTEXT: Single-Page Dynamic UX

**URL:** `app.celeste7.ai` (no fragments, no /app/parts routes)
**Behavior:** Dynamic UI that changes based on detected "lens" (domain)
**Example:** Search "teak seam compound" → UI shows Parts Lens actions/context

---

## TEST METHODOLOGY

### 1. Real User Login (JWT Refresh)
- Log in via actual login form
- JWT refreshes automatically
- Test with real session state

### 2. Search-Driven Lens Detection
- Enter query in search bar
- Backend detects domain (parts/work_order/equipment/etc.)
- Frontend dynamically renders appropriate lens UI

### 3. Action Button Validation
- Click action buttons in Parts Lens context
- **CRITICAL FIX (bffb436):** Buttons now call `/v1/actions/execute` (not `/workflows`)
- Verify actions execute correctly (no 404s)

---

## PARTS LENS TEST MATRIX

### Journey 1: Captain - Search & View Part Details

**User:** CAPTAIN (x@alex-short.com)
**Goal:** Search for marine part, see Parts Lens UI, view details

#### Steps:
1. **Login**
   - Go to `app.celeste7.ai`
   - Enter: x@alex-short.com / Password2!
   - Click "Sign In"
   - ✅ Verify: Dashboard loads, JWT obtained

2. **Search for Marine Part**
   - Click search bar (or focus search input)
   - Type: `teak seam compound for deck maintenance`
   - Press Enter or click Search

3. **Verify Domain Detection**
   - ✅ Backend detects `domain=parts` (PR #208 marine anchors)
   - ✅ Frontend renders Parts Lens UI (dynamic change)
   - ✅ Search results show parts/inventory items

4. **Expected Parts Lens UI Elements**
   - **Context Panel:** Shows parts-specific context
   - **Action Buttons:**
     - "View Part Details"
     - "Check Stock Level"
     - "Log Part Usage"
     - "Create Work Order" (if applicable)
   - **Search Results:** Parts cards with:
     - Part name
     - Part number
     - Stock level
     - Location
     - Image thumbnail (if exists)

5. **Click "View Part Details" Action**
   - Click the "View Part Details" button
   - ✅ Verify: Calls `/v1/actions/execute` (not `/workflows`) - bffb436 fix
   - ✅ Verify: Detail modal/panel opens
   - ✅ Verify: Shows part specifications, history, attachments

**Expected Result:** ✅ Parts Lens UI renders, buttons work, no 404 errors

**If Fails:** Check browser console for:
- Domain detection returned `null` → PR #208 not deployed
- 404 on button click → bffb436 not deployed
- JWT expired → Re-login

---

### Journey 2: HOD - Upload Part Image

**User:** HOD (hod.test@alex-short.com)
**Goal:** Search for part, upload image, verify storage

#### Steps:
1. **Login as HOD**
   - Login: hod.test@alex-short.com / Password2!

2. **Search for Part Without Image**
   - Search: `Raw Water Pump Seal`
   - ✅ Verify: Parts Lens UI appears

3. **Navigate to Part Details**
   - Click part from search results
   - Detail view opens

4. **Upload Image**
   - Look for "Upload Image" button or image section
   - Click "Upload Image" or similar action
   - **Expected:** Modal/form appears
   - Select test image file (PNG/JPEG)
   - Optional: Add description
   - Click "Upload" or "Submit"

5. **Verify Upload**
   - ✅ Verify: Success message appears
   - ✅ Verify: Image thumbnail appears in part details
   - ✅ Verify: No HTTP 500 error (PR #208 JWT fix deployed)
   - ✅ Verify: Calls `/v1/parts/upload-image` correctly

6. **Verify Persistence**
   - Refresh page
   - Search for same part again
   - ✅ Verify: Image still appears

**Expected Result:** ✅ Image uploads successfully, persists across sessions

**If Fails:** Check:
- HTTP 500: PR #208 JWT fix not deployed
- 404: Endpoint route issue
- 403: RBAC issue (HOD should have permission)

---

### Journey 3: Crew - Create Work Order (RBAC)

**User:** CREW (crew.test@alex-short.com)
**Goal:** Search for part issue, create work order, verify RBAC

#### Steps:
1. **Login as Crew**
   - Login: crew.test@alex-short.com / Password2!

2. **Search for Part Needing Maintenance**
   - Search: `bilge pump maintenance`
   - ✅ Verify: Parts Lens or Work Order Lens appears

3. **Create Work Order via Action Button**
   - Click "Create Work Order" button
   - **CRITICAL:** Button now calls `/v1/actions/execute` (bffb436 fix)
   - Modal/form opens

4. **Fill Work Order Form**
   - Title: "Bilge pump inspection - E2E test"
   - Department: **DECK** (crew's department - RBAC enforced)
   - Priority: Medium
   - Description: "Testing crew WO creation"
   - Click "Create" or "Submit"

5. **Verify RBAC Success**
   - ✅ Verify: Work order created (HTTP 200, not 403)
   - ✅ Verify: Success message appears
   - ✅ Verify: PR #194 RBAC fix working (crew CAN create for their department)

6. **Try Creating WO for Wrong Department (Negative Test)**
   - Create another WO with Department: **ENGINEERING**
   - ✅ Verify: Should FAIL with 403 (crew cannot create for other departments)

**Expected Result:** ✅ Crew creates WO for own department, blocked for others

**If Fails:** Check:
- 403 for own department → RBAC metadata missing (crew.metadata->department)
- 404 on button click → bffb436 not deployed
- 409 → Idempotency collision (expected if running multiple times)

---

### Journey 4: Captain - Delete Part Image (SIGNED Action)

**User:** CAPTAIN (x@alex-short.com)
**Goal:** Delete part image with signature (PIN + TOTP)

#### Steps:
1. **Login as Captain**
   - Login: x@alex-short.com / Password2!

2. **Search for Part with Image**
   - Search for part uploaded in Journey 2
   - Open part details

3. **Initiate Delete Image**
   - Click "Delete Image" or trash icon
   - **Expected:** Signature modal appears (SIGNED action)

4. **Provide Signature**
   - Enter PIN: (captain's PIN)
   - Enter TOTP: (from authenticator app if required)
   - Optional: Enter reason: "E2E test cleanup"
   - Click "Confirm Delete"

5. **Verify Deletion**
   - ✅ Verify: Image removed from part
   - ✅ Verify: Success message
   - ✅ Verify: Audit log entry created (can check via backend)

**Expected Result:** ✅ Captain can delete image with signature

**If Fails:** Check:
- Missing signature modal → Frontend config issue
- 403 → Only captain/admin can delete (correct behavior for other roles)
- 500 → Backend issue

---

### Journey 5: Search Edge Cases & Lens Switching

**User:** Any (test with CAPTAIN)
**Goal:** Verify dynamic lens switching based on query

#### Test Cases:

##### 5a. Parts Lens Queries
**Queries to test:**
- "teak seam compound" → domain=parts
- "antifouling paint" → domain=parts
- "sikaflex sealant" → domain=parts
- "caterpillar filter" → domain=parts
- "low stock items" → domain=parts

**Expected:** All trigger Parts Lens UI

##### 5b. Work Order Lens Queries
**Queries to test:**
- "create work order for engine" → domain=work_order
- "maintenance schedule" → domain=work_order
- "pending work orders" → domain=work_order

**Expected:** UI switches to Work Order Lens (different buttons/context)

##### 5c. Equipment Lens Queries
**Queries to test:**
- "port main engine status" → domain=equipment
- "generator runtime hours" → domain=equipment

**Expected:** UI switches to Equipment Lens

##### 5d. Vague/Explore Mode
**Queries to test:**
- "check something" → domain=null
- "" (empty) → domain=null
- "xyz abc 123" → domain=null

**Expected:** Explore mode (generic search, no specific lens)

**Validation:** For each query:
1. Check browser console for domain detection response
2. Observe UI changes (context panel, action buttons)
3. Verify correct lens activated

---

### Journey 6: Action Button Execution (CRITICAL - bffb436)

**User:** HOD (hod.test@alex-short.com)
**Goal:** Verify all Parts Lens action buttons execute correctly

#### Action Buttons to Test:

##### 6a. "Check Stock Level"
1. Search for any part
2. Click "Check Stock Level" button
3. ✅ Verify: Calls `/v1/actions/execute` with `action: "check_stock_level"`
4. ✅ Verify: Returns stock data (no 404)
5. ✅ Verify: UI shows stock information

##### 6b. "Log Part Usage"
1. Search for consumable part
2. Click "Log Part Usage" button
3. ✅ Verify: Modal/form opens
4. Fill quantity used
5. Submit
6. ✅ Verify: Usage logged, stock decremented

##### 6c. "View Part Details"
1. Already tested in Journey 1

##### 6d. "Update Part Information"
1. Click "Update Part Information"
2. ✅ Verify: Form opens with current data
3. Update fields (e.g., location, notes)
4. Submit
5. ✅ Verify: Updates saved

**Expected Result:** ✅ All buttons call correct endpoint, execute successfully

**If Fails:** Check browser Network tab:
- Calls to `/workflows/*` → bffb436 NOT deployed (CRITICAL)
- Calls to `/v1/actions/execute` → bffb436 IS deployed ✅
- 404 responses → Endpoint routing issue

---

## PERFORMANCE METRICS TO TRACK

### Response Times
- Search query → domain detection: < 3 seconds
- Action button click → execution: < 2 seconds
- Image upload → confirmation: < 5 seconds
- Page navigation: < 1 second

### UI Responsiveness
- Lens switching: Instant (no flicker)
- Action button feedback: Immediate (spinner/loading state)
- Search results rendering: < 1 second

### Error Handling
- Invalid JWT: Redirect to login
- 403 Forbidden: Show permission error message
- 500 Server Error: Show user-friendly error
- Network timeout: Retry or show offline message

---

## BROWSER CONSOLE CHECKS

For each journey, check browser DevTools Console for:

### ✅ Success Indicators
```
Domain detected: parts (confidence: 0.9)
Action executed: check_stock_level
JWT refreshed successfully
Image uploaded: <storage_path>
```

### ❌ Error Indicators
```
404 /workflows/view_part_details → bffb436 not deployed!
500 'ValidationResult' object has no attribute 'get' → PR #208 not deployed!
403 Forbidden → RBAC issue
Domain detection returned null → PR #208 anchors missing
```

---

## NETWORK TAB VALIDATION

For each action button click, verify:

### Request URL
- ✅ CORRECT: `POST https://pipeline-core.int.celeste7.ai/v1/actions/execute`
- ❌ WRONG: `POST https://pipeline-core.int.celeste7.ai/workflows/{archetype}`

### Request Payload
```json
{
  "action": "check_stock_level",
  "context": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
  },
  "payload": {
    "part_id": "<uuid>"
  }
}
```

### Response
- Status: 200 OK
- Body: Contains result data (not 404/500)

---

## TEST EXECUTION CHECKLIST

### Pre-Test Setup
- [ ] Confirm deployment: `bffb436` deployed to production
- [ ] Verify backend version: Check commit in `/version` endpoint
- [ ] Clear browser cache/cookies
- [ ] Open browser DevTools (Console + Network tabs)

### Test Execution
- [ ] **Journey 1:** Captain searches & views parts (20 min)
- [ ] **Journey 2:** HOD uploads part image (15 min)
- [ ] **Journey 3:** Crew creates work order (15 min)
- [ ] **Journey 4:** Captain deletes image (SIGNED) (10 min)
- [ ] **Journey 5:** Lens switching tests (30 min)
- [ ] **Journey 6:** All action buttons (40 min)

### Post-Test Validation
- [ ] Review all console logs
- [ ] Check Network tab for failed requests
- [ ] Document any errors/issues
- [ ] Verify data persistence (refresh tests)

---

## EXPECTED OUTCOMES

### ✅ All Tests Pass (Ideal)
- Parts Lens UI renders correctly
- Domain detection works for marine parts (PR #208)
- Action buttons call `/v1/actions/execute` (bffb436)
- Image upload/update/delete work (PR #208 JWT fix)
- RBAC enforced correctly (PR #194)
- No 404/500 errors
- JWT auto-refreshes

### ⚠️ Partial Pass (Some Issues)
- Domain detection fails for marine parts → PR #208 not deployed
- Action buttons 404 → bffb436 not deployed
- Image operations 500 → PR #208 JWT fix not deployed

### ❌ Major Failures
- Cannot login → Auth system issue
- No search results → Backend down
- All buttons 404 → Wrong deployment

---

## ISSUE REPORTING TEMPLATE

If test fails, document:

```markdown
### Issue: [Brief description]

**Journey:** [Journey number and name]
**User:** [CAPTAIN/HOD/CREW]
**Step:** [Which step failed]

**Expected:**
[What should have happened]

**Actual:**
[What actually happened]

**Browser Console:**
```
[Paste console errors]
```

**Network Request:**
- URL: [Request URL]
- Status: [HTTP status code]
- Response: [Error message]

**Screenshot:** [If applicable]

**Suspected Cause:**
- [ ] PR #208 not deployed (JWT fix)
- [ ] bffb436 not deployed (action handler fix)
- [ ] Frontend config issue
- [ ] RBAC permissions issue
- [ ] Other: ___________
```

---

## MANUAL TESTING SCRIPT

For each journey, follow this pattern:

```
1. Open app.celeste7.ai in browser
2. Open DevTools (F12)
3. Switch to Console + Network tabs
4. Execute journey steps
5. Observe:
   - UI changes (lens switching)
   - Console logs (domain detection)
   - Network requests (endpoint calls)
   - Error messages (if any)
6. Document results
```

---

## AUTOMATED TESTING ALTERNATIVE

If you have Playwright/Cypress, run:

```typescript
// Example Playwright test
test('Captain searches for teak compound', async ({ page }) => {
  await page.goto('https://app.celeste7.ai');
  await page.fill('input[type="email"]', 'x@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button:has-text("Sign In")');

  await page.waitForSelector('[data-testid="search-input"]');
  await page.fill('[data-testid="search-input"]', 'teak seam compound');
  await page.press('[data-testid="search-input"]', 'Enter');

  // Verify Parts Lens UI
  await expect(page.locator('[data-testid="parts-lens-context"]')).toBeVisible();
  await expect(page.locator('button:has-text("View Part Details")')).toBeVisible();
});
```

---

## SUCCESS CRITERIA

After 6-hour testing window, Parts Lens is VALIDATED if:

✅ **Core Functionality**
- [x] Domain detection works for marine parts
- [x] Search returns relevant results
- [x] UI dynamically switches between lenses

✅ **Action Buttons**
- [x] All buttons call `/v1/actions/execute` (not `/workflows`)
- [x] No 404 errors on button clicks
- [x] Actions execute and return results

✅ **RBAC**
- [x] Crew can create WO for own department
- [x] Crew blocked from other departments
- [x] HOD can upload images
- [x] Captain can delete images (SIGNED)

✅ **Image Operations**
- [x] Upload works (no 500 error)
- [x] Update works
- [x] Delete works (with signature)

✅ **User Experience**
- [x] JWT auto-refreshes
- [x] No authentication issues
- [x] Responsive UI
- [x] Helpful error messages

---

## FINAL VALIDATION

Once all journeys pass:

1. **Document Results:** Create test report with screenshots
2. **Performance Metrics:** Log response times
3. **Issue Summary:** List any bugs found
4. **Sign-off:** Parts Lens VALIDATED for production use

---

**Testing Start:** 2026-02-09 (6-hour window)
**Tester:** Manual QA or Automated Suite
**Environment:** app.celeste7.ai (production)
**Deployment:** bffb436
