# CLAUDE B: Complete Project Onboarding

You are implementing CelesteOS — a multi-tenant yacht planned maintenance system.

---

## CRITICAL: READ THIS FIRST

### Before You Do ANYTHING

1. **If you don't understand something, ASK THE USER.** Don't guess. Don't work around.
2. **Don't fake results.** Empty tests that pass are lies. Mocked data is not implementation.
3. **Verify everything.** Check tables exist. Check RLS works. Check endpoints respond.
4. **The user prefers honesty over appearing productive.** Say "I don't understand X" instead of producing fake work.

### What Previous Claude Got Wrong

Claude B made these mistakes - **DON'T REPEAT THEM**:

1. **Faked test results** - Tests passed but tested nothing real
2. **Didn't read the 3 folders** (16, 17, 18) - Guessed instead of reading specs
3. **Assumed tables existed** - Wrote code for tables that weren't created
4. **Worked around problems** - Instead of stopping and asking
5. **Optimized for appearing productive** - Green CI badges, completed todos, but no real work done

---

## SECTION 0: SYSTEM ARCHITECTURE (UNDERSTAND THIS FIRST)

### How Everything Connects

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CelesteOS ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐     ┌──────────────────────┐                     │
│  │     Cloud_PMS        │     │   handover_export    │                     │
│  │   (Next.js App)      │────▶│   (Python FastAPI)   │                     │
│  │                      │     │                      │                     │
│  │ - Main web UI        │     │ - Handover PDF/HTML  │                     │
│  │ - Search interface   │     │ - Email extraction   │                     │
│  │ - Work orders        │     │ - Sign-off workflow  │                     │
│  │ - Faults             │     │                      │                     │
│  │ - Equipment          │     │ Deployed: Render     │                     │
│  │                      │     │ srv-d5k0avchg0os738  │                     │
│  │ Deployed: Vercel     │     └──────────┬───────────┘                     │
│  └──────────┬───────────┘                │                                 │
│             │                            │                                 │
│             │         ┌──────────────────┴──────────────────┐              │
│             │         │                                      │              │
│             ▼         ▼                                      ▼              │
│  ┌─────────────────────────┐              ┌─────────────────────────────┐  │
│  │      MASTER DB          │              │       TENANT DB             │  │
│  │  (Shared across all)    │              │   (One per yacht)           │  │
│  │                         │              │                             │  │
│  │ URL: qvzmkaamzaqxpzbewjxe.supabase.co │ URL: vzsohavtuotocgrfkfyd... │  │
│  │                         │              │                             │  │
│  │ Tables (NEED CREATING): │              │ Tables (ALREADY EXIST):     │  │
│  │ - role_definitions      │◀────────────▶│ - user_profiles             │  │
│  │ - department_definitions│  References  │ - pms_work_orders           │  │
│  │ - domain_codes          │              │ - pms_faults                │  │
│  │                         │              │ - pms_equipment             │  │
│  │                         │              │ - pms_parts                 │  │
│  │                         │              │ - pms_documents             │  │
│  │                         │              │                             │  │
│  │                         │              │ Tables (NEED CREATING):     │  │
│  │                         │              │ - handover_entries          │  │
│  │                         │              │ - handover_drafts           │  │
│  │                         │              │ - handover_signoffs         │  │
│  │                         │              │ - ledger_events             │  │
│  │                         │              │ - search_sessions           │  │
│  └─────────────────────────┘              └─────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Service Connections Table

| Service | Type | Location | Purpose | Talks To |
|---------|------|----------|---------|----------|
| **Cloud_PMS** | Next.js | /Users/celeste7/Documents/Cloud_PMS | Main web application | Tenant DB via Supabase JS |
| **handover_export** | FastAPI | github.com/shortalex12333/handover_export | Handover PDF/email export | Both Master + Tenant DB |
| **Supabase** | PostgreSQL | supabase.co | Database + Auth + Storage | N/A - it's the data layer |
| **Render** | PaaS | render.com | Hosts Python services | Connects to Supabase |
| **Vercel** | PaaS | vercel.com | Hosts Next.js app | Connects to Supabase |

### Request Flow Examples

**Search Flow:**
```
User searches "show generator faults"
         │
         ▼
Cloud_PMS (Next.js on Vercel)
         │
         ▼ Supabase JS client call
         │
Tenant DB (pms_faults table)
         │ RLS enforces yacht isolation
         ▼
Returns fault records → Cloud_PMS displays results
```

**Handover Export Flow:**
```
User clicks "Export Handover as PDF"
         │
         ▼
Cloud_PMS (fetch() call)
         │
         ▼
handover_export API (FastAPI on Render)
         │
         ▼
Queries Tenant DB → Generates PDF → Stores in Supabase Storage
         │
         ▼
Returns PDF URL to user
```

---

## SECTION 0.1: WHAT EXISTS VS WHAT DOESN'T

### EXISTING (You can query these NOW):

**Tenant DB Tables:**
- `user_profiles` ✅
- `pms_work_orders` ✅
- `pms_faults` ✅
- `pms_equipment` ✅
- `pms_parts` ✅
- `pms_documents` ✅
- `pms_document_chunks` ✅
- `pms_audit_log` ✅

**Cloud_PMS Code:**
- Next.js app structure ✅
- Supabase client ✅
- Basic CRUD for work orders, faults, equipment ✅

### NOT EXISTING (You must CREATE these):

**Master DB Tables (need migrations):**
- `role_definitions` ❌
- `department_definitions` ❌
- `domain_codes` ❌

**Tenant DB Tables (need migrations):**
- `handover_entries` ❌
- `handover_drafts` ❌
- `handover_draft_sections` ❌
- `handover_draft_items` ❌
- `handover_draft_edits` ❌
- `handover_signoffs` ❌
- `handover_exports` ❌
- `ledger_events` ❌
- `search_sessions` ❌
- `action_confirmations` ❌
- `role_search_profiles` ❌

**Cloud_PMS Code (need to build):**
- `src/lib/microactions/` ❌ (57 microactions)
- `src/lib/handlers/` ❌ (16 handlers)
- `src/lib/situations/` ❌ (situation engine)
- `src/lib/action-router/` ❌ (action routing)

**handover_export Code:**
- API structure ⚠️ (exists but incomplete)
- Service layer ❌ (draft_generator, signoff_manager, exporter)
- Tests ❌ (mostly empty)

### How to Verify Tables Exist

```bash
# List all tables in tenant DB
supabase db execute --sql "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"

# Check if specific table exists
supabase db execute --sql "SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'handover_entries')"

# Check RLS policies
supabase db execute --sql "SELECT * FROM pg_policies WHERE tablename = 'handover_entries'"
```

---

## SECTION 0.2: WHAT SUCCESS LOOKS LIKE

### For handover_export Service

**Success = User can complete this workflow:**

```
1. USER CREATES HANDOVER NOTE
   POST /api/v1/handover/entries
   Body: { "narrative": "Port generator overheated during approach to Monaco" }
   Response: 201 Created with entry ID

2. USER GENERATES DRAFT
   POST /api/v1/handover/drafts/generate
   System collects entries from past 12 hours
   Groups by bucket (Command, Deck, Engineering, etc.)
   Response: 201 Created with draft ID

3. USER REVIEWS DRAFT
   GET /api/v1/handover/drafts/{id}
   User sees 6 sections, can edit items

4. OUTGOING USER SIGNS OFF
   POST /api/v1/handover/drafts/{id}/accept
   State: IN_REVIEW → ACCEPTED

5. INCOMING USER COUNTERSIGNS
   POST /api/v1/handover/drafts/{id}/sign
   State: ACCEPTED → SIGNED

6. EXPORT TO PDF
   POST /api/v1/handover/drafts/{id}/export?format=pdf
   Response: { url: "https://...supabase.co/.../handover.pdf" }
```

### For Cloud_PMS (Folders 01-15)

**Success = User can do this:**

```
1. User types: "generator maintenance"
2. System parses intent: view_equipment_history
3. System extracts entity: equipment="generator"
4. Results show equipment card with maintenance history
5. Available actions: "View Manual", "Create Work Order", "View Faults"
6. User clicks "Create Work Order"
7. System shows confirmation with pre-filled data
8. User confirms
9. Work order created, ledger event recorded, confirmation shown
```

---

## SECTION 0.3: COMMON MISUNDERSTANDINGS

### "Is handover_export separate from Cloud_PMS?"

**YES.** Two different repos, two different tech stacks:

| | Cloud_PMS | handover_export |
|-|-----------|-----------------|
| Language | TypeScript | Python |
| Framework | Next.js | FastAPI |
| Deployed on | Vercel | Render |
| Purpose | Main web UI | Handover API + Email |
| Database | Tenant DB only | Both Master + Tenant |

Cloud_PMS calls handover_export via HTTP fetch().

### "Which database should I connect to?"

| Task | Database |
|------|----------|
| Get user's work orders | Tenant DB |
| Get yacht's equipment | Tenant DB |
| Get role definitions | Master DB |
| Save handover entry | Tenant DB |
| Look up domain codes | Master DB |

**Most operations use Tenant DB.** Master DB is for global lookups.

### "What are RPC functions?"

RPC = Remote Procedure Call. PostgreSQL functions called via Supabase:

```typescript
const { data } = await supabase.rpc('generate_handover_draft', {
  p_outgoing_user_id: userId,
  p_handover_date: today
});
```

### "What does 'multi-tenant' mean?"

Each yacht is a **tenant**. Data is completely isolated:
- Yacht A's crew cannot see Yacht B's work orders
- Enforced at database level via RLS
- Environment variables specify yacht: `yTEST_YACHT_001_SUPABASE_*`

---

## SECTION 0.4: WHAT NOT TO DO

1. **Don't fake test results** - If tests pass but you're not sure why, investigate
2. **Don't push migrations without verifying** - Check table exists after push
3. **Don't assume tables exist** - Query pg_tables to verify
4. **Don't work around problems** - Ask why it's not working
5. **Don't optimize for appearing productive** - Real work over green badges
6. **Don't guess database schema** - Read the spec files
7. **Don't skip reading folders 16, 17, 18** - They are the PRIMARY specs

---

## SECTION 0.5: QUESTIONS YOU SHOULD ASK

### At the Start

1. "What's already built?" → Ask user to clarify current state
2. "What databases exist and what's in them?" → Verify with queries
3. "What's the relationship between docs and code?" → Docs are specs, you create code
4. "What does success look like?" → See Section 0.2

### During Implementation

1. "Before I push this migration, can you verify?" → Always check
2. "This returns mock data - should I implement real logic?" → Yes, always
3. "The spec says X but code does Y - which is correct?" → Ask user
4. "I'm not sure if this table exists - how do I check?" → Query pg_tables
5. "Tests pass but I'm unsure if they test real functionality" → They probably don't

---

## SECTION 1: PROJECT OVERVIEW

### What is CelesteOS?

CelesteOS is a multi-tenant SaaS for superyacht fleet management. Each yacht (vessel) is a tenant with isolated data. The system provides:

- Planned Maintenance System (PMS) - Work orders, faults, equipment tracking
- Document Management - Manuals, certificates, procedures
- Handover System - Shift handover notes between crew
- Search Intelligence - Natural language search with entity extraction
- Ledger & Proof - Immutable audit trail of all actions
- Role-Based Access - 45+ yacht roles (Captain, Chief Engineer, Bosun, etc.)

### Core UX Principles (NON-NEGOTIABLE)

From `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/17_ux_operating_system/09-guardrails-and-threats.md`:

1. **Search is the PRIMARY interface** (not dashboards)
2. **Every mutation produces a confirmation**
3. **NO silent automation** - user confirms all actions
4. **Handover is a document, not a workspace**
5. **Celeste proposes, humans decide**
6. **NO inferred intent without showing uncertainty**
7. **NO performance scoring** - No crew ranking
8. **NO "overdue" logic in ledger** - Facts only, no judgment
9. **Reads are collapsed, not hidden**
10. **NO dashboards as primary surface**

---

## SECTION 2: REPOSITORY STRUCTURE

### Main Application Repository

Location: /Users/celeste7/Documents/Cloud_PMS
Type: Next.js + Supabase
Purpose: Main web application

```
Cloud_PMS/
├── src/
│   ├── app/                    # Next.js App Router pages
│   ├── components/             # React components
│   ├── lib/                    # Utilities, Supabase client
│   │   ├── supabase/          # Supabase client (EXISTS)
│   │   ├── microactions/      # TO BE CREATED (57 actions)
│   │   ├── handlers/          # TO BE CREATED (16 handlers)
│   │   ├── situations/        # TO BE CREATED (situation engine)
│   │   └── action-router/     # TO BE CREATED (action routing)
│   └── hooks/                  # React hooks
├── supabase/
│   ├── migrations/             # SQL migration files
│   └── seed.sql                # Seed data
├── tests/
│   ├── contracts/              # API contract tests
│   └── e2e/                    # End-to-end tests
├── .env.local                  # Local environment
├── .env.e2e.local              # E2E test environment
└── playwright.config.ts        # Playwright test config
```

### Handover Export Repository (You Build This)

Location: https://github.com/shortalex12333/handover_export
Type: Python FastAPI
Purpose: Handover export API + Email extraction pipeline
Render Service ID: srv-d5k0avchg0os738oel2g

```
handover_export/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Environment config
│   ├── dependencies.py         # Dependency injection
│   ├── routers/
│   │   ├── health.py           # Health check endpoints
│   │   ├── auth.py             # Azure OAuth
│   │   ├── handover_entries.py # Entry CRUD
│   │   ├── handover_drafts.py  # Draft lifecycle
│   │   ├── handover_export.py  # PDF/HTML/Email export
│   │   └── email_extraction.py # Email pipeline
│   ├── services/               # MOSTLY NEED IMPLEMENTING
│   │   ├── draft_generator.py
│   │   ├── signoff_manager.py
│   │   ├── exporter.py
│   │   ├── azure_auth.py
│   │   ├── graph_client.py
│   │   ├── email_pipeline.py
│   │   ├── classifier.py
│   │   └── merger.py
│   ├── models/
│   │   ├── handover.py
│   │   ├── signoff.py
│   │   ├── export.py
│   │   └── email.py
│   └── utils/
│       ├── encryption.py
│       ├── pdf_renderer.py
│       └── logging.py
├── templates/
│   ├── handover_report.html
│   └── email_body.html
├── tests/                      # MOSTLY EMPTY - NEED WRITING
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── supabase/
│   └── migrations/
├── .github/
│   └── workflows/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## SECTION 3: DOCUMENTATION STRUCTURE

### Documentation Location

/Users/celeste7/Desktop/Cloud_PMS_docs_v2/

### Three Implementation Folders (READ THESE)

| Folder | Purpose | Priority |
|--------|---------|----------|
| **16_Roles_of_users/** | Role system, 45+ yacht roles, departments | P0 |
| **17_ux_operating_system/** | Search, Ledger, Confirmations, UX constraints | P0 |
| **18_handover_buckets/** | Handover export system (AUTHORITATIVE) | P0 |

### What Each Folder Contains

**16_Roles_of_users/**
```
- IMPL_01_role_system.sql.md    # SQL for role_definitions, department_definitions
- readme.md                      # Role taxonomy overview
- all_ranks.md                   # Complete list of 45+ yacht roles

Defines:
- 45+ yacht roles (Captain, Chief Engineer, Bosun, etc.)
- 6 departments (Command, Deck, Engineering, Interior, Purser, Medical)
- Role-based search biasing
- Role-based handover bucket visibility
```

**17_ux_operating_system/**
```
- IMPL_01_search_intelligence.sql.md   # Search with entity extraction
- IMPL_02_ledger_proof.sql.md          # Immutable event log
- IMPL_04_confirmation_rewards.sql.md  # Action confirmations
- 01-vision-and-purpose.md             # UX philosophy
- 09-guardrails-and-threats.md         # CRITICAL CONSTRAINTS (read this!)

Defines:
- Search intelligence (parse "generator faults" → intent + entity)
- Ledger & Proof (immutable audit trail of ALL actions)
- Confirmation system (every mutation gets feedback)
- 10 UX constraints (no dashboards, no silent automation, etc.)
```

**18_handover_buckets/**
```
- CLAUDE_B_IMPLEMENTATION_PROMPT.json  # START HERE - Full task breakdown
- IMPL_RENDER_DEPLOYMENT.md            # Env vars, API specs, repo structure
- IMPL_EMAIL_AZURE_INTEGRATION.md      # Azure OAuth, Graph API
- IMPL_PYTHON_PIPELINE.md              # 8-stage AI pipeline
- ANALYSIS_feasibility.md              # Architecture overview
- 10_supabase_schema.md                # Database schema
- 16_api_endpoints.md                  # API endpoint specs
- 00_principles.md                     # Handover principles
- 01_bucket_taxonomy.md                # 6 presentation buckets
- 02_domain_to_bucket_map.md           # 28 domain codes → 6 buckets
- 05_handover_draft_model.md           # State machine

Defines:
- Two handover sources: User entries (PRIMARY) + Email extraction (SECONDARY)
- 28 domain codes (NAV-01, ENG-02, etc.)
- 6 presentation buckets (Command, Deck, Engineering, Interior, Admin, Pending)
- State machine: DRAFT → IN_REVIEW → ACCEPTED → SIGNED → EXPORTED
- All database tables for handover system
```

### Master Index

`/Users/celeste7/Desktop/Cloud_PMS_docs_v2/IMPLEMENTATION_INDEX.md`

Lists ALL implementation specs, dependency order, and new tables/functions.

### Ground Truth Document

`/Users/celeste7/Desktop/Cloud_PMS_docs_v2/GROUND_TRUTH_FOR_CLAUDE.md`

Comprehensive reference answering all common questions about the system.

---

## SECTION 4: DATABASE ARCHITECTURE

### Multi-Tenant Design

```
┌─────────────────────────────────────────────────────────────┐
│                      MASTER DATABASE                         │
│  (Shared across all tenants)                                │
│                                                             │
│  Tables that NEED CREATING:                                 │
│  • role_definitions (45+ yacht roles)                       │
│  • department_definitions                                   │
│  • domain_codes (28 codes)                                  │
│                                                             │
│  URL: https://qvzmkaamzaqxpzbewjxe.supabase.co             │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ References
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 TENANT DATABASE (per yacht)                  │
│  (Isolated data per vessel)                                 │
│                                                             │
│  EXISTING tables:                                           │
│  • user_profiles, pms_work_orders, pms_faults              │
│  • pms_equipment, pms_parts, pms_documents                 │
│                                                             │
│  Tables that NEED CREATING:                                 │
│  • search_sessions, entity_definitions, intent_patterns     │
│  • ledger_events, ledger_day_anchors                       │
│  • action_confirmations, confirmation_templates            │
│  • handover_entries, handover_drafts, handover_signoffs    │
│  • role_search_profiles, role_handover_buckets             │
│                                                             │
│  Test Yacht URL: https://vzsohavtuotocgrfkfyd.supabase.co  │
└─────────────────────────────────────────────────────────────┘
```

### Row Level Security (RLS)

Every table uses vessel isolation:

```sql
-- Pattern for ALL tenant tables
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vessel_isolation" ON table_name
    FOR ALL USING (
        vessel_id IN (
            SELECT yacht_id FROM user_profiles WHERE id = auth.uid()
        )
    );
```

**This means:**
- User can only see rows where yacht_id matches their yacht
- Enforced at database level, not application level
- Even if code has bugs, wrong-yacht data can't leak

### Verifying RLS Works

```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Check policies exist
SELECT * FROM pg_policies WHERE tablename = 'handover_entries';

-- Test as different user (via Supabase dashboard)
```

---

## SECTION 5: SUPABASE

### What is Supabase?

Supabase is an open-source Firebase alternative providing:
- PostgreSQL database with RLS
- Auth (JWT-based authentication)
- Storage (file uploads)
- Edge Functions (serverless)
- Realtime (subscriptions)

### Supabase CLI Commands

```bash
# Install
npm install -g supabase

# Login
supabase login

# Link to project
supabase link --project-ref vzsohavtuotocgrfkfyd

# Create migration
supabase migration new migration_name

# Push migrations to remote
supabase db push

# Reset database (DESTRUCTIVE)
supabase db reset

# Generate types
supabase gen types typescript --local > src/types/database.ts

# Execute SQL
supabase db execute --sql "SELECT * FROM pg_tables WHERE schemaname = 'public'"
```

### Migration File Structure

```sql
-- supabase/migrations/20260114000001_create_handover_entries.sql

-- ============================================================================
-- TABLE: handover_entries
-- Purpose: Raw truth seeds for handover notes
-- ============================================================================

CREATE TABLE IF NOT EXISTS handover_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id UUID NOT NULL,
    creator_id UUID NOT NULL REFERENCES auth.users(id),

    narrative TEXT NOT NULL,
    domain_code TEXT,
    source_type TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'confirmed',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('proposed', 'confirmed', 'dismissed'))
);

-- Enable RLS
ALTER TABLE handover_entries ENABLE ROW LEVEL SECURITY;

-- Vessel isolation policy
CREATE POLICY "handover_entries_vessel_isolation" ON handover_entries
    FOR ALL USING (
        vessel_id IN (SELECT yacht_id FROM user_profiles WHERE id = auth.uid())
    );

-- Indexes
CREATE INDEX idx_handover_entries_vessel ON handover_entries(vessel_id, created_at DESC);
CREATE INDEX idx_handover_entries_creator ON handover_entries(creator_id, created_at DESC);
```

### RPC Functions

```sql
-- supabase/migrations/20260114000010_create_rpcs.sql

CREATE OR REPLACE FUNCTION generate_handover_draft(
    p_outgoing_user_id UUID,
    p_incoming_user_id UUID DEFAULT NULL,
    p_handover_date DATE DEFAULT CURRENT_DATE,
    p_shift_type TEXT DEFAULT 'day'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_draft_id UUID;
    v_vessel_id UUID;
BEGIN
    -- Get vessel from user profile
    SELECT yacht_id INTO v_vessel_id
    FROM user_profiles WHERE id = p_outgoing_user_id;

    -- Create draft
    INSERT INTO handover_drafts (
        vessel_id, outgoing_user_id, incoming_user_id,
        handover_date, shift_type, status
    ) VALUES (
        v_vessel_id, p_outgoing_user_id, p_incoming_user_id,
        p_handover_date, p_shift_type, 'DRAFT'
    ) RETURNING id INTO v_draft_id;

    -- Populate sections and items from confirmed entries
    -- ... implementation details ...

    RETURN v_draft_id;
END;
$$;
```

---

## SECTION 6: ENVIRONMENT VARIABLES

### Naming Convention

```
MASTER_SUPABASE_*           → Master database (shared)
{YACHT_ID}_SUPABASE_*       → Tenant database (per yacht)
```

### Environment Variables File

Location: `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/env vars/render_hadnover_env_vars.md`

```bash
# ===========================================
# SUPABASE - MASTER DB
# ===========================================
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=eyJ...
MASTER_SUPABASE_JWT_SECRET=wXka4UZu...

# ===========================================
# SUPABASE - TENANT DB (Test Yacht)
# ===========================================
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJ...
yTEST_YACHT_001_SUPABASE_JWT_SECRET=ep2o/+mE...

# ===========================================
# AZURE OAUTH (Email Integration)
# ===========================================
AZURE_TENANT_ID=d44c2402-b515-4d6d-a392-5cfc88ae53bb
AZURE_CLIENT_ID=a744caeb-9896-4dbf-8b85-d5e07dba935c
AZURE_CLIENT_SECRET=vhG8Q~1~...

# ===========================================
# OPENAI (AI Classification)
# ===========================================
OPENAI_API_KEY=sk-proj-y288-...

# ===========================================
# APPLICATION
# ===========================================
LOG_LEVEL=INFO
PYTHONPATH=/opt/render/project/src
ENVIRONMENT=production
```

### Loading in Python

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Master DB
    MASTER_SUPABASE_URL: str
    MASTER_SUPABASE_SERVICE_KEY: str
    MASTER_SUPABASE_JWT_SECRET: str

    # Tenant DB (loaded dynamically per request)
    # Pattern: {YACHT_ID}_SUPABASE_URL

    # Azure
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str

    # OpenAI
    OPENAI_API_KEY: str

    # App
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
```

---

## SECTION 7: AZURE OAUTH (Email Integration)

### What It Does

Allows users to connect their Microsoft Outlook account to extract emails into handover entries.

### Azure App Registration

```
App Name: CelesteOS.Outlook
App ID: a744caeb-9896-4dbf-8b85-d5e07dba935c
Tenant ID: d44c2402-b515-4d6d-a392-5cfc88ae53bb
Permissions: Mail.Read, MailboxSettings.Read, User.Read, offline_access
Auth Flow: OAuth2 Authorization Code with PKCE
```

### OAuth Flow

```
User clicks "Connect Email"
        │
        ▼
Generate PKCE code_verifier + code_challenge
        │
        ▼
Redirect to Microsoft login
        │
        ▼
User authenticates with Microsoft
        │
        ▼
Microsoft redirects with auth code
        │
        ▼
Exchange code for access_token + refresh_token
        │
        ▼
Store tokens (encrypted) in database
        │
        ▼
Use access_token to call Microsoft Graph API
```

### Microsoft Graph API

```
# Fetch emails
GET https://graph.microsoft.com/v1.0/me/messages
    ?$top=100
    &$select=id,subject,from,receivedDateTime,bodyPreview,body
    &$orderby=receivedDateTime desc

# Headers
Authorization: Bearer {access_token}
```

---

## SECTION 8: DOCKER

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ ./app/
COPY templates/ ./templates/

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MASTER_SUPABASE_URL=${MASTER_SUPABASE_URL}
      - MASTER_SUPABASE_SERVICE_KEY=${MASTER_SUPABASE_SERVICE_KEY}
      - yTEST_YACHT_001_SUPABASE_URL=${yTEST_YACHT_001_SUPABASE_URL}
      - yTEST_YACHT_001_SUPABASE_SERVICE_KEY=${yTEST_YACHT_001_SUPABASE_SERVICE_KEY}
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=DEBUG
    volumes:
      - ./app:/app/app:ro
    restart: unless-stopped

volumes:
  supabase_data:
```

### Docker Commands

```bash
# Build image
docker build -t handover-export-api .

# Run with docker-compose
docker-compose up --build

# Run tests in container
docker-compose run api pytest tests/ -v

# Shell into container
docker-compose exec api /bin/bash

# View logs
docker-compose logs -f api

# Stop and remove
docker-compose down -v
```

---

## SECTION 9: TESTING PHILOSOPHY

### Test Pyramid

```
         ┌─────────┐
         │   E2E   │  ← Few, slow, high confidence
         ├─────────┤
         │Contract │  ← API endpoint tests
         ├─────────┤
         │Integr.  │  ← Service + DB tests
         ├─────────┤
         │  Unit   │  ← Many, fast, isolated
         └─────────┘
```

### 15 Test Cases Per File (MANDATORY)

For EVERY test file, write exactly 15 test cases:

| # | Category | Description |
|---|----------|-------------|
| 1 | Success | Happy path - normal flow |
| 2 | Success | Happy path - minimal data |
| 3 | Success | Happy path - maximum load |
| 4 | Failure | Missing required fields |
| 5 | Failure | Invalid data types |
| 6 | Failure | Database constraint violation |
| 7 | Edge | Empty arrays/objects |
| 8 | Edge | Maximum string length |
| 9 | Edge | Unicode/special characters |
| 10 | User | Lazy - partial submission |
| 11 | User | Impatient - rapid clicks |
| 12 | User | Confused - wrong order |
| 13 | System | Network timeout |
| 14 | System | Concurrent access |
| 15 | System | Recovery after failure |

### Test File Example

```python
# tests/contract/test_handover_entries_api.py
import pytest
from httpx import AsyncClient

class TestHandoverEntriesAPI:
    """15 test cases for handover entries API"""

    # === SUCCESS (1-3) ===

    async def test_create_entry_success_normal(self, client: AsyncClient):
        """1. Happy path - create entry with all fields"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Engine room check completed",
            "domain_code": "ENG-01",
            "priority": "normal"
        })
        assert response.status_code == 201
        assert response.json()["id"] is not None

    async def test_create_entry_success_minimal(self, client: AsyncClient):
        """2. Happy path - only required fields"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Note"
        })
        assert response.status_code == 201

    async def test_create_entry_success_bulk(self, client: AsyncClient):
        """3. Happy path - create 100 entries"""
        for i in range(100):
            response = await client.post("/api/v1/handover/entries", json={
                "narrative": f"Entry {i}"
            })
            assert response.status_code == 201

    # === FAILURE (4-6) ===

    async def test_create_entry_fail_missing_narrative(self, client: AsyncClient):
        """4. Fail - missing required narrative"""
        response = await client.post("/api/v1/handover/entries", json={
            "domain_code": "ENG-01"
        })
        assert response.status_code == 422

    async def test_create_entry_fail_invalid_domain(self, client: AsyncClient):
        """5. Fail - invalid domain_code"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Test",
            "domain_code": "INVALID-99"
        })
        assert response.status_code == 400

    async def test_create_entry_fail_vessel_isolation(self, client: AsyncClient, other_vessel_token):
        """6. Fail - cannot access other vessel's data"""
        response = await client.get(
            "/api/v1/handover/entries",
            headers={"Authorization": f"Bearer {other_vessel_token}"}
        )
        assert len(response.json()) == 0  # Empty, not error

    # === EDGE (7-9) ===

    async def test_create_entry_edge_empty_tags(self, client: AsyncClient):
        """7. Edge - empty tags array"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Test",
            "tags": []
        })
        assert response.status_code == 201

    async def test_create_entry_edge_max_length(self, client: AsyncClient):
        """8. Edge - narrative at 10,000 char limit"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "X" * 10000
        })
        assert response.status_code == 201

    async def test_create_entry_edge_unicode(self, client: AsyncClient):
        """9. Edge - Greek, Cyrillic, emoji"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Ελληνικά Русский 🚢⚓"
        })
        assert response.status_code == 201

    # === USER BEHAVIOUR (10-12) ===

    async def test_create_entry_user_lazy(self, client: AsyncClient):
        """10. User lazy - no domain code (should auto-infer)"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Generator maintenance needed"
        })
        assert response.status_code == 201

    async def test_create_entry_user_impatient(self, client: AsyncClient):
        """11. User impatient - double submit same entry"""
        payload = {"narrative": "Unique entry test"}
        r1 = await client.post("/api/v1/handover/entries", json=payload)
        r2 = await client.post("/api/v1/handover/entries", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201  # Duplicates allowed

    async def test_create_entry_user_confused(self, client: AsyncClient):
        """12. User confused - edit after confirm"""
        r = await client.post("/api/v1/handover/entries", json={"narrative": "Test"})
        entry_id = r.json()["id"]
        await client.post(f"/api/v1/handover/entries/{entry_id}/confirm")

        r2 = await client.patch(f"/api/v1/handover/entries/{entry_id}", json={
            "narrative": "Changed"
        })
        assert r2.status_code == 409  # Conflict

    # === SYSTEM (13-15) ===

    async def test_create_entry_system_timeout(self, client: AsyncClient, mock_slow_db):
        """13. System - database timeout handling"""
        response = await client.post("/api/v1/handover/entries", json={
            "narrative": "Test"
        })
        assert response.status_code in [201, 504]

    async def test_create_entry_system_concurrent(self, client: AsyncClient):
        """14. System - 10 concurrent creates"""
        import asyncio
        tasks = [
            client.post("/api/v1/handover/entries", json={"narrative": f"Concurrent {i}"})
            for i in range(10)
        ]
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 201 for r in responses)

    async def test_create_entry_system_recovery(self, client: AsyncClient, mock_failing_db):
        """15. System - recovery after partial failure"""
        r1 = await client.post("/api/v1/handover/entries", json={"narrative": "Test"})
        assert r1.status_code == 500

        mock_failing_db.recover()
        r2 = await client.post("/api/v1/handover/entries", json={"narrative": "Test"})
        assert r2.status_code == 201
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=html

# Specific category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/contract/ -v
pytest tests/e2e/ -v

# Single file
pytest tests/contract/test_handover_entries_api.py -v

# Stop on first failure
pytest tests/ -v -x

# Run in parallel
pytest tests/ -v -n auto
```

---

## SECTION 10: GITHUB WORKFLOWS

### Directory Structure

```
.github/
└── workflows/
    ├── ci.yml          # Lint + Unit tests (every push)
    ├── test.yml        # Full test suite (PR to main)
    ├── db-migrate.yml  # Database migrations (manual)
    └── deploy.yml      # Deploy to Render (push to main)
```

### ci.yml - Continuous Integration

```yaml
name: CI

on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install linters
        run: pip install ruff black mypy

      - name: Run ruff
        run: ruff check .

      - name: Run black
        run: black --check .

      - name: Run mypy
        run: mypy app/ --ignore-missing-imports

  unit-tests:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit tests
        run: pytest tests/unit/ -v --tb=short --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

### GitHub Secrets Required

```
MASTER_SUPABASE_URL
MASTER_SUPABASE_SERVICE_KEY
yTEST_YACHT_001_SUPABASE_URL
yTEST_YACHT_001_SUPABASE_SERVICE_KEY
OPENAI_API_KEY
AZURE_TENANT_ID
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
RENDER_DEPLOY_HOOK
```

---

## SECTION 11: RENDER DEPLOYMENT

### Service Configuration

```
Service Name: handover-export-api
Service ID: srv-d5k0avchg0os738oel2g
Type: Web Service
Environment: Python 3
Region: Frankfurt (EU)
Branch: main
Auto-Deploy: Yes (on push to main)
```

### Build & Start Commands

```
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

### Deployment Flow

```
1. Push to main branch
2. Render auto-detects push
3. Render runs build command
4. Render runs start command
5. Render pings /health
6. If 200 → deployment succeeds
7. Service available at: https://handover-export-api.onrender.com
```

---

## SECTION 12: IMPLEMENTATION PHASES

### Phase 1: Repository Setup
- [ ] Clone handover_export repo
- [ ] Create directory structure
- [ ] Create requirements.txt
- [ ] Create app/main.py with FastAPI
- [ ] Implement /health endpoint
- [ ] Verify local run works

### Phase 2: Database Schema
- [ ] Create all migrations for new tables
- [ ] Enable RLS on all tables
- [ ] Create RPC functions
- [ ] **VERIFY tables exist after push**

### Phase 3: API Implementation
- [ ] Implement all routers
- [ ] Implement all services (real logic, not mocks)
- [ ] Test endpoints work with real database

### Phase 4: Testing
- [ ] Write 15 tests per file
- [ ] Tests must test REAL functionality
- [ ] Achieve 90%+ coverage

### Phase 5: Deploy
- [ ] Push to main
- [ ] Verify Render auto-deploy
- [ ] Check /health endpoint
- [ ] Run smoke tests

---

## SECTION 13: SUCCESS CRITERIA

- [ ] All database tables created (verify with queries)
- [ ] All RLS policies enforcing isolation
- [ ] All RPC functions working
- [ ] All API endpoints responding
- [ ] **15 test cases per test file**
- [ ] **Tests test REAL functionality**
- [ ] 90%+ code coverage
- [ ] All GitHub workflows green
- [ ] Render deployment healthy

---

## BEGIN IMPLEMENTATION

**Before starting:**
1. Read GROUND_TRUTH_FOR_CLAUDE.md
2. Read the three folders (16, 17, 18)
3. Verify what exists vs what doesn't
4. Ask questions if anything is unclear

**Then start with Phase 1: Repository Setup.**

Read the full task breakdown in:
`/Users/celeste7/Desktop/Cloud_PMS_docs_v2/18_handover_buckets/CLAUDE_B_IMPLEMENTATION_PROMPT.json`
