# LOCAL SANDBOX IMPLEMENTATION SUMMARY
**Date:** 2026-01-12
**Branch:** universal_v1
**Purpose:** Track progress on local simulation environment for Cloud_PMS

---

## OVERVIEW

**Goal:** Create one-command local sandbox for testing CelesteOS end-to-end before merging changes.

**Acceptance Criteria:**
```bash
./scripts/dev/prove.sh
```

Expected output:
- ✅ Supabase started (all 18 migrations applied)
- ✅ Seed data loaded (1 yacht, 2 users, test data)
- ✅ API health check passing
- ✅ Frontend loads with document viewer
- ✅ At least one microaction executes
- ✅ Proof bundle generated with screenshots

---

## COMPLETED (Steps 1-2)

### Step 1: Repo Reconnaissance ✅

**Files Created:**
- `/docs/dev/LOCAL_SANDBOX.md` (430 lines) - Master documentation

**Findings Documented:**
- **Frontend:** Next.js 14 in `/apps/web/` (port 3000)
- **Backend:** FastAPI in `/apps/api/` (port 8000, entry: `pipeline_service.py`)
- **Database:** 18 migrations in `/database/migrations/`
- **Handlers:** 9 handler files with guard compliance
- **Tests:** Extensive test suite (stress tests, pattern validation, SQL campaigns)
- **Environment:** 70+ env vars in `.env.example`

**Dev Tools Found:**
- Makefile with `dev-web`, `dev-api`, `test` commands
- G0 compliance checkers (v1, v2)
- Synthetic data population script
- No existing Supabase local config (created in Step 2)

---

### Step 2: Supabase Local Setup ✅

**Files Created:**

1. **Supabase Configuration**
   ```
   /supabase/
   ├── config.toml              ✅ (12KB, Supabase local config)
   ├── .gitignore               ✅
   ├── migrations/              ✅ (18 migration files copied)
   └── seed.sql                 ✅ (268 lines)
   ```

2. **Migration Files** (all 18 copied with timestamps):
   ```
   00000000000000_00_enable_extensions.sql
   00000000000001_01_core_tables_v2_secure.sql
   00000000000002_01_core_tables.sql
   ...
   00000000000017_11_create_get_user_auth_info_rpc.sql
   ```

3. **Seed Data** (`/supabase/seed.sql`):
   - 1 yacht: M/Y Test Vessel (UUID: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)
   - 2 users:
     - admin@test.com (UUID: bbbbbbbb-..., Chief Engineer, $10k limit)
     - crew@test.com (UUID: cccccccc-..., 2nd Engineer, $1k limit)
   - 1 equipment: Main Generator #1 (Caterpillar C18)
   - 1 part: Oil Filter CAT 1R0739 (qty: 5, min: 3, $45.50)
   - 1 document: Generator Manual (PDF placeholder)
   - 1 work order: 500hr Generator Maintenance
   - 1 shopping list item: Oil Filter reorder (10 units)
   - 1 search chunk: Maintenance schedule text
   - Verification queries with NOTICE output

4. **Helper Scripts:**
   ```
   /scripts/dev/
   ├── supabase_start.sh        ✅ (Start + migrate + seed)
   ├── supabase_reset.sh        ✅ (Reset DB to clean state)
   └── supabase_stop.sh         ✅ (Stop services)
   ```

**Supabase Ports:**
- API: 54321 (http://127.0.0.1:54321)
- DB: 54322 (postgresql://postgres:postgres@127.0.0.1:54322/postgres)
- Studio: 54323 (http://127.0.0.1:54323)
- Inbucket (Email): 54324

**Blocker Identified:**
- ⚠️  Docker Desktop not running (required for `supabase start`)
- User needs to start Docker Desktop before testing

---

## REMAINING WORK (Steps 3-7)

### Step 3: Storage Sandbox + Fixtures (PENDING)

**To Create:**
```
/fixtures/docs/
└── sample.pdf                   # Sample yacht manual (5-10 pages)

/scripts/dev/
└── upload_fixture_docs.sh       # Upload sample.pdf to Supabase Storage
```

**Tasks:**
1. Create `/fixtures/docs/` directory
2. Generate or copy sample PDF (CAT C18 Generator Manual excerpt)
3. Create upload script:
   - Use Supabase client to upload to `documents` bucket
   - Set metadata (yacht_id, document_type, etc.)
   - Link to seed data document record (UUID: ffffffff-...)
4. Create storage buckets in seed.sql or via script:
   - `documents` bucket (private, PDF only)
   - `photos` bucket (private, images only)

**Acceptance:**
- `./scripts/dev/upload_fixture_docs.sh` uploads successfully
- Navigate to http://127.0.0.1:54323 → Storage → see sample.pdf
- Document record in `pms_documents` links to storage object

---

### Step 4: Backend Runner + Mocks (PENDING)

**To Create:**
```
/apps/api/
├── .env.local.example           # Local env vars
└── stubs/
    ├── mock_search_engine.py    # Mock search responses
    └── mock_predictive_engine.py # Mock predictions

/scripts/dev/
├── run_api.sh                   # Start API with local env
└── wait_for_api.sh              # Health check poller
```

**Tasks:**
1. Create `.env.local.example` for API:
   ```bash
   NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
   SUPABASE_SERVICE_KEY=<from supabase status>
   SUPABASE_JWT_SECRET=<from supabase status>
   MOCK_SEARCH_ENGINE=true
   MOCK_PREDICTIVE_ENGINE=true
   OPENAI_API_KEY=sk-test-mock-key  # Optional mock
   ```

2. Create mock stubs:
   - `mock_search_engine.py`: Return hardcoded entities/actions
   - `mock_predictive_engine.py`: Return stub maintenance predictions
   - OCR mock: Return placeholder text for PDF processing

3. Update `pipeline_service.py` to use mocks when env var set

4. Create `run_api.sh`:
   - Load `.env.local`
   - Start uvicorn on port 8000
   - Log to `/logs/api.log`

5. Create `wait_for_api.sh`:
   - Poll GET /health until 200 response
   - Timeout after 30 seconds

**Acceptance:**
- `./scripts/dev/run_api.sh` starts API successfully
- GET http://localhost:8000/health returns 200
- Mock endpoints return stub data (not calling external services)

---

### Step 5: Frontend Runner (PENDING)

**To Create:**
```
/apps/web/
└── .env.local.example           # Local env vars

/scripts/dev/
├── run_web.sh                   # Start Next.js with local env
└── wait_for_web.sh              # Health check poller
```

**Tasks:**
1. Create `.env.local.example` for web:
   ```bash
   NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<from supabase status>
   NEXT_PUBLIC_CLOUD_API_URL=http://localhost:8000
   NODE_ENV=development
   ```

2. Create `run_web.sh`:
   - Load `.env.local`
   - Run `npm run dev` on port 3000
   - Log to `/logs/web.log`

3. Create `wait_for_web.sh`:
   - Poll http://localhost:3000 until server ready
   - Timeout after 60 seconds

**Acceptance:**
- `./scripts/dev/run_web.sh` starts frontend successfully
- Navigate to http://localhost:3000
- Login page appears
- Can login as admin@test.com (after creating auth user)

---

### Step 6: Automated Proof Harness (PENDING)

**To Create:**
```
/tests/smoke/
├── document_viewer.spec.ts      # Playwright: View PDF
├── situation_microaction.spec.ts # Playwright: Execute action
├── api_health.spec.ts           # Playwright API test
└── api/
    ├── test_health.py           # pytest: API health
    ├── test_microaction.py      # pytest: Execute log_part_usage
    └── conftest.py              # pytest fixtures

/scripts/dev/
└── prove.sh                     # Master test runner

/proof/                          # Gitignored output directory
```

**Tasks:**
1. Install Playwright:
   ```bash
   cd apps/web && npx playwright install
   ```

2. Create Playwright tests:
   - `document_viewer.spec.ts`: Login → navigate to docs → verify PDF loads
   - `situation_microaction.spec.ts`: Create situation → execute log_part_usage → verify audit log
   - `api_health.spec.ts`: Call /health endpoint

3. Create pytest tests:
   - `test_health.py`: GET /health returns 200
   - `test_microaction.py`: POST /execute with log_part_usage → verify response

4. Create `prove.sh` master script:
   ```bash
   #!/bin/bash
   # 1. Start Docker Desktop check
   # 2. Start Supabase (supabase_start.sh)
   # 3. Upload fixtures (upload_fixture_docs.sh)
   # 4. Start API (run_api.sh) in background
   # 5. Wait for API (wait_for_api.sh)
   # 6. Start Web (run_web.sh) in background
   # 7. Wait for Web (wait_for_web.sh)
   # 8. Run pytest smoke tests
   # 9. Run Playwright smoke tests
   # 10. Generate proof bundle
   # 11. Cleanup (stop services)
   ```

5. Proof bundle output structure:
   ```
   /proof/<timestamp>/
   ├── summary.txt              # Pass/fail counts
   ├── environment.txt          # Versions, config
   ├── screenshots/
   │   ├── login.png
   │   ├── document_viewer.png
   │   └── situation_created.png
   ├── logs/
   │   ├── supabase.log
   │   ├── api.log
   │   └── web.log
   └── test_results.json        # Structured results
   ```

**Acceptance:**
- `./scripts/dev/prove.sh` runs without errors
- All smoke tests pass
- Proof bundle generated with timestamp
- Screenshots captured for key flows

---

### Step 7: GitHub Workflow (OPTIONAL)

**To Create:**
```
/.github/workflows/
└── sandbox_smoke.yml            # CI workflow
```

**Tasks:**
1. Create workflow triggered on:
   - Push to `universal_v1`
   - PR to `main`

2. Workflow steps:
   - Install Supabase CLI
   - Start Supabase
   - Run migrations
   - Seed data
   - Run API smoke tests (pytest)
   - Upload test results as artifact

**Acceptance:**
- Workflow runs on push
- Tests pass in CI
- Results visible in GitHub Actions

---

## TESTING CHECKLIST

**Once Docker Desktop is running:**

1. **Verify Supabase Setup:**
   ```bash
   ./scripts/dev/supabase_start.sh
   # Check: Migrations applied (18/18)
   # Check: Seed data verification shows ✅
   ```

2. **Verify Studio Access:**
   ```bash
   open http://127.0.0.1:54323
   # Check: Can browse tables
   # Check: See seed data (1 yacht, 2 users, etc.)
   ```

3. **Verify Auth Users:**
   ```bash
   # In Studio, create auth users:
   # - admin@test.com / password123
   # - crew@test.com / password123
   # Link to existing profiles (UUIDs in seed.sql)
   ```

4. **Continue with Step 3** (Storage + Fixtures)

---

## FILES MANIFEST

**Documentation:**
- `/docs/dev/LOCAL_SANDBOX.md` (430 lines) - Master guide
- `/docs/dev/SANDBOX_IMPLEMENTATION_SUMMARY.md` (this file)

**Supabase:**
- `/supabase/config.toml` - Local config
- `/supabase/seed.sql` (268 lines) - Test data
- `/supabase/migrations/` - 18 migration files

**Scripts:**
- `/scripts/dev/supabase_start.sh` - Start Supabase
- `/scripts/dev/supabase_reset.sh` - Reset database
- `/scripts/dev/supabase_stop.sh` - Stop Supabase

**Pending (Steps 3-7):**
- Fixture upload scripts
- API/Web runner scripts
- Mock service stubs
- Smoke tests (Playwright + pytest)
- Master prove.sh script
- GitHub workflow

---

## BLOCKER RESOLUTION

**Current Blocker:** Docker Desktop not running

**To Resolve:**
1. Start Docker Desktop application
2. Wait for Docker daemon to start (green indicator)
3. Run: `./scripts/dev/supabase_start.sh`
4. Verify output shows migrations applied and seed data loaded

**If Docker not installed:**
```bash
# macOS
brew install --cask docker

# Or download from:
# https://docs.docker.com/desktop
```

---

## NEXT ACTION

**Immediate:**
1. ✅ Start Docker Desktop
2. ✅ Run `./scripts/dev/supabase_start.sh`
3. ✅ Verify Supabase Studio at http://127.0.0.1:54323
4. ✅ Check seed data loaded (NOTICE output in logs)
5. ✅ Create auth users in Studio (admin@test.com, crew@test.com)

**Then:**
1. ⏳ Step 3: Create fixtures + upload script
2. ⏳ Step 4: Backend runner + mocks
3. ⏳ Step 5: Frontend runner
4. ⏳ Step 6: Smoke tests + prove.sh
5. ⏳ Step 7: GitHub workflow (optional)

---

**Status:** 2/7 steps complete (Reconnaissance + Supabase setup)
**Blocker:** Docker Desktop (user action required)
**Ready for:** User to start Docker → test Supabase → proceed to Step 3
**Last Updated:** 2026-01-12
