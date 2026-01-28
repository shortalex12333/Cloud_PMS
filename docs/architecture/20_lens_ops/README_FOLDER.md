# Lens Ops Template - Folder Guide

**Location:** `docs/architecture/20_lens_ops/`
**Status:** Production-grade template (v1.0)
**Date Created:** 2026-01-28

---

## Quick Start

**Are you the next engineer?**

👉 **START HERE:** Read `HANDOFF_TO_NEXT_ENGINEER.md` (comprehensive guide)

**Need documentation?**

👉 **READ THIS:** `docs/README.md` (Why/How/What)

**Want to see an example?**

👉 **LOOK HERE:** `examples/parts_lens_example/` (generated files for Parts Lens v2)

---

## Folder Structure

```
lens_ops_template/                               ← Root folder
│
├── README_FOLDER.md                             ← This file (orientation)
├── HANDOFF_TO_NEXT_ENGINEER.md                  ← 🎯 START HERE
│
├── create_lens_ops_template.py                  ← ⭐ Generator script (run this)
│
├── templates/                                    ← Template source files
│   ├── health_worker_template.py                ← Render background worker
│   ├── acceptance_test_template.py              ← CI acceptance tests (400/400/403/200)
│   └── stress_test_template.py                  ← CI stress tests (0×500 requirement)
│
├── migrations/                                   ← DB schema
│   └── ops_health_tables.sql                    ← pms_health_checks, pms_health_events
│
├── docs/                                         ← Documentation
│   ├── README.md                                 ← Complete guide (Why/How)
│   ├── PRODUCTIONIZATION_SUMMARY.md             ← Executive summary
│   └── EVIDENCE_TEMPLATE.md                     ← Evidence structure
│
└── examples/                                     ← Generated examples
    └── parts_lens_example/                       ← Dry-run: Parts Lens v2
        ├── tools/ops/monitors/parts_health_worker.py
        ├── tests/ci/parts_signed_flow_acceptance.py
        ├── tests/stress/parts_actions_endpoints.py
        ├── .github/workflows/parts-staging-acceptance.yml
        ├── .github/workflows/parts-stress.yml
        └── docs/pipeline/PARTS_FEATURE_FLAGS.md
```

---

## What Each Folder Contains

### 📁 `templates/` - Source Templates

**What:** Python template files with placeholders like `{LENS_ID}`, `{DOMAIN}`

**Purpose:** Source code for generated files

**When to Modify:**
- Adding new test cases to acceptance tests
- Changing health check logic
- Updating stress test parameters

**After Modifying:** Re-run generator for all affected lenses

**Files:**
- `health_worker_template.py` - Checks health every N minutes, writes to DB
- `acceptance_test_template.py` - Tests signature validation (400/400/403/200)
- `stress_test_template.py` - Tests concurrent load (0×500 requirement)

---

### 📁 `migrations/` - DB Schema

**What:** SQL migration file for health monitoring tables

**Purpose:** Create DB tables for storing health check results

**When to Apply:**
- Before deploying first health worker
- When updating schema (add columns, functions)

**How to Apply:**
```bash
psql $STAGING_DB_URL < migrations/ops_health_tables.sql
```

**Tables Created:**
- `pms_health_checks` - Aggregated health check results (one row per check)
- `pms_health_events` - Detailed event logs (many events per check)

**Helper Functions:**
- `get_latest_health_check(yacht_id, lens_id)` - Most recent check
- `get_health_check_history(yacht_id, lens_id, hours)` - Historical data
- `get_unhealthy_lenses(yacht_id)` - All degraded/unhealthy lenses

---

### 📁 `docs/` - Documentation

**What:** Markdown documentation files

**Purpose:** Explain Why/How/What for engineers and managers

**Files:**

| File | Purpose | Audience |
|------|---------|----------|
| `README.md` | Complete guide (Why/How/What) | Engineers |
| `PRODUCTIONIZATION_SUMMARY.md` | Executive summary | Managers, reviewers |
| `EVIDENCE_TEMPLATE.md` | Evidence structure (citations) | QA, compliance |

**When to Read:**
- **Before using template:** Read `README.md` (comprehensive)
- **For quick overview:** Read `PRODUCTIONIZATION_SUMMARY.md`
- **For evidence structure:** Read `EVIDENCE_TEMPLATE.md`

---

### 📁 `examples/` - Generated Examples

**What:** Real generated files from running the generator

**Purpose:** Show exactly what the generator produces (before generating for real lenses)

**Folders:**
- `parts_lens_example/` - Generated files for hypothetical "Parts Lens v2"

**What's Inside parts_lens_example/:**
```
tools/ops/monitors/parts_health_worker.py        ← Health worker (runs every 15 min)
tests/ci/parts_signed_flow_acceptance.py         ← Acceptance tests (5 tests)
tests/stress/parts_actions_endpoints.py          ← Stress tests (80 requests)
.github/workflows/parts-staging-acceptance.yml   ← CI workflow (pre-deploy)
.github/workflows/parts-stress.yml               ← CI workflow (nightly)
docs/pipeline/PARTS_FEATURE_FLAGS.md             ← Feature flags doc
```

**How to Review:**
1. Open `parts_health_worker.py` - See LENS_ID="parts", DOMAIN="parts"
2. Check test data - See SIGNED_ACTION="order_part_with_approval"
3. Review workflows - See GitHub Actions configuration

**When to Use:**
- Before generating for real lens (understand output structure)
- As reference when modifying templates
- To verify generator produces correct substitutions

---

## Generator Script

**Location:** `create_lens_ops_template.py` (root of this folder)

**Purpose:** Generate all files for a lens in < 5 minutes

**Usage:**
```bash
python3 create_lens_ops_template.py \
  --lens-id faults \
  --domain faults \
  --feature-flags FAULT_LENS_V1_ENABLED,FAULT_LENS_SUGGESTIONS_ENABLED \
  --roles crew,chief_engineer,chief_officer,captain,manager \
  --output-dir /path/to/project
```

**Output:**
```
✅ Created: tools/ops/monitors/faults_health_worker.py
✅ Created: tests/ci/faults_signed_flow_acceptance.py
✅ Created: tests/stress/faults_actions_endpoints.py
✅ Created: .github/workflows/faults-staging-acceptance.yml
✅ Created: .github/workflows/faults-stress.yml
✅ Created: docs/pipeline/FAULTS_FEATURE_FLAGS.md
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--lens-id` | Yes | Unique identifier | `faults` |
| `--domain` | Yes | Action router domain | `faults` |
| `--feature-flags` | Yes | Comma-separated flags | `FAULT_LENS_V1_ENABLED,FAULT_LENS_SUGGESTIONS_ENABLED` |
| `--roles` | Yes | Comma-separated canon roles | `crew,chief_engineer,captain` |
| `--output-dir` | No | Output directory (default: `.`) | `/path/to/project` |
| `--yacht-id` | No | Test yacht ID | `85fe1119-b04c-41ac-80f1-829d23322598` |
| `--hod-user-id` | No | HOD user ID for tests | `05a488fd-e099-4d18-bf86-d87afba4fcdf` |
| `--signed-action` | No | SIGNED action name | `create_work_order_from_fault` |
| `--entity-type` | No | Entity created by SIGNED action | `work_order` |
| `--entity-id-key` | No | Payload key for entity ID | `fault_id` |
| `--read-action` | No | READ action for stress testing | `view_fault_detail` |

**Help:**
```bash
python3 create_lens_ops_template.py --help
```

---

## Parent Folder Context

**This Folder:** `docs/architecture/20_lens_ops/`

**Parent Folder:** `verification_handoff/`

**Parent Contains:**
- `phase6/` - Fault Lens v1 Phase 1 canary evidence (where this template came from)
  - `PHASE1_CANARY_SMOKE_TESTS.md` - Smoke test results
  - `PHASE8_INTEGRATION_TEST_RESULTS.md` - Acceptance test evidence
  - `PHASE8_STRESS_RESULTS.md` - Stress test results (0×500 verified)
  - `PHASE8_NOTIFICATIONS_EVIDENCE.md` - Idempotency proof
  - `ALL_SCRIPTS_REFERENCE.md` - Ad-hoc scripts catalog (superseded by this template)

**Relationship:**
```
verification_handoff/
├── phase6/                          ← Fault Lens v1 evidence (ad-hoc scripts)
│   ├── PHASE8_INTEGRATION_TEST_RESULTS.md
│   ├── PHASE8_STRESS_RESULTS.md
│   └── ALL_SCRIPTS_REFERENCE.md     ← Manual monitoring (replaced by...)
│
└── lens_ops_template/               ← Production-grade automation (this folder)
    ├── templates/                   ← Replaces ad-hoc scripts
    ├── create_lens_ops_template.py  ← One command generates all
    └── HANDOFF_TO_NEXT_ENGINEER.md  ← Start here
```

**Key Insight:** Phase 6 used ad-hoc scripts for manual monitoring. This template productionizes those scripts into automated, repeatable infrastructure.

---

## Quick Command Reference

### Generate Files for New Lens
```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
python3 docs/architecture/20_lens_ops/create_lens_ops_template.py \
  --lens-id your_lens \
  --domain your_domain \
  --feature-flags YOUR_LENS_V1_ENABLED,YOUR_LENS_SUGGESTIONS_ENABLED \
  --roles crew,chief_engineer,captain,manager \
  --output-dir .
```

### Apply DB Migration
```bash
psql $STAGING_DB_URL < docs/architecture/20_lens_ops/migrations/ops_health_tables.sql
```

### Query Health Checks
```sql
-- Latest health check for faults lens
SELECT * FROM get_latest_health_check('85fe1119-b04c-41ac-80f1-829d23322598', 'faults');

-- Historical data (last 24h)
SELECT * FROM get_health_check_history('85fe1119-b04c-41ac-80f1-829d23322598', 'faults', 24);

-- All unhealthy lenses
SELECT * FROM get_unhealthy_lenses('85fe1119-b04c-41ac-80f1-829d23322598');
```

### Run Tests Locally
```bash
# Acceptance tests
export STAGING_JWT_SECRET="..."
export SUPABASE_SERVICE_KEY="..."
python3 tests/ci/faults_signed_flow_acceptance.py

# Stress tests
python3 tests/stress/faults_actions_endpoints.py
```

### Deploy Health Worker
```bash
# Add to render.yaml
# Deploy via Git push or Render dashboard
git add render.yaml tools/ops/monitors/faults_health_worker.py
git commit -m "Add Faults Health Worker"
git push origin main
```

---

## Success Indicators

**You've successfully used this template when:**

✅ **Generated files exist:**
```bash
ls -la tools/ops/monitors/faults_health_worker.py
ls -la tests/ci/faults_signed_flow_acceptance.py
ls -la tests/stress/faults_actions_endpoints.py
```

✅ **DB tables created:**
```sql
\dt pms_health*
-- Shows: pms_health_checks, pms_health_events
```

✅ **Health worker running:**
```
Render Dashboard → faults-health-worker → Status: Running
```

✅ **CI workflows green:**
```
GitHub Actions → faults-staging-acceptance → ✅ Green
GitHub Actions → faults-stress → ✅ Green
```

✅ **Health checks being written:**
```sql
SELECT COUNT(*) FROM pms_health_checks WHERE lens_id = 'faults';
-- Returns: > 0
```

---

## Need Help?

1. **Read handoff document:** `HANDOFF_TO_NEXT_ENGINEER.md`
2. **Check documentation:** `docs/README.md`
3. **Review example:** `examples/parts_lens_example/`
4. **Run generator help:** `python3 create_lens_ops_template.py --help`
5. **Check testing doctrine:** `/Volumes/Backup/CELESTE/testing_success_ci:cd.md`

---

## Version History

- **v1.0** (2026-01-28) - Initial productionization from Fault Lens v1 Phase 1 canary
  - Created templates for health worker, acceptance tests, stress tests
  - Built generator script with dry-run example (Parts Lens v2)
  - Applied to Fault Lens v1 (pending deployment)

---

**Status:** ✅ Ready for deployment
**Next Action:** Apply Phase A (Fault Lens v1) - see `HANDOFF_TO_NEXT_ENGINEER.md`
