# Stage 3 Handover — Actions, Mutations & Ledger
**Date:** 2026-03-15 | **Predecessor:** Stage 2 (Entity Lenses) | **Author:** Claude Code (review session)

---

## 1. Who We Are and What We're Building

**CelesteOS PMS** is a maritime yacht specific planned maintenance software. 

The foundational design principle: crew issue action-based natural language commands through a Spotlight search bar. The NLP pipeline interprets intent across domains and entities. (analogy: A PA opens all drawers at once. Everything — every test, every feature, every UI decision — flows from this.)

The product has three stages:

| Stage | What | Status |
|---|---|---|
| 1 — Search Pipeline | F1 SSE search, intent extraction, Cortex rewrites, RRF fusion | **Complete. Signed off.** |
| 2 — Entity Lenses | 12 entity types, 12 detail pages, /v1/entity/ endpoints, RouteShell | **Complete. Signed off.** |
| 3 — Actions / Mutations | 126 actions across 10 domains, audit trail, ledger | **~16% tested. Your work starts here.** |

---

## 2. Hardware and Local Environment

Mac Studio (~$4k capex). Zero cloud compute during staging. Zero monthly cost.
We hsot db in supabse, one master for authenticaion, the other is multi tenant with yacht specific. see "/env vars.md" file for credentials.
- We user local docker in replacemnt for render

**Project root:** `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/`
Not `/Volumes/Backup/CELESTE/` — that is the parent volume, not the repo.

```bash
# Start / manage containers
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
./celeste.sh start          # spin up all services
./celeste.sh health         # confirm healthy
./celeste.sh logs api       # tail API logs
./celeste.sh shell api      # exec into API container
```

**Running containers:**
| Container | Port | Notes |
|---|---|---|
| `celeste-api` | 8000 | FastAPI — healthy |
| `celeste-web-local` | 3000 | Next.js frontend |
| `celeste-projection` | — | unhealthy is normal (no health check) |
| `celeste-embedding` | — | unhealthy is normal |

**Mint a captain JWT when you get 401s** (tokens expire every ~2h):
```bash
docker exec celeste-api python3 -c "
import jwt, time, os, urllib.request, json
MASTER_URL = os.environ.get('MASTER_SUPABASE_URL', '')
MASTER_KEY = os.environ.get('MASTER_SUPABASE_SERVICE_KEY', '')
JWT_SECRET = os.environ.get('TENANT_SUPABASE_JWT_SECRET', '')  # NOTE: TENANT_ prefix
req = urllib.request.Request(
  f'{MASTER_URL}/rest/v1/user_accounts?yacht_id=eq.85fe1119-b04c-41ac-80f1-829d23322598&status=eq.active&limit=1'
)
req.add_header('apikey', MASTER_KEY); req.add_header('Authorization', f'Bearer {MASTER_KEY}')
u = json.loads(urllib.request.urlopen(req, timeout=10).read())[0]
token = jwt.encode({'sub': u['id'], 'aud': 'authenticated', 'role': 'authenticated',
  'iss': 'supabase', 'iat': int(time.time()), 'exp': int(time.time()) + 7200, 'email': u['email']},
  JWT_SECRET, algorithm='HS256')
open('/tmp/jwt_token.txt', 'w').write(token)
print('Minted for', u['email'])
"
```

**Test credentials:**
- Email: `x@alex-short.com`, role: `captain`
- User UUID: `a35cad0b-02ff-4287-b6e4-17c96fa6a424` (master DB sub)
- Yacht ID: `85fe1119-b04c-41ac-80f1-829d23322598`
- Tenant alias: `yTEST_YACHT_001`

---

## 3. Two-Database Architecture (Critical)

Every request touches two Supabase projects. **Never mix them up.**

| Variable | Project ID | Purpose |
|---|---|---|
| `MASTER_SUPABASE_URL` | `qvzmkaamzaqxpzbewjxe` | Auth, who you are, tenant lookup |
| `SUPABASE_URL` (tenant) | `vzsohavtuotocgrfkfyd` | All PMS data — entities, ledger, audit, actions |

**Connection:** Direct `:5432`, NOT the Supavisor pooler (doesn't work for this tenant).

Flow: JWT validated against master → `get_my_bootstrap` RPC → resolves `yacht_id` and `tenant_key_alias` → tenant DB queried with service key → **API enforces row isolation via `.eq('yacht_id', yacht_id)` on every query** (not Supabase RLS).

---

## 4. Stage 1 Summary (Search Pipeline — Done)

- F1 SSE search endpoint: `apps/api/routes/f1_search_streaming.py`
- Cortex query preprocessing: `apps/api/cortex/rewrites.py`
- Signal router (entity→target mapping): `apps/api/services/signal_router.py`
- 75-query ground truth suite: 93.3% L1 @3 pass rate, 92% overall @3
- Latency: 1.4s avg (was 8–10s)

**Do not touch the search pipeline.** The NLP is sufficient. Issues in downstream stages are display or mapping bugs, not pipeline bugs.

---

## 5. Stage 2 Summary (Entity Lenses — Done)

- 12 entity types with individual route pages at `/work-orders/{id}`, `/faults/{id}`, etc.
- `RouteShell.tsx` — unified fetch wrapper, calls `GET /v1/entity/{type}/{id}`, renders appropriate LensContent component
- `entity_routes.py` — all 12 `/v1/entity/` endpoints consolidated here
- `HistorySection` and `AttachmentsSection` wired into all entity lens pages
- **Fragmented routes are the canonical architecture.** ContextPanel/LensRenderer is deprecated. Do not build on it.
- `FeatureFlagGuard` was removed — it was silently redirecting all 14 entity pages

**Stage 2 known gaps carried into Stage 3:**
- `warranty` and `worklist` lenses: frontend scaffolding exists, no backend handler, no DB seed data. **Decide scope before touching.**
- `file_size` in `pms_attachments` is not populated by actual uploads (only seeded rows have it). Deferred.
- `handover` and `shopping_list` have type mismatches in `search_index` vs what lenses expect.

---

## 6. Stage 3 Current Status (Your Starting Point)

**126 registered actions** in `apps/api/action_router/registry.py`.
**20 actions tested** in shard-33 + shard-34 E2E suites. **106 actions untested.**

### What shard-33 tests (smoke layer)
- Render: does the entity page load without crashing?
- Basic action: does the action return 200 + DB state changed?
- Coverage: faults, work orders, equipment, inventory, documents, certificates
- Pattern: `callAction` via browser localStorage session JWT

### What shard-34 tests (hard proof layer)
- Three-layer verification: JSON response + ledger_events poll + DB state mutation
- Coverage: same 6 domains, specific actions only
- Pattern: `callActionDirect` (captain JWT) and `callActionAs` (explicit JWT for RBAC)

### Tested actions (20/126):
`acknowledge_fault`, `add_document_tags`, `add_equipment_note`, `add_fault_note`, `add_wo_note`, `assign_work_order`, `cancel_work_order`, `check_stock_level`, `close_fault`, `close_work_order`, `create_vessel_certificate`, `log_part_usage`, `reopen_fault`, `start_work_order`, `supersede_certificate`, `transfer_part`, `update_certificate`, `update_document`, `update_equipment_status`, `upload_document`

### Entirely untested domains:
- **Handover** (8 actions) — `handover_handlers.py`, `handover_workflow_handlers.py`
- **Hours of Rest** (6 actions) — `hours_of_rest_handlers.py`
- **Receiving** (9 actions) — `receiving_handlers.py`
- **Shopping List** (5 actions) — `shopping_list_handlers.py`
- **Warranty / Purchasing** (10 actions) — `p1_compliance_handlers.py`, `p1_purchasing_handlers.py`
- **Parts write-off / adjust** (3 actions) — `part_handlers.py`
- **HistorySection / LedgerPanel UI rendering** — never tested via Playwright (all tests call API directly)

---

## 7. Known Broken / Deferred Items (Do Not Trust the Reports)

These were caught during shard-33/34 review. Do not mark them "done" — they are not.

| Issue | Location | Status |
|---|---|---|
| `update_document` writes no DB row | `document_handlers.py:422` | Broken by design — handler only logs intent. Must be fixed before shipping. |
| `reopen_fault` writes no `ledger_events` row | `p0_actions_routes.py` via `internal_dispatcher` | Audit gap. File a fix. |
| `add_fault_note` writes no `ledger_events` row | Handler only updates `metadata.notes` | Audit gap. File a fix. |
| `transfer_part` ledger `entity_id` = nil UUID | Action not in `_ACTION_ENTITY_MAP` in p0 | Audit gap — every part transfer records nil UUID. Add to map. |
| `update_equipment_status` → 500 | Triggers WO status update with `'closed'` which fails `work_order_status` CHECK constraint | DB bug in handler. Advisory test passes; fix is in the handler. |
| `supersede_certificate` accepts 200 as advisory | `certificate-actions-full.spec.ts` | If 200 returns without signature, the test passes — this is a security bypass not caught. Change to `expect([400, 403])` only. |

---

## 8. E2E Test Setup and Running

### CRITICAL: Source `.env.e2e` before running tests

`SESSION_JWT = generateFreshJwt()` runs at **module load time** in `shard-34/helpers.ts`. If `SUPABASE_JWT_SECRET` is not set, the entire test suite crashes before a single test runs. The run command in shard-34's handoff document omits this — it is wrong. The correct command:

```bash
cd apps/web
source .env.e2e
E2E_BASE_URL=http://localhost:3000 NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=1 npx playwright test --project=shard-33-lens-actions

# Or shard-34:
source .env.e2e && E2E_BASE_URL=http://localhost:3000 NEXT_PUBLIC_API_URL=http://localhost:8000 \
  E2E_NO_SERVER=1 npx playwright test --project=shard-34-lens-actions
```

### JWT naming mismatch (common confusion)

| Context | Variable name |
|---|---|
| Tests (`apps/web/.env.e2e`) | `SUPABASE_JWT_SECRET` |
| API container env | `TENANT_SUPABASE_JWT_SECRET` |
| Service role for admin queries | `SUPABASE_SERVICE_KEY` (tests) / `SUPABASE_SERVICE_ROLE_KEY` (container) |

The values are the same secret — the names differ. Don't confuse them.

### RBAC test pattern (mandatory)

**NEVER use the advisory pattern.** It was deleted. Never reintroduce it.
```typescript
// BANNED — always passes, proves nothing:
expect([200, 403]).toContain(result.status);

// CORRECT — skip until crew user exists, then assert hard:
const crewUserId = await getCrewUserId(); // throws SKIP: if no crew user in DB
const crewJwt = generateFreshJwt(crewUserId, 'e2e-crew@celeste.internal');
const result = await callActionAs(crewPage, crewJwt, action, payload);
expect(result.status).toBe(403);
expect((result.data as { error_code?: string }).error_code).toBe('FORBIDDEN');
```

**19 active crew users exist** in `auth_users_roles` for yacht `85fe1119-...`. `getCrewUserId()` will NOT skip — it will return a real UUID and the RBAC test will fire.

### Which `error_code` the API returns for 403

The API has two RBAC check paths. Which fires depends on whether the action is in the registry with `allowed_roles`:

| Path | Condition | `error_code` |
|---|---|---|
| Universal registry check | Action in `registry.py` with `allowed_roles` set | `FORBIDDEN` |
| Domain-specific check (`FAULT_LENS_ROLES`, `WORK_ORDER_LENS_ROLES`) | Action NOT in registry with `allowed_roles` | `INSUFFICIENT_PERMISSIONS` |

Most core actions (`acknowledge_fault`, `close_fault`, `add_wo_note`, etc.) are in the registry → `FORBIDDEN`.

### Three-layer verification (non-negotiable for every shard-34 test)

```typescript
// 1. JSON response
expect(result.status).toBe(200);
expect(data.status).toBe('success');

// 2. Ledger
await pollLedger(supabaseAdmin, 'action_name', entityId, testStart);

// 3. DB state
await expect.poll(async () => {
  const { data: row } = await supabaseAdmin.from('pms_table')
    .select('field').eq('id', entityId).single();
  return row?.field;
}, { intervals: [500, 1000, 1500], timeout: 8_000 }).toBe('expected_value');
```

`pollLedger` is in `shard-34/helpers.ts` — import it, don't redefine it in each spec file.

---

## 9. Architecture Pitfalls and Contradictions

These will waste your time if you don't know them upfront.

### 9.1 Two certificate tables — always confuse people

| Table | Used by | UUID space |
|---|---|---|
| `pms_certificates` | `entity_routes.py` — GET /v1/entity/certificate/{id} | Separate |
| `pms_vessel_certificates` | `certificate_handlers.py` — action handlers (update, supersede) | Separate |

They are **different tables with different UUIDs**. `getExistingCertificate()` in fixtures queries `pms_certificates`. `getExistingVesselCertificate()` queries `pms_vessel_certificates`. If you use the wrong fixture for the wrong test, you get 404 from a handler that queries the other table.

**Crew certificates** are a third concept — `pms_crew_certificates` — for individual crew member certs (STCW, etc). Different again.

### 9.2 Two audit systems — not interchangeable

| System | Table | Written by | Purpose |
|---|---|---|---|
| Structured audit | `pms_audit_log` | Every handler directly | WHO changed WHAT with OLD/NEW values |
| Event stream | `ledger_events` | `p0_actions_routes.py` centrally | SHA-256 hashed immutable event chain |

Some actions write to both. Some only to `pms_audit_log`. `reopen_fault` and `add_fault_note` write to neither's `ledger_events` (known gap). Tests poll `ledger_events` — if an action doesn't write there, the test must skip the ledger poll and document the gap.

### 9.3 `_ACTION_ENTITY_MAP` in p0 — the ledger entity_id bug

`p0_actions_routes.py` has `_ACTION_ENTITY_MAP` which maps action names to the payload field that contains the entity UUID (e.g., `'close_fault': 'fault_id'`). If an action isn't in this map, the centralized ledger write fires with `entity_id = '00000000-0000-0000-0000-000000000000'` (nil UUID). The ledger row exists but is useless for entity-specific queries. `transfer_part` has this bug. Always check if new actions are in the map.

### 9.4 `action_router/registry.py` is source of truth — not `lens_matrix.json`

`lens_matrix.json` is superseded. It was the original configuration source, but `registry.py` now defines all 126 actions declaratively with `allowed_roles`, `required_fields`, `field_metadata`, etc. When there's a conflict, `registry.py` wins.

### 9.5 `callAction` (shard-33) vs `callActionDirect` / `callActionAs` (shard-34)

| Function | JWT source | When to use |
|---|---|---|
| `callAction` | Browser localStorage (Supabase session) | Shard-33 smoke tests where the page is already logged in |
| `callActionDirect` | `SESSION_JWT` (captain) | Shard-34 positive path (HOD/Captain hard proof) |
| `callActionAs(page, jwt, ...)` | Explicit JWT param | RBAC tests — crew or HOD-specific assertions |

Supabase clears self-minted tokens from localStorage on page load. For RBAC tests that need a specific role, you must use `callActionAs` — the browser session is always captain regardless of which page fixture you use.

### 9.6 `callAction` sends `context: { yacht_id }` — not `payload: { yacht_id }`

The API contract:
```json
{ "action": "...", "context": { "yacht_id": "..." }, "payload": { ... } }
```
The old version of shard-33's `callAction` put `yacht_id` inside `payload`. This was fixed. If you write new action call code, `yacht_id` goes in `context`, not `payload`.

### 9.7 `.single()` throws on 0 rows — use `.maybe_single()`

In `supabase-py`:
- `.single()` — throws exception if 0 rows → 500 Internal Server Error
- `.maybe_single()` — returns `None` if 0 rows → handle as 404

Three entity endpoints were shipping with `.single()` in Stage 2. They were fixed to `.maybe_single()`. Check every new handler you write.

### 9.8 `dict.get(key, default)` does NOT catch explicit `None`

```python
# DB returns {"name": None} — this does NOT use the default:
data.get("name", "Unknown Part")  # returns None

# This DOES use the fallback when DB returns None:
data.get("name") or "Unknown Part"
```
Use `or` fallback for DB fields that might be explicitly `None`, not the default argument.

### 9.9 `NODE_ENV` is always `'production'` during Next.js builds

```javascript
// WRONG — NODE_ENV is 'production' in docker builds:
const isDev = process.env.NODE_ENV === 'development';

// CORRECT — check the API URL instead:
const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
const isLocal = apiUrl.startsWith('http://localhost') || apiUrl.startsWith('http://127.0.0.1');
```

### 9.10 `NEXT_PUBLIC_*` variables bake at build time

These are compiled into the JS bundle during `next build`. They are NOT injectable at runtime via Docker env vars. If you add a new `NEXT_PUBLIC_` variable, it must be in `apps/web/Dockerfile` as an `ARG`/`ENV` declaration AND passed to `docker compose` — otherwise it's `undefined` in the running container.

---

## 10. How the Action Router Actually Works (Read Before Touching)

`POST /v1/actions/execute` in `p0_actions_routes.py` is 307KB. The order of operations:

1. JWT validation → extract `user_id`, `yacht_id`
2. **Universal RBAC check** against `registry.py` `allowed_roles` → returns `error_code: "FORBIDDEN"` if denied
3. **Domain-specific RBAC** (`FAULT_LENS_ROLES`, `WORK_ORDER_LENS_ROLES`, etc.) → returns `error_code: "INSUFFICIENT_PERMISSIONS"`
4. Signature validation (if `requires_signature`)
5. Dispatch to handler (`internal_dispatcher` or direct function call)
6. **Centralized ledger write** (using `_ACTION_ENTITY_MAP` for entity_id)
7. Return response

If an action is in the registry with `allowed_roles`, the universal check (step 2) fires and catches it. If not, it falls through to domain-specific (step 3). This determines which `error_code` your test should assert.

---

## 11. Skills and Plugins to Use

This project uses GSD (planning) + superpowers (discipline enforcement).

### Start every session:
```
/gsd:progress
```
This tells you where you are, what phase you're in, and routes you to the right action.

### Before implementing anything:
```
/gsd:plan-phase N
```
Do not write code without an approved plan. The CLAUDE.md is explicit: never implement directly from natural language.

### Before claiming anything is done:
The `superpowers:verification-before-completion` skill is loaded. Follow it. The iron law:
```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```
A 200 response is not a pass. DB mutation + audit log + ledger event + HistorySection rendering — all four, every time.

The rule about **two independent sources agreeing**:
> A 200 with wrong data is harder to catch than a 500. Errors are loud. Wrong data is silent.
> Always confirm two independently observable facts agree before claiming pass.

This was written into the skill because fabricated seed data (size_bytes: 245678 vs actual 334 bytes) passed the API check but failed on fetching the signed URL.

### For RBAC testing specifically:
`superpowers:test-driven-development` — write the test that asserts 403, run it red (it will 200 because SESSION_JWT is captain), then implement the fix, run it green.

### When hitting unexpected failures:
`superpowers:systematic-debugging` — do not guess, do not retry the same thing. Diagnose with evidence.

### For independent tasks (e.g., test multiple domains in parallel):
`superpowers:dispatching-parallel-agents` — shard-34 tests across 6 domains were written in parallel; use the same approach for HOR, receiving, shopping list.

---

## 12. Execution Order for the Remaining 106 Actions

Start with highest daily operational value:

1. **Remaining work order mutations** — `add_note_to_work_order`, `add_part_to_work_order`, `mark_work_order_complete`, `create_work_order_from_fault`, `reassign_work_order`, `archive_work_order`
2. **Remaining fault mutations** — `update_fault`, `diagnose_fault`, `mark_fault_false_alarm`, `report_fault`
3. **Parts write-off and adjust** — `adjust_stock_quantity` (signed), `write_off_part`, `consume_part`, `receive_part`
4. **Equipment completions** — `create_work_order_for_equipment`, `decommission_equipment` (signed), `flag_equipment_attention`, `archive_equipment`
5. **Fix broken actions** — `update_document` (no-op handler), `update_equipment_status` (WO enum bug), ledger gaps for `reopen_fault` + `add_fault_note` + `transfer_part`
6. **HistorySection UI verification** — for every fixed action, verify the entry appears rendered in the browser lens, not just in the DB
7. **Receiving domain** — `create_receiving` through `reject_receiving`
8. **Shopping list domain** — `create_shopping_list_item` through `promote_candidate_to_part`
9. **Hours of Rest** — `upsert_hours_of_rest`, `sign_monthly_signoff` (MLC 2006 compliance)
10. **Handover domain** — `sign_handover_incoming/outgoing` are signed actions — test the full signing flow
11. **Warranty** — assess scope with user before implementing (no DB data, may be out of scope)
12. **LedgerPanel full E2E** — verify every domain's mutations appear in the ledger timeline UI

---

## 13. Repository Discipline

- **Never commit credentials** — `.env`, `.env.e2e`, service keys
- **Never commit `.swarm/`** — ephemeral session state, in `.gitignore`
- **No version suffixes** — no `_v2`, `_final`, `_old`. Git handles versioning.
- **One canonical location per concept** — if you find `stage3.md` and `stage3_notes.md` both existing, consolidate. This document supersedes both.
- **Commit messages explain WHY** — not "fix bug" but "fix: certificate 500 — entity endpoint queried non-existent table pms_vessel_certificates instead of pms_certificates"
- **TypeScript must stay 0 errors** — `cd apps/web && npx tsc --noEmit` before every commit
- **API imports must stay clean** — `docker exec celeste-api python3 -c "from pipeline_service import app"` before every commit

---

## 14. The Ledger Is Not Optional

Maritime operations run on accountability. Who changed the engine status, who consumed the last spare filter, who signed off rest hours at 0200. If mutations fire without writing to `pms_audit_log` and `ledger_events`, the data exists but cannot be trusted.

Stage 3 is not "add action buttons." It is "make the system auditable."

MLC 2006 and ISM Code compliance require that every crew state change be logged, timestamped, and attributable to a named individual. The audit trail is a regulatory requirement, not a nice-to-have.

---

## 15. Reference Files

| File | Purpose |
|---|---|
| `apps/api/routes/p0_actions_routes.py` | All action endpoints (307KB) |
| `apps/api/action_router/registry.py` | Source of truth for all 126 actions |
| `apps/api/handlers/` | Domain-specific mutation handlers (11 files) |
| `apps/api/routes/ledger_routes.py` | Ledger read/write |
| `apps/api/routes/entity_routes.py` | All 12 GET /v1/entity/ endpoints |
| `apps/web/src/components/lens/RouteShell.tsx` | Unified fetch wrapper for all lens pages |
| `apps/web/src/components/lens/sections/HistorySection.tsx` | Per-entity audit history in lens |
| `apps/web/src/components/ledger/LedgerPanel.tsx` | Full ledger UI panel |
| `apps/web/e2e/rbac-fixtures.ts` | All Playwright fixtures including `getCrewUserId`, `seedFault`, etc. |
| `apps/web/e2e/shard-34-lens-actions/helpers.ts` | `generateFreshJwt`, `callActionAs`, `pollLedger` |
| `apps/web/.env.e2e` | Test secrets — source before running Playwright |
| `docs/STAGE_2_HANDOVER.md` | Stage 2 sign-off and per-lens status |
| `docs/stage3_notes.md` | Initial Stage 3 briefing (architecture overview) |
| `docs/superpowers/agents/` | Per-lens DATA.md and VERIFY.md checklists |
