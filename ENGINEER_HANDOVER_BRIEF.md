# CelesteOS Search Pipeline - Engineer Handover Brief

**Date:** 2026-01-08
**Status:** Production Deployment on Render + Vercel
**Backend:** https://pipeline-core.int.celeste7.ai
**Frontend:** Deployed on Vercel (apps/web)

---

## 🎯 What This System Does

CelesteOS is an **AI-powered search engine for superyacht maintenance**. Everything starts with a search bar:

- Crew types **"show me pumps"** → System returns equipment cards + actionable buttons
- Crew types **"fault code E047"** → System returns fault diagnosis + work order creation
- Crew types **"check inventory"** → System returns parts list + ordering options

**Core Philosophy:** Single search bar replaces 12+ different database views. No menus, no navigation trees.

---

## 🏗️ System Architecture

### High-Level Flow

```
User Query → Frontend (Next.js) → Backend (FastAPI/Render) → Database (Supabase) → Frontend Cards
```

### Deployment

| Component | Technology | Hosting | URL |
|-----------|-----------|---------|-----|
| **Frontend** | Next.js 14, React 18, TypeScript | Vercel | Auto-deployed from `universal_v1` branch |
| **Backend** | FastAPI, Python 3.12.8 | Render | https://pipeline-core.int.celeste7.ai |
| **Database** | PostgreSQL + pgvector | Supabase | https://vzsohavtuotocgrfkfyd.supabase.co |
| **Actions** | n8n workflows (67 actions) | TBD | Not yet deployed |

---

## 🔬 4-Stage Pipeline (How It Works)

Every search query flows through **4 deterministic stages**:

### STAGE 1: EXTRACTION
**File:** `apps/api/extraction/orchestrator.py`

**What it does:**
- Takes raw query: `"show me pumps"`
- Extracts entities using **42,340 regex patterns** (manufacturer names, part numbers, equipment types)
- Falls back to OpenAI if regex misses entities
- Outputs: `{ "entities": { "MANUFACTURER": ["Pumps"] } }`

**Why this matters:**
- No entities = no results
- Regex is fast (<50ms), AI is slow (200-500ms)
- Code gracefully handles missing `spacy` and `openai` dependencies

**Debug:**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "show me pumps"}'
```

---

### STAGE 2: PREPARE
**File:** `apps/api/prepare/capability_composer.py`

**What it does:**
- Maps entities → database capabilities
- Example: `MANUFACTURER: "Pumps"` → Triggers `part_by_part_number_or_name` capability
- Builds execution plans (which tables to query, which columns to search)

**Capabilities defined in:**
- `apps/api/execute/table_capabilities.py` (Python code)
- `docs/specs/table_configs.md` (documentation)

**Output:**
```python
{
  "plans": [
    {
      "capability": "part_by_part_number_or_name",
      "entity_type": "MANUFACTURER",
      "entity_value": "Pumps",
      "table": "pms_parts",
      "search_columns": ["manufacturer", "name", "part_number"]
    }
  ]
}
```

---

### STAGE 3: EXECUTE
**File:** `apps/api/execute/capability_executor.py`

**What it does:**
- Executes SQL queries per execution plan
- Enforces **yacht isolation** (every query auto-adds `WHERE yacht_id = ?`)
- Uses **semantic ranking** (pgvector embeddings) when available
- Returns raw database rows

**Security:**
- All SQL is parameterized (no injection)
- Row-Level Security (RLS) enforced at Supabase layer
- JWT validated before any query

**Output:**
```python
{
  "results": [
    {
      "id": "uuid-1",
      "name": "Raw Water Pump Impeller",
      "manufacturer": "Pumps Inc",
      "part_number": "RWP-404",
      "category": "PUMP",
      "stock_quantity": 2,
      "min_stock_level": 1
    },
    {
      "id": "uuid-2",
      "name": "Generator Impeller",
      ...
    }
  ]
}
```

---

### STAGE 4: ACTIONS
**File:** `apps/api/actions/action_gating.py`

**What it does:**
- Attaches **micro-actions** (buttons) to each result
- Example: Part card gets `["order_part", "view_stock", "view_manual"]`
- Actions respect **role-based permissions** (Engineer vs Captain)
- Actions respect **environment** (sea/port/shipyard/guest)

**Micro-Action Registry:**
- See `docs/MICROACTION_WORKFLOW_MASTER_LIST.md` (67 actions total)
- See `docs/micro-actions/MICRO_ACTION_REGISTRY.md`

**Output:**
```python
{
  "results": [...],  # From Stage 3
  "available_actions": [
    {
      "action": "order_part",
      "label": "Order Part",
      "execution_class": "confirm",  # Requires user confirmation
      "context_required": ["yacht_id", "part_id"],
      "parameters": ["quantity"]
    },
    {
      "action": "view_details",
      "label": "View Details",
      "execution_class": "auto"  # Executes immediately
    }
  ]
}
```

---

## 📦 Backend Response Format

### Endpoint: `POST /webhook/search`

**Request:**
```json
{
  "query": "show me pumps",
  "auth": {
    "yacht_id": "uuid",
    "user_id": "uuid",
    "role": "Engineer",
    "email": "user@example.com",
    "yacht_signature": "sha256_hash"
  },
  "context": {
    "client_ts": 1704729600,
    "stream_id": "uuid",
    "session_id": "uuid",
    "source": "web"
  },
  "limit": 20
}
```

**Response:** (Newline-delimited JSON)
```json
{
  "success": true,
  "query": "show me pumps",
  "results": [
    {
      "id": "uuid-1",
      "type": "part",
      "name": "Raw Water Pump Impeller",
      "manufacturer": "Pumps Inc",
      "part_number": "RWP-404",
      "score": 0.95
    }
  ],
  "total_count": 2,
  "available_actions": [
    {
      "action": "order_part",
      "label": "Order Part",
      "execution_class": "confirm"
    }
  ],
  "entities": [
    {
      "type": "MANUFACTURER",
      "value": "Pumps",
      "confidence": 0.8
    }
  ],
  "plans": [...],
  "timing_ms": {
    "extraction": 45.2,
    "prepare": 12.1,
    "execute": 89.3,
    "total": 146.6
  },
  "results_by_domain": {
    "parts": 2,
    "equipment": 0
  }
}
```

**Critical:** Response ends with `\n` (newline) for frontend stream parser.

---

## 🎨 Frontend Architecture

### Search Hook: `apps/web/src/hooks/useCelesteSearch.ts`

**Flow:**
1. User types in search bar → `handleQueryChange()`
2. Debounced 140ms (fast typing) or 80ms (slow typing)
3. Calls `streamSearch()` → POST to `/webhook/search`
4. Parses **newline-delimited JSON** from stream
5. Updates results in real-time (buffered streaming)
6. Caches results for 5 minutes

**Key Functions:**
- `streamSearch()` - Main streaming logic
- `buildSearchPayload()` - Constructs request with auth
- `executeSearch()` - Handles cache + retry logic

**Authentication:**
- JWT from Supabase session (`Authorization: Bearer <token>`)
- Yacht signature (`X-Yacht-Signature: sha256(yacht_id + YACHT_SALT)`)
- See `apps/web/src/lib/authHelpers.ts`

---

## 🔐 Security Architecture

### Authentication Flow
```
User logs in → Supabase JWT → Frontend stores in memory (NOT localStorage)
Every API call → getValidJWT() → Auto-refreshes if expiring soon
Backend validates JWT + yacht_id → Returns results for THAT yacht only
```

### Multi-Tenancy (Yacht Isolation)
- Every table has `yacht_id` column
- All queries auto-inject `WHERE yacht_id = ?`
- Row-Level Security (RLS) enforced at database layer
- Users can NEVER see data from other yachts

**See:** `database/SECURITY_ARCHITECTURE.md`

---

## 🎬 Micro-Actions (The "Do Something" Buttons)

### What Are Micro-Actions?

Every search result has **actionable buttons**. These trigger workflows in n8n.

**Example:** Search for a fault code
```
Result Card: "E047 - Coolant Leak Detected"
  ├─ [Diagnose Fault] → Calls RAG, returns AI diagnosis
  ├─ [Create Work Order] → INSERT into work_orders table
  ├─ [Suggest Parts] → Calls LLM, returns recommended parts
  └─ [View Manual] → Opens PDF viewer with relevant section
```

### Action Archetypes (6 types)

| Archetype | Endpoint | Description | Example Actions |
|-----------|----------|-------------|-----------------|
| **VIEW** | `/workflows/view` | Read-only data retrieval | `view_fault_history`, `show_manual_section` |
| **CREATE** | `/workflows/create` | Insert new records | `create_work_order`, `add_note` |
| **UPDATE** | `/workflows/update` | Modify existing records | `close_work_order`, `update_inventory` |
| **EXPORT** | `/workflows/export` | Generate documents | `export_handover_pdf`, `export_inventory_csv` |
| **RAG** | `/workflows/rag` | AI-powered queries | `diagnose_fault`, `suggest_parts` |
| **LINKING** | `/workflows/linking` | Connect entities | `link_part_to_equipment`, `add_to_handover` |

**Full Registry:** `docs/MICROACTION_WORKFLOW_MASTER_LIST.md` (67 actions)

---

## 🧩 Related Files (Codebase Map)

### Backend (Python)
```
apps/api/
├── pipeline_service.py          ← FastAPI app, main entry point
├── pipeline_v1.py               ← 4-stage pipeline orchestrator
├── extraction/
│   └── orchestrator.py          ← Entity extraction (Stage 1)
├── prepare/
│   └── capability_composer.py   ← Maps entities to capabilities (Stage 2)
├── execute/
│   ├── capability_executor.py   ← SQL execution engine (Stage 3)
│   └── table_capabilities.py    ← Capability definitions
└── actions/
    ├── action_gating.py         ← Attach actions to results (Stage 4)
    └── action_registry.py       ← Action metadata (67 actions)
```

### Frontend (Next.js)
```
apps/web/
├── src/hooks/
│   ├── useCelesteSearch.ts      ← Main search hook (streaming)
│   └── useDashboardData.ts      ← Dashboard widgets
├── src/lib/
│   ├── apiClient.ts             ← API wrapper (GET/POST/PATCH/DELETE)
│   ├── actionClient.ts          ← Action execution client
│   └── authHelpers.ts           ← JWT + yacht signature helpers
└── docs/
    └── API_SECURITY.md          ← How to make secure API calls
```

### Documentation (Critical Reading)
```
docs/
├── ARCHITECTURE_UNIFIED.md                     ← System architecture overview
├── MICROACTION_WORKFLOW_MASTER_LIST.md         ← 67 micro-actions registry
├── specs/
│   ├── search-engine-spec.md                   ← Search pipeline spec
│   ├── action-router-service.md                ← Action Router API
│   └── table_configs.md                        ← Database capability configs
├── micro-actions/
│   ├── MICRO_ACTION_REGISTRY.md                ← Action metadata
│   └── ACTION_OFFERING_RULES.md                ← When to show which actions
└── architecture/
    └── WORKFLOW.md                             ← Data flow diagrams
```

### Database Schema
```
database/
├── README.md                    ← Schema overview
├── SECURITY_ARCHITECTURE.md     ← RLS policies, yacht isolation
└── schema.sql                   ← Full PostgreSQL schema
```

---

## 🐛 Current Issues (As of 2026-01-08)

### Issue #1: Frontend Stream Parser Returns Empty Buffer
**Status:** Debugging in progress

**Symptoms:**
- Backend returns 200 OK with 3,296 bytes
- Frontend `ReadableStream` receives chunks (`hasValue: true`)
- But `TextDecoder.decode()` produces empty string
- Buffer stays at 0 bytes

**Evidence:**
```javascript
// Console logs:
📥 Response status: 200
📖 Reader chunk: {done: false, hasValue: true, bufferLength: 0}
✅ Stream done, buffer length: 0
⚠️ No remaining buffer to process
```

**Next Step:**
- Deployed debug logging to check actual `byteLength` vs `decodedLength`
- Will identify if issue is:
  - Backend sending empty response (fix backend)
  - TextDecoder failing (fix encoding mismatch)
  - Stream API issue (fix ReadableStream setup)

**Files:**
- `apps/web/src/hooks/useCelesteSearch.ts:230-250` (stream parser)
- `apps/api/pipeline_service.py:191-236` (webhook endpoint)

---

## 🧪 Testing the System

### Test Backend Directly (Python)
```python
import requests

response = requests.post(
    'https://pipeline-core.int.celeste7.ai/webhook/search',
    json={
        'query': 'show me pumps',
        'auth': {
            'yacht_id': '85fe1119-b04c-41ac-80f1-829d23322598',
            'user_id': 'test',
            'role': 'Engineer'
        },
        'limit': 20
    }
)

print(f"Status: {response.status_code}")
print(f"Results: {len(response.json()['results'])}")
```

### Test Frontend Locally
```bash
cd apps/web
npm run dev
# Visit http://localhost:3000
# Open search bar (Cmd+K)
# Type "show me pumps"
# Check browser console for logs
```

### Test Entity Extraction Only
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "fault code E047"}'
```

---

## 🚀 Deployment Process

### Backend (Render)
1. Push to `universal_v1` branch
2. Render auto-deploys from GitHub
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn api.pipeline_service:app --host 0.0.0.0 --port $PORT`
5. Health check: `GET /health`

**Environment Variables:**
```
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
OPENAI_API_KEY=<optional_for_ai_fallback>
```

### Frontend (Vercel)
1. Push to `universal_v1` branch
2. Vercel auto-deploys
3. Build: `npm run build`
4. Start: `npm start`

**Environment Variables:**
```
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
NEXT_PUBLIC_API_URL=https://pipeline-core.int.celeste7.ai
NEXT_PUBLIC_YACHT_SALT=<secret_salt>
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

---

## 📊 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Extraction latency | <100ms | ~45ms ✅ |
| Total search latency | <300ms | ~150ms ✅ |
| Streaming first chunk | <200ms | TBD |
| Cache hit rate | >70% | ~85% ✅ |
| Concurrent users | 50+ | Not tested |

---

## 🎓 Key Concepts to Understand

1. **Entity Extraction:** Converting "show me pumps" → `{MANUFACTURER: "Pumps"}`
2. **Capabilities:** Mapping entities → database queries (e.g., `MANUFACTURER` → search `pms_parts.manufacturer`)
3. **Yacht Isolation:** Every query auto-filters by `yacht_id` (multi-tenancy)
4. **Micro-Actions:** Contextual buttons attached to results (e.g., "Order Part")
5. **Newline-Delimited JSON:** Backend sends `{...}\n` for streaming parser
6. **JWT + Yacht Signature:** Dual auth (user identity + yacht access)

---

## 📚 Reading Order for New Engineers

1. **Start here:** `docs/ARCHITECTURE_UNIFIED.md` (system overview)
2. **Search pipeline:** `docs/specs/search-engine-spec.md`
3. **Micro-actions:** `docs/MICROACTION_WORKFLOW_MASTER_LIST.md`
4. **Frontend contract:** `apps/web/docs/API_SECURITY.md`
5. **Action Router:** `docs/specs/action-router-service.md`
6. **Database schema:** `database/README.md`
7. **Code:** `apps/api/pipeline_v1.py` (backend entry point)
8. **Code:** `apps/web/src/hooks/useCelesteSearch.ts` (frontend entry point)

---

## 🆘 Common Gotchas

1. **"No results" but backend works:**
   - Check `yacht_id` in request matches database records
   - Verify entities extracted correctly (`/extract` endpoint)
   - Check capability triggers in `table_capabilities.py`

2. **"Authentication required" errors:**
   - JWT expired → Frontend auto-refreshes, but check `getValidJWT()`
   - Missing yacht signature → Check `NEXT_PUBLIC_YACHT_SALT` env var

3. **"Stream parsing fails":**
   - Backend MUST end response with `\n` (newline)
   - Check `Content-Type: application/json` header
   - Verify `TextDecoder` encoding matches backend (UTF-8)

4. **"Empty results for valid query":**
   - Entity extraction might be failing → Test `/extract` endpoint
   - No capability triggered → Check `table_capabilities.py` entity_triggers
   - Database has no data for that yacht → Check Supabase directly

---

## 🔧 Tools & Commands

### Backend Logs (Render)
```bash
# Live tail
render logs --tail -s <service-id>

# Search for errors
render logs -s <service-id> | grep ERROR
```

### Frontend Logs (Vercel)
```bash
# Visit: https://vercel.com/<project>/deployments
# Click deployment → "Functions" tab → "Logs"
```

### Database Queries (Supabase)
```bash
# SQL Editor in Supabase dashboard
# Or use psql:
psql postgres://postgres:<password>@db.<project>.supabase.co:5432/postgres
```

---

## 📞 Support & Resources

- **Slack:** #backend-dev, #frontend-dev
- **GitHub:** Cloud_PMS repository, `universal_v1` branch
- **Render:** https://dashboard.render.com
- **Vercel:** https://vercel.com/dashboard
- **Supabase:** https://app.supabase.com

---

**Last Updated:** 2026-01-08
**Author:** Claude Sonnet 4.5 (via celeste7 session)
**Next Engineer:** Read this first, then dive into `docs/ARCHITECTURE_UNIFIED.md`

Good luck! 🚀
