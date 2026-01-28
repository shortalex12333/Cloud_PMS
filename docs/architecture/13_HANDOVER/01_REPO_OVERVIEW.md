# Repository Overview

**Cloud PMS (Property Management System for Superyachts)**

---

## 🎯 Purpose

Cloud PMS is a **multi-tenant yacht management platform** that provides:
- **Document search** across yacht technical manuals, schematics, logs
- **Fault tracking** and maintenance management
- **Intelligent search** with natural language understanding
- **Action-oriented responses** (P0 Actions system)
- **Multi-yacht isolation** (one system, many yachts, data separation)

**Think:** "Google for yacht operations + maintenance tracking + intelligent actions"

---

## 🏢 Repository Structure

### Monorepo Layout
```
Cloud_PMS/
├── apps/
│   ├── web/              # Next.js frontend (Vercel)
│   └── api/              # FastAPI backend (Railway/AWS)
├── packages/             # Shared utilities (if any)
├── tests/                # Test suites
└── HANDOVER_2026_01_09/  # This handover documentation
```

---

## 📁 Frontend: apps/web/ (Next.js 14)

### Key Directories

#### `apps/web/src/lib/`
**Core utilities and clients**

- **`supabaseClient.ts`**
  - Authenticated Supabase client instance
  - Used by ALL READ microactions
  - Preserves user JWT token
  - Location: `apps/web/src/lib/supabaseClient.ts`

- **`authHelpers.ts`** ⚠️ Recently modified
  - `getYachtId()`: Queries `auth_users` to get user's yacht_id
  - `getYachtSignature()`: Generates HMAC-SHA256 signature for yacht isolation
  - `getCurrentUser()`: Returns full user context
  - Location: `apps/web/src/lib/authHelpers.ts:207-212`
  - **Change:** Now queries `auth_users` (was `auth_users_yacht`)

- **`apiClient.ts`**
  - `callCelesteApi()`: Wrapper for backend API calls
  - `searchWithStream()`: Streaming search
  - `getFullAuthContext()`: Assembles complete auth payload
  - Location: `apps/web/src/lib/apiClient.ts`

- **`auth.ts`** ⚠️ Recently modified
  - `getCurrentUser()`: Gets user data from `auth_users`
  - Location: `apps/web/src/lib/auth.ts:72-86`
  - **Change:** Now queries `auth_users` (was `auth_users_yacht`)

#### `apps/web/src/components/`
**UI Components**

- **`situations/`** - Contextual components for search results
  - `DocumentSituationView.tsx` ⚠️ Recently modified
    - Displays document preview and actions
    - **Change:** Now uses authenticated client (line 82-84)
    - Location: `apps/web/src/components/situations/DocumentSituationView.tsx`

- **`actions/`** - P0 Action components
  - `CreateWorkOrderFromFault.tsx`
  - `AddToHandover.tsx`
  - Each action has form + submission logic

- **`modals/`** - Modal dialogs
  - `AddPhotoModal.tsx`
  - `CreateFaultModal.tsx`

#### `apps/web/src/hooks/`
**React Hooks**

- **`useCelesteSearch.ts`**
  - Main search hook
  - Handles debouncing, caching, streaming
  - Location: `apps/web/src/hooks/useCelesteSearch.ts:204-214`

#### `apps/web/src/contexts/`
**React Contexts**

- **`AuthContext.tsx`**
  - Global authentication state
  - Provides current user to all components

#### `apps/web/src/app/`
**Next.js App Router**

- `app/api/integrations/` - API routes for OAuth callbacks
  - `outlook/callback/route.ts` ⚠️ Recently modified
    - Location: `apps/web/src/app/api/integrations/outlook/callback/route.ts:136-141`
    - **Change:** Now queries `auth_users` (was `auth_users_yacht`)

---

## 📁 Backend: apps/api/ (FastAPI)

### Key Files

#### `microaction_service.py`
**Main API service**

- **Endpoints:**
  - `POST /v1/search` - Primary search endpoint
  - `POST /v2/search` - Situation-aware search (V1 Agent)
  - Location: `apps/api/microaction_service.py:1478-1493`

#### `pipeline_service.py`
**Legacy search pipeline**

- **Endpoints:**
  - `POST /search` - Original search (deprecated)
  - `POST /webhook/search` - Frontend webhook endpoint
  - Location: `apps/api/pipeline_service.py:203-218`

#### `middleware/auth.py`
**Authentication Middleware** ✅ Trustworthy

**Functions:**
- `decode_jwt(token)` - Validates JWT from Supabase
- `extract_yacht_id(token)` - Gets yacht_id from JWT
- `extract_user_id(token)` - Gets user_id from JWT
- `validate_user_jwt()` - FastAPI dependency for protected routes
- `inject_yacht_context()` - FastAPI dependency to inject yacht_id

**Security:**
- Validates JWT signature using `SUPABASE_JWT_SECRET`
- Checks expiration
- Extracts `sub` (user_id) and `yacht_id` from payload

Location: `apps/api/middleware/auth.py`

#### `action_router/`
**P0 Actions System**

Structure:
```
action_router/
├── registry.py           # Action registry (maps action_id → handler)
├── schemas/              # Pydantic schemas for actions
├── dispatchers/          # Internal vs N8N dispatchers
└── handlers/             # Individual action handlers
```

**How it works:**
1. Frontend calls `POST /v1/actions/execute` with `action_id` and `payload`
2. Backend looks up handler in registry
3. Executes action (create work order, add to handover, etc.)
4. Returns success/failure response

Location: `apps/api/action_router/`

---

## 🗄️ Database: Supabase PostgreSQL

### Production Instance
- **URL:** `vzsohavtuotocgrfkfyd.supabase.co`
- **Schema:** `public`

### Key Tables

#### `auth_users` ⚠️ Recently modified
**User → Yacht Mapping**

Columns:
- `id` - Primary key (UUID)
- `auth_user_id` - Supabase Auth user ID (UUID)
- `email` - User email
- `yacht_id` - Yacht assignment (UUID) ← **Recently fixed**
- `created_at`, `updated_at`

**Purpose:** Maps authenticated users to their assigned yacht

**Recent Changes:**
- Added SELECT policy: `auth_users_select_own`
- Granted SELECT to `authenticated` role
- Updated yacht_id for `x@alex-short.com` to `85fe1119...`

**Location:** Supabase table
**RLS:** ENABLED
**Policy:** Users can SELECT only their own row (`auth_user_id = auth.uid()`)

#### `search_document_chunks` ✅ Has working RLS
**Embedded document chunks for vector search**

Columns:
- `chunk_id` - Primary key (UUID)
- `yacht_id` - Yacht isolation (UUID)
- `doc_path` - Storage path
- `embedding` - Vector embedding
- `chunk_text` - Text content
- `metadata` - JSON metadata

**RLS Policy:**
```sql
WHERE yacht_id IN (
  SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
)
```

#### `doc_metadata` ✅ Has working RLS
**Document metadata and location**

Columns:
- `doc_id` - Primary key (UUID)
- `yacht_id` - Yacht isolation (UUID)
- `title`, `file_name`, `storage_path`
- `equipment_tags`, `maintenance_tags`

**RLS Policy:** Same yacht_id isolation

#### `faults` ✅ Has working RLS
**Maintenance fault tracking**

Columns:
- `id` - Primary key (UUID)
- `yacht_id` - Yacht isolation
- `title`, `description`, `severity`
- `equipment_id`, `created_by`, `status`

#### `work_orders`
**Work order management**

Linked to faults, equipment, parts

#### `handovers`
**Shift handover notes**

Created by P0 Actions (`add_to_handover`)

#### `yachts`
**Yacht master data**

- `id` - Yacht UUID
- `name`, `flag`, `owner`

---

## 🔑 Authentication & Authorization

### Authentication Flow

1. **User Login**
   - Frontend calls `supabase.auth.signInWithPassword()`
   - Supabase Auth validates credentials
   - Returns JWT token with payload:
     ```json
     {
       "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
       "email": "x@alex-short.com",
       "role": "authenticated",
       "iat": 1736438400,
       "exp": 1736442000
     }
     ```
   - JWT stored in localStorage

2. **Frontend Auth**
   - `getSession()` retrieves JWT
   - Supabase client auto-includes JWT in headers
   - `getYachtId()` queries `auth_users` to get yacht assignment

3. **Backend Auth**
   - Frontend sends JWT in `Authorization: Bearer <token>`
   - Backend middleware validates JWT signature
   - Extracts `user_id` and `yacht_id` from payload

### Authorization (RLS)

**Row Level Security Policies:**

Every table with yacht-specific data has RLS policy:
```sql
CREATE POLICY "<table>_yacht_isolation"
ON <table>
FOR SELECT
TO authenticated
USING (
  yacht_id IN (
    SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
  )
);
```

**How it works:**
- PostgreSQL intercepts every query
- Automatically adds `WHERE yacht_id = <user's yacht_id>`
- Users CANNOT see data from other yachts
- Enforced at database level (cannot bypass)

---

## 🔄 Data Flow

### Search Flow

```
User types "generator cooling" in search bar
  ↓
[FRONTEND] useCelesteSearch hook
  ↓
[FRONTEND] getYachtId() queries auth_users → yacht_id
  ↓
[FRONTEND] getYachtSignature(yacht_id) → HMAC-SHA256 signature
  ↓
[FRONTEND] Assembles payload:
  {
    query: "generator cooling",
    auth: {
      user_id: "a35cad0b...",
      yacht_id: "85fe1119...",
      yacht_signature: "<hash>"
    }
  }
  ↓
[FRONTEND] POST /webhook/search
  ↓
[BACKEND] Validates JWT
  ↓
[BACKEND] Extracts yacht_id from request body
  ↓
[BACKEND] Queries search_document_chunks (RLS applied)
  ↓
[BACKEND] Returns results (only documents for user's yacht)
  ↓
[FRONTEND] Displays search results
```

### Document Access Flow

```
User clicks document in search results
  ↓
[FRONTEND] DocumentSituationView renders
  ↓
[FRONTEND] Queries search_document_chunks (RLS applied)
  ↓
[RLS] Checks: chunk's yacht_id = user's yacht_id?
  ↓
[RLS] If YES: Returns chunk data
[RLS] If NO: Returns 0 rows (406 error)
  ↓
[FRONTEND] Queries doc_metadata (RLS applied)
  ↓
[FRONTEND] Gets storage_path
  ↓
[FRONTEND] Generates signed URL for Supabase Storage
  ↓
[FRONTEND] Displays document in iframe
```

---

## 🎨 Architecture Patterns

### READ vs MUTATE Microactions

**READ Microactions** (Frontend Direct)
- Use: `import { supabase } from '@/lib/supabaseClient'`
- Examples:
  - Display document
  - Show fault details
  - List work orders
- **Why:** Fast, no backend round-trip, RLS enforced automatically

**MUTATE Microactions** (Backend API)
- Use: `callCelesteApi('/v1/actions/execute', { action_id, payload })`
- Examples:
  - Create work order
  - Add to handover
  - Update fault status
- **Why:** Complex business logic, validation, side effects, audit logging

### Multi-Tenancy (Yacht Isolation)

**Strategy:** Shared database, row-level isolation

**Implementation:**
- Every table has `yacht_id` column
- RLS policies enforce: `WHERE yacht_id = <user's yacht_id>`
- Frontend never specifies yacht_id (extracted from auth)
- Backend validates yacht_id matches JWT

**Benefits:**
- Single codebase for all yachts
- Cost-effective (shared infrastructure)
- Easy to add new yachts

**Risks:**
- RLS misconfiguration = data leakage
- Performance at scale (many yachts)

---

## 🧪 Testing

### Test User
- **Email:** `x@alex-short.com`
- **Password:** (Not in handover, ask user)
- **Yacht ID:** `85fe1119-b04c-41ac-80f1-829d23322598`

### Test Data Location
- **Documents:** Supabase Storage bucket `documents/85fe1119.../`
- **Search Chunks:** `search_document_chunks` table
- **Sample queries:** "generator cooling", "navigation equipment", "safety procedures"

### Local Development
```bash
# Frontend
cd apps/web
npm install
npm run dev  # localhost:3000

# Backend (not running locally in this session)
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload  # localhost:8000
```

---

## 🚀 Deployment

### Frontend (Vercel)
- **Project:** `c7s-projects-4a165667/cloud-pms`
- **Branch:** `universal_v1`
- **Deploy:** `vercel --prod` from repository root
- **Latest:** `cloud-ezkuoo4zj-c7s-projects-4a165667.vercel.app`

### Backend (Railway/AWS)
- **URL:** `https://pipeline-core.int.celeste7.ai`
- **Not modified in this session**

### Database (Supabase)
- **Managed:** No deployment needed
- **Migrations:** Run SQL directly in SQL Editor

---

## 📊 Repository Health

### Recent Activity
- ✅ Fixed authentication issues
- ✅ Updated frontend to use correct table
- ✅ Fixed RLS policies
- ⚠️ Still debugging 404 errors on auth_users

### Known Issues
1. Frontend 404 on auth_users despite correct RLS policy
2. Environment variable propagation on Vercel unclear
3. Some TypeScript warnings in build logs

### Code Quality
- TypeScript compilation: ✅ Passes
- ESLint warnings: ⚠️ Some (non-blocking)
- Tests: ❓ Not run in this session

---

**Next:** [02_ARCHITECTURE.md](./02_ARCHITECTURE.md) - Deep dive into system architecture
