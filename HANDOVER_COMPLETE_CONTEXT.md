# Complete Context Handover: CelesteOS Cloud PMS

---

## My Sole Purpose

**I am a verification engineer.** My job is NOT to:
- Explain code
- Write documentation
- Give opinions
- Say "should work"

**My job IS to:**
1. Execute actions against PRODUCTION
2. Capture HTTP responses
3. Query databases for proof
4. Save evidence to files
5. Report PASS or FAIL with hard proof

**The standard**: Production-grade engineering. Real user flows. Real database changes. Real audit trails. No mocks. No staging. No "it works on my machine."

**Test User**: `x@alex-short.com` on https://app.celeste7.ai
**Evidence Location**: `verification_handoff/evidence/`

---

## Purpose of the Site

**CelesteOS** is a **Planned Maintenance System (PMS)** for superyachts.

### What Yacht Crews Do With It
- Log faults (engine vibration, AC failure, etc.)
- Create work orders for repairs
- Track equipment maintenance schedules
- Document completed work with photos
- Hand over issues between shifts/crew changes

### Why It Matters
- Yachts are worth $10M-$100M+
- Missed maintenance = equipment failure at sea
- No audit trail = liability issues
- Silent failures = crews lose trust

### Core Entities
| Entity | Table | Purpose |
|--------|-------|---------|
| Fault | `pms_faults` | Something is broken/wrong |
| Work Order | `pms_work_orders` | Task to fix something |
| Equipment | `pms_equipment` | Physical asset being maintained |
| Document | `pms_documents` | Photos, PDFs, manuals |
| Audit Log | `pms_audit_log` | Who did what when |

### Multi-Tenant Architecture
Each yacht is a tenant. Data isolation is enforced by `yacht_id` on every row.

```sql
-- CORRECT: Yacht-isolated query
SELECT * FROM pms_faults WHERE id = 'xxx' AND yacht_id = 'yyy';

-- WRONG: Data leak across yachts
SELECT * FROM pms_faults WHERE id = 'xxx';
```

---

## The 100-Phase Verification Plan

### Overview

| Chunk | Phases | Focus | Status |
|-------|--------|-------|--------|
| Foundation | 1-5 | Auth, Bootstrap, Basic UI | ✅ Done |
| Data Layer | 6-10 | RLS, Queries, Caching | ✅ Done |
| Documents | 11-12 | Upload, Storage, Retrieval | ✅ Done |
| **Mutations** | **13-20** | **Actions, Side Effects, Audit** | **🔶 In Progress** |
| Journeys | 21-40 | Full User Flows | 🔲 Not Started |
| Edge Cases | 41-60 | Error Handling, Offline, Race Conditions | 🔲 Not Started |
| Performance | 61-80 | Load Testing, Optimization | 🔲 Not Started |
| Security | 81-90 | Penetration Testing, RLS Verification | 🔲 Not Started |
| Polish | 91-100 | UI/UX, Accessibility, Final QA | 🔲 Not Started |

---

### Phase Breakdown

#### Phases 1-5: Foundation
- [x] User can log in with email/password
- [x] Bootstrap endpoint returns user's yacht_id and role
- [x] Session persists across page refresh
- [x] Logout works
- [x] Protected routes redirect to login

#### Phases 6-10: Data Layer
- [x] Row Level Security enforced on all tables
- [x] User can only see their yacht's data
- [x] Queries return expected data shape
- [x] Caching doesn't leak stale data
- [x] Real-time subscriptions work

#### Phases 11-12: Documents
- [x] Upload document to storage
- [x] Retrieve document with signed URL
- [x] Document linked to fault/work order
- [x] Delete document removes from storage

#### Phases 13-20: Mutations (CURRENT FOCUS)
- [x] **Phase 13**: `acknowledge_fault` - PASS
- [ ] Phase 14: `update_fault` - Not tested
- [ ] Phase 15: `add_to_handover` - Not tested
- [ ] Phase 16: `create_work_order` - Not tested
- [ ] Phase 17: `complete_work_order` - Not tested
- [ ] Phase 18: `log_equipment_hours` - Not tested
- [ ] Phase 19: `diagnose_fault` (AI) - Not tested
- [ ] Phase 20: Batch mutations - Not tested

**Definition of PASS for any mutation**:
```
1. UI click triggers HTTP request
2. Backend returns 200/201
3. DB row changes (before ≠ after)
4. Audit log created with execution_id
5. Evidence saved to file
```

#### Phases 21-40: User Journeys
- [ ] Journey 1: Report fault → Acknowledge → Diagnose → Create WO → Complete
- [ ] Journey 2: Schedule maintenance → Generate WO → Assign → Complete
- [ ] Journey 3: Equipment inspection → Log hours → Flag issues
- [ ] Journey 4: Shift handover → Review outstanding → Acknowledge
- [ ] Journey 5: Document upload → Link to entity → Retrieve

#### Phases 41-60: Edge Cases
- [ ] Network failure during mutation
- [ ] Concurrent edits to same entity
- [ ] Token expiry mid-session
- [ ] Invalid payload handling
- [ ] Orphaned records cleanup

#### Phases 61-80: Performance
- [ ] Page load < 2 seconds
- [ ] List renders 100+ items without lag
- [ ] Mutations complete < 500ms
- [ ] No memory leaks on long sessions

#### Phases 81-90: Security
- [ ] Cannot access other yacht's data via API
- [ ] Cannot bypass RLS with crafted requests
- [ ] Audit log cannot be tampered
- [ ] Service role key not exposed to client

#### Phases 91-100: Polish
- [ ] All buttons have loading states
- [ ] Error messages are user-friendly
- [ ] Mobile responsive
- [ ] Accessibility audit passes

---

## Environment Variables

### Required for Testing

```bash
# Tenant DB (yacht operations)
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=<ask team lead>

# Master DB (auth, fleet registry)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=<ask team lead>

# Test credentials
TEST_EMAIL=x@alex-short.com
TEST_PASSWORD=Password2!
```

### Where to Set Them

| Context | Location |
|---------|----------|
| Local dev | Terminal: `export VAR=value` |
| Local persistent | `apps/web/.env.local` |
| CI/CD | GitHub Secrets |
| Vercel | Project Settings → Environment Variables |
| Render | Service → Environment |

### What Each Does

| Variable | Used By | Purpose |
|----------|---------|---------|
| `TENANT_SUPABASE_SERVICE_ROLE_KEY` | E2E tests | Bypass RLS for DB verification |
| `MASTER_SUPABASE_SERVICE_ROLE_KEY` | E2E tests | Setup test user if needed |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Client-side Supabase connection |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Public anon key (RLS enforced) |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Server-side admin operations |

### Security Notes
- Service role keys bypass RLS - NEVER expose to client
- Anon key is safe for client (RLS protects data)
- Rotate keys if compromised

---

## How to Test

### 1. E2E Mutation Proof Test (Phase 13)

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Set the service key
export TENANT_SUPABASE_SERVICE_ROLE_KEY="eyJ..."

# Run the test
npx playwright test tests/e2e/phase13_mutation_proof.spec.ts --reporter=list
```

**What it does**:
1. Resets fault to `open` status
2. Logs in as test user
3. Navigates to fault
4. Clicks Acknowledge button
5. Queries DB before and after
6. Queries audit log
7. Saves proof to JSON file
8. Asserts PASS or FAIL

**Evidence output**: `verification_handoff/evidence/phase13/`

### 2. Run All E2E Tests

```bash
npx playwright test
```

### 3. Run Specific Test File

```bash
npx playwright test tests/e2e/some_test.spec.ts
```

### 4. Run with UI (Debug Mode)

```bash
npx playwright test --ui
```

### 5. API Unit Tests

```bash
cd apps/api
pytest tests/ -v
```

### 6. Build Frontend

```bash
cd apps/web
npm run build
```

### 7. Type Check

```bash
cd apps/web
npm run typecheck
```

---

## Facilities (Infrastructure)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRODUCTION                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐                                                        │
│  │   GitHub     │                                                        │
│  │   Repo       │                                                        │
│  └──────┬───────┘                                                        │
│         │                                                                │
│         │ push to main                                                   │
│         ▼                                                                │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐     │
│  │   Vercel     │         │   Render     │         │   Supabase   │     │
│  │  (Frontend)  │────────▶│  (Backend)   │────────▶│  (Database)  │     │
│  │              │         │              │         │              │     │
│  │ Next.js      │         │ Python       │         │ PostgreSQL   │     │
│  │ React        │         │ FastAPI      │         │ + Auth       │     │
│  │ TypeScript   │         │ + n8n        │         │ + Storage    │     │
│  └──────────────┘         └──────────────┘         └──────────────┘     │
│         │                        │                        │              │
│         │                        │                        │              │
│  app.celeste7.ai      pipeline-core.int.       vzsohavtuotocgrfkfyd     │
│                         celeste7.ai             .supabase.co             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Vercel (Frontend)

| Item | Value |
|------|-------|
| URL | https://app.celeste7.ai |
| Framework | Next.js 14 |
| Deploy Trigger | Push to `main` branch |
| Build Command | `npm run build` |
| Output | `.next/` |
| Deploy Time | ~1-2 minutes |

**Dashboard**: https://vercel.com (need team access)

### Render (Backend)

| Item | Value |
|------|-------|
| URL | https://pipeline-core.int.celeste7.ai |
| Framework | Python FastAPI |
| Deploy Trigger | Push to `main` OR manual |
| Start Command | `uvicorn main:app` |
| Deploy Time | ~2-5 minutes |

**Services**:
- Python API (`/v1/*`) - Direct CRUD actions
- n8n Workflows (`/workflows/*`) - Complex multi-step pipelines

**Dashboard**: https://dashboard.render.com (need team access)

### Supabase (Database)

**Tenant DB** (yacht operations):
| Item | Value |
|------|-------|
| URL | https://vzsohavtuotocgrfkfyd.supabase.co |
| Tables | `pms_faults`, `pms_work_orders`, `pms_equipment`, `pms_audit_log`, `pms_documents` |
| RLS | Enabled on all tables |

**Master DB** (auth & fleet):
| Item | Value |
|------|-------|
| URL | https://qvzmkaamzaqxpzbewjxe.supabase.co |
| Tables | `fleet_registry`, `user_accounts`, `auth.users` |
| Purpose | Which user belongs to which yacht |

**Dashboard**: https://supabase.com/dashboard

### GitHub

| Item | Value |
|------|-------|
| Repo | https://github.com/shortalex12333/Cloud_PMS |
| Main Branch | `main` |
| CI/CD | GitHub Actions (if configured) |

---

## CI/CD Integration

### Current Flow

```
Developer pushes to main
         │
         ▼
┌─────────────────┐
│  GitHub Actions │ (if configured)
│  - Lint         │
│  - Type check   │
│  - Unit tests   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│     Vercel      │     │     Render      │
│  Auto-deploys   │     │  Auto-deploys   │
│  frontend       │     │  backend        │
└─────────────────┘     └─────────────────┘
```

### GitHub Actions (if exists)

Check `.github/workflows/` for workflow files.

Typical setup:
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm test
```

### Vercel Integration

- Connected to GitHub repo
- Auto-deploys on push to `main`
- Preview deploys on PRs
- Environment variables set in Vercel dashboard

### Render Integration

- Connected to GitHub repo
- May auto-deploy or require manual trigger
- Check Render dashboard for deploy settings
- Environment variables set in Render dashboard

---

## Common Errors & Solutions

### Error: "Failed to acknowledge fault"

**Cause**: Frontend calling wrong endpoint
```
WRONG: /workflows/update (n8n)
RIGHT: /v1/actions/execute (Python API)
```

**Fix**: Use `actionClient.executeAction()` not `useActionHandler`

### Error: "Could not find table in schema cache"

**Cause**: Wrong table name

**Fix**: Use `pms_` prefix. Tables are:
- `pms_faults` (not `faults`)
- `pms_audit_log` (not `audit_log`)
- `pms_work_orders` (not `work_orders`)

### Error: "Fault not found" (404)

**Cause**: Missing yacht_id in query

**Fix**: Add `.eq('yacht_id', yacht_id)` to every query

### Error: "signature cannot be null"

**Cause**: `pms_audit_log.signature` is NOT NULL

**Fix**: Include signature object:
```python
"signature": {
    "user_id": user_id,
    "execution_id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "action": "acknowledge_fault"
}
```

### Error: Test passes first time, fails second time

**Cause**: Fault already in target state (idempotent)

**Fix**: Reset fault at start of test:
```typescript
await supabase.from('pms_faults').update({ status: 'open' }).eq('id', FAULT_ID).eq('yacht_id', YACHT_ID);
```

### Error: Changes not reflected in production

**Cause**: Deployment not complete

**Fix**:
1. Check Vercel dashboard for frontend
2. Check Render dashboard for backend
3. Wait for deploy to finish
4. Hard refresh browser (Cmd+Shift+R)

---

## Key Files Reference

| Purpose | File |
|---------|------|
| Action definitions | `apps/web/src/types/actions.ts` |
| Workflow mappings | `apps/web/src/types/workflow-archetypes.ts` |
| API client (correct) | `apps/web/src/lib/actionClient.ts` |
| Server-driven UI hook | `apps/web/src/hooks/useActionDecisions.ts` |
| Fault card UI | `apps/web/src/components/cards/FaultCard.tsx` |
| Acknowledge modal | `apps/web/src/components/modals/AcknowledgeFaultModal.tsx` |
| Backend handlers | `apps/api/routes/p0_actions_routes.py` |
| E2E proof test | `tests/e2e/phase13_mutation_proof.spec.ts` |
| Evidence output | `verification_handoff/evidence/phase13/` |

---

## Quick Commands Cheat Sheet

```bash
# Navigate to project
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Set test credentials
export TENANT_SUPABASE_SERVICE_ROLE_KEY="your-key"

# Run Phase 13 test
npx playwright test tests/e2e/phase13_mutation_proof.spec.ts --reporter=list

# Run all tests
npx playwright test

# Build frontend
cd apps/web && npm run build

# Type check
cd apps/web && npm run typecheck

# View evidence
cat verification_handoff/evidence/phase13/P13_MUTATION_acknowledge_fault_proof.json
```

---

## Summary

**My purpose**: Verify production works with hard evidence.

**Current state**: Phase 13 `acknowledge_fault` PASS. Everything else untested.

**Next steps**: Test remaining mutations (update_fault, add_to_handover, etc.)

**Golden rule**: Evidence first, claims second. Never say DONE without proof file.
