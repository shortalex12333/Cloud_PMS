# Lessons Learned

---

## LESSON: Batched Cleanup Specs Get Underspecified — Delete Dead Code Per Task

**Date:** 2026-03-17
**Context:** Phase 5 Execution Layer Refactor — migrating 69 elif blocks from `p0_actions_routes.py` into typed handler files. Phase 4 had deleted its elif blocks inline (per task). Phase 5 deferred cleanup to a single Task 7.
**Failure:** Task 7's spec said "delete 3 dead duplicate elif blocks" — which was only the shadow-duplicate problem. The 68 dead elif blocks for the Phase 5-migrated actions were never specified in Task 7, so they were never deleted. File ended at 5,494 lines instead of ~2,630. Claimed "0 legacy chain remaining" was false.
**Root Cause:** Batched cleanup deferred to end-of-phase is easy to underspecify because the planner focuses on the anomalous cases (the 3 duplicates) rather than the systematic ones (68 migrated blocks). Per-task deletion has the right scope: the engineer who just wrote the handler knows exactly which elif to delete.
**Guard Added:** When migrating a legacy code block to a new location:
- DELETE the old block in the same commit as the new code — same task, same PR
- Never defer dead code deletion to a cleanup task at phase end
- If a cleanup task does exist, its spec must enumerate every block to delete, not just anomalies
**Test Added:** After any migration, verify: `grep -c 'elif action == "ACTION_NAME"' monolith.py` == 0 as part of the task's verification step.
**Reusable Pattern:** Strangler fig migration checklist per action:
  1. Write new handler function
  2. Register in HANDLERS dict
  3. Delete the old elif block
  4. Verify: grep for old elif == 0, syntax compiles, handler count unchanged
**Tags:** refactoring, strangler-fig, dead-code, migration, planning

---

## LESSON: Postgres Trigger Chains Require Full-Depth Tracing

**Date:** 2026-03-16
**Context:** Stage 3 remediation — 31 E2E test failures across 6 root causes. Wrote a 900-line remediation doc with exact SQL fixes for each.
**Failure:** 4 of 6 root cause diagnoses were wrong or incomplete. Fixes applied by the executing engineer were fundamentally different from what the doc prescribed.
**Root Cause:** Diagnosed from the outside in (error message → handler code → first matching table) instead of from the inside out (read the trigger function source → follow the full chain). Never ran the diagnostic SQL we wrote in the doc ourselves.

**Specific misdiagnoses:**

| REM | Doc said | Reality |
|-----|---------|---------|
| 002 | Missing UNIQUE on `pms_hours_of_rest` | Missing UNIQUE on `pms_crew_hours_warnings` (a different table — the trigger target) + RETURNING clause mismatch in `check_hor_violations` |
| 003 | "Add one INSERT policy" | 4 layers: `current_setting()::uuid` cast on empty string, SECURITY DEFINER missing, `return=representation` needs SELECT policy, partial unique constraint |
| 004 | "Trigger expects compliance_percentage" | No trigger involved. `calculate_month_summary` RPC returns dict not list → `data[0]` is `KeyError(0)` → `str(KeyError(0))` = `"0"`. A Python data structure bug. |
| 005 | "Seed pms_part_stock" | Trigger reads `pms_inventory_stock` — a third table entirely |

**Guard Added:** When diagnosing Postgres errors that occur during INSERT:
1. ALWAYS run the trigger inspection SQL and read the function source before proposing a fix
2. Follow the FULL trigger chain: table A → trigger → function → table B → trigger → function → table C
3. If the error message is unusual (like `"0"`), suspect Python-layer bugs before inventing trigger hypotheses
4. Never assume the handler's target table is where the constraint/policy is missing — triggers redirect to other tables

**Test Added:** The remediation doc's "diagnose-before-fix" pattern (Step 1 in each REM) was correct in structure but should have been executed during diagnosis, not deferred to the implementer.

**Reusable Pattern:** For any Postgres error during a mutation:
```sql
-- Step 1: Find ALL triggers on the table
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers WHERE event_object_table = 'TABLE_NAME';

-- Step 2: Read EVERY trigger function's source
SELECT p.proname, p.prosrc FROM pg_trigger t
JOIN pg_proc p ON t.tgfnoid = p.oid
WHERE t.tgrelid = 'TABLE_NAME'::regclass;

-- Step 3: For each function that INSERTs into another table, repeat Steps 1-2 on THAT table
-- Step 4: Check RLS policies on ALL tables in the chain
SELECT tablename, policyname, cmd, qual, with_check FROM pg_policies
WHERE tablename IN ('table_a', 'table_b', 'table_c');
```

**Tags:** database, triggers, rls, diagnosis, postgres, stage3

---

## LESSON: RLS Policies That Use current_setting() Fail Silently When App Doesn't SET It

**Date:** 2026-03-16
**Context:** Stage 3 REM-003 — `create_crew_template` blocked by RLS 42501 even after adding INSERT policy.
**Failure:** The API uses Supabase client (`self.db.table(...)`) which never calls `SET app.current_yacht_id`. RLS policies that reference `current_setting('app.current_yacht_id')` evaluate with NULL or empty string, which when cast to UUID throws `22P02` or silently blocks the row.
**Root Cause:** The API enforces yacht isolation via `.eq('yacht_id', yacht_id)` in application code, not via RLS `current_setting()`. But DB triggers that fire during INSERTs inherit the session context — which has no `app.current_yacht_id` set.
**Guard Added:** When writing RLS policies for tables that receive writes from triggers (not just direct API calls), use `NULLIF(current_setting('app.current_yacht_id', true), '')` to handle the empty/null case, or use SECURITY DEFINER on the trigger function to bypass RLS entirely.
**Test Added:** None (DB-level).
**Reusable Pattern:** Any time a trigger writes to a table with RLS, check whether the session context (`current_setting`) is set. If the API uses Supabase client, it almost certainly isn't.
**Tags:** rls, supabase, triggers, current_setting, security-definer, stage3

---

## LESSON: Python dict[0] Returns KeyError(0), str(KeyError(0)) = "0"

**Date:** 2026-03-16
**Context:** Stage 3 REM-004 — `create_monthly_signoff` returned `{"code":"DATABASE_ERROR","message":"0"}`.
**Failure:** Assumed the "0" was from a Postgres trigger. Actually: `calculate_month_summary` RPC returns a dict (not a list), `data[0]` on a dict raises `KeyError(0)`, and the handler's `except Exception as e: builder.set_error("DATABASE_ERROR", str(e))` converts it to the string `"0"`.
**Root Cause:** The handler at line 568 does `summary_result.data[0]` assuming data is a list. When the RPC returns a dict, Python raises `KeyError(0)` — and `str(KeyError(0))` is `"0"` because KeyError formats its argument as the repr.
**Guard Added:** When an error message is a bare number or looks like a coerced value, suspect Python exception stringification before blaming the database.
**Test Added:** None yet.
**Reusable Pattern:** `str(KeyError(0))` = `"0"`, `str(KeyError('foo'))` = `"'foo'"`. Always check whether "unusual" error messages are Python exceptions being str()'d.
**Tags:** python, debugging, error-messages, keyerror, stage3

---

## LESSON: Remediation Docs Must Be Verified Against Trigger Source, Not Just Error Codes

**Date:** 2026-03-16
**Context:** Wrote a 900-line remediation doc that went through 4 rounds of engineer review. Still had 4/6 wrong root causes.
**Failure:** The doc's structure was excellent (symptom → evidence → remedy → verify), but the content was based on inference from error codes rather than reading the actual database objects.
**Root Cause:** We had access to the test logs and handler source but not a live DB connection to inspect triggers. We wrote plausible hypotheses and labeled some as such (REM-004), but stated others as facts (REM-002: "trigger uses ON CONFLICT on these columns") without evidence.
**Guard Added:** A remediation doc should distinguish:
- **CONFIRMED** — we read the source and verified
- **INFERRED** — plausible from the error code but trigger source not inspected
- **HYPOTHESIS** — our best guess, needs verification

Every fix that touches a trigger must be labeled INFERRED or HYPOTHESIS unless the trigger function source is included in the evidence section.
**Test Added:** None.
**Reusable Pattern:** Error code → handler code → table name gives you the SYMPTOM. Only reading `pg_proc.prosrc` gives you the CAUSE.
**Tags:** documentation, diagnosis, remediation, process, stage3
