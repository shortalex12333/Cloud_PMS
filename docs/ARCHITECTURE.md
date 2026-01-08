# CelesteOS Architecture

Cloud-first AI-powered Yacht PMS - System Architecture Overview

## Monorepo Structure

```
Cloud_PMS/
├── apps/                    # Deployable applications
│   ├── web/                 # Next.js frontend (Vercel)
│   ├── api/                 # FastAPI backend (Render)
│   └── worker/              # Background workers (Hetzner) [placeholder]
├── packages/                # Shared code
│   └── shared/              # Shared types/schemas [placeholder]
├── docs/                    # Documentation
│   ├── ARCHITECTURE.md      # This file
│   ├── DEPLOYMENT.md        # Deployment guide
│   ├── RANKING_SYSTEM.md    # Search ranking documentation
│   └── deprecated/          # Archived docs (n8n workflows, etc.)
├── database/                # Database migrations
│   ├── migrations/          # SQL migration files
│   └── setup_complete.sql   # Complete DB setup script
├── tests/                   # Test suites
│   └── action_router/       # Action router tests
├── scripts/                 # Development/deployment scripts
├── Makefile                 # Developer commands
└── README.md                # Project overview
```

---

## Frontend (`/apps/web`)

**Technology**: Next.js 14, React 18, TypeScript, Tailwind CSS
**Deployment**: Vercel
**Entry Point**: `apps/web/src/app/page.tsx`

### Key Components

- **Search Interface** (`src/components/SearchBar.tsx`): Universal search bar
- **Results Display** (`src/components/ResultCard.tsx`): Search result cards
- **Micro-Actions** (`src/components/MicroActions.tsx`): Contextual actions
- **Pages**:
  - `/search` - Search results page
  - `/dashboard` - Analytics dashboard
  - `/faults`, `/parts`, `/work-orders` - PMS modules
  - `/login` - Authentication
  - `/settings` - User settings
  - `/briefing` - Daily briefing

### Data Flow

```
User Input → SearchBar → POST /api/webhook/search
                            ↓
                         Backend Pipeline
                            ↓
                      Results + Actions
                            ↓
                      ResultCard Display
```

---

## Backend (`/apps/api`)

**Technology**: FastAPI, Python 3.11+, OpenAI API, Supabase
**Deployment**: Render
**Entry Point**: `apps/api/pipeline_service.py`

### Pipeline Architecture

The backend implements a 4-stage search pipeline:

```
1. EXTRACT    → Entity extraction from user query
2. PREPARE    → Capability preparation (determine what to search)
3. EXECUTE    → SQL execution + ranking
4. ACTIONS    → Micro-action generation
```

### Module Structure

```
apps/api/
├── pipeline_service.py       # FastAPI app, routes
├── pipeline_v1.py            # Pipeline orchestrator
├── extraction/               # Stage 1: Entity extraction
│   ├── entity_extractor.py
│   ├── intent_classifier.py
│   └── query_parser.py
├── prepare/                  # Stage 2: Capability prep
│   ├── capability_mapper.py
│   └── search_strategy.py
├── execute/                  # Stage 3: SQL execution
│   ├── sql_builder.py
│   ├── query_executor.py
│   └── result_ranker.py      # RAG Stage 4 ranking
├── actions/                  # Stage 4: Micro-actions
│   ├── action_generator.py
│   └── action_templates.py
├── handlers/                 # Micro-action handlers
│   ├── fault_handler.py
│   ├── parts_handler.py
│   └── work_order_handler.py
├── action_router/            # Action routing system
│   ├── router.py
│   ├── validators/           # Request validation
│   ├── dispatchers/          # Internal/external dispatch
│   └── schemas/              # Action schemas
├── integrations/             # External integrations
│   ├── supabase.py
│   ├── search_engine.py
│   └── predictive_engine.py
└── middleware/               # Auth middleware
    └── auth.py
```

### Ranking System

Located in `execute/result_ranker.py`, implements RAG Stage 4 techniques:
- Match mode hierarchy (EXACT_ID > EXACT_CANONICAL > EXACT_TEXT > FUZZY > VECTOR)
- Proximity scoring
- Catalog detection
- Intent-table priors
- Full scoring transparency

See `/docs/RANKING_SYSTEM.md` for details.

---

## Database Layer

**Technology**: Supabase (Postgres 15 + pgvector)
**Location**: `database/`

### Core Tables

- `yachts` - Vessel data
- `user_profiles` - User accounts (linked to auth.users)
- `user_roles` - RBAC permissions
- `pms_equipment` - Equipment inventory
- `pms_parts` - Spare parts
- `pms_faults` - Fault log
- `pms_work_orders` - Maintenance tasks
- `search_fault_code_catalog` - Diagnostic codes
- `search_handover_forms` - Handover documentation

### Security Model

- Row Level Security (RLS) enabled on all tables
- Per-yacht data isolation
- Role-based access control (HOD/Crew/Vendor)
- API tokens for device/agent access

See `/database/SECURITY_ARCHITECTURE.md` for details.

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
               ┌────────────────┐
               │  Vercel CDN    │ (Frontend)
               │  apps/web      │
               └────────┬───────┘
                        │
                        │ Search Query
                        ▼
               ┌────────────────┐
               │  Render.com    │ (Backend)
               │  apps/api      │
               │  Pipeline V1   │
               └────────┬───────┘
                        │
                        │ SQL Queries
                        ▼
               ┌────────────────┐
               │  Supabase      │ (Database)
               │  Postgres +    │
               │  pgvector      │
               └────────────────┘
```

### Production URLs

- Frontend: `https://celeste7.vercel.app`
- API: `https://api.celeste7.ai`
- Webhook: `https://api.celeste7.ai/webhook/search`
- Database: `vzsohavtuotocgrfkfyd.supabase.co`

---

## Data Flow Example

**Query**: "show me all faults"

```
1. User types query in SearchBar
2. Frontend POSTs to /api/webhook/search
3. Backend EXTRACT stage:
   - Intent: search_faults
   - Entities: []
4. Backend PREPARE stage:
   - Capability: search_faults
   - Table: pms_faults
5. Backend EXECUTE stage:
   - SQL: SELECT * FROM pms_faults WHERE yacht_id = ...
   - Ranking: Apply result_ranker scoring
6. Backend ACTIONS stage:
   - Generate micro-actions: [View Details, Update Status, Export]
7. Backend returns JSON response
8. Frontend renders ResultCards with actions
```

---

## Development Workflow

### Local Setup

```bash
# Install dependencies
make install

# Start frontend (port 3000)
make dev-web

# Start backend (port 8000)
make dev-api
```

### Testing

```bash
# Run all tests
make test

# Lint code
make lint

# Type check frontend
make typecheck
```

### Code Structure

- **Frontend**: React components → API calls → State management
- **Backend**: FastAPI routes → Pipeline orchestrator → Supabase
- **Database**: Supabase migrations → RLS policies → Triggers

---

## Migration from n8n

**Previous Architecture**:
- Search bar → n8n webhook → n8n workflow → Backend

**Current Architecture**:
- Search bar → Direct webhook → Backend pipeline

**Changes**:
- Removed n8n dependency
- Direct POST to `https://api.celeste7.ai/webhook/search`
- n8n workflows archived in `docs/deprecated/n8n-workflows/`

---

## Future Architecture

### Workers (`/apps/worker`)

Planned background processing:
- Document ingestion (PDFs, manuals)
- Vector index updates
- Scheduled reports
- Email notifications

Deployment: Hetzner Cloud

### Shared Packages (`/packages/shared`)

Planned shared code:
- TypeScript types for API contracts
- Zod schemas for validation
- Utility functions

---

## Key Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 | Server-side rendering, routing |
| UI | React 18 + Tailwind CSS | Component library, styling |
| Backend | FastAPI | High-performance API framework |
| Database | Supabase (Postgres) | Managed Postgres + Auth |
| Vector Search | pgvector | Semantic search |
| LLM | OpenAI GPT-4 | Entity extraction, ranking |
| Deployment | Vercel + Render | Serverless + container hosting |
| Monitoring | Vercel Analytics, Render Logs | Performance tracking |

---

## Security Considerations

- All API requests authenticated via Supabase JWT
- Row Level Security enforces yacht-level isolation
- API tokens hashed with SHA256
- Environment variables managed via platform secrets
- CORS restricted to known origins
- SQL injection prevented via parameterized queries

---

## Performance Optimizations

- Frontend: Next.js SSR, image optimization, code splitting
- Backend: Connection pooling, query caching, async I/O
- Database: Indexed columns, materialized views, query optimization
- Ranking: Multi-stage filtering reduces vector search load

---

## Documentation Map

- **This file** - Architecture overview
- `/docs/DEPLOYMENT.md` - Deployment instructions
- `/docs/RANKING_SYSTEM.md` - Search ranking details
- `/database/SECURITY_ARCHITECTURE.md` - Database security
- `/database/DATABASE_SCHEMA.md` - Table definitions
- `/docs/frontend_search_contract.md` - API contracts

For more details, explore the `/docs` directory.
