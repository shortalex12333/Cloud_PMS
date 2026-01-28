# Shopping List Lens v1 - Complete Documentation Index

**Status**: ✅ Production-Ready with Automated Monitoring
**Version**: 1.0.0
**Date**: 2026-01-28
**Test Coverage**: 27/27 passing (100%)

---

## Overview

Shopping List Lens v1 is a comprehensive procurement request management system with role-based approval workflows, defense-in-depth security, and automated health monitoring.

**Key Features**:
- ✅ 5 microactions (create, approve, reject, promote, view history)
- ✅ Role-based access control (CREW → HOD → ENGINEER)
- ✅ Defense-in-depth security (3 layers)
- ✅ 100% test pass rate (27/27 tests)
- ✅ Automated health monitoring
- ✅ CI/CD workflows

---

## Documentation Structure

### 1. Architecture Documentation

**File**: [SHOPPING_LIST_LENS_V1.md](./SHOPPING_LIST_LENS_V1.md)

**Contents**:
- Executive Summary
- System Architecture (3-layer defense-in-depth)
- The 5 Shopping List Actions
- Database Schema (pms_shopping_list_items, state_history)
- Security Architecture (Router, Handlers, RLS)
- State Machine (candidate → approved/rejected)
- API Reference (endpoints, authentication, responses)
- Testing Infrastructure (27/27 tests)
- Deployment Status

**For**: Backend engineers, architects

---

### 2. Microaction Catalog

**File**: [SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md](./SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md)

**Contents**:
- All 5 actions documented with 12 dimensions each:
  1. Identification
  2. Access Control
  3. Interface
  4. Triggers
  5. Preconditions
  6. Validation Rules
  7. Side Effects
  8. Related Actions
  9. Success States
  10. Error States
  11. UI Surfacing
  12. Examples
- Role Permission Matrix
- Field Reference Tables
- Complete curl examples

**For**: Product managers, QA engineers, frontend engineers

---

### 3. Visual Flowcharts

**File**: [SHOPPING_LIST_LENS_V1_FLOWCHARTS.md](./SHOPPING_LIST_LENS_V1_FLOWCHARTS.md)

**Contents**:
- 6 Mermaid flowcharts:
  1. Master Journey Map (role-gated paths)
  2. Create Shopping List Item Flow
  3. Approve Shopping List Item Flow
  4. Reject Shopping List Item Flow
  5. Promote Candidate to Part Flow
  6. Role Permission Matrix
- 4 complete user journey examples
- Field requirement summary tables
- State machine diagram
- Security architecture notes

**For**: Frontend engineers, UI/UX designers, QA

---

### 4. Engineer Handoff

**File**: [SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md](./SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md)

**Contents**:
- What was built (executive summary)
- Architecture overview (state machine, roles, security)
- Files created/modified (handlers, migrations, tests)
- Database changes (RLS policies, helper functions)
- API endpoints (5 actions with examples)
- Testing infrastructure (27/27 tests)
- How to continue work (add actions, debug, extend)
- Quick reference (key files, concepts, credentials)

**For**: Next engineer on the project

---

### 5. Ops Deployment

**File**: [SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md](./SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md)

**Contents**:
- Ops files generated (health worker, tests, workflows)
- Shopping List Lens specifics (no SIGNED actions)
- Deployment steps (DB migration, Render worker, CI)
- Configuration (feature flags, test users)
- Success criteria (health checks, monitoring)
- Testing philosophy (canon doctrine)
- Next steps (deployment, monitoring, rollout)

**For**: DevOps, site reliability engineers

---

## Quick Navigation

### By Role

**Backend Engineer**:
1. Start with [Architecture](./SHOPPING_LIST_LENS_V1.md)
2. Review [Engineer Handoff](./SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md)
3. Check [Ops Deployment](./SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md) for monitoring

**Frontend Engineer**:
1. Start with [Flowcharts](./SHOPPING_LIST_LENS_V1_FLOWCHARTS.md)
2. Review [Microaction Catalog](./SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md)
3. Check API Reference in [Architecture](./SHOPPING_LIST_LENS_V1.md#api-reference)

**QA Engineer**:
1. Start with [Microaction Catalog](./SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md)
2. Review [Flowcharts](./SHOPPING_LIST_LENS_V1_FLOWCHARTS.md) for test scenarios
3. Check [Engineer Handoff](./SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md#testing-infrastructure)

**Product Manager**:
1. Start with [Microaction Catalog](./SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md)
2. Review [Flowcharts](./SHOPPING_LIST_LENS_V1_FLOWCHARTS.md) for user journeys
3. Check Executive Summary in [Architecture](./SHOPPING_LIST_LENS_V1.md#executive-summary)

**DevOps/SRE**:
1. Start with [Ops Deployment](./SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md)
2. Review [Engineer Handoff](./SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md) for credentials
3. Check Database Changes in [Architecture](./SHOPPING_LIST_LENS_V1.md#database-schema)

---

## Key Technical Details

### The 5 Actions

| Action | Variant | Roles | Purpose |
|--------|---------|-------|---------|
| `create_shopping_list_item` | MUTATE | All authenticated | Request item for procurement |
| `approve_shopping_list_item` | MUTATE | HOD only | Approve item for ordering |
| `reject_shopping_list_item` | MUTATE | HOD only | Reject item with reason |
| `promote_candidate_to_part` | MUTATE | Engineers only | Add to parts catalog |
| `view_shopping_list_item_history` | READ | All authenticated | View state changes |

### Role Hierarchy

```
crew/deckhand/steward         → Create only
    ↓
engineer/eto                  → Create + Promote
    ↓
chief_officer/purser          → Create + Approve + Reject (HOD)
    ↓
chief_engineer                → Create + Approve + Reject + Promote (HOD + Engineer)
    ↓
captain/manager               → Full access (all actions)
```

### Defense-in-Depth Security (3 Layers)

**Layer 1: Router** (`apps/api/main.py`)
- Action definitions enforce `allowed_roles`
- First line of defense

**Layer 2: Handlers** (`apps/api/handlers/shopping_list_handlers.py`)
- Explicit `is_hod()` and `is_engineer()` checks
- Returns 403 with descriptive messages

**Layer 3: Database (RLS)**
- 4 role-specific UPDATE policies
- Blocks direct SQL access
- Proven: 0 rows updated when CREW attempts approve/reject/promote

### State Machine

```
candidate → approved (terminal, can be promoted)
         → rejected (terminal, rejected_at set)

approved → promoted (extended state, promoted_to_part_id set)
```

---

## Test Results

### Docker RLS Tests: 18/18 ✅

**Location**: `tests/docker/run_shopping_list_rls_tests.py`

**Coverage**:
- 8 Role & CRUD tests (CREW, HOD, ENGINEER operations)
- 4 Isolation tests (anonymous, cross-yacht, yacht filtering)
- 6 Edge case tests (validation, double operations)

**Evidence**: `docs/pipeline/shopping_list_lens/PHASE3_DOCKER_RLS_RESULTS.md`

### Staging Acceptance Tests: 9/9 ✅

**Location**: `tests/ci/staging_shopping_list_acceptance.py`

**Coverage**:
- Action list filtering (CREW vs HOD)
- CREW operations (create=200, approve/reject/promote=403)
- HOD operations (approve=200, reject=200)
- ENGINEER operations (promote=200)

**Evidence**: `docs/pipeline/shopping_list_lens/PHASE4_STAGING_ACCEPTANCE_RESULTS.md`

### Combined Results: 27/27 (100%) ✅

- ✅ 0×500 requirement met (zero 5xx errors)
- ✅ Backend authority principle validated
- ✅ Defense-in-depth security proven
- ✅ All role gates functioning correctly

---

## Deployment Status

### Production Readiness: ✅ READY

**Code**:
- ✅ 5 handlers implemented with role checks
- ✅ RLS policies applied and verified
- ✅ Migration scripts idempotent

**Testing**:
- ✅ 100% test pass rate (27/27)
- ✅ Evidence documented with transcripts
- ✅ 0×500 requirement met

**Monitoring**:
- ✅ Health worker generated
- ✅ CI/CD workflows configured
- ⏳ Ready for Render deployment

**Documentation**:
- ✅ Architecture documented
- ✅ Action catalog complete
- ✅ Flowcharts created
- ✅ Engineer handoff written
- ✅ Ops deployment guide ready

---

## Ops Infrastructure

### Automated Health Monitoring

**File**: `tools/ops/monitors/shopping_list_health_worker.py`

**Functionality**:
- Checks every 15 minutes (configurable)
- Tests: service health, feature flags, action list
- Writes to `pms_health_checks` table
- Emits structured logs for Render dashboard

**Deployment**: Add to `render.yaml` as background worker

### CI/CD Workflows

**Acceptance Tests**: `.github/workflows/shopping_list-staging-acceptance.yml`
- Triggers on Shopping List code changes
- Runs acceptance tests against staging
- Uploads evidence artifacts

**Stress Tests**: `.github/workflows/shopping_list-stress.yml`
- Runs nightly at 2 AM UTC
- Tests 50 concurrent /list + 30 /execute
- Enforces 0×500 requirement
- Reports P50/P95/P99 latencies

### Database Schema

**Tables**:
- `pms_health_checks` - Aggregated health check results
- `pms_health_events` - Detailed event logs

**Helper Functions**:
- `get_latest_health_check(yacht_id, lens_id)`
- `get_health_check_history(yacht_id, lens_id, hours)`
- `get_unhealthy_lenses(yacht_id)`

**Migration**: `supabase/migrations/20260128_ops_health_tables.sql`

---

## Feature Flags

### Current Status

**Flag**: `SHOPPING_LIST_LENS_V1_ENABLED`
- **Default**: `false` (OFF on main branch)
- **Staging Canary**: ⏳ Not yet enabled
- **Production**: ❌ Disabled

### Toggle Procedures

**Enable Canary** (Staging):
```bash
# Render Dashboard → Environment
SHOPPING_LIST_LENS_V1_ENABLED=true

# Trigger deployment
curl -X POST "https://api.render.com/deploy/srv-YOUR-SERVICE-ID?key=YOUR-KEY"
```

**Disable** (Rollback):
```bash
# Render Dashboard → Environment
SHOPPING_LIST_LENS_V1_ENABLED=false

# Trigger deployment (same as above)
```

**Documentation**: `docs/pipeline/SHOPPING_LIST_FEATURE_FLAGS.md`

---

## Important Notes

### Shopping List Lens Specifics

⚠️ **No SIGNED Actions**: Shopping List Lens has no SIGNED actions. All actions are MUTATE or READ:
- **MUTATE**: create, approve, reject, promote
- **READ**: view_history

This differs from other lenses (e.g., Faults Lens has SIGNED action `create_work_order_from_fault`).

**Implications**:
- Signed flow acceptance test needs adaptation for MUTATE role gating
- Health worker and stress tests work as-is
- No signature validation required (no PIN/TOTP)

### Testing Doctrine

All tests enforce CelesteOS testing doctrine:

**1. Expected 4xx is Success (When Asserted)**
- Citation: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:799`
- CREW getting 403 for approve = PASS (not failure)

**2. 500 is Always Failure**
- Citation: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`
- Any 5xx error = test failure (0×500 requirement)

**3. Evidence Artifacts Required**
- Citation: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:815`
- Full HTTP transcripts, status codes, before/after DB state

---

## File Locations

### Documentation

| File | Location | Purpose |
|------|----------|---------|
| README.md | docs/architecture/20_SHOPPING_LIST_LENS/ | This file (index) |
| SHOPPING_LIST_LENS_V1.md | docs/architecture/20_SHOPPING_LIST_LENS/ | Architecture |
| SHOPPING_LIST_LENS_V1_MICROACTION_CATALOG.md | docs/architecture/20_SHOPPING_LIST_LENS/ | Action catalog |
| SHOPPING_LIST_LENS_V1_FLOWCHARTS.md | docs/architecture/20_SHOPPING_LIST_LENS/ | Visual flows |
| SHOPPING_LIST_LENS_V1_ENGINEER_HANDOFF.md | docs/architecture/20_SHOPPING_LIST_LENS/ | Engineer handoff |
| SHOPPING_LIST_LENS_V1_OPS_DEPLOYMENT.md | docs/architecture/20_SHOPPING_LIST_LENS/ | Ops deployment |

### Code

| File | Location | Purpose |
|------|----------|---------|
| shopping_list_handlers.py | apps/api/handlers/ | Handler implementations |
| 20260128_shopping_list_rls_fix.sql | supabase/migrations/ | RLS policies |
| run_shopping_list_rls_tests.py | tests/docker/ | Docker RLS tests (18) |
| staging_shopping_list_acceptance.py | tests/ci/ | Staging tests (9) |

### Ops Infrastructure

| File | Location | Purpose |
|------|----------|---------|
| shopping_list_health_worker.py | tools/ops/monitors/ | Health monitoring |
| shopping_list_signed_flow_acceptance.py | tests/ci/ | Acceptance tests |
| shopping_list_actions_endpoints.py | tests/stress/ | Stress tests |
| shopping_list-staging-acceptance.yml | .github/workflows/ | CI workflow |
| shopping_list-stress.yml | .github/workflows/ | CI workflow |
| SHOPPING_LIST_FEATURE_FLAGS.md | docs/pipeline/ | Feature flags |
| 20260128_ops_health_tables.sql | supabase/migrations/ | Health tables |

### Evidence

| File | Location | Purpose |
|------|----------|---------|
| PHASE3_DOCKER_RLS_RESULTS.md | docs/pipeline/shopping_list_lens/ | RLS test evidence |
| PHASE4_STAGING_ACCEPTANCE_RESULTS.md | docs/pipeline/shopping_list_lens/ | Acceptance evidence |

---

## Next Steps for Deployment

### Phase 1: Apply DB Migration ✅

```bash
psql $STAGING_DB_URL < supabase/migrations/20260128_ops_health_tables.sql
```

**Status**: Migration file ready, needs application to staging/production

### Phase 2: Deploy Health Worker ⏳

**Action**: Add to `render.yaml` and deploy

**Status**: Worker file generated, needs Render configuration

### Phase 3: Enable CI Workflows ⏳

**Action**: Add GitHub Secrets and trigger workflows

**Status**: Workflow files ready, needs GitHub configuration

### Phase 4: Monitor for 7 Days ⏳

**Action**: Query `pms_health_checks` table daily

**Status**: Waiting for health worker deployment

### Phase 5: Enable Feature Flag ⏳

**Action**: Set `SHOPPING_LIST_LENS_V1_ENABLED=true` in Render

**Status**: Waiting for successful monitoring period

---

## Success Criteria

✅ **Documentation**: 100% complete (5 comprehensive files)
✅ **Testing**: 27/27 passing (100% pass rate)
✅ **Security**: Defense-in-depth proven (3 layers)
✅ **Code Quality**: RLS policies + handler checks + router gates
✅ **Ops Infrastructure**: Health worker + CI/CD + monitoring
⏳ **Deployment**: Ready for Render deployment
⏳ **Monitoring**: Pending health worker deployment
⏳ **Production**: Pending feature flag enablement

---

## Contact & Support

**Codebase**: `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/`

**Documentation**: `docs/architecture/20_SHOPPING_LIST_LENS/`

**Testing Doctrine**: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md`

**Lens Ops Template**: `docs/architecture/20_lens_ops/`

**Evidence**: `docs/pipeline/shopping_list_lens/`

---

**Shopping List Lens v1**: ✅ Complete, Documented, Production-Ready

**Status**: Ready for deployment with automated monitoring 🚀
