# Part Lens v2 - Deployment Log

**Date**: 2026-01-28
**Branch**: `security/signoff`
**Commit**: `b0cacd3` (Direct SQL implementation)

---

## Deployment Strategy

### Phase 0: Branch Deployment
- **Target**: Staging API service
- **Source**: `security/signoff` branch (bypass main merge requirement)
- **Commit**: `b0cacd3` - "fix(part-lens): Bypass PostgREST with direct SQL"

### Changes Deployed
1. **TenantPGGateway** (`apps/api/db/tenant_pg_gateway.py`)
   - Direct psycopg2 connections to tenant databases
   - `get_part_stock()` for canonical pms_part_stock reads
   - Connection context manager with yacht_id filtering

2. **view_part_details Handler**
   - Replaced PostgREST `.table("pms_part_stock").select(...)` with direct SQL
   - Uses `get_part_stock(tenant_key_alias, yacht_id, part_id)`
   - Added `tenant_key_alias` parameter

3. **consume_part Handler**
   - Pre-check stock via SQL (409 if insufficient)
   - Wrapped RPC `deduct_stock_inventory` to handle 204
   - SQL confirmation query if RPC returns 204
   - Verification: `qty_after == qty_before - quantity`

4. **Router Updates**
   - Pass `tenant_key_alias` to both handlers
   - Tenant routing preserved from auth middleware

---

## Required Environment Variables (Staging)

### MASTER Database
```bash
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=<service_role_key>
MASTER_SUPABASE_JWT_SECRET=<jwt_secret>
MASTER_DB_PASSWORD=<postgres_password>
```

### TENANT_1 Database
```bash
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=<service_role_key>
yTEST_YACHT_001_DB_PASSWORD=<postgres_password>
```

---

## Deployment Steps (Manual - User Action Required)

### 1. Configure Render Staging
```
1. Go to: https://dashboard.render.com
2. Select: celeste-pipeline-v1 (staging)
3. Settings → Build & Deploy
4. Branch: Change from "main" to "security/signoff"
5. Click "Save"
6. Manual Deploy → "Deploy Latest Commit"
```

### 2. Verify Deployment
Wait 3-5 minutes for build, then test:

```bash
# Health check
curl https://pipeline-core.int.celeste7.ai/health

# Expected: 200 OK
```

### 3. Post-Deployment Verification
```bash
# Test low stock suggestions
curl -H "Authorization: Bearer $HOD_JWT" \
  https://pipeline-core.int.celeste7.ai/v1/parts/low-stock

# Test view_part_details
curl -X POST \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"view_part_details","context":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"},"payload":{"part_id":"8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3"}}' \
  https://pipeline-core.int.celeste7.ai/v1/actions/execute

# Expected: 200 with part details (no PostgREST 204)
```

---

## Acceptance Criteria

- [ ] Health endpoint returns 200
- [ ] view_part_details returns 200 (not 400/204)
- [ ] consume_part returns 200 for sufficient stock
- [ ] consume_part returns 409 for insufficient stock
- [ ] No 5xx errors in Render logs
- [ ] Render logs show: `[PGGateway] Connected to yTEST_YACHT_001`

---

## Rollback Plan

If deployment fails:
1. Render Dashboard → Build & Deploy → Branch: Change back to "main"
2. Manual Deploy → Deploy Latest Commit
3. Review errors in deployment logs
4. Fix issues on `security/signoff` branch
5. Retry deployment

---

## Timeline

- **Hour 0-1**: Deploy + health verification
- **Hour 1-2**: Storage RLS migration
- **Hour 2-4**: Core Acceptance (6/6 PASS)
- **Hour 4-5**: Stress tests
- **Hour 5-6**: Evidence bundle + CI gates
- **Post-Hour 6**: Merge to main → Enable 5% canary

---

## Notes

- PR creation skipped: `security/signoff` already contains commit `b0cacd3`
- Main branch already has equivalent changes via cherry-pick `c1dd4a9`
- No functional difference between branches at this commit
- Testing from `security/signoff` to validate before official merge
