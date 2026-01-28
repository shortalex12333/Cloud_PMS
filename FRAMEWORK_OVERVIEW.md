# Verification Framework Overview

**Date Created:** 2026-01-22
**Purpose:** Two-framework approach to action verification
**Status:** Foundation complete, ready for per-action documentation

---

## The Problem with Catalog-Only Verification

**Old Approach:**
```
Engineer reads COMPLETE_ACTION_EXECUTION_CATALOG.md → Tests if code matches
```

**Issues:**
1. ❌ Catalog is outdated (table names wrong, fields missing)
2. ❌ Doesn't explain HOW users trigger actions
3. ❌ No guard rails documented
4. ❌ No customer journey context

**Result:** Engineers test against documentation wishes, not reality.

---

## The New Two-Framework Approach

### Framework 1: DATABASE_RELATIONSHIPS.md

**What It Is:** Ground truth of database schema

**Contains:**
- ✅ Actual table names (pms_work_orders, not work_orders)
- ✅ Real column names (quantity_on_hand, not current_quantity)
- ✅ Foreign key relationships
- ✅ RLS policies
- ✅ Soft delete patterns
- ✅ Data types and constraints
- ✅ Common query patterns

**Use It For:**
- Writing mutation proof tests (BEFORE/AFTER queries)
- Understanding which tables are affected
- Avoiding column name traps
- Verifying foreign key constraints
- Testing RLS enforcement

**Example:**
```markdown
## Table: pms_work_orders

| Column | Type | Nullable | Foreign Key |
|--------|------|----------|-------------|
| id | uuid | ❌ | - |
| yacht_id | uuid | ❌ | → master DB |
| equipment_id | uuid | ✅ | → pms_equipment.id |
| title | text | ❌ | - |
| status | text | ❌ | - | (planned, open, in_progress, completed) |
```

### Framework 2: CUSTOMER_JOURNEY_FRAMEWORK.md

**What It Is:** How users interact with the system

**Contains:**
- ✅ Natural language query variants (55+ per action)
- ✅ UI journey (search → button → modal → form → submit)
- ✅ Form fields (types, validation, defaults)
- ✅ Guard rails (frontend, backend, database)
- ✅ Success flows
- ✅ Error flows
- ✅ Context sources (where action is triggered from)

**Use It For:**
- Writing realistic E2E tests
- Understanding user experience
- Testing query detection
- Verifying error messages
- Identifying edge cases

**Example:**
```markdown
### create_work_order Journey

Query Variants:
- "create a work order"
- "create work order for generator"
- "new wo for main engine"
- "schedule maintenance"
... 50+ more

UI Flow:
1. User types query → SpotlightSearch
2. Backend detects action → Returns button
3. User clicks button → Modal opens
4. User fills form (title, priority, equipment)
5. User submits → API call
6. Success toast → Modal closes
```

---

## How to Use Both Frameworks Together

### Step 1: Choose Action to Verify

Example: `create_work_order`

### Step 2: Consult DATABASE_RELATIONSHIPS.md

**Find relevant tables:**
```markdown
Primary Table: pms_work_orders
Foreign Keys:
- yacht_id → master DB (RLS enforced)
- equipment_id → pms_equipment.id (optional)
- created_by → master DB users (required)

Columns to verify:
- id (uuid, auto-generated)
- title (text, required)
- status (text, always "planned" on create)
- priority (text, mapped: routine|critical|emergency)
- created_at (timestamptz, auto-set)
```

**Plan mutation test:**
```sql
-- BEFORE
SELECT COUNT(*) FROM pms_work_orders WHERE title = 'Test WO 123';
-- Expected: 0

-- AFTER (execute action)
SELECT * FROM pms_work_orders WHERE title = 'Test WO 123';
-- Expected: 1 row with correct data
```

### Step 3: Consult CUSTOMER_JOURNEY_FRAMEWORK.md

**Understand user journey:**
```markdown
Query: "create a work order"
Button: "Create Work Order"
Form Fields:
- title (text, required)
- description (textarea, optional)
- priority (select, default: routine)
- equipment (select, optional)

Guard Rails:
- Frontend: title.trim().length > 0
- Backend: if not title: raise 400
- Database: RLS enforces yacht_id
```

**Plan E2E test:**
```typescript
// 1. Type query
await page.fill('[data-testid="spotlight-input"]', 'create a work order');

// 2. Click action button
await page.click('button:has-text("Create Work Order")');

// 3. Fill form
await page.fill('[name="title"]', 'Test WO 123');

// 4. Submit
await page.click('button:has-text("Create")');

// 5. Verify success
await page.waitForSelector('.toast:has-text("created")');
```

### Step 4: Write Tests

**Mutation Proof Test:**
```typescript
test('create_work_order writes to database', async () => {
  // BEFORE
  const { data: before } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('title', 'Test WO 123');
  expect(before).toHaveLength(0);

  // EXECUTE
  const response = await executeAction('create_work_order',
    { yacht_id, user_id },
    { title: 'Test WO 123' }
  );
  expect(response.status).toBe('success');

  // AFTER
  const { data: after } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('title', 'Test WO 123')
    .single();

  expect(after).toBeTruthy();
  expect(after.status).toBe('planned');
  expect(after.priority).toBe('routine');

  // AUDIT
  const { data: audit } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('entity_id', after.id);

  expect(audit).toHaveLength(1); // ❌ Currently fails - audit gap
});
```

**Customer Journey Test:**
```typescript
test('create_work_order full UI journey', async ({ page }) => {
  await page.goto('/app');

  // 1. Type query
  await page.fill('[data-testid="spotlight-input"]', 'create work order for main engine');
  await page.press('[data-testid="spotlight-input"]', 'Enter');

  // 2. Action button appears
  await page.waitForSelector('button:has-text("Create Work Order")');

  // 3. Click button
  await page.click('button:has-text("Create Work Order")');

  // 4. Modal opens with form
  await page.waitForSelector('[data-testid="action-modal"]');

  // 5. Fill form
  await page.fill('[name="title"]', 'Oil change for main engine');
  await page.selectOption('[name="priority"]', 'routine');

  // 6. Submit
  await page.click('button:has-text("Create Work Order")');

  // 7. Success toast
  await page.waitForSelector('.toast:has-text("Work order created")');

  // 8. Verify database
  const { data } = await supabase
    .from('pms_work_orders')
    .select('*')
    .eq('title', 'Oil change for main engine')
    .single();

  expect(data).toBeTruthy();
});
```

### Step 5: Document Findings

**In verification file:**
```markdown
## create_work_order Verification

### Database Mutations ✅
- Table: pms_work_orders ✅
- Columns: id, yacht_id, title, status, priority, created_at ✅
- Foreign Keys: equipment_id (optional, validated if provided) ✅

### Audit Trail ❌
- pms_audit_log entry: NOT CREATED
- **BLOCKER:** No audit logging implemented
- Fix: Add 25 lines of code (see acknowledge_fault pattern)

### Customer Journey ✅
- Query detection: 10/55 variants tested ✅
- Button appears: ✅
- Modal opens: ✅
- Form fields: title, description, priority, equipment ✅
- Submit succeeds: ✅
- Toast confirmation: ✅

### Guard Rails ✅
- Frontend validation: title required ✅
- Backend validation: title required, equipment exists (if provided) ✅
- RLS enforcement: yacht_id filter ✅
- Soft delete: Hard deletes blocked ✅
```

---

## Verification Checklist

**For each action, verify:**

### ✅ Database Layer (Use: DATABASE_RELATIONSHIPS.md)
- [ ] Correct table name used
- [ ] All required columns written
- [ ] Foreign keys valid (entities exist)
- [ ] RLS policies enforced (yacht_id filter)
- [ ] Soft delete pattern used (deleted_at, not DELETE)
- [ ] Audit log entry created
- [ ] Data types correct (uuid, text, timestamptz)

### ✅ Customer Journey (Use: CUSTOMER_JOURNEY_FRAMEWORK.md)
- [ ] 10+ query variants tested
- [ ] Action button appears after query
- [ ] Modal/form opens when clicked
- [ ] All form fields present
- [ ] Required fields validated (frontend)
- [ ] Submit calls correct API
- [ ] Success toast appears
- [ ] Error toasts show helpful messages

### ✅ Guard Rails (Use: Both)
- [ ] Frontend validation prevents bad input
- [ ] Backend validation catches edge cases
- [ ] Database constraints enforced
- [ ] RLS prevents cross-yacht access
- [ ] Enum values validated
- [ ] Length limits enforced

### ✅ Error Handling (Use: CUSTOMER_JOURNEY_FRAMEWORK.md)
- [ ] 400: Missing field → Error message shown
- [ ] 404: Invalid entity → Error message shown
- [ ] 401: Not authenticated → Redirect to login
- [ ] 403: Wrong yacht → Error message shown
- [ ] 500: Server error → Error message + retry

---

## Comparison: Old vs New Approach

### Old Approach (Catalog-Only)

```
1. Read COMPLETE_ACTION_EXECUTION_CATALOG.md
2. Find create_work_order entry
3. See: "Table: work_orders, Required: equipment_id, description"
4. Write test expecting those
5. Test fails because:
   - Table is actually pms_work_orders
   - equipment_id is optional
   - description is optional
6. Update catalog? Update code? Which is right?
```

**Problems:**
- ❌ Catalog is aspirational, not factual
- ❌ No clarity on what's real vs documented
- ❌ No customer journey context
- ❌ Wastes time chasing ghosts

### New Approach (Two Frameworks)

```
1. Read DATABASE_RELATIONSHIPS.md
   → Table: pms_work_orders
   → Required: title only
   → Optional: equipment_id, description
   → Status: always "planned"

2. Read CUSTOMER_JOURNEY_FRAMEWORK.md
   → Query: "create a work order"
   → Form: title, description, priority, equipment
   → Guard Rails: frontend + backend validate title

3. Write tests based on REALITY:
   - Mutation test uses pms_work_orders
   - E2E test types query, clicks button, fills form
   - Expects title required, others optional

4. Tests pass because they match reality
5. Find gap: No audit log entry
6. Fix code to add audit logging
```

**Benefits:**
- ✅ Tests based on reality, not documentation
- ✅ Customer journey included
- ✅ Clear guard rails
- ✅ Faster verification
- ✅ Find real gaps (audit logging)

---

## Framework Maintenance

### When to Update DATABASE_RELATIONSHIPS.md

**Triggers:**
- Schema migration runs (new columns, tables)
- Foreign keys added/removed
- RLS policies changed
- Indexes added
- Constraints modified

**Process:**
1. Run `node scripts/discover_database_relationships.js`
2. Review generated output
3. Update DATABASE_RELATIONSHIPS.md
4. Note changes in git commit

### When to Update CUSTOMER_JOURNEY_FRAMEWORK.md

**Triggers:**
- UI redesign (modal → inline form)
- New form fields added
- Validation rules changed
- Error messages updated
- New action variants discovered

**Process:**
1. Screenshot new UI journey (or describe)
2. Document new form fields
3. Update guard rails section
4. Add new query variants
5. Update E2E test examples

---

## Per-Action Documentation Template

**For each action, create:**

### Section 1: Database Mutations (From: DATABASE_RELATIONSHIPS.md)
```markdown
## Tables Affected
- pms_work_orders (INSERT)
- pms_audit_log (INSERT) ← if implemented

## Columns Written
- id (uuid, auto-generated)
- yacht_id (uuid, from context)
- title (text, from payload)
- status (text, hardcoded: "planned")
- created_at (timestamptz, auto-set)

## Foreign Key Validation
- equipment_id → pms_equipment.id (if provided, validate exists)
```

### Section 2: Customer Journey (From: CUSTOMER_JOURNEY_FRAMEWORK.md)
```markdown
## Query Variants
1. "create a work order"
2. "create work order for generator"
3. "new wo"
... 10+ total

## UI Journey
1. User types → SpotlightSearch
2. Button appears → "Create Work Order"
3. User clicks → Modal opens
4. Form shown:
   - Title (text, required)
   - Description (textarea, optional)
   - Priority (select, default: routine)
   - Equipment (select, optional)
5. User submits → API call
6. Success toast → Modal closes

## Guard Rails
- Frontend: title.trim().length > 0
- Backend: if not title: 400
- Database: RLS yacht_id filter
```

### Section 3: Test Results
```markdown
## Mutation Test: ✅ PASS
- BEFORE: 0 rows
- AFTER: 1 row with correct data
- Audit: ❌ FAIL (no audit log entry)

## E2E Test: ✅ PASS
- Query detection: ✅
- Button appears: ✅
- Form submits: ✅
- Toast shows: ✅

## Error Tests: ✅ PASS
- Missing title → 400 ✅
- Invalid equipment_id → 404 ✅
- No auth → 401 ✅
```

---

## Current Status

### Frameworks Complete ✅
- ✅ DATABASE_RELATIONSHIPS.md created
- ✅ CUSTOMER_JOURNEY_FRAMEWORK.md created
- ✅ FRAMEWORK_OVERVIEW.md (this file) created

### Actions Documented: 1/64
- ✅ create_work_order (detailed example in both frameworks)
- ⏳ 63 actions remaining

### Next Steps
1. For each action, fill in both framework sections
2. Write mutation proof test (using DATABASE_RELATIONSHIPS)
3. Write E2E journey test (using CUSTOMER_JOURNEY_FRAMEWORK)
4. Document findings in verification file
5. Move to next action

---

## Benefits of Two-Framework Approach

### For Engineers
- ✅ Clear ground truth (database schema)
- ✅ Realistic test scenarios (customer journey)
- ✅ Faster debugging (know where to look)
- ✅ No guessing about catalog accuracy

### For Testing
- ✅ Write tests that match reality
- ✅ Cover full journey, not just API
- ✅ Verify guard rails at all layers
- ✅ Test query detection accurately

### For Documentation
- ✅ Living documents (update as system evolves)
- ✅ Easy to maintain (two focused files)
- ✅ Easy to reference (table of contents)
- ✅ Clear separation of concerns

### For Verification
- ✅ 215-point template still valid
- ✅ But now grounded in reality
- ✅ References both frameworks
- ✅ Tests what matters

---

## File Structure

```
BACK_BUTTON_CLOUD_PMS/
│
├── DATABASE_RELATIONSHIPS.md          ← Framework 1 (schema)
├── CUSTOMER_JOURNEY_FRAMEWORK.md      ← Framework 2 (UX)
├── FRAMEWORK_OVERVIEW.md              ← This file (how to use both)
│
├── ACTION_VERIFICATION_TEMPLATE.md    ← 215-point checklist (uses both frameworks)
├── ACTION_VERIFICATION_GUIDE.md       ← Step-by-step instructions
├── README_VERIFICATION_SYSTEM.md      ← System overview
│
├── _VERIFICATION/
│   ├── CREATE_WORK_ORDER_DEEP_DIVE.md ← Example (uses both frameworks)
│   ├── MUTATION_PROOFS.md              ← Test results tracker
│   └── verify_[action].md              ← Future action verifications
│
├── tests/e2e/
│   ├── mutation_proof_create_work_order.spec.ts  ← Database test
│   └── journey_create_work_order.spec.ts         ← Full journey test
│
└── _archive/misc/
    └── COMPLETE_ACTION_EXECUTION_CATALOG.md  ← Reference (outdated, use with caution)
```

---

## Quick Start for New Engineers

**To verify an action:**

1. **Read this file** (5 minutes)
2. **Read DATABASE_RELATIONSHIPS.md** - Find your action's tables (10 minutes)
3. **Read CUSTOMER_JOURNEY_FRAMEWORK.md** - Find your action's journey (10 minutes)
4. **Copy ACTION_VERIFICATION_TEMPLATE.md** (1 minute)
5. **Fill in template using both frameworks** (2-3 hours)
6. **Write tests** (2-3 hours)
7. **Run tests, document findings** (1 hour)

**Total:** 6-8 hours for thorough verification

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Status:** Complete and ready for use
