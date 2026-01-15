# EVERYTHING YOU NEED - The Complete Guide

**For: New Claude (or 9-year-old technical wizard)**

---

## WHAT IS THIS PROJECT?

Imagine a **super fancy yacht** (like a floating mansion). The people who work on it need help remembering:
- What's broken? (faults)
- What needs fixing? (work orders)
- What parts do we have? (inventory)
- Who's working today? (crew)

**CelesteOS** is the app that helps them. When someone types "the generator is overheating", the app shows buttons like:
- "Diagnose Problem"
- "Create Work Order"
- "Order Parts"

**Your job:** Make those buttons work AND make them appear only at the right time.

---

## THE THREE PLACES CODE LIVES

Think of it like a restaurant:

```
┌─────────────────────────────────────────────────────────────┐
│  1. FRONTEND (The Menu - what customers see)                │
│     Location: /apps/web/                                    │
│     Deployed: https://app.celeste7.ai                       │
│     Language: TypeScript + React + Next.js                  │
│     This is: Buttons, forms, pages, modals                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  2. BACKEND (The Kitchen - where food is made)              │
│     Location: /apps/api/                                    │
│     Deployed: https://pipeline-core.int.celeste7.ai         │
│     Language: Python                                        │
│     This is: AI search, recommendations, smart stuff        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  3. DATABASE (The Fridge - where ingredients are stored)    │
│     Location: Supabase cloud                                │
│     URL: https://vzsohavtuotocgrfkfyd.supabase.co           │
│     Language: SQL + PostgreSQL                              │
│     This is: Work orders, faults, equipment, users          │
└─────────────────────────────────────────────────────────────┘
```

---

## THE DOCUMENTS (Your Instruction Manuals)

### THE GOSPEL (Read This Most)

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md
```

**What is it?** 6,584 lines that describe EVERY action in detail.
**Why read it?** It tells you exactly what each button should do.

---

### THE 57 MICROACTIONS (Your Todo List)

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md
```

**What is it?** A table of all 57 buttons you need to build.
**Each row tells you:**
- `action_name` - What's it called? (e.g., `diagnose_fault`)
- `card_type` - Where does it appear? (e.g., fault card, work order card)
- `side_effect_type` - Does it change data? (read_only, mutation_light, mutation_heavy)
- `cluster` - What category? (fix_something, do_maintenance, etc.)

---

### THE TRIGGER RULES (When Buttons Appear)

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
```

**What is it?** Rules for WHEN each button shows up.
**Example:**
- `suggest_parts` button ONLY appears IF the fault is in the known_faults database
- `assign_work_order` ONLY appears IF user is HOD or Chief Engineer
- `order_part` ONLY appears IF the part is out of stock

**THIS IS WHAT'S MISSING RIGHT NOW.** Buttons show all the time instead of only when rules are met.

---

### THE PYTHON HANDLERS (The Answer Key)

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/
```

**What is it?** 16 Python files that show EXACTLY what each action does.
**These are the SOURCE OF TRUTH.** Your TypeScript must match these.

| File | What Actions It Covers |
|------|------------------------|
| `fault_handlers.py` | diagnose_fault, add_fault_note, add_fault_photo |
| `work_order_handlers.py` | create_work_order, mark_complete, add_note |
| `work_order_mutation_handlers.py` | assign, add_parts, close |
| `equipment_handlers.py` | view_details, view_history, add_note |
| `inventory_handlers.py` | view_stock, order_part, log_usage |
| `handover_handlers.py` | add_to_handover, export, edit_section |
| `compliance_handlers.py` | hours_of_rest, view_compliance |
| `purchasing_mutation_handlers.py` | create_purchase, approve, track_delivery |
| `list_handlers.py` | view_worklist, add_task |
| `manual_handlers.py` | show_manual_section |
| `situation_handlers.py` | detect_situation, get_recommendations |

---

### THE MAIN TASK PROMPT

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/README_PROMPT_2.MD
```

**What is it?** 1,074 lines explaining the whole project.
**Read if:** You want the big picture of what we're building.

---

### THE HANDOVER (What Previous Claude Did Wrong)

```
/Users/celeste7/Documents/Cloud_PMS/HANDOVER_TO_NEXT_CLAUDE.md
```

**What is it?** Honest admission of mistakes.
**Key mistakes to avoid:**
1. Wrote handlers WITHOUT reading Python specs
2. Ran tests with service key (bypasses security)
3. Never built frontend UI buttons
4. Claimed "tests pass" but tests tested the code, not the spec

---

### THE MISSION CHECKLIST

```
/Users/celeste7/Documents/Cloud_PMS/CONTINUE_ALL_MICROACTIONS.md
```

**What is it?** Checklist of all 57 actions with [x] marks.
**Current status:** 57 handlers exist, but trigger logic is NOT implemented.

---

### THE VERIFICATION STATUS (What's Real vs Fake)

```
/Users/celeste7/Documents/Cloud_PMS/VERIFICATION_STATUS.md
```

**What is it?** Honest assessment of what's actually working.
**Summary:** Handlers exist and compile. Triggers, thresholds, role checks do NOT.

---

## FOLDER STRUCTURE (Where Things Live)

```
/Users/celeste7/Documents/Cloud_PMS/          <- THE CODE
├── apps/
│   ├── web/                                   <- FRONTEND (TypeScript)
│   │   ├── src/
│   │   │   ├── app/                           <- Pages (Next.js routes)
│   │   │   ├── components/
│   │   │   │   ├── cards/                     <- FaultCard, WorkOrderCard, etc.
│   │   │   │   └── modals/                    <- DiagnoseFaultModal, etc.
│   │   │   ├── lib/
│   │   │   │   ├── microactions/
│   │   │   │   │   ├── handlers/              <- YOUR 57 HANDLERS
│   │   │   │   │   ├── registry.ts            <- Action definitions
│   │   │   │   │   ├── executor.ts            <- Runs handlers
│   │   │   │   │   └── types.ts               <- TypeScript types
│   │   │   │   ├── situations/                <- AI situation detection
│   │   │   │   ├── action-router/             <- Routes actions to handlers
│   │   │   │   └── supabaseClient.ts          <- Database connection
│   │   │   └── providers/
│   │   │       └── MicroactionsProvider.tsx   <- Registers handlers on load
│   │   └── tests/
│   │       ├── unit/                          <- Fast tests with mocks
│   │       └── integration/                   <- Tests with real database
│   │
│   └── api/                                   <- BACKEND (Python)
│       └── handlers/                          <- Python handlers (SOURCE OF TRUTH)
│
├── supabase/
│   └── migrations/                            <- SQL changes to database
│
├── tests/
│   └── e2e/                                   <- End-to-end tests (Playwright)
│       └── microactions/                      <- Tests that click real buttons
│
└── .github/
    └── workflows/
        └── e2e.yml                            <- GitHub runs tests on push
```

```
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/     <- THE DOCUMENTATION
├── 03_MICROACTIONS/
│   ├── MICRO_ACTION_REGISTRY.md               <- All 57 actions defined
│   └── ACTION_OFFERING_RULES.md               <- When each action appears
├── 04_HANDLERS/
│   └── *.py                                   <- Python handlers (16 files)
├── COMPLETE_ACTION_EXECUTION_CATALOG.md       <- THE GOSPEL (6,584 lines)
└── README_PROMPT_2.MD                         <- Main task prompt
```

---

## ENVIRONMENT VARIABLES

These are secret values the app needs to connect to things.

### For Local Development (.env.local)

```bash
# Supabase (Database)
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# For tests that need admin access
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY

# Backend API
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
```

### For GitHub Actions (Secrets)

These are set in GitHub repo settings:

| Secret Name | What It Is |
|-------------|------------|
| `TENANT_SUPABASE_URL` | Database URL |
| `TENANT_SUPABASE_SERVICE_ROLE_KEY` | Admin database key |
| `TEST_USER_EMAIL` | x@alex-short.com |
| `TEST_USER_PASSWORD` | Password2! |
| `TEST_USER_YACHT_ID` | 85fe1119-b04c-41ac-80f1-829d23322598 |
| `VERCEL_PROD_URL` | https://app.celeste7.ai |
| `RENDER_API_URL` | https://pipeline-core.int.celeste7.ai |

---

## TEST CREDENTIALS (For Logging In)

```
Email:    x@alex-short.com
Password: Password2!
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

Use these to:
1. Log into https://app.celeste7.ai
2. Run E2E tests
3. Test with real user permissions

---

## THE IMPORT PATTERN (Very Important!)

**WRONG (will break):**
```typescript
import { createClient } from '@/lib/supabase/server';
const supabase = createClient();
```

**CORRECT:**
```typescript
import { supabase } from '@/lib/supabaseClient';
// Just use it directly - it's already created
```

---

## HOW DATA FLOWS (Step by Step)

```
1. USER types: "generator overheating"
                    ↓
2. FRONTEND sends to Python backend
                    ↓
3. PYTHON AI figures out:
   - Equipment: Generator 1
   - Problem: Overheating
   - Suggests actions: diagnose_fault, create_work_order
                    ↓
4. FRONTEND shows card with buttons
                    ↓
5. USER clicks "Diagnose"
                    ↓
6. FRONTEND calls TypeScript handler
                    ↓
7. HANDLER talks to Supabase database
                    ↓
8. DATABASE returns/stores data
                    ↓
9. FRONTEND shows result in modal
```

---

## WHAT'S MISSING (The Gap)

### Built:
- 57 TypeScript handler functions
- FaultCard with buttons (always visible)
- Build passes, tests pass

### NOT Built:
```
┌─────────────────────────────────────────────────────────────┐
│  TRIGGER LOGIC                                              │
│  - Check: Is this fault in known_faults database?           │
│  - Check: Is this part out of stock?                        │
│  - Check: Is the user an Engineer, HOD, or Captain?         │
│  - THEN: Show or hide the button                            │
└─────────────────────────────────────────────────────────────┘

Right now: ALL buttons show ALL the time
Should be: Buttons show ONLY when rules in ACTION_OFFERING_RULES.md are met
```

---

## COMMANDS CHEAT SHEET

```bash
# Go to project
cd /Users/celeste7/Documents/Cloud_PMS

# Install dependencies
cd apps/web && npm install

# Run development server
cd apps/web && npm run dev

# Check if code compiles
cd apps/web && npm run build

# Run unit tests
cd apps/web && npm run test:unit

# Run integration tests (needs database)
cd apps/web && npm run test:integration

# Run E2E tests (needs browser)
npx playwright test --headed

# Push changes to GitHub
git add . && git commit -m "your message" && git push origin main

# Check database tables
supabase db dump --schema public | grep "CREATE TABLE"

# Apply database migration
supabase db push
```

---

## SUMMARY: YOUR MISSION

```
1. READ the trigger rules in ACTION_OFFERING_RULES.md
2. ADD conditional logic to card components
3. MAKE buttons appear ONLY when conditions are met
4. TEST with E2E tests
5. PUSH to GitHub
6. VERIFY on production
```

**The handlers are done. The buttons exist. Now make them SMART.**

---

## FILES TO READ (In Order)

| Order | File | Why |
|-------|------|-----|
| 1 | `/Users/celeste7/CLAUDE.md` | Project memory |
| 2 | `/Users/celeste7/Documents/Cloud_PMS/EVERYTHING_YOU_NEED.md` | This file |
| 3 | `/Users/celeste7/Documents/Cloud_PMS/CONTINUE_ALL_MICROACTIONS.md` | Checklist |
| 4 | `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md` | Trigger rules |
| 5 | `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md` | Action specs |
| 6 | `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md` | The Gospel |

---

## QUICK REFERENCE

| What | Where |
|------|-------|
| Frontend code | `/apps/web/src/` |
| Handlers | `/apps/web/src/lib/microactions/handlers/` |
| Card components | `/apps/web/src/components/cards/` |
| Modals | `/apps/web/src/components/modals/` |
| E2E tests | `/tests/e2e/microactions/` |
| Python handlers | `/Desktop/Cloud_PMS_docs_v2/04_HANDLERS/` |
| Action specs | `/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/` |
| The Gospel | `/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md` |
| Database | https://vzsohavtuotocgrfkfyd.supabase.co |
| Production | https://app.celeste7.ai |

---

**You're a 9-year-old wizard. You've got this.**
