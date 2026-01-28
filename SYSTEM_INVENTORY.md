# SYSTEM INVENTORY

**Repository:** BACK_BUTTON_CLOUD_PMS
**Purpose:** Yacht Planned Maintenance System (PMS) with Natural Language Interface
**Date:** 2026-01-22
**Status:** 95% HTTP health, 1.5% proven database mutations

**This is the truth, not aspiration.**

---

## WHAT THIS SYSTEM IS

A FastAPI backend that accepts natural language queries from yacht crew, extracts entities using GPT-4o-mini, maps them to maintenance actions, and executes database mutations via 81 Python handlers.

**Example flow:**
```
Crew: "The generator is overheating"
  → GPT extracts: entity="generator", problem="overheating"
  → System offers actions: [diagnose_fault, view_history, view_manual]
  → Crew clicks [diagnose_fault]
  → Handler queries DB, returns diagnostic steps
```

**The product is NOT:**
- A frontend application (frontend exists but is minimal)
- A document management system (documents table exists but underused)
- A fully verified system (only 1/64 actions have proven DB mutations)

---

## ARCHITECTURE

### Two-Database Model

**MASTER DB** (Supabase project 1)
- Purpose: Fleet-wide user accounts, yacht registry, cross-yacht audit
- Tables: `fleet_registry`, `user_accounts`, `db_registry`, `security_events`
- RPC: `get_my_bootstrap()`, `ensure_user_account()`

**TENANT DB** (Supabase project 2 - per yacht)
- Purpose: Single-yacht PMS data (equipment, faults, work orders, parts)
- Tables: See "Core Tables" section below
- RLS: All tables enforce `yacht_id` isolation

**Critical invariant:** Yacht = tenant boundary. One yacht = one tenant DB. Users can belong to multiple yachts (via MASTER DB), but each yacht's PMS data is isolated in TENANT DB.

---

## DATABASE MIGRATIONS

### Master Database (7 migrations)

Executed in this order:

| # | File | Purpose | Tables Created |
|---|------|---------|----------------|
| 000 | `create_fleet_registry.sql` | Yacht registry table | `fleet_registry` |
| 001 | `create_user_accounts.sql` | Cross-yacht user accounts | `user_accounts` |
| 002 | `create_db_registry.sql` | Tenant DB connection strings | `db_registry` |
| 003 | `create_security_events.sql` | Audit log for auth events | `security_events` |
| 004 | `create_get_my_bootstrap_rpc.sql` | User bootstrap RPC | RPC: `get_my_bootstrap()` |
| 005 | `create_ensure_user_account_rpc.sql` | User upsert RPC | RPC: `ensure_user_account()` |
| 006 | `add_tenant_key_alias.sql` | Tenant key alias column | Alters `db_registry` |
| 007 | `update_get_my_bootstrap_with_alias.sql` | Update RPC for alias | Alters RPC |

**Current state:** All 7 applied to production MASTER DB.

**Known issue:** Migration 002 stores Supabase connection strings in `db_registry` table. These include service role keys. This table MUST have strict RLS (service role only).

---

### Tenant Database (12+ migrations)

**CRITICAL NAMING INCONSISTENCY:**
- Migration files create tables as `public.equipment`, `public.faults`, etc.
- Handlers reference them as `pms_equipment`, `pms_faults`, etc.
- **This implies tables were renamed post-migration OR handlers are wrong.**
- **Status unknown:** Need to verify actual table names in production DB.

Executed in this order:

| # | File | Purpose | Tables/Changes |
|---|------|---------|----------------|
| 00 | `enable_extensions.sql` | Enable pgcrypto for UUID | Extensions |
| 01 | `core_tables_v2_secure.sql` | Auth tables | `yachts`, `user_profiles`, `user_roles`, `api_tokens`, `yacht_signatures` |
| 02 | `p0_actions_tables_REVISED.sql` | PMS domain tables | `equipment`, `faults`, `parts`, `work_orders`, `work_order_notes`, `work_order_parts`, `part_usage`, `handover`, `audit_log` |
| 03 | `add_accountability_columns.sql` | Add created_by/updated_by | Alters multiple tables |
| 04 | `trust_accountability_tables.sql` | Unknown (file not read) | Unknown |
| 05 | `rename_auth_tables.sql` | Unknown (file not read) | Unknown |
| 06 | `fix_jwt_hook_function.sql` | JWT validation function | Function |
| 07 | `fix_rls_policies_jwt_fallback.sql` | RLS policy fixes | Policies |
| 08 | `add_storage_rls_policy.sql` | Storage bucket RLS | Policy |
| 09 | `fix_search_chunks_rls_table_name.sql` | Search table RLS fix | Policy |
| 10 | `add_row_security_off_to_rpc.sql` | Disable RLS for RPC functions | Functions |
| 11 | `create_get_user_auth_info_rpc.sql` | User auth info RPC | RPC |

**Current state:** Unknown which migrations are applied to production TENANT DB. No migration tracking table confirmed.

**Deprecated files:**
- `01_core_tables.sql` (superseded by `01_core_tables_v2_secure.sql`)
- `02_p0_actions_tables.sql` (superseded by `02_p0_actions_tables_REVISED.sql`)

**Known issues:**
- Multiple migrations have "fix" in the name, implying iterative fixes
- Auth table naming changed mid-development (migration 05)
- RLS policies required multiple fixes (migrations 07, 09)
- JWT validation function required fix (migration 06)

---

## CORE TABLES (Grouped by Domain)

### Authentication & User Management

| Table | Purpose | RLS | Key Columns |
|-------|---------|-----|-------------|
| `yachts` | Vessel registry | No (shared) | `id`, `name`, `signature`, `status` |
| `user_profiles` | User basic info | Yes (yacht_id) | `id`, `yacht_id`, `email`, `name` |
| `user_roles` | Role assignments (RBAC) | Yes (yacht_id) | `user_id`, `yacht_id`, `role`, `is_active` |
| `api_tokens` | Device/API tokens | Yes (yacht_id) | `token_hash`, `user_id`, `scopes`, `is_revoked` |
| `yacht_signatures` | Yacht install keys | No (service only) | `yacht_id`, `signature`, `created_at` |

**Roles supported:** `chief_engineer`, `eto`, `captain`, `manager`, `vendor`, `crew`, `deck`, `interior`

**Token types:** `api_key`, `device`, `agent`

---

### PMS Domain Tables

**CRITICAL:** These tables have a naming inconsistency. Migration creates `public.equipment` but handlers reference `pms_equipment`. Status unverified.

| Table (Migration) | Table (Handlers) | Purpose | RLS | Key Columns |
|-------------------|------------------|---------|-----|-------------|
| `equipment` | `pms_equipment` | Equipment registry | Yes | `id`, `yacht_id`, `equipment_name`, `system` |
| `faults` | `pms_faults` | Fault reports | Yes | `id`, `yacht_id`, `equipment_id`, `description`, `status` |
| `parts` | `pms_parts` | Spare parts inventory | Yes | `id`, `yacht_id`, `part_name`, `quantity_on_hand`, `quantity_minimum` |
| `work_orders` | `pms_work_orders` | Maintenance work orders | Yes | `id`, `yacht_id`, `title`, `assigned_to`, `status`, `priority` |
| `work_order_notes` | `pms_work_order_notes` | WO notes/comments | Yes | `id`, `work_order_id`, `note_text`, `created_by` |
| `work_order_parts` | `pms_work_order_parts` | Parts used in WO | Yes | `id`, `work_order_id`, `part_id`, `quantity` |
| `part_usage` | `part_usage` | Part usage log | Yes | `id`, `part_id`, `quantity_used`, `used_by` |
| `handover` | `pms_handover` | Watch handover items | Yes | `id`, `yacht_id`, `watch`, `content` |
| `audit_log` | `pms_audit_log` | Action audit trail | Yes | `id`, `yacht_id`, `action`, `entity_id`, `user_id` |

**Known column name issues:**
- `pms_parts.quantity_on_hand` sometimes coded as `current_quantity_onboard`
- `pms_parts.quantity_minimum` sometimes coded as `min_quantity` or `reorder_point`
- `documents.storage_path` sometimes coded as `file_path` or `url`
- `pms_faults.fault_number` sometimes coded as `fault_code`

---

### Undocumented Tables (Referenced in Handlers)

These tables are referenced by handlers but not found in migration files:

| Table | References | Status |
|-------|-----------|--------|
| `pms_checklists` | Handler: `view_checklist` | Unknown if exists |
| `pms_checklist_items` | Handler: `complete_checklist_item` | Unknown if exists |
| `pms_shopping_list_items` | Handler: `add_to_shopping_list` | Unknown if exists |
| `purchase_request_items` | Handler: `create_purchase_request` | Unknown if exists |
| `hours_of_rest` | Handler: `view_hours_of_rest` | Unknown if exists |
| `compliance_status` | Handler: `export_compliance_report` | Unknown if exists |
| `documents` | Handler: `view_document`, `search_manuals` | Unknown if exists |

**Impact:** Handlers may fail at runtime if these tables don't exist. Test results show 61/64 actions return 200, suggesting these tables exist OR handlers gracefully handle missing tables.

---

## SECURITY PRIMITIVES

### Row Level Security (RLS)

**Design:** All PMS tables enforce `yacht_id` isolation via RLS policies.

**Example policy:**
```sql
CREATE POLICY "Users can only see their yacht's equipment"
ON equipment FOR SELECT
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**JWT flow:**
1. Client sends JWT in `Authorization: Bearer <token>` header
2. Backend validates JWT, extracts `yacht_id` claim
3. Backend sets PostgreSQL session variable `app.current_yacht_id`
4. RLS policies use this variable to filter rows

**Known issues:**
- RLS policies required multiple fixes (migrations 07, 09)
- Some RPC functions have RLS disabled (migration 10) - **security risk**
- No RLS test coverage confirmed

**Threat model:** RLS prevents cross-yacht data leaks. If JWT validation fails or session variable not set, queries return no rows (safe failure mode).

---

### Token Lifecycle

**Device tokens:**
1. Device generates token, stores hash in `api_tokens` table
2. Token has scopes (e.g., `['read:documents', 'write:faults']`)
3. Token can be revoked (`is_revoked = true`)
4. Token has expiration (`expires_at`)

**Token validation:**
- Handler: `jwt_validator.py` validates JWT tokens
- Handler: `role_validator.py` validates user roles
- Handler: `yacht_validator.py` validates yacht access

**Known issue:** No token rotation mechanism. Tokens are long-lived unless manually revoked.

---

### Pairing Flow

**Purpose:** Onboard new devices to a yacht.

**Not implemented.** No migration files, no handlers, no tests for pairing flow.

**Referenced in:** Old documentation only (_archive/).

---

## BACKEND IMPLEMENTATION

### Action Execution Pipeline

**File:** `apps/api/routes/p0_actions_routes.py` (4,160 lines)

**Structure:**
```python
@router.post("/v1/actions/execute")
async def execute_action(request: ExecuteActionRequest):
    action = request.action

    if action == "diagnose_fault":
        # Handler 1 (lines 120-156)
        fault_id = payload.get("fault_id")
        fault = db.table("pms_faults").select("*").eq("id", fault_id).single()
        # ... diagnostic logic ...
        return {"status": "success", "diagnostic_steps": [...]}

    elif action == "create_work_order":
        # Handler 2 (lines 1325-1356)
        wo_data = {"title": payload["title"], "yacht_id": yacht_id, ...}
        result = db.table("pms_work_orders").insert(wo_data).execute()
        return {"status": "success", "work_order_id": result.data[0]["id"]}

    # ... 79 more handlers ...
```

**Total handlers:** 81 (covers 64 documented actions, some actions have multiple handler variants)

**Handler pattern:**
1. Extract payload fields
2. Validate required fields (raises 400 if missing)
3. Query/mutate database via Supabase client
4. Return structured response

**Known issues:**
- No consistent error handling (some handlers return `{"status": "error"}`, others raise exceptions)
- No consistent response format (some return `{"status": "success", "message": "..."}`, others return entity objects)
- No transaction boundaries (multi-table mutations can partially fail)
- Audit logging inconsistent (4/64 actions have audit logs, 60/64 don't)

---

### Natural Language Pipeline

**File:** `apps/api/services/pipeline_service.py` (~800 lines)

**Flow:**
```
1. User query: "The generator is overheating"
2. GPT-4o-mini extraction: {equipment: "generator", problem: "overheating"}
3. Table capabilities lookup: equipment table → actions: [diagnose_fault, view_history, view_manual]
4. Return action buttons to UI
```

**Known issues:**
- Entity extraction sometimes fails (GPT returns empty or wrong entities)
- No confidence scoring (all extracted entities treated as equally valid)
- No feedback loop (if user rejects suggested action, no learning occurs)

---

### Test Infrastructure

**E2E tests:** Playwright (TypeScript)

**Key files:**
- `tests/e2e/diagnostic_baseline.spec.ts` - Direct action execution (61/64 pass)
- `tests/e2e/nl_to_action_mapping.spec.ts` - NL→Action flow (64/64 pass)
- `tests/helpers/test-data-discovery.ts` - Auto-discovers entity IDs from test DB

**Test pattern:**
```typescript
test('diagnose_fault action', async ({ request }) => {
  const response = await request.post('/v1/actions/execute', {
    data: {
      action: 'diagnose_fault',
      payload: { fault_id: FAULT_ID },
      yacht_id: TEST_YACHT_ID,
      user_id: TEST_USER_ID
    }
  });
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe('success');
});
```

**What tests verify:**
- ✅ Handler returns HTTP 200
- ✅ Response has expected structure
- ❌ Database mutation occurred
- ❌ Audit log entry created
- ❌ Data integrity maintained

**Test coverage:**
- 64/64 actions have HTTP tests
- 1/64 actions have database mutation tests
- 0/64 actions have audit log tests
- 0/64 actions have RLS tests

---

## IMPLEMENTATION GUIDES (Backend)

### Ingestion Pipeline

**Purpose:** Extract entities from maintenance manuals, equipment docs, crew messages.

**Status:** Conceptually designed, not implemented.

**Referenced in:** `_archive/` documentation only.

---

### Email Integration

**Purpose:** Monitor inbox for maintenance requests, auto-create work orders.

**Status:** Partially implemented. OAuth flow exists, email watcher not confirmed working.

**Files:**
- `apps/api/services/email_watcher.py` (exists, status unknown)
- `apps/api/routes/oauth_routes.py` (Outlook OAuth flow)

**Known issue:** Email watcher runbook exists (`apps/api/docs/EMAIL_WATCHER_RUNBOOK.md`) but no confirmation it runs in production.

---

### Search Pipeline

**Purpose:** Full-text search across manuals, equipment docs, fault history.

**Status:** Partially implemented. GraphRAG query exists but search chunks table has RLS issues.

**Files:**
- `apps/api/services/graphrag_query.py` (GraphRAG query)
- Migration 09: `fix_search_chunks_rls_table_name.sql` (RLS fix)

**Known issue:** Search chunks table name mismatch required migration fix.

---

## WHAT EXISTS (Summary)

### Production-Ready
- ❌ Nothing is production-ready.

### Pilot-Ready (Needs ops + UI glue)
- ✅ 61/64 action handlers return HTTP 200
- ✅ NL→Action pipeline works (64/64 NL tests pass)
- ✅ Database schema exists
- ✅ RLS policies exist
- ⚠️ Auth flow works (but tokens never rotate)
- ⚠️ Audit logging exists (but only 4/64 actions use it)

### Conceptually Correct but Incomplete
- ⚠️ Database mutations (61 handlers respond correctly, but only 1 proven to write DB)
- ⚠️ Error handling (inconsistent formats, no transaction boundaries)
- ⚠️ Email integration (OAuth works, watcher status unknown)
- ⚠️ Search pipeline (exists but RLS required fixes)

### Explicitly Deferred
- ❌ Pairing flow (no implementation)
- ❌ Device onboarding (no implementation)
- ❌ Document ingestion pipeline (no implementation)
- ❌ Load testing (no benchmarks)
- ❌ Penetration testing (security patches applied but not tested)

---

## KNOWN RISKS

### HIGH Risk
1. **Table naming inconsistency:** Migrations create `public.equipment` but handlers reference `pms_equipment`. If actual tables have wrong names, ALL handlers fail at runtime.
2. **No database mutation proof:** Only 1/64 actions have been proven to write to database. The other 60 might not work.
3. **No audit logging:** 60/64 actions don't create audit log entries. Compliance risk (ISO 9001, SOLAS).
4. **RLS disabled for RPC functions:** Migration 10 disables RLS for some functions. Potential cross-yacht data leak.

### MEDIUM Risk
1. **No token rotation:** API tokens are long-lived. If compromised, only manual revocation works.
2. **No transaction boundaries:** Multi-table mutations can partially fail, leaving DB in inconsistent state.
3. **Undocumented tables:** 7+ tables referenced by handlers but not found in migrations. If they don't exist, handlers fail.
4. **Column name inconsistencies:** Handlers use different column names than schema. Risk of runtime errors.

### LOW Risk
1. **No confidence scoring:** NL extraction treats all entities equally. UX issue, not correctness issue.
2. **Inconsistent error formats:** Frontend can't reliably parse errors. UX issue.

---

## TECHNICAL DEBT

### Database
- Migration tracking: No `schema_migrations` table confirmed
- Multiple "fix" migrations imply iterative development, not planned design
- Deprecated migration files not deleted

### Code
- Action handlers in single 4,160-line file (should be modular)
- No shared error handling (each handler implements own error logic)
- No shared response format (inconsistent JSON structures)
- No transaction boundaries (database integrity risk)

### Tests
- HTTP-only tests (no database mutation verification)
- No RLS tests (security risk)
- No audit log tests (compliance risk)
- No load tests (performance unknown)

### Documentation
- 79 markdown files at root (excessive)
- Agent/Watchdog/Verification docs are meta-system docs, not product docs (confusing)
- `_archive/` contains 200+ old docs (should be in Git history, not repo)

---

## AREAS THAT LOOK DONE BUT ARE NOT

### Action Handlers
**Looks done:** 81 handlers implemented, 61/64 return HTTP 200.
**Actually:** Only 1/64 proven to write to database. HTTP 200 ≠ database mutation.

### Audit Logging
**Looks done:** `audit_log` table exists, some handlers call it.
**Actually:** Only 4/64 actions create audit log entries. 60/64 don't log.

### Security (RLS)
**Looks done:** RLS policies exist on all tables, migrations applied.
**Actually:** RLS disabled for some RPC functions (migration 10). No RLS tests. Unknown if yacht isolation actually works.

### Documentation
**Looks done:** 79 markdown files covering architecture, testing, deployment.
**Actually:** Most docs are stale, aspirational, or meta-docs about verification systems. Real product docs are minimal.

---

## THE GAP BETWEEN CLAIMED AND VERIFIED

**Claimed:** 64 actions working, 95% system health.
**Verified:** 61 actions return HTTP 200. 1 action proven with database mutation.

**HTTP 200 ≠ Working.**

The handlers **respond** correctly. We haven't **proven** they **write** correctly (except 1).

---

## FILES THAT MUST NOT BE CHANGED CASUALLY

### Critical Database Files
- `database/master_migrations/*` - Master DB schema (fleet registry, user accounts)
- `database/migrations/01_core_tables_v2_secure.sql` - Auth tables (yachts, users, roles, tokens)
- `database/migrations/02_p0_actions_tables_REVISED.sql` - PMS domain tables (equipment, faults, work orders, parts)

**Why:** These define the entire data model. Changing them breaks everything. If changes needed, create new migration (don't edit existing).

### Critical Backend Files
- `apps/api/routes/p0_actions_routes.py` - All 81 action handlers
- `apps/api/services/pipeline_service.py` - NL→Action mapping

**Why:** These are the product. Refactoring without full test coverage = production outage.

### Critical Test Files
- `tests/e2e/diagnostic_baseline.spec.ts` - Health check (proves 61/64 working)
- `tests/helpers/test-data-discovery.ts` - Finds entity IDs (required for tests to run)

**Why:** These are the only proof the system works. Breaking these = no verification.

---

## VERIFICATION SYSTEM (Meta-System)

**What it is:** Documentation and prompts for a 4-agent AI system to verify all 64 actions.

**Status:** Designed but not executed. Agent 3 completed (pattern analysis). Agent 4 (bulk fixes) not started.

**Files:** All `AGENT_*.md`, `WATCHDOG_*.md`, `VERIFICATION_*.md` files at root.

**Purpose:** Automate verification that all 64 actions actually write to database and create audit logs.

**This is NOT part of the product.** It's verification infrastructure.

---

## WHAT ASSUMPTIONS ARE SAFE TO RELY ON

### Database
- ✅ Yacht = tenant boundary (enforced by RLS)
- ✅ All PMS tables have `yacht_id` column
- ✅ All PMS tables have RLS policies (but not tested)
- ✅ Users can belong to multiple yachts (via MASTER DB)

### Backend
- ✅ Action handlers exist for all 64 documented actions
- ✅ Handlers return HTTP 200 for valid payloads (61/64 confirmed)
- ⚠️ Handlers write to database (only 1/64 confirmed)
- ⚠️ Handlers create audit logs (only 4/64 confirmed)

### Tests
- ✅ E2E test infrastructure works (Playwright)
- ✅ Test data discovery works (auto-finds entity IDs)
- ❌ Tests verify database mutations (only 1/64)

---

**This inventory is complete as of 2026-01-22.**

**Next:** See ARCHITECTURE.md, SECURITY_INVARIANTS.md, MATURITY_ASSESSMENT.md, HANDOVER.md.
