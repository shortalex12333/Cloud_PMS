# Documentation File Index

> Quick reference to find any documentation file.

---

## Priority Files (Read These First)

| File | Location | Purpose |
|------|----------|---------|
| **ONBOARDING.md** | `docs/` | Start here - complete developer guide |
| **COMPLETE_ACTION_EXECUTION_CATALOG.md** | `root/` | All 67 actions with full code (6,584 lines) |
| **ARCHITECTURE_V4_COMPLETE.md** | `root/` | System architecture overview |

---

## Actions & Microactions

| File | Location | Lines | Purpose |
|------|----------|-------|---------|
| COMPLETE_ACTION_EXECUTION_CATALOG.md | root | 6,584 | **MASTER** - All actions with implementation |
| COMPLETE_ACTION_CATALOG_SPEC.md | root | 1,175 | Action specifications |
| ACTION_SYSTEM_ARCHITECTURE.md | root | 1,357 | Action system design |
| ACTION_HANDLER_IMPLEMENTATION_STATUS.md | root | ~300 | Implementation checklist |
| ACTION_TRIGGERS_AND_FLOWS.md | root | ~400 | Action trigger logic |
| P0_ACTION_CONTRACTS.md | root | 1,376 | Priority 0 contracts |
| P0_ACTIONS_TEST_GUIDE.md | root | ~200 | P0 testing guide |
| P0_ACTIONS_TEST_QUERIES.md | root | 1,741 | Test queries |
| ACTION_TO_TABLE_MAP.md | docs/actions/ | ~400 | Action → Table mapping |
| ACTION_BACKEND_SPEC.md | docs/actions/ | 1,956 | Backend implementation |
| MICRO_ACTION_REGISTRY.md | docs/micro-actions/ | ~600 | Microaction definitions |
| ACTION_OFFERING_MAP.md | docs/micro-actions/ | ~300 | Card → Actions mapping |
| ACTION_OFFERING_RULES.md | docs/micro-actions/ | ~200 | Display rules |
| COMPLETE_67_ACTIONS_AUDIT.md | docs/ | ~800 | Audit of all actions |
| MICROACTION_WORKFLOW_MASTER_LIST.md | docs/ | 1,100 | Workflow master list |

---

## Database

| File | Location | Purpose |
|------|----------|---------|
| DATABASE_SCHEMA_EXECUTION_SPEC.md | root | Column-by-column specs |
| DATABASE_SCHEMA_EXECUTION_SPEC_PART2.md | root | Continued specs |
| DATABASE_SCHEMA_EXECUTION_SPEC_PART3.md | root | Continued specs |
| DATABASE_SCHEMA.md | docs/ | Schema overview |
| DATABASE_REQUIREMENTS_MVP.md | root | MVP requirements |
| DATABASE_NAMING_AND_TRUST_FINAL.md | root | Naming conventions |
| 00_MASTER_DATABASE_SPEC_README.md | root | Database master spec |
| COMPLETE_TABLE_AUDIT.md | docs/ | Table audit |
| COLUMN_SEARCH_MATRIX.md | docs/ | Search column mapping |

---

## Situations

| File | Location | Purpose |
|------|----------|---------|
| SITUATIONAL_STATE_ARCHITECTURE_V4.md | root | Complete situation system (1,202 lines) |
| SITUATION_STATE_DESIGN_V2.md | root | Earlier design version |

---

## Architecture

| File | Location | Purpose |
|------|----------|---------|
| ARCHITECTURE_V4_COMPLETE.md | root | Full architecture (2,130 lines) |
| ARCHITECTURE_UNIFIED.md | docs/ | Unified architecture |
| ARCHITECTURE.md | docs/ | Architecture overview |
| V4_FOLDER_STRUCTURE_AND_ORGANIZATION.md | root | Folder structure |
| GUARDS_RULES_OF_THE_ROAD.md | root | Development guardrails |
| GUARD_SEVERITY_TAXONOMY.md | root | Error severity levels |

---

## Deployment

| File | Location | Purpose |
|------|----------|---------|
| DEPLOYMENT.md | docs/ | Deployment guide |
| DEPLOYMENT_READY.md | root | Deployment checklist |
| DEPLOYMENT_SUMMARY.md | root | Deployment summary |
| DEPLOYMENT_COMPLETE_SUMMARY.md | root | Post-deployment notes |
| DEPLOY_MIGRATIONS_GUIDE.md | root | Migration guide |
| RENDER_DEPLOYMENT_TEST_RESULTS.md | root | Render test results |
| VERCEL_DEPLOYMENT_STATUS.md | root | Vercel status |

---

## Search & Query

| File | Location | Purpose |
|------|----------|---------|
| GRAPHRAG_QUERY_PATTERNS.md | docs/ | Query patterns (1,359 lines) |
| QUERY_TYPES.md | docs/ | Query type definitions |
| frontend_search_contract.md | docs/ | Frontend search contract |
| ENTITY_TYPES.md | docs/ | Entity type definitions |
| INTENT_SYSTEM.md | docs/ | Intent recognition |

---

## Development Guides

| File | Location | Purpose |
|------|----------|---------|
| ONBOARDING.md | docs/ | New developer guide |
| CODE_REVIEW_GUIDE.md | docs/ | Code review standards |
| SYSTEM_OPERATIONS_GUIDE.md | docs/ | Operations guide |
| INTEGRATION.md | docs/ | Integration guide |

---

## Scripts

| File | Location | Purpose |
|------|----------|---------|
| prove_prod_parity.sh | scripts/dev/ | Prod-parity test harness |
| supabase_start.sh | scripts/dev/ | Start local Supabase |
| supabase_stop.sh | scripts/dev/ | Stop local Supabase |
| supabase_reset.sh | scripts/dev/ | Reset local database |

---

## Contracts & Schemas

| File | Location | Purpose |
|------|----------|---------|
| pipeline_response.schema.json | contracts/ | API response JSON schema |

---

## Bug Fixes & Diagnostics (Historical)

These files document past issues and fixes:

| File | Purpose |
|------|---------|
| BACKEND_BUG_FOUND.md | Past backend bug |
| BACKEND_SEARCH_BUG.md | Search bug fix |
| BUGS_FOUND_AND_FIXED.md | Bug summary |
| CORS_POLICY_ANALYSIS.md | CORS issues |
| CHROME_BLOCKING_FIX.md | Browser fix |
| DIAGNOSTIC_*.md | Various diagnostics |
| FIX_*.md | Various fixes |
| APPLY_*.md | Fix applications |

---

## Phase Documentation (Historical)

| File | Location | Purpose |
|------|----------|---------|
| PHASE_1_COMPLETION_STATUS.md | docs/ | Phase 1 status |
| PHASE_2_MASTER_ARCHITECTURE.md | docs/ | Phase 2 architecture |
| PHASE_5_BACKEND_BLUEPRINT.md | docs/ | Phase 5 backend |
| phase3/*.md | docs/phase3/ | Phase 3 docs |
| phase4/*.md | docs/phase4/ | Phase 4 docs |

---

## Quick Links by Task

### "I need to add a new action"
1. `COMPLETE_ACTION_EXECUTION_CATALOG.md` - See existing patterns
2. `docs/actions/ACTION_TO_TABLE_MAP.md` - Find the right table
3. `apps/api/handlers/` - Implement handler

### "I need to understand the database"
1. `DATABASE_SCHEMA_EXECUTION_SPEC.md` - Column details
2. `docs/DATABASE_SCHEMA.md` - Overview
3. `supabase/migrations/` - Actual SQL

### "I need to understand situations"
1. `SITUATIONAL_STATE_ARCHITECTURE_V4.md` - Full design

### "I need to deploy"
1. `docs/ONBOARDING.md` Section 9 - Production Pipeline
2. `DEPLOYMENT.md` - Details

### "I need to run locally"
1. `docs/ONBOARDING.md` Section 3-4 - Quick Start & Setup
2. `scripts/dev/` - Helper scripts

---

*Use `grep -r "keyword" .` to search all docs*
