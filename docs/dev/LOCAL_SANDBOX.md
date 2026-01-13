# LOCAL SANDBOX ENVIRONMENT
**Purpose:** End-to-end testing environment for CelesteOS before merging to main
**Branch:** universal_v1
**Date:** 2026-01-12

---

## REPO RECONNAISSANCE (Step 1)

### Services Architecture

**Frontend (Next.js 14)**
- **Location:** `/apps/web/`
- **Port:** 3000
- **Entry:** `npm run dev` (next dev)
- **Dependencies:** React 18, Supabase client, TanStack Query, Radix UI
- **Key Features:**
  - Document viewer
  - Situation creation
  - Microaction execution UI
  - Authentication with Supabase Auth

**Backend API (FastAPI)**
- **Location:** `/apps/api/`
- **Port:** 8000
- **Entry:** `pipeline_service.py` (uvicorn)
- **Dependencies:** FastAPI, Supabase Python client, OpenAI, pytest
- **Endpoints:**
  - POST /search - Main search pipeline
  - POST /extract - Entity extraction
  - GET /health - Health check
  - GET /capabilities - Service info
  - P0 actions routes (in `/routes/p0_actions_routes.py`)

**Worker Service**
- **Location:** `/apps/worker/`
- **Status:** Minimal/unused (empty directory)

---

### Database Structure

**Migration Files:** 18 migrations in `/database/migrations/`
```
00_enable_extensions.sql
01_core_tables_v2_secure.sql
02_auth_sync_trigger.sql
02_p0_actions_tables_REVISED.sql (29KB - latest P0 tables)
03_add_accountability_columns.sql
03_fix_document_rpc.sql
03_fix_search_chunks_rls.sql
04_kill_auth_users_table.sql
04_trust_accountability_tables.sql
05_rename_auth_tables.sql
06_fix_jwt_hook_function.sql
07_fix_rls_policies_jwt_fallback.sql
08_add_storage_rls_policy.sql
09_fix_search_chunks_rls_table_name.sql
10_add_row_security_off_to_rpc.sql
11_create_get_user_auth_info_rpc.sql
```

**Setup Scripts:**
- `setup_complete.sql` (14KB)
- `setup_complete_FIXED.sql` (13KB)

**Supabase Local:**
- ❌ Not configured (no `/supabase/` directory)
- ✅ Supabase CLI installed: `/opt/homebrew/bin/supabase`

---

### Handlers Implemented

**API Handlers:** `/apps/api/handlers/`
```python
equipment_handlers.py      (21KB)
fault_handlers.py          (22KB)
handover_handlers.py       (15KB)
inventory_handlers.py      (22KB)  # Existing, not from governance implementation
list_handlers.py           (26KB)
manual_handlers.py         (10KB)
purchasing_mutation_handlers.py (20KB)  # Updated with table name fixes
work_order_handlers.py     (15KB)
work_order_mutation_handlers.py (52KB)
```

**Guard Compliance:**
- Guard declarations per handler (GUARDS dict)
- CI compliance checker: `/scripts/check_g0_compliance_v2.py`

---

### Test Infrastructure

**Test Suite:** `/tests/`
```
action_router/          - Action routing tests
entity_extraction/      - Entity extraction validation
sql_campaign/           - SQL stress testing
stress_test_*.py        - Performance tests
pattern_suite_audit.py  - Pattern validation
test_microactions.py    - Microaction tests
test_pipeline_endpoint.py - Pipeline API tests
```

**Synthetic Data:**
- `scripts/populate_synthetic_data.py` (37KB)
- `stress_test_dataset_v3.json` (942KB)

---

### Environment Variables

**Configuration:** `.env.example` (274 lines)

**Critical for Local Sandbox:**
```bash
# Supabase (Required)
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321  # Local Supabase
NEXT_PUBLIC_SUPABASE_ANON_KEY=<local_anon_key>
SUPABASE_SERVICE_KEY=<local_service_key>
SUPABASE_JWT_SECRET=<local_jwt_secret>

# Backend API
NEXT_PUBLIC_CLOUD_API_URL=http://localhost:8000
CLOUD_API_URL=http://localhost:8000

# Mock External Services (for testing)
MOCK_SEARCH_ENGINE=true
MOCK_PREDICTIVE_ENGINE=true

# Storage
STORAGE_PROVIDER=supabase  # Use local Supabase Storage

# OpenAI (for embeddings)
OPENAI_API_KEY=<your_key>  # Optional - can mock
```

---

### Existing Dev Scripts

**Makefile Commands:**
```bash
make dev-web        # Start Next.js frontend (port 3000)
make dev-api        # Start FastAPI backend (port 8000)
make install        # Install all dependencies
make test           # Run all tests
make lint           # Run linters
make typecheck      # TypeScript checking
make clean          # Clean build artifacts
```

**API Entry Point:**
```bash
cd apps/api && uvicorn pipeline_service:app --reload --host 0.0.0.0 --port 8000
```

---

## IMPLEMENTATION PLAN

### Step 2: Supabase Local Setup

**Create:**
```
/supabase/
├── config.toml              # Supabase local config
├── seed.sql                 # Seed data (1 yacht, 2 users, test data)
└── .gitignore               # Ignore temp files

/scripts/dev/
├── supabase_start.sh        # Start local Supabase + run migrations
├── supabase_reset.sh        # Reset DB to clean state
└── supabase_stop.sh         # Stop local Supabase
```

**Seed Data Requirements:**
- 1 yacht: "M/Y Test Vessel" (UUID: seed-yacht-001)
- 2 users: admin@test.com (Chief Engineer), crew@test.com (Engineer)
- 1 document: Sample maintenance manual PDF
- 1 work order: "Generator maintenance"
- 1 part: "Oil filter" (quantity: 5, minimum: 3)
- 1 shopping list item: "Hydraulic oil"

---

### Step 3: Storage Sandbox

**Approach:** Use Supabase Storage emulator (included in `supabase start`)

**Create:**
```
/fixtures/docs/
└── sample.pdf               # Sample yacht manual (from existing docs or generated)

/scripts/dev/
└── upload_fixture_docs.sh   # Upload sample.pdf to local Supabase Storage
```

**Buckets to Create:**
- `documents` - For PDF manuals
- `photos` - For receiving/fault images

---

### Step 4: Backend Sandbox Runner

**Create:**
```
/scripts/dev/
├── run_api.sh               # Start API with local env
└── wait_for_api.sh          # Health check poller

/apps/api/
└── .env.local.example       # Local-specific env vars
```

**Mock Stubs Required:**
- Search engine responses (pattern matching)
- Predictive engine responses (stub data)
- OCR processing (return placeholder text)

---

### Step 5: Frontend Sandbox Runner

**Create:**
```
/scripts/dev/
├── run_web.sh               # Start web with local env
└── wait_for_web.sh          # Health check poller

/apps/web/
└── .env.local.example       # Local-specific env vars
```

**Features to Test:**
- Document viewer displays sample.pdf
- Situation creation works
- At least one microaction executes (e.g., log_part_usage)

---

### Step 6: Automated Proof Harness

**Create:**
```
/tests/smoke/
├── document_viewer.spec.ts      # Playwright: View PDF
├── situation_microaction.spec.ts # Playwright: Create situation + execute action
└── api_health.spec.ts           # Playwright: API endpoints

/tests/smoke/api/
├── test_health.py               # pytest: API health
├── test_microaction_execute.py  # pytest: Execute one action
└── conftest.py                  # pytest fixtures

/scripts/dev/
└── prove.sh                     # Master test runner
```

**Proof Bundle Output:**
```
/proof/<timestamp>/
├── summary.txt                  # Pass/fail summary
├── screenshots/                 # Playwright screenshots
│   ├── document_viewer.png
│   └── situation_created.png
├── logs/
│   ├── supabase.log
│   ├── api.log
│   └── web.log
├── test_results.json            # Test results
└── environment.txt              # Versions, config
```

---

### Step 7: GitHub Workflow (Optional)

**Create:**
```
/.github/workflows/
└── sandbox_smoke.yml            # CI workflow
```

**Triggers:**
- On push to universal_v1
- On PR to main

**Steps:**
1. Install Supabase CLI
2. Run migrations
3. Start API
4. Run API smoke tests
5. Upload test results

---

## SUCCESS CRITERIA

**One-Command Startup:**
```bash
./scripts/dev/prove.sh
```

**Expected Output:**
```
✅ Supabase started (port 54321)
✅ Migrations applied (18 migrations)
✅ Seed data loaded (1 yacht, 2 users)
✅ Fixture documents uploaded (sample.pdf)
✅ API started (port 8000)
✅ Web started (port 3000)
✅ Document viewer test: PASS
✅ Situation + microaction test: PASS
✅ API health test: PASS

Proof bundle: /proof/2026-01-12_14-30-22/
```

**Manual Verification:**
1. Navigate to http://localhost:3000
2. Login as admin@test.com / password123
3. See document viewer with sample.pdf
4. Create situation "Generator maintenance"
5. Execute microaction "log_part_usage" on "Oil filter"
6. See audit log entry created

---

## PREREQUISITES

**Required Software:**
- ✅ Supabase CLI (installed: `/opt/homebrew/bin/supabase`)
- ⚠️  Docker Desktop (REQUIRED - not currently running)
- ✅ Node.js 20+ (for Next.js frontend)
- ✅ Python 3.11+ (for FastAPI backend)

**Install Docker Desktop:**
```bash
# macOS
brew install --cask docker

# Or download from: https://docs.docker.com/desktop
```

**Start Docker Desktop** before running Supabase local.

---

## IMPLEMENTATION PROGRESS

### ✅ Step 1: Repo Reconnaissance (COMPLETE)
- [x] Identified service architecture (Next.js + FastAPI)
- [x] Mapped existing migrations (18 files)
- [x] Analyzed environment variables
- [x] Documented existing handlers and tests
- [x] Created LOCAL_SANDBOX.md

### ✅ Step 2: Supabase Local Setup (COMPLETE)
- [x] Initialized Supabase config (`/supabase/config.toml`)
- [x] Created migrations directory with all 18 migrations
- [x] Created comprehensive seed data (`/supabase/seed.sql`)
  - 1 yacht: M/Y Test Vessel
  - 2 users: admin@test.com, crew@test.com
  - 1 equipment: Main Generator #1
  - 1 part: Oil Filter (quantity: 5, min: 3)
  - 1 document: Generator Manual
  - 1 work order: 500hr Maintenance
  - 1 shopping list item: Oil Filter reorder
- [x] Created helper scripts:
  - `/scripts/dev/supabase_start.sh` - Start + migrate + seed
  - `/scripts/dev/supabase_reset.sh` - Reset to clean state
  - `/scripts/dev/supabase_stop.sh` - Stop services

**Blocker:** Docker Desktop not running (required for Supabase local)

### ⏳ Step 3: Storage Sandbox + Fixtures (NEXT)
- [ ] Create fixtures directory
- [ ] Add sample PDF (generator manual)
- [ ] Create upload script for fixtures
- [ ] Configure Supabase Storage buckets

### ⏳ Step 4: Backend Runner + Mocks
- [ ] Create .env.local.example for API
- [ ] Create run_api.sh script
- [ ] Add mock stubs for external services
- [ ] Create wait_for_api.sh health check

### ⏳ Step 5: Frontend Runner
- [ ] Create .env.local.example for web
- [ ] Create run_web.sh script
- [ ] Create wait_for_web.sh health check

### ⏳ Step 6: Automated Proof Harness
- [ ] Create smoke tests (Playwright + pytest)
- [ ] Create prove.sh master script
- [ ] Configure proof bundle output

### ⏳ Step 7: Run & Verify
- [ ] Execute prove.sh
- [ ] Verify all tests pass
- [ ] Generate proof bundle with screenshots

---

## NEXT STEPS

**Immediate:**
1. Start Docker Desktop
2. Run `./scripts/dev/supabase_start.sh` to verify setup
3. Check Supabase Studio at http://127.0.0.1:54323
4. Verify seed data loaded correctly

**Then Continue:**
1. Step 3: Storage sandbox + fixture upload
2. Step 4: Backend runner with mocks
3. Step 5: Frontend runner
4. Step 6: Smoke tests
5. Step 7: Full prove.sh run

---

**Last Updated:** 2026-01-12
**Status:** Step 2 complete (Supabase setup) - awaiting Docker Desktop
**Branch:** universal_v1
**Next:** Start Docker Desktop → test Supabase start → Step 3
