# Quick Start - Post-Deployment Testing

## 1. Deploy Changes

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
git add apps/api/orchestration/prepare_module.py
git add apps/api/routes/orchestrated_search_routes.py
git commit -m "Fix inventory lens blockers: parts routing + context + actions

- Added parts/faults query builders to hybrid retrieval (prepare_module.py)
- Added context metadata and actions array to /v2/search (orchestrated_search_routes.py)
- Verified parity across /v1/search, /v2/search, and /search endpoints
- All endpoints now include context + actions filtered by role
- Inventory domain consistently normalized to parts

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main
```

Wait for Render to deploy (check: https://dashboard.render.com)

## 2. Obtain Fresh JWT Tokens

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
python3 test_artifacts/obtain_jwt_tokens.py
```

Expected output:
```
Obtaining JWT for crew...
✓ crew: eyJhbGciOiJIUzI1NiIsInR5cC...
Obtaining JWT for hod...
✓ hod: eyJhbGciOiJIUzI1NiIsInR5cC...

✓ Tokens saved to: /private/tmp/claude/.../scratchpad/test_user_tokens.json
```

## 3. Run All Parity Tests

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api
bash test_artifacts/inventory/parity/run_all_parity_tests.sh
```

This runs 3 test suites:
1. **Suggestions contract** - Verifies /v1/actions/list role filtering
2. **Action execution** - Verifies error mapping and role gating
3. **Endpoint parity** - Compares /v1/search, /v2/search, /search

## 4. Verify Results

### Expected: All GREEN

```
✅ PASS: HOD can see check_stock_level
✅ PASS: Crew cannot see log_part_usage (forbidden)
✅ PASS: HOD can see log_part_usage
✅ PASS: Crew only has READ actions
✅ PASS: HOD has both READ and MUTATE actions
✅ PASS: HOD has more actions than crew

✅ PASS: Invalid part_id returns 4xx (not 500)
✅ PASS: Crew forbidden from MUTATE action (403)
✅ PASS: HOD authorized for MUTATE action (200/404)

✅ PASS: All endpoints return parts for inventory queries
✅ PASS: All endpoints include context metadata
✅ PASS: All endpoints include actions array
```

### Check Response Files

```bash
cd test_artifacts/inventory/parity

# View suggestions contract results
cat hod_check_stock.json | jq '.actions[] | {action_id, variant}'

# View endpoint parity results
cat v2_crew_parts_low_in_stock.json | jq '{context, actions: .actions | length, first_result: .results[0].domain}'

# View action execution results
cat hod_mutate_response.json | jq '{status, error}'
```

## 5. Manual Smoke Test

Test one query per endpoint to verify end-to-end:

```bash
# Get fresh token
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/.../scratchpad/test_user_tokens.json)

# Test /v2/search
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  "https://pipeline-core.int.celeste7.ai/v2/search" \
  -d '{"query_text":"parts low in stock"}' | jq '{
    context: .context.domain,
    actions: .actions | length,
    first_result: .results[0].domain
  }'

# Expected output:
# {
#   "context": "parts",
#   "actions": 2,
#   "first_result": "parts"
# }
```

## 6. Troubleshooting

### JWT Token Expired
```bash
python3 test_artifacts/obtain_jwt_tokens.py
```

### Tests Failing
1. Check response files in `test_artifacts/inventory/parity/`
2. Look for error messages
3. Verify deployment completed: `curl https://pipeline-core.int.celeste7.ai/health`

### Network Issues
```bash
# Verify API is reachable
curl -sS "https://pipeline-core.int.celeste7.ai/health"

# Expected: {"status":"healthy","version":"1.0.0","pipeline_ready":true}
```

## 7. What to Look For

### ✅ GOOD
- Context includes `"domain": "parts"`
- Actions array has 2+ items for crew, 8+ for HOD
- Results have `"domain": "parts"` (not "work_orders")
- Action variants: crew=READ only, HOD=READ+MUTATE

### ❌ BAD
- Context missing or null
- Actions array empty or null
- Results have `"domain": "work_orders"` for parts queries
- Crew can see MUTATE actions (403 should block)
- Invalid part_id returns 500 (should be 404)

## Files Modified

- `apps/api/orchestration/prepare_module.py` (lines 256-264)
- `apps/api/routes/orchestrated_search_routes.py` (multiple sections)

## Files to Review

- `test_artifacts/inventory/FINAL_REPORT.md` - Comprehensive analysis
- `test_artifacts/inventory/parity/*.json` - Test results

## Production API

**Base URL**: https://pipeline-core.int.celeste7.ai

**Endpoints**:
- `/v1/search` - GraphRAG search with cards + actions
- `/v2/search` - Orchestrated search (my fixes)
- `/search` - Fusion search with action surfacing
- `/v1/actions/list` - Action suggestions by domain + role
- `/v1/actions/execute` - Action execution with role gating
