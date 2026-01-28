# Repository Map - Where Is Everything?

**Visual guide to the BACK_BUTTON_CLOUD_PMS repository**

**Purpose:** Help new engineers find files quickly
**When to use:** When you don't know where something is
**Reading time:** 5 minutes

---

## 🎯 Quick Navigation

**I want to...**

| Task | Go To |
|------|-------|
| Find a microaction handler | `apps/api/routes/p0_actions_routes.py` |
| See all 64 microactions | `tests/fixtures/microaction_registry.ts` |
| Understand database schema | `DATABASE_RELATIONSHIPS.md` |
| See how users interact | `CUSTOMER_JOURNEY_FRAMEWORK.md` |
| Run a test | `tests/e2e/*.spec.ts` |
| Query the database | `scripts/*.js` |
| See the main UI | `apps/web/src/app/app/page.tsx` |
| Find SpotlightSearch | `apps/web/src/components/spotlight/SpotlightSearch.tsx` |
| Verify an action | Copy `ACTION_VERIFICATION_TEMPLATE.md` |

---

## 📁 Full Repository Structure

```
BACK_BUTTON_CLOUD_PMS/
│
├── 📖 DOCUMENTATION (Start Here)
│   ├── ONBOARDING.md                      ← 👈 START HERE (30-min quick start)
│   ├── GLOSSARY.md                        ← All terms defined
│   ├── REPOSITORY_MAP.md                  ← You are here
│   ├── TESTING_STANDARDS.md               ← What is success/failure
│   ├── LOCAL_SETUP.md                     ← Environment setup
│   │
│   ├── ARCHITECTURE.md                    ← How the system works
│   ├── MICROACTIONS_EXPLAINED.md          ← What are microactions
│   ├── SITUATIONS_EXPLAINED.md            ← What are situations
│   ├── DEPLOYMENT_ARCHITECTURE.md         ← Where is it deployed
│   ├── QUICK_REFERENCE.md                 ← Cheat sheet
│   │
│   ├── FRAMEWORK_OVERVIEW.md              ← How to verify actions
│   ├── DATABASE_RELATIONSHIPS.md          ← Schema ground truth
│   ├── CUSTOMER_JOURNEY_FRAMEWORK.md      ← User experience
│   │
│   ├── ACTION_VERIFICATION_TEMPLATE.md    ← Copy this for each action
│   ├── ACTION_VERIFICATION_GUIDE.md       ← Step-by-step guide
│   └── README_VERIFICATION_SYSTEM.md      ← System overview
│
├── 🔧 BACKEND (FastAPI Python)
│   └── apps/api/
│       ├── routes/
│       │   └── p0_actions_routes.py       ← ⭐ ALL 81 handlers (4160 lines)
│       │                                     Search: action == "your_action"
│       ├── microaction_service.py         ← Microaction utilities
│       ├── microaction_extractor.py       ← NL query → action detection
│       ├── microaction_config.py          ← Action configuration
│       ├── microaction_patterns.json      ← NL patterns for detection
│       │
│       ├── pipeline_service.py            ← Main FastAPI app
│       ├── auth.py                        ← JWT validation
│       ├── database.py                    ← Supabase clients
│       │
│       └── requirements.txt               ← Python dependencies
│
├── 🎨 FRONTEND (Next.js React TypeScript)
│   └── apps/web/
│       ├── src/
│       │   ├── app/
│       │   │   └── app/
│       │   │       ├── page.tsx           ← ⭐ Single surface (main UI)
│       │   │       ├── ContextPanel.tsx   ← Entity detail panel
│       │   │       └── DeepLinkHandler.tsx ← E2E deep linking
│       │   │
│       │   ├── components/
│       │   │   ├── spotlight/
│       │   │   │   ├── SpotlightSearch.tsx     ← ⭐ Main search bar
│       │   │   │   └── SpotlightResultRow.tsx  ← Search result display
│       │   │   │
│       │   │   ├── situations/
│       │   │   │   └── SituationRouter.tsx     ← Situation state management
│       │   │   │
│       │   │   └── email/
│       │   │       └── EmailInboxView.tsx      ← Email integration
│       │   │
│       │   ├── lib/
│       │   │   ├── actionClient.ts        ← ⭐ API calls to /v1/actions/execute
│       │   │   ├── supabaseClient.ts      ← Supabase initialization
│       │   │   └── utils.ts               ← Utility functions
│       │   │
│       │   ├── hooks/
│       │   │   ├── useCelesteSearch.ts    ← Search hook (calls /search)
│       │   │   ├── useSituationState.ts   ← Situation state management
│       │   │   └── useAuth.ts             ← Auth context
│       │   │
│       │   ├── contexts/
│       │   │   ├── SurfaceContext.tsx     ← UI state management
│       │   │   └── AuthContext.tsx        ← User auth context
│       │   │
│       │   └── types/
│       │       ├── search.ts              ← Search result types
│       │       └── situation.ts           ← Situation types
│       │
│       ├── package.json                   ← Node dependencies
│       └── tsconfig.json                  ← TypeScript config
│
├── 🧪 TESTS
│   └── tests/
│       ├── e2e/                           ← ⭐ Playwright E2E tests
│       │   ├── mutation_proof_create_work_order.spec.ts  ← Gold standard
│       │   ├── nl_queries_create_work_order.spec.ts      ← NL query tests
│       │   ├── microactions_matrix.spec.ts               ← All 64 actions
│       │   └── [other action tests]
│       │
│       ├── fixtures/
│       │   └── microaction_registry.ts    ← ⭐ All 64 actions defined
│       │
│       └── test_microactions.py           ← Python unit tests
│
├── 📊 VERIFICATION WORK
│   └── _VERIFICATION/
│       ├── CREATE_WORK_ORDER_DEEP_DIVE.md    ← Complete example (5,800 words)
│       ├── EXECUTIVE_SUMMARY_CREATE_WO.md    ← Summary + findings
│       ├── MUTATION_PROOFS.md                ← Progress tracker (1/64)
│       ├── COMPREHENSIVE_FAULT_REPORT.md     ← System-wide audit
│       │
│       └── verify_[action_name].md           ← Your work goes here
│                                                (copy template for each)
│
├── 🔨 SCRIPTS (Database & Utilities)
│   └── scripts/
│       ├── discover_database_relationships.js  ← Discover DB schema
│       ├── analyze_pms_audit_log.js           ← Analyze audit log
│       ├── check_create_wo_audit.js           ← Check specific action
│       ├── list_tables.js                     ← List all DB tables
│       ├── get_action_context.js              ← Get action metadata
│       │
│       └── [other utility scripts]
│
├── 📚 REFERENCE (Use with Caution)
│   └── _archive/
│       └── misc/
│           └── COMPLETE_ACTION_EXECUTION_CATALOG.md  ← ⚠️ OUTDATED (6584 lines)
│                                                        Catalog is aspirational,
│                                                        not reality. Cross-check
│                                                        with DATABASE_RELATIONSHIPS.md
│
├── 🔐 ENVIRONMENT
│   ├── .env.e2e                           ← Test environment (gitignored)
│   ├── .env.e2e.example                   ← Template (commit this)
│   └── .auth/
│       └── access_token.txt               ← JWT token for scripts
│
├── ⚙️ CONFIGURATION
│   ├── package.json                       ← Root dependencies
│   ├── playwright.config.ts               ← Playwright test config
│   ├── tsconfig.json                      ← TypeScript config
│   └── .gitignore                         ← Ignored files
│
└── 📄 ROOT FILES
    ├── README.md                          ← Project overview
    ├── DEPLOYMENT.md                      ← Deployment instructions
    └── package-lock.json                  ← Dependency lock file
```

---

## 🎯 Critical Files (Top 10)

**If you only learn 10 files, make it these:**

### 1. ONBOARDING.md (Root)
**What:** New engineer start here guide
**Why:** Gets you productive in 30 minutes
**Size:** ~3,000 words
**Read first:** Yes

### 2. apps/api/routes/p0_actions_routes.py
**What:** ALL microaction handlers (81 handlers, 4160 lines)
**Why:** This is where the magic happens
**How to use:** Search for `action == "your_action_name"`
**Example:**
```python
grep -n 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py
# Line 1325
```

### 3. tests/fixtures/microaction_registry.ts
**What:** All 64 microactions listed
**Why:** See what actions exist
**Format:**
```typescript
{
  action: "create_work_order",
  label: "Create Work Order",
  cluster: "DO_MAINTENANCE",
  mutationType: "MUTATE_MEDIUM"
}
```

### 4. DATABASE_RELATIONSHIPS.md (Root)
**What:** Ground truth of database schema
**Why:** Avoid column name traps, understand relationships
**Size:** ~8,200 words
**Cross-reference with:** Handler code

### 5. CUSTOMER_JOURNEY_FRAMEWORK.md (Root)
**What:** How users interact with the system
**Why:** Understand UX, write realistic tests
**Size:** ~7,500 words
**Contains:** Query variants, UI flows, guard rails

### 6. apps/web/src/app/app/page.tsx
**What:** Main UI (single surface)
**Why:** See the entry point for frontend
**Contains:** SpotlightSearch, ContextPanel layout

### 7. apps/web/src/components/spotlight/SpotlightSearch.tsx
**What:** Main search bar component
**Why:** Understand how users trigger actions
**Contains:** Query handling, action button rendering, result display

### 8. apps/web/src/lib/actionClient.ts
**What:** API client for calling microactions
**Why:** See how frontend calls backend
**Function:** `executeAction(action, context, payload)`

### 9. tests/e2e/mutation_proof_create_work_order.spec.ts
**What:** Gold standard mutation proof test
**Why:** Template for all other action tests
**Pattern:** BEFORE → EXECUTE → AFTER → AUDIT

### 10. ACTION_VERIFICATION_TEMPLATE.md (Root)
**What:** 215-point checklist for verifying actions
**Why:** Copy this for each action you verify
**Size:** ~5,000 words
**Usage:** `cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_your_action.md`

---

## 📂 Directory Deep Dives

### apps/api/ (Backend)

**Purpose:** FastAPI Python backend serving microaction handlers

**Key files:**
```
apps/api/
├── routes/
│   └── p0_actions_routes.py       ← 81 handlers, elif chain
│
├── microaction_*.py               ← Microaction utilities
├── pipeline_service.py            ← Main FastAPI app (endpoints: /search, /v1/actions/execute)
├── auth.py                        ← JWT validation
├── database.py                    ← Supabase client setup
│
└── requirements.txt               ← fastapi, supabase, openai, etc.
```

**How to find a handler:**
```bash
grep -n 'action == "mark_work_order_complete"' apps/api/routes/p0_actions_routes.py
```

**Pattern:**
```python
elif action in ("mark_work_order_complete", "complete_work_order", "mark_complete"):
    # Validation
    # Transform data
    # Write to DB
    # Write to audit log (if implemented)
    # Return response
```

---

### apps/web/ (Frontend)

**Purpose:** Next.js React TypeScript frontend (single surface UI)

**Key structure:**
```
apps/web/src/
├── app/
│   └── app/
│       ├── page.tsx               ← Main entry point (/app route)
│       └── ContextPanel.tsx       ← Entity detail panel
│
├── components/
│   ├── spotlight/
│   │   └── SpotlightSearch.tsx   ← Main search bar (always visible)
│   │
│   └── situations/
│       └── SituationRouter.tsx    ← Handles IDLE/CANDIDATE/ACTIVE states
│
├── lib/
│   ├── actionClient.ts            ← executeAction() function
│   └── supabaseClient.ts          ← Supabase setup
│
├── hooks/
│   ├── useCelesteSearch.ts        ← POST /search hook
│   └── useSituationState.ts       ← Situation state management
│
└── contexts/
    ├── SurfaceContext.tsx         ← Global UI state
    └── AuthContext.tsx            ← User auth (JWT, yacht_id)
```

**How it flows:**
```
User types query
  ↓
SpotlightSearch.tsx
  ↓
useCelesteSearch hook → POST /search
  ↓
Backend returns actions
  ↓
Action button rendered
  ↓
User clicks button
  ↓
Modal opens (form)
  ↓
User submits
  ↓
actionClient.executeAction() → POST /v1/actions/execute
  ↓
Backend handler runs
  ↓
Database updated
  ↓
Response returned
  ↓
Toast notification shown
```

---

### tests/ (Testing)

**Purpose:** E2E tests with Playwright

**Structure:**
```
tests/
├── e2e/                           ← Playwright browser tests
│   ├── mutation_proof_*.spec.ts  ← Database mutation tests
│   ├── nl_queries_*.spec.ts      ← Natural language query tests
│   ├── microactions_matrix.spec.ts ← All 64 actions smoke test
│   └── journey_*.spec.ts         ← Full UI journey tests
│
├── fixtures/
│   └── microaction_registry.ts   ← All 64 actions defined
│
└── playwright.config.ts           ← Test configuration
```

**How to run:**
```bash
# Single test
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts

# All tests
npx playwright test

# With UI
npx playwright test --ui

# Debug mode
npx playwright test --debug
```

**Test pattern:**
```typescript
test('action mutation proof', async () => {
  // 1. BEFORE - Query database
  const { data: before } = await supabase.from('table').select('*');
  expect(before).toHaveLength(0);

  // 2. EXECUTE - Call action
  await executeAction('action_name', {...});

  // 3. AFTER - Verify database
  const { data: after } = await supabase.from('table').select('*');
  expect(after).toHaveLength(1);

  // 4. AUDIT - Check audit log
  const { data: audit } = await supabase.from('pms_audit_log').select('*');
  expect(audit).toHaveLength(1);
});
```

---

### _VERIFICATION/ (Your Work)

**Purpose:** Store completed action verifications

**Structure:**
```
_VERIFICATION/
├── CREATE_WORK_ORDER_DEEP_DIVE.md     ← Example (5,800 words)
├── EXECUTIVE_SUMMARY_CREATE_WO.md     ← Summary
├── MUTATION_PROOFS.md                 ← Progress tracker (1/64)
├── COMPREHENSIVE_FAULT_REPORT.md      ← System-wide audit
│
└── verify_[action_name].md            ← Copy template here
```

**Workflow:**
```bash
# 1. Copy template
cp ACTION_VERIFICATION_TEMPLATE.md _VERIFICATION/verify_add_work_order_note.md

# 2. Fill it in (2-3 hours)
# - Database mutations
# - Customer journey
# - Guard rails
# - Test results

# 3. Create tests
touch tests/e2e/mutation_proof_add_work_order_note.spec.ts

# 4. Update tracker
# Edit MUTATION_PROOFS.md: 2/64 complete
```

---

### scripts/ (Utilities)

**Purpose:** Node.js scripts for database queries and analysis

**Common scripts:**
```
scripts/
├── discover_database_relationships.js  ← Run to regenerate schema
├── analyze_pms_audit_log.js           ← Check audit coverage
├── check_create_wo_audit.js           ← Specific action audit check
├── list_tables.js                     ← List all tables
└── get_action_context.js              ← Get action metadata
```

**How to run:**
```bash
# Requires .env.e2e with Supabase credentials
node scripts/analyze_pms_audit_log.js
```

**Output:** JSON or Markdown reports

---

## 🚫 What to Ignore

### Ignore These Directories:
```
node_modules/          ← Dependencies (18,000+ files)
.next/                 ← Next.js build artifacts
.playwright/           ← Playwright browser binaries
__pycache__/           ← Python cache
.git/                  ← Git metadata
dist/                  ← Build output
build/                 ← Build output
```

### Ignore These Files:
```
*.tsbuildinfo          ← TypeScript build info
package-lock.json      ← Dependency lock (don't edit manually)
*.pyc                  ← Python compiled
.DS_Store              ← macOS metadata
```

### Use With Caution:
```
_archive/              ← Old docs, may be outdated
COMPLETE_ACTION_EXECUTION_CATALOG.md  ← Outdated (cross-check reality)
```

---

## 🔍 How to Find Things

### Find a Microaction Handler
```bash
grep -n 'action == "your_action"' apps/api/routes/p0_actions_routes.py
```

### Find Which Table an Action Uses
```bash
# Method 1: Check handler
grep -A 20 'action == "create_work_order"' apps/api/routes/p0_actions_routes.py | grep "\.table("

# Method 2: Check DATABASE_RELATIONSHIPS.md
grep -n "pms_work_orders" DATABASE_RELATIONSHIPS.md
```

### Find All Actions in a Cluster
```bash
# Check microaction_registry.ts
grep -n "cluster.*DO_MAINTENANCE" tests/fixtures/microaction_registry.ts
```

### Find Tests for an Action
```bash
ls tests/e2e/*create_work_order*.spec.ts
```

### Find Frontend Component
```bash
find apps/web/src -name "*Spotlight*.tsx"
```

### Find How to Call an Action
```bash
# Check actionClient.ts
cat apps/web/src/lib/actionClient.ts
```

---

## 📊 File Statistics

**Total Files (excluding node_modules):** ~500 files

**Breakdown by Type:**
- Documentation (*.md): 20+ files (~50,000 words)
- Backend Python (*.py): 30+ files (~8,000 lines)
- Frontend TypeScript (*.ts, *.tsx): 200+ files (~30,000 lines)
- Tests (*.spec.ts): 15+ files (~5,000 lines)
- Scripts (*.js): 20+ files (~2,000 lines)
- Config (*.json, *.config.*): 15+ files

**Largest Files:**
1. `apps/api/routes/p0_actions_routes.py` - 4,160 lines
2. `_archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md` - 6,584 lines
3. `DATABASE_RELATIONSHIPS.md` - ~8,200 words
4. `CUSTOMER_JOURNEY_FRAMEWORK.md` - ~7,500 words

---

## 🎯 Common Workflows

### Verify a New Action
```
1. Choose action (tests/fixtures/microaction_registry.ts)
2. Copy template (ACTION_VERIFICATION_TEMPLATE.md → _VERIFICATION/)
3. Research handler (apps/api/routes/p0_actions_routes.py)
4. Research database (DATABASE_RELATIONSHIPS.md)
5. Research journey (CUSTOMER_JOURNEY_FRAMEWORK.md)
6. Fill in template
7. Write mutation test (tests/e2e/)
8. Run test
9. Update tracker (_VERIFICATION/MUTATION_PROOFS.md)
```

### Debug a Failing Test
```
1. Read test file (tests/e2e/*.spec.ts)
2. Run with --debug flag
3. Check handler code (apps/api/routes/p0_actions_routes.py)
4. Check database schema (DATABASE_RELATIONSHIPS.md)
5. Query database manually (scripts/*.js)
6. Fix issue
7. Re-run test
```

### Add a New Microaction
```
1. Add to registry (tests/fixtures/microaction_registry.ts)
2. Add handler (apps/api/routes/p0_actions_routes.py)
3. Update DATABASE_RELATIONSHIPS.md (if new table)
4. Update CUSTOMER_JOURNEY_FRAMEWORK.md (add journey)
5. Write verification (copy template)
6. Write tests
7. Update progress tracker
```

---

## 🆘 Quick Help

**I can't find...**

| What | Where |
|------|-------|
| A microaction handler | `grep -n 'action == "..."' apps/api/routes/p0_actions_routes.py` |
| A table schema | DATABASE_RELATIONSHIPS.md |
| A UI component | `find apps/web/src/components -name "*Component*.tsx"` |
| A test | `ls tests/e2e/*action*.spec.ts` |
| Environment variables | .env.e2e.example |
| Documentation | Root *.md files |

**I need to...**

| Task | Command |
|------|---------|
| Run tests | `npx playwright test` |
| Query database | `node scripts/list_tables.js` |
| Start frontend | `cd apps/web && npm run dev` |
| Start backend | `cd apps/api && uvicorn pipeline_service:app --reload` |
| Install dependencies | `npm install` |

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team

**Next:** Read TESTING_STANDARDS.md to understand success criteria
