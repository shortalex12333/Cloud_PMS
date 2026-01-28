# Quick Start: Action Verification

**Start verifying actions TODAY without getting overwhelmed**

**Time to first action verified:** 15 minutes
**Time to complete Phase 1 (5 actions):** 5 hours
**Time to pattern analysis:** 1 hour
**Total time to bulk fixes:** 2-3 days

---

## 🎯 What You'll Do

1. **Phase 1:** Verify 5 representative actions (5 hours)
2. **Phase 2:** Analyze patterns found (1 hour)
3. **Phase 3:** Fix patterns in bulk (varies)

**Goal:** Find patterns FIRST, fix in bulk LATER

---

## ⚡ Start NOW (15 Minutes)

### Step 1: Setup Environment (5 min)

```bash
# Ensure .env.e2e exists
cp .env.e2e.example .env.e2e

# Fill in credentials (get from team):
# TENANT_SUPABASE_URL=https://...
# TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
# TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
# TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424

# Test connection
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

If test passes → Ready to start verification ✅

### Step 2: Pick First Action (1 min)

**Start with:** `create_work_order` (already has test)

### Step 3: Copy Template (1 min)

```bash
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_create_work_order.md
```

### Step 4: Find Handler (2 min)

```bash
grep -n 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py
```

**Result:** Line 1847-1923 (example)

### Step 5: Fill Template - Handler Section (5 min)

Open `_VERIFICATION/verify_create_work_order.md` and fill in:

```markdown
## Handler Analysis

**File:** apps/api/routes/p0_actions_routes.py
**Line:** 1847-1923
**Tables used:** pms_work_orders
**Validations:** None (relies on DB constraints)
**Audit logging:** NO
**Returns:** {status: 'success', entity_id: ...}
```

### Step 6: Run Test (1 min)

```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

**Did it pass?**
- ✅ Yes → Continue to Step 7
- ❌ No → Note error in template, continue anyway (we're observing, not fixing)

---

## 📋 Phase 1: Verify 5 Actions (5 Hours)

**Time:** 1 hour per action
**Goal:** Find patterns, don't fix bugs

### Actions to Verify

**Pick these 5 for diversity:**
1. `create_work_order` (create entity)
2. `assign_work_order` (update relationship)
3. `add_note` (simple create)
4. `mark_fault_resolved` (status update)
5. `get_work_order_details` (read-only)

### For EACH Action (1 Hour)

**Use the 10-step protocol from VERIFICATION_METHODOLOGY.md:**

1. Copy template (1 min)
2. Read handler code (10 min)
3. Check database schema (5 min)
4. Query BEFORE state (5 min)
5. Execute action (10 min)
6. Query AFTER state (5 min)
7. Check audit log (5 min)
8. Test error cases (10 min)
9. Document findings (10 min)
10. Mark done (1 min)

**Set a timer: 60 minutes**

If you go over, you're going too deep. Document "needs more investigation" and move on.

### Record Findings

**Open:** `_VERIFICATION/PHASE_1_FINDINGS.md`

**For each action, fill in:**
```markdown
### 1. create_work_order

**Date:** 2026-01-22
**Time:** 55 minutes
**Status:** ✅ Verified

**6 Proofs:**
- [x] HTTP 200 returned
- [x] Response contains entity_id
- [x] Database row created
- [x] Database row has correct values
- [ ] Audit log entry created ❌
- [ ] Audit log entry has correct values ❌

**Error cases tested:**
- [ ] 400 for invalid input ❌
- [ ] 404 for invalid entity (N/A)
- [ ] 403 for wrong yacht ⚠️

**Gaps found:**
1. Missing audit log
2. No input validation
3. RLS not verified

**Notes:**
Handler doesn't call audit logging function. No Pydantic validation.
```

### Avoid Overwhelm

**If you notice issues in OTHER actions while verifying current action:**

→ Write in `_VERIFICATION/RELATED_ISSUES.md`
→ Don't stop current verification
→ Don't try to fix other actions

**Example:**
```markdown
# RELATED_ISSUES.md

### Issue: assign_work_order also missing audit

**Found while verifying:** create_work_order
**Severity:** HIGH
**Description:** Noticed assign_work_order handler also doesn't write to pms_audit_log

**Why not fixing now:** Outside scope of current verification. Likely a pattern (will fix in bulk).
```

---

## 🔍 Phase 2: Pattern Analysis (1 Hour)

**When:** After completing 5 action verifications
**Input:** PHASE_1_FINDINGS.md
**Output:** PATTERN_ANALYSIS.md

### Process

**Open:** `_VERIFICATION/PATTERN_ANALYSIS.md`

**Look for patterns:**
1. How many actions missing audit logs? (4/5 = 80% = PATTERN)
2. How many actions missing validation? (3/5 = 60% = PATTERN)
3. How many actions missing RLS tests? (5/5 = 100% = PATTERN)

**For each pattern, document:**
```markdown
### Pattern H1: Missing Audit Logs

**Severity:** HIGH (compliance requirement)
**Scope:** 4/5 actions (80%)
**Actions affected:**
- create_work_order
- assign_work_order
- mark_fault_resolved
- get_work_order_details (expected for read-only)

**Root Cause:**
No enforcement mechanism, audit logging not part of handler template

**Fix Approach:**
1. Create audit helper function
2. Add to ALL mutation handlers (~30 actions)
3. Create test helper to verify audit
4. Add to ALL mutation tests

**Estimated Effort:** 5 hours (10 min per action × 30 actions)
**Priority:** 1 (fix first)
```

**Prioritize patterns:**
1. High severity first (security, compliance)
2. Then medium severity (UX, validation)
3. Then low severity (optimizations)

---

## 🔧 Phase 3: Bulk Fixes (Varies)

**When:** After pattern analysis
**Goal:** Fix patterns, not individual bugs

### For Each Pattern (High → Low Priority)

**Open:** `_VERIFICATION/PATTERN_FIXES.md`

**Document the fix:**

1. **Design the solution ONCE**
   - Example: Create `write_audit_log()` helper function

2. **Apply to ALL affected actions**
   - Don't fix 1 at a time
   - Use search/replace where possible
   - Fix all 30 actions in one pass

3. **Test the pattern fix**
   - Create test helper that verifies pattern
   - Run on all affected actions

4. **Document results**
   - How many actions fixed?
   - Test pass rate?
   - Any issues?

**Example:**

```markdown
# PATTERN_FIXES.md

### Fix H1: Missing Audit Logs

**Actions affected:** 30
**Time spent:** 6 hours

**Implementation:**
1. Created apps/api/utils/audit.py helper ✅
2. Added to 30 handlers ✅
3. Created tests/helpers/audit.ts test helper ✅
4. Updated 30 tests ✅

**Test Results:**
- Pass rate: 28/30 (93%)
- Issues: 2 actions had unrelated test failures

**Verification:**
Audit log entries before: 10
Audit log entries after: 500+
✅ Pattern fixed successfully
```

---

## 🚨 How to Not Get Overwhelmed

### Rule 1: ONE ACTION AT A TIME
Close all files except:
- Template you're filling in
- Handler code for current action
- Test for current action

### Rule 2: SET A TIMER
60 minutes per action. If over → note "needs investigation" and move on.

### Rule 3: OBSERVE, DON'T FIX
Document gaps, don't try to fix them yet.

### Rule 4: USE THE CHECKLIST
Don't work from memory. Follow template exactly.

### Rule 5: SIDE ISSUES → RELATED_ISSUES.MD
Don't let side issues distract from current action.

---

## ✅ Success Checklist

**After Phase 1 (5 actions), you should have:**
- [ ] 5 completed verification documents
- [ ] PHASE_1_FINDINGS.md filled in
- [ ] Clear list of patterns identified
- [ ] RELATED_ISSUES.md with any side issues found
- [ ] Total time: ~5 hours

**After Phase 2 (pattern analysis), you should have:**
- [ ] PATTERN_ANALYSIS.md filled in
- [ ] Patterns prioritized (high → medium → low)
- [ ] Fix approach designed for each pattern
- [ ] Total time: ~1 hour

**After Phase 3 (bulk fixes), you should have:**
- [ ] PATTERN_FIXES.md documenting all fixes
- [ ] Test pass rate for each pattern fix
- [ ] All 64 actions compliant with standards
- [ ] Total time: ~2-3 days

---

## 📁 Files You'll Use

### Read These First (15 min)
1. **VERIFICATION_METHODOLOGY.md** - Full methodology explanation
2. **TESTING_STANDARDS.md** - What is success?
3. **QUICK_REFERENCE.md** - Copy-paste commands

### Fill These During Verification
1. **_VERIFICATION/verify_[action].md** - One per action (use template)
2. **_VERIFICATION/PHASE_1_FINDINGS.md** - Summary of 5 actions
3. **_VERIFICATION/RELATED_ISSUES.md** - Side issues found
4. **_VERIFICATION/PATTERN_ANALYSIS.md** - Pattern categorization
5. **_VERIFICATION/PATTERN_FIXES.md** - Bulk fix documentation

### Reference During Work
1. **DATABASE_RELATIONSHIPS.md** - Table schemas, RLS policies
2. **CUSTOMER_JOURNEY_FRAMEWORK.md** - How users trigger actions
3. **GLOSSARY.md** - Term definitions

---

## 💡 Pro Tips

1. **Start with create_work_order** - Already has test, well-documented
2. **Set timer for 60 min** - Prevents going too deep
3. **Copy-paste from QUICK_REFERENCE.md** - Don't retype commands
4. **Document as you go** - Don't rely on memory
5. **Take breaks** - After each action, 5 min break
6. **One action per session** - Better focus
7. **Morning = verification** - Afternoon = analysis/fixing
8. **Trust the process** - Patterns will emerge after 5 actions

---

## 🚀 Start NOW

**Ready to begin? Run these commands:**

```bash
# 1. Copy template
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_create_work_order.md

# 2. Find handler
grep -n 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py

# 3. Run test
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts

# 4. Open template and start filling in
# _VERIFICATION/verify_create_work_order.md
```

**Set timer: 60 minutes**

**Go!** 🏃

---

## 📞 When You Get Stuck

**Problem:** Don't know what to verify
**Solution:** Follow 6 proofs checklist in TESTING_STANDARDS.md

**Problem:** Test is failing
**Solution:** Document failure, don't spend >15 min investigating

**Problem:** Found bugs in other actions
**Solution:** Write in RELATED_ISSUES.md, stay focused on current action

**Problem:** Going over 1 hour per action
**Solution:** You're going too deep. Document "needs more investigation" and move on

**Problem:** Not sure if this is a pattern
**Solution:** Document in PHASE_1_FINDINGS.md, analyze after 5 actions

**Problem:** Want to fix bug NOW
**Solution:** NO. Document it. Fix in bulk during Phase 3.

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Purpose:** Get started verifying actions TODAY without overwhelm
**Time to complete:** 2-3 days total (5 hours Phase 1 + 1 hour Phase 2 + 1-2 days Phase 3)

**Next steps:** Copy template, find handler, set timer, GO! 🚀
