# 02_EVIDENCE_LEDGER.md — Traceable Evidence Registry

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Total Evidence Items:** 25
**Evidence Files:** See `10_EVIDENCE_INDEX.md` for complete file list

---

## EVIDENCE COLLECTION RULES

- Each item has a unique ID (E001, E002, etc.)
- Each item has a corresponding file in `/verification_handoff/evidence/`
- "Code review" is NOT evidence (marked as CODE_ONLY)
- Items without output are in `04_DO_NOT_TRUST_LIST.md`

---

## AUTHENTICATION EVIDENCE

### E001: User Login Returns Valid JWT
**Claim:** Supabase auth issues JWT on successful login
**Evidence File:** `evidence/E001_login_response.json`
**Command:**
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: ANON_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/login_payload.json
```
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E002: JWT Contains yacht_id in Claims
**Claim:** JWT payload includes yacht_id, user_id, role
**Evidence File:** `evidence/E002_jwt_decoded.json`
**Actual Claims Found:**
```json
{
  "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "email": "x@alex-short.com",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "user_role": "captain"
}
```
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

---

## RLS EVIDENCE

### E003: Authenticated User Can Read Own Yacht Data
**Claim:** RLS allows access to user's yacht data
**Evidence File:** `evidence/E003_auth_user_query.json`
**Output:** 3 work orders with yacht_id `85fe1119-b04c-41ac-80f1-829d23322598`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E004: Cross-Yacht Query Returns Empty
**Claim:** RLS blocks access to other yachts
**Evidence File:** `evidence/E004_cross_yacht_blocked.json`
**Output:** `[]`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E005: Anonymous Access Returns Empty
**Claim:** RLS blocks anonymous access
**Evidence File:** `evidence/E005_anon_blocked.json`
**Output:** `[]`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E006: Handovers RLS Works
**Claim:** handovers table has proper RLS
**Evidence File:** `evidence/E006_handover_rls.json`
**Output:** 2 handovers returned, all with correct yacht_id
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E007: Email Tables RLS Works
**Claim:** email_threads has RLS
**Evidence File:** `evidence/E007_email_rls.json`
**Output:** 1 email thread with correct yacht_id
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

---

## DATABASE EVIDENCE

### E008: Work Orders Table Exists with Data
**Claim:** pms_work_orders table exists and has data
**Evidence File:** `evidence/E008_work_orders_exist.json`
**Output:** 3 work orders with yacht_id, title, status
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E009: Equipment Table Exists with Data
**Claim:** pms_equipment table exists with yacht_id
**Evidence File:** `evidence/E009_equipment_exist.json`
**Output:** 3 equipment records (Generator 2, HVAC Chiller, Bow Thruster)
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E010: Handovers Table Has Data
**Claim:** handovers table exists with actual records
**Evidence File:** `evidence/E010_handovers_data.json`
**Output:** 3 handovers including "Chief Engineer Watch Handover"
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E011: Handover Items Table Has Data
**Claim:** handover_items table exists with records
**Evidence File:** `evidence/E011_handover_items.json`
**Output:** 3 items with yacht_id, handover_id, summary
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E012: Documents Table Has 2760 Rows
**Claim:** documents table has substantial data
**Evidence File:** `evidence/E012_documents_count.json`
**Output:** `{"total_documents": 2760, "evidence": "content-range: 0-0/2760"}`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E013: Email Watchers Active
**Claim:** email_watchers has active watcher
**Evidence File:** `evidence/E013_email_watcher.json`
**Output:** `{"sync_status": "active", "provider": "microsoft_graph"}`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

---

## STORAGE EVIDENCE

### E014: Storage Buckets Exist
**Claim:** 6 storage buckets configured
**Evidence File:** `evidence/E014_storage_buckets.json`
**Output:** Full bucket metadata for 6 buckets
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E015: All Buckets Are Private
**Claim:** No public buckets
**Evidence File:** `evidence/E015_all_buckets_private.json`
**Output:** `{"all_private": true, "buckets": [...]}`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E016: Anonymous Storage Access Blocked
**Claim:** Bucket listing requires auth
**Evidence File:** `evidence/E016_anon_storage_blocked.json`
**Output:** `{"statusCode":"400","message":"headers must have required property 'authorization'"}`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E017: Documents Bucket Has Yacht-Scoped Folders
**Claim:** Files organized by yacht_id prefix
**Evidence File:** `evidence/E017_yacht_folders.json`
**Output:** Folders: 01_BRIDGE, 01_OPERATIONS, 02_ENGINEERING, 03_DECK, 04_ACCOMMODATION
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

---

## SEARCH/PIPELINE EVIDENCE

### E018: Pipeline Search Returns 401
**Claim:** Pipeline backend rejects Supabase JWTs
**Evidence File:** `evidence/E018_pipeline_401.json`
**Output:** `{"detail":"Invalid token: Signature verification failed"}`
**Result:** ❌ FAILED (JWT signature mismatch - see B001)
**Date:** 2026-01-19

### E019: Supabase Search RPCs Return Parameter Error
**Claim:** unified_search_v2 RPC doesn't match expected signature
**Evidence File:** `evidence/E019_rpc_mismatch.json`
**Output:** `{"code":"PGRST202","message":"Could not find the function..."}`
**Result:** ❌ FAILED (see B003)
**Date:** 2026-01-19

---

## CI/CD EVIDENCE

### E020: Web Tests Pass
**Claim:** Frontend unit tests pass
**Evidence File:** `evidence/E020_web_tests.txt`
**Output:** `Test Files 15 passed, Tests 324 passed`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E021: CI Workflows Exist
**Claim:** GitHub Actions workflows configured
**Evidence File:** `evidence/E021_ci_workflows.txt`
**Output:** 6 workflow files listed
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

---

## MICROACTION EVIDENCE

### E022: Action Registry Has 71 Actions
**Claim:** 71 microactions defined (corrected from 67)
**Evidence File:** `evidence/E022_action_count.json`
**Output:** `{"actions_defined": 71, "handler_mappings": 359}`
**Source:** `apps/api/actions/action_registry.py`
**Result:** ✅ VERIFIED
**Date:** 2026-01-19

### E023: Microaction Test Reference
**Claim:** Test results available
**Evidence File:** `evidence/E023_note.txt`
**Note:** See E020_web_tests.txt for microaction unit test results
**Result:** Reference only
**Date:** 2026-01-19

---

## CODE INSPECTION (NOT RUNTIME VERIFICATION)

### E024: documentLoader.ts Has Path Validation
**Claim:** Frontend validates yacht_id in storage paths
**Evidence File:** `evidence/E024_path_validation_code.txt`
**Code Location:** `apps/web/src/lib/documentLoader.ts:44-52`
**Result:** ⚠️ CODE_ONLY (not runtime verified)
**Date:** 2026-01-19

### E025: AuthContext Uses Bootstrap Endpoint
**Claim:** Frontend calls /v1/bootstrap for yacht context
**Evidence File:** `evidence/E025_bootstrap_code.txt`
**Code Location:** `apps/web/src/contexts/AuthContext.tsx:117`
**Result:** ⚠️ CODE_ONLY (bootstrap returns 401 - B001)
**Date:** 2026-01-19

---

## BLOCKER SEARCH EVIDENCE

### B006: Placeholder Pattern Search
**Claim:** No dangerous placeholder patterns in code
**Evidence File:** `evidence/B006_placeholder_search.txt`
**Patterns Searched:**
- `00000000-0000-0000-0000-000000000000` → NO MATCHES
- `placeholder-yacht-id` → NO MATCHES
- `placeholder-user-id` → NO MATCHES
**SSR Placeholder Found:** `apps/web/src/lib/supabaseClient.ts:15` (intentional, low risk)
**Result:** ✅ NO DANGEROUS PATTERNS
**Date:** 2026-01-19

---

## EVIDENCE NOT COLLECTED (REQUIRES CLAUDE B)

| Claim | Why Not Collected |
|-------|-------------------|
| Production UI renders correctly | Did not visit apps.celeste7.ai |
| Email shows in search surface | Did not view UI |
| add_to_handover works | Did not trigger action |
| Audit logs written on mutation | Did not verify audit table |
| MS Graph OAuth token valid | Did not test OAuth flow |
| All 71 microactions work | Only subset verified |

