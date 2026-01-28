# SYSTEM MAP - CelesteOS Infrastructure Truth Table

**Generated:** 2026-01-13
**Purpose:** Authoritative mapping of services, databases, and routing

---

## Domain Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION DOMAINS                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐      ┌───────────────────────────────────────┐   │
│  │   VERCEL         │      │              RENDER                   │   │
│  │                  │      │                                       │   │
│  │ app.celeste7.ai  │──────│  pipeline-core.int.celeste7.ai       │   │
│  │ (Next.js 14)     │ API  │  (FastAPI + uvicorn)                  │   │
│  │                  │ calls│                                       │   │
│  │ auth.celeste7.ai │      │  Entrypoint:                          │   │
│  │ (legacy redirect)│      │  api.pipeline_service:app             │   │
│  └──────────────────┘      └───────────────────────────────────────┘   │
│           │                              │                              │
│           │ auth                         │ data queries                 │
│           ▼                              ▼                              │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                        SUPABASE                                 │    │
│  │                                                                 │    │
│  │  ┌─────────────────────┐    ┌─────────────────────┐            │    │
│  │  │     MASTER DB       │    │     TENANT DB       │            │    │
│  │  │                     │    │   (per yacht)       │            │    │
│  │  │ qvzmkaamzaqxpzbewjxe│    │ vzsohavtuotocgrfkfyd│            │    │
│  │  │                     │    │ (TEST_YACHT_001)    │            │    │
│  │  │ Tables:             │    │                     │            │    │
│  │  │ - auth.users        │    │ Tables:             │            │    │
│  │  │ - user_accounts     │    │ - pms_work_orders   │            │    │
│  │  │ - fleet_registry    │    │ - pms_faults        │            │    │
│  │  │ - security_events   │    │ - pms_equipment     │            │    │
│  │  │                     │    │ - doc_metadata      │            │    │
│  │  │ RPCs:               │    │ - document_chunks   │            │    │
│  │  │ - get_my_bootstrap  │    │ - parts_inventory   │            │    │
│  │  │ - log_security_event│    │ - audit_log         │            │    │
│  │  └─────────────────────┘    └─────────────────────┘            │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Service Ownership

| Domain | Platform | Branch | Auto-deploy | Purpose |
|--------|----------|--------|-------------|---------|
| `app.celeste7.ai` | Vercel | `main` | Yes | Production frontend |
| `auth.celeste7.ai` | Vercel | `main` | Yes | Legacy (redirect to app) |
| `pipeline-core.int.celeste7.ai` | Render | `main` | Yes | API backend |

---

## Database Ownership

| Database | Project ID | Type | Owner | Purpose |
|----------|------------|------|-------|---------|
| MASTER | `qvzmkaamzaqxpzbewjxe` | Control Plane | All yachts | Auth, tenant registry |
| TEST_YACHT_001 | `vzsohavtuotocgrfkfyd` | Data Plane | Single yacht | PMS data |

### MASTER DB Responsibilities

- **Auth:** Supabase Auth for all users (single sign-on)
- **User Mapping:** `user_accounts` → maps user_id to yacht_id
- **Fleet Registry:** `fleet_registry` → maps yacht_id to tenant credentials
- **Security Logging:** `security_events` → audit trail

### TENANT DB Responsibilities

- **PMS Data:** Work orders, faults, equipment, inventory
- **Documents:** doc_metadata, document_chunks
- **Audit:** audit_log for mutations

---

## Request Flow

### 1. Login Flow

```
Browser → app.celeste7.ai/login
       → Supabase Auth (MASTER: qvzm...)
       → Returns JWT with user_id (sub claim)
       → Frontend stores in Supabase client
```

### 2. Bootstrap Flow

```
Frontend → get_my_bootstrap() RPC (MASTER DB)
        → Returns: { yacht_id, yacht_name, role, tenant_key_alias }
        → Frontend stores in AuthContext
```

### 3. API Request Flow

```
Frontend → POST /search (pipeline-core.int.celeste7.ai)
        → Header: Authorization: Bearer <jwt>
        → Backend: Verify JWT using MASTER_SUPABASE_JWT_SECRET
        → Backend: Extract user_id from JWT (sub claim)
        → Backend: lookup_tenant_for_user(user_id) → MASTER DB
        → Backend: get_tenant_client(tenant_key_alias) → Tenant DB
        → Backend: Execute query against Tenant DB
        → Return results
```

---

## Environment Variable Map

### Vercel (Frontend)

| Variable | Purpose | Public |
|----------|---------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | Master Supabase URL | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Auth anon key | Yes |
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |

### Render (Backend)

| Variable | Purpose | Source |
|----------|---------|--------|
| `MASTER_SUPABASE_URL` | Master DB URL | Hardcoded fallback |
| `MASTER_SUPABASE_JWT_SECRET` | JWT signing secret | Supabase Dashboard |
| `MASTER_SUPABASE_SERVICE_KEY` | Service role key | Supabase Dashboard |
| `yTEST_YACHT_001_SUPABASE_URL` | Tenant DB URL | Per-tenant |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | Tenant service key | Per-tenant |
| `OPENAI_API_KEY` | Embeddings | OpenAI |

---

## Tenant Key Alias Convention

Format: `y<yacht_id_no_dashes>`

Example:
- yacht_id: `TEST_YACHT_001`
- tenant_key_alias: `yTEST_YACHT_001`

Environment variables:
- `yTEST_YACHT_001_SUPABASE_URL`
- `yTEST_YACHT_001_SUPABASE_SERVICE_KEY`

---

## Cross-Tenant Protection

1. **JWT Verification:** All requests verified with MASTER_SUPABASE_JWT_SECRET
2. **User→Tenant Lookup:** user_id from JWT → MASTER DB → yacht_id
3. **No Frontend Trust:** Backend ignores yacht_id from request body
4. **RLS Policies:** Each tenant DB has yacht_id isolation via RLS

---

## Health Check Endpoints

| Service | Endpoint | Expected |
|---------|----------|----------|
| Backend | `GET /health` | `{"status": "healthy"}` |
| Backend | `GET /version` | `{"git_commit": "...", "environment": "..."}` |
| Master Supabase | `GET /rest/v1/` | 200 with empty array |
| Tenant Supabase | `GET /rest/v1/` | 200 with empty array |

---

## TODO (Unknowns to Verify)

- [ ] Confirm auth.celeste7.ai redirects correctly to app.celeste7.ai
- [ ] Verify CSP headers allow both Supabase URLs
- [ ] Check if additional tenant DBs exist beyond TEST_YACHT_001

---

**Last Updated:** 2026-01-13
