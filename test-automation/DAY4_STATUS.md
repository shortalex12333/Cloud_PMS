# Day 4: Frontend Testing with Playwright

**Date:** 2026-02-10
**Status:** STARTING NOW ⏳

---

## Goal

**UI perfect, zero 404s, all critical user journeys working**

Test frontend at app.celeste7.ai with headless browser:
- Login flow for all user roles
- Search → Results → Actions flow
- Lens switching (Parts/Work Orders/Equipment/Faults)
- Action button execution
- Error handling and edge cases
- Capture screenshots for evidence

---

## Frontend Architecture

**Target:** https://app.celeste7.ai
**Type:** Single-page React app
**Dynamic:** Lens changes based on search context
**No fragments:** URL stays `app.celeste7.ai` (no /parts, /work-orders)

**User Roles:**
- Captain (x@alex-short.com)
- HOD (hod.test@alex-short.com)
- Crew (crew.test@alex-short.com)

---

## Hours 1-4: Comprehensive Frontend Testing

### Test Matrix:

**1. Login Flow (All Roles)**
- [ ] Captain login → Dashboard renders
- [ ] HOD login → Dashboard renders
- [ ] Crew login → Dashboard renders
- [ ] Invalid credentials → Error message
- [ ] Expired JWT → Redirect to login
- [ ] JWT refresh works

**2. Search Flow**
- [ ] Search "filter" → Parts lens activates
- [ ] Search "work order" → Work Orders lens activates
- [ ] Search "equipment" → Equipment lens activates
- [ ] Empty search → Shows recent items
- [ ] Invalid query → Graceful handling
- [ ] Search results render correctly

**3. Lens Switching**
- [ ] Parts lens: Shows part cards
- [ ] Work Orders lens: Shows WO cards
- [ ] Equipment lens: Shows equipment cards
- [ ] Faults lens: Shows fault cards
- [ ] Lens indicator visible (UI shows current lens)
- [ ] Domain detection accurate

**4. Action Buttons**
- [ ] "View Details" button visible
- [ ] "Create Work Order" button visible
- [ ] "Log Usage" button visible (Parts lens)
- [ ] Button click → Action executes
- [ ] Success message appears
- [ ] Error handling works

**5. RBAC Enforcement**
- [ ] Captain sees all actions
- [ ] HOD sees management actions
- [ ] Crew sees limited actions
- [ ] Disabled buttons for unauthorized actions
- [ ] Error message for forbidden actions

**6. Edge Cases**
- [ ] No network → Error message
- [ ] Slow response → Loading indicator
- [ ] 404 from backend → User-friendly error
- [ ] 500 from backend → User-friendly error
- [ ] Session timeout → Redirect to login

---

## Hours 5-8: Fixes & Optimization

### Expected Issues:

1. **UI Errors:**
   - Console errors (React warnings, etc.)
   - Missing error boundaries
   - Unhandled promise rejections

2. **Routing Issues:**
   - 404s from incorrect API paths
   - CORS errors
   - Auth token not sent correctly

3. **UX Issues:**
   - Loading states missing
   - Error messages unclear
   - Actions don't provide feedback

4. **Performance:**
   - Slow page load
   - Janky animations
   - Large bundle size

---

## Success Criteria

- [ ] All 3 user roles can log in successfully
- [ ] Search → Results → Actions flow works end-to-end
- [ ] All 4 lenses render correctly
- [ ] Action buttons execute without errors
- [ ] Zero 404 errors on valid requests
- [ ] Zero console errors on happy path
- [ ] All critical paths have screenshot evidence
- [ ] RBAC enforcement working correctly

---

## Playwright Setup

**Required:**
- Playwright installed (`npm install -D @playwright/test`)
- Browsers installed (`npx playwright install`)
- Test config at `playwright.config.ts`

**Test Location:**
- `test-automation/frontend/` (new directory)
- Or `apps/web/tests/playwright/` (if exists)

---

**Starting:** Now
**Target Completion:** 8 hours
