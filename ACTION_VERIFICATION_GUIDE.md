# Action Verification Guide for Engineers

## Quick Start

**Goal:** Systematically verify all 64 actions are production-ready.

**Process:** One action at a time, verify 215 checkpoints.

**Time:** ~20-25 hours per action (full verification)

---

## Step-by-Step Process

### Step 1: Choose an Action

Pick an action from the list of 64:
- Priority order: High-value actions first (create_work_order, mark_complete, etc.)
- Alphabetical order: If no priority
- Random: If you don't care

**List of all 64 actions:**
```
See tests/fixtures/microaction_registry.ts
OR _archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md
```

### Step 2: Copy the Template

```bash
# Copy template to new file
cp ACTION_VERIFICATION_TEMPLATE.md "_VERIFICATION/verify_[action_name].md"

# Example:
cp ACTION_VERIFICATION_TEMPLATE.md "_VERIFICATION/verify_create_work_order.md"
```

### Step 3: Fill in Metadata

Open the new file and fill in:
- Action ID
- Date started
- Your name
- Reference line numbers:
  - Catalog: `_archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md` (line XXX)
  - Handler: `apps/api/routes/p0_actions_routes.py` (line XXX)
  - Registry: `tests/fixtures/microaction_registry.ts` (line XXX)

**How to find line numbers:**
```bash
# Find in catalog
grep -n "### ACTION.*action_name" _archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md

# Find in handler
grep -n 'action == "action_name"' apps/api/routes/p0_actions_routes.py

# Find in registry
grep -n '"action_name"' tests/fixtures/microaction_registry.ts
```

### Step 4: Read the Catalog Entry

Open `_archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md` and read the FULL entry for your action.

**What to look for:**
- Tables Affected
- Row Operations (INSERT/UPDATE/DELETE)
- Columns Modified
- Required Inputs
- Optional Inputs
- Validation Rules
- Expected behavior

**Copy relevant sections into your verification file** under "Catalog Says:"

### Step 5: Work Through Each Section

**IMPORTANT ORDER:**

1. **Start with Section 4 (Database Mutations)** ✅ MOST CRITICAL
   - This verifies the action actually works
   - HTTP 200 doesn't mean success
   - You MUST verify database state changes

2. **Then Section 5 (Audit Trail)** ✅ COMPLIANCE REQUIREMENT
   - Verify audit log entry exists
   - Not optional

3. **Then Section 3 (Backend Execution)** ✅ CORE FUNCTIONALITY
   - Handler exists and works

4. **Then Section 6 (Negative Testing)** ✅ ERROR HANDLING
   - Test all error codes
   - 400/404 are expected, not failures

5. **Then Sections 1, 2, 7-10** ✅ COMPLETE COVERAGE
   - NL queries
   - Frontend
   - Integration
   - Performance
   - Deployment
   - Documentation

---

## ⚠️ CRITICAL: Understanding "Success"

### ❌ WRONG: "It returned 200, so it works"

```bash
curl -X POST /v1/actions/execute -d '{...}'
# Response: {"status": "success", "work_order_id": "abc-123"}
# HTTP Status: 200

# ❌ You're DONE? NO!
```

### ✅ RIGHT: "It returned 200 AND database changed correctly"

```bash
# 1. Query BEFORE
psql -c "SELECT * FROM pms_work_orders WHERE id = 'abc-123';"
# Result: 0 rows

# 2. Execute action
curl -X POST /v1/actions/execute -d '{...}'
# Response: {"status": "success", "work_order_id": "abc-123"}

# 3. Query AFTER
psql -c "SELECT * FROM pms_work_orders WHERE id = 'abc-123';"
# Result: 1 row with correct data

# 4. Query audit log
psql -c "SELECT * FROM pms_audit_log WHERE entity_id = 'abc-123';"
# Result: 1 audit entry

# ✅ NOW you're done
```

**You MUST verify:**
1. HTTP response (200)
2. Response contains entity ID
3. Database row exists
4. Database row has correct values
5. Audit log entry exists
6. Audit log entry has correct values

**All 6 checks MUST pass.**

---

## How to Connect to Database

### Option 1: Supabase Studio (GUI)

1. Go to: https://vzsohavtuotocgrfkfyd.supabase.co
2. Login with service role key
3. Navigate to Table Editor
4. Run SQL queries

### Option 2: psql (Command Line)

```bash
# Install psql if needed
brew install postgresql

# Connect to tenant DB
psql "postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

# Run query
SELECT * FROM pms_work_orders WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

### Option 3: Node.js Script

```javascript
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

async function query() {
  const { data } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('id', 'abc-123');
  console.log(data);
}
```

---

## How to Run Tests

### NL Query Tests

```bash
# Create test file
cat > tests/e2e/nl_queries_create_work_order.spec.ts << 'EOF'
[Copy from template]
EOF

# Run test
npx playwright test tests/e2e/nl_queries_create_work_order.spec.ts --project=e2e-chromium
```

### Mutation Proof Tests

```bash
# Create test file (copy from template or create_work_order example)
cp tests/e2e/mutation_proof_create_work_order.spec.ts \
   tests/e2e/mutation_proof_[action_name].spec.ts

# Edit for your action
# Run test
npx playwright test tests/e2e/mutation_proof_[action_name].spec.ts --project=e2e-chromium
```

### Frontend Journey Tests

```bash
# Run Playwright in UI mode (easier for recording journey)
npx playwright test --ui

# Select your test file
# Watch it run
# Debug failures
```

---

## Checklist for Each Action

### Absolute Minimum (Must Do)

- [ ] Database mutation verified (query before/after)
- [ ] Audit log verified (query pms_audit_log)
- [ ] Handler code reviewed (read the Python)
- [ ] 1 successful test case
- [ ] 3 error test cases (400, 404, 401)

**Time:** ~2-3 hours

### Recommended (Should Do)

- [ ] All of above PLUS:
- [ ] 10+ NL query variations tested
- [ ] Frontend journey tested (Playwright)
- [ ] Security tests (SQL injection, XSS)
- [ ] Performance measured
- [ ] Catalog cross-checked

**Time:** ~8-10 hours

### Complete (Production Ready)

- [ ] All 215 checklist items
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Deployed and smoke tested

**Time:** ~20-25 hours

---

## Common Pitfalls

### ❌ Pitfall 1: Trusting HTTP 200

**Wrong:**
```
"It returned 200, it works!"
```

**Right:**
```
"It returned 200. Let me verify the database actually changed."
```

### ❌ Pitfall 2: Assuming Column Names

**Wrong:**
```python
# Assuming column is called 'current_quantity'
UPDATE pms_parts SET current_quantity = 10
```

**Right:**
```bash
# First, check actual schema
psql -c "\d pms_parts"
# Oh, it's called 'quantity_on_hand'
```

### ❌ Pitfall 3: Assuming Table Names

**Wrong:**
```
"It's probably 'work_orders'"
```

**Right:**
```
"Let me check: SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%work%order%';"
# Result: pms_work_orders
```

### ❌ Pitfall 4: Forgetting Audit Log

**Wrong:**
```
"Database row exists. Done!"
```

**Right:**
```
"Database row exists. Now let me check audit log... OH NO, it's missing. NOT DONE."
```

### ❌ Pitfall 5: Not Testing Errors

**Wrong:**
```
"200 works. Moving on."
```

**Right:**
```
"200 works. Now let me test:
- 400 (missing field)
- 404 (bad equipment_id)
- 401 (no token)
- 403 (wrong yacht)
All return correct error messages? Good, now I'm done."
```

---

## Template Sections Explained

### Why 15 Sections?

Each section tests a different dimension:

1. **NL Queries** - Can users FIND this action?
2. **Frontend** - Can users EXECUTE this action?
3. **Backend** - Does handler WORK?
4. **Database** - Does data GET WRITTEN?
5. **Audit** - Is action TRACEABLE?
6. **Errors** - Do errors HELP users?
7. **Integration** - Does it work WITH other actions?
8. **Performance** - Is it FAST enough?
9. **Deployment** - Does it work in PRODUCTION?
10. **Documentation** - Can others UNDERSTAND it?
11-15. (Future expansion)

**All 15 must be ✅ for "DONE"**

---

## What "DONE" Actually Means

### Level 0: Not Started
- [ ] Template copied
- Progress: 0/215

### Level 1: Basic Verification (2-3 hours)
- [x] Database mutation verified
- [x] Audit log verified
- [x] Handler reviewed
- [x] 1 success test
- [x] 3 error tests
- Progress: ~20/215

### Level 2: Thorough Verification (8-10 hours)
- [x] All of Level 1
- [x] NL queries tested
- [x] Frontend tested
- [x] Security tested
- [x] Catalog cross-checked
- Progress: ~100/215

### Level 3: Production Ready (20-25 hours)
- [x] All 215 items checked
- [x] All tests passing
- [x] Documentation complete
- [x] Deployed and smoke tested
- Progress: 215/215 ✅

**For most actions, aim for Level 2. Only critical actions need Level 3.**

---

## Example: Verifying create_work_order

**1. Copy template:**
```bash
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_create_work_order.md
```

**2. Find references:**
```bash
# Catalog
grep -n "create_work_order" _archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md
# Line: 487

# Handler
grep -n 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py
# Line: 1325
```

**3. Read catalog entry (lines 487-650):**
- Tables: pms_work_orders, pms_audit_log
- Columns: id, yacht_id, title, description, priority, status, created_by, created_at
- Required: title
- Optional: description, priority, equipment_id

**4. Test database mutation:**
```bash
# Before
psql -c "SELECT COUNT(*) FROM pms_work_orders WHERE title = 'Test WO 123';"
# 0

# Execute
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"action":"create_work_order","context":{...},"payload":{"title":"Test WO 123"}}'
# Response: {"status":"success","work_order_id":"abc-123"}

# After
psql -c "SELECT * FROM pms_work_orders WHERE id = 'abc-123';"
# 1 row ✅

# Audit
psql -c "SELECT * FROM pms_audit_log WHERE entity_id = 'abc-123';"
# 0 rows ❌ BUG FOUND!
```

**5. Document finding:**
```markdown
## 5️⃣ AUDIT TRAIL

- [x] **5.1** Audit log entry created
  - **Query:** SELECT * FROM pms_audit_log WHERE entity_id = 'abc-123'
  - **Entry Found:** ❌ NO
  - **Status:** ❌ FAIL
  - **BLOCKER:** create_work_order does NOT write audit log
  - **Fix:** Add 25 lines of code (see acknowledge_fault pattern)
```

**6. Continue through all 215 items...**

---

## FAQ

**Q: Do I need to verify all 64 actions?**
A: Eventually yes. Start with high-priority actions.

**Q: Can I skip sections?**
A: For quick verification, do sections 3, 4, 5 minimum. For production, do all.

**Q: What if catalog is wrong?**
A: Document the discrepancy. Update catalog. Use reality, not catalog.

**Q: What if I find a bug?**
A: Document it as a blocker. Don't mark section as complete until fixed.

**Q: HTTP 200 but wrong data in DB?**
A: That's a bug. Mark DB mutation section as ❌ FAIL.

**Q: No audit log but everything else works?**
A: That's a CRITICAL blocker. Action is NOT done until audit log exists.

**Q: How long should this take?**
A: Basic verification: 2-3 hours. Full verification: 20-25 hours.

---

## Getting Help

**Stuck? Ask:**
- "What does the catalog say about this action?"
- "Has anyone verified this action before?"
- "Is there a similar action I can reference?"
- "Is this expected behavior or a bug?"

**Resources:**
- Catalog: `_archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md`
- Handler code: `apps/api/routes/p0_actions_routes.py`
- Test registry: `tests/fixtures/microaction_registry.ts`
- Example: `_VERIFICATION/CREATE_WORK_ORDER_DEEP_DIVE.md`

---

## Final Checklist

Before marking an action as DONE:

- [ ] I queried the database BEFORE the action
- [ ] I executed the action via API
- [ ] I queried the database AFTER the action
- [ ] I verified the row exists with correct data
- [ ] I queried pms_audit_log and verified audit entry
- [ ] I tested at least 3 error scenarios (400, 404, 401)
- [ ] I cross-checked catalog vs. reality
- [ ] I documented all findings
- [ ] I created/updated test files
- [ ] All tests are passing
- [ ] No critical blockers remain

**If all boxes checked: Action is DONE ✅**

---

**Template Version:** 2.0
**Guide Version:** 1.0
**Last Updated:** 2026-01-22
