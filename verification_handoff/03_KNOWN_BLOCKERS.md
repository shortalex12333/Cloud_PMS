# 03_KNOWN_BLOCKERS.md — Critical Blockers Registry

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Total Blockers:** 6 (1 cleared, 5 active)

---

## B001: Pipeline JWT Signature Mismatch

### Symptom
All requests to pipeline-core.int.celeste7.ai return 401:
```json
{"detail":"Invalid token: Signature verification failed"}
```

### Scope / Blast Radius
- **Search:** All semantic search broken
- **Bootstrap:** User context loading fails → users stuck in "pending" state
- **Actions:** Any microaction routed through pipeline fails
- **Estimated Impact:** 80%+ of product functionality

### Code Locations
| File | Line | Description |
|------|------|-------------|
| `apps/api/middleware/auth.py` | 33 | `MASTER_SUPABASE_JWT_SECRET = os.getenv(...)` |
| `apps/api/middleware/auth.py` | 57-58 | Warning if env var not set |
| `apps/api/middleware/auth.py` | 191 | JWT verification uses this secret |
| `apps/api/action_router/validators/jwt_validator.py` | 36-41 | Action router JWT validation |

### Evidence File
`evidence/E018_pipeline_401.json`

### Reproduction Steps
```bash
# 1. Login to get JWT
JWT=$(curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' | jq -r '.access_token')

# 2. Call bootstrap (should work, currently fails)
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json"
```

### Observed Error
```json
{"detail":"Invalid token: Signature verification failed"}
```

### Suspected Root Cause (Evidence-Based)
1. Supabase project has its own JWT secret (in project settings)
2. Render backend uses `MASTER_SUPABASE_JWT_SECRET` env var to verify
3. These are **different values**

**Evidence:**
- Code in `apps/api/middleware/auth.py:33` references `MASTER_SUPABASE_JWT_SECRET`
- Supabase JWTs decode correctly on jwt.io
- Backend returns "Signature verification failed" not "Malformed token"

### Fastest Fix Path
1. Go to Supabase Dashboard → Project Settings → API
2. Copy the JWT Secret
3. Go to Render Dashboard → Environment Variables
4. Set `MASTER_SUPABASE_JWT_SECRET` to the copied value
5. Redeploy Render service

### Acceptance Tests After Fix
```bash
# Test 1: Bootstrap returns yacht context
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer $JWT" | jq '.yacht_id'
# Expected: "85fe1119-b04c-41ac-80f1-829d23322598"

# Test 2: Search returns results
curl -s -X POST "https://pipeline-core.int.celeste7.ai/webhook/search" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"fuel filter"}'
# Expected: JSON array of search results, not 401
```

---

## B002: Missing PMS Tables

### Symptom
Microaction handlers fail with:
```
relation "pms_maintenance_schedules" does not exist
```

### Scope / Blast Radius
~15 microactions blocked:
- `schedule_maintenance`
- `create_certificate`
- `link_contract`
- `set_compliance_due`
- `update_schedule_template`
- And ~10 more

### Code Locations
| File | Line | Description |
|------|------|-------------|
| `apps/api/routes/p0_actions_routes.py` | 1278-1281 | Block for missing `pms_maintenance_schedules` |
| `apps/api/routes/p0_actions_routes.py` | 1294-1297 | Block for missing `pms_certificates`/`pms_service_contracts` |

### Missing Tables (Code References Found)
| Table | Referenced In | Purpose |
|-------|---------------|---------|
| `pms_maintenance_schedules` | `apps/api/routes/p0_actions_routes.py:1278` | Maintenance scheduling |
| `pms_certificates` | `apps/api/routes/p0_actions_routes.py:1294` | Equipment certifications |
| `pms_service_contracts` | `apps/api/routes/p0_actions_routes.py:1294` | Service contracts |
| `pms_schedule_templates` | handlers/*.py | Schedule templates |
| `pms_compliance_items` | handlers/*.py | Compliance tracking |

### Tables That DO Exist (Verified)
- `pms_work_orders` ✅ (E008)
- `pms_equipment` ✅ (E009)
- `pms_parts` ✅
- `pms_faults` ✅
- `pms_handover` ✅
- `pms_purchase_orders` ✅
- `pms_work_order_notes` ✅
- `pms_work_order_parts` ✅

### Reproduction Steps
```bash
# Try to query missing table
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_maintenance_schedules?select=id&limit=1" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
# Expected error: 404 or relation does not exist
```

### Suspected Root Cause
Migrations for these tables were not run, or tables are planned but not implemented.

### Fastest Fix Path
1. Check `supabase/migrations/` for migration files containing these tables
2. If migrations exist: Run `supabase db push` or apply via Supabase CLI
3. If migrations don't exist: Create them or mark dependent microactions as NOT_IMPLEMENTED

### Acceptance Tests After Fix
```bash
# For each missing table:
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/{table_name}?select=id&limit=1" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
# Expected: 200 OK (empty array is fine, no error)
```

---

## B003: Supabase Search RPC Signature Mismatch

### Symptom
Calling `unified_search_v2` RPC returns:
```
PGRST202 - Could not find function with parameters
```

### Scope / Blast Radius
- Fallback search when pipeline is unavailable
- Local ILIKE search works, but advanced features don't

### Code Locations
| File | Line | Description |
|------|------|-------------|
| `apps/api/execute/table_capabilities.py` | 251 | Comment: "RPC removed - unified_search_v2 doesn't exist" |
| `apps/api/execute/capability_executor.py` | 275 | RPC params build for unified_search_v2 |
| `apps/web/src/hooks/useCelesteSearch.ts` | 183-264 | Frontend search hook (uses pipeline, not RPC) |

### Evidence File
`evidence/E019_rpc_mismatch.json`

### Reproduction Steps
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/rpc/unified_search_v2" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"search_query":"fuel filter"}'
```

### Observed Error
```json
{
  "code": "PGRST202",
  "message": "Could not find the function public.unified_search_v2(search_query) in the schema cache"
}
```

### Suspected Root Cause
Code expects RPC with one signature, but DB has different signature or RPC doesn't exist.

**Evidence:** Code comment at `apps/api/execute/table_capabilities.py:251` says "RPC removed - unified_search_v2 doesn't exist with expected signature"

### Fastest Fix Path
1. List actual RPCs in Supabase: Dashboard → Database → Functions
2. Compare with code expectations in `apps/web/src/hooks/useCelesteSearch.ts`
3. Either: Update code to match actual RPC signature, OR create missing RPC

### Acceptance Tests After Fix
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/rpc/unified_search_v2" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"search_query":"fuel filter"}'
# Expected: Array of search results
```

---

## B004: Email UX Placement (NOT VERIFIED)

### Symptom
Email reportedly appears in sidebar navigation instead of as a surface under search.

### Scope / Blast Radius
- UX doctrine violation
- Users confused about where email is
- Inconsistent with "one URL" principle

### Reproduction Steps
1. Visit https://apps.celeste7.ai
2. Login as x@alex-short.com
3. Look for email in sidebar vs search results

### Observed Logs/Errors
**NOT COLLECTED** — Claude A did not visit production site

### Suspected Root Cause (UNVERIFIED)
Code may have email as separate route/page instead of search surface.

### Fastest Fix Path
1. **First:** Claude B must verify by visiting production site
2. If confirmed: Remove email from sidebar navigation
3. Ensure email search results appear in main search

### Acceptance Tests After Fix
1. Email NOT visible in sidebar navigation
2. Searching "email from John" shows email results in search
3. Clicking email result opens inline, not new page

---

## B005: add_to_handover ActionExecutionError (NOT VERIFIED)

### Symptom
Reported in prior context: `add_to_handover` action returns ActionExecutionError

### Scope / Blast Radius
- Handover write path broken
- Users cannot add items to handovers via UI

### Code Locations
| File | Line | Description |
|------|------|-------------|
| `apps/api/handlers/handover_handlers.py` | 40-222 | `add_to_handover_prefill` function |
| `apps/api/handlers/handover_handlers.py` | 229-377 | `add_to_handover_execute` function |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | 338-393 | `add_to_handover` dispatcher function |
| `apps/api/action_router/dispatchers/internal_dispatcher.py` | 1890 | Handler registration: `"add_to_handover": add_to_handover` |
| `apps/api/actions/action_registry.py` | 835-841 | Action definition in registry |
| `apps/api/actions/action_gating.py` | 73 | Action is in GATED_ACTIONS list |

### Reproduction Steps
1. Login to production
2. Navigate to handover context
3. Try to add item to handover
4. Observe error

### Observed Logs/Errors
**NOT COLLECTED** — Error was referenced but not captured

### Suspected Root Cause
Unknown. Possible causes:
- Handler throws error (check `handover_handlers.py:375`)
- Wrong table reference
- Missing yacht_id in payload
- RLS blocking write
- Action is GATED and requires confirmation flow

### Fastest Fix Path
1. Claude B must reproduce and capture full error
2. Check `apps/api/handlers/handover_handlers.py:229` for `add_to_handover_execute`
3. Verify handler is registered in `apps/api/action_router/dispatchers/internal_dispatcher.py:1890`
4. Check Render logs for stack trace

### Acceptance Tests After Fix
```bash
# API test
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "add_to_handover",
    "params": {"handover_id": "...", "summary": "Test item"}
  }'
# Expected: 200 OK with created item
```

---

## B006: Placeholder IDs in Code (VERIFIED - NO DANGEROUS PATTERNS)

### Symptom
Code may use placeholder UUIDs when yacht_id is null:
```javascript
const yachtId = user?.yachtId || '00000000-0000-0000-0000-000000000000';
```

### Scope / Blast Radius
- Silent data loss (RLS returns empty)
- Orphaned records in DB
- Impossible to debug (no errors logged)

### Evidence File
`evidence/B006_placeholder_search.txt`

### Search Results (VERIFIED 2026-01-19)
| Pattern | Result |
|---------|--------|
| `00000000-0000-0000-0000-000000000000` | **NO MATCHES** in `apps/web/src/` |
| `placeholder-yacht-id` | **NO MATCHES** |
| `placeholder-user-id` | **NO MATCHES** |
| Literal `"placeholder"` strings | 5 matches (all safe - see below) |

### Safe Placeholder Occurrences Found
| File | Line | Risk | Reason |
|------|------|------|--------|
| `apps/web/src/lib/supabaseClient.ts` | 15 | LOW | SSR guard - intentional dummy client |
| `apps/web/src/lib/supabaseClient.ts` | 83 | NONE | Code comment only |
| `apps/web/src/lib/supabaseClient.ts` | 106 | NONE | Code comment only |
| `apps/web/src/lib/microactions/confirmation.ts` | 44 | NONE | UI text templating comment |
| `apps/web/src/lib/supabase.ts` | 250 | NONE | Code comment only |

### Status
**✅ VERIFIED - NO DANGEROUS PATTERNS FOUND**

The SSR placeholder at `supabaseClient.ts:15` is expected behavior for server-side rendering and does not affect authenticated requests. Client is recreated with real values on client-side (line 57).

### Acceptance Tests (ALREADY PASSING)
1. ✅ Grep returns zero matches for all-zero UUID
2. ✅ Grep returns zero matches for placeholder-yacht-id
3. ✅ Grep returns zero matches for placeholder-user-id
4. Claude B should verify: With pending user (no yacht), "Awaiting activation" screen shown

---

## BLOCKER PRIORITY MATRIX

| ID | Severity | Effort | Priority | Status |
|----|----------|--------|----------|--------|
| B001 | CRITICAL | Low (env var) | **P0** | ACTIVE |
| B002 | HIGH | Medium (migrations) | P1 | ACTIVE |
| B003 | MEDIUM | Medium (RPC alignment) | P2 | ACTIVE |
| B004 | MEDIUM | Low (UI change) | P2 | NOT VERIFIED |
| B005 | MEDIUM | Unknown | P2 | NOT VERIFIED |
| B006 | ~~HIGH~~ | ~~Medium~~ | ~~P1~~ | ✅ CLEARED |

**Recommended Fix Order:** B001 → B002 → B003 → B004 → B005

**Note:** B006 has been cleared after systematic search found no dangerous placeholder patterns.

