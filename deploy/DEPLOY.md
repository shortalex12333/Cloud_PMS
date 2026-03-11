# CelesteOS — Deployment Guide

## Quick Start (30 seconds)

```bash
cd deploy/local
./celeste.sh start          # Start API + background workers
./celeste.sh health         # Verify everything is up
./celeste.sh search "pump"  # Test a search
```

---

## Architecture

```
User types "pump"
       │
       ▼
   [ Next.js ]  ── auth ──►  MASTER Supabase (qvzmkaamzaqxpzbewjxe)
       │                      └─ user_accounts, fleet_registry
       │ SSE
       ▼
   [ API :8000 ]  ── data ──►  TENANT Supabase (vzsohavtuotocgrfkfyd)
       │                        └─ search_index (12,251 rows)
       │                        └─ pms_equipment, pms_faults, pms_parts...
       │
       ├─ Worker 1-3 (inline): Intent, Exact, BM25
       ├─ Cortex rewrites: query expansion
       └─ f1_search_cards() RPC: Trigram + TSV + Vector + Exact
              │
              ▼
         RRF Fusion (K=60) → SSE stream → results
```

### Background Workers (keep search_index hot)

| Worker | Container | What it does |
|--------|-----------|-------------|
| Projectionist | `celeste-projection` | Watches source tables, writes to search_index |
| Embedder | `celeste-embedding` | Generates 1536-dim OpenAI vectors |
| Nightly | `celeste-nightly` | Learns yacht-specific vocabulary from clicks |

---

## Folder Structure

```
deploy/
├── DEPLOY.md              ← You are here
├── local/                 ← THE ACTIVE DEPLOYMENT
│   ├── .env               ← All secrets (gitignored)
│   ├── .env.web           ← Frontend env (public keys only)
│   ├── docker-compose.yml ← Stack definition
│   ├── celeste.sh         ← CLI to manage everything
│   └── .gitignore         ← Protects secrets
│
└── archive/               ← OLD FILES (reference only, do not use)
    ├── render/            ← Render blueprint YAMLs (cancelled)
    │   ├── render.yaml               7 services, $49/mo
    │   ├── render-email-rag.yaml     duplicate email worker
    │   └── render-api-staging.yaml   staging API + another duplicate
    ├── old-compose/       ← Previous docker-compose attempts
    │   ├── docker-compose.original.yml
    │   ├── docker-compose.local.yml
    │   ├── docker-compose.macstudio.yml
    │   └── docker-compose.f1-workers.yml
    ├── old-env/           ← Previous scattered .env files
    └── old-scripts/       ← Previous startup scripts
```

---

## CLI Reference

```bash
cd deploy/local

# Lifecycle
./celeste.sh start          # API + projection + embedding workers
./celeste.sh start-all      # + web frontend
./celeste.sh stop            # Stop everything
./celeste.sh rebuild [svc]   # Rebuild one or all services

# Observability
./celeste.sh logs [svc]      # Follow logs (api, projection, embedding, web)
./celeste.sh status          # Container status + resource usage
./celeste.sh health          # Health check all endpoints
./celeste.sh db-check        # Verify DB connection + embedding coverage

# Testing
./celeste.sh search "query"  # Quick F1 search test (mints JWT, hits SSE)
./celeste.sh shell [svc]     # Shell into container
./celeste.sh nightly         # Run feedback loop manually
```

---

## What Was Cancelled on Render ($75/mo → $0)

| Render Service | Cost | Replaced By | Status |
|---------------|------|-------------|--------|
| celeste-pipeline-v1 | $7 | `api` container | Local |
| projection-worker | $7 | `projection` container | Local |
| embedding-worker | $7 | `embedding` container | Local |
| cache-invalidation-listener | $7 | **Deleted** (Redis disabled) | Gone |
| nightly-feedback-loop | $7 | `nightly` container (manual) | Local |
| documents-health-worker | $7 | **Deleted** (monitoring fluff) | Gone |
| shopping-list-health-worker | $7 | **Deleted** (monitoring fluff) | Gone |
| celeste-email-watcher | $7 | Not yet replicated | Later |
| email-rag-worker | $7 | Not yet replicated | Later |
| celeste-api-staging | $7 | **Deleted** (duplicate) | Gone |

---

## Database Connections

| DB | Host | Port | Purpose |
|----|------|------|---------|
| MASTER | `qvzmkaamzaqxpzbewjxe.supabase.co` | REST API | Auth + fleet_registry |
| TENANT | `db.vzsohavtuotocgrfkfyd.supabase.co` | **5432 direct** | All PMS data |

**Supavisor pooler (:6543) does NOT work for this tenant.** Direct connection only.

---

## Key Decisions

1. **Redis disabled** — All code paths gracefully degrade. Cortex uses in-memory LRU cache instead.
2. **Direct DB connections** — Port swap hack (5432→6543) removed from `f1_search_streaming.py` and `nightly_feedback_loop.py`.
3. **Statement timeout raised** — From 800ms to 3000ms for local dev (262ms TCP latency to AWS us-east-1). Configurable via `F1_STATEMENT_TIMEOUT` env var.
4. **Frontend auth model** — Vercel/web only talks to MASTER Supabase for auth. All PMS data goes through the API to TENANT DB. Frontend never touches TENANT directly.
