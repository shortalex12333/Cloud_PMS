# Local Setup Guide

**Get your environment running in 10 minutes**

**Purpose:** Set up local development and testing environment
**Audience:** New engineers
**Prerequisites:** macOS, Windows, or Linux with terminal access

---

## ✅ Prerequisites

### Required Software

**1. Node.js 18+**
```bash
# Check version
node --version  # Should be v18.x.x or higher

# Install if needed (macOS)
brew install node

# Install if needed (Windows)
# Download from: https://nodejs.org

# Install if needed (Linux)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**2. Python 3.12+ (for backend development)**
```bash
# Check version
python3 --version  # Should be 3.12.x or higher

# Install if needed (macOS)
brew install python@3.12

# Install if needed (Windows)
# Download from: https://www.python.org

# Install if needed (Linux)
sudo apt-get install python3.12
```

**3. Git**
```bash
# Check version
git --version

# Should already be installed on most systems
```

**Optional but Recommended:**

**4. PostgreSQL Client (psql) - for database queries**
```bash
# Install (macOS)
brew install postgresql

# Install (Windows)
# Download from: https://www.postgresql.org

# Install (Linux)
sudo apt-get install postgresql-client
```

**5. VS Code or your preferred editor**
- Download from: https://code.visualstudio.com

---

## 📦 Installation Steps

### Step 1: Clone Repository

```bash
# If you haven't already
git clone <repository-url>
cd BACK_BUTTON_CLOUD_PMS
```

### Step 2: Install Dependencies

**Install root dependencies:**
```bash
npm install
```

**Install backend dependencies (optional for testing):**
```bash
cd apps/api
pip install -r requirements.txt
cd ../..
```

**Install frontend dependencies (optional for UI testing):**
```bash
cd apps/web
npm install
cd ../..
```

**Expected output:**
```
added 500+ packages in 30s
```

**If errors:** See Troubleshooting section below

---

## 🔐 Environment Configuration

### Step 3: Copy Environment Template

```bash
# Copy the example file
cp .env.e2e.example .env.e2e
```

**Important:** `.env.e2e` is gitignored. Never commit credentials!

### Step 4: Get Credentials from Team

**You need these credentials:**

1. **TENANT_SUPABASE_URL** - Supabase project URL for tenant database
2. **TENANT_SUPABASE_SERVICE_ROLE_KEY** - Service role key (bypasses RLS)
3. **TEST_YACHT_ID** - UUID of test yacht
4. **TEST_USER_ID** - UUID of test user

**How to get them:**
- Ask team lead or check secure credential store
- For test environment: Check team documentation
- **NEVER** use production credentials for local testing!

### Step 5: Fill in .env.e2e

**Edit `.env.e2e` with your editor:**
```bash
# Example values (replace with real ones)
TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

**Check that it's loaded:**
```bash
# Should show your values
node -e "require('dotenv').config({path: '.env.e2e'}); console.log(process.env.TENANT_SUPABASE_URL)"
```

---

## ✅ Verify Setup

### Step 6: Run One Test

**Run the gold standard mutation proof test:**
```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

**Expected output (PASS):**
```
Running 1 test using 1 worker

  ✓  tests/e2e/mutation_proof_create_work_order.spec.ts:XX:XX
     create_work_order mutation proof (2s)

1 passed (3s)
```

**If you see warnings about audit log:**
```
⚠️ WARNING: No audit log entry found for work_order_id...
```
**This is EXPECTED** - It's a known gap we're documenting. Test should still pass.

**If test passes:** ✅ You're set up correctly!

**If test fails:** See Troubleshooting section below

---

## 🧪 Running Tests

### Run All Tests
```bash
npx playwright test
```

### Run Specific Test
```bash
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts
```

### Run With UI (Visual Debugging)
```bash
npx playwright test --ui
```

### Run in Debug Mode
```bash
npx playwright test --debug
```

### Run Specific Browser
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Generate Test Report
```bash
npx playwright test
npx playwright show-report
```

---

## 🗄️ Database Access

### Option 1: Supabase Studio (GUI - Easiest)

**Access:**
1. Open browser to: https://vzsohavtuotocgrfkfyd.supabase.co
2. Login with team credentials
3. Navigate to: Table Editor
4. Select table (e.g., pms_work_orders)
5. Run queries in SQL Editor

**Pros:** Visual, easy to explore
**Cons:** Requires browser, slower for automation

### Option 2: Node.js Scripts (Recommended)

**Run utility scripts:**
```bash
# List all tables
node scripts/list_tables.js

# Analyze audit log
node scripts/analyze_pms_audit_log.js

# Check specific action
node scripts/check_create_wo_audit.js
```

**Pros:** Fast, scriptable, uses .env.e2e
**Cons:** Requires writing scripts

### Option 3: psql (Command Line)

**Connect to database:**
```bash
# Get connection string from Supabase dashboard
psql "postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
```

**Run queries:**
```sql
-- List tables
\dt pms_*

-- Query work orders
SELECT * FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 10;

-- Check audit log
SELECT * FROM pms_audit_log
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY created_at DESC
LIMIT 10;
```

**Pros:** Full SQL power, fast
**Cons:** Command-line only

### Option 4: Node.js REPL (Quick Queries)

**Start interactive session:**
```bash
node
```

**Run queries:**
```javascript
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({path: '.env.e2e'});

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);

// Query work orders
const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('yacht_id', process.env.TEST_YACHT_ID)
  .limit(5);

console.log(data);
```

**Pros:** Interactive, uses .env.e2e, JavaScript syntax
**Cons:** Requires Node.js knowledge

---

## 🚀 Running Services Locally

### Frontend (Next.js)

```bash
cd apps/web
npm run dev
```

**Access:** http://localhost:3000/app

**Expected:** SpotlightSearch interface

**Note:** Backend must be running separately for actions to work

### Backend (FastAPI)

```bash
cd apps/api
uvicorn pipeline_service:app --reload
```

**Access:** http://localhost:8000/docs (Swagger UI)

**Expected:** FastAPI interactive docs

**Endpoints:**
- POST /search - Natural language query → actions
- POST /v1/actions/execute - Execute microaction

### Full Stack (Both)

**Terminal 1:**
```bash
cd apps/api
uvicorn pipeline_service:app --reload
```

**Terminal 2:**
```bash
cd apps/web
npm run dev
```

**Test:** Open http://localhost:3000/app, type query, should detect actions

---

## 🐛 Troubleshooting

### Error: "supabaseUrl is required"

**Symptom:**
```
Error: supabaseUrl is required.
```

**Cause:** .env.e2e not loaded

**Fix:**
```bash
# Check file exists
ls -la .env.e2e

# Check file has content
cat .env.e2e

# Ensure script loads it
# In your script, add:
require('dotenv').config({path: '.env.e2e'});
```

### Error: "Invalid API key"

**Symptom:**
```
Error: Invalid API key
```

**Cause:** Wrong or expired service role key

**Fix:**
1. Check .env.e2e has correct key
2. Verify key in Supabase dashboard
3. Key should start with `eyJhbGciOiJIUzI1NiI...`
4. Ask team for updated key if expired

### Error: "Could not find the table"

**Symptom:**
```
Error: Could not find the table 'public.pms_work_orders' in the schema cache
```

**Cause:** Table doesn't exist in database OR wrong database URL

**Fix:**
1. Check TENANT_SUPABASE_URL is correct
2. Verify table exists: `node scripts/list_tables.js`
3. Check you're not using master DB URL (should be tenant DB)

### Error: "Playwright not installed"

**Symptom:**
```
Error: Playwright Test did not expect test() to be called here.
```

**Cause:** Playwright browsers not installed

**Fix:**
```bash
npx playwright install
```

### Error: "Cannot find module"

**Symptom:**
```
Error: Cannot find module '@supabase/supabase-js'
```

**Cause:** Dependencies not installed

**Fix:**
```bash
# Root
npm install

# Frontend
cd apps/web && npm install

# Backend
cd apps/api && pip install -r requirements.txt
```

### Test Times Out

**Symptom:**
```
Test timeout of 30000ms exceeded
```

**Cause:** Network slow, database slow, or action hanging

**Fix:**
```bash
# Increase timeout
npx playwright test --timeout=60000

# Or in test file:
test.setTimeout(60000);
```

### Database Query Returns 0 Rows

**Symptom:**
```
Expected: 1 row
Actual: 0 rows
```

**Cause:** RLS filtering out rows (wrong yacht_id) OR data doesn't exist

**Fix:**
```javascript
// Always include yacht_id filter
const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('yacht_id', process.env.TEST_YACHT_ID)  // ← CRITICAL
  .eq('id', work_order_id);

// If still 0 rows, check if work order actually exists
const { data: all } = await supabase
  .from('pms_work_orders')
  .select('*', { count: 'exact' });
console.log('Total work orders:', all.length);
```

### Port Already in Use

**Symptom:**
```
Error: Port 3000 is already in use
```

**Cause:** Another process using port

**Fix:**
```bash
# Kill process on port 3000 (macOS/Linux)
lsof -ti:3000 | xargs kill -9

# Or use different port
PORT=3001 npm run dev
```

### Python Import Error

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Cause:** Python dependencies not installed

**Fix:**
```bash
cd apps/api
pip install -r requirements.txt

# If using virtual env (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🔧 Advanced Setup

### Using Virtual Environment (Python)

**Recommended for backend development:**
```bash
cd apps/api

# Create virtual env
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Deactivate when done
deactivate
```

### Using NVM (Node Version Manager)

**Recommended for managing Node versions:**
```bash
# Install nvm (macOS/Linux)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install Node 18
nvm install 18
nvm use 18

# Verify
node --version  # Should be v18.x.x
```

### Using Docker (Optional)

**Not required, but available:**
```bash
# Build
docker build -t celeste-pms .

# Run
docker run -p 8000:8000 celeste-pms
```

---

## 📋 Environment Variables Reference

**Complete list of .env.e2e variables:**

```bash
# === REQUIRED FOR TESTS ===
TENANT_SUPABASE_URL=https://your-project.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424

# === OPTIONAL (for specific tests) ===
MASTER_SUPABASE_URL=https://master-db.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...

# === OPENAI (for NL query tests) ===
OPENAI_API_KEY=sk-...

# === DEBUG ===
DEBUG=true
LOG_LEVEL=info
```

**Security Notes:**
- Never commit .env.e2e to git
- Never share service role keys
- Use test environment, not production
- Rotate keys regularly

---

## ✅ Setup Checklist

**Complete setup checklist:**

- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.12+ installed (optional) (`python3 --version`)
- [ ] Repository cloned
- [ ] Root dependencies installed (`npm install`)
- [ ] .env.e2e created (`cp .env.e2e.example .env.e2e`)
- [ ] .env.e2e filled with credentials
- [ ] Playwright installed (`npx playwright install`)
- [ ] Database connection tested (`node scripts/list_tables.js`)
- [ ] One test passing (`npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts`)

**If all checked:** ✅ You're ready to start verifying actions!

---

## 🚀 Next Steps

**After setup is complete:**

1. **Read TESTING_STANDARDS.md** - Understand what "success" means
2. **Pick a simple action** - Start with add_work_order_note or assign_work_order
3. **Copy verification template** - `cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_your_action.md`
4. **Start verifying!** - Follow ACTION_VERIFICATION_GUIDE.md

---

## 📞 Getting Help

**If stuck:**
1. Check this troubleshooting section
2. Search for error message in repository
3. Ask team on Slack/Discord
4. Check #onboarding channel

**Common questions:**
- "Where do I get credentials?" → Ask team lead
- "Which database URL?" → Tenant DB (not master)
- "Why 0 rows?" → Check yacht_id filter
- "Test timing out?" → Network issue or action hanging

---

## 🎯 Quick Commands Reference

```bash
# Install dependencies
npm install

# Run one test
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts

# Run all tests
npx playwright test

# Run with UI
npx playwright test --ui

# Query database
node scripts/list_tables.js

# Start frontend
cd apps/web && npm run dev

# Start backend
cd apps/api && uvicorn pipeline_service:app --reload

# Check environment
node -e "require('dotenv').config({path: '.env.e2e'}); console.log(process.env.TENANT_SUPABASE_URL)"
```

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team

**Setup time:** ~10 minutes
**First test run:** ~2 minutes
**Total to productivity:** ~15 minutes

**Next:** Read TESTING_STANDARDS.md
