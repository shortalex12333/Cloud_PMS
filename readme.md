# CelesteOS Cloud PMS

**Yacht Planned Maintenance System with Natural Language Interface**

Crew speaks naturally → AI understands intent → System executes maintenance actions

---

## Quick Start

```bash
# 1. You're here
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/

# 2. First, read the handover
open _HANDOVER/README.md

# 3. Run health check
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium

# Expected: 95% pass (61/64 actions working)
```

---

## Project Structure

```
BACK_BUTTON_CLOUD_PMS/
│
├── README.md                 ← YOU ARE HERE
│
├── _HANDOVER/                ← START HERE (Engineer handover)
│   ├── README.md             ← Entry point - read first
│   ├── 01_STATUS.md          ← Current system status (95% health)
│   ├── 02_WHATS_LEFT.md      ← Remaining work (~38 hours)
│   ├── 03_HOW_TO_RUN.md      ← All test commands
│   └── 04_KNOWN_TRAPS.md     ← Common issues and fixes
│
├── apps/                     ← SOURCE CODE
│   ├── api/                  ← Python FastAPI backend
│   │   ├── routes/
│   │   │   └── p0_actions_routes.py  ← ALL 81 ACTION HANDLERS
│   │   ├── services/
│   │   └── handlers/
│   └── web/                  ← Next.js frontend
│       └── src/
│
├── tests/                    ← TEST SUITE
│   ├── e2e/                  ← Playwright E2E tests
│   │   ├── diagnostic_baseline.spec.ts   ← Health check (run first)
│   │   ├── nl_to_action_mapping.spec.ts  ← NL coverage (64/64)
│   │   └── chat_to_action.spec.ts        ← Full E2E flow
│   ├── helpers/
│   │   └── test-data-discovery.ts        ← Finds real entity IDs
│   └── fixtures/
│       └── microaction_registry.ts       ← Action definitions
│
├── database/                 ← Database schemas
├── migrations/               ← SQL migrations
├── supabase/                 ← Supabase config
├── scripts/                  ← Utility scripts
│
├── _archive/                 ← Old docs (for reference only)
│
├── ENGINEER_HANDOVER.md      ← Detailed technical handover
├── KNOWN_ISSUES.md           ← Issue patterns and solutions
└── TEST_COVERAGE_REPORT.md   ← What's tested vs not
```

---

## System Status

```
┌─────────────────────────────────────────────────┐
│            CURRENT STATE: 95%                   │
├─────────────────────────────────────────────────┤
│  Handlers Implemented     81/81    (100%)       │
│  Actions Returning 200    61/64    (95%)        │
│  NL Tests Passing         64/64    (100%)       │
│  Production Verified      1/64     (1.5%)       │
└─────────────────────────────────────────────────┘
```

**The Gap:** Handlers respond correctly, but only 1 has been proven to actually write to the database.

---

## What This System Does

### The 7 Action Clusters (64 total actions)

| Cluster | Actions | Purpose |
|---------|---------|---------|
| fix_something | 10 | Fault diagnosis, repair guidance |
| do_maintenance | 16 | Work orders, checklists, worklists |
| manage_equipment | 9 | Equipment details, history, manuals |
| control_inventory | 7 | Parts stock, orders, usage tracking |
| communicate_status | 10 | Handovers, summaries, photos |
| comply_audit | 5 | Hours of rest, compliance |
| procure_suppliers | 7 | Purchase requests, deliveries |

### How It Works

```
User: "The generator is overheating"
         │
         ▼
┌─────────────────────────────────────┐
│  /search endpoint                   │
│  - GPT-4o-mini extracts entities    │
│  - Maps to capabilities             │
│  - Returns available actions        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  UI shows action buttons:           │
│  [Diagnose] [View History] [Manual] │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  /v1/actions/execute                │
│  - Handler processes action         │
│  - Writes to database               │
│  - Returns result                   │
└─────────────────────────────────────┘
```

---

## Essential Commands

```bash
# Health check (61/64 pass expected)
npx playwright test tests/e2e/diagnostic_baseline.spec.ts --project=e2e-chromium

# NL coverage (64/64 pass expected)
npx playwright test tests/e2e/nl_to_action_mapping.spec.ts --project=e2e-chromium

# Single action test
npx playwright test -g "diagnose_fault"

# Start backend
cd apps/api && uvicorn main:app --reload
```

---

## For New Engineers

### Where to Start

1. **Read** `_HANDOVER/README.md` - 5 minutes
2. **Run** the health check - 5 minutes
3. **Read** `_HANDOVER/04_KNOWN_TRAPS.md` - 10 minutes
4. **Start** on `_HANDOVER/02_WHATS_LEFT.md` tasks

### Key Files to Know

| File | What It Contains |
|------|------------------|
| `apps/api/routes/p0_actions_routes.py` | All 81 action handlers (4,160 lines) |
| `tests/fixtures/microaction_registry.ts` | All 64 action definitions |
| `tests/e2e/diagnostic_baseline.spec.ts` | Health check tests |
| `tests/helpers/test-data-discovery.ts` | Finds real test data IDs |

### The Main Gap to Close

```
What exists:    95% of handlers return HTTP 200
What's missing: Proof they actually write to the database
How to fix:     Run each mutation, verify DB change, verify audit log
Time estimate:  ~38 hours total
```

---

## Environment Setup

```bash
# Required environment variables
MASTER_SUPABASE_URL=https://xxx.supabase.co
MASTER_SUPABASE_SERVICE_ROLE_KEY=eyJ...
TENANT_SUPABASE_URL=https://yyy.supabase.co
TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJ...
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
TEST_USER_ID=a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

---

## Tech Stack

- **Backend:** Python FastAPI
- **Frontend:** Next.js / React
- **Database:** Supabase (PostgreSQL)
- **AI:** GPT-4o-mini for entity extraction
- **Tests:** Playwright

---

## Links

- **Git:** https://github.com/shortalex12333/Cloud_PMS.git
- **Branch:** main

---

*Last updated: 2026-01-22*
