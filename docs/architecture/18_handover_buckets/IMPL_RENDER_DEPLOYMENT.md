# Handover Export System — Render Deployment Specification

> **Target Repository**: https://github.com/shortalex12333/handover_export
> **Created**: 2026-01-14
> **Purpose**: Complete deployment configuration for Claude B auto-deployment

---

## System Overview

This service handles **TWO primary export workflows**:

| Workflow | Source | Process |
|----------|--------|---------|
| **User Handover Export** | `handover_entries` table (user-created notes) | Query by user_id → Assemble draft → Sign → Export PDF/HTML/Email |
| **Email Extraction** | Microsoft Outlook emails | Fetch → Classify → Summarize → Create handover entries |

**Critical**: The user-populated handover table is the PRIMARY use case. Email extraction is an ADDITIONAL source that feeds into the same handover system.

---

## Quick Reference

| Setting | Value |
|---------|-------|
| Service Type | Web Service |
| Runtime | Python 3 |
| Region | Frankfurt (EU) |
| Instance Type | Starter (can scale) |
| Auto-Deploy | Yes (on push to `main`) |

---

## 1. Render Service Configuration

### Basic Settings

```yaml
Name: handover-export-api
Type: Web Service
Environment: Python 3
Region: Frankfurt (EU Central)
Branch: main
Root Directory: /  # or /api if monorepo structure
```

### Build Configuration

```yaml
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Alternative Start Commands** (depending on structure):
```bash
# If using gunicorn with uvicorn workers (production)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT

# If simple FastAPI
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 2. Environment Variables

### Required Variables

Uses same naming convention as existing Render services (see `/env vars/render env vars.md`):

| Variable | Description | Example Value |
|----------|-------------|---------------|
| **Supabase - Master DB** | | |
| `MASTER_SUPABASE_URL` | Master Supabase project URL | `https://qvzmkaamzaqxpzbewjxe.supabase.co` |
| `MASTER_SUPABASE_SERVICE_KEY` | Master service role key | `eyJ...` |
| `MASTER_SUPABASE_JWT_SECRET` | Master JWT secret | `wXka4UZu...` |
| **Supabase - Tenant DB** | Pattern: `{YACHT_ID}_SUPABASE_*` | |
| `yTEST_YACHT_001_SUPABASE_URL` | Tenant Supabase project URL | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` | Tenant service role key | `eyJ...` |
| `yTEST_YACHT_001_SUPABASE_JWT_SECRET` | Tenant JWT secret | `ep2o/+mE...` |
| **OpenAI** | | |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o-mini | `sk-proj-...` |
| **Azure OAuth** | | |
| `AZURE_TENANT_ID` | Microsoft Azure AD Tenant | `d44c2402-b515-4d6d-a392-5cfc88ae53bb` |
| `AZURE_CLIENT_ID` | Azure App Registration ID | `a744caeb-9896-4dbf-8b85-d5e07dba935c` |
| `AZURE_CLIENT_SECRET` | Azure App Secret (if confidential client) | `{from Azure portal}` |
| **Application** | | |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `PYTHONPATH` | Python module path | `/opt/render/project/src` |

**Tenant DB Naming Convention**:
- Pattern: `{YACHT_ID}_SUPABASE_URL`, `{YACHT_ID}_SUPABASE_SERVICE_KEY`, `{YACHT_ID}_SUPABASE_JWT_SECRET`
- Example: `yTEST_YACHT_001_SUPABASE_URL` for test yacht
- Service resolves yacht from request context → loads correct tenant credentials

**Why Two Databases?**
- **Master DB**: `role_definitions`, `department_definitions`, `domain_codes` (shared reference data)
- **Tenant DB**: `handover_entries`, `handover_drafts`, `handover_signoffs`, `user_profiles` (vessel-specific)

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_MODEL` | Model for classification/merging | `gpt-4o-mini` |
| `MAX_CONCURRENT_CLASSIFICATIONS` | Parallel AI calls | `10` |
| `MAX_CONCURRENT_MERGES` | Parallel merge operations | `5` |
| `EMAIL_FETCH_BATCH_SIZE` | Emails per Graph API call | `100` |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | API rate limiting | `60` |
| `REDIS_URL` | Redis for caching (optional) | `None` |
| `SENTRY_DSN` | Error tracking (optional) | `None` |

### Environment Variable Template

Copy this to Render dashboard (matches existing services):

```env
# ===========================================
# SUPABASE - MASTER DB (shared reference data)
# ===========================================
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=
MASTER_SUPABASE_JWT_SECRET=

# ===========================================
# SUPABASE - TENANT DB (per yacht, pattern: {YACHT_ID}_SUPABASE_*)
# ===========================================
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=
yTEST_YACHT_001_SUPABASE_JWT_SECRET=

# ===========================================
# OPENAI (for email classification)
# ===========================================
OPENAI_API_KEY=

# ===========================================
# AZURE OAUTH (for email extraction)
# ===========================================
AZURE_TENANT_ID=d44c2402-b515-4d6d-a392-5cfc88ae53bb
AZURE_CLIENT_ID=a744caeb-9896-4dbf-8b85-d5e07dba935c
AZURE_CLIENT_SECRET=

# ===========================================
# APPLICATION
# ===========================================
LOG_LEVEL=INFO
PYTHONPATH=/opt/render/project/src
```

---

## 3. Repository Structure

Claude B should create this structure in the `handover_export` repo:

```
handover_export/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Environment configuration
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # OAuth endpoints (Azure)
│   │   ├── health.py           # Health check endpoints
│   │   │
│   │   │ # === USER HANDOVER EXPORT (PRIMARY) ===
│   │   ├── handover_drafts.py  # Draft generation, review, sign-off
│   │   ├── handover_export.py  # PDF/HTML/Email export
│   │   ├── handover_entries.py # CRUD for user handover notes
│   │   │
│   │   │ # === EMAIL EXTRACTION (SECONDARY) ===
│   │   └── email_extraction.py # Email-to-handover pipeline
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   │
│   │   │ # === CORE HANDOVER SERVICES ===
│   │   ├── draft_generator.py  # Assemble entries into draft
│   │   ├── draft_reviewer.py   # Review state machine
│   │   ├── signoff_manager.py  # Accept/countersign workflow
│   │   ├── exporter.py         # PDF/HTML/Email generation
│   │   │
│   │   │ # === EMAIL SERVICES ===
│   │   ├── azure_auth.py       # Azure OAuth service
│   │   ├── graph_client.py     # Microsoft Graph API
│   │   ├── email_pipeline.py   # 8-stage orchestrator
│   │   ├── classifier.py       # AI classification
│   │   └── merger.py           # AI summary merging
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── handover.py         # Handover entries, drafts, sections
│   │   ├── signoff.py          # Sign-off and countersign models
│   │   ├── export.py           # Export job models
│   │   ├── email.py            # Email extraction models
│   │   └── database.py         # Supabase table models
│   │
│   └── utils/
│       ├── __init__.py
│       ├── encryption.py       # Token encryption
│       ├── rate_limiter.py     # Rate limiting
│       ├── pdf_renderer.py     # PDF generation (WeasyPrint)
│       └── logging.py          # Structured logging
│
├── templates/
│   ├── handover_report.html    # Jinja2 template for PDF/HTML
│   ├── email_body.html         # Email template
│   └── styles.css              # Report styling
│
├── tests/
│   ├── __init__.py
│   ├── test_draft_generation.py
│   ├── test_signoff_workflow.py
│   ├── test_export.py
│   ├── test_email_pipeline.py
│   └── test_integration.py
│
├── requirements.txt
├── render.yaml                 # Render Blueprint (optional)
├── Dockerfile                  # Alternative to native Python
├── .env.example
└── README.md
```

---

## 4. requirements.txt

```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
gunicorn==21.2.0
python-multipart==0.0.6

# Microsoft Graph
msal==1.26.0
httpx==0.26.0

# OpenAI
openai==1.10.0

# Supabase
supabase==2.3.0

# Security
cryptography==41.0.7
python-jose[cryptography]==3.3.0

# Utilities
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# PDF Generation
weasyprint==60.2
jinja2==3.1.3

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0

# Monitoring (optional)
sentry-sdk[fastapi]==1.39.1
```

---

## 5. render.yaml Blueprint (Optional)

For Infrastructure as Code deployment:

```yaml
services:
  - type: web
    name: handover-export-api
    env: python
    region: frankfurt
    plan: starter
    branch: main
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      # Master DB
      - key: MASTER_SUPABASE_URL
        sync: false
      - key: MASTER_SUPABASE_SERVICE_KEY
        sync: false
      - key: MASTER_SUPABASE_JWT_SECRET
        sync: false
      # Tenant DB (test yacht)
      - key: yTEST_YACHT_001_SUPABASE_URL
        sync: false
      - key: yTEST_YACHT_001_SUPABASE_SERVICE_KEY
        sync: false
      - key: yTEST_YACHT_001_SUPABASE_JWT_SECRET
        sync: false
      # OpenAI
      - key: OPENAI_API_KEY
        sync: false
      # Azure OAuth
      - key: AZURE_TENANT_ID
        sync: false
      - key: AZURE_CLIENT_ID
        sync: false
      - key: AZURE_CLIENT_SECRET
        sync: false
      # Application
      - key: LOG_LEVEL
        value: INFO
      - key: PYTHONPATH
        value: /opt/render/project/src
      - key: PYTHON_VERSION
        value: 3.11.7
```

---

## 6. Health Check Endpoint

Claude B must implement this endpoint for Render health monitoring:

```python
# app/routers/health.py
from fastapi import APIRouter, Response
from datetime import datetime

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """
    Render uses this endpoint to verify service health.
    Returns 200 if service is operational.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness_check(supabase = Depends(get_supabase)):
    """
    Deep health check including dependencies.
    """
    checks = {
        "api": "ok",
        "supabase": "unknown",
        "openai": "unknown"
    }

    # Check Supabase
    try:
        await supabase.table("email_extraction_jobs").select("id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception as e:
        checks["supabase"] = f"error: {str(e)}"

    # Check OpenAI (lightweight)
    try:
        # Just verify API key format
        if settings.OPENAI_API_KEY.startswith("sk-"):
            checks["openai"] = "ok"
    except Exception as e:
        checks["openai"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())

    return Response(
        content=json.dumps({"status": "ready" if all_ok else "degraded", "checks": checks}),
        status_code=200 if all_ok else 503,
        media_type="application/json"
    )
```

---

## 7. User Handover Export API (PRIMARY)

These endpoints handle the main handover export workflow from user-populated entries.

### 7.1 Handover Entry Endpoints

```python
# app/routers/handover_entries.py

@router.get("/api/v1/handover/entries")
async def list_entries(
    user_id: Optional[str] = None,      # Filter by creator
    vessel_id: str = Depends(get_vessel),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    domain_code: Optional[str] = None,
    status: Optional[str] = None,        # confirmed, proposed, dismissed
    limit: int = 100,
    offset: int = 0
):
    """
    List handover entries filtered by user_id and other criteria.
    Primary endpoint for building handover drafts.
    """

@router.post("/api/v1/handover/entries")
async def create_entry(
    entry: HandoverEntryCreate,
    user_id: str = Depends(get_current_user)
):
    """
    Create new handover entry (user-populated note).
    """

@router.patch("/api/v1/handover/entries/{entry_id}")
async def update_entry(entry_id: str, updates: HandoverEntryUpdate):
    """Update entry text or domain classification."""

@router.post("/api/v1/handover/entries/{entry_id}/confirm")
async def confirm_entry(entry_id: str):
    """Confirm a proposed entry."""

@router.post("/api/v1/handover/entries/{entry_id}/dismiss")
async def dismiss_entry(entry_id: str, reason: Optional[str] = None):
    """Dismiss an entry from handover."""
```

### 7.2 Draft Generation Endpoints

```python
# app/routers/handover_drafts.py

@router.post("/api/v1/handover/drafts/generate")
async def generate_draft(
    request: DraftGenerateRequest,
    user_id: str = Depends(get_current_user),
    vessel_id: str = Depends(get_vessel)
):
    """
    Generate handover draft from entries.

    Request body:
    {
        "outgoing_user_id": "uuid",     # User handing over
        "incoming_user_id": "uuid",     # User receiving (optional)
        "handover_date": "2026-01-14",
        "shift_type": "day" | "night",
        "entry_ids": ["uuid", ...],     # Specific entries (optional)
        "include_all_confirmed": true   # Or include all confirmed entries
    }

    Returns draft_id for subsequent operations.
    """

@router.get("/api/v1/handover/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """
    Get draft with sections and items.
    Returns full draft structure organised by presentation buckets.
    """

@router.post("/api/v1/handover/drafts/{draft_id}/review")
async def enter_review(draft_id: str):
    """Transition: DRAFT → IN_REVIEW"""

@router.patch("/api/v1/handover/drafts/{draft_id}/items/{item_id}")
async def edit_item(draft_id: str, item_id: str, updates: ItemUpdate):
    """Edit item text. Creates audit trail in handover_draft_edits."""

@router.post("/api/v1/handover/drafts/{draft_id}/items/merge")
async def merge_items(draft_id: str, item_ids: List[str]):
    """Merge multiple items into one."""
```

### 7.3 Sign-off Endpoints

```python
# app/routers/handover_drafts.py (continued)

@router.post("/api/v1/handover/drafts/{draft_id}/accept")
async def accept_handover(
    draft_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Outgoing user accepts/signs the handover.
    Transition: IN_REVIEW → ACCEPTED
    Records sign-off in handover_signoffs table.
    """

@router.post("/api/v1/handover/drafts/{draft_id}/sign")
async def countersign_handover(
    draft_id: str,
    user_id: str = Depends(get_current_user),
    notes: Optional[str] = None
):
    """
    Incoming user countersigns the handover.
    Transition: ACCEPTED → SIGNED
    Records countersign in handover_signoffs table.
    """
```

### 7.4 Export Endpoints

```python
# app/routers/handover_export.py

@router.post("/api/v1/handover/drafts/{draft_id}/export")
async def export_handover(
    draft_id: str,
    format: str = "pdf",  # pdf, html, email
    recipients: Optional[List[str]] = None  # For email format
):
    """
    Export signed handover to PDF/HTML/Email.
    Transition: SIGNED → EXPORTED
    Stores export record in handover_exports table.

    Returns:
    - PDF: { "format": "pdf", "url": "storage_url", "filename": "..." }
    - HTML: { "format": "html", "content": "<html>..." }
    - Email: { "format": "email", "sent_to": [...], "message_id": "..." }
    """

@router.get("/api/v1/handover/exports")
async def list_exports(
    vessel_id: str = Depends(get_vessel),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """List previous handover exports."""

@router.get("/api/v1/handover/exports/{export_id}/download")
async def download_export(export_id: str):
    """Download previously exported PDF."""
```

### 7.5 Data Models

```python
# app/models/handover.py

class HandoverEntryCreate(BaseModel):
    narrative: str                      # The handover note text
    domain_code: Optional[str] = None   # e.g., 'ENG-03'
    source_type: str = "user"           # 'user' | 'email' | 'system'
    source_ref: Optional[str] = None    # Reference to source (email_id, etc)
    priority: str = "normal"            # 'critical' | 'high' | 'normal'
    tags: Optional[List[str]] = None

class DraftGenerateRequest(BaseModel):
    outgoing_user_id: str
    incoming_user_id: Optional[str] = None
    handover_date: date
    shift_type: str                     # 'day' | 'night'
    entry_ids: Optional[List[str]] = None
    include_all_confirmed: bool = True

class HandoverDraftResponse(BaseModel):
    id: str
    status: str                         # DRAFT | IN_REVIEW | ACCEPTED | SIGNED | EXPORTED
    outgoing_user: UserSummary
    incoming_user: Optional[UserSummary]
    handover_date: date
    shift_type: str
    sections: List[DraftSection]        # Organised by presentation bucket
    created_at: datetime
    accepted_at: Optional[datetime]
    signed_at: Optional[datetime]

class DraftSection(BaseModel):
    bucket: str                         # e.g., 'Command', 'Engineering'
    items: List[DraftItem]

class DraftItem(BaseModel):
    id: str
    narrative: str
    domain_code: str
    priority: str
    source_entry_ids: List[str]
    edited: bool
```

---

## 8. Auto-Deploy Configuration

### GitHub Integration

1. Connect Render to GitHub repository
2. Select `shortalex12333/handover_export`
3. Branch: `main`
4. Auto-Deploy: **Enabled**

### Deploy Triggers

| Trigger | Action |
|---------|--------|
| Push to `main` | Auto-deploy |
| Pull Request | Preview deploy (optional) |
| Manual | Deploy button in Render dashboard |

### Deploy Hooks (Optional)

Render provides a deploy hook URL that can be called to trigger deployment:

```bash
# Trigger deploy via webhook
curl -X POST https://api.render.com/deploy/srv-{service-id}?key={deploy-key}
```

---

## 8. Scaling Configuration

### Initial Settings (Starter)

```yaml
Instance Type: Starter
RAM: 512 MB
CPU: 0.5
```

### Production Settings (Recommended)

```yaml
Instance Type: Standard
RAM: 2 GB
CPU: 1
Instances: 2 (for availability)
```

### Auto-Scaling (Pro Plan)

```yaml
Min Instances: 1
Max Instances: 5
Target CPU: 70%
Target Memory: 80%
```

---

## 9. Logging and Monitoring

### Log Drain (Optional)

Send logs to external service:

```yaml
Log Stream URL: https://logs.example.com/ingest
```

### Structured Logging Format

```python
# app/utils/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "job_id"):
            log_obj["job_id"] = record.job_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)
```

---

## 10. Secrets Management

### Render Secret Files

For sensitive multi-line values (like certificates):

1. Go to Service > Environment > Secret Files
2. Add file with path `/etc/secrets/azure-cert.pem`
3. Access in code: `open('/etc/secrets/azure-cert.pem').read()`

### Encryption Key Generation

Generate secure encryption key:

```python
import secrets
print(secrets.token_hex(32))
# Output: 64-character hex string
```

---

## 11. CORS Configuration

For frontend integration:

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://celesteos.app",
        "https://*.celesteos.app",
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 12. Deployment Checklist for Claude B

### Pre-Deployment

- [ ] Create repository structure as specified in Section 3
- [ ] **USER HANDOVER (PRIMARY)**:
  - [ ] Implement handover entry CRUD endpoints
  - [ ] Implement draft generation from `handover_entries` filtered by `user_id`
  - [ ] Implement sign-off workflow (accept → countersign)
  - [ ] Implement PDF/HTML/Email export
- [ ] **EMAIL EXTRACTION (SECONDARY)**:
  - [ ] Implement Azure OAuth from `IMPL_EMAIL_AZURE_INTEGRATION.md`
  - [ ] Implement 8-stage pipeline from `IMPL_PYTHON_PIPELINE.md`
- [ ] Add health check endpoint (Section 6)
- [ ] Create `requirements.txt` (Section 4)
- [ ] Add `.env.example` with all variables
- [ ] Write basic tests

### Render Setup

- [ ] Create new Web Service in Render
- [ ] Connect to `shortalex12333/handover_export`
- [ ] Set Root Directory (if needed)
- [ ] Configure Build Command: `pip install -r requirements.txt`
- [ ] Configure Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Add all environment variables from Section 2
- [ ] Set Health Check Path: `/health`
- [ ] Enable Auto-Deploy

### Post-Deployment

- [ ] Verify `/health` returns 200
- [ ] Verify `/health/ready` shows all services connected
- [ ] **USER HANDOVER TESTS**:
  - [ ] Test query handover_entries by user_id
  - [ ] Test draft generation from entries
  - [ ] Test sign-off state transitions
  - [ ] Test PDF export generation
- [ ] **EMAIL EXTRACTION TESTS**:
  - [ ] Test OAuth flow with Azure
  - [ ] Test email extraction endpoint
- [ ] Verify Supabase writes work
- [ ] Monitor logs for errors

---

## 13. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Check requirements.txt includes all dependencies |
| Port binding failed | Ensure using `$PORT` environment variable |
| Azure auth fails | Verify redirect URI matches Render URL |
| Supabase connection timeout | Check SUPABASE_URL is correct |
| OpenAI rate limit | Reduce MAX_CONCURRENT_CLASSIFICATIONS |

### Render-Specific Notes

1. **Zero-downtime deploys**: Render keeps old instance running until new one is healthy
2. **Sleep on free tier**: Starter instances may sleep after inactivity (upgrade to Standard for always-on)
3. **Disk storage**: Render instances have ephemeral disk - use Supabase Storage for persistence

---

## 14. Related Documentation

| Document | Purpose |
|----------|---------|
| `IMPL_EMAIL_AZURE_INTEGRATION.md` | Azure OAuth, Graph API, database schema |
| `IMPL_PYTHON_PIPELINE.md` | 8-stage pipeline implementation |
| `IMPL_FRONTEND_JOURNEY.md` | Frontend integration and UX flows |
| `ANALYSIS_feasibility.md` | Overall system architecture |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-14 | Initial specification created |
