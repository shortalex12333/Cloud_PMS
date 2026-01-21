# E001: SECRET SCAN EVIDENCE

**Date:** 2026-01-20
**Phase:** 0 - Immediate Security Containment
**Status:** CRITICAL FINDINGS - ASSUME COMPROMISE

---

## Executive Summary

| Finding | Status | In Git? |
|---------|--------|---------|
| Supabase Service Role Keys | EXPOSED | YES (in test files) |
| Supabase Anon Keys | EXPOSED | YES (in test files) |
| OpenAI API Key | EXPOSED | NO (local only) |
| JWT Secrets | EXPOSED | YES (in test files) |
| Test Credentials | EXPOSED | NO (local only) |

**VERDICT: ASSUME ALL KEYS COMPROMISED. ROTATE IMMEDIATELY.**

---

## CRITICAL: Secrets in Git-Tracked Files

### File: `apps/api/tests/test_v2_search_endpoint.py`
**Git Status:** TRACKED (in version control history)

```
Line 28: os.environ.setdefault('MASTER_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q')

Line 31: os.environ.setdefault('TENANT_1_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY')
```

### Decoded JWT Payloads:

**MASTER Service Key:**
```json
{
  "iss": "supabase",
  "ref": "qvzmkaamzaqxpzbewjxe",
  "role": "service_role",
  "iat": 1763979046,
  "exp": 2079555046
}
```
- **Project:** qvzmkaamzaqxpzbewjxe (MASTER DB)
- **Role:** service_role (FULL ACCESS)
- **URL:** https://qvzmkaamzaqxpzbewjxe.supabase.co

**TENANT Service Key:**
```json
{
  "iss": "supabase",
  "ref": "vzsohavtuotocgrfkfyd",
  "role": "service_role",
  "iat": 1763592875,
  "exp": 2079168875
}
```
- **Project:** vzsohavtuotocgrfkfyd (TENANT DB)
- **Role:** service_role (FULL ACCESS)
- **URL:** https://vzsohavtuotocgrfkfyd.supabase.co

---

## HIGH: Secrets in Local Files (Not in Git)

### File: `.env.e2e` (NOT tracked - in .gitignore)

| Line | Variable | Value (truncated) | Type |
|------|----------|-------------------|------|
| 9 | MASTER_SUPABASE_ANON_KEY | eyJhbGciOiJIUzI1Ni... | Anon Key |
| 10 | MASTER_SUPABASE_SERVICE_ROLE_KEY | eyJhbGciOiJIUzI1Ni... | Service Key |
| 14 | TENANT_SUPABASE_SERVICE_ROLE_KEY | eyJhbGciOiJIUzI1Ni... | Service Key |
| 19 | SUPABASE_SERVICE_KEY | eyJhbGciOiJIUzI1Ni... | Service Key |
| 23 | TEST_USER_EMAIL | x@alex-short.com | Credential |
| 24 | TEST_USER_PASSWORD | Password2! | Credential |
| 32 | OPENAI_API_KEY | sk-proj-y288-URnPTK... | API Key |

### File: `apps/web/.env.local` (NOT tracked - in .gitignore)

| Line | Variable | Value (truncated) | Type |
|------|----------|-------------------|------|
| 6 | NEXT_PUBLIC_SUPABASE_ANON_KEY | eyJhbGciOiJIUzI1Ni... | Anon Key |
| 12 | NEXT_PUBLIC_YACHT_SALT | celeste_yacht_salt_2024 | Weak Salt |

---

## Files with JWT References (31 total)

The following files contain JWT token patterns:
1. `apps/api/tests/test_v2_search_endpoint.py` - **HARDCODED SECRETS**
2. `apps/api/tests/test_context_navigation.py` - Contains test JWTs
3. `apps/api/e2e_sandbox.py` - References env vars
4. `apps/api/e2e_sandbox_runner.py` - References env vars
5. `apps/api/e2e_test_harness.py` - References env vars
6. `apps/api/test_edge_cases.py` - References env vars
7. `apps/api/test_p2_handlers.py` - References env vars
8. `apps/api/test_p3_handlers.py` - References env vars
9. `apps/api/test_situations.py` - References env vars
10. Multiple documentation files - Examples only

---

## Supabase Projects Identified

| Project Ref | Type | URL | Status |
|-------------|------|-----|--------|
| qvzmkaamzaqxpzbewjxe | MASTER | https://qvzmkaamzaqxpzbewjxe.supabase.co | KEYS COMPROMISED |
| vzsohavtuotocgrfkfyd | TENANT | https://vzsohavtuotocgrfkfyd.supabase.co | KEYS COMPROMISED |

---

## REQUIRED ACTIONS

### IMMEDIATE (Before any other work):

1. **Rotate MASTER Supabase Keys**
   - Go to: https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/settings/api
   - Regenerate: service_role key, anon key, JWT secret

2. **Rotate TENANT Supabase Keys**
   - Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/settings/api
   - Regenerate: service_role key, anon key, JWT secret

3. **Rotate OpenAI API Key**
   - Go to: https://platform.openai.com/api-keys
   - Revoke: sk-proj-y288-URnPTK...
   - Generate new key

4. **Change Test User Password**
   - In Supabase Auth, reset password for: x@alex-short.com

5. **Remove Hardcoded Secrets from Test Files**
   - File: `apps/api/tests/test_v2_search_endpoint.py`
   - Replace hardcoded keys with os.getenv() calls

6. **Add CI Secret Scanning**
   - Add gitleaks or trufflehog to CI pipeline
   - Block merges containing secrets

---

## PROOF OF EXPOSURE

### Git Tracking Status:
```bash
$ git ls-files | grep test_v2_search_endpoint
apps/api/tests/test_v2_search_endpoint.py
```

### Hardcoded Secret Grep:
```bash
$ grep "os.environ.setdefault.*eyJ" apps/api/tests/test_v2_search_endpoint.py
Line 28: os.environ.setdefault('MASTER_SUPABASE_SERVICE_KEY', 'eyJhbGci...')
Line 31: os.environ.setdefault('TENANT_1_SUPABASE_SERVICE_KEY', 'eyJhbGci...')
```

---

## Verdict

**STATUS: BLOCKED**

Cannot proceed with any verification until:
- [ ] All Supabase keys rotated
- [ ] OpenAI key rotated
- [ ] Test user password changed
- [ ] Hardcoded secrets removed from test files
- [ ] CI secret scanning enabled

**The exposed service_role keys provide FULL DATABASE ACCESS including:**
- Bypass all RLS policies
- Read/write/delete any data
- Access auth.users table
- Modify database schema

---

**Evidence File:** E001_SECRET_SCAN.md
**Created:** 2026-01-20
**Auditor:** Claude B
