# CelesteOS Cloud PMS

**Yacht Planned Maintenance System**

Status: 95% HTTP health, 1.5% database mutations proven
Date: 2026-01-22

---

## 🚨 START HERE (New Engineers)

**Read these 4 files in order:**

1. **`SYSTEM_INVENTORY.md`** - What exists, why it exists, what's correct, what's unfinished
2. **`SECURITY_INVARIANTS.md`** - What must never be broken (non-negotiable rules)
3. **`MATURITY_ASSESSMENT.md`** - Brutally honest status (no optimism, no hand-waving)
4. **`HANDOVER.md`** - If you had 1 week, what would you do first?

**Time to read:** 90 minutes total

---

## WHAT THIS SYSTEM IS

A FastAPI backend that accepts natural language queries from yacht crew, extracts entities using GPT-4o-mini, maps them to maintenance actions, and executes database mutations via 81 Python handlers.

**Example:**
```
Crew: "The generator is overheating"
  → GPT extracts: entity="generator", problem="overheating"
  → System offers: [diagnose_fault, view_history, view_manual]
  → Crew clicks [diagnose_fault]
  → Handler queries DB, returns diagnostic steps
```

---

## WHAT THIS SYSTEM IS NOT

- ❌ A fully verified system (only 1/64 actions have proven database mutations)
- ❌ Production-ready (needs 40 hours verification work before pilot)
- ❌ A frontend application (frontend exists but minimal)

---

## CURRENT STATUS

```
┌─────────────────────────────────────────────────┐
│  Handlers Implemented     81/81    (100%)       │
│  HTTP 200 Success         61/64    (95%)        │
│  Database Mutations       1/64     (1.5%)       │
│  Audit Logging            4/64     (6%)         │
│  RLS Tested               0/64     (0%)         │
└─────────────────────────────────────────────────┘
```

**The Gap:** Handlers respond correctly (HTTP 200), but only 1 action has been proven to actually write to the database.

**See:** `MATURITY_ASSESSMENT.md` for detailed breakdown.

---

## CRITICAL ISSUES

### HIGH Priority (Must Fix Before Pilot)

1. **Verify database mutations (60/64 actions unverified)**
   - Effort: 30 hours
   - Impact: Pilot broken without this

2. **Add audit logging (60/64 actions missing audit logs)**
   - Effort: 8.5 hours
   - Impact: Compliance violations (ISO 9001, SOLAS)

3. **Test RLS (0/64 actions have yacht isolation tests)**
   - Effort: 1 hour (minimum for 5 critical actions)
   - Impact: CRITICAL security risk (cross-yacht data leaks possible)

4. **Verify table naming consistency**
   - Effort: 30 minutes
   - Impact: If tables have wrong names, ALL handlers fail

**Total effort before pilot:** 40 hours

**See:** `MATURITY_ASSESSMENT.md` for complete risk analysis.

---

## SECURITY INVARIANTS (Non-Negotiable)

1. **Yacht Isolation Enforced by RLS** - Every table MUST have RLS policies filtering by `yacht_id`
2. **No Plaintext Secrets** - API tokens, passwords MUST be hashed, never stored/returned in plaintext
3. **No Mutation Without Auditability** - Every INSERT/UPDATE/DELETE MUST create audit log entry
4. **JWT Validation MUST Succeed Before DB Access** - No queries without valid JWT
5. **RLS Policies MUST Filter by Session Variable** - Use `current_setting('app.current_yacht_id')`
6. **Service Role Key MUST NEVER Be Exposed to Client** - Backend only, never frontend
7. **No SQL Injection** - Parameterized queries only, never string concatenation
8. **Tokens MUST Be Revocable** - Check `is_revoked` flag before granting access

**Breaking these = security breach.**

**See:** `SECURITY_INVARIANTS.md` for enforcement details and examples.

---

## ARCHITECTURE

### Two-Database Model

**MASTER DB** (fleet registry, user accounts)
- `fleet_registry`, `user_accounts`, `db_registry`, `security_events`

**TENANT DB** (per-yacht PMS data)
- `pms_equipment`, `pms_faults`, `pms_work_orders`, `pms_parts`, etc.
- **Critical:** RLS enforces `yacht_id` isolation

**See:** `SYSTEM_INVENTORY.md` for complete table list and migration order.

---

## KEY FILES

| File | Purpose | Lines |
|------|---------|-------|
| `apps/api/routes/p0_actions_routes.py` | All 81 action handlers | 4,160 |
| `tests/e2e/diagnostic_baseline.spec.ts` | Health check (61/64 pass) | 500 |
| `tests/helpers/test-data-discovery.ts` | Auto-discovers test entity IDs | 360 |
| `database/migrations/01_core_tables_v2_secure.sql` | Auth tables (yachts, users, roles, tokens) | ~500 |
| `database/migrations/02_p0_actions_tables_REVISED.sql` | PMS domain tables | ~800 |

---

## ESSENTIAL COMMANDS

```bash
# Health check (61/64 pass expected)
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium

# NL coverage (64/64 pass expected)
npx playwright test tests/e2e/nl_to_action_mapping.spec.ts --project=e2e-chromium

# Single action test
npx playwright test -g "create_work_order"

# Start backend
cd apps/api && uvicorn main:app --reload
```

---

## ENVIRONMENT SETUP

```bash
# Required environment variables
MASTER_SUPABASE_URL=https://xxx.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJ...
TENANT_SUPABASE_URL=https://yyy.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJ...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

**See:** `.env.example` for all required variables.

---

## TECH STACK

- **Backend:** Python FastAPI
- **Frontend:** Next.js / React
- **Database:** Supabase (PostgreSQL + RLS)
- **AI:** GPT-4o-mini for entity extraction
- **Tests:** Playwright

---

## FILE ORGANIZATION

```
BACK_BUTTON_CLOUD_PMS/
├── README.md                      ← YOU ARE HERE
├── SYSTEM_INVENTORY.md            ← Read first: Complete inventory
├── SECURITY_INVARIANTS.md         ← Read second: Non-negotiable rules
├── MATURITY_ASSESSMENT.md         ← Read third: Brutally honest status
├── HANDOVER.md                    ← Read fourth: Week 1 action plan
│
├── apps/                          ← Source code
│   ├── api/                       ← Python FastAPI backend
│   └── web/                       ← Next.js frontend
│
├── database/                      ← Database schemas and migrations
│   ├── master_migrations/         ← Master DB (fleet registry)
│   └── migrations/                ← Tenant DB (PMS data)
│
├── tests/                         ← Test suite
│   ├── e2e/                       ← Playwright E2E tests
│   ├── helpers/                   ← Test helpers
│   └── fixtures/                  ← Test data and action definitions
│
├── scripts/                       ← Utility scripts
│
├── _HANDOVER/                     ← Old handover docs (superseded)
├── _VERIFICATION/                 ← Verification results
└── _archive/                      ← Historical docs
```

---

## WHAT TO DO FIRST

### Day 1: Verify the Foundation (8 hours)

1. **Check table names match** (30 min)
   - Query production DB: `\dt`
   - Compare to handler references: `grep 'table("' apps/api/routes/p0_actions_routes.py`
   - If mismatch: ALL handlers broken, fix immediately

2. **Run health check** (5 min)
   - `npx playwright test tests/e2e/diagnostic_baseline.spec.ts`
   - Expected: 61/64 pass
   - If <50 pass: Something broke, investigate

3. **Test ONE mutation end-to-end** (1 hour)
   - Run action via API
   - Query DB to verify row created
   - Query audit log to verify entry created
   - If no DB row: Handler returned 200 but didn't write (CRITICAL BUG)
   - If no audit log: Compliance violation

4. **Document findings** (4 hours)

**See:** `HANDOVER.md` for complete Day 1-5 plan.

---

## KNOWN RISKS

### CRITICAL

- **Table naming inconsistency:** Migrations create `public.equipment` but handlers reference `pms_equipment`. If mismatch, ALL handlers fail.
- **Database mutations unverified:** Only 1/64 proven to write to DB. Others might not work.
- **No audit logging:** 60/64 actions don't create audit logs. Compliance risk.
- **RLS not tested:** Unknown if yacht isolation actually works. Security risk.

### HIGH

- **No token rotation:** Compromised tokens can't be rotated, only revoked.
- **No transaction boundaries:** Multi-table mutations can partially fail.
- **Undocumented tables:** 7 tables referenced by handlers but not in migrations.

**See:** `MATURITY_ASSESSMENT.md` for complete risk analysis.

---

## WHAT MUST NOT BE CHANGED CASUALLY

1. **Database migrations** - Create new migrations, don't edit existing
2. **Action handlers file** (`p0_actions_routes.py`) - 4,160 lines, no test coverage
3. **RLS policies** - Test on local DB first, breaking these = cross-yacht data leaks
4. **Test helper** (`test-data-discovery.ts`) - All tests depend on this
5. **Environment variables** - Wrong credentials = all DB queries fail

**See:** `HANDOVER.md` for detailed guidance on what not to refactor.

---

## SAFE ASSUMPTIONS

✅ **Yacht = tenant boundary** (RLS enforces `yacht_id` isolation)
✅ **Action handlers exist for all 64 documented actions**
✅ **E2E test infrastructure works** (Playwright tests run reliably)
✅ **Database schema is stable** (migrations applied)

❌ **"95% health" means actions work** (HTTP 200 ≠ database mutation)
❌ **Handlers write to database** (only 1/64 proven)
❌ **Audit logging is complete** (only 4/64 have audit logs)
❌ **RLS has been tested** (0/64 actions tested)
❌ **Documentation is current** (most docs stale or aspirational)

**See:** `HANDOVER.md` for complete assumptions list.

---

## LINKS

- **Git:** https://github.com/shortalex12333/Cloud_PMS.git
- **Branch:** main

---

## VERIFICATION SYSTEM (Meta-System)

**What it is:** Documentation and prompts for a 4-agent AI system to verify all 64 actions.

**Status:** Designed but not executed. Agent 3 completed (pattern analysis). Agent 4 (bulk fixes) not started.

**Files:** All `AGENT_*.md`, `WATCHDOG_*.md`, `VERIFICATION_*.md` files.

**This is NOT part of the product.** It's verification infrastructure.

**See:** `MULTI_AGENT_VERIFICATION_PLAN.md` for details.

---

## CONTACTS

- **Repository:** This is a local checkpoint before handover
- **Last Updated:** 2026-01-22
- **Status:** STOP / CONSOLIDATE / HANDOVER mode

---

**IMPORTANT:**

This README is the truth as of 2026-01-22. Trust the code + tests over docs.

**Read the 4 consolidation documents first:** SYSTEM_INVENTORY.md, SECURITY_INVARIANTS.md, MATURITY_ASSESSMENT.md, HANDOVER.md.

**They contain brutal honesty about what works and what doesn't.**
