# Render Environment Variables Setup

**Service**: `celeste-pipeline-v1` (pipeline-core.int.celeste7.ai)
**Purpose**: Configure MASTER→TENANT routing for Part Lens v2
**Status**: ⚠️ **ACTION REQUIRED**

---

## Problem

API was experiencing PostgREST 204 errors because it wasn't configured to connect to TENANT_1 database. The API uses `tenant_key_alias` from MASTER database's `fleet_registry` table to determine which TENANT database to connect to.

**Example flow**:
1. JWT contains yacht_id: `85fe1119-b04c-41ac-80f1-829d23322598`
2. API queries MASTER DB fleet_registry → finds `tenant_key_alias = "yTEST_YACHT_001"`
3. API looks for env vars: `yTEST_YACHT_001_SUPABASE_URL` and `yTEST_YACHT_001_SUPABASE_SERVICE_KEY`
4. Uses these to connect to TENANT_1 database for PMS operations

---

## Solution

Updated `render.yaml` with proper environment variable configuration (commit `a30bdcd`). Render will auto-redeploy, but **service keys must be set manually** in the Render Dashboard.

---

## Required Actions in Render Dashboard

Go to: https://dashboard.render.com/web/srv-[service-id]/env

### Set These Environment Variables

| Key | Value | Notes |
|-----|-------|-------|
| `MASTER_SUPABASE_SERVICE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q` | For fleet_registry lookups |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY` | For TENANT_1 PMS data |
| `SUPABASE_SERVICE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY` | Fallback (same as TENANT_1) |

### Steps

1. Go to Render Dashboard → `celeste-pipeline-v1` → Environment
2. Click "Add Environment Variable" for each key above
3. Paste the service key value
4. Click "Save Changes"
5. Wait for automatic redeploy (~3-5 minutes)

---

## Verification

After Render redeploys with the new environment variables, test consume_part:

```bash
cd /private/tmp/claude/-Volumes-Backup-CELESTE/6154729d-7aeb-45f6-a740-f9e2eea35f83/scratchpad
python3 test_consume_part.py
```

**Expected Results**:
- ✅ Sufficient stock → 200
- ✅ Insufficient stock → 409
- ✅ Zero PostgREST 204 errors

---

## Technical Details

### Fleet Registry Entry

```json
{
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "yacht_name": "M/Y Test Vessel",
  "tenant_key_alias": "yTEST_YACHT_001",
  "active": true
}
```

### TENANT_1 Database

- **Project Ref**: `vzsohavtuotocgrfkfyd`
- **URL**: https://vzsohavtuotocgrfkfyd.supabase.co
- **Schema**: pms_part_stock view, deduct_stock_inventory RPC, storage buckets (all verified ✅)

### MASTER Database

- **Project Ref**: `qvzmkaamzaqxpzbewjxe`
- **URL**: https://qvzmkaamzaqxpzbewjxe.supabase.co
- **Schema**: fleet_registry, auth_users_profiles, auth_users_roles

---

## Current Status

- ✅ render.yaml updated (commit a30bdcd)
- ✅ TENANT_1 migrations verified (pms_part_stock, deduct_stock_inventory, storage buckets)
- ✅ RPC works directly on TENANT_1 (tested successfully: 84 → 79)
- ⏸️ Awaiting Render env vars to be set
- ⏸️ Awaiting Render redeploy
- ⏸️ Awaiting consume_part test verification

**Timeline**: ~10 minutes after setting env vars in Render dashboard

---

**Prepared By**: Claude Sonnet 4.5
**Date**: 2026-01-28
**Commit**: a30bdcd
