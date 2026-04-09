# Agent Launch Orchestrator — 24 Agents, 12 Lenses

**Purpose:** Spawn 24 agents (2 per lens) to implement and verify all entity endpoints.
**Order:** DATA agents run first, VERIFY agents run after Docker rebuild.

---

## Phase 1 — DATA Agents (implement endpoints)

### For lenses 1–5: endpoints already exist, DATA agents only verify shape.
### For lenses 6–12: endpoints must be created in `apps/api/routes/entity_routes.py`.

**Spawn all DATA agents in parallel after confirming Docker is running:**

```bash
docker ps | grep celeste-api
# Must be: Up (healthy)
```

### DATA Agent Instructions

Each agent reads its dedicated DATA.md and implements or verifies the endpoint.

| Agent | File | Task |
|-------|------|------|
| data-01-work-order | `lens-01-work-order/DATA.md` | Verify existing endpoint shape |
| data-02-fault | `lens-02-fault/DATA.md` | Verify existing endpoint shape |
| data-03-equipment | `lens-03-equipment/DATA.md` | Verify existing endpoint shape |
| data-04-part | `lens-04-part/DATA.md` | Verify existing endpoint shape |
| data-05-receiving | `lens-05-receiving/DATA.md` | Verify existing endpoint shape |
| data-06-certificate | `lens-06-certificate/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-07-document | `lens-07-document/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-08-hours-of-rest | `lens-08-hours-of-rest/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-09-shopping-list | `lens-09-shopping-list/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-10-warranty | `lens-10-warranty/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-11-handover-export | `lens-11-handover-export/DATA.md` | **IMPLEMENT** in entity_routes.py |
| data-12-purchase-order | `lens-12-purchase-order/DATA.md` | **IMPLEMENT** in entity_routes.py |

---

## Shared Context for ALL DATA Agents

All DATA agents for lenses 6–12 write to the SAME file:
`apps/api/routes/entity_routes.py`

**File header (create if not exists):**

```python
"""
Entity lens endpoints — GET /v1/entity/{type}/{id}
One endpoint per entity type. Each returns the canonical shape consumed by RouteShell.
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from apps.api.auth import get_authenticated_user
from apps.api.tenant import get_tenant_client

logger = logging.getLogger(__name__)
router = APIRouter()
```

**Mount in pipeline_service.py** (add after other router includes, ~line 370):

```python
from apps.api.routes.entity_routes import router as entity_routes_router
app.include_router(entity_routes_router)
```

---

## Phase 2 — Docker Rebuild

After ALL DATA agents complete:

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/deploy/local
docker compose build celeste-api && docker compose up -d celeste-api
# Wait for health check
sleep 10
curl -s http://localhost:8000/health
```

---

## Phase 3 — VERIFY Agents (test endpoints)

Spawn all VERIFY agents in parallel after Docker rebuild is healthy.

| Agent | File | Tests |
|-------|------|-------|
| verify-01-work-order | `lens-01-work-order/VERIFY.md` | curl + frontend |
| verify-02-fault | `lens-02-fault/VERIFY.md` | curl + frontend |
| verify-03-equipment | `lens-03-equipment/VERIFY.md` | curl + frontend |
| verify-04-part | `lens-04-part/VERIFY.md` | curl + frontend |
| verify-05-receiving | `lens-05-receiving/VERIFY.md` | curl + frontend |
| verify-06-certificate | `lens-06-certificate/VERIFY.md` | curl + frontend |
| verify-07-document | `lens-07-document/VERIFY.md` | curl + frontend |
| verify-08-hours-of-rest | `lens-08-hours-of-rest/VERIFY.md` | curl + frontend |
| verify-09-shopping-list | `lens-09-shopping-list/VERIFY.md` | curl + frontend |
| verify-10-warranty | `lens-10-warranty/VERIFY.md` | curl + frontend |
| verify-11-handover-export | `lens-11-handover-export/VERIFY.md` | curl + frontend |
| verify-12-purchase-order | `lens-12-purchase-order/VERIFY.md` | curl + frontend |

---

## JWT Setup (required for all VERIFY agents)

```bash
# Mint token (must be done before spawning VERIFY agents)
python3 /tmp/mint_jwt.py
# Token saved to /tmp/jwt_token.txt
TOKEN=$(cat /tmp/jwt_token.txt)
```

If `/tmp/mint_jwt.py` doesn't exist, see `BACK_BUTTON_CLOUD_PMS/docs/superpowers/JWT_SETUP.md`.

---

## Success Criteria

All 12 lenses pass:
- [ ] OpenAPI registers the endpoint
- [ ] `curl` returns 200 with required non-null fields
- [ ] Browser: `/entity-type/{id}` loads without error
- [ ] No 500s in `docker logs celeste-api`

---

## Agent Directory Structure

```
docs/superpowers/agents/
├── LAUNCH.md                    ← this file
├── lens-01-work-order/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-02-fault/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-03-equipment/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-04-part/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-05-receiving/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-06-certificate/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-07-document/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-08-hours-of-rest/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-09-shopping-list/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-10-warranty/
│   ├── DATA.md
│   └── VERIFY.md
├── lens-11-handover-export/
│   ├── DATA.md
│   └── VERIFY.md
└── lens-12-purchase-order/
    ├── DATA.md
    └── VERIFY.md
```
