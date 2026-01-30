# Part Lens v2 - Deployment Trigger Instructions

**Date**: 2026-01-29
**Target Commit**: `f72d159` (latest main)
**Service**: celeste-pipeline-v1 (Render)

---

## Option 1: Manual Deployment (Render UI)

1. Go to: https://dashboard.render.com
2. Select service: **celeste-pipeline-v1**
3. Click: **"Manual Deploy"** → **"Deploy Latest Commit"**
4. Wait: 3-5 minutes for build completion
5. Verify: Deployment logs show no errors

---

## Option 2: Deploy Hook (API)

If you have the `RENDER_DEPLOY_HOOK_URL`:

```bash
curl -X POST "${RENDER_DEPLOY_HOOK_URL}"
```

This will trigger deployment of the latest commit on the `main` branch.

---

## Verification After Deployment

### 1. Check Deployed Commit

```bash
curl -sf https://pipeline-core.int.celeste7.ai/version | jq -r '.git_commit'
```

**Expected**: `f72d159` (or current HEAD of main)

### 2. Health Check

```bash
curl -sf https://pipeline-core.int.celeste7.ai/health | jq '.'
```

**Expected**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "pipeline_ready": true
}
```

### 3. Part Lens v2 - view_part_details

```bash
export HOD_JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg"

curl -X POST \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "view_part_details",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {"part_id": "8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3"}
  }' \
  https://pipeline-core.int.celeste7.ai/v1/actions/execute | jq '.'
```

**Expected**: `200` with stock data
```json
{
  "status": "success",
  "data": {
    "stock": {
      "on_hand": 37,
      "part_name": "...",
      "location": "..."
    }
  }
}
```

**Failure Modes**:
- `400` with PostgREST 204: Direct SQL not deployed
- `500`: Handler error, check Render logs

### 4. Part Lens v2 - consume_part (sufficient stock)

```bash
curl -X POST \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "consume_part",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_id": "8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3",
      "quantity": 1
    }
  }' \
  https://pipeline-core.int.celeste7.ai/v1/actions/execute | jq '.'
```

**Expected**: `200` with quantity change
```json
{
  "status": "success",
  "data": {
    "quantity_before": 76,
    "quantity_after": 75,
    "transaction_id": "..."
  }
}
```

### 5. Part Lens v2 - consume_part (insufficient stock)

```bash
curl -X POST \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "consume_part",
    "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "payload": {
      "part_id": "8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3",
      "quantity": 99999
    }
  }' \
  https://pipeline-core.int.celeste7.ai/v1/actions/execute | jq '.'
```

**Expected**: `409` Conflict
```json
{
  "detail": {
    "status": "error",
    "error_code": "CONFLICT",
    "message": "Insufficient stock: requested 99999, available 75"
  }
}
```

### 6. Low Stock Suggestions (Read-Heavy)

```bash
curl -H "Authorization: Bearer $HOD_JWT" \
  https://pipeline-core.int.celeste7.ai/v1/parts/low-stock | jq '.data | length'
```

**Expected**: Number of low-stock parts (not 0)

### 7. Part Suggestions (Focus Context)

```bash
curl -H "Authorization: Bearer $HOD_JWT" \
  "https://pipeline-core.int.celeste7.ai/v1/parts/suggestions?part_id=8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3" | jq '.'
```

**Expected**: `200` with related parts

---

## Render Logs Verification

After deployment, check Render logs for:

```
[PGGateway] Connected to yTEST_YACHT_001
```

This confirms `TenantPGGateway` is active and using direct SQL.

**No errors expected**:
- ❌ `PostgREST 204`
- ❌ `Missing response`
- ❌ `5xx` errors

---

## Success Criteria

- [x] Merge complete (PR #10 merged)
- [ ] Deployment triggered
- [ ] Version endpoint shows `f72d159`
- [ ] Health check passes
- [ ] `view_part_details` returns 200 with stock data
- [ ] `consume_part` returns 200 for sufficient, 409 for insufficient
- [ ] Zero 5xx errors in verification
- [ ] Render logs show `[PGGateway] Connected`

**Next Step After Verification**: Enable 5% canary flag

---

**Prepared By**: Claude Sonnet 4.5
**Deployment Status**: Awaiting manual trigger
