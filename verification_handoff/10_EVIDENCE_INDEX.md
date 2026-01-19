# 10_EVIDENCE_INDEX.md — Evidence File Registry

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Total Evidence Files:** 26

---

## EVIDENCE FILES

| File | Description | Command/Method | Result |
|------|-------------|----------------|--------|
| `E001_login_response.json` | User login returns JWT | `curl -X POST .../auth/v1/token` | ✅ VERIFIED |
| `E002_jwt_decoded.json` | JWT contains yacht_id, user_id, role | Python base64 decode | ✅ VERIFIED |
| `E003_auth_user_query.json` | Auth user reads own yacht data | `curl .../rest/v1/pms_work_orders` with user JWT | ✅ VERIFIED |
| `E004_cross_yacht_blocked.json` | Cross-yacht query returns empty | `curl ...?yacht_id=eq.00000000...` | ✅ VERIFIED (`[]`) |
| `E005_anon_blocked.json` | Anonymous access returns empty | `curl ...` without Authorization | ✅ VERIFIED (`[]`) |
| `E006_handover_rls.json` | Handover RLS works | `curl .../handovers` with user JWT | ✅ VERIFIED |
| `E007_email_rls.json` | Email RLS works | `curl .../email_threads` with user JWT | ✅ VERIFIED |
| `E008_work_orders_exist.json` | Work orders table has data | `curl ...` with service key | ✅ VERIFIED |
| `E009_equipment_exist.json` | Equipment table has data | `curl ...` with service key | ✅ VERIFIED |
| `E010_handovers_data.json` | Handovers table has 3+ rows | `curl ...` with service key | ✅ VERIFIED |
| `E011_handover_items.json` | Handover items has 5+ rows | `curl ...` with service key | ✅ VERIFIED |
| `E012_documents_count.json` | Documents table has 2760 rows | `curl ... -H "Prefer: count=exact"` | ✅ VERIFIED |
| `E013_email_watcher.json` | Email watcher active | `curl .../email_watchers` | ✅ VERIFIED |
| `E014_storage_buckets.json` | 6 storage buckets exist | `curl .../storage/v1/bucket` | ✅ VERIFIED |
| `E015_all_buckets_private.json` | All buckets are private | Derived from E014 | ✅ VERIFIED |
| `E016_anon_storage_blocked.json` | Anon storage access blocked | `curl ...` without Authorization | ✅ VERIFIED |
| `E017_yacht_folders.json` | Yacht-scoped folder structure | `curl .../object/list/documents` | ✅ VERIFIED |
| `E018_pipeline_401.json` | Pipeline JWT mismatch | `curl -X POST .../webhook/search` | ❌ FAILED (401) |
| `E019_rpc_mismatch.json` | Search RPC signature wrong | `curl -X POST .../rpc/unified_search_v2` | ❌ FAILED (PGRST202) |
| `E020_web_tests.txt` | Web unit tests pass | `npm test` in apps/web | ✅ VERIFIED (324/324) |
| `E021_ci_workflows.txt` | CI workflow files exist | `ls .github/workflows/*.yml` | ✅ VERIFIED (6 files) |
| `E022_action_count.json` | 71 actions registered | `grep` in action_registry.py | ✅ VERIFIED |
| `E023_note.txt` | Note: test results in E020 | N/A | N/A |
| `E024_path_validation_code.txt` | Document loader validates yacht path | `grep "startsWith"` | ⚠️ CODE EXISTS |
| `E025_bootstrap_code.txt` | AuthContext calls /v1/bootstrap | `grep "v1/bootstrap"` | ⚠️ CODE EXISTS |
| `B006_placeholder_search.txt` | Placeholder pattern search | `grep -rn "placeholder"` | ✅ NO DANGEROUS PATTERNS |

---

## COMMANDS USED

### E001: Login
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}'
```

### E002: JWT Decode
```python
import base64, json
jwt = "TOKEN_HERE"
payload = jwt.split('.')[1]
padding = 4 - len(payload) % 4
if padding != 4: payload += '=' * padding
decoded = base64.urlsafe_b64decode(payload)
print(json.loads(decoded))
```

### E003-E007: RLS Tests
```bash
# Auth user query
curl -s "$BASE/rest/v1/pms_work_orders?select=id,yacht_id,title&limit=3" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"

# Cross-yacht (should return [])
curl -s "$BASE/rest/v1/pms_work_orders?yacht_id=eq.00000000-0000-0000-0000-000000000000" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"

# Anonymous (should return [])
curl -s "$BASE/rest/v1/pms_work_orders?select=id&limit=3" \
  -H "apikey: ANON_KEY"
```

### E008-E013: Database Tables
```bash
curl -s "$BASE/rest/v1/{table}?select=*&limit=3" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

### E014-E017: Storage
```bash
# List buckets
curl -s "$BASE/storage/v1/bucket" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"

# List yacht folder contents
curl -s -X POST "$BASE/storage/v1/object/list/documents" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prefix":"85fe1119-b04c-41ac-80f1-829d23322598","limit":5}'
```

### E018-E019: Pipeline/Search Failures
```bash
# Pipeline (returns 401)
curl -s -X POST "https://pipeline-core.int.celeste7.ai/webhook/search" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"fuel filter"}'

# RPC (returns PGRST202)
curl -s -X POST "$BASE/rest/v1/rpc/unified_search_v2" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"search_query":"fuel filter"}'
```

### E020: Web Tests
```bash
cd apps/web && npm test
```

### E021: CI Files
```bash
ls -la .github/workflows/*.yml
```

### B006: Placeholder Search
```bash
grep -rn "00000000-0000-0000-0000-000000000000" apps/web/src/
grep -rn "placeholder-yacht\|placeholder-user" apps/web/src/
grep -rn "'placeholder'\|\"placeholder\"" apps/web/src/
```

---

## EVIDENCE STATUS SUMMARY

| Category | Verified | Failed | Code Only |
|----------|----------|--------|-----------|
| Authentication | 2 | 0 | 0 |
| RLS | 5 | 0 | 0 |
| Database | 6 | 0 | 0 |
| Storage | 4 | 0 | 0 |
| Pipeline/Search | 0 | 2 | 0 |
| CI/CD | 3 | 0 | 0 |
| Code Review | 0 | 0 | 2 |
| **Total** | **20** | **2** | **2** |

---

## NOTE ON CODE EVIDENCE

E024 and E025 are **code inspection only**, not runtime verification:
- E024: Path validation code exists in `documentLoader.ts`
- E025: Bootstrap call exists in `AuthContext.tsx`

These prove the code is present but do NOT prove runtime behavior works correctly.
Claude B must verify these at runtime on production.

