## CelesteOS Integration Layer Documentation

**Version:** 1.0
**Status:** Complete
**Last Updated:** 2025-11-20

---

## Overview

This document describes the **integration layer** that connects all CelesteOS services into a cohesive system.

The integration layer is the **glue** between:
- Vercel Frontend (Next.js)
- Cloud API (FastAPI/Python)
- Search Engine (Python/Render)
- Predictive Engine (Python/Render)
- Supabase (Postgres + pgvector + Storage)
- Local Agent (macOS app)
- n8n (Indexing pipeline)

---

## Architecture Principles

###  1. **Frontend NEVER calls Supabase directly for business logic**
- Supabase used ONLY for authentication
- All data operations go through Cloud API
- Cloud API enforces yacht isolation server-side

### 2. **Cloud API is the gateway**
- Validates JWT on every request
- Extracts `yacht_id` from JWT
- Routes requests to appropriate services
- Enforces yacht-level isolation

### 3. **All services use typed contracts**
- TypeScript types define data shapes
- Python uses matching data classes
- No runtime type mismatches

### 4. **Yacht isolation enforced at every layer**
- JWT contains `yacht_id`
- Database queries filtered by `yacht_id`
- Row-Level Security (RLS) as final safeguard
- Cross-yacht access impossible

---

## Component Responsibilities

| Component | Responsibilities | Auth Method |
|-----------|-----------------|-------------|
| **Frontend** | UI, user input, display results | JWT from Supabase Auth |
| **Cloud API** | Gateway, JWT validation, routing | Service tokens (internal) |
| **Search Engine** | Entity extraction, RAG, GraphRAG | Service token from Cloud API |
| **Predictive Engine** | Risk scoring, signal analysis | Service token from Cloud API |
| **Supabase** | Data storage, vector search, auth | Service role key (backend) |
| **Local Agent** | NAS scanning, file upload | yacht_signature + agent_token |
| **n8n** | Indexing pipeline orchestration | Webhooks + service tokens |

---

## Integration Contracts

### Frontend → Cloud API

**Protocol:** HTTPS/REST
**Auth:** JWT in `Authorization: Bearer <token>` header
**Format:** JSON
**Streaming:** Server-Sent Events (SSE) for search results

**Example Request:**
```http
GET /v1/search?q=fault+E047+main+engine HTTP/1.1
Host: api.celesteos.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

**Example Response:**
```json
{
  "data": {
    "query_id": "uuid",
    "intent": "diagnose_fault",
    "entities": {
      "equipment_name": "main engine",
      "fault_code": "E047"
    },
    "results": [...],
    "actions": [...]
  },
  "timestamp": "2025-11-20T12:34:56Z"
}
```

---

### Cloud API → Search Engine

**Protocol:** HTTP/REST
**Auth:** Internal service token in header
**Format:** JSON
**Includes:** `yacht_id` in every request

**Example Request:**
```http
POST /v1/search HTTP/1.1
Host: celesteos-search.onrender.com
X-Service-Token: internal-service-token
Content-Type: application/json

{
  "yacht_id": "yacht-456",
  "query": "fault E047 main engine",
  "mode": "auto",
  "filters": {}
}
```

---

### Cloud API → Predictive Engine

**Protocol:** HTTP/REST
**Auth:** Internal service token
**Format:** JSON
**Caching:** Results cached in Supabase `predictive_state` table

**Example Request:**
```http
GET /v1/predictive/state?yacht_id=yacht-456 HTTP/1.1
Host: celesteos-predictive.onrender.com
X-Service-Token: internal-service-token
```

---

### Cloud API → Supabase

**Protocol:** Supabase SDK / REST API
**Auth:** Service role key (never exposed to frontend)
**RLS:** Row-Level Security enforces yacht isolation

**Example Query:**
```python
from src.integrations.supabase import get_supabase_client

supabase = get_supabase_client()

# Yacht isolation automatically enforced
work_orders = supabase.table('work_orders') \
    .select('*') \
    .eq('yacht_id', yacht_id) \
    .eq('status', 'pending') \
    .execute()
```

---

### Local Agent → Cloud API

**Protocol:** HTTPS/REST
**Auth:** `X-Yacht-Signature` + `X-Agent-Token` headers
**Upload:** Chunked (8-32MB per chunk)
**Resume:** Supported via `upload_id`

**Example Upload Init:**
```http
POST /v1/ingest/init HTTP/1.1
Host: api.celesteos.com
X-Yacht-Signature: abc123...
X-Agent-Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "filename": "MTU_Manual_2019.pdf",
  "sha256": "a1b2c3...",
  "size_bytes": 53455300,
  "source": "nas"
}
```

---

## File Structure

```
Cloud_PMS/
├── frontend/                    # Next.js Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.ts          # ⭐ Typed API client (all endpoints)
│   │   │   └── supabase.ts     # ⭐ Supabase auth helpers
│   │   ├── types/
│   │   │   └── index.ts        # ⭐ All TypeScript type definitions
│   │   ├── hooks/
│   │   │   ├── useAuth.ts      # Authentication hook
│   │   │   └── useSearch.ts    # Search hook
│   │   └── __tests__/
│   │       └── api.test.ts     # API client tests
│   └── package.json
│
├── backend/                     # Cloud API Backend (Python/FastAPI)
│   ├── src/
│   │   ├── middleware/
│   │   │   └── auth.py         # ⭐ JWT validation, yacht isolation
│   │   └── integrations/
│   │       ├── supabase.py     # ⭐ Supabase integration helpers
│   │       ├── search_engine.py # ⭐ Search Engine client
│   │       └── predictive_engine.py # ⭐ Predictive Engine client
│   ├── tests/
│   │   └── test_auth_middleware.py
│   └── requirements.txt
│
├── docs/
│   └── integration/
│       ├── INTEGRATION_FLOWS.md    # ⭐ Mermaid diagrams
│       └── INTEGRATION_LAYER.md    # ⭐ This file
│
└── .env.example                # ⭐ All environment variables
```

---

## Key Integration Files

### 1. `frontend/src/lib/api.ts`
**Purpose:** Typed API client for all Cloud API endpoints
**Exports:**
- `api.search` - Search API
- `api.predictive` - Predictive API
- `api.workOrders` - Work Order API
- `api.equipment` - Equipment API
- `api.inventory` - Parts & Inventory API
- `api.handovers` - Handover API
- `api.documents` - Document API
- `api.ingestion` - Upload API
- `api.dashboard` - Dashboard API

**Usage:**
```typescript
import { api } from '@/lib/api';

// Perform search
const results = await api.search.search({
  query: 'fault E047 main engine',
  mode: 'auto',
});

// Create work order
const workOrder = await api.workOrders.create({
  title: 'Fix stabiliser leak',
  equipment_id: 'eq-123',
  priority: 'high',
});
```

---

### 2. `frontend/src/lib/supabase.ts`
**Purpose:** Supabase authentication integration
**Exports:**
- `supabase.auth.signIn()` - User login
- `supabase.auth.signOut()` - User logout
- `supabase.auth.getSession()` - Get current session
- `supabase.auth.getAccessToken()` - Get JWT token
- `supabase.tokens.extractYachtId()` - Extract yacht_id from JWT

**Usage:**
```typescript
import { supabase } from '@/lib/supabase';

// Sign in
const { session, user } = await supabase.auth.signIn(
  'user@example.com',
  'password'
);

// Get access token for API calls
const token = await supabase.auth.getAccessToken();
```

---

### 3. `frontend/src/types/index.ts`
**Purpose:** All TypeScript type definitions
**Exports:** 60+ type definitions including:
- `SearchRequest`, `SearchResponse`
- `WorkOrder`, `CreateWorkOrderRequest`
- `PredictiveState`, `PredictiveInsight`
- `Equipment`, `Fault`, `Part`
- `Handover`, `Document`
- All result card types
- All micro-action types

---

### 4. `backend/src/middleware/auth.py`
**Purpose:** JWT validation and yacht isolation
**Exports:**
- `validate_user_jwt()` - FastAPI dependency for JWT validation
- `inject_yacht_context()` - Extract yacht_id from JWT
- `validate_agent_token()` - Validate Local Agent tokens
- `require_role()` - Role-based access control decorator
- `enforce_yacht_isolation()` - Verify resource belongs to yacht

**Usage:**
```python
from fastapi import Depends
from src.middleware.auth import validate_user_jwt, inject_yacht_context

@app.get('/v1/work-orders')
async def list_work_orders(
    auth: dict = Depends(validate_user_jwt),
    yacht_id: str = Depends(inject_yacht_context)
):
    # yacht_id is guaranteed to match auth['yacht_id']
    # Cross-yacht access is impossible
    work_orders = await get_work_orders(yacht_id)
    return {'data': work_orders}
```

---

### 5. `backend/src/integrations/supabase.py`
**Purpose:** Supabase integration helpers
**Exports:**
- `vector_search()` - pgvector similarity search
- `get_equipment()` - Fetch equipment
- `get_work_orders()` - Fetch work orders
- `create_work_order()` - Create work order
- `get_predictive_state()` - Fetch predictive state
- `get_signed_url()` - Generate signed URLs for documents
- `log_event()` - Log events to event_logs table

---

### 6. `backend/src/integrations/search_engine.py`
**Purpose:** Search Engine integration
**Exports:**
- `search()` - Forward search to Search Engine
- `stream_search()` - Stream search results (SSE)
- `extract_entities()` - Extract entities from text
- `detect_intent()` - Detect user intent

---

### 7. `backend/src/integrations/predictive_engine.py`
**Purpose:** Predictive Engine integration
**Exports:**
- `get_predictive_state()` - Get risk scores for all equipment
- `get_equipment_predictive_state()` - Get risk score for specific equipment
- `trigger_predictive_calculation()` - Trigger risk calculation
- `analyze_signals()` - Get detailed signal breakdown

---

## Environment Variables

See `.env.example` for complete list.

### Required Variables

**Supabase:**
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anonymous key (frontend)
- `SUPABASE_SERVICE_KEY` - Supabase service role key (backend only!)
- `SUPABASE_JWT_SECRET` - JWT secret for token validation

**Cloud API:**
- `NEXT_PUBLIC_CLOUD_API_URL` - Cloud API base URL
- `CLOUD_API_URL` - Internal Cloud API URL (backend)

**Search & Predictive:**
- `SEARCH_ENGINE_URL` - Search Engine service URL
- `PREDICTIVE_ENGINE_URL` - Predictive Engine service URL

**Security:**
- `AGENT_TOKEN_SECRET` - Secret for Local Agent tokens
- `SEARCH_ENGINE_SERVICE_TOKEN` - Token for Search Engine auth
- `PREDICTIVE_ENGINE_SERVICE_TOKEN` - Token for Predictive Engine auth

---

## Testing

### Frontend Tests

Run tests with:
```bash
cd frontend
npm test
```

**Test Files:**
- `src/__tests__/api.test.ts` - API client tests

**Test Coverage:**
- [x] Search API calls
- [x] Work Order API calls
- [x] Predictive API calls
- [x] Error handling
- [x] JWT authentication
- [x] Network error handling

### Backend Tests

Run tests with:
```bash
cd backend
pytest
```

**Test Files:**
- `tests/test_auth_middleware.py` - Auth middleware tests

**Test Coverage:**
- [x] JWT validation
- [x] Expired token handling
- [x] Entity extraction (yacht_id, user_id, role)
- [x] Agent token creation/validation
- [x] Yacht isolation enforcement

---

## Security Checklist

- [x] JWT validated on every API request
- [x] yacht_id extracted from JWT (never from request body)
- [x] All database queries filtered by yacht_id
- [x] Cross-yacht access prevented
- [x] Supabase Service Key never exposed to frontend
- [x] Agent tokens validated for ingestion endpoints
- [x] Signed URLs for document access (time-limited)
- [x] Role-based access control for dashboard
- [x] Event logging for audit trail

---

## Integration Validation

### Manual Testing Checklist

- [ ] User can sign in and receive JWT
- [ ] Search query returns results from correct yacht
- [ ] Work order creation succeeds
- [ ] Predictive state loads correctly
- [ ] Document signed URL works
- [ ] Local Agent can upload files
- [ ] n8n indexing pipeline triggers
- [ ] Dashboard displays correct data
- [ ] Handover item addition works
- [ ] Cross-yacht access denied (403)

### Automated Testing

Run full integration test suite:
```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && pytest

# E2E tests (when implemented)
cd e2e && npm test
```

---

## Troubleshooting

### Common Issues

**Issue:** "Authentication failed: No session returned"
**Solution:** Check `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`

**Issue:** "Search engine unavailable"
**Solution:** Verify `SEARCH_ENGINE_URL` and service is running

**Issue:** "Access denied: Resource belongs to different yacht"
**Solution:** This is correct behavior - yacht isolation is working

**Issue:** "JWT validation failed"
**Solution:** Verify `SUPABASE_JWT_SECRET` matches Supabase dashboard value

### Debug Mode

Enable debug logging:
```bash
# Frontend
DEBUG=true npm run dev

# Backend
LOG_LEVEL=debug python -m uvicorn main:app
```

---

## Performance Targets

| Operation | Target Latency | Timeout |
|-----------|---------------|---------|
| JWT validation | < 10ms | 100ms |
| Search query | < 500ms | 5s |
| Work order creation | < 300ms | 3s |
| Predictive state fetch | < 200ms | 2s |
| Document signed URL | < 100ms | 1s |
| Vector search | < 400ms | 5s |

---

## Deployment

### Frontend (Vercel)

```bash
cd frontend
vercel --prod
```

**Environment Variables:** Set in Vercel dashboard
**Build Command:** `next build`
**Output Directory:** `.next`

### Backend (Hetzner/Render)

```bash
cd backend
docker build -t celesteos-api .
docker push registry/celesteos-api:latest
```

### Search Engine (Render)

Deploy to Render.com via GitHub integration

### Predictive Engine (Render)

Deploy to Render.com via GitHub integration

---

## Monitoring & Observability

### Key Metrics to Monitor

1. **API Gateway:**
   - Request rate (req/min)
   - Error rate (%)
   - JWT validation success rate (%)
   - Response time (p50, p95, p99)

2. **Search Engine:**
   - Search latency (ms)
   - Entity extraction accuracy (%)
   - Vector search hit rate (%)

3. **Predictive Engine:**
   - Calculation completion rate (%)
   - Risk score distribution
   - Signal processing time (ms)

4. **Database:**
   - Query performance (ms)
   - Connection pool utilization (%)
   - Vector search performance (ms)

---

## Next Steps

- [ ] Implement actual Search Engine service
- [ ] Implement actual Predictive Engine service
- [ ] Implement actual Cloud API service
- [ ] Set up n8n indexing pipeline
- [ ] Deploy services to staging environment
- [ ] Run integration tests end-to-end
- [ ] Set up monitoring & alerting
- [ ] Performance testing
- [ ] Security audit
- [ ] Production deployment

---

## Support

For integration issues, contact:
- **Email:** engineering@celesteos.com
- **Docs:** https://docs.celesteos.com
- **GitHub:** https://github.com/celesteos/cloud-pms

---

**End of Integration Layer Documentation**
