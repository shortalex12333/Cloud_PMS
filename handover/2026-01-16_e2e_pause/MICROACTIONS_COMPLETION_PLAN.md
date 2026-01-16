# MICROACTIONS COMPLETION PLAN

**Created:** 2026-01-16
**Status:** INCOMPLETE - ~53% of handlers wired
**Goal:** Production-ready microactions system with all 95 handlers callable, tested, and verified

---

## CURRENT STATE ASSESSMENT

### What Exists vs What Works

| Category | Handlers Written | Handlers Registered | Gap |
|----------|-----------------|---------------------|-----|
| Core (fault, WO, worklist) | 39 | 39 | 0 |
| P1 Compliance | 2 | 0 | **2** |
| P1 Purchasing | 4 | 1 | **3** |
| P2 Mutation Light | 20 | 5 | **15** |
| P3 Read Only | 30 | 5 | **25** |
| **TOTAL** | **~95** | **~50** | **~45** |

### Root Cause

The handler getter functions exist but are NEVER CALLED:

```python
# These are defined but not invoked:
get_p1_compliance_handlers(supabase_client)   # 2 handlers
get_p1_purchasing_handlers(supabase_client)   # 4 handlers
get_p2_mutation_light_handlers(supabase_client)  # 20 handlers
get_p3_read_only_handlers(supabase_client)    # 30 handlers
```

### Empty Tables (No Test Data)

| Table | Status |
|-------|--------|
| pms_hours_of_rest | EMPTY |
| pms_checklists | NOT FOUND |
| pms_checklist_items | NOT FOUND |

---

## PHASE 8: Wire Missing Handlers to Dispatcher

### Description

Register all ~45 unregistered handlers by calling the getter functions in `internal_dispatcher.py` and merging them into `INTERNAL_HANDLERS`.

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/apps/api/action_router/dispatchers/internal_dispatcher.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p1_compliance_handlers.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p1_purchasing_handlers.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p2_mutation_light_handlers.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p3_read_only_handlers.py
```

### Files to Modify

```
/Users/celeste7/Documents/Cloud_PMS/apps/api/action_router/dispatchers/internal_dispatcher.py
```

### Tasks

1. Read `internal_dispatcher.py` - understand current INTERNAL_HANDLERS structure
2. Read each p1/p2/p3 handler file - find the `get_*_handlers()` export function
3. Add imports at top of `internal_dispatcher.py`:
   ```python
   from handlers.p1_compliance_handlers import get_p1_compliance_handlers
   from handlers.p1_purchasing_handlers import get_p1_purchasing_handlers
   from handlers.p2_mutation_light_handlers import get_p2_mutation_light_handlers
   from handlers.p3_read_only_handlers import get_p3_read_only_handlers
   ```
4. Create a function to merge handlers:
   ```python
   def build_handler_registry(supabase_client):
       handlers = {**INTERNAL_HANDLERS}
       handlers.update(get_p1_compliance_handlers(supabase_client))
       handlers.update(get_p1_purchasing_handlers(supabase_client))
       handlers.update(get_p2_mutation_light_handlers(supabase_client))
       handlers.update(get_p3_read_only_handlers(supabase_client))
       return handlers
   ```
5. Update dispatcher to use merged handlers
6. Handle naming collisions (log warning if duplicate keys)

### Verification

```bash
# Count handlers before
grep -c '"[a-z_]*":' apps/api/action_router/dispatchers/internal_dispatcher.py

# After modification, log total count
print(f"Total handlers registered: {len(handlers)}")
# Expected: ~95
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 8: Wire Missing Handlers to Dispatcher

Step-by-step:
1. Read internal_dispatcher.py - note the INTERNAL_HANDLERS dict structure
2. Read p1_compliance_handlers.py - find get_p1_compliance_handlers() function
3. Read p1_purchasing_handlers.py - find get_p1_purchasing_handlers() function
4. Read p2_mutation_light_handlers.py - find get_p2_mutation_light_handlers() function
5. Read p3_read_only_handlers.py - find get_p3_read_only_handlers() function
6. Modify internal_dispatcher.py:
   - Add imports for all getter functions
   - Create build_handler_registry() that merges all handlers
   - Update the dispatch logic to use merged handlers
7. Print total handler count (expect ~95)

Show evidence at each step. Do NOT skip file reads.
Stop when done and report handler count.
```

---

## PHASE 9: Seed Empty Tables

### Description

Create SQL seed scripts to populate empty tables with test data so handlers can be properly tested.

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p1_compliance_handlers.py  # See required fields
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p3_read_only_handlers.py   # See view handlers
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/scripts/seed_hours_of_rest.sql
/Users/celeste7/Documents/Cloud_PMS/scripts/seed_checklists.sql
```

### Tasks

1. Read p1_compliance_handlers.py to understand pms_hours_of_rest schema
2. Read p3_read_only_handlers.py to understand view requirements
3. Create seed_hours_of_rest.sql:
   ```sql
   -- Seed 7 days of HOR data for test user
   INSERT INTO pms_hours_of_rest (
     id, yacht_id, user_id, record_date, rest_periods,
     total_rest_hours, is_daily_compliant, is_weekly_compliant,
     location, voyage_type, status, created_at
   ) VALUES
   -- Day 1: Compliant (11 hrs rest)
   ('hor-001', '85fe1119-b04c-41ac-80f1-829d23322598',
    'a0d66b00-581f-4d27-be6b-5b679d5cd347',
    '2026-01-10',
    '[{"start": "22:00", "end": "06:00", "hours": 8}, {"start": "12:00", "end": "15:00", "hours": 3}]',
    11, true, true, 'At Sea', 'at_sea', 'submitted', NOW()),
   -- ... more rows
   ```
4. Create seed_checklists.sql (if tables exist)
5. Run seeds against tenant database

### Verification

```sql
SELECT COUNT(*) FROM pms_hours_of_rest;  -- Expect: 7+
SELECT COUNT(*) FROM pms_checklists;      -- Expect: 3+
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 9: Seed Empty Tables

Step-by-step:
1. Read p1_compliance_handlers.py - extract pms_hours_of_rest schema requirements
2. Read p3_read_only_handlers.py - extract view_hours_of_rest requirements
3. Check if pms_hours_of_rest table exists (query information_schema or try SELECT)
4. Create scripts/seed_hours_of_rest.sql with 7 days of sample data
5. Create scripts/seed_checklists.sql if pms_checklists table exists
6. Run the seed scripts

Show SQL and row counts. Stop when tables have data.
```

---

## PHASE 10: Implement Trigger/Threshold Logic

### Description

Add business rule logic that automatically triggers actions based on conditions (low stock, overdue items, compliance violations).

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/inventory_handlers.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/work_order_handlers.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/p1_compliance_handlers.py
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
```

### Files to Create/Modify

```
/Users/celeste7/Documents/Cloud_PMS/apps/api/services/trigger_service.py
/Users/celeste7/Documents/Cloud_PMS/apps/api/routes/triggers_routes.py
```

### Triggers to Implement

| Trigger ID | Condition | Check Query | Action |
|------------|-----------|-------------|--------|
| LOW_STOCK | part.quantity_on_hand < part.minimum_stock | `SELECT * FROM pms_parts WHERE quantity_on_hand < minimum_stock` | Flag for reorder |
| OVERDUE_WO | wo.due_date < NOW() AND status NOT IN ('completed','cancelled') | `SELECT * FROM pms_work_orders WHERE due_date < NOW() AND status = 'planned'` | Set attention_flag |
| HOR_VIOLATION | total_rest_hours < 10 | `SELECT * FROM pms_hours_of_rest WHERE total_rest_hours < 10` | Create compliance alert |
| MAINTENANCE_DUE | equipment.next_maintenance < NOW() + 7 days | `SELECT * FROM pms_equipment WHERE next_service_date < NOW() + INTERVAL '7 days'` | Show warning badge |

### Tasks

1. Read ACTION_OFFERING_RULES.md to understand trigger specifications
2. Create trigger_service.py with check functions:
   ```python
   class TriggerService:
       def check_low_stock(self, yacht_id: str) -> List[Dict]:
           # Query parts below minimum
           # Return list of triggered items

       def check_overdue_work_orders(self, yacht_id: str) -> List[Dict]:
           # Query overdue WOs
           # Return list with attention flags

       def check_hor_violations(self, yacht_id: str) -> List[Dict]:
           # Query non-compliant HOR records
           # Return violations
   ```
3. Create triggers_routes.py with endpoint:
   ```python
   @router.get("/v1/triggers/check")
   async def check_all_triggers(yacht_id: str):
       # Run all trigger checks
       # Return combined results
   ```
4. Add trigger checks to relevant handlers (e.g., after updating stock)

### Verification

```bash
# Test trigger endpoint
curl -X GET "https://pipeline-core.int.celeste7.ai/v1/triggers/check?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598" \
  -H "Authorization: Bearer $TOKEN"
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 10: Implement Trigger/Threshold Logic

Step-by-step:
1. Read ACTION_OFFERING_RULES.md to understand trigger specifications
2. Read inventory_handlers.py to understand stock checking
3. Read work_order_handlers.py to understand WO status logic
4. Create apps/api/services/trigger_service.py with:
   - check_low_stock()
   - check_overdue_work_orders()
   - check_hor_violations()
   - check_maintenance_due()
5. Create apps/api/routes/triggers_routes.py with /v1/triggers/check endpoint
6. Register routes in main app
7. Test endpoint with curl

Show code for each trigger. Verify endpoint returns data.
```

---

## PHASE 11: Button Visibility Matrix Tests

### Description

Create comprehensive E2E tests verifying all 57 microaction buttons appear in the correct UI contexts with correct conditions.

### Files to Read

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/spotlight/MicroactionButton.tsx
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/tests/fixtures/microaction_registry.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/visibility_matrix.spec.ts
```

### Tasks

1. Read MICRO_ACTION_REGISTRY.md - extract all 57 actions with their contexts
2. Read ACTION_OFFERING_RULES.md - extract visibility conditions per action
3. Create tests/fixtures/microaction_registry.ts:
   ```typescript
   export const MICROACTION_REGISTRY = [
     {
       id: 'diagnose_fault',
       cluster: '01_fix_something',
       context: 'fault_detail',
       button_selector: '[data-action="diagnose_fault"]',
       visible_when: {
         entity_status: ['open'],
         user_roles: ['any'],
       },
       hidden_when: {
         entity_status: ['diagnosed', 'closed', 'false_alarm'],
       },
     },
     // ... all 57 actions
   ];
   ```
4. Create visibility_matrix.spec.ts:
   ```typescript
   import { MICROACTION_REGISTRY } from '../../fixtures/microaction_registry';

   for (const action of MICROACTION_REGISTRY) {
     test.describe(`Button: ${action.id}`, () => {

       test(`visible when conditions met`, async ({ page }) => {
         // Create entity with required status
         // Navigate to context
         // Assert button visible
         await expect(page.locator(action.button_selector)).toBeVisible();
       });

       test(`hidden when conditions NOT met`, async ({ page }) => {
         // Create entity with wrong status
         // Navigate to context
         // Assert button NOT visible
         await expect(page.locator(action.button_selector)).not.toBeVisible();
       });
     });
   }
   ```

### Verification

```bash
npx playwright test tests/e2e/microactions/visibility_matrix.spec.ts --reporter=list
# Expected: 114 tests (57 visible + 57 hidden)
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 11: Button Visibility Matrix Tests

Step-by-step:
1. Read MICRO_ACTION_REGISTRY.md - list all 57 actions with contexts
2. Read ACTION_OFFERING_RULES.md - extract visibility conditions
3. Read MicroactionButton.tsx - understand button rendering logic
4. Create tests/fixtures/microaction_registry.ts with all 57 actions:
   - id, cluster, context, button_selector
   - visible_when conditions
   - hidden_when conditions
5. Create tests/e2e/microactions/visibility_matrix.spec.ts
6. Run tests, report pass/fail count

Output the full microaction_registry.ts file. Show test results.
```

---

## PHASE 12: RLS Permission Tests

### Description

Test that Row Level Security policies correctly restrict actions based on user roles. Use real user tokens, NOT service key.

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/supabase/migrations/*_rls*.sql  # RLS policies
/Users/celeste7/Documents/Cloud_PMS/tests/helpers/supabase_tenant.ts
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/rls_permissions.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/fixtures/test_users.ts
```

### Test Users Required

| Role | Email | Password | Can Do | Cannot Do |
|------|-------|----------|--------|-----------|
| member | member@test.celeste7.ai | TestPass1! | View, add notes | Approve, delete |
| chief_engineer | chief@test.celeste7.ai | TestPass1! | All WO/fault actions | Delete yacht |
| eto | eto@test.celeste7.ai | TestPass1! | Equipment actions | Approve purchases |
| captain | captain@test.celeste7.ai | TestPass1! | Approve purchases | - |
| manager | manager@test.celeste7.ai | TestPass1! | All actions | - |

### Tasks

1. Create test_users.ts:
   ```typescript
   export const TEST_USERS = {
     member: { email: 'member@test.celeste7.ai', password: 'TestPass1!', role: 'member' },
     chief_engineer: { email: 'chief@test.celeste7.ai', password: 'TestPass1!', role: 'chief_engineer' },
     // ...
   };
   ```
2. Create rls_permissions.spec.ts:
   ```typescript
   const ROLE_ACTION_MATRIX = [
     { action: 'approve_purchase', allowed: ['captain', 'manager'], denied: ['member', 'eto'] },
     { action: 'delete_document', allowed: ['chief_engineer', 'captain', 'manager'], denied: ['member'] },
     // ...
   ];

   for (const { action, allowed, denied } of ROLE_ACTION_MATRIX) {
     for (const role of allowed) {
       test(`${action} allowed for ${role}`, async () => {
         await loginAs(TEST_USERS[role]);
         const response = await executeAction(action, payload);
         expect(response.status).not.toBe(403);
       });
     }
     for (const role of denied) {
       test(`${action} denied for ${role}`, async () => {
         await loginAs(TEST_USERS[role]);
         const response = await executeAction(action, payload);
         expect(response.status).toBe(403);
       });
     }
   }
   ```

### Verification

```bash
npx playwright test tests/e2e/microactions/rls_permissions.spec.ts
# All role-based tests should pass
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 12: RLS Permission Tests

Step-by-step:
1. Read RLS migration files to understand permission policies
2. Read supabase_tenant.ts to understand auth helpers
3. Create tests/fixtures/test_users.ts with 5 role-based test accounts
4. Create tests/e2e/microactions/rls_permissions.spec.ts:
   - Define ROLE_ACTION_MATRIX mapping actions to allowed/denied roles
   - Generate tests for each action × role combination
   - Use real user tokens (login flow), not service key
5. Run tests, report results

Show the ROLE_ACTION_MATRIX. Report pass/fail by role.
```

---

## PHASE 13: Edge Cases & Validation Tests

### Description

Test boundary conditions, invalid inputs, and error handling for all actions.

### Files to Read

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md
/Users/celeste7/Documents/Cloud_PMS/apps/api/handlers/*.py  # Validation logic
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/edge_cases.spec.ts
```

### Edge Cases to Test

| Action | Test Case | Input | Expected |
|--------|-----------|-------|----------|
| add_wo_part | Zero quantity | `{ quantity: 0 }` | 400 |
| add_wo_part | Negative quantity | `{ quantity: -1 }` | 400 |
| add_wo_part | Exceeds max | `{ quantity: 1000001 }` | 400 |
| update_hours_of_rest | Over 24 hours | `{ rest_periods: [{hours: 25}] }` | 400 |
| update_hours_of_rest | Negative hours | `{ rest_periods: [{hours: -1}] }` | 400 |
| delete_document | Already deleted | `{ document_id: 'deleted-doc' }` | 404 or 409 |
| delete_shopping_item | Linked to order | `{ item_id: 'linked-item' }` | 409 |
| approve_purchase | Self-approval | Same user who created | 403 |
| approve_purchase | Wrong status | PO status = 'draft' | 400 |
| create_work_order | Title too short | `{ title: 'AB' }` | 400 |
| create_work_order | Invalid priority | `{ priority: 'super_urgent' }` | 400 |

### Tasks

1. Read COMPLETE_ACTION_EXECUTION_CATALOG.md for validation rules
2. Read handler files to understand validation logic
3. Create edge_cases.spec.ts:
   ```typescript
   const EDGE_CASES = [
     { action: 'add_wo_part', name: 'zero_quantity', payload: { quantity: 0 }, expected: 400 },
     { action: 'add_wo_part', name: 'negative_quantity', payload: { quantity: -1 }, expected: 400 },
     // ...
   ];

   for (const edge of EDGE_CASES) {
     test(`${edge.action}: ${edge.name}`, async () => {
       const response = await executeAction(edge.action, edge.payload);
       expect(response.status).toBe(edge.expected);
     });
   }
   ```

### Verification

```bash
npx playwright test tests/e2e/microactions/edge_cases.spec.ts
# All edge cases should return expected status codes
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 13: Edge Cases & Validation Tests

Step-by-step:
1. Read COMPLETE_ACTION_EXECUTION_CATALOG.md - extract validation rules per action
2. Read handler files - find validation logic (min/max, required fields, status checks)
3. Create tests/e2e/microactions/edge_cases.spec.ts with:
   - EDGE_CASES array covering all boundary conditions
   - Tests for invalid inputs, missing fields, wrong states
4. Run tests, verify all return expected status codes

List all edge cases tested. Report pass/fail count.
```

---

## PHASE 14: GitHub CI Workflow

### Description

Create automated CI workflow that runs all verification tests on every push/PR.

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/.github/workflows/microaction_verification.yml
```

### Workflow Structure

```yaml
name: Microaction Verification Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:  # Manual trigger
  schedule:
    - cron: '0 6 * * *'  # Daily at 6am UTC

env:
  TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
  TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
  TEST_USER_YACHT_ID: ${{ secrets.TEST_USER_YACHT_ID }}

jobs:
  handler-count:
    name: Verify Handler Registration
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Count registered handlers
        run: |
          count=$(grep -c '"[a-z_]*":' apps/api/action_router/dispatchers/internal_dispatcher.py)
          echo "Registered handlers: $count"
          if [ $count -lt 90 ]; then
            echo "ERROR: Expected 90+ handlers, found $count"
            exit 1
          fi

  visibility-matrix:
    name: Button Visibility Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test tests/e2e/microactions/visibility_matrix.spec.ts
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: visibility-matrix-report
          path: playwright-report/

  rls-permissions:
    name: RLS Permission Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test tests/e2e/microactions/rls_permissions.spec.ts

  edge-cases:
    name: Edge Case Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test tests/e2e/microactions/edge_cases.spec.ts

  summary:
    name: Verification Summary
    needs: [handler-count, visibility-matrix, rls-permissions, edge-cases]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check results
        run: |
          echo "## Microaction Verification Results" >> $GITHUB_STEP_SUMMARY
          echo "| Check | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| Handler Count | ${{ needs.handler-count.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Visibility Matrix | ${{ needs.visibility-matrix.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| RLS Permissions | ${{ needs.rls-permissions.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Edge Cases | ${{ needs.edge-cases.result }} |" >> $GITHUB_STEP_SUMMARY
```

### Tasks

1. Create the workflow file
2. Add required secrets to GitHub repo settings
3. Test workflow with manual dispatch
4. Verify all jobs pass

### Verification

```bash
# Trigger workflow manually
gh workflow run microaction_verification.yml

# Check status
gh run list --workflow=microaction_verification.yml
```

### Prompt for Claude

```
Read MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 14: GitHub CI Workflow

Step-by-step:
1. Create .github/workflows/microaction_verification.yml with:
   - handler-count job (verify 90+ handlers)
   - visibility-matrix job (run button tests)
   - rls-permissions job (run role tests)
   - edge-cases job (run validation tests)
   - summary job (aggregate results)
2. List required GitHub secrets
3. Show how to trigger workflow manually

Output the complete workflow file.
```

---

## EXECUTION CHECKLIST

| Phase | Description | Status | Blocker |
|-------|-------------|--------|---------|
| 8 | Wire missing handlers | NOT STARTED | None |
| 9 | Seed empty tables | NOT STARTED | Phase 8 |
| 10 | Implement triggers | NOT STARTED | Phase 8, 9 |
| 11 | Visibility matrix tests | NOT STARTED | Phase 8 |
| 12 | RLS permission tests | NOT STARTED | Phase 8 |
| 13 | Edge case tests | NOT STARTED | Phase 8 |
| 14 | GitHub CI workflow | NOT STARTED | Phase 11-13 |

---

## COMPLETION CRITERIA

The system is **production-ready** when:

- [ ] 95+ handlers registered in dispatcher
- [ ] All empty tables seeded with test data
- [ ] Trigger logic implemented and tested
- [ ] 114 visibility tests passing (57 visible + 57 hidden)
- [ ] RLS tests passing for all 5 roles
- [ ] Edge case tests passing
- [ ] CI workflow green on main branch
- [ ] Manual smoke test on app.celeste7.ai passes

---

## QUICK START

To begin, give Claude this prompt:

```
Read /Users/celeste7/Documents/Cloud_PMS/MICROACTIONS_COMPLETION_PLAN.md

Execute PHASE 8: Wire Missing Handlers to Dispatcher

Follow the step-by-step instructions in the plan.
Show evidence at each step.
Do NOT skip file reads.
```

---

**END OF PLAN**
