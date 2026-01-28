# REPOSITORY ORIENTATION: STEP 1 - STRUCTURAL MAP

**Date:** 2026-01-22
**Purpose:** Map where everything lives, no assumptions, no design
**Status:** Current state documentation

---

## REPOSITORY STRUCTURE

```
BACK_BUTTON_CLOUD_PMS/
├── README.md                          ← Entry point (updated 2026-01-22)
├── [56 .md files at root]            ← Documentation (consolidation + meta-docs)
├── apps/                              ← Source code (backend + frontend)
├── database/                          ← Database schemas and migrations
├── tests/                             ← Test suite (contract + e2e + fixtures)
├── scripts/                           ← Utility scripts
├── _HANDOVER/                         ← Old handover docs (superseded)
├── _VERIFICATION/                     ← Verification results (meta-system)
└── _archive/                          ← Historical docs
```

---

## 1. WHERE MICRO-ACTIONS ARE DEFINED

### Single Source of Truth

**`tests/fixtures/microaction_registry.ts`** (1,451 lines)
- **76 micro-actions defined** (not 64 as previous docs claimed)
- Machine-readable test fixture
- Contains complete specification for each action:
  - `id`: Unique action identifier
  - `label`: Human-readable name
  - `cluster`: Which of 7 clusters it belongs to
  - `cardTypes`: What entity types trigger it
  - `sideEffectType`: read_only | mutation_light | mutation_heavy
  - `triggers`: Role/status/condition-based gating
  - `endpoint`: API endpoint path
  - `requiredFields`: Validation schema
  - `expectedChanges`: Database mutations expected
  - `edgeCases`: Known failure scenarios
  - `description`: What it does

### Cluster Distribution (from registry statistics)

- **fix_something**: Fault diagnosis, resolution, escalation
- **do_maintenance**: Work orders, checklists, scheduling
- **manage_equipment**: Equipment status, history, documentation
- **control_inventory**: Parts tracking, stock levels, usage logs
- **communicate_status**: Handovers, summaries, notifications
- **comply_audit**: Hours of rest, compliance tracking, survey tags
- **procure_suppliers**: Purchase requests, approvals, delivery tracking
- **additional**: Miscellaneous actions

### Related Schema Files

**`tests/fixtures/test_data.json`**
- Test entity IDs (fault_id, work_order_id, equipment_id, part_id)
- Used by test helper for auto-discovery

**`tests/fixtures/test_users.ts`**
- Test user definitions with roles
- JWT token generation

---

## 2. WHERE MICRO-ACTIONS ARE IMPLEMENTED

### Main Handler File

**`apps/api/routes/p0_actions_routes.py`** (4,186 lines)
- **81 action handlers implemented** (grep count: 81 `elif action ==` statements)
- FastAPI router with 3 endpoint types:
  - `/v1/actions/{action_name}/prefill` - Pre-fill form data
  - `/v1/actions/{action_name}/preview` - Preview changes before commit
  - `/v1/actions/execute` - Execute action
- All routes require JWT authentication
- All routes validate yacht isolation

**Handler structure:**
```python
if action == "create_work_order_from_fault":
    # Handler implementation
elif action == "add_note_to_work_order":
    # Handler implementation
# ... 79 more actions
```

### Handler Modules (17 files)

**`apps/api/handlers/`**
- `work_order_mutation_handlers.py` - Work order mutations
- `fault_handlers.py` - Fault lifecycle management
- `inventory_handlers.py` - Parts and stock management
- `handover_handlers.py` - Handover notes and summaries
- `manual_handlers.py` - Equipment manual access
- `equipment_handlers.py` - Equipment status and history
- `list_handlers.py` - List/search queries
- `purchasing_mutation_handlers.py` - Purchase request mutations
- `work_order_handlers.py` - Work order queries
- `p1_compliance_handlers.py` - Compliance (HOR, surveys)
- `p1_purchasing_handlers.py` - Purchase request queries
- `p2_mutation_light_handlers.py` - Light mutations (notes, tags)
- `p3_read_only_handlers.py` - Read-only queries
- `situation_handlers.py` - Context-aware queries
- `context_navigation_handlers.py` - Navigation between entities
- `schema_mapping.py` - Table/field name mappings
- `__init__.py` - Module initialization

**Handler instantiation pattern (from p0_actions_routes.py:94-106):**
```python
supabase = get_supabase_client()
wo_handlers = WorkOrderMutationHandlers(supabase)
inventory_handlers = InventoryHandlers(supabase)
handover_handlers = HandoverHandlers(supabase)
manual_handlers = ManualHandlers(supabase)
```

### Action Router Infrastructure

**`apps/api/action_router/`**
- `router.py` - Main router logic
- `registry.py` - Action registry lookup
- `logger.py` - Logging infrastructure

**Validators:**
- `validators/jwt_validator.py` - JWT authentication validation
- `validators/role_validator.py` - Role-based access control
- `validators/yacht_validator.py` - Yacht isolation validation
- `validators/schema_validator.py` - Payload schema validation
- `validators/field_validator.py` - Field-level validation
- `validators/validation_result.py` - Validation result wrapper

**Dispatchers:**
- `dispatchers/internal_dispatcher.py` - Internal action dispatch
- `dispatchers/n8n_dispatcher.py` - External workflow dispatch (n8n)

---

## 3. WHERE GUARD RAILS LIVE

### Guard Rail Implementation (In Code)

**Guard rails are NOT labeled G0-G3 in code.** They are implemented as:

**Role-Based Access (conceptual G1):**
- Enforced in: `action_router/validators/role_validator.py`
- Defined in: `microaction_registry.ts` → `triggers.roles`
- Example: `roles: ['chief_engineer', 'captain']` or `roles: 'any'`

**Status-Based Triggering (conceptual G2):**
- Enforced in: Handler logic + frontend action offering
- Defined in: `microaction_registry.ts` → `triggers.status`
- Example: `status: ['open', 'diagnosed', 'in_progress']`

**Multi-Condition Gating (conceptual G3):**
- Enforced in: Handler logic
- Defined in: `microaction_registry.ts` → `triggers.conditions[]`
- Example: Check if equipment has active maintenance contract

**Always Allowed (conceptual G0):**
- Actions with `roles: 'any'` and no status/condition restrictions

### Security Invariants

**`SECURITY_INVARIANTS.md`** (7,200 words)
- 8 non-negotiable security rules
- I1: Yacht isolation enforced by RLS
- I2: No plaintext secrets
- I3: No mutation without auditability
- I4: JWT validation before DB access
- I5: RLS policies filter by session variable
- I6: Service role key never exposed to client
- I7: No SQL injection
- I8: Tokens must be revocable

**Enforcement locations:**
- JWT validation: `action_router/validators/jwt_validator.py`
- Yacht isolation: `action_router/validators/yacht_validator.py`
- RLS policies: `database/migrations/01_core_tables_v2_secure.sql`
- SQL injection prevention: Supabase client (parameterized queries)

---

## 4. WHERE ARCHITECTURAL DECISIONS ARE LOCKED

### Architectural Decision Documents

**`ARCHITECTURE.md`**
- Two-database model (MASTER DB + TENANT DB)
- Yacht = tenant boundary
- Single Postgres + RLS (NOT per-tenant databases)

**`SYSTEM_INVENTORY.md`** (6,800 words)
- Complete inventory of migrations, tables, handlers
- Table naming analysis (migrations vs handlers)
- Known risks and technical debt

**`MATURITY_ASSESSMENT.md`** (7,500 words)
- Production-ready: NONE
- Pilot-ready: 3 components (with caveats)
- 40 hours work needed before pilot
- Maturity rating: 2.25/5

**`HANDOVER.md`** (6,500 words)
- What must NOT be refactored casually
- Safe vs unsafe assumptions
- Debugging decision tree

### Non-Negotiable Files (from HANDOVER.md:264)

1. **Database migrations** - Create new migrations, don't edit existing
2. **p0_actions_routes.py** - 4,186 lines, no test coverage
3. **RLS policies** - Breaking these = cross-yacht data leaks
4. **test-data-discovery.ts** - All tests depend on this
5. **Environment variables** - Wrong credentials = all DB queries fail

---

## 5. DATABASE SCHEMA

### Master Database (8 migrations)

**Location:** `database/master_migrations/`

- `000_create_fleet_registry.sql` - Yacht entities (fleet-level)
- `001_create_user_accounts.sql` - User authentication
- `002_create_db_registry.sql` - Tenant database routing table
- `003_create_security_events.sql` - Audit trail for security events
- `004_create_get_my_bootstrap_rpc.sql` - Bootstrap RPC function
- `005_create_ensure_user_account_rpc.sql` - User provisioning RPC
- `006_add_tenant_key_alias.sql` - Tenant routing keys
- `007_update_get_my_bootstrap_with_alias.sql` - Bootstrap with routing

**Purpose:** User authentication, fleet registry, tenant routing

### Tenant Database (~15 migrations)

**Location:** `database/migrations/`

**Core migrations:**
- `00_enable_extensions.sql` - Enable Postgres extensions
- `01_core_tables_v2_secure.sql` - Auth tables (yachts, users, roles, tokens) + RLS
- `02_p0_actions_tables_REVISED.sql` - PMS domain tables (equipment, faults, work_orders, parts)

**Incremental migrations:**
- `03_add_accountability_columns.sql` - Audit columns (created_by, updated_by)
- `04_trust_accountability_tables.sql` - Accountability tables
- `05_rename_auth_tables.sql` - Auth table renames
- `06_fix_jwt_hook_function.sql` - JWT hook fixes
- `07_fix_rls_policies_jwt_fallback.sql` - RLS policy fixes
- `08_add_storage_rls_policy.sql` - Storage bucket RLS
- `09_fix_search_chunks_rls_table_name.sql` - Search RLS fixes
- `10_add_row_security_off_to_rpc.sql` - RPC security settings
- `11_create_get_user_auth_info_rpc.sql` - Auth info RPC

**Purpose:** PMS data (equipment, faults, work orders, parts, etc.) with RLS

---

## 6. TESTING INFRASTRUCTURE

### Test Structure

**Location:** `tests/`

**Contract Tests** (`tests/contracts/`)
- `jwt_verification_priority.test.ts` - JWT validation order
- `master_bootstrap.test.ts` - Master DB bootstrap contract
- `render_search_contract.test.ts` - Search functionality contract
- `rls-proof/email-isolation.test.ts` - Email isolation proof
- `rls-proof/yacht-isolation.test.ts` - Yacht isolation proof
- `tenant_has_docs.test.ts` - Document system contract

**E2E Tests** (`tests/e2e/`)
- `diagnostic_baseline.spec.ts` - Health check (61/64 pass expected)
- `nl_to_action_mapping.spec.ts` - NL→Action pipeline (64/64 pass expected)
- `auth.spec.ts` - Authentication flow
- `create_work_order_nl_queries.spec.ts` - Work order creation
- `full_flow_verification.spec.ts` - End-to-end flow
- `journey_truth.spec.ts` - User journey validation
- `chat_to_action.spec.ts` - Chat interface
- Plus ~15 more e2e test files

**Test Helpers** (`tests/helpers/`)
- `test-data-discovery.ts` (360 lines) - Auto-discovers test entity IDs from DB
- `seed-e2e-data.ts` - Seeds test data for e2e tests

**Test Fixtures** (`tests/fixtures/`)
- `microaction_registry.ts` (1,451 lines) - THE definitive micro-action catalog
- `test_data.json` - Test entity IDs
- `test_users.ts` - Test user definitions

**Test Framework:** Playwright (E2E), TypeScript

---

## 7. FRONTEND APPLICATION

### Frontend Structure

**Location:** `apps/web/`

**Next.js App Router:**
- `src/app/` - Page components
- `src/components/` - Reusable UI components
- `src/contexts/` - React contexts (auth, yacht, etc.)
- `src/hooks/` - Custom React hooks
- `src/lib/` - Utility functions
- `src/providers/` - Context providers
- `src/types/` - TypeScript type definitions
- `src/styles/` - Global styles
- `middleware.ts` - Next.js middleware (auth, routing)

**Status:** Minimal frontend, backend-focused system

---

## 8. DOCUMENTATION FILES AT ROOT

### Consolidation Documents (Created 2026-01-22)

- `SYSTEM_INVENTORY.md` (6,800 words) - What exists, what's unfinished
- `SECURITY_INVARIANTS.md` (7,200 words) - Non-negotiable security rules
- `MATURITY_ASSESSMENT.md` (7,500 words) - Brutally honest status
- `HANDOVER.md` (6,500 words) - Week 1 plan for next engineer
- `REPOSITORY_REORGANIZATION_PLAN.md` (4,000 words) - Proposed structure
- `CONSOLIDATION_COMPLETE.md` - Summary of consolidation work
- `README.md` (updated) - Clear entry point

### Meta-System Documents (Multi-Agent Verification)

**Agent Prompts:**
- `AGENT_1_ORCHESTRATOR_COMPLETE.md` - Agent 1 setup
- `AGENT_2_PROMPT.md` - Agent 2 (single action verification)
- `AGENT_3_PROMPT.md` - Agent 3 (pattern analysis)
- `AGENT_4_PROMPT.md` - Agent 4 (bulk fixes)
- `AGENT_COMMUNICATION_PROTOCOL.md` - Inter-agent communication
- `AGENT_LAUNCH_STANDARD.md` - How to launch agents

**Agent Handoffs:**
- `AGENT_1_HANDOFF.md` - Agent 1 → Agent 2/3/4
- `AGENT_2_HANDOFF.md` - Agent 2 → Agent 1
- `AGENT_3_HANDOFF_OLD.md`, `AGENT_3_HANDOFF.md` - Agent 3 → Agent 1
- `AGENT_3_COMPLETION_VERIFIED.md` - Agent 3 completion status

**Watchdog Documents:**
- `WATCHDOG_*.md` (multiple files) - Monitoring system

**Verification Documents:**
- `ACTION_VERIFICATION_GUIDE.md` - How to verify actions
- `ACTION_VERIFICATION_TEMPLATE.md` - Template for verification reports
- `AUTONOMOUS_VERIFICATION_SYSTEM_READY.md` - System readiness
- `MULTI_AGENT_VERIFICATION_PLAN.md` - Overall verification strategy

**Status:** Agent 3 completed (pattern analysis). Agent 4 not started.

### Product Documentation

- `ARCHITECTURE.md` - System architecture
- `briefing.md` - System briefing

### Total Count

**56 markdown files at root** (2026-01-22 count)

---

## 9. WHERE INCOMPLETE OR PLACEHOLDER FILES EXIST

### Known Incomplete Implementations (from MATURITY_ASSESSMENT.md)

**Database Mutations:**
- Only 1/64 actions proven to write to database
- 63/64 actions return HTTP 200 but database mutation unverified
- Files: All handlers in `apps/api/handlers/*.py`

**Audit Logging:**
- Only 4/64 actions create audit logs
- 60/64 actions missing audit logging (I3 violation)
- Files: All handlers in `apps/api/handlers/*.py`

**RLS Testing:**
- 0/64 actions have RLS tests
- Unknown if yacht isolation actually works for any action
- Files: Missing test files in `tests/contracts/rls-proof/`

**Table Naming:**
- Migrations create `public.equipment`
- Handlers reference `pms_equipment`
- Unknown if mismatch exists (unverified)
- Files: `database/migrations/*.sql` vs `apps/api/handlers/*.py`

### Incomplete Meta-System Components

**Agent 4 (Bulk Fixes):**
- Prompt exists: `AGENT_4_PROMPT.md`
- Launch standard exists: `AGENT_4_READY_TO_LAUNCH.md`
- Status: Not started

**Repository Reorganization:**
- Plan exists: `REPOSITORY_REORGANIZATION_PLAN.md`
- Move commands documented
- Status: Not executed (requires user approval)

---

## 10. ENVIRONMENT AND CONFIGURATION

### Environment Variables

**Required:**
- `MASTER_SUPABASE_URL` - Master DB URL
- `MASTER_SUPABASE_SERVICE_ROLE_KEY` - Master DB service key
- `TENANT_SUPABASE_URL` - Tenant DB URL (or per-yacht)
- `TENANT_SUPABASE_SERVICE_ROLE_KEY` - Tenant DB service key (or per-yacht)
- `TEST_YACHT_ID` - Test yacht UUID
- `TEST_USER_ID` - Test user UUID
- `DEFAULT_YACHT_CODE` - Default yacht code (e.g., `yTEST_YACHT_001`)

**Per-Yacht Routing (optional):**
- `{yacht_code}_SUPABASE_URL` - Yacht-specific DB URL
- `{yacht_code}_SUPABASE_SERVICE_KEY` - Yacht-specific DB service key

**File:** `.env` (local), Render environment variables (production)

### Configuration Files

- `package.json` - Node.js dependencies
- `requirements.txt` - Python dependencies
- `playwright.config.ts` - Playwright test config
- `tsconfig.json` - TypeScript config
- `next.config.js` - Next.js config

---

## 11. SCRIPTS AND UTILITIES

### Scripts Directory

**Location:** `scripts/`

**Purpose:** Utility scripts for database setup, data seeding, migrations

**Status:** Not inventoried in detail (low priority)

---

## 12. CI/CD AND DEPLOYMENT

### GitHub Actions

**Location:** `.github/workflows/`

**Status:** Exists but not inventoried in detail

### Deployment

**Platform:** Render (mentioned in docs)

**Status:** Production deployment exists but not documented here

---

## SUMMARY: WHERE EVERYTHING IS

| Component | Location | Line Count | Status |
|-----------|----------|------------|--------|
| **Micro-action definitions** | `tests/fixtures/microaction_registry.ts` | 1,451 | ✅ 76 actions defined |
| **Action implementations** | `apps/api/routes/p0_actions_routes.py` | 4,186 | ✅ 81 handlers implemented |
| **Handler modules** | `apps/api/handlers/*.py` | ~10,000+ | ⚠️ Database mutations unverified |
| **Action router** | `apps/api/action_router/` | ~2,000 | ✅ JWT/role/yacht validation |
| **Validators** | `apps/api/action_router/validators/` | ~1,000 | ✅ Implemented |
| **Master migrations** | `database/master_migrations/*.sql` | ~2,000 | ✅ 8 migrations |
| **Tenant migrations** | `database/migrations/*.sql` | ~5,000 | ✅ ~15 migrations |
| **Contract tests** | `tests/contracts/*.test.ts` | ~1,500 | ⚠️ RLS tests missing |
| **E2E tests** | `tests/e2e/*.spec.ts` | ~8,000 | ✅ 61/64 pass |
| **Test helpers** | `tests/helpers/test-data-discovery.ts` | 360 | ✅ Auto-discovery works |
| **Frontend** | `apps/web/src/` | ~5,000+ | ⚠️ Minimal, not primary focus |
| **Documentation** | `*.md` (root) | ~60,000 | ⚠️ 56 files, needs consolidation |
| **Security invariants** | `SECURITY_INVARIANTS.md` | 7,200 | ✅ 8 rules documented |
| **Architecture** | `ARCHITECTURE.md` | ~2,000 | ✅ Two-database model |

---

## KEY FINDINGS

1. **76 micro-actions defined, 81 handlers implemented** (5 more handlers than definitions - likely variants)
2. **Guard rails implemented as role/status/condition checks**, not labeled G0-G3 in code
3. **Security invariants documented but not fully enforced** (I3: 60/64 missing audit logs, I1/I5: RLS not tested)
4. **Database mutations unverified** (only 1/64 proven)
5. **Test infrastructure works** (61/64 actions return HTTP 200)
6. **Documentation is excessive** (56 files at root, reorganization plan created but not executed)
7. **Architectural decisions locked** in SYSTEM_INVENTORY.md, SECURITY_INVARIANTS.md, HANDOVER.md
8. **Meta-system (multi-agent verification) partially complete** (Agent 3 done, Agent 4 not started)

---

## NEXT STEPS

- **STEP 2:** Compare 76 definitions vs 81 implementations (which are missing/extra?)
- **STEP 3:** Map guard rail enforcement in code (where are role/status/condition checks?)
- **STEP 4:** Calculate implementation status by cluster (percentage complete)
- **STEP 5:** Identify untested high-risk actions (mutation_heavy with no RLS tests)
- **STEP 6:** Document system intent (who uses this, what problem does it solve)

---

**Status:** STEP 1 complete. Repository structure mapped.

**Truth:** We know where everything lives. We do not yet know what works vs what's missing.
