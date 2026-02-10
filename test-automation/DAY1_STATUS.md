# Day 1: Infrastructure & Baseline Testing

**Date:** 2026-02-10
**Status:** IN PROGRESS ⏳

---

## Hours 1-2: Setup (STARTING NOW)

### Task 1.1: Install Dependencies ✅
```bash
# Python dependencies for testing
pip install pytest pytest-playwright requests supabase

# Playwright browser
playwright install chromium
```

### Task 1.2: Create Test Harness
- [ ] Automated test runner
- [ ] Results logging
- [ ] Screenshot capture
- [ ] Performance metrics

### Task 1.3: Environment Setup
- [ ] Load test credentials
- [ ] Verify API connectivity
- [ ] Verify database access

---

## Hours 3-4: Baseline Tests (NEXT)

### Journey Tests to Run:
1. Search & Domain Detection
2. Action Button Execution
3. Image Operations
4. RBAC Enforcement
5. Lens Switching
6. End-to-End Flows

### Expected Baseline:
- Some tests will fail (that's OK)
- Capture ALL failures
- Prioritize by severity
- Document root causes

---

## Hours 5-8: Initial Fixes

### Critical Bugs to Fix:
1. Database trigger constraint (image upload duplicate)
2. Test data setup (ensure parts exist)
3. Any 404s or 500s found

### Fix Strategy:
- Fix immediately if pattern recognized
- Document each fix
- Retest after fix
- Commit working code

---

## Success Criteria

- ✅ Test infrastructure working
- ✅ All 6 journeys tested
- ✅ Baseline metrics captured
- ✅ Top 3 critical bugs fixed
- ✅ Day 1 report generated

---

**Next Update:** After baseline tests complete
