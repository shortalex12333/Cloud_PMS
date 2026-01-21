# FIX LOG

**Date:** 2026-01-20
**Updated:** 2026-01-21
**Status:** P0 FIXES APPLIED

---

## Rotation Checklist (DEFERRED)

| Item | Status |
|------|--------|
| MASTER Supabase service_role key rotated | ⏳ DEFERRED |
| TENANT Supabase service_role key rotated | ⏳ DEFERRED |
| OpenAI API key revoked | ⏳ DEFERRED |
| New keys in Render | ⏳ DEFERRED |
| New keys in Vercel | ⏳ DEFERRED |
| Local .env files updated | ⏳ DEFERRED |

**Note:** Key rotation deferred to final deployment phase per user directive.

---

## P0: CRITICAL FIXES (Exact Patches Prepared)

### P0-FIX-001: JWT Signature Verification

**File:** `apps/api/routes/auth_routes.py`
**Function:** `get_outlook_status`
**Lines:** 426-435

#### Current Code (INSECURE):
```python
        # Decode JWT to get user_id (Supabase JWT structure)
        import jwt
        try:
            # Decode without verification (we trust tokens from frontend)
            # In production, you'd verify with Supabase JWT secret
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get('sub')
        except Exception as e:
            logger.warning(f"[Auth] Failed to decode JWT: {e}")
            return OutlookStatusResponse(connected=False)
```

#### Fixed Code:
```python
        # Decode and VERIFY JWT signature
        import jwt

        # Get JWT secret (try MASTER first, then TENANT)
        jwt_secret = (
            os.getenv("MASTER_SUPABASE_JWT_SECRET") or
            os.getenv("TENANT_SUPABASE_JWT_SECRET") or
            os.getenv("SUPABASE_JWT_SECRET")
        )

        if not jwt_secret:
            logger.error("[Auth] No JWT secret configured for signature verification")
            return OutlookStatusResponse(connected=False)

        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_exp": True}
            )
            user_id = payload.get('sub')
        except jwt.ExpiredSignatureError:
            logger.warning("[Auth] JWT expired")
            return OutlookStatusResponse(connected=False)
        except jwt.InvalidTokenError as e:
            logger.warning(f"[Auth] JWT validation failed: {e}")
            return OutlookStatusResponse(connected=False)
```

#### Regression Test:
```python
# tests/security/test_jwt_forgery.py

import pytest
import jwt
from datetime import datetime, timedelta

def test_forged_jwt_rejected():
    """Verify forged JWTs are rejected."""
    # Create a forged token with invalid signature
    forged_payload = {
        "sub": "fake-user-id",
        "role": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    forged_token = jwt.encode(forged_payload, "wrong-secret", algorithm="HS256")

    response = client.get(
        "/auth/outlook/status",
        headers={"Authorization": f"Bearer {forged_token}"}
    )

    # Must NOT return user data
    assert response.status_code == 200
    assert response.json()["connected"] == False

def test_valid_jwt_accepted():
    """Verify valid JWTs work."""
    # Use actual Supabase JWT from authenticated user
    valid_token = os.getenv("TEST_VALID_JWT")

    response = client.get(
        "/auth/outlook/status",
        headers={"Authorization": f"Bearer {valid_token}"}
    )

    # Should work with valid token
    assert response.status_code == 200
```

#### Exploit Before/After:

**Before (Exploit Succeeds):**
```bash
# Forge a JWT with any user_id
FORGED_TOKEN=$(python3 -c "import jwt; print(jwt.encode({'sub': 'victim-user-id', 'role': 'authenticated'}, 'wrong-key', algorithm='HS256'))")

curl -X GET "https://pipeline-core.int.celeste7.ai/auth/outlook/status" \
  -H "Authorization: Bearer $FORGED_TOKEN"

# Result: Returns victim's Outlook status (VULNERABLE)
```

**After (Exploit Fails):**
```bash
# Same forged token
curl -X GET "https://pipeline-core.int.celeste7.ai/auth/outlook/status" \
  -H "Authorization: Bearer $FORGED_TOKEN"

# Result: {"connected": false} - token rejected (SECURE)
```

---

### P0-FIX-002: Auth Enforcement - context_navigation_routes.py

**File:** `apps/api/routes/context_navigation_routes.py`
**Routes:** 5 endpoints
**Lines:** 60, 85, 116, 148, 181

#### Import Addition (Top of file):
```python
# Add after existing imports
from fastapi import Depends
from middleware.auth import get_authenticated_user
```

#### Fix 2a: /create endpoint (Line 60)

**Current:**
```python
@router.post("/create", response_model=NavigationContext)
async def create_context(
    data: NavigationContextCreate,
    authorization: Optional[str] = Header(None)
):
    supabase = get_supabase_client()
    context = create_navigation_context(supabase, data)
    return context
```

**Fixed:**
```python
@router.post("/create", response_model=NavigationContext)
async def create_context(
    data: NavigationContextCreate,
    user_context: dict = Depends(get_authenticated_user)
):
    # Override any client-supplied IDs with JWT-verified values
    data.yacht_id = user_context["yacht_id"]
    data.user_id = user_context["user_id"]

    supabase = get_supabase_client()
    context = create_navigation_context(supabase, data)
    return context
```

#### Fix 2b: /update-anchor endpoint (Line 85)

**Current:**
```python
@router.put("/{context_id}/update-anchor", response_model=NavigationContext)
async def update_anchor(
    context_id: UUID,
    anchor_type: str,
    anchor_id: UUID,
    yacht_id: UUID,
    user_id: UUID,
    authorization: Optional[str] = Header(None)
):
```

**Fixed:**
```python
@router.put("/{context_id}/update-anchor", response_model=NavigationContext)
async def update_anchor(
    context_id: UUID,
    anchor_type: str,
    anchor_id: UUID,
    user_context: dict = Depends(get_authenticated_user)
):
    yacht_id = UUID(user_context["yacht_id"])
    user_id = UUID(user_context["user_id"])
```

#### Fix 2c: /related endpoint (Line 116)

**Current:**
```python
@router.post("/related", response_model=RelatedResponse)
async def get_related_artifacts(
    data: RelatedRequest,
    authorization: Optional[str] = Header(None)
):
```

**Fixed:**
```python
@router.post("/related", response_model=RelatedResponse)
async def get_related_artifacts(
    data: RelatedRequest,
    user_context: dict = Depends(get_authenticated_user)
):
    # Verify yacht_id matches authenticated user
    if str(data.yacht_id) != user_context["yacht_id"]:
        raise HTTPException(status_code=403, detail="Yacht mismatch")
```

#### Fix 2d: /add-relation endpoint (Line 148)

**Current:**
```python
@router.post("/add-relation", response_model=dict)
async def add_relation(
    data: AddRelationRequest,
    authorization: Optional[str] = Header(None)
):
```

**Fixed:**
```python
@router.post("/add-relation", response_model=dict)
async def add_relation(
    data: AddRelationRequest,
    user_context: dict = Depends(get_authenticated_user)
):
    # Verify yacht_id matches authenticated user
    if str(data.yacht_id) != user_context["yacht_id"]:
        raise HTTPException(status_code=403, detail="Yacht mismatch")
```

#### Fix 2e: /{context_id}/end endpoint (Line 181)

**Current:**
```python
@router.post("/{context_id}/end", response_model=NavigationContext)
async def end_context(
    context_id: UUID,
    yacht_id: UUID,
    user_id: UUID,
    authorization: Optional[str] = Header(None)
):
```

**Fixed:**
```python
@router.post("/{context_id}/end", response_model=NavigationContext)
async def end_context(
    context_id: UUID,
    user_context: dict = Depends(get_authenticated_user)
):
    yacht_id = UUID(user_context["yacht_id"])
    user_id = UUID(user_context["user_id"])
```

#### Regression Test:
```python
# tests/security/test_auth_required.py

def test_context_create_requires_auth():
    """Verify /api/context/create requires valid JWT."""
    response = client.post(
        "/api/context/create",
        json={"yacht_id": "...", "user_id": "..."}
        # NO Authorization header
    )
    assert response.status_code == 401

def test_context_create_rejects_forged_jwt():
    """Verify /api/context/create rejects forged JWT."""
    forged = jwt.encode({"sub": "fake"}, "wrong-secret")
    response = client.post(
        "/api/context/create",
        json={"yacht_id": "...", "user_id": "..."},
        headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401
```

---

### P0-FIX-003: Auth Enforcement - triggers_routes.py

**File:** `apps/api/routes/triggers_routes.py`
**Routes:** 5 endpoints
**Lines:** 65, 98, 128, 158, 191

#### Import Addition:
```python
from fastapi import Depends
from middleware.auth import get_authenticated_user
```

#### Fix 3a: /check endpoint (Line 65)

**Current:**
```python
@router.get("/check")
async def check_all_triggers(
    yacht_id: str = Query(..., description="Yacht ID to check triggers for"),
    authorization: Optional[str] = Header(None)
):
```

**Fixed:**
```python
@router.get("/check")
async def check_all_triggers(
    user_context: dict = Depends(get_authenticated_user)
):
    yacht_id = user_context["yacht_id"]  # FROM JWT, not query param
```

#### Fix 3b-3e: Similar pattern for remaining 4 endpoints

All must:
1. Remove `yacht_id: str = Query(...)` parameter
2. Add `user_context: dict = Depends(get_authenticated_user)`
3. Extract `yacht_id = user_context["yacht_id"]`

---

### P0-FIX-004: Tenant Isolation - action_executor.py

**File:** `apps/api/actions/action_executor.py`
**Lines:** 1355, 1497, 1922, 1982

#### Fix 4a: Line 1355

**Current:**
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).execute()
```

**Fixed:**
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).eq("yacht_id", self.yacht_id).execute()
```

#### Fix 4b: Line 1497

**Current:**
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).execute()
```

**Fixed:**
```python
self.db.table("work_orders").update(update_data).eq("id", entity_id).eq("yacht_id", self.yacht_id).execute()
```

#### Fix 4c: Line 1922

**Current:**
```python
current = self.db.table("purchases").select("status").eq("id", entity_id).single().execute()
```

**Fixed:**
```python
current = self.db.table("purchases").select("status").eq("id", entity_id).eq("yacht_id", self.yacht_id).single().execute()
```

#### Fix 4d: Line 1982

**Current:**
```python
current = self.db.table("checklist_items").select("notes").eq("id", entity_id).single().execute()
```

**Fixed:**
```python
current = self.db.table("checklist_items").select("notes").eq("id", entity_id).eq("yacht_id", self.yacht_id).single().execute()
```

---

### P0-FIX-005: Tenant Isolation - internal_dispatcher.py

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Lines:** 255, 449

#### Fix 5a: Line 255 (handovers)

**Current:**
```python
result = supabase.table("handovers").update({
    "content": content,
    "updated_at": datetime.utcnow().isoformat(),
    "updated_by": params["user_id"],
}).eq("id", params["handover_id"]).execute()
```

**Fixed:**
```python
result = supabase.table("handovers").update({
    "content": content,
    "updated_at": datetime.utcnow().isoformat(),
    "updated_by": params["user_id"],
}).eq("id", params["handover_id"]).eq("yacht_id", params["yacht_id"]).execute()
```

#### Fix 5b: Line 449 (documents)

**Current:**
```python
result = supabase.table("documents").update({
    "deleted_at": datetime.utcnow().isoformat(),
    "deleted_by": params["user_id"],
    "delete_reason": params.get("reason", "Deleted via API"),
}).eq("id", params["document_id"]).execute()
```

**Fixed:**
```python
result = supabase.table("documents").update({
    "deleted_at": datetime.utcnow().isoformat(),
    "deleted_by": params["user_id"],
    "delete_reason": params.get("reason", "Deleted via API"),
}).eq("id", params["document_id"]).eq("yacht_id", params["yacht_id"]).execute()
```

---

### P0-FIX-006: Tenant Isolation - work_order_mutation_handlers.py

**File:** `apps/api/handlers/work_order_mutation_handlers.py`
**Line:** 914

**Current:**
```python
part_res = self.db.table("pms_parts").select("id, name, part_number, quantity_on_hand").eq("id", wp["part_id"]).limit(1).execute()
```

**Fixed:**
```python
part_res = self.db.table("pms_parts").select("id, name, part_number, quantity_on_hand").eq("id", wp["part_id"]).eq("yacht_id", yacht_id).limit(1).execute()
```

---

### P0-FIX-007: File Upload Hardening

**File:** `apps/api/routes/email.py`
**Lines:** 1293-1305

#### Add Constants (Top of file or in config):
```python
# File upload security constants
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
```

#### Replace Lines 1293-1305:

**Current:**
```python
        import base64
        file_data = base64.b64decode(content_bytes)

        # Determine storage path
        filename = attachment.get('name', 'attachment')
        content_type = attachment.get('contentType', 'application/octet-stream')
        folder = request.target_folder or 'email-attachments'
        storage_path = f"{yacht_id}/{folder}/{uuid.uuid4()}-{filename}"

        # Upload to storage
        supabase.storage.from_('documents').upload(
            storage_path, file_data,
            {'content-type': content_type}
        )
```

**Fixed:**
```python
        import base64
        import os
        import re

        file_data = base64.b64decode(content_bytes)

        # SECURITY: Validate file size
        if len(file_data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
            )

        # SECURITY: Validate and sanitize filename
        original_filename = attachment.get('name', 'attachment')
        # Extract extension safely
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # SECURITY: Validate MIME type
        content_type = attachment.get('contentType', 'application/octet-stream')
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Content type '{content_type}' not allowed"
            )

        # SECURITY: Generate safe storage path (no user-provided path components)
        safe_filename = f"{uuid.uuid4()}{ext}"
        storage_path = f"{yacht_id}/email-attachments/{safe_filename}"

        # Upload to storage
        supabase.storage.from_('documents').upload(
            storage_path, file_data,
            {'content-type': content_type}
        )
```

---

### P0-FIX-008: Remove Secrets from Git

**File:** `apps/api/tests/test_v2_search_endpoint.py`
**Lines:** 28, 31

**Current:**
```python
os.environ.setdefault('MASTER_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIs...')
...
os.environ.setdefault('TENANT_1_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1Ni...')
```

**Fixed:**
```python
# Require environment variables - do not provide defaults for secrets
if not os.getenv('MASTER_SUPABASE_SERVICE_KEY'):
    pytest.skip("MASTER_SUPABASE_SERVICE_KEY not set - required for integration tests")

if not os.getenv('TENANT_1_SUPABASE_SERVICE_KEY'):
    pytest.skip("TENANT_1_SUPABASE_SERVICE_KEY not set - required for integration tests")
```

---

### P0-FIX-009: CI Secret Scanning

**File:** `.github/workflows/security.yml` (NEW FILE)

```yaml
name: Security Scanning

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for gitleaks

      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Check for hardcoded secrets
        run: |
          # Fail if any JWT patterns found in code
          if grep -rE "eyJhbGciOiJIUzI1NiIs" --include="*.py" --include="*.ts" --include="*.js" .; then
            echo "ERROR: Hardcoded JWT tokens found in code!"
            exit 1
          fi

          # Fail if any OpenAI keys found
          if grep -rE "sk-proj-|sk-[a-zA-Z0-9]{48}" --include="*.py" --include="*.ts" --include="*.js" .; then
            echo "ERROR: Hardcoded API keys found in code!"
            exit 1
          fi

          echo "No hardcoded secrets detected"
```

---

## P1 Fixes (APPLIED 2026-01-21)

### P1-FIX-001: open_document Storage Path Validation

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**File:** `apps/api/action_router/registry.py`
**Lines:** 199-233 (dispatcher), 195-205 (registry)

**Issue:** `open_document` handler could generate signed URLs for any storage path, allowing cross-tenant document access.

**Fix:**
1. Added `yacht_id` to required_fields in registry
2. Added server-side validation that `storage_path` starts with `{yacht_id}/`

```python
# SECURITY FIX P1-001: Validate storage_path belongs to user's yacht
yacht_id = params["yacht_id"]
storage_path = params["storage_path"]

if not storage_path.startswith(f"{yacht_id}/"):
    raise ValueError(f"Access denied: Document does not belong to your yacht")
```

---

### P1-FIX-002: add_note Entity Ownership Check

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Lines:** 89-124

**Issue:** `add_note` handler inserted notes with `equipment_id` without verifying equipment belongs to yacht.

**Fix:** Added SELECT query with yacht_id filter before INSERT.

```python
# SECURITY FIX P1-002: Verify equipment belongs to yacht before INSERT
eq_result = supabase.table("pms_equipment").select("id, name").eq(
    "id", params["equipment_id"]
).eq("yacht_id", params["yacht_id"]).execute()

if not eq_result.data:
    raise ValueError(f"Equipment {params['equipment_id']} not found or access denied")
```

---

### P1-FIX-003: report_fault Entity Ownership Check

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Lines:** 558-601

**Issue:** `report_fault` handler inserted faults with `equipment_id` without verifying equipment belongs to yacht.

**Fix:** Added SELECT query with yacht_id filter before INSERT.

```python
# SECURITY FIX P1-003: Verify equipment belongs to yacht before INSERT
eq_result = supabase.table("pms_equipment").select("id, name").eq(
    "id", params["equipment_id"]
).eq("yacht_id", params["yacht_id"]).execute()

if not eq_result.data:
    raise ValueError(f"Equipment {params['equipment_id']} not found or access denied")
```

---

### P1-FIX-004: add_to_handover Entity Ownership Check

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Lines:** 360-462

**Issue:** `add_to_handover` handler inserted handover items with `entity_id` without verifying entity belongs to yacht.

**Fix:** Added dynamic entity lookup based on entity_type before INSERT.

```python
# SECURITY FIX P1-004: Verify entity belongs to yacht before INSERT
entity_table_map = {
    "equipment": "pms_equipment",
    "fault": "pms_faults",
    "work_order": "pms_work_orders",
    "part": "pms_parts",
    "document": "documents",
}

if entity_id and entity_type in entity_table_map:
    table_name = entity_table_map[entity_type]
    entity_result = supabase.table(table_name).select("id").eq(
        "id", entity_id
    ).eq("yacht_id", yacht_id).execute()

    if not entity_result.data:
        raise ValueError(f"{entity_type.capitalize()} {entity_id} not found or access denied")
```

---

### P1-FIX-005: Silent Audit Log Failures

**File:** `apps/api/action_router/dispatchers/internal_dispatcher.py`
**Lines:** 336-349, 434-451, 502-516, 556-570

**Issue:** 4 locations had `except Exception: pass` that silently swallowed audit log failures.

**Fix:** Added logging import and replaced silent pass with `logger.warning()`.

```python
# Import added at top of file
import logging
logger = logging.getLogger(__name__)

# Pattern applied to all 4 locations
except Exception as e:
    logger.warning(f"Audit log failed for {action_name} ({entity_type}={entity_id}): {e}")
```

---

## P1 Fixes - Remaining (QUEUED)

| # | Issue | File | Lines | Status |
|---|-------|------|-------|--------|
| 14 | JWT aud verification | jwt_validator.py | 70 | ⏳ QUEUED |
| 15 | JWT aud verification | microaction_service.py | 324 | ⏳ QUEUED |

---

## P2 Fixes (Queued - Apply After P1 Verified)

| # | Issue | File | Lines | Status |
|---|-------|------|-------|--------|
| 16 | Additional input validation | Various | - | ⏳ QUEUED |

---

## Completed Fixes

| # | Issue | Fixed By | Date | Verified |
|---|-------|----------|------|----------|
| P0-001 | JWT Signature Verification | Claude B | 2026-01-21 | Static ✅ |
| P0-002 | Auth - context_navigation_routes (5 routes) | Claude B | 2026-01-21 | Static ✅ |
| P0-003 | Auth - triggers_routes (5 routes) | Claude B | 2026-01-21 | Static ✅ |
| P0-004 | RLS - action_executor (4 queries) | Claude B | 2026-01-21 | Static ✅ |
| P0-005 | RLS - internal_dispatcher (2 queries) | Claude B | 2026-01-21 | Static ✅ |
| P0-006 | RLS - work_order_handlers (1 query) | Claude B | 2026-01-21 | Static ✅ |
| P0-007 | File Upload Hardening | Claude B | 2026-01-21 | Static ✅ |
| P0-008 | Remove Secrets from Git | Claude B | 2026-01-21 | Static ✅ |
| P0-009 | CI Secret Scanning | Claude B | 2026-01-21 | Static ✅ |
| P1-001 | open_document path validation | Claude B | 2026-01-21 | Static ✅ |
| P1-002 | add_note entity ownership | Claude B | 2026-01-21 | Static ✅ |
| P1-003 | report_fault entity ownership | Claude B | 2026-01-21 | Static ✅ |
| P1-004 | add_to_handover entity ownership | Claude B | 2026-01-21 | Static ✅ |
| P1-005 | Silent audit log failures (4x) | Claude B | 2026-01-21 | Static ✅ |

---

## Verification Protocol

For each fix:
1. Apply the patch
2. Run regression test
3. Execute exploit (must fail)
4. Document in evidence file
5. Mark as verified

**This log will be updated as fixes are applied.**
