# Welcome to CelesteOS Cloud PMS

**👋 START HERE - New Engineer Onboarding**

Welcome! You're about to work on a natural language yacht maintenance system. This document will get you from zero to productive in 30 minutes (quick start) or 4 hours (deep dive).

---

## 🎯 What Is This Project?

**CelesteOS Cloud PMS** is a Planned Maintenance System for superyachts with a natural language interface.

**Instead of this (traditional UI):**
```
User: Clicks "Maintenance" → "Work Orders" → "New Work Order" →
      Fills 10-field form → Clicks "Save"
```

**Users do this:**
```
User: Types "create a work order for the generator"
      → System shows button "Create Work Order"
      → User clicks → Pre-filled form opens → Submit
```

**Your job:** Verify that all 64 "microactions" (like `create_work_order`) actually work end-to-end.

---

## 📊 Current State

- **Total Microactions:** 64
- **Verified:** 1/64 (create_work_order)
- **Your Mission:** Help verify the remaining 63

**What "verified" means:**
1. ✅ Database mutation confirmed (not just HTTP 200)
2. ✅ Audit log entry created
3. ✅ Natural language queries detected
4. ✅ Frontend journey tested
5. ✅ All guard rails working
6. ✅ Error messages helpful

---

## ⚡ Quick Start (30 Minutes)

**Goal:** Understand the system basics and run one test

### Step 1: Read Core Concepts (10 minutes)

**Read these files in order:**

1. **GLOSSARY.md** ← Defines: microaction, situation, yacht, tenant, RLS, soft delete
2. **REPOSITORY_MAP.md** ← Shows where everything is
3. **TESTING_STANDARDS.md** ← Defines success vs failure

**Don't read anything else yet.** These 3 files give you 80% of what you need.

### Step 2: Set Up Your Environment (10 minutes)

**Read:**
- **LOCAL_SETUP.md** ← How to install dependencies and run tests

**Then do:**
```bash
# 1. Install dependencies
npm install

# 2. Copy environment file
cp .env.e2e.example .env.e2e

# 3. Fill in credentials (ask team for these)
# Edit .env.e2e with:
# - TENANT_SUPABASE_URL
# - TENANT_SUPABASE_SERVICE_ROLE_KEY
# - TEST_YACHT_ID
# - TEST_USER_ID
```

### Step 3: Run One Test (10 minutes)

**Run the gold standard mutation proof test:**
```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

**Expected output:**
```
✅ create_work_order mutation proof
   - BEFORE: 0 work orders with test title
   - AFTER: 1 work order created
   - Database row verified
   - ⚠️ WARNING: No audit log entry (known gap)

1 passed (2s)
```

**If this passes:** You're set up correctly! ✅

**If this fails:** Check LOCAL_SETUP.md troubleshooting section

---

## 🔍 Deep Dive (4 Hours)

**Goal:** Fully understand the architecture and verification process

### Hour 1: System Architecture (60 minutes)

**Read in this order:**

1. **ARCHITECTURE.md** (20 min)
   - Multi-tenant architecture (Master DB vs Tenant DB)
   - Auth flow (JWT → User context → Yacht access)
   - Pipeline architecture (Query → Action detection → Execution)

2. **MICROACTIONS_EXPLAINED.md** (20 min)
   - What is a microaction?
   - Why 64 microactions?
   - How are they different from REST APIs?

3. **SITUATIONS_EXPLAINED.md** (20 min)
   - What is a situation? (IDLE → CANDIDATE → ACTIVE)
   - How contexts flow from situations to actions
   - State machine diagram

**After reading, you should understand:**
- ✅ Why we have microactions instead of REST endpoints
- ✅ How JWT contains yacht_id and user_id
- ✅ What "situation" means
- ✅ Multi-tenant isolation (RLS)

### Hour 2: Database & Customer Journey (60 minutes)

**Read:**

1. **DATABASE_RELATIONSHIPS.md** (30 min)
   - All tables and columns (ground truth)
   - Foreign key relationships
   - RLS policies
   - Soft delete patterns
   - **Critical:** Column name traps (quantity_on_hand vs current_quantity)

2. **CUSTOMER_JOURNEY_FRAMEWORK.md** (30 min)
   - How users interact with the system
   - Natural language query variants
   - UI journey breakdown (query → button → modal → form)
   - Form fields and validation
   - Guard rails at all layers

**After reading, you should understand:**
- ✅ What tables actually exist (pms_work_orders, not work_orders)
- ✅ How users trigger actions (type query → click button → fill form)
- ✅ What guard rails exist (frontend, backend, database)
- ✅ What "mutation proof" means (BEFORE/AFTER database queries)

### Hour 3: Verification Process (60 minutes)

**Read:**

1. **FRAMEWORK_OVERVIEW.md** (15 min)
   - How to use DATABASE_RELATIONSHIPS + CUSTOMER_JOURNEY together
   - Old approach vs new approach
   - Step-by-step verification workflow

2. **ACTION_VERIFICATION_GUIDE.md** (20 min)
   - Step-by-step instructions
   - Common pitfalls
   - Database connection examples
   - Testing patterns

3. **README_VERIFICATION_SYSTEM.md** (10 min)
   - System overview
   - 215-point checklist explained
   - Three verification levels (Quick, Thorough, Production)

4. **_VERIFICATION/CREATE_WORK_ORDER_DEEP_DIVE.md** (15 min)
   - Complete worked example
   - See what "fully verified" looks like
   - 5,800 words of analysis

**After reading, you should understand:**
- ✅ The 215-point verification checklist
- ✅ How to write mutation proof tests
- ✅ How to write customer journey tests
- ✅ What "done" looks like

### Hour 4: Hands-On Practice (60 minutes)

**Do this:**

1. **Pick a simple action** (15 min)
   ```bash
   # Look at the registry
   cat tests/fixtures/microaction_registry.ts | grep -A 5 "add_work_order_note"
   ```

2. **Research the action** (20 min)
   - Open DATABASE_RELATIONSHIPS.md → Find pms_work_order_notes table
   - Open CUSTOMER_JOURNEY_FRAMEWORK.md → Find "Add Child Entity" template
   - Open apps/api/routes/p0_actions_routes.py → Search for "add_work_order_note"

3. **Copy the template** (5 min)
   ```bash
   cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_add_work_order_note.md
   ```

4. **Fill in Section 4 (Database Mutations)** (20 min)
   - What table? pms_work_order_notes
   - What columns? id, work_order_id, note_text, created_by, created_at
   - What's the BEFORE query? SELECT COUNT(*) FROM pms_work_order_notes WHERE work_order_id = ?
   - What's the AFTER query? SELECT * FROM pms_work_order_notes WHERE work_order_id = ? ORDER BY created_at DESC LIMIT 1

**After this hour:**
- ✅ You've researched an action using both frameworks
- ✅ You've started filling in the template
- ✅ You understand the verification workflow

---

## 🎯 Your First Task (Recommended)

**We recommend you verify one of these "easy" actions first:**

### Option 1: `add_work_order_note` (Easiest)
**Why easy:**
- Simple: Just inserts one row to pms_work_order_notes
- No complex validation
- No foreign key lookups needed
- Inline UI (not a modal)

**Estimated time:** 2-3 hours for full verification

### Option 2: `mark_work_order_complete` (Medium)
**Why medium:**
- Updates existing row (not create)
- State transition (planned → completed)
- Sets completed_at, completed_by fields
- Requires existing work order to test

**Estimated time:** 3-4 hours for full verification

### Option 3: `assign_work_order` (Medium)
**Why medium:**
- Updates assigned_to field
- Validates user exists
- Simple form (one dropdown)

**Estimated time:** 3-4 hours for full verification

**Don't start with:**
- ❌ create_work_order_from_fault (complex, multi-table)
- ❌ order_part (complex, external integrations)
- ❌ create_pm_schedule (complex, scheduling logic)

---

## 🎓 Learning Path Summary

### Path A: Quick Start (30 min) → Start Verifying
```
Read: GLOSSARY + REPOSITORY_MAP + TESTING_STANDARDS (10 min)
Setup: LOCAL_SETUP (10 min)
Test: Run mutation_proof_create_work_order (10 min)
→ You can start verifying simple actions
```

### Path B: Deep Dive (4 hours) → Full Understanding
```
Hour 1: Architecture (ARCHITECTURE + MICROACTIONS + SITUATIONS)
Hour 2: Data & UX (DATABASE_RELATIONSHIPS + CUSTOMER_JOURNEY)
Hour 3: Verification (FRAMEWORK_OVERVIEW + GUIDE + README)
Hour 4: Hands-on (Research + Template + Practice)
→ You fully understand the system
```

**Recommendation:** Do Path A on Day 1, Path B over Week 1

---

## 📚 Documentation Index

### 🎯 Start Here (You Are Here)
- **ONBOARDING.md** ← This file
- GLOSSARY.md ← All terms defined
- REPOSITORY_MAP.md ← Where is everything
- QUICK_REFERENCE.md ← Cheat sheet

### 🏗️ Understanding the System
- ARCHITECTURE.md ← How it works
- MICROACTIONS_EXPLAINED.md ← What are microactions
- SITUATIONS_EXPLAINED.md ← What are situations
- DEPLOYMENT_ARCHITECTURE.md ← Where is it deployed

### 📋 Verification System
- FRAMEWORK_OVERVIEW.md ← How to use both frameworks
- DATABASE_RELATIONSHIPS.md ← Schema ground truth
- CUSTOMER_JOURNEY_FRAMEWORK.md ← User experience
- ACTION_VERIFICATION_TEMPLATE.md ← 215-point checklist
- ACTION_VERIFICATION_GUIDE.md ← Step-by-step guide
- README_VERIFICATION_SYSTEM.md ← System overview

### 🧪 Testing
- TESTING_STANDARDS.md ← What is success/failure
- LOCAL_SETUP.md ← How to run locally

### 📊 Examples
- _VERIFICATION/CREATE_WORK_ORDER_DEEP_DIVE.md ← Complete example
- _VERIFICATION/EXECUTIVE_SUMMARY_CREATE_WO.md ← Summary
- _VERIFICATION/MUTATION_PROOFS.md ← Progress tracker

---

## 🆘 Getting Help

### When You're Stuck

**1. Check the docs first:**
- QUICK_REFERENCE.md ← Common tasks and errors
- TESTING_STANDARDS.md ← Success criteria
- LOCAL_SETUP.md ← Troubleshooting

**2. Search the codebase:**
```bash
# Find handler for action
grep -n 'action == "your_action"' apps/api/routes/p0_actions_routes.py

# Find table columns
grep -n "pms_your_table" DATABASE_RELATIONSHIPS.md

# Find test examples
ls tests/e2e/*your_action*.spec.ts
```

**3. Ask the team:**
- "Has anyone verified [action] before?"
- "What does this error mean: [error]"
- "Is this expected behavior: [behavior]"

### Common Beginner Questions

**Q: What's the difference between a microaction and a REST endpoint?**
A: Read MICROACTIONS_EXPLAINED.md. Short answer: Microactions include context (yacht_id, user_id) automatically and are triggered by natural language.

**Q: What does "HTTP 200 ≠ Success" mean?**
A: Read TESTING_STANDARDS.md. Short answer: You must verify database state changed, not just that handler returned 200.

**Q: How do I know which table an action writes to?**
A: Read DATABASE_RELATIONSHIPS.md + search handler code. Cross-check both.

**Q: What are "situations"?**
A: Read SITUATIONS_EXPLAINED.md. Short answer: User focus state (IDLE, CANDIDATE, ACTIVE).

**Q: Why is there a Master DB and Tenant DB?**
A: Read ARCHITECTURE.md. Short answer: Master = users/yachts, Tenant = one yacht's data (multi-tenant isolation).

**Q: What does RLS mean?**
A: Read GLOSSARY.md. Short answer: Row Level Security - PostgreSQL feature that filters queries by yacht_id.

---

## ⚠️ Common Pitfalls (Avoid These!)

### Pitfall 1: Trusting the Catalog
**Wrong:**
```
Read COMPLETE_ACTION_EXECUTION_CATALOG.md →
Says table = "work_orders" →
Write test using work_orders →
Test fails
```

**Right:**
```
Read DATABASE_RELATIONSHIPS.md →
Says table = "pms_work_orders" →
Write test using pms_work_orders →
Test passes
```

**Lesson:** The catalog is outdated. Use DATABASE_RELATIONSHIPS.md as ground truth.

### Pitfall 2: Trusting HTTP 200
**Wrong:**
```
curl /v1/actions/execute → 200 OK → "It works!"
```

**Right:**
```
curl /v1/actions/execute → 200 OK
Query database → Row exists with correct data ✅
Query audit log → Entry exists ✅
→ NOW it works!
```

**Lesson:** HTTP 200 just means "handler didn't crash." Verify database state.

### Pitfall 3: Testing in Isolation
**Wrong:**
```
Test just the API call:
fetch('/v1/actions/execute', {body: {...}})
```

**Right:**
```
Test the full journey:
1. Type query in UI
2. Click action button
3. Fill form
4. Submit
5. Verify database
6. Verify audit log
```

**Lesson:** Test the customer journey, not just the API.

### Pitfall 4: Assuming Column Names
**Wrong:**
```
Assume: quantity field is called "current_quantity"
Write: SELECT current_quantity FROM pms_parts
→ Error: column doesn't exist
```

**Right:**
```
Check DATABASE_RELATIONSHIPS.md first
Find: Column is called "quantity_on_hand"
Write: SELECT quantity_on_hand FROM pms_parts
→ Works!
```

**Lesson:** Always check schema first. Don't guess column names.

### Pitfall 5: Forgetting Audit Log
**Wrong:**
```
✅ Database row created
✅ All fields correct
→ Done!
```

**Right:**
```
✅ Database row created
✅ All fields correct
❌ Audit log entry missing → NOT DONE (BLOCKER)
```

**Lesson:** Audit log is REQUIRED for all mutation actions (compliance).

---

## 📈 Success Metrics (How You'll Be Evaluated)

### After Week 1, you should:
- ✅ Understand microactions vs REST APIs
- ✅ Know what "mutation proof" means
- ✅ Have verified 1-2 simple actions fully
- ✅ Know the difference between Master DB and Tenant DB
- ✅ Understand RLS and soft delete patterns

### After Week 2, you should:
- ✅ Have verified 3-5 actions (mix of easy + medium)
- ✅ Written mutation proof tests for each
- ✅ Written E2E journey tests for each
- ✅ Found at least 1 bug (missing audit log, wrong column, etc.)
- ✅ Be comfortable with the verification workflow

### After Month 1, you should:
- ✅ Have verified 10-15 actions
- ✅ Be able to verify an action in 2-3 hours (down from 6-8 hours)
- ✅ Help onboard the next new engineer
- ✅ Contribute to improving the documentation

---

## 🎯 Your Week 1 Checklist

### Day 1: Onboarding
- [ ] Read ONBOARDING.md (this file)
- [ ] Read GLOSSARY.md
- [ ] Read REPOSITORY_MAP.md
- [ ] Read TESTING_STANDARDS.md
- [ ] Set up local environment (LOCAL_SETUP.md)
- [ ] Run mutation_proof_create_work_order test successfully

### Day 2: Deep Dive
- [ ] Read ARCHITECTURE.md
- [ ] Read MICROACTIONS_EXPLAINED.md
- [ ] Read SITUATIONS_EXPLAINED.md
- [ ] Read DATABASE_RELATIONSHIPS.md
- [ ] Read CUSTOMER_JOURNEY_FRAMEWORK.md

### Day 3: Learn Verification
- [ ] Read FRAMEWORK_OVERVIEW.md
- [ ] Read ACTION_VERIFICATION_GUIDE.md
- [ ] Read CREATE_WORK_ORDER_DEEP_DIVE.md (example)
- [ ] Copy ACTION_VERIFICATION_TEMPLATE.md
- [ ] Start verifying add_work_order_note (practice)

### Day 4-5: First Verification
- [ ] Complete verification of add_work_order_note
- [ ] Write mutation proof test
- [ ] Write E2E journey test (optional for week 1)
- [ ] Document findings in _VERIFICATION/verify_add_work_order_note.md
- [ ] Update MUTATION_PROOFS.md tracker

**By end of Week 1:** You should have fully verified 1 action and feel confident doing more.

---

## 💡 Tips for Success

### 1. Start Small
Don't try to verify create_work_order_from_fault on Day 1. Start with add_work_order_note.

### 2. Use Both Frameworks
Always cross-reference DATABASE_RELATIONSHIPS.md + CUSTOMER_JOURNEY_FRAMEWORK.md. Neither is complete alone.

### 3. Test Reality, Not Documentation
The catalog (COMPLETE_ACTION_EXECUTION_CATALOG.md) is outdated. Test what the code ACTUALLY does.

### 4. Verify the Database
HTTP 200 ≠ Success. Always query the database BEFORE and AFTER to verify mutation.

### 5. Check Audit Logs
Every mutation action MUST create an audit log entry. If missing, that's a BLOCKER.

### 6. Ask Questions
If something doesn't make sense, ask. Don't assume.

### 7. Document Everything
Fill in the template as you go. Don't try to remember everything at the end.

### 8. Take Breaks
Verification is detail-oriented work. Take breaks every 90 minutes.

---

## 🚀 Ready to Start?

### Quick Start Path (30 min):
1. Read GLOSSARY.md (5 min)
2. Read REPOSITORY_MAP.md (5 min)
3. Read TESTING_STANDARDS.md (5 min)
4. Set up environment (10 min) - LOCAL_SETUP.md
5. Run one test (5 min)

**Then:** Pick a simple action and start verifying!

### Deep Dive Path (4 hours):
1. Hour 1: Architecture docs
2. Hour 2: Database + Customer Journey docs
3. Hour 3: Verification process docs
4. Hour 4: Hands-on practice

**Then:** You fully understand the system and can verify efficiently!

---

## 📞 Who to Contact

**Questions about:**
- Verification process → Check ACTION_VERIFICATION_GUIDE.md
- Database schema → Check DATABASE_RELATIONSHIPS.md
- Customer journey → Check CUSTOMER_JOURNEY_FRAMEWORK.md
- Setup issues → Check LOCAL_SETUP.md
- Anything else → Ask the team

---

## ✅ You're Ready!

You now have everything you need to:
- ✅ Understand what this project is
- ✅ Set up your local environment
- ✅ Run tests
- ✅ Understand the verification process
- ✅ Verify your first action

**Welcome to the team! Let's verify these 64 microactions and make this system bulletproof.**

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Next Review:** After first new engineer onboards (gather feedback)

---

**Next Steps:**
1. ✅ Read GLOSSARY.md (defines all terms)
2. ✅ Read REPOSITORY_MAP.md (shows where everything is)
3. ✅ Read TESTING_STANDARDS.md (defines success)
4. ✅ Read LOCAL_SETUP.md (get your environment running)
5. 🚀 Start verifying!
