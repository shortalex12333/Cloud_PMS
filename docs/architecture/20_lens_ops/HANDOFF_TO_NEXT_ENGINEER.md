# Handoff to Next Engineer: Lens Ops Template

**Date:** 2026-01-28
**From:** Claude (Phase 1 Canary Deployment)
**To:** Next Engineer
**Status:** ✅ Template Complete, Ready for Deployment

---

## What Was Accomplished

You are receiving a **production-grade Lens Ops Template** that transforms ad-hoc canary scripts into automated, auditable infrastructure. This was built during Fault Lens v1 Phase 1 canary deployment.

**Problem Solved:**
- Manual health checks every 1-2 hours (unsustainable)
- No audit trail (who checked what when)
- Not repeatable (tribal knowledge in scripts)
- Doesn't scale (20 lenses × 4 phases = 80 manual interventions)

**Solution Delivered:**
- Automated health monitoring (Render background workers)
- CI-driven acceptance tests (GitHub Actions)
- Evidence-driven testing (raw HTTP transcripts, percentiles)
- Reusable templates (instantiate any lens in < 5 minutes)

---

## Folder Structure (Where Everything Is)

```
docs/architecture/20_lens_ops/          ← YOU ARE HERE
│
├── HANDOFF_TO_NEXT_ENGINEER.md                  ← This file (start here)
├── create_lens_ops_template.py                  ← Generator script ⭐
│
├── templates/                                    ← Template files (source)
│   ├── health_worker_template.py                ← Render background worker
│   ├── acceptance_test_template.py              ← CI acceptance tests
│   └── stress_test_template.py                  ← CI stress tests
│
├── migrations/                                   ← DB schema
│   └── ops_health_tables.sql                    ← Health monitoring tables
│
├── docs/                                         ← Documentation
│   ├── README.md                                 ← Complete guide (read this)
│   ├── PRODUCTIONIZATION_SUMMARY.md             ← Executive summary
│   └── EVIDENCE_TEMPLATE.md                     ← Evidence structure
│
└── examples/                                     ← Dry-run example
    └── parts_lens_example/                       ← Generated "Parts Lens v2"
        ├── tools/ops/monitors/parts_health_worker.py
        ├── tests/ci/parts_signed_flow_acceptance.py
        ├── tests/stress/parts_actions_endpoints.py
        ├── .github/workflows/parts-staging-acceptance.yml
        ├── .github/workflows/parts-stress.yml
        └── docs/pipeline/PARTS_FEATURE_FLAGS.md
```

**Key Insight:** The `examples/parts_lens_example/` folder shows you exactly what the generator produces. Review these files to understand the output before generating for real lenses.

---

## Your Mission (What to Build Next)

### Phase A: Deploy Lens Ops for Fault Lens v1 (Immediate)

**Goal:** Replace manual monitoring with automated health worker for Fault Lens v1

**Steps:**

#### 1. Apply DB Migration

**Why:** Health workers need `pms_health_checks` and `pms_health_events` tables

**Command:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Apply to staging
psql $STAGING_DB_URL < docs/architecture/20_lens_ops/migrations/ops_health_tables.sql

# Verify tables created
psql $STAGING_DB_URL -c "\\dt pms_health*"
```

**Expected Output:**
```
 pms_health_checks | table | postgres
 pms_health_events | table | postgres
```

**Verification:**
```sql
-- Test RLS policies
SELECT * FROM pms_health_checks WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
-- Should return empty (no checks yet)
```

---

#### 2. Generate Faults Lens Files

**Why:** Create production files from templates

**Command:**
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

python3 docs/architecture/20_lens_ops/create_lens_ops_template.py \
  --lens-id faults \
  --domain faults \
  --feature-flags FAULT_LENS_V1_ENABLED,FAULT_LENS_SUGGESTIONS_ENABLED,FAULT_LENS_SIGNED_ACTIONS_ENABLED \
  --roles crew,chief_engineer,chief_officer,captain,manager \
  --yacht-id 85fe1119-b04c-41ac-80f1-829d23322598 \
  --hod-user-id 05a488fd-e099-4d18-bf86-d87afba4fcdf \
  --crew-user-id 57e82f78-0a2d-4a7c-a428-6287621d06c5 \
  --captain-user-id c2f980b6-9a69-4953-bc33-3324f08602fe \
  --signed-action create_work_order_from_fault \
  --entity-type work_order \
  --entity-id-key fault_id \
  --read-action view_fault_detail \
  --output-dir .
```

**Expected Output:**
```
✅ Created: tools/ops/monitors/faults_health_worker.py
✅ Created: tests/ci/faults_signed_flow_acceptance.py
✅ Created: tests/stress/faults_actions_endpoints.py
✅ Created: .github/workflows/faults-staging-acceptance.yml
✅ Created: .github/workflows/faults-stress.yml
✅ Created: docs/pipeline/FAULTS_FEATURE_FLAGS.md
```

**Review These Files:**
- Check `tools/ops/monitors/faults_health_worker.py` - Verify LENS_ID, DOMAIN, FEATURE_FLAGS
- Check test data (yacht_id, user_ids) - Should match staging environment
- Check `.github/workflows/` - Verify paths and secrets

---

#### 3. Deploy Health Worker to Render

**Why:** Automate health monitoring (replaces manual `monitor_canary_health.py`)

**File to Update:** `render.yaml` (add new worker service)

**Configuration:**
```yaml
services:
  # Existing services...

  # NEW: Faults Health Worker
  - type: worker
    name: faults-health-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python tools/ops/monitors/faults_health_worker.py
    envVars:
      - key: HEALTH_CHECK_INTERVAL_MINUTES
        value: 15  # Check every 15 minutes
      - key: API_BASE_URL
        value: https://pipeline-core.int.celeste7.ai
      - key: TENANT_SUPABASE_URL
        sync: false  # From existing env vars
      - key: TENANT_SUPABASE_JWT_SECRET
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: RENDER_API_KEY
        value: rnd_8BakHjSO36rN90gAbQHgfqTnFjJY
      - key: RENDER_SERVICE_ID
        value: srv-d5fr5hre5dus73d3gdn0
```

**Deploy:**
```bash
git add render.yaml tools/ops/monitors/faults_health_worker.py
git commit -m "Add Faults Health Worker for automated canary monitoring"
git push origin main

# Or trigger via Render dashboard:
# Dashboard → Service → Deploy Latest Commit
```

**Verification:**
```bash
# Check Render logs for worker startup
# Expected: [FeatureFlags] FAULT_LENS_V1_ENABLED=True
# Expected: Starting health check for lens=faults yacht=85fe1119-...

# Check DB after 15 minutes
psql $STAGING_DB_URL -c "SELECT * FROM pms_health_checks WHERE lens_id = 'faults' ORDER BY observed_at DESC LIMIT 1;"

# Should see: status='healthy', p95_latency_ms=..., error_rate_percent=0.00
```

**Troubleshooting:**
- **Worker crashes on startup:** Check env vars (JWT_SECRET, SERVICE_KEY)
- **No DB writes:** Check RLS policies (service_role must have INSERT permission)
- **503 errors:** Feature flags may be OFF (check Render env vars)

---

#### 4. Enable CI Workflows (GitHub Actions)

**Why:** Automate acceptance and stress testing

**Files to Commit:**
```bash
git add .github/workflows/faults-staging-acceptance.yml
git add .github/workflows/faults-stress.yml
git add tests/ci/faults_signed_flow_acceptance.py
git add tests/stress/faults_actions_endpoints.py
git commit -m "Add CI workflows for Faults Lens v1 acceptance and stress tests"
git push origin main
```

**Add GitHub Secrets:**
Go to GitHub → Settings → Secrets and variables → Actions → New repository secret

Add:
- `STAGING_JWT_SECRET` = `ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==`
- `SUPABASE_SERVICE_KEY` = (existing value from Render)
- `STAGING_DB_URL` = (staging PostgreSQL URL)

**Trigger Workflow Manually:**
1. Go to GitHub → Actions
2. Select "faults - Staging Acceptance"
3. Click "Run workflow" → "Run workflow"

**Expected Result:**
- Workflow runs in ~2 minutes
- 5/5 tests passing
- Artifacts uploaded (evidence files)

**Troubleshooting:**
- **401 Unauthorized:** Check `STAGING_JWT_SECRET` matches staging environment
- **Connection refused:** Check `STAGING_API_URL` is correct
- **Tests fail:** Check test data (yacht_id, user_ids, equipment_id)

---

#### 5. Monitor for 7 Days (Verify Automation Works)

**Why:** Ensure automated checks catch issues before proceeding to other lenses

**What to Monitor:**

**A. Health Worker Status (Every Day):**
```sql
-- Get latest health checks for faults lens
SELECT
  observed_at,
  status,
  p95_latency_ms,
  error_rate_percent,
  sample_size
FROM pms_health_checks
WHERE lens_id = 'faults'
  AND yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY observed_at DESC
LIMIT 10;
```

**Expected:** Status = 'healthy', error_rate = 0.00%, one row every 15 minutes

**B. Health Events (Check for Errors):**
```sql
-- Get recent errors
SELECT
  he.created_at,
  he.level,
  he.detail_json
FROM pms_health_events he
JOIN pms_health_checks hc ON he.check_id = hc.id
WHERE hc.lens_id = 'faults'
  AND he.level = 'error'
  AND he.created_at >= now() - interval '24 hours'
ORDER BY he.created_at DESC;
```

**Expected:** 0 rows (no errors)

**C. Render Worker Logs:**
```
Render Dashboard → faults-health-worker → Logs

Expected every 15 minutes:
[2026-01-28T15:00:00Z] INFO: Starting health check for lens=faults yacht=85fe1119-...
[2026-01-28T15:00:01Z] INFO: ✅ Service health: healthy (4/4 handlers)
[2026-01-28T15:00:02Z] INFO: ✅ Feature flags: enabled
[2026-01-28T15:00:03Z] INFO: ✅ List endpoint: 200 OK (12 actions, 867ms)
[2026-01-28T15:00:04Z] INFO: ✅ Suggestions endpoint: 200 OK (11 actions, 1234ms)
[2026-01-28T15:00:05Z] INFO: ✅ Wrote health check to DB: id=...
[2026-01-28T15:00:05Z] INFO: Sleeping for 15 minutes...
```

**D. CI Workflow Results:**
```
GitHub → Actions → "faults - Staging Acceptance"

Expected: ✅ Green (5/5 tests passing)
Download artifacts → faults-acceptance-evidence.zip → view transcripts
```

**E. Nightly Stress Tests:**
```
GitHub → Actions → "faults - Stress Testing"

Expected: ✅ Green (0×500 across 80 requests)
Download artifacts → faults-stress-results.md → verify P50/P95/P99
```

**Decision After 7 Days:**
- ✅ All checks green → Proceed to Phase B (other lenses)
- ⚠️ Degraded status → Investigate (check Render logs, DB queries)
- ❌ Unhealthy status → Rollback (disable feature flags)

---

### Phase B: Instantiate for Other Lenses (After Phase A Success)

**Goal:** Apply Lens Ops Template to Certificates, Equipment, Parts, etc.

**For Each Lens:**

#### 1. Gather Lens Parameters

**What You Need:**
- **lens_id:** Unique identifier (e.g., `certificates`, `equipment`)
- **domain:** Action router domain (usually same as lens_id)
- **feature_flags:** List of flags (e.g., `CERTIFICATES_LENS_V1_ENABLED`)
- **roles:** Comma-separated canon roles
- **signed_action:** SIGNED action name (if applicable)
- **entity_type:** Entity created by SIGNED action (e.g., `certificate_renewal`)
- **entity_id_key:** Payload key for entity ID (e.g., `certificate_id`)
- **read_action:** READ action for stress testing (e.g., `view_certificate_detail`)

**Example (Certificates Lens):**
```bash
lens_id=certificates
domain=certificates
feature_flags=CERTIFICATES_LENS_V1_ENABLED,CERTIFICATES_SUGGESTIONS_ENABLED
roles=crew,chief_engineer,chief_officer,captain,manager
signed_action=renew_certificate_with_approval
entity_type=certificate_renewal
entity_id_key=certificate_id
read_action=view_certificate_detail
```

#### 2. Run Generator

**Command:**
```bash
python3 docs/architecture/20_lens_ops/create_lens_ops_template.py \
  --lens-id certificates \
  --domain certificates \
  --feature-flags CERTIFICATES_LENS_V1_ENABLED,CERTIFICATES_SUGGESTIONS_ENABLED \
  --roles crew,chief_engineer,chief_officer,captain,manager \
  --signed-action renew_certificate_with_approval \
  --entity-type certificate_renewal \
  --entity-id-key certificate_id \
  --read-action view_certificate_detail \
  --output-dir .
```

#### 3. Review Generated Files

**Check:**
- Template placeholders replaced (no `{LENS_ID}` remaining)
- Test data matches staging environment
- Feature flags match `apps/api/integrations/feature_flags.py`

#### 4. Deploy Worker + Enable CI

**Same as Phase A, steps 3-4**

#### 5. Monitor for 24h

**Same as Phase A, step 5** (but verify certificates-specific checks)

---

### Phase C: Ops Dashboard Integration (Future Enhancement)

**Goal:** Build UI for viewing health checks (optional, not blocking)

**Requirements:**
- Query `pms_health_checks` table (RLS-scoped)
- Display lens health status (healthy/degraded/unhealthy)
- Show latency trends (P95 over time)
- Alert on unhealthy status

**Tables to Query:**
```sql
-- Latest health check per lens
SELECT DISTINCT ON (lens_id)
  lens_id,
  status,
  p95_latency_ms,
  error_rate_percent,
  observed_at
FROM pms_health_checks
WHERE yacht_id = get_user_yacht_id()
ORDER BY lens_id, observed_at DESC;

-- Historical trends (last 24h)
SELECT * FROM get_health_check_history(get_user_yacht_id(), 'faults', 24);

-- Unhealthy lenses
SELECT * FROM get_unhealthy_lenses(get_user_yacht_id());
```

**UI Mockup:**
```
Lens Health Dashboard
─────────────────────
Faults        ✅ Healthy    P95: 867ms   Last checked: 2 min ago
Certificates  ⚠️ Degraded   P95: 3.2s    Last checked: 5 min ago
Equipment     ✅ Healthy    P95: 1.1s    Last checked: 1 min ago
Parts         ❌ Unhealthy  P95: 12s     Last checked: 15 min ago

[View Details] [Refresh]
```

**Not Blocking:** This is a "nice to have" - health workers write to DB regardless of UI

---

## Key Files to Know

### Templates (Source Code)

**Location:** `docs/architecture/20_lens_ops/templates/`

| File | Purpose | What to Modify |
|------|---------|----------------|
| `health_worker_template.py` | Render worker | Update check logic, add new endpoints |
| `acceptance_test_template.py` | CI acceptance | Add more test cases, change assertions |
| `stress_test_template.py` | CI stress | Change concurrency, add more endpoints |

**When to Update Templates:**
- New testing pattern emerges (e.g., new assertion type)
- Health check needs new probe (e.g., check Redis connection)
- Stress test parameters change (e.g., increase to 100 concurrent)

**After Updating Templates:**
```bash
# Re-run generator for all affected lenses
python3 create_lens_ops_template.py --lens-id faults ...
python3 create_lens_ops_template.py --lens-id certificates ...
```

---

### Generator Script

**Location:** `docs/architecture/20_lens_ops/create_lens_ops_template.py`

**What It Does:**
1. Loads templates from `templates/` directory
2. Replaces placeholders (`{LENS_ID}`, `{DOMAIN}`, etc.)
3. Writes instantiated files to output directory

**When to Update Generator:**
- Add new template file (update `generate_*` functions)
- Add new placeholder (update `replacements` dict)
- Change output directory structure

**Example: Add New Template**
```python
def generate_my_new_template(lens_id: str, domain: str, output_dir: Path, config: Dict[str, str]):
    """Generate my new template file."""
    template = load_template("my_new_template.py")

    replacements = {
        "LENS_ID": lens_id,
        "DOMAIN": domain,
        **config
    }

    content = instantiate_template(template, replacements)
    output_path = output_dir / "path" / "to" / f"{lens_id}_my_file.py"
    write_file(output_path, content)
```

---

### DB Migration

**Location:** `docs/architecture/20_lens_ops/migrations/ops_health_tables.sql`

**Tables:**
- `pms_health_checks` - Aggregated health check results
- `pms_health_events` - Detailed event logs (info/warning/error)

**Helper Functions:**
- `get_latest_health_check(yacht_id, lens_id)` - Most recent check
- `get_health_check_history(yacht_id, lens_id, hours)` - Historical data
- `get_unhealthy_lenses(yacht_id)` - All degraded/unhealthy lenses

**When to Update Migration:**
- Add new column to health checks (e.g., `cpu_usage_percent`)
- Add new helper function (e.g., `get_health_check_by_date_range`)
- Change RLS policies (e.g., allow purser to view health checks)

**Important:** After modifying migration, re-apply to staging/production:
```bash
psql $STAGING_DB_URL < migrations/ops_health_tables.sql
psql $PRODUCTION_DB_URL < migrations/ops_health_tables.sql
```

---

### Documentation

**Location:** `docs/architecture/20_lens_ops/docs/`

| File | Purpose | Audience |
|------|---------|----------|
| `README.md` | Complete guide (Why/How) | Engineers (you) |
| `PRODUCTIONIZATION_SUMMARY.md` | Executive summary | Managers, reviewers |
| `EVIDENCE_TEMPLATE.md` | Evidence structure | QA, compliance |

**When to Update Docs:**
- Testing doctrine changes (update citations)
- New template added (update README sections)
- Instantiation process changes (update step-by-step guides)

---

## Testing Doctrine (Non-Negotiable)

All templates enforce CelesteOS testing doctrine. You must adhere to these when modifying templates:

### 1. Expected 4xx is Success (When Asserted)

**Cite:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:799`

> "Role denial asserts 403 (crew mutations)" - When testing role gating, a 403 response for unauthorized roles is a **PASS**, not a failure.

**Implementation:**
```python
# CORRECT: Assert 403 for CREW
status, body = execute_action("create_work_order_from_fault", crew_jwt, payload)
assert status == 403, f"Expected 403, got {status}"  # ✅ PASS
assert body["error_code"] == "invalid_signer_role"

# WRONG: Treat 403 as failure
assert status == 200, f"Expected 200, got {status}"  # ❌ FAIL (incorrect expectation)
```

### 2. 500 is Always Failure

**Cite:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`

> "500 indicates bug in contracts" - A 500 error always indicates a bug. Stress tests **must report 0×500** to pass.

**Implementation:**
```python
# Stress test verdict
if status_5xx_count > 0:
    verdict = "FAIL"
    reason = f"{status_5xx_count}×500 errors detected"
else:
    verdict = "PASS"  # Only PASS if 0×500
```

### 3. Evidence Artifacts Required

**Cite:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:815`

> "Evidence table types" - Tests must capture raw HTTP transcripts, status codes, response bodies, before/after DB state.

**Implementation:**
```python
# CORRECT: Capture full transcript
transcript = f"""
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {jwt[:20]}...
Content-Type: application/json

{json.dumps(payload, indent=2)}

HTTP/1.1 {status} {reason}
Content-Type: application/json

{json.dumps(body, indent=2)}
"""
evidence.append(transcript)

# WRONG: Only log pass/fail
print("Test passed")  # ❌ No evidence artifact
```

### 4. Verdict Thresholds

**Cite:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:708`

> "Success rate, P95" - Stress tests must report P50/P95/P99 latencies. Verdict: PASS if 0×500.

**Implementation:**
```python
# Compute percentiles
p50 = statistics.median(latencies)
p95 = latencies[int(len(latencies) * 0.95)]
p99 = latencies[int(len(latencies) * 0.99)]

# Report in evidence
print(f"P50: {p50}ms, P95: {p95}ms, P99: {p99}ms")

# Verdict
verdict = "PASS" if status_5xx_count == 0 else "FAIL"
```

**If You Break These Rules:**
- Tests will fail in CI (incorrect assertions)
- Evidence will be rejected by reviewers (missing transcripts)
- Stress tests will pass when they shouldn't (accepting 500s)

---

## Common Pitfalls (Things to Avoid)

### 1. Forgetting to Update Test Data

**Problem:** Generated tests use placeholder IDs (e.g., `00000000-0000-0000-0000-000000000001`)

**Symptom:** Tests fail with 404 Not Found

**Solution:** Update test data after generation:
```python
# In faults_signed_flow_acceptance.py
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"  # ✅ Real staging yacht
TEST_ENTITY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"  # ✅ Real fault ID

# WRONG
TEST_ENTITY_ID = "00000000-0000-0000-0000-000000000001"  # ❌ Placeholder
```

### 2. Mixing Environments

**Problem:** Running staging tests against production

**Symptom:** 403 Forbidden (JWT signed with wrong secret)

**Solution:** Check environment variables:
```bash
# CORRECT
STAGING_API_URL=https://pipeline-core.int.celeste7.ai
STAGING_JWT_SECRET=ep2o/+mEQD/...  # Staging secret

# WRONG
STAGING_API_URL=https://pipeline-core.int.celeste7.ai
STAGING_JWT_SECRET=<production_secret>  # ❌ Wrong secret
```

### 3. Not Checking RLS Policies

**Problem:** Health worker writes fail with 403 Forbidden

**Symptom:** No rows in `pms_health_checks` table

**Solution:** Verify RLS policies allow service_role INSERT:
```sql
-- Check policies
\d pms_health_checks

-- Should see:
-- POLICY "service_role_write_health_checks" FOR INSERT TO service_role
```

### 4. Hardcoding Secrets in Code

**Problem:** JWT secrets committed to Git

**Symptom:** Security vulnerability

**Solution:** Use environment variables:
```python
# CORRECT
JWT_SECRET = os.getenv('STAGING_JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("STAGING_JWT_SECRET not set")

# WRONG
JWT_SECRET = "ep2o/+mEQD/b54M8W50Vk3..."  # ❌ Hardcoded secret
```

### 5. Ignoring Feature Flag State

**Problem:** Tests expect 200 but get 503 FEATURE_DISABLED

**Symptom:** Tests fail in CI but pass locally

**Solution:** Check feature flags before running tests:
```bash
# Verify flags are enabled in staging
curl -s https://api.render.com/v1/services/srv-.../env-vars \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  | jq '.[] | select(.envVar.key | contains("FAULT_LENS"))'

# Should show:
# FAULT_LENS_V1_ENABLED=true
# FAULT_LENS_SUGGESTIONS_ENABLED=true
```

---

## Troubleshooting Guide

### Health Worker Issues

**Problem:** Worker crashes on startup

**Logs:**
```
KeyError: 'TENANT_SUPABASE_JWT_SECRET'
```

**Solution:** Add missing env var to Render dashboard

---

**Problem:** Worker runs but no DB writes

**Logs:**
```
❌ Failed to write health check to DB: 403 - Forbidden
```

**Solution:** Check RLS policies (service_role needs INSERT permission)

---

**Problem:** Worker reports 503 FEATURE_DISABLED

**Logs:**
```
❌ List endpoint: 503 FEATURE_DISABLED
```

**Solution:** Enable feature flags in Render dashboard

---

### CI Workflow Issues

**Problem:** Workflow fails with "invalid_token"

**Logs:**
```
{"error_code": "invalid_token", "message": "Signature verification failed"}
```

**Solution:** Check GitHub secret `STAGING_JWT_SECRET` matches staging environment

---

**Problem:** Tests fail with 404 Not Found

**Logs:**
```
[FAIL] Test 4: CAPTAIN signature: Expected 200, got 404
```

**Solution:** Update test data (yacht_id, fault_id, equipment_id)

---

**Problem:** Artifacts not uploaded

**Logs:**
```
No artifacts found matching the path: verification_handoff/phase*/
```

**Solution:** Tests didn't generate evidence files (check test script errors)

---

### DB Migration Issues

**Problem:** Migration fails with "relation already exists"

**Logs:**
```
ERROR: relation "pms_health_checks" already exists
```

**Solution:** Migration already applied (safe to ignore, or use `CREATE TABLE IF NOT EXISTS`)

---

**Problem:** Helper functions not found

**Logs:**
```
ERROR: function get_latest_health_check does not exist
```

**Solution:** Re-run migration (functions defined in same file)

---

## Success Criteria (How to Know You're Done)

### Phase A Complete (Faults Lens)

✅ **DB Migration Applied:**
```sql
SELECT COUNT(*) FROM pms_health_checks WHERE lens_id = 'faults';
-- Should return > 0 (health checks being written)
```

✅ **Health Worker Running:**
```
Render Dashboard → faults-health-worker → Status: Running
Logs show: "✅ OVERALL: CANARY HEALTHY" every 15 minutes
```

✅ **CI Workflows Green:**
```
GitHub Actions → faults-staging-acceptance → ✅ Green (5/5 passing)
GitHub Actions → faults-stress → ✅ Green (0×500)
```

✅ **Evidence Artifacts Generated:**
```bash
# Download from GitHub Actions
unzip faults-acceptance-evidence.zip
cat verification_handoff/phase6/FAULTS_ACCEPTANCE_EVIDENCE.md
# Should contain: HTTP transcripts, status codes, audit logs
```

✅ **7-Day Monitoring Complete:**
```sql
SELECT COUNT(*) FROM pms_health_checks
WHERE lens_id = 'faults'
  AND status = 'healthy'
  AND observed_at >= now() - interval '7 days';
-- Should return ~672 rows (7 days × 24 hours × 4 checks/hour)
```

### Phase B Complete (All Lenses)

✅ **Each Lens Has:**
- Health worker deployed and running
- CI workflows enabled and green
- Evidence artifacts being generated
- 24h monitoring shows "healthy" status

✅ **Ops Dashboard (Optional):**
- UI shows lens health status
- Historical trends visible
- Alerts configured for unhealthy status

---

## Questions & Answers

**Q: Can I modify templates after generation?**
A: Yes, but prefer updating the template source and re-generating. This keeps all lenses consistent.

**Q: What if a lens doesn't have SIGNED actions?**
A: Skip `--signed-action`, `--entity-type`, `--entity-id-key` parameters. Tests will skip signature validation tests.

**Q: How do I add a new endpoint to health checks?**
A: Update `health_worker_template.py` → add new `check_*` function → re-generate all lenses

**Q: Can I run health worker locally?**
A: Yes:
```bash
export TENANT_SUPABASE_JWT_SECRET=...
export SUPABASE_SERVICE_KEY=...
python tools/ops/monitors/faults_health_worker.py
```

**Q: What if CI workflows are too slow?**
A: Reduce concurrency in stress tests (edit `stress_test_template.py`)

**Q: How do I debug RLS policy issues?**
A: Use service_role in psql:
```bash
psql $STAGING_DB_URL -c "SET ROLE service_role; INSERT INTO pms_health_checks (...) VALUES (...);"
```

---

## Contact & Support

**Documentation:** `docs/architecture/20_lens_ops/docs/README.md`

**Testing Doctrine:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md`

**Phase 1 Evidence:** `verification_handoff/phase6/` (Fault Lens v1 canary results)

**Generator Help:**
```bash
python3 docs/architecture/20_lens_ops/create_lens_ops_template.py --help
```

**DB Schema:**
```bash
psql $STAGING_DB_URL -c "\\d pms_health_checks"
psql $STAGING_DB_URL -c "\\df get_*"
```

---

## Final Notes

**What Success Looks Like:**
- Phase 1 canary took 24h manual monitoring
- With Lens Ops Template, Phase 2+ take 0 manual hours (fully automated)
- New lens deployment: < 1 hour (generator + deploy + enable CI)
- Ops dashboard shows real-time health across all lenses

**What Failure Looks Like:**
- Health worker crashes repeatedly (fix env vars)
- CI workflows stay red (fix test data)
- No DB writes (fix RLS policies)
- Manual monitoring continues (defeat the purpose!)

**Your Goal:**
Replace ALL manual monitoring with automated health workers. When done, you should never manually check canary health again—just query `pms_health_checks` table or view ops dashboard.

---

**Good luck! You've got this. 🚀**

**Start with Phase A, Step 1 (Apply DB Migration) and work sequentially.**
