# NOT VERIFIED - SECURITY BLOCKERS

**Date:** 2026-01-20
**Updated:** 2026-01-21
**Auditor:** Claude B
**Status:** P0+P1 CODE FIXES APPLIED - ROTATION DEFERRED

---

## Summary

This document lists all items that **CANNOT be marked as verified** due to critical security issues.

**UPDATE 2026-01-21:** P0 code fixes have been applied. Secret rotation deferred to final deployment.

---

## PHASE 0: SECRET HYGIENE

| Item | Status | Blocker |
|------|--------|---------|
| Secret Rotation | ❌ NOT VERIFIED | User action required - keys exposed in git |
| CI Secret Scanning | ❌ NOT VERIFIED | No gitleaks/trufflehog in CI |

**Evidence:** [E001_SECRET_SCAN.md](evidence/E001_SECRET_SCAN.md)

### Exposed Secrets Requiring Rotation:
1. MASTER Supabase Service Key - `qvzmkaamzaqxpzbewjxe`
2. TENANT Supabase Service Key - `vzsohavtuotocgrfkfyd`
3. OpenAI API Key - `sk-proj-y288...`
4. Test User Password - `Password2!`

---

## PHASE 1: JWT VERIFICATION

| Item | Status | Blocker |
|------|--------|---------|
| JWT Signature Verification | ✅ FIXED (P0-001) | Was: `verify_signature: False` at auth_routes.py:431 |
| JWT Audience Verification | ⚠️ P1 QUEUED | `verify_aud: False` in 2 locations |

**Evidence:** [E002_JWT_VERIFICATION.md](evidence/E002_JWT_VERIFICATION.md)

### Critical Bug:
```python
# auth_routes.py:431
payload = jwt.decode(token, options={"verify_signature": False})
```

---

## PHASE 2: AUTHENTICATION

| Item | Status | Blocker |
|------|--------|---------|
| All Routes Protected | ✅ FIXED (P0-002, P0-003) | Was: 10 routes with no auth |
| user_id from JWT | ✅ FIXED | Now extracted from JWT |
| yacht_id from JWT | ✅ FIXED | Now extracted from JWT |

**Evidence:** [E003_AUTH_ROUTES.md](evidence/E003_AUTH_ROUTES.md)

### Fixed Routes:
- `context_navigation_routes.py`: 5 routes - P0-002
- `triggers_routes.py`: 5 routes - P0-003

---

## PHASE 3: TENANT ISOLATION

| Item | Status | Blocker |
|------|--------|---------|
| All Queries Have yacht_id | ✅ FIXED (P0-004, P0-005, P0-006) | Was: 7 queries missing yacht_id |
| RLS Enforced | ⚠️ CODE-LEVEL | Service key still bypasses RLS - code-level filtering applied |

**Evidence:** [E004_RLS_BYPASS.md](evidence/E004_RLS_BYPASS.md)

### Fixed Queries:
- `action_executor.py`: 4 queries - P0-004
- `internal_dispatcher.py`: 2 queries - P0-005
- `work_order_mutation_handlers.py`: 1 query - P0-006

---

## PHASE 4: FILE UPLOAD

| Item | Status | Blocker |
|------|--------|---------|
| File Type Validation | ✅ FIXED (P0-007) | Extension + MIME whitelist |
| File Size Limits | ✅ FIXED (P0-007) | 50MB limit enforced |
| Path Traversal Prevention | ✅ FIXED (P0-007) | UUID-only filenames, fixed folder |
| Virus Scanning | ⚠️ NOT IMPLEMENTED | Consider for future enhancement |

**Evidence:** [E005_FILE_UPLOAD.md](evidence/E005_FILE_UPLOAD.md)

---

## PHASE 5: HANDLER DATA FLOW

**Status:** AUDITED - P1 FIXES APPLIED

| Item | Status | Issue |
|------|--------|-------|
| Router Validation Pipeline | ✅ VERIFIED | 10-step validation enforced |
| Yacht Isolation Check | ✅ VERIFIED | context.yacht_id == user.yacht_id |
| Exception Handling | ✅ VERIFIED | Proper HTTP status codes, logged |
| `open_document` Path Validation | ✅ FIXED (P1-001) | yacht_id prefix validation added |
| Entity Ownership Validation | ✅ FIXED (P1-002,003,004) | All 3 handlers now verify ownership |
| Silent Audit Failures | ✅ FIXED (P1-005) | All 4 locations now log warnings |

**Evidence:** [E006_PHASE5_HANDLER_FLOW.md](evidence/E006_PHASE5_HANDLER_FLOW.md)

### P1 Fixes Applied (2026-01-21):
- ✅ `open_document`: Now validates storage_path starts with yacht_id (P1-001)
- ✅ `add_note`: Now verifies equipment_id belongs to yacht (P1-002)
- ✅ `report_fault`: Now verifies equipment_id belongs to yacht (P1-003)
- ✅ `add_to_handover`: Now verifies entity_id belongs to yacht (P1-004)
- ✅ Silent audit log failures replaced with logger.warning (P1-005)

---

## PHASE 6: MICROACTION EXECUTION VERIFICATION

**Status:** FRAMEWORK READY - AWAITING EXECUTION

| Item | Status | Notes |
|------|--------|-------|
| Test Framework | ✅ CREATED | `verification_handoff/scripts/phase6_microaction_tests.py` |
| Evidence Template | ✅ CREATED | `verification_handoff/evidence/E007_PHASE6_MICROACTION_TESTS.md` |
| Test Actions (10) | ⏳ PENDING | report_fault, open_document, add_note, add_to_handover, etc. |
| Positive Tests | ⏳ PENDING | Valid JWT, matching yacht_id |
| Cross-Yacht Tests | ⏳ PENDING | Mismatched yacht_id in context |
| Ownership Tests | ⏳ PENDING | P1 fix verification |
| Audit Log Verification | ⏳ PENDING | Verify entries created |

**Evidence:** [E007_PHASE6_MICROACTION_TESTS.md](evidence/E007_PHASE6_MICROACTION_TESTS.md)

### Test Execution Requirements:
```bash
export API_BASE_URL="https://pipeline-core.int.celeste7.ai"
export TEST_JWT="<valid_jwt_token>"
export TEST_YACHT_ID="<yacht_id_from_jwt>"
export TEST_EQUIPMENT_ID="<equipment_id_belonging_to_yacht>"
export FOREIGN_YACHT_ID="<different_yacht_id>"
export FOREIGN_EQUIPMENT_ID="<equipment_id_from_foreign_yacht>"

python verification_handoff/scripts/phase6_microaction_tests.py
```

---

## PHASES 7-9: NOT YET AUDITED

| Phase | Status | Reason |
|-------|--------|--------|
| 7: Email & Document Flows | ⏳ PENDING | After Phase 6 |
| 8: RAG / Entity Extraction | ⏳ PENDING | After Phase 7 |
| 9: Production Parity & CI | ⏳ PENDING | After Phase 8 |

---

## VERDICT

**STATUS: P0+P1 CODE FIXES APPLIED - PHASE 6 FRAMEWORK READY**

### P0 Fixes Completed (2026-01-21):
1. ⏳ Rotate all exposed Supabase keys - DEFERRED to final deployment
2. ⏳ Rotate OpenAI API key - DEFERRED to final deployment
3. ✅ Remove hardcoded secrets from test files - P0-008
4. ✅ Fix `verify_signature: False` in auth_routes.py - P0-001
5. ✅ Add `Depends(get_authenticated_user)` to 10 unauthenticated routes - P0-002, P0-003
6. ✅ Add `yacht_id` filter to 7 database queries - P0-004, P0-005, P0-006
7. ✅ Add file upload validation - P0-007
8. ✅ Add CI secret scanning - P0-009

### P1 Fixes Completed (2026-01-21):
1. ✅ `open_document` yacht_id path validation - P1-001
2. ✅ `add_note` entity ownership check - P1-002
3. ✅ `report_fault` entity ownership check - P1-003
4. ✅ `add_to_handover` entity ownership check - P1-004
5. ✅ Silent audit log failures → logger.warning - P1-005

### Current Status:
- ✅ Phase 5: Handler Data Flow - AUDITED, P1 FIXES APPLIED
- ⏳ Phase 6: Microaction Verification - FRAMEWORK READY, AWAITING EXECUTION
- ⏳ Phase 7: Email & Document Flows - PENDING
- ⏳ Phase 8: RAG / Entity Extraction - PENDING
- ⏳ Phase 9: Production Parity & CI - PENDING

### Deferred to Final Deployment:
- Secret rotation for exposed keys

---

**This document will be updated as issues are resolved.**
