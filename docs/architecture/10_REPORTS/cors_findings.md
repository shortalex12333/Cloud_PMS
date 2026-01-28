# CORS Findings Report

**Date:** 2026-01-12
**Test Method:** HTTP preflight (OPTIONS) requests via curl and Python

---

## Summary

| Origin | Status | Notes |
|--------|--------|-------|
| https://app.celeste7.ai | ALLOWED | Production |
| https://auth.celeste7.ai | ALLOWED | Auth domain |
| https://cloud-pms-git-universalv1-*.vercel.app | ALLOWED | Preview |
| http://localhost:3000 | ALLOWED | Local dev |
| https://staging.celeste7.ai | **BLOCKED** | Missing from Render env var |
| https://malicious-site.com | BLOCKED | Correctly rejected |

---

## Issue Found

### CORS-STAGING-001: staging.celeste7.ai blocked by CORS

**Symptom:**
```
Origin: https://staging.celeste7.ai
Preflight Status: 400
ACAO Header: Not present
```

**Root Cause:**
The deployed backend on Render has `ALLOWED_ORIGINS` environment variable that does NOT include `staging.celeste7.ai`.

The code default includes it:
```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auth.celeste7.ai,https://app.celeste7.ai,https://staging.celeste7.ai,https://api.celeste7.ai,..."
)
```

But Render environment variable overrides the default and doesn't include staging.

**Fix:**
Update Render environment variable `ALLOWED_ORIGINS` to include `https://staging.celeste7.ai`:

```
ALLOWED_ORIGINS=https://auth.celeste7.ai,https://app.celeste7.ai,https://staging.celeste7.ai,https://api.celeste7.ai,https://cloud-pms-git-universalv1-c7s-projects-4a165667.vercel.app,http://localhost:3000,http://localhost:8000
```

---

## CSP-001 Status: RESOLVED

The `next.config.js` CSP connect-src already includes:
- `https://vzsohavtuotocgrfkfyd.supabase.co`
- `https://pipeline-core.int.celeste7.ai`
- `https://api.celeste7.ai`

No CSP violations for legitimate API requests.

---

## CORS-001 Status: RESOLVED

The `/v1/documents/{id}/sign` endpoint correctly returns CORS headers for allowed origins.

```
Origin: https://app.celeste7.ai
Preflight: 200 OK
ACAO: https://app.celeste7.ai
ACAM: GET, POST, OPTIONS
Actual Request: 401 (expected - no auth provided)
```

---

## Test Evidence

```bash
# Passing test (app.celeste7.ai)
curl -v -X OPTIONS \
  -H "Origin: https://app.celeste7.ai" \
  -H "Access-Control-Request-Method: POST" \
  https://pipeline-core.int.celeste7.ai/health

# Response:
# HTTP/2 200
# access-control-allow-origin: https://app.celeste7.ai
# access-control-allow-methods: GET, POST, OPTIONS

# Failing test (staging.celeste7.ai)
curl -v -X OPTIONS \
  -H "Origin: https://staging.celeste7.ai" \
  -H "Access-Control-Request-Method: POST" \
  https://pipeline-core.int.celeste7.ai/health

# Response:
# HTTP/2 400
# (no access-control-allow-origin header)
```

---

## Remediation

1. **Render Dashboard:**
   - Navigate to `pipeline-core` service
   - Environment tab
   - Update `ALLOWED_ORIGINS` to include `https://staging.celeste7.ai`
   - Redeploy

2. **Verification:**
   ```bash
   curl -v -X OPTIONS -H "Origin: https://staging.celeste7.ai" \
     https://pipeline-core.int.celeste7.ai/health
   ```
   Should return `access-control-allow-origin: https://staging.celeste7.ai`
