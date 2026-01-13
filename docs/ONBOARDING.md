# CelesteOS Developer Onboarding Guide

> **Last Updated:** January 2026
> **Purpose:** Everything a new developer needs to understand, run, and extend this system.

---

## Table of Contents

1. [What Is This System?](#1-what-is-this-system)
2. [Architecture Overview](#2-architecture-overview)
3. [Quick Start (5 minutes)](#3-quick-start-5-minutes)
4. [Local Development Setup](#4-local-development-setup)
5. [Database Schema](#5-database-schema)
6. [Actions & Microactions](#6-actions--microactions)
7. [Situations System](#7-situations-system)
8. [API Endpoints](#8-api-endpoints)
9. [Production Pipeline](#9-production-pipeline)
10. [Testing Strategy](#10-testing-strategy)
11. [File Index](#11-file-index)
12. [Common Questions](#12-common-questions)

---

## 1. What Is This System?

**CelesteOS** is a yacht/vessel Property Management System (PMS) with:
- Natural language search ("show overdue work orders")
- AI-powered query understanding
- Microactions (quick buttons on result cards)
- Situations (contextual views that aggregate related data)

**Tech Stack:**
| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, TypeScript, Tailwind |
| Backend API | FastAPI (Python 3.11) |
| Database | PostgreSQL via Supabase |
| AI/Search | OpenAI embeddings, custom ranking |
| Hosting | Vercel (frontend), Render (API), Supabase Cloud (DB) |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│  apps/web/src/                                                   │
│  ├── app/           → Pages (briefing, search, situations)       │
│  ├── components/    → UI components (cards, modals, search)      │
│  └── lib/           → API clients, utilities                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND API (FastAPI)                    │
│  apps/api/                                                       │
│  ├── microaction_service.py  → Main FastAPI app                  │
│  ├── handlers/               → Action handlers (DB mutations)    │
│  ├── routes/                 → API route definitions             │
│  ├── action_router/          → JWT validation, routing           │
│  └── pipeline_gateway.py     → Local/Remote/Replay routing       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ SQL
┌─────────────────────────────────────────────────────────────────┐
│                         DATABASE (Supabase/PostgreSQL)           │
│  Tables: work_orders, faults, inventory_items, documents,        │
│          equipment, handover_items, crew, purchasing, etc.       │
│  RLS: Row Level Security per yacht_id                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Quick Start (5 minutes)

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker Desktop
- Supabase CLI (`brew install supabase/tap/supabase`)

### Commands

```bash
# 1. Clone and install
git clone https://github.com/shortalex12333/Cloud_PMS.git
cd Cloud_PMS
npm install                    # Frontend deps
pip install -r apps/api/requirements.txt  # Backend deps

# 2. Start local Supabase (Docker)
supabase start                 # Starts PostgreSQL + Auth + Storage

# 3. Start backend API
cd apps/api && uvicorn microaction_service:app --reload --port 8000

# 4. Start frontend
cd apps/web && npm run dev     # Runs on http://localhost:3000

# 5. Open browser
open http://localhost:3000
```

---

## 4. Local Development Setup

### 4.1 Supabase Local (Docker)

**Start:**
```bash
supabase start
```

**Output shows:**
```
API URL: http://127.0.0.1:54321
DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
Studio: http://127.0.0.1:54323
Anon Key: eyJhbGciOiJIUzI1NiIs...
Service Key: eyJhbGciOiJIUzI1NiIs...
```

**Stop:**
```bash
supabase stop
```

**Reset (wipe all data):**
```bash
supabase db reset
```

### 4.2 Environment Variables

**Backend (`apps/api/.env`):**
```env
# Supabase (Local)
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_KEY=<service_role_key from supabase start>
SUPABASE_ANON_KEY=<anon_key from supabase start>
SUPABASE_JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long

# Database
DB_HOST=127.0.0.1
DB_PORT=54322
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres

# Server
PORT=8000
LOG_LEVEL=DEBUG

# Pipeline Gateway (for prod-parity testing)
PIPELINE_MODE=local          # local | remote | replay
PIPELINE_REMOTE_URL=https://cloud-pms.onrender.com/search
```

**Frontend (`apps/web/.env.local`):**
```env
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4.3 Database Migrations

Migrations live in: `supabase/migrations/`

**Apply migrations:**
```bash
supabase db reset   # Resets and runs all migrations
```

**Seed data:**
```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres < supabase/seed.sql
```

---

## 5. Database Schema

### 5.1 Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `work_orders` | Maintenance tasks | id, title, status, priority, yacht_id |
| `faults` | Equipment faults | id, title, severity, status, equipment_id |
| `inventory_items` | Spare parts | id, name, quantity, min_stock, location |
| `documents` | Manuals, certs | id, title, file_path, document_type |
| `equipment` | Yacht equipment | id, name, category, location |
| `handover_items` | Crew handover notes | id, title, category, status |
| `crew` | Crew members | id, name, role, yacht_id |
| `purchasing_requests` | Purchase orders | id, item_name, quantity, status |

### 5.2 Schema Files

| File | Purpose |
|------|---------|
| `supabase/migrations/*.sql` | Official migrations (run by Supabase) |
| `database/migrations/01_core_tables_v2_secure.sql` | Reference schema |
| `docs/DATABASE_SCHEMA.md` | Schema documentation |
| `DATABASE_SCHEMA_EXECUTION_SPEC.md` | Detailed column specs |

### 5.3 Row Level Security (RLS)

All tables use RLS to isolate data by `yacht_id`:
```sql
CREATE POLICY "Users can only see their yacht data"
ON work_orders FOR SELECT
USING (yacht_id = auth.jwt()->>'yacht_id');
```

---

## 6. Actions & Microactions

### 6.1 What Are They?

- **Action**: A database mutation (create, update, delete)
- **Microaction**: A quick-action button shown on result cards

Example: A WorkOrder card shows buttons like:
- "Mark Complete" → calls `complete_work_order` action
- "Add Note" → calls `add_work_order_note` action
- "Assign Crew" → calls `assign_work_order` action

### 6.2 Action Flow

```
User clicks button → Frontend calls /api/actions/execute
                   → Backend validates JWT
                   → Routes to handler function
                   → Handler mutates database
                   → Returns ActionResponse
                   → Frontend updates UI
```

### 6.3 Key Files

| File | Purpose |
|------|---------|
| `COMPLETE_ACTION_EXECUTION_CATALOG.md` | **MASTER FILE** - All 67 actions with code (6,500 lines) |
| `docs/actions/ACTION_TO_TABLE_MAP.md` | Action → Table mapping |
| `docs/actions/ACTION_BACKEND_SPEC.md` | Backend implementation spec |
| `docs/micro-actions/MICRO_ACTION_REGISTRY.md` | All microaction definitions |
| `docs/micro-actions/ACTION_OFFERING_MAP.md` | Which actions show on which cards |

### 6.4 Handler Implementation

Handlers are in `apps/api/handlers/`:

```python
# Example: apps/api/handlers/work_order_mutation_handlers.py

async def complete_work_order(payload: Dict, context: ActionContext) -> Dict:
    """Mark a work order as completed."""
    work_order_id = payload.get("work_order_id")

    result = await supabase.from_("work_orders") \
        .update({"status": "completed", "completed_at": datetime.utcnow()}) \
        .eq("id", work_order_id) \
        .eq("yacht_id", context.yacht_id) \
        .execute()

    return ResponseBuilder.success(
        action="complete_work_order",
        result={"work_order_id": work_order_id},
        message="Work order marked complete"
    )
```

### 6.5 Action Categories

| Category | Actions | Handler File |
|----------|---------|--------------|
| Work Orders | create, complete, assign, add_note | `work_order_mutation_handlers.py` |
| Inventory | adjust_quantity, transfer, reorder | `inventory_handlers.py` |
| Handover | add_item, update_status, archive | `handover_handlers.py` |
| Documents | upload, view, download | `manual_handlers.py` |
| Purchasing | create_request, approve, reject | `purchasing_mutation_handlers.py` |

---

## 7. Situations System

### 7.1 What Are Situations?

A **Situation** is a contextual view that aggregates related data around an entity or event.

Example: "Generator Fault Situation" shows:
- The fault details
- Related work orders
- Equipment history
- Relevant manuals
- Suggested actions

### 7.2 Situation Types

| Type | Triggered By | Shows |
|------|--------------|-------|
| `fault_situation` | Clicking a fault | Fault + related WOs + equipment + manuals |
| `work_order_situation` | Clicking a WO | WO details + parts + crew + history |
| `equipment_situation` | Clicking equipment | Equipment + faults + maintenance history |
| `inventory_situation` | Low stock alert | Item + suppliers + reorder history |

### 7.3 Key Files

| File | Purpose |
|------|---------|
| `SITUATIONAL_STATE_ARCHITECTURE_V4.md` | Complete situation system design |
| `apps/web/src/app/situations/` | Frontend situation views |
| `apps/api/handlers/situation_handlers.py` | Backend situation data fetching |

---

## 8. API Endpoints

### 8.1 Main Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/search` | POST | Natural language search |
| `/api/actions/execute` | POST | Execute an action |
| `/api/pipeline/execute` | POST | Pipeline gateway (local/remote/replay) |
| `/health` | GET | Health check |

### 8.2 Search Request/Response

**Request:**
```json
{
  "query": "overdue work orders",
  "context": {
    "yacht_id": "uuid-here"
  }
}
```

**Response:**
```json
{
  "success": true,
  "query": "overdue work orders",
  "ranked_groups": [
    {
      "group_type": "work_orders",
      "title": "Overdue Work Orders",
      "items": [
        {
          "id": "wo-123",
          "title": "Replace oil filter",
          "entity_type": "work_order",
          "microactions": [
            {"action_id": "complete_work_order", "label": "Complete"},
            {"action_id": "assign_work_order", "label": "Assign"}
          ]
        }
      ]
    }
  ]
}
```

### 8.3 Action Request/Response

**Request:**
```json
{
  "action": "complete_work_order",
  "payload": {
    "work_order_id": "wo-123"
  },
  "context": {
    "yacht_id": "uuid-here"
  }
}
```

**Response:**
```json
{
  "success": true,
  "action": "complete_work_order",
  "result": {
    "work_order_id": "wo-123"
  },
  "message": "Work order marked complete"
}
```

---

## 9. Production Pipeline

### 9.1 Deployment Architecture

```
GitHub (universal_v1 branch)
        │
        ├──► Vercel (auto-deploy frontend)
        │    └── apps/web → https://celesteos.vercel.app
        │
        └──► Render (auto-deploy backend)
             └── apps/api → https://cloud-pms.onrender.com

Supabase Cloud (manual config)
        └── Database → https://xxx.supabase.co
```

### 9.2 Environment Variables (Production)

**Render Dashboard:**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=<production service key>
SUPABASE_JWT_SECRET=<production jwt secret>
OPENAI_API_KEY=<openai key>
LOG_LEVEL=INFO
PIPELINE_MODE=local
```

**Vercel Dashboard:**
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<production anon key>
NEXT_PUBLIC_API_URL=https://cloud-pms.onrender.com
```

### 9.3 Deploy Process

1. Push to `universal_v1` branch
2. Render auto-deploys backend (~3 min)
3. Vercel auto-deploys frontend (~1 min)
4. Database migrations: Manual via Supabase dashboard

### 9.4 Prod-Parity Testing

The Pipeline Gateway allows testing local code against production data:

```bash
# Record production responses as cassettes
PIPELINE_MODE=remote PIPELINE_RECORD=1 ./scripts/dev/prove_prod_parity.sh

# Replay cassettes for deterministic tests
PIPELINE_MODE=replay ./scripts/dev/prove_prod_parity.sh --replay
```

---

## 10. Testing Strategy

### 10.1 Test Types

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/unit/` | Individual function tests |
| Integration | `tests/integration/` | API endpoint tests |
| E2E | `tests/e2e/` | Full user flow tests |
| Smoke | `tests/smoke/` | Quick production checks |

### 10.2 Running Tests

```bash
# Backend unit tests
cd apps/api && pytest

# Frontend tests
cd apps/web && npm test

# E2E tests (requires running services)
cd apps/web && npx playwright test

# Prod-parity proof
./scripts/dev/prove_prod_parity.sh
```

### 10.3 Test Data

- Local: `supabase/seed.sql` provides demo data
- Tests use yacht_id: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`

---

## 11. File Index

### 11.1 Root Documentation Files

| File | Lines | Purpose |
|------|-------|---------|
| `COMPLETE_ACTION_EXECUTION_CATALOG.md` | 6,584 | **MASTER** - All 67 actions with code |
| `ARCHITECTURE_V4_COMPLETE.md` | 2,130 | System architecture |
| `ACTION_SYSTEM_ARCHITECTURE.md` | 1,357 | Action system design |
| `SITUATIONAL_STATE_ARCHITECTURE_V4.md` | 1,202 | Situations system |
| `COMPLETE_ACTION_CATALOG_SPEC.md` | 1,175 | Action specifications |
| `P0_ACTION_CONTRACTS.md` | 1,376 | Priority 0 action contracts |
| `DATABASE_SCHEMA_EXECUTION_SPEC.md` | 800+ | Database column specs |

### 11.2 docs/ Folder Structure

```
docs/
├── actions/
│   ├── ACTION_TO_TABLE_MAP.md      # Action → Table mapping
│   └── ACTION_BACKEND_SPEC.md      # Backend implementation
├── micro-actions/
│   ├── MICRO_ACTION_REGISTRY.md    # All microactions
│   ├── ACTION_OFFERING_MAP.md      # Card → Actions mapping
│   └── ACTION_OFFERING_RULES.md    # Display rules
├── architecture/
│   └── *.md                        # Architecture docs
├── design/
│   └── *.md                        # Design specs
├── dev/
│   └── *.md                        # Developer guides
└── ONBOARDING.md                   # THIS FILE
```

### 11.3 Code Structure

```
apps/
├── api/                            # Backend (FastAPI)
│   ├── microaction_service.py      # Main app
│   ├── handlers/                   # Action handlers
│   │   ├── work_order_mutation_handlers.py
│   │   ├── inventory_handlers.py
│   │   ├── handover_handlers.py
│   │   └── ...
│   ├── routes/                     # API routes
│   ├── action_router/              # JWT validation
│   ├── pipeline_gateway.py         # Local/Remote/Replay
│   └── schema_validator.py         # Response validation
│
├── web/                            # Frontend (Next.js)
│   └── src/
│       ├── app/                    # Pages
│       ├── components/             # UI components
│       └── lib/                    # Utilities

contracts/
└── pipeline_response.schema.json   # API response schema

scripts/dev/
├── prove_prod_parity.sh            # Prod-parity test harness
├── supabase_start.sh               # Start local DB
└── supabase_reset.sh               # Reset local DB

supabase/
├── migrations/                     # Database migrations
├── seed.sql                        # Test data
└── config.toml                     # Supabase config
```

---

## 12. Common Questions

### Q: How do I add a new action?

1. Add handler function in `apps/api/handlers/<category>_handlers.py`
2. Register in action router (`apps/api/action_router/`)
3. Add to `COMPLETE_ACTION_EXECUTION_CATALOG.md`
4. Add microaction button in frontend component

### Q: How do I add a new database table?

1. Create migration: `supabase migration new add_my_table`
2. Edit `supabase/migrations/<timestamp>_add_my_table.sql`
3. Add RLS policies
4. Run: `supabase db reset`
5. Update `DATABASE_SCHEMA_EXECUTION_SPEC.md`

### Q: How do I test against production data?

```bash
PIPELINE_MODE=remote ./scripts/dev/prove_prod_parity.sh
```

### Q: Where is the main API entry point?

`apps/api/microaction_service.py`

### Q: Where are all the actions defined?

`COMPLETE_ACTION_EXECUTION_CATALOG.md` (6,584 lines)

### Q: How does authentication work?

- Frontend: Supabase Auth (JWT tokens)
- Backend: JWT validation via `apps/api/action_router/validators/jwt_validator.py`
- All requests include JWT in Authorization header
- JWT contains `yacht_id` for RLS

### Q: Why are there so many .md files in root?

Historical documentation. Key files are listed in [File Index](#11-file-index). Others are archived/obsolete.

### Q: How do I see the database?

- Local: http://127.0.0.1:54323 (Supabase Studio)
- Production: Supabase Dashboard

### Q: What's the difference between local and production?

| Aspect | Local | Production |
|--------|-------|------------|
| Database | Docker PostgreSQL | Supabase Cloud |
| API | localhost:8000 | cloud-pms.onrender.com |
| Frontend | localhost:3000 | celesteos.vercel.app |
| Data | Seed data | Real data |

---

## Need Help?

1. Check this document first
2. Search `*.md` files: `grep -r "keyword" docs/`
3. Check `COMPLETE_ACTION_EXECUTION_CATALOG.md` for action details
4. Check handler files in `apps/api/handlers/`

---

*This document was generated to help new developers onboard quickly. Keep it updated!*
