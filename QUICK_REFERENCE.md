# Quick Reference

**Cheat sheet for common tasks**

**Purpose:** Fast answers to common questions
**Audience:** All engineers
**Format:** Copy-paste ready commands

---

## ⚡ Quick Start

**New engineer? Start here:**
1. Read ONBOARDING.md (5 min)
2. Read GLOSSARY.md (5 min)
3. Read TESTING_STANDARDS.md (5 min)
4. Run `cp .env.e2e.example .env.e2e` and fill in credentials
5. Run `npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts`
6. If test passes → You're ready!

---

## 🧪 Testing

### Run One Test
```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

### Run All Tests
```bash
npx playwright test
```

### Run Tests in UI Mode
```bash
npx playwright test --ui
```

### Debug a Test
```bash
npx playwright test --debug tests/e2e/your_test.spec.ts
```

### Generate Test Report
```bash
npx playwright test
npx playwright show-report
```

### Run Specific Browser
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

---

## 🗄️ Database Queries

### List All Tables
```bash
node scripts/list_tables.js
```

### Query Work Orders
```javascript
// In Node REPL or script
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({path: '.env.e2e'});

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('yacht_id', process.env.TEST_YACHT_ID)
  .limit(10);

console.log(data);
```

### Check Audit Log
```javascript
const { data } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('yacht_id', process.env.TEST_YACHT_ID)
  .order('created_at', { ascending: false })
  .limit(20);

console.log(data);
```

### Find Equipment by Name
```javascript
const { data } = await supabase
  .from('pms_equipment')
  .select('*')
  .eq('yacht_id', process.env.TEST_YACHT_ID)
  .ilike('name', '%generator%');

console.log(data);
```

### Check if Action Created Audit Entry
```javascript
const { data } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('action', 'create_work_order')
  .eq('entity_id', 'your-work-order-id');

console.log(data.length > 0 ? 'Audit entry exists' : 'No audit entry');
```

### Using psql (Command Line)
```bash
# Connect
psql "postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

# List tables
\dt pms_*

# Query
SELECT * FROM pms_work_orders WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598' LIMIT 10;

# Check audit
SELECT * FROM pms_audit_log ORDER BY created_at DESC LIMIT 10;

# Exit
\q
```

---

## 🔍 Finding Things

### Find Microaction Handler
```bash
grep -n 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py
```

### Find All Actions
```bash
cat tests/fixtures/microaction_registry.ts | grep -E '"action":'
```

### Find Tests for an Action
```bash
ls tests/e2e/*create_work_order*.spec.ts
```

### Find Which Table an Action Uses
```bash
# Method 1: Check handler code
grep -A 20 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py | grep "\.table("

# Method 2: Check DATABASE_RELATIONSHIPS.md
grep -n "pms_work_orders" DATABASE_RELATIONSHIPS.md
```

### Find Frontend Component
```bash
find apps/web/src/components -name "*Spotlight*.tsx"
```

### Search for Text in Codebase
```bash
grep -r "create_work_order" apps/ --include="*.py" --include="*.ts" --include="*.tsx"
```

---

## 📝 Verification Workflow

### Start Verifying an Action

**1. Copy template:**
```bash
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_[action_name].md
```

**2. Find handler code:**
```bash
grep -n 'action == "[action_name]"' apps/api/routes/p0_actions_routes.py
```

**3. Find catalog entry:**
```bash
grep -n "[action_name]" _archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md
```

**4. Check database tables:**
```bash
# See DATABASE_RELATIONSHIPS.md
grep -n "pms_" DATABASE_RELATIONSHIPS.md
```

**5. Fill in template:**
- Open `_VERIFICATION/verify_[action_name].md`
- Work through 215 checkpoints
- Document findings

**6. Create test:**
```bash
touch tests/e2e/mutation_proof_[action_name].spec.ts
```

**7. Run test:**
```bash
npx playwright test tests/e2e/mutation_proof_[action_name].spec.ts
```

**8. Update tracker:**
```bash
# Edit _VERIFICATION/MUTATION_PROOFS.md
# Increment count: 2/64 complete
```

---

## 🚀 Running Services Locally

### Frontend (Next.js)
```bash
cd apps/web
npm run dev
# Access: http://localhost:3000/app
```

### Backend (FastAPI)
```bash
cd apps/api
uvicorn pipeline_service:app --reload
# Access: http://localhost:8000/docs
```

### Both at Once
```bash
# Terminal 1
cd apps/api && uvicorn pipeline_service:app --reload

# Terminal 2
cd apps/web && npm run dev
```

---

## 📊 Common Database Queries

### Count Work Orders
```sql
SELECT COUNT(*) FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND deleted_at IS NULL;
```

### Find Work Orders by Status
```sql
SELECT * FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND status = 'open'
AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 20;
```

### Check Which Actions Have Audit Logs
```sql
SELECT DISTINCT action, COUNT(*) as count
FROM pms_audit_log
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY action
ORDER BY count DESC;
```

### Find Recent Faults
```sql
SELECT * FROM pms_faults
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND deleted_at IS NULL
ORDER BY detected_at DESC
LIMIT 10;
```

### Find Equipment with Attention Flags
```sql
SELECT * FROM pms_equipment
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND attention_flag = true
AND deleted_at IS NULL;
```

### Find Parts Low in Stock
```sql
SELECT * FROM pms_parts
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
AND quantity_on_hand < minimum_quantity;
```

---

## 🐛 Troubleshooting

### "supabaseUrl is required"
**Fix:**
```bash
# Check .env.e2e exists
ls -la .env.e2e

# Check it has content
cat .env.e2e | grep TENANT_SUPABASE_URL

# Ensure script loads it
require('dotenv').config({path: '.env.e2e'});
```

### "Invalid API key"
**Fix:**
```bash
# Verify key in .env.e2e
cat .env.e2e | grep SERVICE_ROLE_KEY

# Get new key from team if expired
```

### "Table not found"
**Fix:**
```bash
# List all tables
node scripts/list_tables.js

# Check you're using correct table name
# Correct: pms_work_orders
# Wrong: work_orders
```

### "Playwright not installed"
**Fix:**
```bash
npx playwright install
```

### "Cannot find module"
**Fix:**
```bash
# Root dependencies
npm install

# Frontend dependencies
cd apps/web && npm install

# Backend dependencies
cd apps/api && pip install -r requirements.txt
```

### Test Times Out
**Fix:**
```bash
# Increase timeout
npx playwright test --timeout=60000

# Or in test file:
test.setTimeout(60000);
```

### Port Already in Use
**Fix:**
```bash
# Kill process on port 3000 (macOS/Linux)
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm run dev
```

---

## 🔑 Environment Variables

### Required for Tests (.env.e2e)
```bash
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

### Optional
```bash
MASTER_SUPABASE_URL=https://master.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
OPENAI_API_KEY=sk-...
DEBUG=true
LOG_LEVEL=info
```

---

## 📁 Key File Locations

### Documentation
```
ONBOARDING.md                   ← Start here
GLOSSARY.md                     ← All terms defined
REPOSITORY_MAP.md               ← Where everything is
TESTING_STANDARDS.md            ← Success criteria
DATABASE_RELATIONSHIPS.md       ← Schema ground truth
CUSTOMER_JOURNEY_FRAMEWORK.md   ← User experience
```

### Code
```
apps/api/routes/p0_actions_routes.py    ← All 81 handlers (4160 lines)
apps/web/src/app/app/page.tsx           ← Main UI
apps/web/src/components/spotlight/SpotlightSearch.tsx  ← Search bar
apps/web/src/lib/actionClient.ts        ← API calls
```

### Tests
```
tests/e2e/mutation_proof_*.spec.ts      ← Database mutation tests
tests/fixtures/microaction_registry.ts  ← All 64 actions defined
```

### Verification
```
ACTION_VERIFICATION_TEMPLATE.md         ← Copy this for each action
_VERIFICATION/CREATE_WORK_ORDER_DEEP_DIVE.md  ← Example verification
_VERIFICATION/MUTATION_PROOFS.md        ← Progress tracker
```

---

## 🎯 Testing Patterns

### Mutation Proof Pattern
```typescript
test('action_name mutation proof', async () => {
  // BEFORE
  const { data: before } = await supabase.from('table').select('*').eq('field', 'value');
  expect(before).toHaveLength(0);

  // EXECUTE
  const response = await executeAction('action_name', context, payload);
  expect(response.status).toBe('success');

  // AFTER
  const { data: after } = await supabase.from('table').select('*').eq('id', response.entity_id).single();
  expect(after).toBeTruthy();

  // AUDIT
  const { data: audit } = await supabase.from('pms_audit_log').select('*').eq('entity_id', response.entity_id);
  expect(audit).toHaveLength(1);
});
```

### Validation Error Pattern
```typescript
test('action rejects invalid input', async () => {
  const response = await executeAction('action_name', context, {});
  expect(response.status).toBe('error');
  expect(response.error_code).toBe('VALIDATION_ERROR');
});
```

### Entity Not Found Pattern
```typescript
test('action returns 404 for invalid entity', async () => {
  const response = await executeAction('action_name', context, {
    entity_id: '00000000-0000-0000-0000-000000000000'
  });
  expect(response.status).toBe('error');
  expect(response.error_code).toBe('NOT_FOUND');
});
```

---

## 🔗 Quick Links

**Documentation:**
- [Onboarding](./ONBOARDING.md)
- [Glossary](./GLOSSARY.md)
- [Repository Map](./REPOSITORY_MAP.md)
- [Testing Standards](./TESTING_STANDARDS.md)
- [Database Schema](./DATABASE_RELATIONSHIPS.md)
- [Customer Journey](./CUSTOMER_JOURNEY_FRAMEWORK.md)

**Code:**
- [Handlers](./apps/api/routes/p0_actions_routes.py)
- [Frontend](./apps/web/src/app/app/page.tsx)
- [Action Registry](./tests/fixtures/microaction_registry.ts)

**Examples:**
- [Verification Example](./\_VERIFICATION/CREATE_WORK_ORDER_DEEP_DIVE.md)
- [Test Example](./tests/e2e/mutation_proof_create_work_order.spec.ts)

---

## 📞 Getting Help

**Check documentation first:**
1. GLOSSARY.md - Understand terms
2. TESTING_STANDARDS.md - Success criteria
3. LOCAL_SETUP.md - Troubleshooting

**Ask the team:**
- "Has anyone verified [action] before?"
- "What does this error mean: [error]"
- "Where can I find [file/code]?"

**Search the codebase:**
```bash
grep -r "your search term" apps/ tests/ --include="*.py" --include="*.ts" --include="*.tsx"
```

---

## ✅ Success Checklist

**Verify an action is DONE when:**
- [ ] HTTP 200 returned
- [ ] Response contains entity ID
- [ ] Database row created/updated
- [ ] Database row has correct values
- [ ] Audit log entry created
- [ ] Audit log entry has correct values
- [ ] 400 error for invalid input
- [ ] 404 error for invalid entity
- [ ] 401/403 for auth issues
- [ ] RLS prevents cross-yacht access
- [ ] Soft delete prevents hard deletes
- [ ] Tests passing
- [ ] Verification file complete
- [ ] Progress tracker updated

---

## 💡 Pro Tips

1. **Always include yacht_id filter** in database queries
2. **HTTP 200 ≠ Success** - Verify database state
3. **Copy verification template** for each action
4. **Use DATABASE_RELATIONSHIPS.md** as ground truth (not catalog)
5. **Test both success AND failure** cases
6. **Check audit log** for every mutation
7. **400/404 are EXPECTED** failures, not bugs
8. **Start with simple actions** (add_note, assign, etc.)
9. **Use mutation proof pattern** for all tests
10. **Document findings** as you go

---

## 🎓 Common Tasks

**Find an action:**
```bash
grep -n 'action == "your_action"' apps/api/routes/p0_actions_routes.py
```

**Test an action:**
```bash
npx playwright test tests/e2e/mutation_proof_your_action.spec.ts
```

**Query database:**
```bash
node -e "require('dotenv').config({path:'.env.e2e'}); ..."
# Or use scripts/your_script.js
```

**Check audit log:**
```javascript
const {data} = await supabase.from('pms_audit_log').select('*').eq('action','your_action');
```

**Verify RLS:**
```javascript
// Try to query different yacht (should return empty)
const {data} = await supabase.from('pms_work_orders').select('*').eq('yacht_id', 'different-uuid');
expect(data).toHaveLength(0);
```

---

## 🚀 Speed Run (5 Minutes)

**Complete action verification in 5 minutes (quick check):**

```bash
# 1. Find handler (30 sec)
grep -n 'action == "your_action"' apps/api/routes/p0_actions_routes.py

# 2. Check what table it uses (30 sec)
grep -A 10 'action == "your_action"' apps/api/routes/p0_actions_routes.py | grep "\.table("

# 3. Query BEFORE (30 sec)
# In Node REPL:
const {data:before} = await supabase.from('table').select('*').eq('field','value');

# 4. Execute action (1 min)
const response = await executeAction('your_action', {...}, {...});

# 5. Query AFTER (30 sec)
const {data:after} = await supabase.from('table').select('*').eq('id', response.entity_id);

# 6. Check audit (30 sec)
const {data:audit} = await supabase.from('pms_audit_log').select('*').eq('entity_id', response.entity_id);

# 7. Document (1 min)
# Write findings in verification file
```

**Result:** Quick validation (not full verification, but good for spotting critical issues)

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team

**Bookmark this page!** → Use as daily reference
