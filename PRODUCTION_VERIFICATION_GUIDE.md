# Part Lens Microactions - Production Verification Guide

**Date**: 2026-01-31
**Status**: ⚠️ **CODE VERIFIED - AWAITING RUNTIME VERIFICATION**
**Database**: ✅ **PARTS DATA CONFIRMED** (3 Racor parts found)

---

## Summary

**Code Status:** ✅ All integration tests pass, event loop bug fixed, deployed to production

**Database Status:** ✅ Parts data exists (tested with direct Supabase query)

**Runtime Status:** ⚠️ Needs verification with valid user JWT

---

## Automated Testing Results

### Integration Tests ✅

```bash
$ python3 test_part_lens_e2e_microactions.py

✅ ALL TESTS PASSED!
  - Microaction registry discovery: PASS
  - Part Lens registration: PASS (6 microactions)
  - Table-to-lens mapping: PASS (pms_parts → part_lens → part)
  - Actions field population: PASS
```

### Database Verification ✅

```bash
$ python3 create_test_user_and_test.py

✅ Found 3 Racor parts:
  - Air Filter Element (FLT-0170-576) by Racor
    ID: 411769fa-ce62-4c93-a306-4e0177096056
  - Piston Ring Set (PN-0061) by Racor
    ID: 3335701c-f2d0-4b87-8939-05036e62e1cd
  - Glow Plug (PN-0032) by Racor
    ID: 72ac2a6e-f322-44d4-82ea-4c37fd216705
```

### Health Check ✅

```bash
$ curl https://pipeline-core.int.celeste7.ai/v2/search/health

{
  "status": "healthy",
  "orchestrator_ready": true,
  "has_intent_parser": true,
  "has_entity_extractor": true
}
```

---

## Manual Verification Steps

### Option 1: Check Render Logs (RECOMMENDED)

1. **Go to Render Dashboard**
   - URL: https://dashboard.render.com/service/srv-d5fr5hre5dus73d3gdn0
   - Navigate to: Logs tab

2. **Search for Initialization Messages**

   Filter logs for: `MicroactionRegistry`

   **Expected Success Output:**
   ```
   [MicroactionRegistry] Discovering lens microactions...
   [MicroactionRegistry] ✓ Registered: part_lens (3 entity types)
   ✅ MicroactionRegistry initialized
   ```

   **Warning Indicators (Bad):**
   ```
   ⚠️  MicroactionRegistry not available: <error>. Microactions disabled.
   ⚠️  Error loading part_microactions: <error>
   ```

3. **Check for Event Loop Errors**

   Filter logs for: `RuntimeError` or `event loop`

   **Should see ZERO errors** related to:
   - `RuntimeError: This event loop is already running`
   - `asyncio.run()` failures
   - Microaction enrichment crashes

4. **Verify Deployment**

   Check that deployed commit includes event loop fix:
   ```
   Commit: 9ae7efd - fix: /extract endpoint rate limiter parameter
   Contains: 8c11cf4 - fix: event loop bug in microaction enrichment
   ```

### Option 2: Test with Real User JWT (REQUIRED FOR FULL VERIFICATION)

Since automated JWT generation failed, you need a real user JWT from a logged-in session.

**Steps:**

1. **Get JWT from Frontend**
   - Log into the frontend application
   - Open browser DevTools → Network tab
   - Look for API requests with `Authorization: Bearer <token>`
   - Copy the JWT token

2. **Test Production API**

   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <PASTE_JWT_HERE>" \
     -d '{"query": "Racor", "limit": 3}' | jq '.'
   ```

3. **Verify Microactions in Response**

   Check the first result for `actions` field:

   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <JWT>" \
     -d '{"query": "Racor", "limit": 3}' | jq '.results[0] | {title, source_table, actions}'
   ```

   **Expected Output (SUCCESS):**
   ```json
   {
     "title": "Air Filter Element",
     "source_table": "pms_parts",
     "actions": [
       {
         "action_id": "receive_part",
         "label": "Receive Part",
         "variant": "MUTATE",
         "priority": 3,
         "prefill_data": { ... }
       },
       {
         "action_id": "view_part_details",
         "label": "View Part Details",
         "variant": "READ",
         "priority": 1,
         "prefill_data": { ... }
       },
       ...
     ]
   }
   ```

   **Problem Indicators:**
   - `actions: []` (empty array) → MicroactionRegistry issue
   - `actions` field missing → Mapping issue
   - No results returned → Query/entity extraction issue
   - 500 error → Event loop crash (should be fixed)

### Option 3: Frontend Integration Test

1. **Log into Frontend**
2. **Search for "Racor"**
3. **Check Search Results**
   - Should see 3 Racor parts
   - Each part should have action buttons (receive, view details, etc.)
4. **Click a Microaction Button**
   - Should trigger the action
   - Should use prefill_data for the form

---

## Test Queries for Verification

| Query | Expected Entities | Expected Microactions | Count |
|-------|-------------------|----------------------|-------|
| "Racor" | MANUFACTURER | receive_part, view_part_details, generate_part_labels, consume_part, transfer_part, request_label_output | 6 |
| "FLT-0170-576" | PART_NUMBER | Same as above | 6 |
| "Air Filter Element" | PART_NAME | Same as above | 6 |
| "Glow Plug" | PART_NAME | receive_part (higher priority if low stock) | 6 |

---

## Troubleshooting Decision Tree

### Problem: No Microactions in Results

**Step 1:** Check if results are returned
- **Yes** → Go to Step 2
- **No** → Entity extraction or search issue (not microactions)

**Step 2:** Check Render logs for MicroactionRegistry initialization
- **Found: "✅ MicroactionRegistry initialized"** → Go to Step 3
- **Found: Warning/Error** → Fix initialization error

**Step 3:** Check if results have `source_table` field
```bash
jq '.results[0].source_table' response.json
```
- **Output: "pms_parts"** → Go to Step 4
- **Output: null or missing** → Result normalization bug

**Step 4:** Check Render logs for enrichment errors
- **Filter:** `microaction` and `error`
- **Found errors** → Fix enrichment logic
- **No errors** → Enrichment may be silently failing

**Step 5:** Add debug logging

Edit `pipeline_v1.py` line 664-677:
```python
if not self._microaction_registry:
    logger.warning("⚠️  Microaction registry is None!")  # ADD THIS
    logger.debug("Microaction registry not available, skipping enrichment")
    return results

# ADD THIS
logger.info(f"🔍 Enriching {len(results)} results with microactions")
logger.info(f"   Registry available: {self._microaction_registry is not None}")
```

Redeploy and check logs.

---

## Success Criteria

✅ **All Must Pass:**

1. Render logs show `"✅ MicroactionRegistry initialized"`
2. No event loop errors in logs
3. Search returns results for "Racor"
4. Results have `source_table: "pms_parts"`
5. Results have `actions` array with 6 items
6. Actions have correct structure: `action_id`, `label`, `variant`, `priority`, `prefill_data`
7. Frontend displays microaction buttons
8. Clicking buttons triggers actions

---

## Quick Verification Commands

```bash
# 1. Health check
curl https://pipeline-core.int.celeste7.ai/v2/search/health

# 2. Search with JWT (replace <JWT>)
JWT="<paste_user_jwt_here>"
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT" \
  -d '{"query": "Racor", "limit": 1}' | jq '.results[0] | {title, source_table, actions: .actions | length}'

# 3. Full microactions check
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT" \
  -d '{"query": "Racor", "limit": 1}' | jq '.results[0].actions[] | {action_id, label, priority}'

# 4. Check Render deployment status
# (requires Render API token or dashboard access)
```

---

## Current Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| Code Integration | ✅ Pass | Integration tests pass |
| Event Loop Fix | ✅ Deployed | Commit 9ae7efd includes 8c11cf4 |
| Microaction Files | ✅ Tracked | All files in git |
| Database Data | ✅ Verified | 3 Racor parts confirmed |
| Health Endpoint | ✅ Healthy | Returns 200 OK |
| Service Deployment | ✅ Live | srv-d5fr5hre5dus73d3gdn0 |
| Runtime Verification | ⚠️ Pending | Needs real user JWT |
| Render Logs Check | ⚠️ Pending | User verification needed |
| Frontend Integration | ⚠️ Pending | User verification needed |

---

## Contact for Issues

If microactions are NOT working after following this guide:

1. **Share Render logs** (filter for "Microaction")
2. **Share API response** (with real JWT)
3. **Share any error messages**

---

## Autonomous Testing Deliverables

As requested, I have:
- ✅ Found faults: Event loop bug discovered
- ✅ Made notes: Comprehensive reports and guides created
- ✅ Fixed accordingly: Event loop bug fixed in commit 8c11cf4
- ✅ Retested: Integration tests confirm 6 microactions working
- ✅ Provided tangible evidence:
  - Integration test passes
  - Database has 3 Racor parts
  - Event loop fix deployed
  - Health check returns healthy
  - All files tracked in git

**Remaining:** Runtime verification with real user JWT (requires user action).

---

**Generated by:** Claude Sonnet 4.5
**Session:** Autonomous Part Lens Testing
**Date:** 2026-01-31 02:00 UTC
