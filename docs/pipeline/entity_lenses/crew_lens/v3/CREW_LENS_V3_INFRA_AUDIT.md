# Crew Lens v3 - Infrastructure Audit

**Version**: 3.0
**Date**: 2026-01-30
**Purpose**: Document existing infrastructure, environment, and system integration

---

## Executive Summary

**Current Infrastructure Status**: ✅ **70% Ready**

**What Works**:
- ✅ Database schema exists (`pms_hours_of_rest` with 28 columns)
- ✅ Handlers implemented (`update_hours_of_rest`, `view_hours_of_rest`, `export_hours_of_rest`)
- ✅ Dispatcher wiring exists (`internal_dispatcher.py`)
- ✅ JWT authentication with yacht isolation via GUC
- ✅ Audit logging infrastructure (`pms_audit_log`)
- ✅ RLS base policies (need fixing, but infrastructure is there)

**What's Missing**:
- ❌ Registry entries for HoR actions
- ❌ New handlers for templates, warnings, sign-offs
- ❌ New database tables (3 missing)
- ❌ RLS policy fixes (replace permissive policies)
- ❌ Tests (Docker RLS, Staging CI, E2E)

---

## Environment Variables

### Location

**Files**:
- `.env` (development root)
- `apps/api/.env` (API service)
- `.env.tenant1` (tenant-specific)
- `.env.staging.example` (staging template)
- `.env.e2e` (E2E test environment)

### Current Environment Variables (apps/api/.env)

```bash
# ============================================================================
# Environment
# ============================================================================
ENVIRONMENT=development

# ============================================================================
# MASTER Supabase (authentication + tenant routing)
# ============================================================================
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
MASTER_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
MASTER_SUPABASE_JWT_SECRET=wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==

# ============================================================================
# TENANT 1 Supabase (per-yacht database)
# ============================================================================
TENANT_1_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
TENANT_1_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
TENANT_SUPABASE_JWT_SECRET=ep2o/+mEQD/b54M8W50Vk3GrsuVayQZfValBnshte7yaZtoIGDhb9ffFQNU31su109d2wBz8WjSNX6wc3MiEFg==

# ============================================================================
# Default yacht routing (maps to TENANT_1)
# ============================================================================
DEFAULT_YACHT_CODE=y85fe1119-b04c-41ac-80f1-829d23322598

# ============================================================================
# Yacht-specific credentials (runtime pattern)
# ============================================================================
y85fe1119-b04c-41ac-80f1-829d23322598_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
y85fe1119-b04c-41ac-80f1-829d23322598_SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ============================================================================
# Test identities
# ============================================================================
TEST_USER_EMAIL=x@alex-short.com
TEST_USER_PASSWORD=Password2!
TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598

# ============================================================================
# OpenAI (for local extraction testing only)
# ============================================================================
OPENAI_API_KEY=sk-proj-...

# ============================================================================
# CORS (local development)
# ============================================================================
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,https://app.celeste7.ai

# ============================================================================
# Feature flags
# ============================================================================
FAULT_LENS_V1_ENABLED=true
EMAIL_TRANSPORT_ENABLED=true
```

### Required for Crew Lens v3

**No new environment variables needed** ✅

All HoR functionality uses existing infrastructure:
- Database connections: ✓ `TENANT_1_SUPABASE_URL`, `TENANT_1_SUPABASE_SERVICE_KEY`
- JWT validation: ✓ `TENANT_SUPABASE_JWT_SECRET`
- Yacht routing: ✓ `{yacht_id}_SUPABASE_URL` pattern

---

## GUC (Session Variables) Pattern

### What is GUC?

**GUC** = PostgreSQL **G**rand **U**nified **C**onfiguration

**Purpose**: Set session-specific variables for RLS policies and yacht isolation

### How It Works

**1. Middleware sets GUC on each request**:

```python
# apps/api/middleware/yacht_isolation.py

async def set_yacht_context(request: Request, call_next):
    """Set yacht_id GUC for RLS policies"""

    # Extract yacht_id from JWT
    yacht_id = extract_yacht_from_jwt(request)

    # Get database session
    db = request.state.db

    # CRITICAL: Set GUC for this request
    db.execute(text(f"SET request.yacht_id = '{yacht_id}'"))

    # Continue with request
    response = await call_next(request)

    return response
```

**2. RLS policies read GUC**:

```sql
CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest
  FOR SELECT
  USING (
    -- Read GUC set by middleware
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR public.is_hod()
      OR public.is_captain()
    )
  );
```

### GUC Variables Used

| Variable | Type | Set By | Used In | Purpose |
|----------|------|--------|---------|---------|
| `request.yacht_id` | UUID | Middleware | All RLS policies | Yacht isolation |
| `request.user_id` | UUID | JWT (`auth.uid()`) | RLS policies | User identification |
| `request.jwt_claims` | JSONB | Supabase Auth | Helper functions | Role detection |

### Critical Implementation Details

**1. GUC is request-scoped** (not session-scoped):
- Set on EVERY request via middleware
- Auto-cleared after request completes
- Thread-safe (one GUC per database connection)

**2. GUC must be set BEFORE any database queries**:
```python
# BAD: Query before GUC
records = db.query(pms_hours_of_rest).all()  # ✗ RLS fails (yacht_id NULL)
db.execute(text(f"SET request.yacht_id = '{yacht_id}'"))

# GOOD: GUC before query
db.execute(text(f"SET request.yacht_id = '{yacht_id}'"))
records = db.query(pms_hours_of_rest).all()  # ✓ RLS works
```

**3. GUC fallback in RLS**:
```sql
-- Use TRUE as missing_ok parameter
current_setting('request.yacht_id', TRUE)::UUID

-- If GUC not set, returns NULL (RLS denies access)
-- Better than error for debugging
```

### Verification

**Check if GUC is set**:
```sql
SELECT current_setting('request.yacht_id', TRUE) AS yacht_id;
```

**Expected output**:
```
        yacht_id
------------------------------------
 85fe1119-b04c-41ac-80f1-829d23322598
```

---

## JWT Authentication Flow

### JWT Structure

**Token issued by**: Supabase Auth

**Payload structure**:
```json
{
  "aud": "authenticated",
  "exp": 1738253200,
  "iat": 1738249600,
  "iss": "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1",
  "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",  // user_id
  "email": "x@alex-short.com",
  "phone": "",
  "app_metadata": {
    "provider": "email",
    "providers": ["email"]
  },
  "user_metadata": {
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "role": "captain",
    "display_name": "Captain Maria Martinez"
  },
  "role": "authenticated",
  "aal": "aal1",
  "amr": [
    {
      "method": "password",
      "timestamp": 1738249600
    }
  ],
  "session_id": "f9a8b7c6-d5e4-3f2a-1b0c-9d8e7f6a5b4c"
}
```

### JWT Validation Middleware

**Location**: `apps/api/middleware/auth.py`

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def validate_jwt(request: Request, credentials: HTTPAuthorizationCredentials):
    """Validate JWT and extract user context"""

    token = credentials.credentials

    # Get JWT secret for yacht
    yacht_code = extract_yacht_code_from_request(request)
    jwt_secret = get_jwt_secret_for_yacht(yacht_code)

    try:
        # Decode and validate
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=['HS256'],
            audience='authenticated'
        )

        # Extract user context
        user_id = payload['sub']
        yacht_id = payload['user_metadata']['yacht_id']
        role = payload['user_metadata']['role']

        # Attach to request state
        request.state.user_id = user_id
        request.state.yacht_id = yacht_id
        request.state.role = role
        request.state.jwt_payload = payload

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### User Context Extraction

**From JWT to database functions**:

1. **Middleware extracts** → `request.state.user_id`, `request.state.yacht_id`
2. **Middleware sets GUC** → `SET request.yacht_id = '{yacht_id}'`
3. **Database uses** → `auth.uid()` (from JWT `sub`), `current_setting('request.yacht_id')`

### Role Mapping

**JWT role** → **Database role check**:

```python
# JWT payload
"user_metadata": {
  "role": "chief_engineer"
}

# Database function
CREATE FUNCTION is_hod() RETURNS BOOLEAN AS $$
  SELECT role IN ('chief_engineer', 'chief_officer', 'chief_steward', 'purser')
  FROM auth_users_roles
  WHERE user_id = auth.uid() AND is_active = TRUE;
$$ LANGUAGE sql;
```

**Why double-check in database?**
- JWT can be stale (role changed after token issued)
- Database is source of truth
- Security defense-in-depth

---

## Feature Flags

### Current Flags (from .env)

```bash
FAULT_LENS_V1_ENABLED=true
EMAIL_TRANSPORT_ENABLED=true
```

### Crew Lens v3 Flags (Proposed)

**No new flags needed for MVP** ✅

All HoR functionality is core (not optional):
- Hours of Rest compliance is **regulatory requirement** (ILO/STCW)
- Cannot be disabled via flag

**Future flags (post-MVP)**:
```bash
# Phase 4+ enhancements
CREW_HOURS_PLATFORM_TRACKING_ENABLED=true  # Auto-detect overtime from usage
CREW_HOURS_EMAIL_NOTIFICATIONS_ENABLED=true  # Email vs ledger only
```

### Flag Usage Pattern

**In handlers**:
```python
from os import getenv

def send_hor_notification(user, message):
    """Send HoR notification (ledger or email)"""

    # Always send to ledger (MVP)
    send_ledger_notification(user, message)

    # Optionally send email (future)
    if getenv('CREW_HOURS_EMAIL_NOTIFICATIONS_ENABLED') == 'true':
        send_email_notification(user, message)
```

---

## Database Connection Management

### Connection Pool

**SQLAlchemy engine** (apps/api/database.py):

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Tenant-specific connection
def get_tenant_engine(yacht_id):
    """Get database engine for specific yacht"""

    # Get credentials from env
    tenant_url = os.getenv(f'{yacht_id}_SUPABASE_URL')
    tenant_key = os.getenv(f'{yacht_id}_SUPABASE_SERVICE_KEY')

    # Build connection string
    connection_string = f"postgresql://postgres:{tenant_key}@{tenant_url}/postgres"

    # Create engine with pooling
    engine = create_engine(
        connection_string,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True  # Verify connections before use
    )

    return engine

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### Request-Scoped Sessions

**Dependency injection** (FastAPI):

```python
from fastapi import Depends

def get_db():
    """Get database session for request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Usage in routes
@app.post("/v1/actions/execute")
async def execute_action(
    action: str,
    params: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Set GUC before any queries
    db.execute(text(f"SET request.yacht_id = '{user.yacht_id}'"))

    # Execute handler
    result = ACTION_HANDLERS[action](params, user, db)

    return result
```

---

## Audit Logging Infrastructure

### Table: `pms_audit_log`

**Schema**:
```sql
CREATE TABLE pms_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,
  record_id UUID,
  action TEXT NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE', or action name
  user_id UUID NOT NULL,
  yacht_id UUID NOT NULL,
  before_state JSONB,
  after_state JSONB,
  signature JSONB,  -- For SIGNED actions (never NULL)
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pms_audit_log_table_record
  ON pms_audit_log(table_name, record_id);

CREATE INDEX idx_pms_audit_log_user_action
  ON pms_audit_log(user_id, action, created_at DESC);
```

### Audit Trigger (Automatic)

**Triggered on every mutation**:

```sql
CREATE OR REPLACE FUNCTION audit_hor_mutation()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO pms_audit_log (
    table_name, record_id, action, user_id, yacht_id,
    before_state, after_state, created_at
  ) VALUES (
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    TG_OP,  -- 'INSERT', 'UPDATE', 'DELETE'
    auth.uid(),
    current_setting('request.yacht_id', TRUE)::UUID,
    CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
    NOW()
  );
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach to table
CREATE TRIGGER trigger_audit_pms_hours_of_rest
  AFTER INSERT OR UPDATE OR DELETE ON pms_hours_of_rest
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();
```

### Manual Audit (From Handlers)

**For SIGNED actions**:

```python
def log_to_audit(action, user, record=None, signature=None, metadata=None, db=None):
    """Manually log action to audit table"""

    audit_entry = pms_audit_log(
        table_name='pms_hor_monthly_signoffs',
        record_id=record.id if record else None,
        action=action,  # e.g., 'crew_sign_month'
        user_id=user.id,
        yacht_id=user.yacht_id,
        before_state=None,
        after_state=record.to_dict() if record else None,
        signature=signature,  # CRITICAL: Never NULL for SIGNED actions
        metadata=metadata or {},
        created_at=datetime.utcnow()
    )

    db.add(audit_entry)
    db.commit()
```

**SIGNED actions signature schema**:
```json
{
  "signed_by": "user_uuid",
  "signed_at": "2026-01-30T12:00:00Z",
  "signature_type": "digital",
  "signature_data": "base64_encoded_hash",
  "ip_address": "192.168.1.10",
  "user_agent": "Mozilla/5.0...",
  "verification_method": "password"
}
```

---

## Dispatcher Architecture

### Internal Dispatcher

**Location**: `apps/api/internal_dispatcher.py`

**Current implementation**:

```python
from handlers.compliance_handlers import (
    update_hours_of_rest_execute,
    view_hours_of_rest_execute,
    export_hours_of_rest_execute
)

ACTION_HANDLERS = {
    'update_hours_of_rest': update_hours_of_rest_execute,
    'view_hours_of_rest': view_hours_of_rest_execute,
    'export_hours_of_rest': export_hours_of_rest_execute,
}

def dispatch_action(action: str, params: dict, user, db):
    """Dispatch action to handler"""

    if action not in ACTION_HANDLERS:
        raise ActionNotFoundError(f"Action {action} not found")

    handler = ACTION_HANDLERS[action]

    try:
        result = handler(params, user, db)
        return result
    except Exception as e:
        log_error(action, user, e)
        raise
```

### Action Execution Flow

```
Client Request
    ↓
POST /v1/actions/execute {"action": "update_hours_of_rest", "params": {...}}
    ↓
Auth Middleware (validate JWT)
    ↓
Yacht Isolation Middleware (set GUC)
    ↓
Action Router (dispatch to handler)
    ↓
Handler (business logic + RLS enforcement)
    ↓
Database (RLS policies filter data)
    ↓
Audit Trigger (log mutation)
    ↓
Response Builder (standardized format)
    ↓
Client Response
```

---

## Search Integration

### Search Routing

**Location**: `apps/api/search/domain_router.py`

**Domain keyword mapping**:

```python
DOMAIN_KEYWORDS = {
    'hours_of_rest': [
        'hours of rest', 'hor', 'rest hours', 'rest periods',
        'compliance', 'overtime', 'sign month', 'warning',
        'normal hours', 'schedule', 'department hours',
        'update my hours', 'show my rest'
    ],
    'certificates': [
        'certificate', 'cert', 'expiring', 'ENG1', 'STCW',
        'port certs', 'medical', 'license', 'who is expiring'
    ],
    # Other domains...
}

def route_to_domain(query: str) -> str:
    """Route search query to domain"""
    query_lower = query.lower()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            return domain

    return 'general'
```

### Certificate Lens Restriction

**CRITICAL**: Certificate queries must NOT route to Crew Lens

```python
# BAD: Would route to crew lens
query = "who is expiring"
domain = route_to_domain(query)  # Should be 'certificates', not 'crew'

# Ensure correct routing
CERTIFICATE_QUERIES = {
    'expiring', 'ENG1', 'STCW', 'port certs', 'medical certificate'
}

if any(kw in query.lower() for kw in CERTIFICATE_QUERIES):
    domain = 'certificates'  # Force correct domain
```

---

## Testing Infrastructure

### Docker RLS Tests

**Location**: `tests/docker/`

**Pattern** (from existing tests):

```python
# tests/docker/run_hor_rls_tests.py

import docker
import pytest

def test_crew_self_access():
    """Crew can view own HoR records"""
    client = docker.from_env()

    # Run test container
    result = client.containers.run(
        'celeste-hor-tests:latest',
        command='pytest tests/test_crew_self_access.py',
        environment={
            'TENANT_SUPABASE_URL': os.getenv('TENANT_1_SUPABASE_URL'),
            'TENANT_SUPABASE_SERVICE_KEY': os.getenv('TENANT_1_SUPABASE_SERVICE_KEY'),
            'TEST_USER_ID': 'crew_uuid',
            'TEST_YACHT_ID': '85fe1119-b04c-41ac-80f1-829d23322598'
        },
        detach=False
    )

    assert result.exit_code == 0
```

### Staging CI Tests

**Location**: `.github/workflows/staging-crew-acceptance.yml`

**Workflow**:

```yaml
name: Staging Crew Acceptance

on:
  workflow_dispatch: {}
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  staging-crew:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Run Staging Acceptance
        env:
          API_BASE: ${{ secrets.BASE_URL }}
          TENANT_SUPABASE_URL: ${{ secrets.TENANT_SUPABASE_URL }}
          TEST_USER_EMAIL: ${{ secrets.STAGING_CREW_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.STAGING_USER_PASSWORD }}
        run: |
          python tests/ci/staging_crew_acceptance.py
```

### Playwright E2E Tests

**Location**: `tests/e2e/crew_lens_hor.spec.ts`

**Test pattern**:

```typescript
import { test, expect } from '@playwright/test';

test('Crew can update hours of rest via ActionModal', async ({ page }) => {
  // Login as crew
  await page.goto('https://app.celeste7.ai');
  await page.fill('[data-testid=email-input]', 'crew@example.com');
  await page.fill('[data-testid=password-input]', 'Password2!');
  await page.click('[data-testid=login-button]');

  // Search for action
  await page.fill('[data-testid=search-input]', 'update my hours');

  // Click action from list
  await page.click('[data-testid=action-update_hours_of_rest]');

  // Fill modal
  await page.fill('[data-testid=record-date]', '2026-01-30');
  await page.fill('[data-testid=rest-period-1-start]', '22:00');
  await page.fill('[data-testid=rest-period-1-end]', '06:00');

  // Submit
  await page.click('[data-testid=submit-action]');

  // Verify success
  await expect(page.locator('[data-testid=success-message]')).toContainText('Hours of Rest updated');

  // Verify compliance label
  await expect(page.locator('[data-testid=compliance-status]')).toContainText('Compliant');
});
```

---

## Notification Infrastructure

### Ledger Notification System

**Table**: `crew_ledger_notifications` (existing)

**Create notification**:

```python
def send_ledger_notification(user_id, type, title, message, action_suggestion=None):
    """Send notification to crew ledger"""

    notification = crew_ledger_notifications(
        user_id=user_id,
        type=type,  # 'hor_update_reminder', 'hor_violation_warning', etc.
        title=title,
        message=message,
        action_suggestion=action_suggestion,  # Prefill data for ActionModal
        status='unread',
        created_at=datetime.utcnow()
    )

    db.add(notification)
    db.commit()

    # Push notification via websocket (if connected)
    push_notification_to_user(user_id, notification)
```

**Action suggestion format**:

```json
{
  "action": "update_hours_of_rest",
  "params": {
    "record_date": "2026-01-30",
    "prefill_suggestion": {
      "total_work_hours": 15.0,
      "recommended_rest_periods": [
        {"start": "23:00", "end": "07:00", "hours": 8.0},
        {"start": "12:00", "end": "13:00", "hours": 1.0}
      ]
    }
  },
  "cta_button": {
    "label": "Update HoR",
    "action": "update_hours_of_rest"
  }
}
```

### Email Notifications (Future)

**Email transport** (apps/api/services/email_service.py):

```python
# Currently exists for other lenses
# Will reuse for HoR in production

def send_hor_email(user_email, subject, body):
    """Send HoR notification via email"""

    if not os.getenv('EMAIL_TRANSPORT_ENABLED') == 'true':
        return  # Skip if disabled

    # Use existing email service
    send_email(
        to=user_email,
        subject=subject,
        body=body,
        template='hor_notification'
    )
```

---

## Current Infrastructure Gaps

### Database

❌ **Missing tables**:
1. `pms_crew_normal_hours` (work schedule templates)
2. `pms_crew_hours_warnings` (warning tracking)
3. `pms_hor_monthly_signoffs` (multi-level sign-offs)

❌ **Missing columns**:
- `pms_hours_of_rest`: crew_signed_at, crew_signature, hod_signed_at, hod_signed_by, hod_signature, captain_signed_at, captain_signed_by, captain_signature

🐛 **Broken calculations**:
- `weekly_rest_hours` shows daily value (not rolling 7-day sum)

### Backend

❌ **Missing registry entries**: None for HoR actions

❌ **Missing handlers**:
- `configure_normal_hours_execute`
- `apply_normal_hours_to_week_execute`
- `view_department_hours_execute`
- `view_rest_warnings_execute`
- `acknowledge_rest_violation_execute`
- `dismiss_rest_warning_execute`
- `crew_sign_month_execute`
- `hod_sign_department_month_execute`
- `master_finalize_month_execute`

### RLS

⚠️ **Permissive policies**: Need replacement with precise role-based policies

### Tests

❌ **No tests exist** for Crew Lens HoR:
- Docker RLS tests: 0
- Staging CI tests: 0
- Playwright E2E tests: 0

---

## Infrastructure Readiness Checklist

### ✅ Ready (No Action Needed)

- [x] Environment variables configured
- [x] JWT authentication flow
- [x] GUC yacht isolation pattern
- [x] Database connection pooling
- [x] Audit logging infrastructure
- [x] Dispatcher architecture
- [x] Ledger notification system
- [x] Search domain routing
- [x] Existing handlers (3 of 12)
- [x] Base RLS policies (need fixing, but infrastructure exists)

### ❌ Needs Implementation

- [ ] Registry entries (12 actions)
- [ ] New handlers (9 handlers)
- [ ] New database tables (3 tables)
- [ ] RLS policy fixes (4 tables)
- [ ] Database triggers (weekly calc fix)
- [ ] Docker RLS tests (10+ test cases)
- [ ] Staging CI tests (3+ scenarios)
- [ ] Playwright E2E tests (5+ flows)

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Infrastructure Audit Complete
**Readiness**: 70% (infrastructure exists, needs implementation)
