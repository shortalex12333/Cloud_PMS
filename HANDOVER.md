# HANDOVER FOR NEXT ENGINEER

**Assume you are senior, have zero prior context.**

Date: 2026-01-22

---

## IF YOU HAD 1 WEEK, WHAT WOULD YOU DO FIRST?

### Day 1: Verify The Foundation (8 hours)

**Morning (4 hours): Confirm What Actually Works**

```bash
# 1. Check actual table names in production DB (30 min)
# Connect to TENANT DB
psql $TENANT_SUPABASE_URL

# List all tables
\dt

# Expected: pms_equipment, pms_faults, pms_work_orders, etc.
# OR: equipment, faults, work_orders, etc.
# Compare to handler references: grep 'table("' apps/api/routes/p0_actions_routes.py
# If mismatch: handlers will fail at runtime. FIX IMMEDIATELY.
```

```bash
# 2. Run health check (5 min)
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium

# Expected: 61/64 pass
# If <50 pass: something broke, investigate before continuing
```

```bash
# 3. Test ONE mutation end-to-end (1 hour)
# Goal: Prove ONE action actually writes to database

# Run action
curl -X POST https://api.celesteos.com/v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_work_order",
    "payload": {
      "title": "Test WO from new engineer",
      "priority": "medium",
      "assigned_to": "'$TEST_USER_ID'"
    },
    "yacht_id": "'$TEST_YACHT_ID'",
    "user_id": "'$TEST_USER_ID'"
  }'

# Record work_order_id from response
WO_ID="<work_order_id from response>"

# Query database directly
psql $TENANT_SUPABASE_URL -c "SELECT * FROM pms_work_orders WHERE id = '$WO_ID';"

# Expected: 1 row returned
# If 0 rows: Handler returned 200 but didn't write to DB. CRITICAL BUG.
```

```bash
# 4. Check audit log (30 min)
psql $TENANT_SUPABASE_URL -c "SELECT * FROM pms_audit_log WHERE action = 'create_work_order' AND entity_id = '$WO_ID';"

# Expected: 1 row returned
# If 0 rows: No audit logging. COMPLIANCE VIOLATION.
```

**Afternoon (4 hours): Document What You Found**

Create `DAY_1_FINDINGS.md`:

```markdown
# Day 1 Findings

## Table Names
- Actual: [pms_equipment | equipment]
- Handlers reference: pms_equipment
- Match: [YES | NO]
- Action needed: [NONE | FIX HANDLERS | FIX MIGRATIONS]

## Health Check
- Pass rate: 61/64 (95%)
- New failures: [NONE | list]

## Mutation Test: create_work_order
- HTTP response: [200 | 500 | other]
- DB row created: [YES | NO]
- Audit log created: [YES | NO]
- Conclusion: [WORKING | BROKEN | PARTIALLY WORKING]

## Next Steps
1. [Fix table name mismatch | Test more mutations | Add audit logging]
2. [...]
```

**Why this matters:**
- If table names mismatch: ALL handlers broken, entire system non-functional
- If mutation test fails: "95% health" is meaningless, need to verify all 64 actions
- If no audit log: compliance violation, legal liability

---

### Day 2-3: Verify Critical Path (16 hours)

**Goal:** Prove the 10 most critical actions actually work end-to-end.

**Critical actions (in order of importance):**
1. `diagnose_fault` - Core workflow starter
2. `create_work_order` - Main mutation
3. `assign_work_order` - Assignment workflow
4. `add_work_order_note` - Communication
5. `mark_work_order_complete` - Workflow closer
6. `acknowledge_fault` - Fault acknowledgment
7. `view_equipment_details` - Most common read
8. `view_work_order_details` - Most common read
9. `log_part_usage` - Inventory tracking
10. `view_stock_level` - Inventory tracking

**For each action (1.5 hours each = 15 hours):**

```bash
# 1. Run action via API (10 min)
curl -X POST https://api.celesteos.com/v1/actions/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"action": "<action_name>", "payload": {...}, "yacht_id": "...", "user_id": "..."}'

# 2. Query DB to verify mutation (if mutation) (10 min)
psql $TENANT_SUPABASE_URL -c "SELECT * FROM <table> WHERE id = '<entity_id>';"

# 3. Query audit log (10 min)
psql $TENANT_SUPABASE_URL -c "SELECT * FROM pms_audit_log WHERE action = '<action_name>' AND entity_id = '<entity_id>';"

# 4. Test RLS: Create entity with Yacht A, query with Yacht B (20 min)
# Expected: 0 rows returned (yacht isolation works)
# If rows returned: RLS BROKEN, CRITICAL SECURITY BUG

# 5. Document results (30 min)
```

**At end of Day 3:** You'll know if critical path works or not.

**If <7/10 working:** System not pilot-ready. Focus on fixing mutations.

**If 7-10/10 working:** System pilot-ready with caveats. Proceed to Day 4.

---

### Day 4-5: Close the Audit Gap (16 hours)

**Goal:** Add audit logging to all 60 actions missing it.

**Why audit logging matters:**
- ISO 9001, SOLAS require audit trails for maintenance actions
- Without audit logs, can't reconstruct what happened if something breaks
- Legal liability if can't prove who did what when

**Approach:**

```python
# 1. Create audit helper function (1 hour)
# File: apps/api/utils/audit.py

async def write_audit_log(
    db_client,
    action: str,
    entity_id: str,
    yacht_id: str,
    user_id: str,
    old_values: dict = {},
    new_values: dict = {}
):
    """Write audit log entry for any mutation."""
    audit_entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_id": entity_id,
        "yacht_id": yacht_id,
        "user_id": user_id,
        "old_values": old_values,
        "new_values": new_values,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        db_client.table("pms_audit_log").insert(audit_entry).execute()
        logger.info(f"Audit log created: {action} / {entity_id}")
    except Exception as e:
        # Don't fail action if audit fails, but log error
        logger.error(f"Audit log failed: {action} / {entity_id} / {e}")
```

```python
# 2. Add audit call to each handler (5 min × 60 = 5 hours)
# Pattern:

# BEFORE:
result = db.table("pms_work_orders").insert(wo_data).execute()
return {"status": "success", "work_order_id": work_order_id}

# AFTER:
from apps.api.utils.audit import write_audit_log

result = db.table("pms_work_orders").insert(wo_data).execute()
work_order_id = result.data[0]["id"]

# Add audit log
await write_audit_log(
    db,
    action="create_work_order",
    entity_id=work_order_id,
    yacht_id=yacht_id,
    user_id=user_id,
    new_values=wo_data
)

return {"status": "success", "work_order_id": work_order_id}
```

```bash
# 3. Test audit logging works (10 min × 60 = 10 hours)
# For each action, run action → query audit log → verify entry exists
```

**At end of Day 5:** All 60 actions have audit logging.

**Deliverable:** PR with audit logging added to all handlers.

---

## IF SOMETHING BREAKS IN PRODUCTION, WHERE DO YOU LOOK?

### Symptom: "Action returns 500 Internal Server Error"

**Check in this order:**

1. **Backend logs (Render or wherever backend is deployed)**
   ```bash
   # Check for Python stack traces
   # Look for: "Traceback (most recent call last)"
   # Common errors:
   #   - KeyError: Missing field in payload
   #   - AttributeError: Trying to access None.field
   #   - psycopg2.OperationalError: Database connection failed
   ```

2. **Database connection**
   ```bash
   # Is DB reachable?
   psql $TENANT_SUPABASE_URL -c "SELECT 1;"

   # Expected: "1"
   # If timeout: DB down or firewall blocking
   # If "FATAL: password authentication failed": Credentials rotated
   ```

3. **Database RLS policies**
   ```bash
   # Was session variable set?
   # Check backend logs for: "set_yacht_context called with yacht_id=..."
   # If missing: RLS will block all queries, return empty results
   ```

4. **Handler code**
   ```bash
   # File: apps/api/routes/p0_actions_routes.py
   # Search for action name: grep -n "action == \"create_work_order\"" apps/api/routes/p0_actions_routes.py
   # Check line number from grep, read handler logic
   # Common bugs:
   #   - Referencing wrong table name (pms_equipment vs equipment)
   #   - Referencing wrong column name (quantity_on_hand vs current_quantity_onboard)
   #   - Missing required field in payload
   ```

---

### Symptom: "Action returns 200 but nothing happens"

**Check in this order:**

1. **Query database directly**
   ```bash
   # Did the mutation actually write to DB?
   psql $TENANT_SUPABASE_URL -c "SELECT * FROM pms_work_orders WHERE id = '<entity_id>';"

   # Expected: 1 row
   # If 0 rows: Handler returned 200 but didn't write to DB
   ```

2. **Check handler return value**
   ```bash
   # Does response include entity_id?
   # If response is {"status": "success", "message": "..."} with no entity_id:
   #   - Handler might not have entity_id to return
   #   - Handler might have failed silently
   ```

3. **Check RLS policies**
   ```bash
   # Was mutation blocked by RLS?
   # Check handler logs for: "INSERT returned 0 rows"
   # If RLS policy too restrictive, INSERT succeeds but returns empty (no error)
   ```

---

### Symptom: "User from Yacht A sees Yacht B's data"

**CRITICAL SECURITY BUG. Check in this order:**

1. **Was JWT validated?**
   ```python
   # Check backend logs for: "JWT validated: yacht_id=..."
   # If missing: JWT validation skipped, all data visible
   ```

2. **Was session variable set?**
   ```python
   # Check backend logs for: "set_yacht_context called with yacht_id=..."
   # If missing: RLS policies don't filter, all rows visible
   ```

3. **Are RLS policies correct?**
   ```sql
   # Check RLS policy on affected table
   SELECT schemaname, tablename, policyname, qual
   FROM pg_policies
   WHERE tablename = 'pms_equipment';

   # Expected: USING (yacht_id = current_setting('app.current_yacht_id')::uuid)
   # If using hardcoded yacht_id or wrong session variable: RLS broken
   ```

4. **Was service role key used instead of anon key?**
   ```bash
   # Check frontend code for: SUPABASE_SERVICE_ROLE_KEY
   # If found: Service role bypasses RLS, all data visible
   # If found: CRITICAL SECURITY ISSUE, rotate service role key immediately
   ```

---

### Symptom: "NL query returns wrong actions"

**Check in this order:**

1. **GPT extraction output**
   ```bash
   # Check backend logs for: "GPT extracted: {entities: [...], problem: ...}"
   # Common issues:
   #   - Wrong entity extracted (e.g., "engine" instead of "generator")
   #   - No entities extracted (GPT returned empty)
   #   - Ambiguous entities (e.g., "pump" matches 5 different pumps)
   ```

2. **Table capabilities mapping**
   ```bash
   # File: apps/api/services/pipeline_service.py
   # Check TABLE_CAPABILITIES dict
   # Common issues:
   #   - Entity type not mapped to any table (e.g., "battery" not in TABLE_CAPABILITIES)
   #   - Table capabilities don't include expected action (e.g., equipment → [diagnose_fault] but user expects [view_manual])
   ```

3. **Action button logic**
   ```bash
   # File: apps/web/src/components/chat/*
   # Check how action buttons are rendered
   # Common issues:
   #   - Action button not wired to correct handler
   #   - Action button payload missing required fields
   ```

---

## WHAT MUST NOT BE REFACTORED CASUALLY

### Database Migrations

**Files:** `database/master_migrations/*`, `database/migrations/*`

**Why critical:**
- These define the entire data model
- Changing them requires re-running migrations on production DB
- If migrations fail mid-way, production DB is in inconsistent state

**If you need to change schema:**
1. **DO NOT edit existing migration files**
2. Create NEW migration file with incremental changes
3. Test on local DB first
4. Test on staging DB second
5. Run on production DB during maintenance window
6. Have rollback plan ready

**Example:**
```bash
# WRONG: Edit existing migration
# vim database/migrations/02_p0_actions_tables_REVISED.sql
# # Add new column to pms_work_orders table
# ALTER TABLE pms_work_orders ADD COLUMN new_field TEXT;

# RIGHT: Create new migration
# vim database/migrations/12_add_new_field_to_work_orders.sql
# ALTER TABLE pms_work_orders ADD COLUMN new_field TEXT;
# # Then run migration on production
```

---

### Action Handlers File

**File:** `apps/api/routes/p0_actions_routes.py` (4,160 lines)

**Why critical:**
- Contains ALL 81 action handlers
- Breaking one handler can affect multiple actions (copy-paste reuse)
- No test coverage for most handlers (only HTTP-level tests)

**If you need to change a handler:**
1. **Read the entire handler first** (don't assume from name)
2. **Check what tables it queries** (grep for `table("pms_...`)
3. **Test locally before deploying** (run e2e test for that action)
4. **Deploy during low-traffic window** (in case handler breaks)
5. **Have rollback ready** (git revert + redeploy)

**Common mistakes:**
- Changing field name in one handler, breaking another that uses same field
- Assuming column name from code, not checking actual DB schema
- Changing response format, breaking frontend parsing

**Example:**
```python
# WRONG: Assume column name
result = db.table("pms_parts").select("current_quantity_onboard").execute()

# RIGHT: Check actual schema first
# psql -c "\d pms_parts"  # Shows: quantity_on_hand, not current_quantity_onboard
result = db.table("pms_parts").select("quantity_on_hand").execute()
```

---

### RLS Policies

**Files:** Database migrations with `CREATE POLICY` statements

**Why critical:**
- RLS is the ONLY enforcement of yacht isolation
- If RLS broken, cross-yacht data leaks occur
- No test coverage for RLS (assumed working but never verified)

**If you need to change RLS policy:**
1. **Test on local DB first** (create multi-yacht test data, verify isolation)
2. **Test on staging DB second** (verify policy doesn't block legitimate queries)
3. **Monitor logs after deployment** (watch for "0 rows returned" errors)
4. **Have rollback ready** (DROP POLICY + CREATE POLICY with old definition)

**Common mistakes:**
- Creating policy that's too restrictive (blocks legitimate queries)
- Creating policy that's too permissive (leaks data across yachts)
- Forgetting to set session variable before queries (policy doesn't filter)

**Example:**
```sql
-- WRONG: Too permissive (allows all users)
CREATE POLICY "Allow all" ON pms_equipment USING (true);

-- WRONG: Too restrictive (blocks all non-service-role queries)
CREATE POLICY "Service role only" ON pms_equipment USING (false);

-- RIGHT: Filter by yacht_id via session variable
CREATE POLICY "Yacht isolation" ON pms_equipment
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

---

### Test Helper: test-data-discovery.ts

**File:** `tests/helpers/test-data-discovery.ts`

**Why critical:**
- Auto-discovers entity IDs from test DB (equipment_id, fault_id, work_order_id, etc.)
- All e2e tests depend on this
- If this breaks, all tests fail with "entity not found"

**If you need to change it:**
1. **Understand what it does** (reads `tests/fixtures/microaction_registry.ts`, queries DB for entity IDs)
2. **Test locally first** (run one e2e test, verify IDs discovered correctly)
3. **Don't change query logic** (only change if DB schema changes)

**Common mistakes:**
- Changing query to filter by wrong yacht_id (returns no results)
- Changing query to return multiple results (test expects single entity)
- Breaking query syntax (all tests fail immediately)

---

### Environment Variables

**Files:** `.env`, `.env.e2e`, Render environment settings

**Why critical:**
- Wrong credentials = all DB queries fail
- Wrong yacht_id = tests query wrong yacht's data
- Service role key leaked = security breach

**If you need to change env vars:**
1. **Update .env.example first** (documents what vars are needed)
2. **Update .env.e2e for tests** (test vars different from prod vars)
3. **Update Render settings for backend** (prod vars)
4. **NEVER commit actual secrets to Git** (only .env.example with placeholders)

**Critical vars:**
```bash
# Master DB (fleet registry, user accounts)
MASTER_SUPABASE_URL=https://xxx.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# Tenant DB (PMS data for all yachts)
TENANT_SUPABASE_URL=https://yyy.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# Test data
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

---

## WHAT ASSUMPTIONS ARE SAFE TO RELY ON

### Safe Assumptions

✅ **Yacht = tenant boundary**
- All PMS tables have `yacht_id` column
- RLS policies filter by `yacht_id`
- Users can belong to multiple yachts (via MASTER DB)

✅ **Users from Yacht A cannot see Yacht B's data**
- RLS policies enforce isolation (not tested but policies look correct)
- Session variable `app.current_yacht_id` set by backend

✅ **Action handlers exist for all 64 documented actions**
- File: `apps/api/routes/p0_actions_routes.py`
- 81 handlers total (some actions have multiple variants)

✅ **E2E test infrastructure works**
- Playwright tests run reliably
- Test data discovery works (auto-finds entity IDs)
- Health check test passes (61/64 actions return 200)

✅ **Database schema is stable**
- Migrations have been applied
- Tables exist (need to verify actual names match handler references)
- Columns exist (need to verify actual names match handler references)

---

### Unsafe Assumptions (DO NOT RELY ON)

❌ **"95% health" means actions actually work**
- Health metric is HTTP-only (checks if handler returns 200)
- Does NOT verify database mutations occurred
- Does NOT verify audit logs created
- Only 1/64 actions proven to work end-to-end

❌ **Handlers write to database**
- Only 1/64 handlers proven with database mutation
- 60/64 unverified (might return 200 without writing to DB)

❌ **Audit logging is complete**
- Only 4/64 handlers create audit log entries
- 60/64 missing audit logging (compliance violation)

❌ **RLS has been tested**
- RLS policies exist but not tested
- Unknown if yacht isolation actually works
- No multi-yacht test scenarios

❌ **Documentation is current**
- Many docs are stale or aspirational
- Most docs in `_archive/` are outdated
- Trust code + tests over docs

❌ **Table names match between migrations and handlers**
- Migrations create `public.equipment`, handlers reference `pms_equipment`
- This inconsistency is unverified
- Could cause all handlers to fail at runtime

---

## SAFE BETS FOR QUICK WINS

### If you have 4 hours:

**Test 5 critical actions end-to-end** (mutation → DB query → verify row → verify audit log)

Result: You'll know if critical path works or if system fundamentally broken.

---

### If you have 1 day:

**Add audit logging to top 10 most-used actions**

Result: Compliance risk reduced, debugging becomes possible.

---

### If you have 3 days:

**Verify all 64 actions with mutation proof tests**

Result: You'll know exactly what works and what doesn't. Can confidently pilot or block pilot.

---

### If you have 1 week:

**Close the verification gap** (mutation tests + audit logging + basic RLS tests)

Result: System is pilot-ready with confidence.

---

## DEBUGGING DECISION TREE

```
Action fails
│
├─ Returns 500?
│  ├─ Check backend logs for stack trace
│  ├─ Check DB connection (psql $TENANT_SUPABASE_URL -c "SELECT 1;")
│  └─ Check handler code for bugs
│
├─ Returns 200 but nothing happens?
│  ├─ Query DB directly (did mutation occur?)
│  ├─ Check response for entity_id (does it exist?)
│  └─ Check RLS policies (was mutation blocked?)
│
├─ Returns wrong data?
│  ├─ Check RLS session variable (was yacht_id set?)
│  ├─ Check JWT validation (was yacht_id extracted?)
│  └─ Check RLS policies (are they correct?)
│
└─ Frontend shows error?
   ├─ Check response format (does frontend expect different structure?)
   ├─ Check network tab (is request even reaching backend?)
   └─ Check CORS (is origin allowed?)
```

---

## FILES TO READ FIRST

**In this order:**

1. **This file (HANDOVER.md)** - You're here
2. **SYSTEM_INVENTORY.md** - What exists, why it exists
3. **SECURITY_INVARIANTS.md** - What must never be broken
4. **MATURITY_ASSESSMENT.md** - Brutally honest status
5. **`_HANDOVER/README.md`** - Quick-start guide
6. **`apps/api/routes/p0_actions_routes.py`** - All 81 action handlers
7. **`tests/e2e/diagnostic_baseline.spec.ts`** - Health check tests

**DO NOT read first:**
- Docs in `_archive/` (outdated)
- Agent/Watchdog/Verification docs (meta-system, not product)
- Old handover docs in root (superseded by this file)

---

## WHEN TO CALL FOR HELP

**Call immediately if:**
- Health check passes <50/64 actions (system fundamentally broken)
- You find service role key in frontend code (security breach)
- RLS test shows cross-yacht data leak (security breach)
- Audit log table doesn't exist (compliance risk)

**Call within 24 hours if:**
- Table naming mismatch found (all handlers might be broken)
- 0 audit log entries found (compliance violation)
- Database mutations unverified after 1 week (project at risk)

**Call within 1 week if:**
- You're stuck on verification approach (need guidance on priorities)
- You need production DB access (can't verify without it)
- You need to change RLS policies (high risk, need review)

---

## FINAL ADVICE

**Trust the code + tests, not the docs.**

- If docs say "95% working" but tests show only 1/64 proven: trust tests.
- If docs say "audit logging complete" but queries show 4/64: trust queries.
- If docs say "RLS tested" but no test files exist: assume not tested.

**When in doubt, verify.**

- Don't assume handlers write to DB: test one, confirm it works.
- Don't assume RLS works: create multi-yacht test data, verify isolation.
- Don't assume table names match: query production DB, verify.

**Work incrementally.**

- Don't try to verify all 64 actions at once: start with top 10.
- Don't try to add audit logging to all 60 handlers at once: start with 10.
- Don't try to fix all issues at once: fix highest-impact issues first.

**Communicate risks up.**

- If you find security issues: escalate immediately.
- If you find compliance issues: document and prioritize.
- If you find fundamental issues (table naming mismatch): block pilot until fixed.

**Good luck. This system is 60% of the way there. You can get it to 100%.**

---

**End of handover.**
