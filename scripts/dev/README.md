# Development Scripts
**Purpose:** Local sandbox environment management scripts for Cloud_PMS

---

## Quick Start

**Prerequisites:**
1. Docker Desktop installed and running
2. Supabase CLI installed (`brew install supabase/tap/supabase`)
3. Node.js 20+, Python 3.11+

**One-Time Setup:**
```bash
# 1. Start Supabase (runs migrations + seed data)
./scripts/dev/supabase_start.sh

# 2. Verify in Supabase Studio
open http://127.0.0.1:54323

# 3. Create auth users (in Studio):
#    - admin@test.com / password123 (link to UUID: bbbbbbbb-...)
#    - crew@test.com / password123 (link to UUID: cccccccc-...)

# 4. Upload fixtures (when implemented)
# ./scripts/dev/upload_fixture_docs.sh

# 5. Start backend (when implemented)
# ./scripts/dev/run_api.sh

# 6. Start frontend (when implemented - separate terminal)
# ./scripts/dev/run_web.sh
```

**Daily Use:**
```bash
# Start everything (when prove.sh is complete)
./scripts/dev/prove.sh
```

---

## Available Scripts

### Supabase Management

**`supabase_start.sh`**
- Starts local Supabase instance
- Runs all 18 migrations automatically
- Loads seed data (1 yacht, 2 users, test data)
- Outputs API keys and connection strings

**Usage:**
```bash
./scripts/dev/supabase_start.sh
```

**Output:**
- API URL: http://127.0.0.1:54321
- Studio: http://127.0.0.1:54323
- DB: postgresql://postgres:postgres@127.0.0.1:54322/postgres
- Anon key, service key, JWT secret (copy to .env.local)

---

**`supabase_reset.sh`**
- Resets database to clean state
- Re-runs all migrations
- Re-loads seed data
- **WARNING:** Deletes all local data

**Usage:**
```bash
./scripts/dev/supabase_reset.sh
# Prompts for confirmation (y/N)
```

**Use when:**
- Migrations changed
- Seed data updated
- Database in bad state

---

**`supabase_stop.sh`**
- Stops all Supabase services
- Preserves data (restart with supabase_start.sh)

**Usage:**
```bash
./scripts/dev/supabase_stop.sh
```

---

### Storage & Fixtures (PENDING)

**`upload_fixture_docs.sh`** (not yet implemented)
- Uploads sample PDFs to Supabase Storage
- Creates storage buckets if needed
- Links to seed data documents

**Planned usage:**
```bash
./scripts/dev/upload_fixture_docs.sh
# Uploads: /fixtures/docs/sample.pdf
# Bucket: documents
# Links to: pms_documents record (UUID: ffffffff-...)
```

---

### Backend Management (PENDING)

**`run_api.sh`** (not yet implemented)
- Starts FastAPI backend on port 8000
- Loads .env.local
- Enables mock external services
- Logs to /logs/api.log

**Planned usage:**
```bash
./scripts/dev/run_api.sh
# Starts: http://localhost:8000
# Health: http://localhost:8000/health
```

---

**`wait_for_api.sh`** (not yet implemented)
- Polls API health endpoint
- Blocks until API ready or timeout
- Used by prove.sh

**Planned usage:**
```bash
./scripts/dev/wait_for_api.sh
# Polls: GET http://localhost:8000/health
# Timeout: 30 seconds
```

---

### Frontend Management (PENDING)

**`run_web.sh`** (not yet implemented)
- Starts Next.js frontend on port 3000
- Loads .env.local
- Logs to /logs/web.log

**Planned usage:**
```bash
./scripts/dev/run_web.sh
# Starts: http://localhost:3000
# Opens browser automatically
```

---

**`wait_for_web.sh`** (not yet implemented)
- Polls frontend until ready
- Blocks until loaded or timeout
- Used by prove.sh

**Planned usage:**
```bash
./scripts/dev/wait_for_web.sh
# Polls: http://localhost:3000
# Timeout: 60 seconds
```

---

### Testing & Proof (PENDING)

**`prove.sh`** (not yet implemented)
- Master script - runs full sandbox
- Starts all services
- Runs smoke tests
- Generates proof bundle

**Planned usage:**
```bash
./scripts/dev/prove.sh
# Output: /proof/<timestamp>/
# Contains: screenshots, logs, test results
```

**Acceptance criteria:**
- ✅ Supabase started
- ✅ Migrations applied (18/18)
- ✅ Seed data loaded
- ✅ Fixtures uploaded
- ✅ API health: PASS
- ✅ Frontend loads: PASS
- ✅ Document viewer: PASS
- ✅ Microaction execute: PASS
- ✅ Proof bundle generated

---

## Seed Data Reference

**Yacht:**
- ID: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`
- Name: M/Y Test Vessel
- State: at_dock

**Users:**
- Admin: `bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb`
  - Email: admin@test.com
  - Role: Chief Engineer
  - Signature limit: $10,000
- Crew: `cccccccc-cccc-cccc-cccc-cccccccccccc`
  - Email: crew@test.com
  - Role: 2nd Engineer
  - Signature limit: $1,000

**Equipment:**
- ID: `dddddddd-dddd-dddd-dddd-dddddddddddd`
- Name: Main Generator #1
- Type: Caterpillar C18 ACERT

**Parts:**
- ID: `eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee`
- Name: Oil Filter - CAT 1R0739
- Quantity: 5 (min: 3)
- Location: Shelf A3, Box 12

**Documents:**
- ID: `ffffffff-ffff-ffff-ffff-ffffffffffff`
- Title: CAT C18 Generator Maintenance Manual
- File: sample.pdf (to be uploaded)

**Work Orders:**
- ID: `11111111-1111-1111-1111-111111111111`
- Title: Generator #1 - 500 Hour Maintenance
- Status: scheduled

---

## Troubleshooting

**"Docker daemon not running"**
- Start Docker Desktop
- Wait for green indicator
- Retry script

**"Migrations failed"**
- Check migration syntax in `/supabase/migrations/`
- Review Supabase logs: `supabase logs`
- Reset and retry: `./scripts/dev/supabase_reset.sh`

**"Seed data not loaded"**
- Check seed.sql syntax
- Look for NOTICE messages in terminal output
- Verify in Studio: http://127.0.0.1:54323

**"Port already in use"**
- Stop conflicting services
- Or stop Supabase: `./scripts/dev/supabase_stop.sh`
- Change ports in `/supabase/config.toml`

---

## File Locations

```
/Users/celeste7/Documents/Cloud_PMS/
├── docs/dev/
│   ├── LOCAL_SANDBOX.md             # Master documentation
│   └── SANDBOX_IMPLEMENTATION_SUMMARY.md  # Progress tracker
├── scripts/dev/                     # This directory
│   ├── README.md                    # This file
│   ├── supabase_start.sh            ✅
│   ├── supabase_reset.sh            ✅
│   ├── supabase_stop.sh             ✅
│   ├── upload_fixture_docs.sh       ⏳ (pending)
│   ├── run_api.sh                   ⏳ (pending)
│   ├── wait_for_api.sh              ⏳ (pending)
│   ├── run_web.sh                   ⏳ (pending)
│   ├── wait_for_web.sh              ⏳ (pending)
│   └── prove.sh                     ⏳ (pending)
├── supabase/
│   ├── config.toml                  ✅
│   ├── seed.sql                     ✅
│   └── migrations/                  ✅ (18 files)
├── fixtures/docs/                   ⏳ (to create)
│   └── sample.pdf                   ⏳
└── proof/                           ⏳ (auto-generated)
    └── <timestamp>/
```

---

**Status:** 3/9 scripts complete (Supabase management)
**Next:** Implement fixture upload, API runner, frontend runner, prove.sh
**Documentation:** See `/docs/dev/LOCAL_SANDBOX.md`
**Last Updated:** 2026-01-12
