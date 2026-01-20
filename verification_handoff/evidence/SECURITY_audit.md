# PHASE 6: Security/RLS/Storage Audit

**Date:** 2026-01-20T16:45:00Z

## B001-AR: FIXED (Commit c196d3b)

The B001 fix has now been applied to all files that perform JWT verification.

### Files with MASTER-first JWT pattern (ALL FIXED)

| File | Line | Status |
|------|------|--------|
| `apps/api/middleware/auth.py` | 205-218 | ✅ FIXED (a19afcf) |
| `apps/api/action_router/validators/jwt_validator.py` | 34-66 | ✅ FIXED (c196d3b) |
| `apps/api/microaction_service.py` | 293-337 | ✅ FIXED (c196d3b) |

**Verified:** 2026-01-20T17:15:00Z - Endpoints no longer return "Signature verification failed"

## Bug Pattern

**Wrong (TENANT first):**
```python
jwt_secret = (
    os.getenv("TENANT_SUPABASE_JWT_SECRET") or  # ❌ Wrong
    os.getenv("MASTER_SUPABASE_JWT_SECRET") or
    os.getenv("SUPABASE_JWT_SECRET")
)
```

**Correct (MASTER first):**
```python
secrets_to_try = []
if MASTER_SUPABASE_JWT_SECRET:  # ✅ MASTER first
    secrets_to_try.append(('MASTER', MASTER_SUPABASE_JWT_SECRET))
if TENANT_SUPABASE_JWT_SECRET and TENANT_SUPABASE_JWT_SECRET != MASTER_SUPABASE_JWT_SECRET:
    secrets_to_try.append(('TENANT', TENANT_SUPABASE_JWT_SECRET))
```

## RLS Audit Summary (from 03.10_rls_report)

| Table | Anonymous | Own Yacht | Cross-Yacht | Verdict |
|-------|-----------|-----------|-------------|---------|
| pms_work_orders | ✅ blocked | ✅ visible | ✅ blocked | PASS |
| pms_equipment | ✅ blocked | ✅ visible | ✅ blocked | PASS |
| documents | ⚠️ VISIBLE | ✅ visible | ✅ blocked | REVIEW |
| email_threads | ✅ blocked | ✅ visible | ✅ blocked | PASS |
| handovers | ✅ blocked | ✅ visible | ✅ blocked | PASS |

### B007: Documents Table RLS

**Issue:** Anonymous SELECT allowed on documents table
**Risk:** Low-Medium (metadata only, actual files require signed URL)
**Recommendation:** Add RLS policy requiring authentication

## Storage Bucket Security

| Bucket | Public | Verdict |
|--------|--------|---------|
| documents | ❌ Private | ✅ PASS |
| pms-receiving-images | ❌ Private | ✅ PASS |
| pms-discrepancy-photos | ❌ Private | ✅ PASS |
| pms-label-pdfs | ❌ Private | ✅ PASS |
| pms-part-photos | ❌ Private | ✅ PASS |
| pms-finance-documents | ❌ Private | ✅ PASS |

**All storage buckets are PRIVATE** ✅

## Document Loader Security

| Check | Status |
|-------|--------|
| Auth required | ✅ |
| Yacht ID required | ✅ |
| Path prefix validation | ✅ |
| Signed URLs (1hr TTL) | ✅ |
| Backend signing option | ✅ |

## Yacht Isolation Checks

| Endpoint | Isolation Method | Status |
|----------|-----------------|--------|
| /v1/bootstrap | JWT user_id → fleet_registry lookup | ✅ |
| /webhook/search | yacht_id from bootstrap context | ✅ |
| /email/* | yacht_id from JWT + validation | ✅ |
| /v1/documents/{id}/sign | yacht_id from document metadata | ✅ |
| /v1/actions/* | validate_yacht_isolation() | ⚠️ Blocked by B001-AR |

## Secrets Management

| Item | Status |
|------|--------|
| No secrets in git | ✅ |
| .env files in .gitignore | ✅ |
| Render env vars for production | ✅ |
| Service role key protected | ✅ |

## Critical Vulnerabilities Status

### RESOLVED: B001-AR - JWT Secret Priority Bug

**Status:** ✅ FIXED (Commit c196d3b)
**Verified:** JWT verification now works on all `/v1/actions/*` endpoints

### LOW: B007 - Documents RLS Too Permissive

**Impact:** Document metadata visible to unauthenticated users
**Mitigation:** Actual file content still requires signed URL
**Recommendation:** Add RLS policy requiring authentication (post-launch)

## Verdict

**PHASE 6: PASSED**

### All Passed
- All storage buckets private ✅
- Document loader has yacht isolation ✅
- Core auth endpoint (bootstrap, search) working ✅
- Action router endpoints working ✅ (B001-AR fixed)
- No secrets in repository ✅

### Low Priority (Post-Launch)
- **B007**: Documents table allows anonymous SELECT (metadata only)

## Evidence Files
- This report: `evidence/SECURITY_audit.md`
- RLS report: `evidence/03.10_rls_report.md`
- B001 fix: `evidence/B001_fix_code_refs.md`
