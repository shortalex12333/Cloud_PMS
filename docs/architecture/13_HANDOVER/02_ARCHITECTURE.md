# System Architecture

**Deep dive into Cloud PMS architecture, actions, microactions, and intent system**

---

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                   (Next.js 14 / Vercel)                     │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐│
│  │ Search Bar     │  │ Document     │  │ Fault Tracker   ││
│  │ Component      │  │ Viewer       │  │ Component       ││
│  └────────────────┘  └──────────────┘  └─────────────────┘│
│           │                   │                   │         │
│           └───────────────────┴───────────────────┘         │
│                              │                               │
│                    ┌─────────▼──────────┐                  │
│                    │  useCelesteSearch  │                  │
│                    │  Hook              │                  │
│                    └─────────┬──────────┘                  │
│                              │                               │
│         ┌────────────────────┼────────────────────┐        │
│         │                    │                    │        │
│   ┌─────▼──────┐      ┌─────▼──────┐      ┌─────▼──────┐ │
│   │ Supabase   │      │  Auth      │      │   API      │ │
│   │ Client     │      │  Helpers   │      │   Client   │ │
│   │ (READ)     │      │            │      │  (MUTATE)  │ │
│   └─────┬──────┘      └─────┬──────┘      └─────┬──────┘ │
└─────────┼────────────────────┼────────────────────┼────────┘
          │                    │                    │
          │ JWT Auth           │ JWT + yacht_id     │ JWT + yacht_signature
          │                    │                    │
┌─────────▼────────────────────▼────────────────────▼────────┐
│                      SUPABASE LAYER                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ PostgreSQL   │  │ Auth Service │  │ Storage      │    │
│  │ + RLS        │  │ (JWT)        │  │ (Documents)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                                       │           │
│         │ RLS Policies Check:                  │           │
│         │ yacht_id = user's yacht_id           │           │
│         └───────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
          │
          │ Service Role Key (Bypasses RLS)
          │
┌─────────▼─────────────────────────────────────────────────┐
│                         BACKEND                            │
│                  (FastAPI / Railway)                       │
│                                                             │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Search         │  │ Action       │  │ Auth         │ │
│  │ Pipeline       │  │ Router       │  │ Middleware   │ │
│  │                │  │ (P0 Actions) │  │              │ │
│  └────────────────┘  └──────────────┘  └──────────────┘ │
│          │                   │                  │         │
│          └───────────────────┴──────────────────┘         │
│                              │                             │
│                    ┌─────────▼────────┐                  │
│                    │  Supabase Client │                  │
│                    │ (Service Role)   │                  │
│                    └──────────────────┘                  │
└───────────────────────────────────────────────────────────┘
```

---

## 🎯 Actions vs Microactions

### Philosophy: "mess=failure"

The system distinguishes between **READ** and **MUTATE** operations with strict conventions:

### READ Microactions
**Definition:** Operations that display data without modification

**Implementation:**
- Use authenticated Supabase client from frontend
- Direct database queries (RLS enforced)
- No backend API call
- Fast, low-latency

**Examples:**
- Display document preview
- Show fault details
- List equipment
- View work orders

**Code Pattern:**
```typescript
// ✅ CORRECT: READ microaction
import { supabase } from '@/lib/supabaseClient';

const { data, error } = await supabase
  .from('search_document_chunks')
  .select('*')
  .eq('chunk_id', chunkId)
  .single();
```

**Location:** Frontend components directly query Supabase
- `apps/web/src/components/situations/DocumentSituationView.tsx:82-84`

### MUTATE Microactions (P0 Actions)
**Definition:** Operations that create, update, or delete data

**Implementation:**
- Use backend API endpoint
- POST to `/v1/actions/execute`
- Backend validates, applies business logic, logs
- Returns success/failure

**Examples:**
- Create work order
- Add to handover
- Update fault status
- Create equipment record

**Code Pattern:**
```typescript
// ✅ CORRECT: MUTATE microaction
import { callCelesteApi } from '@/lib/apiClient';

const result = await callCelesteApi('/v1/actions/execute', {
  method: 'POST',
  body: JSON.stringify({
    action_id: 'add_to_handover',
    payload: {
      title: 'Generator cooling issue',
      description: '...',
      severity: 'medium'
    }
  })
});
```

**Location:** Backend action router
- Registry: `apps/api/action_router/registry.py`
- Handlers: `apps/api/action_router/handlers/`

---

## 🚫 CRITICAL ANTI-PATTERNS

### ❌ DO NOT CREATE NEW SUPABASE CLIENT

**Wrong:**
```typescript
// ❌ LOSES AUTHENTICATION
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const { data } = await supabase
  .from('auth_users')
  .select('yacht_id');
// Result: 406 error (no JWT token attached)
```

**Right:**
```typescript
// ✅ PRESERVES AUTHENTICATION
import { supabase } from '@/lib/supabaseClient';

const { data } = await supabase
  .from('auth_users')
  .select('yacht_id');
// Result: JWT automatically included, RLS enforced correctly
```

**Why this matters:**
- Creating new client = new instance without authentication context
- Supabase client caches JWT token from `supabase.auth.getSession()`
- New instance doesn't have this cached token
- Result: All queries fail RLS checks

**Recently fixed:** `DocumentSituationView.tsx` was creating new client

---

## 🧩 P0 Actions System

### What are P0 Actions?

**P0 Actions** are user-initiated operations that require:
- Data validation
- Business logic
- Side effects (notifications, webhooks)
- Audit logging
- Complex state changes

### Action Registry

**Location:** `apps/api/action_router/registry.py`

**Structure:**
```python
ACTION_REGISTRY = {
    'add_to_handover': {
        'handler': add_to_handover_handler,
        'schema': AddToHandoverSchema,
        'description': 'Add item to shift handover notes',
        'dispatcher': 'internal'  # or 'n8n'
    },
    'create_work_order': {
        'handler': create_work_order_handler,
        'schema': CreateWorkOrderSchema,
        'description': 'Create maintenance work order',
        'dispatcher': 'internal'
    },
    # ... more actions
}
```

### Action Execution Flow

```
Frontend: User clicks "Add to Handover" button
  ↓
Frontend: Calls executeAction('add_to_handover', payload)
  ↓
[apiClient.ts] POST /v1/actions/execute
  ↓
[Backend] Action Router receives request
  ↓
[Backend] Validates JWT (middleware)
  ↓
[Backend] Extracts yacht_id from JWT
  ↓
[Backend] Looks up action in registry
  ↓
[Backend] Validates payload against schema
  ↓
[Backend] Dispatches to handler
  ↓
[Handler] add_to_handover_handler(payload, yacht_id)
  ↓
[Handler] Inserts row into handovers table
  ↓
[Handler] Returns success response
  ↓
Frontend: Shows success toast
```

### Action Handler Example

**Location:** `apps/api/action_router/handlers/add_to_handover.py` (hypothetical)

```python
from supabase import create_client

async def add_to_handover_handler(
    payload: AddToHandoverSchema,
    yacht_id: str,
    user_id: str
) -> dict:
    """
    Add item to shift handover notes
    """
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Bypasses RLS
    )

    # Insert handover item
    result = supabase.table('handovers').insert({
        'yacht_id': yacht_id,  # Enforced by backend
        'created_by': user_id,
        'title': payload.title,
        'description': payload.description,
        'severity': payload.severity,
        'created_at': 'now()'
    }).execute()

    # Log action
    log_action('add_to_handover', user_id, yacht_id, result.data)

    return {
        'success': True,
        'handover_id': result.data[0]['id']
    }
```

### Dispatchers

**Internal Dispatcher**
- Python function executed in FastAPI process
- Direct database access
- Fast, synchronous

**N8N Dispatcher**
- Sends webhook to N8N workflow automation
- Used for complex workflows (email notifications, Slack, etc.)
- Asynchronous, may take longer

**Location:** `apps/api/action_router/dispatchers/`

---

## 🔍 Intent System

### What is Intent?

The search system doesn't just match keywords—it **understands user intent**.

### Intent Types

**Location:** Backend pipeline processes query to extract intent

#### 1. `free-text` Intent
**Description:** General search, no specific target
**Example:** "generator cooling"
**Response:** Documents, faults, equipment matching query

#### 2. `fault` Intent
**Description:** User looking for fault/issue information
**Example:** "show me generator faults"
**Response:** Fault records, related documents

#### 3. `equipment` Intent
**Description:** User looking for equipment information
**Example:** "navigation equipment"
**Response:** Equipment list, manuals, faults for that equipment

#### 4. `document` Intent
**Description:** User looking for specific document
**Example:** "generator manual"
**Response:** Documents matching title/type

#### 5. `work-order` Intent
**Description:** User looking for work orders
**Example:** "open work orders for starboard engine"
**Response:** Work order records

### Intent Detection Pipeline

**Location:** `apps/api/intent_parser.py`

```
User query: "generator cooling issue"
  ↓
[Intent Parser] Analyzes query
  ↓
[Entity Extraction] Identifies:
  - Equipment: "generator"
  - Symptom: "cooling"
  - Type: "issue" → fault intent
  ↓
[Intent Classification] → "fault" intent
  ↓
[Query Builder] Constructs SQL:
  SELECT * FROM faults
  WHERE equipment LIKE '%generator%'
    AND description LIKE '%cooling%'
    AND yacht_id = <user's yacht_id>
  ↓
[Results] Returns faults + related documents
```

### Intent-Aware Responses

**Situation Detection** (V2 Search)

Location: `apps/api/microaction_service.py:1571-1586`

The system detects **situations** based on search patterns:

- **Recurrent Fault:** Same fault happening multiple times
- **Pre-Charter Risk:** Critical issue before charter
- **Expert Escalation:** Issue requires manufacturer contact
- **Safety Critical:** Immediate attention required

**Example:**
```
Query: "generator overheating"
  ↓
[Situation Engine] Detects:
  - Equipment: Generator
  - Symptom: Overheating
  - History: 3 similar faults in past 30 days
  ↓
[Situation] → "Recurrent Fault"
  ↓
[Response] Includes:
  - Documents (cooling system manual)
  - Related faults (past overheating issues)
  - Recommended Action: "Create work order for generator cooling system inspection"
```

---

## 🔐 Authentication & Authorization Architecture

### JWT Token Structure

**Issued by:** Supabase Auth
**Algorithm:** HS256 (HMAC-SHA256)
**Secret:** `SUPABASE_JWT_SECRET` (environment variable)

**Payload:**
```json
{
  "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",  // user_id
  "email": "x@alex-short.com",
  "role": "authenticated",
  "iat": 1736438400,  // issued at
  "exp": 1736442000,  // expires at
  "iss": "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1"
}
```

**Note:** JWT does NOT contain `yacht_id`

### Yacht Context Injection

**Problem:** JWT doesn't include yacht_id, but backend needs it for authorization

**Solution:** Multi-step process

1. **Frontend Queries auth_users**
   ```typescript
   const { data } = await supabase
     .from('auth_users')
     .select('yacht_id')
     .eq('auth_user_id', session.user.id)
     .single();

   const yachtId = data.yacht_id;
   ```

2. **Frontend Generates Yacht Signature**
   ```typescript
   const yachtSignature = await getYachtSignature(yachtId);
   // SHA256(yachtId + YACHT_SALT)
   ```

3. **Frontend Sends Both**
   ```typescript
   fetch('/webhook/search', {
     headers: {
       'Authorization': `Bearer ${jwt}`,
       'X-Yacht-Signature': yachtSignature
     },
     body: JSON.stringify({
       query: '...',
       auth: {
         user_id: session.user.id,
         yacht_id: yachtId,
         yacht_signature: yachtSignature
       }
     })
   });
   ```

4. **Backend Validates**
   ```python
   # Validate JWT first
   payload = jwt.decode(token, SUPABASE_JWT_SECRET)
   user_id = payload['sub']

   # Extract yacht_id from request body
   yacht_id = request_body['auth']['yacht_id']

   # Verify yacht_signature matches
   expected_sig = hmac.sha256(yacht_id + YACHT_SALT)
   assert request_body['auth']['yacht_signature'] == expected_sig
   ```

**Why this approach?**
- JWT payload is immutable (signed by Supabase)
- Can't add custom claims to Supabase JWT
- yacht_id is dynamic (user can switch yachts)
- Signature prevents tampering

### Row Level Security (RLS) Deep Dive

**What is RLS?**
PostgreSQL feature that automatically filters rows based on user context

**How it works:**

1. **User queries table**
   ```sql
   SELECT * FROM faults WHERE equipment = 'generator';
   ```

2. **PostgreSQL intercepts query**

3. **Applies RLS policy**
   ```sql
   -- Original query transformed to:
   SELECT * FROM faults
   WHERE equipment = 'generator'
     AND yacht_id IN (
       SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
     );
   ```

4. **Returns filtered results**

**Key function: `auth.uid()`**
- Extracts user_id from JWT token in request
- Works automatically with Supabase client
- Returns `NULL` if no JWT (blocks access)

### RLS Policy Examples

**auth_users SELECT policy** ⚠️ Recently added

Location: Supabase database

```sql
CREATE POLICY "auth_users_select_own"
  ON auth_users
  FOR SELECT
  TO authenticated
  USING (
    auth_user_id = auth.uid()
  );
```

**Explanation:**
- Users can SELECT from auth_users
- Only rows where `auth_user_id = auth.uid()`
- Result: Users see only their own row

**search_document_chunks SELECT policy** ✅ Working

```sql
CREATE POLICY "search_document_chunks_yacht_isolation"
  ON search_document_chunks
  FOR SELECT
  TO authenticated
  USING (
    yacht_id IN (
      SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
    )
  );
```

**Explanation:**
- Users can SELECT from search_document_chunks
- Only rows where yacht_id matches user's yacht_id
- Sub-query looks up user's yacht in auth_users
- Result: Users see only documents for their yacht

### RLS Policy Testing

**In Supabase SQL Editor:**

```sql
-- Simulate authenticated user
SET LOCAL role authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"}';

-- This query now runs with RLS enforced
SELECT * FROM auth_users;

-- Should return only the row for user a35cad0b...
```

---

## 🗂️ Database Schema Details

### Multi-Tenancy Pattern

**Every tenant-specific table has:**
1. `yacht_id UUID` column
2. RLS policy enforcing yacht isolation
3. Index on `yacht_id` for performance

**Example:**
```sql
CREATE TABLE faults (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  severity TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT faults_yacht_id_fkey
    FOREIGN KEY (yacht_id) REFERENCES yachts(id)
);

CREATE INDEX faults_yacht_id_idx ON faults(yacht_id);

CREATE POLICY "faults_yacht_isolation"
  ON faults
  FOR ALL
  TO authenticated
  USING (
    yacht_id IN (
      SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
    )
  );
```

### auth_users Table Deep Dive

**Purpose:** Central authentication mapping

**Schema:**
```sql
CREATE TABLE auth_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id UUID NOT NULL UNIQUE,  -- From Supabase Auth
  email TEXT NOT NULL UNIQUE,
  yacht_id UUID NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT auth_users_yacht_id_fkey
    FOREIGN KEY (yacht_id) REFERENCES yachts(id)
);
```

**Critical Fields:**
- `auth_user_id`: Links to Supabase Auth user (JWT `sub`)
- `yacht_id`: User's assigned yacht (⚠️ recently fixed)
- Both are UUIDs, must match exactly

**Recent Issues:**
- Had wrong yacht_id (`00000000...` instead of `85fe1119...`)
- Caused RLS to block all yacht-specific queries
- Fixed by UPDATE statement

---

## 📊 Data Flow Examples

### Example 1: Search Flow (Complete)

```
[FRONTEND]
User types: "generator cooling"
  ↓
useCelesteSearch.ts debounces input (80ms)
  ↓
getFullAuthContext() called
  ↓
getYachtId() → SELECT yacht_id FROM auth_users WHERE auth_user_id = <user>
  ← Returns: "85fe1119-b04c-41ac-80f1-829d23322598"
  ↓
getYachtSignature(yachtId) → SHA256(yachtId + YACHT_SALT)
  ← Returns: "f3a7b2c9..."
  ↓
Assemble payload:
{
  query: "generator cooling",
  auth: {
    user_id: "a35cad0b...",
    yacht_id: "85fe1119...",
    yacht_signature: "f3a7b2c9..."
  }
}
  ↓
POST /webhook/search with JWT in Authorization header
  ↓
[BACKEND]
Middleware validates JWT
  ↓
Extract yacht_id from body: "85fe1119..."
  ↓
Verify yacht_signature matches
  ↓
Query Supabase:
SELECT * FROM search_document_chunks
WHERE embedding <-> query_embedding < 0.8
  AND yacht_id = '85fe1119...'  -- Added by RLS policy
LIMIT 10
  ↓
[SUPABASE]
RLS policy checks:
  - Is user authenticated? YES (JWT valid)
  - Does yacht_id match user's yacht? YES (85fe1119... = 85fe1119...)
  ↓
Returns 10 document chunks
  ↓
[BACKEND]
Formats response, adds actions
  ↓
[FRONTEND]
Displays search results
```

### Example 2: Document Access (Current Problem)

```
[FRONTEND]
User clicks document
  ↓
DocumentSituationView renders
  ↓
supabase.from('search_document_chunks')
  .select('*')
  .eq('chunk_id', '...')
  .single()
  ↓
[SUPABASE - RLS Check #1]
Policy: search_document_chunks_yacht_isolation
Using: yacht_id IN (
  SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
)
  ↓
Sub-query executes:
SELECT yacht_id FROM auth_users WHERE auth_user_id = 'a35cad0b...'
  ↓
⚠️ PROBLEM: Returns 404 (not 406!)
  ↓
[FRONTEND]
Error: "No yacht assignment found in database"
```

**Why 404 instead of 406?**
- 406: RLS policy blocks row (row exists but user can't access)
- 404: No row found (row doesn't exist OR policy prevents seeing it)

**Current hypothesis:**
- Table grant missing: `GRANT SELECT ON auth_users TO authenticated`
- OR policy not applied correctly
- OR JWT token not being passed correctly

---

## 🔧 Trustworthiness Assessment

### ✅ HIGH TRUST (Verified Working)

**Backend Middleware** (`apps/api/middleware/auth.py`)
- JWT validation working correctly
- Yacht context extraction working
- Recently tested, no changes needed

**RLS Policies (Except auth_users)**
- `search_document_chunks` RLS working
- `doc_metadata` RLS working
- `faults` RLS working
- User can't see other yachts' data

**P0 Actions System**
- `add_to_handover` action working
- Action registry working
- Dispatchers working

### ⚠️ MEDIUM TRUST (Recently Changed)

**Frontend Authentication** (`authHelpers.ts`, `auth.ts`)
- Just changed from `auth_users_yacht` to `auth_users`
- TypeScript compiles, but runtime behavior needs verification
- May have caching issues

**auth_users RLS Policy**
- Just added today
- SQL query works in Supabase, but frontend still getting 404
- Needs investigation

**DocumentSituationView.tsx**
- Just changed to use authenticated client
- Should work, but untested in production

### ❌ LOW TRUST (Needs Investigation)

**Vercel Environment Variables**
- Not verified if they match production Supabase
- Unclear if recent deployment picked up new code

**Frontend Supabase Client**
- Possibly caching old credentials
- May need client reset or cache clear

**RLS Policy Application Timing**
- Unclear if policies apply immediately
- May need database connection pool reset

---

**Next:** [03_USER_JOURNEY.md](./03_USER_JOURNEY.md) - Complete user journey flow
