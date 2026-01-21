# CRITICAL REPRODUCTIONS

**Date:** 2026-01-20
**Status:** STOP-SHIP CONDITIONS EXIST

---

## PHASE 0: SECRET EXPOSURE

### Reproduction: Service Role Key in Git History

**Static Proof:**
- File: `apps/api/tests/test_v2_search_endpoint.py`
- Lines: 28, 31
- Git Status: TRACKED

**Dynamic Proof:**
```bash
# Verify file is tracked
$ git ls-files | grep test_v2_search_endpoint
apps/api/tests/test_v2_search_endpoint.py

# Extract the secrets
$ grep "SUPABASE_SERVICE_KEY" apps/api/tests/test_v2_search_endpoint.py
os.environ.setdefault('MASTER_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIs...')
os.environ.setdefault('TENANT_1_SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1Ni...')
```

**Impact:** Anyone with repo access can extract service_role keys and bypass ALL security.

---

## REQUIRED ROTATIONS (User Action Required)

### 1. MASTER Supabase Project: qvzmkaamzaqxpzbewjxe

**Dashboard URL:** https://supabase.com/dashboard/project/qvzmkaamzaqxpzbewjxe/settings/api

Rotate:
- [ ] Service Role Key (currently exposed)
- [ ] Anon Key
- [ ] JWT Secret

### 2. TENANT Supabase Project: vzsohavtuotocgrfkfyd

**Dashboard URL:** https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/settings/api

Rotate:
- [ ] Service Role Key (currently exposed)
- [ ] Anon Key
- [ ] JWT Secret

### 3. OpenAI API Key

**Dashboard URL:** https://platform.openai.com/api-keys

- [ ] Revoke key starting with: sk-proj-y288-URnPTK...
- [ ] Generate new key
- [ ] Update in Render environment variables

### 4. Test User Password

- [ ] Reset password for: x@alex-short.com
- [ ] Update in secure location (NOT in code)

---

## After Rotation Checklist

1. [ ] Update Render environment variables with new keys
2. [ ] Update Vercel environment variables with new keys
3. [ ] Verify services still work with new keys
4. [ ] Remove hardcoded secrets from test_v2_search_endpoint.py
5. [ ] Add gitleaks to CI pipeline

---

## Evidence References

- [E001_SECRET_SCAN.md](evidence/E001_SECRET_SCAN.md) - Complete secret inventory

---

**BLOCKING:** Cannot proceed with Phases 1-9 until rotations confirmed.
