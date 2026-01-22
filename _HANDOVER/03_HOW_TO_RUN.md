# 03 - HOW TO RUN TESTS

## Environment Setup

### Required Environment Variables

Create `.env` file or export these:

```bash
# Master database (user management)
MASTER_SUPABASE_URL=https://xxx.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Tenant database (yacht data)
TENANT_SUPABASE_URL=https://yyy.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Test user
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=...
```

### Install Dependencies

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
npm install
npx playwright install
```

---

## Test Commands

### 1. Health Check (Run This First)

```bash
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium
```

**Expected Output:**
```
SYSTEM HEALTH SCORE: 95%
61 passed (5m)
```

### 2. NL→Action Coverage

```bash
npx playwright test tests/e2e/nl_to_action_mapping.spec.ts --project=e2e-chromium
```

**Expected Output:**
```
64 passed (4.5m)
```

### 3. Full E2E Chat Flow

```bash
npx playwright test tests/e2e/chat_to_action.spec.ts --project=e2e-chromium
```

**Expected Output:**
```
21 passed
```

### 4. Single Action Test

```bash
# Test specific action
npx playwright test tests/e2e/diagnostic_baseline.spec.ts -g "diagnose_fault"

# Test specific cluster
npx playwright test tests/e2e/diagnostic_baseline.spec.ts -g "fix_something"
```

### 5. Debug Mode (UI)

```bash
# Opens browser UI
npx playwright test --ui

# Step-through debugging
npx playwright test --debug
```

### 6. See All Output

```bash
# Verbose output
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium 2>&1 | tee test_output.txt
```

---

## Quick Reference

| What You Want | Command |
|---------------|---------|
| Full health check | `npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium` |
| NL test coverage | `npx playwright test tests/e2e/nl_to_action_mapping.spec.ts --project=e2e-chromium` |
| Single action | `npx playwright test -g "action_name"` |
| With browser UI | `npx playwright test --ui` |
| Debug mode | `npx playwright test --debug` |
| All tests | `npx playwright test --project=e2e-chromium` |

---

## Backend Commands (if needed)

```bash
# Start backend locally
cd apps/api
uvicorn main:app --reload --port 8000

# Run Python tests
pytest tests/

# Check specific handler
grep -A 50 'elif action == "diagnose_fault"' apps/api/routes/p0_actions_routes.py
```

---

## Database Commands (Supabase)

```bash
# Using Supabase CLI
supabase db dump -f schema.sql

# Direct psql (if you have connection string)
psql $DATABASE_URL -c "SELECT * FROM pms_faults LIMIT 5;"
```

---

## Useful Grep Commands

```bash
# Find all action handlers
grep 'elif action ==' apps/api/routes/p0_actions_routes.py

# Count handlers
grep -c 'elif action ==' apps/api/routes/p0_actions_routes.py
# Should return: 81

# Find specific handler
grep -A 30 'elif action == "create_work_order"' apps/api/routes/p0_actions_routes.py

# Find all REQUIRED_FIELDS definitions
grep -B 2 'REQUIRED_FIELDS' apps/api/routes/p0_actions_routes.py
```

---

## If Tests Fail

1. **Check environment variables are set**
   ```bash
   echo $TENANT_SUPABASE_URL
   ```

2. **Check backend is running**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check test data exists**
   ```bash
   # The test auto-discovers data, but you can check manually
   npx ts-node -e "
   const { discoverTestData } = require('./tests/helpers/test-data-discovery');
   discoverTestData().then(console.log);
   "
   ```

4. **Check the known issues**
   - See `04_KNOWN_TRAPS.md`
   - See `../KNOWN_ISSUES.md`

---

*Updated: 2026-01-22*
