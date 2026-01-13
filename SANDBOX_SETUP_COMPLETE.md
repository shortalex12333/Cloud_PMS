# ✅ LOCAL SANDBOX SETUP - STEPS 1 & 2 COMPLETE

**Date:** 2026-01-12
**Repository:** Cloud_PMS (branch: universal_v1)
**Status:** Supabase local environment configured and ready to test

---

## WHAT'S BEEN COMPLETED

### Step 1: Repo Reconnaissance ✅

**Analyzed:**
- ✅ Service architecture (Next.js 14 frontend + FastAPI backend)
- ✅ Database structure (18 existing migrations)
- ✅ Environment variables (70+ vars documented)
- ✅ Existing handlers (9 handler files with guard compliance)
- ✅ Test infrastructure (extensive smoke tests, stress tests)
- ✅ Dev tooling (Makefile, G0 compliance checkers)

**Documentation Created:**
- `/docs/dev/LOCAL_SANDBOX.md` (430 lines) - Master guide with full implementation plan
- `/docs/dev/SANDBOX_IMPLEMENTATION_SUMMARY.md` (400 lines) - Detailed progress tracker

---

### Step 2: Supabase Local Setup ✅

**1. Initialized Supabase:**
```
/supabase/
├── config.toml              # Local Supabase configuration
├── .gitignore               # Ignore temp files
├── migrations/              # 18 migration files (copied from /database/migrations/)
└── seed.sql                 # Comprehensive test data (268 lines)
```

**Configuration:**
- API Port: 54321 (http://127.0.0.1:54321)
- Database Port: 54322
- Studio Port: 54323 (http://127.0.0.1:54323)
- Email Testing: 54324

**2. Created Seed Data:**

Seed data includes everything needed for end-to-end testing:

**Yacht:**
- M/Y Test Vessel (UUID: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa)
- State: at_dock (safe for testing)
- Flag: Marshall Islands

**Users:**
- admin@test.com (UUID: bbbbbbbb-..., Chief Engineer, $10k signature limit)
- crew@test.com (UUID: cccccccc-..., 2nd Engineer, $1k signature limit)

**Equipment:**
- Main Generator #1 (Caterpillar C18 ACERT)
- Location: Engine Room - Starboard
- Status: operational, Criticality: critical

**Inventory:**
- Oil Filter - CAT 1R0739
- Quantity: 5 (minimum: 3) - will trigger low stock alert at 2
- Location: Shelf A3, Box 12
- Cost: $45.50, Lead time: 7 days

**Documents:**
- CAT C18 Generator Maintenance Manual (placeholder for PDF)
- Links to sample.pdf (to be uploaded in Step 3)

**Work Orders:**
- Generator #1 - 500 Hour Maintenance
- Status: scheduled
- Assigned to crew user

**Shopping List:**
- Oil Filter reorder request (10 units)
- Reason: Stock replenishment for upcoming maintenance

**Search Chunks:**
- Sample maintenance schedule text for search testing

**3. Created Helper Scripts:**

```bash
/scripts/dev/
├── README.md                # Quick reference guide (200 lines)
├── supabase_start.sh        # Start Supabase + migrate + seed ✅
├── supabase_reset.sh        # Reset DB to clean state ✅
└── supabase_stop.sh         # Stop all services ✅
```

All scripts are executable and include detailed help output.

---

## WHAT YOU NEED TO DO NOW

### ⚠️ BLOCKER: Docker Desktop Required

**Current Issue:**
- Supabase local requires Docker Desktop to be running
- Docker daemon is not currently started

**To Resolve:**

1. **If Docker Desktop is installed:**
   ```bash
   # Open Docker Desktop application
   # Wait for green "Docker Desktop is running" indicator
   ```

2. **If Docker Desktop is NOT installed:**
   ```bash
   # macOS
   brew install --cask docker

   # Or download from:
   # https://docs.docker.com/desktop

   # After install, start Docker Desktop
   ```

---

## TESTING THE SETUP (Once Docker is Running)

### Step-by-Step Verification:

**1. Start Supabase:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS
./scripts/dev/supabase_start.sh
```

**Expected Output:**
```
✅ Supabase Started Successfully
📍 Endpoints:
  - API URL: http://127.0.0.1:54321
  - Studio: http://127.0.0.1:54323
  - DB: postgresql://postgres:postgres@127.0.0.1:54322/postgres

🔑 Credentials:
  anon key: eyJh... (long JWT)
  service_role key: eyJh... (long JWT)
  JWT secret: super-secret-jwt-token-...
```

**Look for:**
- ✅ "18 migrations applied"
- ✅ Seed data verification NOTICE messages:
  ```
  NOTICE: ================================
  NOTICE: SEED DATA VERIFICATION
  NOTICE: ================================
  NOTICE: Yachts: 1
  NOTICE: Users: 2
  NOTICE: Equipment: 1
  NOTICE: Parts: 1
  NOTICE: Documents: 1
  NOTICE: Work Orders: 1
  NOTICE: Shopping List: 1
  NOTICE: ✅ Seed data loaded successfully!
  ```

**2. Open Supabase Studio:**
```bash
open http://127.0.0.1:54323
```

**Verify in Studio:**
- Navigate to "Table Editor"
- Check `yacht_registry` table → 1 row (M/Y Test Vessel)
- Check `auth_users_profiles` table → 2 rows (admin, crew)
- Check `pms_parts` table → 1 row (Oil Filter)
- Check `pms_equipment` table → 1 row (Generator)

**3. Create Auth Users (Important!):**

The seed data creates user **profiles**, but not auth users. You need to create them in Studio:

1. In Studio, go to "Authentication" → "Users"
2. Click "Add User" → "Create new user"
3. Create admin:
   - Email: admin@test.com
   - Password: password123
   - **User ID:** bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb (must match seed data!)
4. Create crew:
   - Email: crew@test.com
   - Password: password123
   - **User ID:** cccccccc-cccc-cccc-cccc-cccccccccccc (must match seed data!)

Alternatively, use SQL in Studio:
```sql
-- Run in SQL Editor
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  confirmation_token,
  raw_app_meta_data,
  raw_user_meta_data
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  'authenticated',
  'authenticated',
  'admin@test.com',
  crypt('password123', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW(),
  '',
  '{"provider":"email","providers":["email"]}',
  '{}'
);

-- Repeat for crew user with UUID: cccccccc-cccc-cccc-cccc-cccccccccccc
```

**4. Test Database Connection:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Run test query:
SELECT name FROM yacht_registry;
# Expected: M/Y Test Vessel

\q  # Exit
```

---

## WHAT'S NEXT (Steps 3-7)

Once Supabase is verified working, you can proceed with:

### Step 3: Storage Sandbox + Fixtures
- Create `/fixtures/docs/sample.pdf` (generator manual excerpt)
- Create upload script to push to Supabase Storage
- Verify document accessible via API

### Step 4: Backend Runner + Mocks
- Create `.env.local` for API with Supabase credentials
- Create `run_api.sh` to start FastAPI backend
- Add mock stubs for external services (search, predictive)
- Verify API health endpoint responds

### Step 5: Frontend Runner
- Create `.env.local` for web with Supabase credentials
- Create `run_web.sh` to start Next.js
- Verify frontend loads at http://localhost:3000
- Test login with admin@test.com

### Step 6: Automated Proof Harness
- Install Playwright for frontend tests
- Create smoke tests (document viewer, microaction execution)
- Create `prove.sh` master script
- Generate proof bundle with screenshots

### Step 7: GitHub Workflow (Optional)
- Create CI workflow for automated testing on push
- Run migrations + smoke tests in GitHub Actions

---

## FILES CREATED (Summary)

**Documentation:**
```
/docs/dev/
├── LOCAL_SANDBOX.md (430 lines) - Master guide
├── SANDBOX_IMPLEMENTATION_SUMMARY.md (400 lines) - Progress tracker
```

**Supabase Configuration:**
```
/supabase/
├── config.toml (12KB) - Supabase local config
├── seed.sql (268 lines) - Test data with verification
├── .gitignore - Ignore temp files
└── migrations/ (18 files) - All DB migrations
```

**Scripts:**
```
/scripts/dev/
├── README.md (200 lines) - Quick reference
├── supabase_start.sh ✅ - Start + migrate + seed
├── supabase_reset.sh ✅ - Reset to clean state
└── supabase_stop.sh ✅ - Stop services
```

**Root Handoff:**
```
/SANDBOX_SETUP_COMPLETE.md (this file)
```

---

## QUICK REFERENCE

**Start Supabase:**
```bash
./scripts/dev/supabase_start.sh
```

**Reset Database:**
```bash
./scripts/dev/supabase_reset.sh
```

**Stop Supabase:**
```bash
./scripts/dev/supabase_stop.sh
```

**Check Status:**
```bash
supabase status
```

**View Logs:**
```bash
supabase logs
```

**Open Studio:**
```bash
open http://127.0.0.1:54323
```

---

## TROUBLESHOOTING

**"Cannot connect to Docker daemon"**
- Start Docker Desktop
- Wait for green indicator
- Retry `supabase_start.sh`

**"Migrations failed"**
- Check syntax in `/supabase/migrations/`
- Review logs: `supabase logs`
- Reset: `./scripts/dev/supabase_reset.sh`

**"Seed data not visible"**
- Look for NOTICE messages in terminal
- Check Studio tables manually
- Verify seed.sql ran (no errors in logs)

**"Port 54321 already in use"**
- Stop existing Supabase: `supabase stop`
- Or change port in `/supabase/config.toml`

---

## SUCCESS CRITERIA

✅ **You'll know setup is working when:**
1. `./scripts/dev/supabase_start.sh` completes without errors
2. Studio opens at http://127.0.0.1:54323
3. Database tables contain seed data (1 yacht, 2 users, etc.)
4. Auth users created (admin@test.com, crew@test.com)
5. Can query database via psql

---

## NEXT IMMEDIATE ACTION

1. ✅ Start Docker Desktop (if not running)
2. ✅ Run `./scripts/dev/supabase_start.sh`
3. ✅ Verify seed data in Studio (http://127.0.0.1:54323)
4. ✅ Create auth users (admin, crew)
5. ⏳ Proceed to Step 3 (fixtures + storage)

---

**Documentation:** `/docs/dev/LOCAL_SANDBOX.md`
**Progress Tracker:** `/docs/dev/SANDBOX_IMPLEMENTATION_SUMMARY.md`
**Scripts Guide:** `/scripts/dev/README.md`

**Status:** 2/7 steps complete
**Ready for:** Docker Desktop → Supabase verification → Step 3
**Last Updated:** 2026-01-12
