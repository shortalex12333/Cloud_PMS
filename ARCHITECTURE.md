# System Architecture

**Complete technical architecture of CelesteOS Cloud PMS**

**Purpose:** Understand how the entire system works
**Audience:** Engineers who want deep technical understanding
**Reading time:** 20 minutes

---

## 🎯 High-Level Overview

**CelesteOS Cloud PMS is a natural language yacht maintenance system built on:**
- **Frontend:** Next.js + React + TypeScript (Single Surface UI)
- **Backend:** FastAPI + Python (Microaction Router)
- **Database:** Supabase (PostgreSQL with RLS)
- **AI:** GPT-4o-mini (Natural language → action detection)

**Architecture Pattern:** Multi-tenant SaaS with RLS isolation

---

## 🏗️ System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER BROWSER                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Frontend (Next.js - Vercel)                       │    │
│  │  - SpotlightSearch component                       │    │
│  │  - ContextPanel component                          │    │
│  │  - JWT stored in memory                            │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    │ HTTPS
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                  Backend (FastAPI - Render)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Pipeline Service (FastAPI)                          │  │
│  │  - POST /search (GPT-4o-mini → action detection)    │  │
│  │  - POST /v1/actions/execute (microaction router)    │  │
│  │  - JWT validation                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Action Router (p0_actions_routes.py)               │  │
│  │  - 81 handlers in elif chain                        │  │
│  │  - Validates, transforms, executes                   │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    │ Supabase Client
                    │
┌───────────────────▼─────────────────────────────────────────┐
│               Database (Supabase - PostgreSQL)              │
│  ┌─────────────────────────┐   ┌────────────────────────┐  │
│  │  Master DB              │   │  Tenant DB             │  │
│  │  - user_profiles        │   │  - pms_work_orders     │  │
│  │  - yachts               │   │  - pms_faults          │  │
│  │  - oauth_tokens         │   │  - pms_equipment       │  │
│  │  (Shared across yachts) │   │  - pms_parts           │  │
│  │                         │   │  - pms_audit_log       │  │
│  │                         │   │  (Per-yacht isolation) │  │
│  └─────────────────────────┘   └────────────────────────┘  │
│                                                             │
│  RLS Policies: yacht_id filtering on ALL tenant tables     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Multi-Tenant Architecture

### Master DB vs Tenant DB

**Master DB (Shared):**
- **Purpose:** User authentication, yacht registry, global config
- **Tables:**
  - `user_profiles` - User accounts (email, password hash, role)
  - `yachts` - Yacht registry (name, owner, subscription)
  - `oauth_tokens` - OAuth integration tokens
  - `tenant_keys` - Maps yacht_id → Supabase instance URL
- **Access:** All yachts share this database
- **Security:** Each user has access only to their yacht_id

**Tenant DB (Isolated):**
- **Purpose:** One yacht's PMS data
- **Tables:**
  - `pms_work_orders` - Maintenance work orders
  - `pms_faults` - Equipment faults
  - `pms_equipment` - Asset registry
  - `pms_parts` - Parts catalog + inventory
  - `pms_audit_log` - Audit trail
  - ... (all pms_* tables)
- **Access:** RLS enforces yacht_id filtering
- **Security:** Cross-yacht access impossible (enforced at DB level)

**Why this architecture?**
- **Data isolation:** Yacht A cannot see Yacht B's data
- **Scalability:** Can move yachts to different Supabase instances
- **Compliance:** Easier to meet data residency requirements
- **Performance:** Each yacht's queries only scan their data

---

## 🔄 Request Flow (End-to-End)

### Journey 1: Natural Language Query → Action Button

**User types: "create a work order for the generator"**

```
1. Frontend (SpotlightSearch.tsx)
   ↓ User types query in search bar
   ↓ useCelesteSearch hook detects Enter/debounce
   ↓

2. POST /search
   ↓ Headers: Authorization: Bearer {JWT}
   ↓ Body: {"query": "create a work order for the generator"}
   ↓

3. Backend (pipeline_service.py)
   ↓ Validate JWT → Extract user_id, yacht_id
   ↓ Call GPT-4o-mini with query + context
   ↓

4. GPT-4o-mini
   ↓ Analyzes query
   ↓ Detects intent: "create_work_order"
   ↓ Extracts entities: equipment mention "generator"
   ↓

5. Backend Returns
   ↓ {
   ↓   "actions": [
   ↓     {
   ↓       "action": "create_work_order",
   ↓       "label": "Create Work Order",
   ↓       "pre_filled_context": {"equipment_name": "generator"},
   ↓       "form_fields": [...]
   ↓     }
   ↓   ],
   ↓   "results": [... search results ...]
   ↓ }
   ↓

6. Frontend (SpotlightSearch.tsx)
   ↓ Receives response
   ↓ Renders action button: "Create Work Order"
   ↓ Renders search results below
```

### Journey 2: Action Button Click → Database Mutation

**User clicks "Create Work Order" button**

```
1. Frontend (SpotlightSearch.tsx)
   ↓ User clicks action button
   ↓ Opens modal with form
   ↓ Form pre-filled with context (equipment: "generator")
   ↓

2. User Fills Form
   ↓ Title: "Replace generator oil filter"
   ↓ Description: "Filter clogged, need replacement"
   ↓ Priority: "routine"
   ↓

3. User Clicks Submit
   ↓ Frontend validates required fields
   ↓ Calls executeAction()
   ↓

4. actionClient.ts
   ↓ Gets JWT from supabase.auth.getSession()
   ↓ Calls POST /v1/actions/execute
   ↓ Headers: Authorization: Bearer {JWT}
   ↓ Body: {
   ↓   "action": "create_work_order",
   ↓   "context": {
   ↓     "yacht_id": "...",  // From JWT
   ↓     "user_id": "..."    // From JWT
   ↓   },
   ↓   "payload": {
   ↓     "title": "Replace generator oil filter",
   ↓     "description": "Filter clogged...",
   ↓     "priority": "routine"
   ↓   }
   ↓ }
   ↓

5. Backend (pipeline_service.py)
   ↓ Validate JWT → Extract user_id, yacht_id
   ↓ Route to p0_actions_routes.py
   ↓

6. Action Router (p0_actions_routes.py)
   ↓ elif action in ("create_work_order", "create_wo"):
   ↓   # Validate required fields
   ↓   if not payload.get("title"):
   ↓       raise HTTPException(400, "title is required")
   ↓
   ↓   # Transform data
   ↓   priority = map_priority(payload.get("priority"))
   ↓
   ↓   # Write to database
   ↓   wo_data = {
   ↓       "yacht_id": yacht_id,
   ↓       "title": payload["title"],
   ↓       "status": "planned",
   ↓       "created_by": user_id,
   ↓       ...
   ↓   }
   ↓   result = db_client.table("pms_work_orders").insert(wo_data).execute()
   ↓
   ↓   # Return success
   ↓   return {"status": "success", "work_order_id": result.data[0]["id"]}
   ↓

7. Database (Supabase)
   ↓ RLS policy checks yacht_id matches user's JWT
   ↓ Inserts row into pms_work_orders
   ↓ Returns inserted row
   ↓

8. Backend Returns
   ↓ {
   ↓   "status": "success",
   ↓   "work_order_id": "50e9c919-6fc2-4b3d-b913-e0da3285f14d",
   ↓   "message": "Work order created"
   ↓ }
   ↓

9. Frontend (actionClient.ts)
   ↓ Receives response
   ↓ Closes modal
   ↓ Shows toast: "✅ Work order created"
   ↓ Refreshes data (if needed)
```

---

## 🔑 Authentication & Authorization Flow

### Login Flow

```
1. User enters email + password
   ↓

2. Frontend calls Supabase Auth
   ↓ supabase.auth.signInWithPassword({email, password})
   ↓

3. Supabase Auth (Master DB)
   ↓ Validates credentials
   ↓ Queries user_profiles table
   ↓ Generates JWT with:
   ↓   - user_id (sub)
   ↓   - yacht_id (custom claim)
   ↓   - role (custom claim)
   ↓   - exp (expiration)
   ↓

4. Frontend Stores JWT
   ↓ In memory (React state)
   ↓ NOT in localStorage (security)
   ↓

5. All API Calls Include JWT
   ↓ Authorization: Bearer {JWT}
```

### JWT Structure

```json
{
  "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",  // user_id
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",  // Which yacht
  "role": "engineer",  // User role
  "email": "john@yacht.com",
  "iat": 1737561600,  // Issued at
  "exp": 1737648000   // Expires (24 hours)
}
```

### Authorization Flow

```
1. Frontend sends JWT in every request
   ↓ Authorization: Bearer {JWT}
   ↓

2. Backend validates JWT
   ↓ Verify signature (Supabase public key)
   ↓ Check expiration
   ↓ Extract user_id, yacht_id, role
   ↓

3. Backend uses yacht_id for RLS
   ↓ db_client = get_tenant_supabase_client(tenant_alias)
   ↓ Sets session: yacht_id = {yacht_id from JWT}
   ↓

4. All DB queries filtered by yacht_id
   ↓ RLS policy enforces:
   ↓   WHERE yacht_id = current_setting('app.current_yacht_id')::uuid
   ↓

5. Cross-yacht access impossible
   ↓ Even if user tries to query different yacht_id
   ↓ RLS blocks the query
```

---

## 📊 Database Architecture

### RLS (Row Level Security)

**Every tenant table has this policy:**
```sql
CREATE POLICY "yacht_isolation" ON pms_work_orders
FOR ALL
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**What this means:**
- Every query is automatically filtered by yacht_id
- User on Yacht A cannot see Yacht B's rows
- Enforced at PostgreSQL level (not application)
- Fail-safe: Wrong yacht_id → 0 rows returned

**Example:**
```javascript
// Frontend request
const { data } = await supabase
  .from('pms_work_orders')
  .select('*');

// PostgreSQL executes
SELECT * FROM pms_work_orders
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'  -- Automatic!
```

### Soft Delete Pattern

**Hard deletes are BLOCKED:**
```sql
CREATE POLICY "prevent_hard_deletes" ON pms_work_orders
FOR DELETE
USING (false);  -- Always deny DELETE
```

**Must use soft delete:**
```sql
UPDATE pms_work_orders
SET deleted_at = NOW(),
    deleted_by = 'user-uuid',
    deletion_reason = 'User requested deletion'
WHERE id = '...';
```

**Queries filter soft-deleted:**
```sql
SELECT * FROM pms_work_orders
WHERE yacht_id = '...'
  AND deleted_at IS NULL;  -- Exclude soft-deleted
```

**Why soft delete?**
- Audit trail preserved
- Can restore if needed
- Compliance requirement (ISO 9001)
- No accidental data loss

---

## 🎨 Frontend Architecture

### Single Surface Paradigm

**One URL:** `/app`
**No routing:** All state-based, no navigation

**Layout:**
```
┌──────────────────────────────────────────────┐
│                                              │
│            [SpotlightSearch]                 │
│            Always visible, centered          │
│                                              │
│                                              │
│                                              │
│                              ┌─────────────┐ │
│                              │ ContextPanel│ │
│                              │ (slides in) │ │
│                              │             │ │
│                              │ Entity      │ │
│                              │ Details     │ │
│                              │             │ │
│                              │ [Actions]   │ │
│                              └─────────────┘ │
└──────────────────────────────────────────────┘
```

**State management:**
- **SurfaceContext** - Global UI state (panel open/closed)
- **SituationState** - Current entity focus (IDLE/CANDIDATE/ACTIVE)
- **AuthContext** - User auth (JWT, yacht_id, user_id)

**No page reloads:** Everything via state transitions

### Component Hierarchy

```
App Surface (page.tsx)
├── AuthProvider
│   ├── SurfaceProvider
│   │   ├── SpotlightSearch
│   │   │   ├── Search Input
│   │   │   ├── Action Buttons (if detected)
│   │   │   ├── Search Results
│   │   │   └── Email Inbox (inline)
│   │   │
│   │   ├── ContextPanel
│   │   │   ├── Entity Details (work order, fault, equipment, etc.)
│   │   │   ├── Action Buttons (contextual)
│   │   │   ├── Notes Section
│   │   │   ├── Parts Section
│   │   │   └── History Section
│   │   │
│   │   └── Action Modals (overlay when action clicked)
│   │       ├── Form Fields
│   │       ├── Validation
│   │       └── Submit/Cancel
```

### Data Flow (Frontend)

```
User Action
  ↓
Component Event Handler
  ↓
Hook (useCelesteSearch, useSituationState, etc.)
  ↓
API Call (actionClient.executeAction)
  ↓
Backend Response
  ↓
Hook Updates State
  ↓
React Re-renders
  ↓
UI Updates
```

---

## ⚙️ Backend Architecture

### FastAPI Service Structure

```
apps/api/
├── pipeline_service.py          ← Main FastAPI app
│   ├── @app.post("/search")
│   └── @app.post("/v1/actions/execute")
│
├── routes/
│   └── p0_actions_routes.py     ← 81 handlers (elif chain)
│
├── microaction_service.py       ← Microaction utilities
├── microaction_extractor.py     ← GPT-4o-mini integration
├── auth.py                      ← JWT validation
└── database.py                  ← Supabase client management
```

### Action Router Pattern

**All 81 handlers in one file (p0_actions_routes.py):**
```python
async def handle_action_request(action: str, context: dict, payload: dict):
    # Extract context
    user_id = context.get("user_id")
    yacht_id = context.get("yacht_id")

    # Route to handler (elif chain)
    if action == "report_fault":
        # Handler code for report_fault
        ...
        return {"status": "success", "fault_id": "..."}

    elif action in ("create_work_order", "create_wo"):
        # Handler code for create_work_order
        ...
        return {"status": "success", "work_order_id": "..."}

    elif action == "mark_work_order_complete":
        # Handler code for mark_work_order_complete
        ...
        return {"status": "success"}

    # ... 78 more handlers

    else:
        raise HTTPException(404, f"Action '{action}' not found")
```

**Why elif chain instead of routing?**
- All handlers in one place (easier to search)
- Shared validation and context
- Simple to understand flow
- Performance: No routing overhead

**Tradeoff:** 4,160 lines in one file (but searchable)

### Database Client Management

**Two Supabase clients:**

1. **Master DB Client**
```python
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_KEY = os.getenv("MASTER_SUPABASE_SERVICE_ROLE_KEY")
master_client = create_client(MASTER_SUPABASE_URL, MASTER_SUPABASE_KEY)
```
Used for: User auth, yacht registry

2. **Tenant DB Client (per yacht)**
```python
def get_tenant_supabase_client(tenant_alias: str):
    # Lookup tenant URL from tenant_keys table
    tenant_url = get_tenant_url(tenant_alias)
    tenant_key = get_tenant_key(tenant_alias)

    tenant_client = create_client(tenant_url, tenant_key)

    # Set RLS context
    tenant_client.rpc('set_yacht_id', {'yacht_id': yacht_id}).execute()

    return tenant_client
```
Used for: All PMS queries (work orders, faults, equipment, parts)

---

## 🤖 AI Integration (GPT-4o-mini)

### Natural Language → Action Detection

**Endpoint:** `POST /search`

**Flow:**
```python
def extract_microactions(query: str, user_context: dict):
    # 1. Build prompt
    prompt = f"""
    User query: "{query}"
    User context: yacht_id={user_context['yacht_id']}

    Detect which microaction(s) this query intends.
    Available actions: {MICROACTION_REGISTRY}

    Return JSON: {{"actions": [...]}}
    """

    # 2. Call GPT-4o-mini
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1  # Low temperature for consistency
    )

    # 3. Parse response
    detected = json.loads(response.choices[0].message.content)

    return detected["actions"]
```

**Example input/output:**
```
Input: "create a work order for the generator"

Output: [
  {
    "action": "create_work_order",
    "confidence": 0.95,
    "extracted_entities": {
      "equipment_mention": "generator"
    }
  }
]
```

**Why GPT-4o-mini (not GPT-4)?**
- Faster (< 500ms response time)
- Cheaper ($0.15 per 1M tokens vs $30)
- Sufficient for intent detection
- Can handle 64 action vocabulary

---

## 📦 Deployment Architecture

**Production stack:**
```
Frontend:
- Platform: Vercel
- URL: https://app.celeste7.ai
- Framework: Next.js 14 (App Router)
- Deployment: Git push → auto-deploy

Backend:
- Platform: Render
- URL: https://pipeline-core.int.celeste7.ai
- Framework: FastAPI + uvicorn
- Deployment: Git push → auto-deploy

Database:
- Platform: Supabase
- Master DB: https://master.supabase.co
- Tenant DBs: Per-yacht Supabase instances
- Backups: Automatic daily

AI:
- Provider: OpenAI
- Model: gpt-4o-mini
- Endpoint: https://api.openai.com/v1/chat/completions
```

**See DEPLOYMENT_ARCHITECTURE.md for full details**

---

## 🔄 Data Synchronization

### Cache Strategy

**No caching (currently):**
- All queries go to database
- Fresh data every request
- Tradeoff: Slower but always current

**Future:** Redis cache layer for:
- Equipment list (changes rarely)
- Parts catalog (changes rarely)
- User profiles (changes rarely)

### Real-Time Updates

**Current:** Poll-based
- Frontend polls every 30 seconds
- Checks for new work orders, faults, etc.

**Future:** WebSocket/SSE
- Real-time push updates
- Supabase Realtime integration

---

## 🔒 Security Architecture

### Security Layers

**Layer 1: Frontend Validation**
- Required fields checked
- Enum values validated
- Length limits enforced
**Purpose:** UX (immediate feedback)
**NOT trusted:** Can be bypassed

**Layer 2: JWT Validation**
- Signature verified
- Expiration checked
- Claims extracted
**Purpose:** Authentication
**Cannot be bypassed:** Cryptographic

**Layer 3: Backend Validation**
- Required fields re-checked
- Entity existence verified
- Business logic validated
**Purpose:** Guard rails
**Cannot be bypassed:** Server-side

**Layer 4: Database RLS**
- yacht_id filtering enforced
- Cross-yacht access blocked
- Soft delete enforced
**Purpose:** Data isolation
**Cannot be bypassed:** PostgreSQL-level

**Defense in depth:** All 4 layers must pass

### Threat Model

**Protected against:**
- ✅ SQL injection (parameterized queries)
- ✅ Cross-yacht data access (RLS)
- ✅ XSS (React escapes by default)
- ✅ CSRF (JWT in header, not cookie)
- ✅ Unauthorized access (JWT required)
- ✅ Data tampering (audit log)
- ✅ Accidental deletion (soft delete)

**NOT protected against (yet):**
- ⚠️ Rate limiting (can spam API)
- ⚠️ DDoS (no WAF configured)
- ⚠️ Brute force login (no account lockout)

---

## 📈 Performance Characteristics

**Target latencies:**
- `/search` endpoint: < 1 second (GPT-4o-mini call)
- `/v1/actions/execute`: < 500ms (simple actions)
- Database query: < 100ms (indexed queries)
- Frontend render: < 100ms (React re-render)

**Bottlenecks:**
- GPT-4o-mini API (500ms-1s)
- Cross-region database latency (if yacht in EU, DB in US)
- Large audit log queries (100+ MB tables)

**Optimizations applied:**
- Indexes on yacht_id (all tables)
- Indexes on common foreign keys (equipment_id, work_order_id)
- Limit queries (never SELECT * without LIMIT)
- Connection pooling (Supabase Pooler)

---

## 🧪 Testing Architecture

**Test levels:**
1. **Unit tests** - Individual functions (Python: pytest, JS: none currently)
2. **Integration tests** - Handler + database (Playwright)
3. **E2E tests** - Full user journey (Playwright)
4. **Mutation proofs** - Database state verification (Playwright)

**Test database:**
- Separate Supabase instance
- TEST_YACHT_ID: `85fe1119-b04c-41ac-80f1-829d23322598`
- Cleaned between test runs (soft delete)

**CI/CD:**
- Git push → Vercel runs frontend build
- Git push → Render runs backend deploy
- Manual: Run Playwright tests locally

**Future:** Automated test runs on every PR

---

## 🎯 Design Decisions

### Why Single Surface (no routing)?

**Decision:** One URL (`/app`), all state-based

**Pros:**
- Simpler mental model
- Faster (no page reloads)
- More app-like UX
- Easier state management

**Cons:**
- No deep linking (mitigated with query params)
- No browser back/forward (by design)
- Harder to bookmark specific views

**Verdict:** Pros outweigh cons for this use case

### Why Microactions (not REST)?

**Decision:** Action-based API (`create_work_order`) not resource-based API (`POST /work_orders`)

**Pros:**
- Natural language alignment ("create a work order" → `create_work_order`)
- Context automatic (yacht_id, user_id from JWT)
- Audit trail built-in
- Business logic encapsulated

**Cons:**
- Not REST-compliant
- Harder to document (64 actions vs 10 endpoints)
- Can't use OpenAPI auto-gen tools

**Verdict:** Better UX for natural language interface

### Why Multi-Tenant (not separate DBs per yacht)?

**Decision:** RLS isolation in shared DB, not separate databases

**Pros:**
- Easier schema migrations (one migration, all yachts)
- Easier backup/restore (one database)
- Cost-effective (fewer Supabase instances)

**Cons:**
- RLS must be perfect (data leak risk)
- Performance can affect all yachts (noisy neighbor)
- Can't customize schema per yacht

**Verdict:** Good tradeoff for current scale (< 100 yachts)

---

## 📚 Related Documentation

- **MICROACTIONS_EXPLAINED.md** - Deep dive into microactions concept
- **SITUATIONS_EXPLAINED.md** - State machine for user focus
- **DATABASE_RELATIONSHIPS.md** - Complete schema reference
- **DEPLOYMENT_ARCHITECTURE.md** - Production deployment details

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team
**Architecture Review:** Quarterly
