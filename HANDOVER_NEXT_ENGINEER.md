# Engineering Handover: CelesteOS Cloud PMS

**Date**: 2026-01-21
**Prepared By**: Claude Opus 4.5 (AI Engineering Assistant)
**Status**: Phase 13 Complete - Backend Remediation Done

---

## What This Project Is

**CelesteOS** is a yacht management platform (PMS = Planned Maintenance System) deployed at:

| Environment | URL |
|-------------|-----|
| **Production** | https://app.celeste7.ai |
| **Backend API** | https://pipeline-core.int.celeste7.ai |
| **Tenant DB** | https://vzsohavtuotocgrfkfyd.supabase.co |
| **Master DB** | https://qvzmkaamzaqxpzbewjxe.supabase.co |

**Test User**: `x@alex-short.com` (role: captain, yacht_id: `85fe1119-b04c-41ac-80f1-829d23322598`)

---

## My Role (AI Engineering Assistant)

I am your pair programmer. I:

1. **Write code** - Frontend (Next.js/React), Backend (Python/FastAPI), Tests (Playwright)
2. **Debug production** - Real E2E tests against production, not mocks
3. **Verify with evidence** - Screenshots, DB queries, HTTP responses, audit logs
4. **Never bullshit** - If something fails, I say "FAIL" not "should work"

**What I am NOT**:
- A chatbot that explains things without doing them
- An assistant that writes code but doesn't test it
- Someone who marks things "DONE" without production evidence

---

## The 100-Phase Plan

The project has a multi-phase verification plan. Here's where we are:

| Phase | Description | Status |
|-------|-------------|--------|
| 1-12 | Foundation, Auth, RLS, Documents, Email, OAuth | ✅ Complete |
| **13** | **Server-Driven Decisions + Mutations** | ✅ **JUST COMPLETED** |
| 14-100 | Remaining journeys, edge cases, performance | 🔲 Not started |

### Phase 13 Specifically (What I Just Did)

**Goal**: Verify that micro-actions (like `acknowledge_fault`) work end-to-end in production.

**Definition of PASS** (strict, no exceptions):
1. UI click → HTTP request fired
2. Backend returns 200/201 (not 4xx/5xx)
3. DB row actually changes (before/after proof)
4. Audit log created with `execution_id`
5. Evidence saved to file

**What Was Broken**:
- Frontend called wrong endpoint (`/workflows/update` instead of `/v1/actions/execute`)
- Audit log wasn't being created

**What I Fixed**:
- `AcknowledgeFaultModal.tsx` - Use correct `actionClient`
- `p0_actions_routes.py` - Add audit log creation
- `phase13_mutation_proof.spec.ts` - E2E test with DB verification

---

## Critical Documents to Read

| Document | Location | Purpose |
|----------|----------|---------|
| **Phase 13 Report** | `verification_handoff/PHASE_13_PROD_REPORT.md` | Complete evidence of what passed |
| **Mutation Proof** | `verification_handoff/evidence/phase13/P13_MUTATION_acknowledge_fault_proof.json` | JSON proof with DB before/after |
| **Action Registry** | `apps/web/src/types/actions.ts` | All 67+ micro-actions defined |
| **Workflow Archetypes** | `apps/web/src/types/workflow-archetypes.ts` | How actions map to endpoints |
| **Backend Handlers** | `apps/api/routes/p0_actions_routes.py` | Where actions are executed |
| **Decision Engine** | Server-driven via `/v1/decisions` | Controls what buttons show |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUCTION                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐ │
│  │   Frontend   │────▶│   Backend API    │────▶│  Tenant DB  │ │
│  │  (Vercel)    │     │   (Render)       │     │  (Supabase) │ │
│  │              │     │                  │     │             │ │
│  │ app.celeste  │     │ pipeline-core.   │     │ vzsohav...  │ │
│  │ 7.ai         │     │ int.celeste7.ai  │     │ .supabase   │ │
│  └──────────────┘     └──────────────────┘     └─────────────┘ │
│         │                      │                      │         │
│         │                      │                      │         │
│         ▼                      ▼                      ▼         │
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐ │
│  │  /v1/        │     │  /v1/actions/    │     │ pms_faults  │ │
│  │  decisions   │     │  execute         │     │ pms_work_   │ │
│  │              │     │                  │     │ orders      │ │
│  │ Returns      │     │ Runs handlers    │     │ pms_audit_  │ │
│  │ allowed      │     │ for mutations    │     │ log         │ │
│  │ actions      │     │                  │     │             │ │
│  └──────────────┘     └──────────────────┘     └─────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Concept: Server-Driven UI

The frontend does NOT decide what buttons to show. The backend does.

```typescript
// Frontend calls:
const { decisions, isAllowed } = useActionDecisions('fault', faultId);

// Backend returns:
{
  "allowed": ["acknowledge_fault", "diagnose_fault", ...],
  "blocked": ["delete_fault", ...],
  "execution_id": "uuid"
}

// Frontend renders buttons based on server response
{isAllowed('acknowledge_fault') && <AcknowledgeButton />}
```

This is called **fail-closed** behavior: if the server doesn't respond, NO buttons show.

---

## How to Run Tests

### E2E Tests (Production)

```bash
# Set environment variables
export TENANT_SUPABASE_SERVICE_ROLE_KEY="your-key-here"

# Run Phase 13 mutation proof test
npx playwright test tests/e2e/phase13_mutation_proof.spec.ts --reporter=list

# Run all E2E tests
npx playwright test
```

### API Tests

```bash
# Run acknowledge_fault regression test
cd apps/api
pytest tests/api/test_acknowledge_fault.py -v
```

### Build

```bash
cd apps/web
npm run build
```

---

## What SUCCESS Really Looks Like

### NOT Success ❌

```
- "The code looks correct"
- "It should work"
- "Tests pass locally"
- "I deployed the fix"
- Error: 404 Not Found
- Error: 500 Internal Server Error
- DB unchanged after action
- "Audit log will be created"
```

### SUCCESS ✅

```json
{
  "action": "acknowledge_fault",
  "httpStatus": 200,
  "dbBefore": { "status": "open" },
  "dbAfter": { "status": "investigating" },
  "auditLog": {
    "execution_id": "34f03655-2e95-4d7a-bf7e-8ee629f5b885",
    "old_values": { "status": "open" },
    "new_values": { "status": "investigating" }
  },
  "verdict": "PASS"
}
```

**The only acceptable proof is**:
1. Screenshot of UI before action
2. Screenshot of UI after action
3. HTTP 200 response captured
4. DB query showing row changed
5. Audit log query showing entry created
6. All saved to `verification_handoff/evidence/`

---

## Current State: What Works

| Feature | Status | Evidence |
|---------|--------|----------|
| Login | ✅ PASS | HTTP 200 |
| Bootstrap (get_my_bootstrap) | ✅ PASS | Returns yacht_id, role |
| /v1/decisions | ✅ PASS | Returns allowed actions |
| FaultCard buttons | ✅ PASS | All 7 buttons visible |
| acknowledge_fault | ✅ PASS | DB + audit verified |
| update_fault | 🔲 UI exists, backend not tested |
| add_to_handover | 🔲 UI exists, backend not tested |
| Work Order actions | 🔲 WorkOrderCard not integrated |
| Equipment actions | 🔲 EquipmentCard not integrated |

---

## What Needs to Be Done Next

### Immediate (Phase 13 Completion)

1. **Test `update_fault`** - Similar to acknowledge_fault
2. **Test `add_to_handover`** - Linking action
3. **Integrate WorkOrderCard** with `useActionDecisions`
4. **Integrate EquipmentCard** with `useActionDecisions`

### Phase 14+

5. Run full Journey 2 (Work Order flow)
6. Run full Journey 3 (Equipment flow)
7. Test all 67 micro-actions with evidence
8. Performance testing
9. Error handling edge cases

---

## Common Issues & Fixes

### "Failed to acknowledge fault" in UI
**Cause**: Frontend calling wrong endpoint
**Fix**: Use `actionClient.executeAction()` not `useActionHandler`

### "Could not find table in schema cache"
**Cause**: Table doesn't exist or RLS blocking
**Fix**: Check tenant DB has table, verify service role key

### Audit log not created
**Cause**: Wrong table name or missing signature field
**Fix**: Use `pms_audit_log` (tenant convention), include `signature` (NOT NULL)

### DB not changing after action
**Cause**: Handler doesn't exist or yacht isolation failing
**Fix**: Check `p0_actions_routes.py` has handler, verify yacht_id matches

---

## Repository Structure

```
BACK_BUTTON_CLOUD_PMS/
├── apps/
│   ├── web/                    # Next.js frontend (Vercel)
│   │   ├── src/
│   │   │   ├── components/     # React components
│   │   │   │   ├── cards/      # FaultCard, WorkOrderCard, etc.
│   │   │   │   └── modals/     # AcknowledgeFaultModal, etc.
│   │   │   ├── hooks/          # useActionDecisions, useAuth
│   │   │   ├── lib/            # actionClient, apiClient
│   │   │   └── types/          # actions.ts, workflow-archetypes.ts
│   │   └── ...
│   └── api/                    # Python FastAPI backend (Render)
│       ├── routes/             # API routes
│       │   └── p0_actions_routes.py  # Action handlers
│       ├── action_router/      # Action routing logic
│       └── handlers/           # Domain handlers
├── supabase/
│   └── migrations/             # DB schema migrations
├── tests/
│   ├── e2e/                    # Playwright E2E tests
│   │   └── phase13_mutation_proof.spec.ts
│   └── api/                    # API unit tests
│       └── test_acknowledge_fault.py
└── verification_handoff/
    ├── evidence/               # All proof artifacts
    │   └── phase13/            # Phase 13 specific
    └── PHASE_13_PROD_REPORT.md # Summary report
```

---

## Environment Variables You Need

```bash
# Tenant DB (yacht operations data)
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=<get from team>

# Master DB (auth, fleet registry)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=<get from team>

# Test user credentials
TEST_EMAIL=x@alex-short.com
TEST_PASSWORD=<get from team>
```

---

## Golden Rules

1. **Never say DONE without evidence** - Screenshot + DB query + HTTP response
2. **Test in production, not staging** - The URL is `app.celeste7.ai`
3. **FAIL is a valid result** - Document it clearly, don't hide it
4. **Audit logs are mandatory** - Silent failures are forbidden
5. **Yacht isolation is non-negotiable** - Every query must include `yacht_id`
6. **Read the code before changing it** - Use `Read` tool first
7. **One task at a time** - Use TodoWrite to track progress

---

## Contact & Resources

- **GitHub Repo**: https://github.com/shortalex12333/Cloud_PMS
- **Production Site**: https://app.celeste7.ai
- **Supabase Dashboard (Tenant)**: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd

---

## Final Words

This is a real production system used by real yacht crews. Every action a user takes must:
1. Work the first time
2. Show clear feedback
3. Save to the database
4. Create an audit trail

If something fails silently, crews lose trust. If data doesn't save, maintenance gets missed. If audit logs are empty, accountability disappears.

**Your job is to make this bulletproof. No excuses. Hard proof only.**

Good luck, engineer.
