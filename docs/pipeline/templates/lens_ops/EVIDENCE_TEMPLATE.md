# {LENS_ID} Evidence Package

**Date:** {DATE}
**Environment:** Staging Canary (pipeline-core.int.celeste7.ai)
**Result:** {RESULT} ({PASS_COUNT}/{TOTAL_COUNT} tests passing)

---

## Executive Summary

This document provides tangible evidence that {LENS_ID} lens is production-ready:

✅ **Signature Validation:** 400/400/403/200 flow verified (missing/invalid/role-denied/success)
✅ **Stress Testing:** 0×500 verified across {STRESS_REQUEST_COUNT}+ concurrent requests
✅ **Notifications Idempotency:** UNIQUE constraint enforces single-row guarantee
✅ **Feature Flags:** Fail-closed behavior verified (503 when OFF, 200 when ON)

**Citations:**
- Role denial 403: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:799`
- 500 as hard fail: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`
- Evidence artifacts: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:815`
- Verdict thresholds: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:708`

---

## 1. Signature Validation Evidence

**Purpose:** Prove strict enforcement of signature requirements for SIGNED actions

**Test File:** `tests/ci/{LENS_ID}_signed_flow_acceptance.py`

**Tests:**
1. ✅ Missing signature → 400 signature_required
2. ✅ Invalid signature structure → 400 invalid_signature
3. ✅ CREW attempts SIGNED action → 403 invalid_signer_role (expected, per canon)
4. ✅ CAPTAIN valid signature → 200 + entity created
5. ✅ HOD (manager) valid signature → 200 + entity created

**Citation:**
> /Volumes/Backup/CELESTE/testing_success_ci:cd.md:799
> "Role denial asserts 403 (crew mutations)" - Expected 4xx is success when asserted explicitly

### Test 1: Missing Signature

**Expected:** 400 signature_required

**Request:**
```http
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "action": "{SIGNED_ACTION}",
  "context": {"yacht_id": "{YACHT_ID}"},
  "payload": {
    "yacht_id": "{YACHT_ID}",
    "{ENTITY_ID_KEY}": "{TEST_ENTITY_ID}"
    // NOTE: signature intentionally missing
  }
}
```

**Response:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": {
    "status": "error",
    "error_code": "signature_required",
    "message": "Signature payload required for SIGNED action"
  }
}
```

✅ **PASS:** 400 signature_required (strict enforcement confirmed)

---

### Test 2: Invalid Signature Structure

**Expected:** 400 invalid_signature

**Request:**
```http
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {jwt}
Content-Type: application/json

{
  "action": "{SIGNED_ACTION}",
  "context": {"yacht_id": "{YACHT_ID}"},
  "payload": {
    "yacht_id": "{YACHT_ID}",
    "{ENTITY_ID_KEY}": "{TEST_ENTITY_ID}",
    "signature": {"invalid": "structure"}  // Missing required keys
  }
}
```

**Response:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": {
    "status": "error",
    "error_code": "invalid_signature",
    "message": "Invalid signature: missing keys ['role_at_signing', 'signature_type', 'signed_at', 'user_id']"
  }
}
```

✅ **PASS:** 400 invalid_signature (structure validation confirmed)

---

### Test 3: CREW Denied (403)

**Expected:** 403 invalid_signer_role (PASS, not fail - per testing doctrine)

**Request:**
```http
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {crew_jwt}
Content-Type: application/json

{
  "action": "{SIGNED_ACTION}",
  "context": {"yacht_id": "{YACHT_ID}"},
  "payload": {
    "yacht_id": "{YACHT_ID}",
    "{ENTITY_ID_KEY}": "{TEST_ENTITY_ID}",
    "signature": {
      "signed_at": "2026-01-28T...",
      "user_id": "{CREW_USER_ID}",
      "role_at_signing": "crew",
      "signature_type": "pin_totp",
      "signature_hash": "mock_hash"
    }
  }
}
```

**Response:**
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": {
    "status": "error",
    "error_code": "invalid_signer_role",
    "message": "Role 'crew' cannot sign this action",
    "required_roles": ["captain", "manager"]
  }
}
```

✅ **PASS:** 403 invalid_signer_role (role gating confirmed)

**Citation:**
> /Volumes/Backup/CELESTE/testing_success_ci:cd.md:799
> "Role denial asserts 403 (crew mutations)" - This 403 is an expected, correct response

---

### Test 4: CAPTAIN Signature (200)

**Expected:** 200 + entity created

**Request:**
```http
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {captain_jwt}
Content-Type: application/json

{
  "action": "{SIGNED_ACTION}",
  "context": {"yacht_id": "{YACHT_ID}"},
  "payload": {
    "yacht_id": "{YACHT_ID}",
    "{ENTITY_ID_KEY}": "{TEST_ENTITY_ID}",
    "signature": {
      "signed_at": "2026-01-28T...",
      "user_id": "{CAPTAIN_USER_ID}",
      "role_at_signing": "captain",
      "signature_type": "pin_totp",
      "signature_hash": "mock_hash"
    }
  }
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "result": {
    "{ENTITY_TYPE}_id": "{ENTITY_ID}",
    "yacht_id": "{YACHT_ID}",
    ...
  }
}
```

✅ **PASS:** 200 + {ENTITY_TYPE} created (CAPTAIN allowed)

---

### Test 5: HOD (Manager) Signature (200)

**Expected:** 200 + entity created

**Request:**
```http
POST /v1/actions/execute HTTP/1.1
Authorization: Bearer {hod_jwt}
Content-Type: application/json

{
  "action": "{SIGNED_ACTION}",
  "context": {"yacht_id": "{YACHT_ID}"},
  "payload": {
    "yacht_id": "{YACHT_ID}",
    "{ENTITY_ID_KEY}": "{TEST_ENTITY_ID}",
    "signature": {
      "signed_at": "2026-01-28T...",
      "user_id": "{HOD_USER_ID}",
      "role_at_signing": "manager",
      "signature_type": "pin_totp",
      "signature_hash": "mock_hash"
    }
  }
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "result": {
    "{ENTITY_TYPE}_id": "{ENTITY_ID}",
    "yacht_id": "{YACHT_ID}",
    ...
  }
}
```

✅ **PASS:** 200 + {ENTITY_TYPE} created (HOD/manager allowed)

---

## 2. Stress Testing Evidence

**Purpose:** Prove 0×500 under concurrent load (hard requirement)

**Test File:** `tests/stress/{LENS_ID}_actions_endpoints.py`

**Configuration:**
- {LIST_CONCURRENCY} concurrent requests to `/v1/actions/list?domain={DOMAIN}`
- {EXECUTE_CONCURRENCY} concurrent requests to `/v1/actions/execute` (READ variant)

**Citation:**
> /Volumes/Backup/CELESTE/testing_success_ci:cd.md:249
> "500 means failure" - Any 5xx error indicates bug in contracts/stress

### Test 1: /v1/actions/list

**Results:**

| Metric | Value |
|--------|-------|
| Total Requests | {LIST_CONCURRENCY} |
| Status 200 | {LIST_200_COUNT} |
| Status 4xx | {LIST_4XX_COUNT} |
| Status 5xx | **{LIST_5XX_COUNT}** |
| Success Rate | {LIST_SUCCESS_RATE}% |

**Latencies:**

| Percentile | Latency (ms) |
|------------|--------------|
| P50 (median) | {LIST_P50} |
| P95 | {LIST_P95} |
| P99 | {LIST_P99} |
| Min | {LIST_MIN} |
| Max | {LIST_MAX} |

✅ **Verdict:** PASS (0×500)

---

### Test 2: /v1/actions/execute (READ variant)

**Results:**

| Metric | Value |
|--------|-------|
| Total Requests | {EXECUTE_CONCURRENCY} |
| Status 200 | {EXECUTE_200_COUNT} |
| Status 4xx | {EXECUTE_4XX_COUNT} |
| Status 5xx | **{EXECUTE_5XX_COUNT}** |
| Success Rate | {EXECUTE_SUCCESS_RATE}% |

**Latencies:**

| Percentile | Latency (ms) |
|------------|--------------|
| P50 (median) | {EXECUTE_P50} |
| P95 | {EXECUTE_P95} |
| P99 | {EXECUTE_P99} |
| Min | {EXECUTE_MIN} |
| Max | {EXECUTE_MAX} |

✅ **Verdict:** PASS (0×500)

**Note on 404 Responses:**
- 404 is the **correct** response for non-existent entity IDs (stress testing uses fake IDs)
- This proves error handling is working (not 500)
- In production, valid IDs would return 200

---

### Overall Stress Verdict

**Total Requests:** {TOTAL_STRESS_REQUESTS}
**Total 5xx Errors:** **{TOTAL_5XX_COUNT}**

✅ **PASS:** 0×500 across all requests (hard requirement met)

**Citation:**
> /Volumes/Backup/CELESTE/testing_success_ci:cd.md:708
> "Success rate, P95 latencies, 0×500 requirement" - Verdict: PASS if 0×500

---

## 3. Feature Flags Evidence

**Purpose:** Prove fail-closed behavior (503 when OFF, 200 when ON)

**Flags:**
{FEATURE_FLAGS_LIST}

### Before Enablement (Flags OFF)

**Request:**
```http
POST /v1/actions/suggestions HTTP/1.1
Authorization: Bearer {jwt}
Content-Type: application/json

{"domain": "{DOMAIN}"}
```

**Response:**
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "error",
  "error_code": "FEATURE_DISABLED",
  "message": "{LENS_ID} lens is disabled (canary flag off)"
}
```

✅ **Fail-closed behavior confirmed:** 503 when flags OFF

---

### After Enablement (Flags ON)

**Request:**
```http
POST /v1/actions/suggestions HTTP/1.1
Authorization: Bearer {jwt}
Content-Type: application/json

{"domain": "{DOMAIN}"}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "actions": [
    {
      "action_id": "{ACTION_1}",
      "label": "{ACTION_1_LABEL}",
      "variant": "MUTATE",
      ...
    },
    ...
  ],
  "total_count": {ACTION_COUNT}
}
```

✅ **Feature enabled:** 200 OK with real actions

---

## 4. Notifications Idempotency Evidence (Optional)

**Purpose:** Prove UNIQUE constraint enforces single-row guarantee

**Table:** `pms_notifications`

**Constraint:**
```sql
CONSTRAINT unique_notification UNIQUE (yacht_id, user_id, idempotency_key)
```

### Test: Duplicate Insert

**Attempt 1:**
```sql
INSERT INTO pms_notifications (..., idempotency_key = 'test_key_123') ...
```
**Result:** 201 Created (row count: 1)

**Attempt 2 (duplicate):**
```sql
INSERT INTO pms_notifications (..., idempotency_key = 'test_key_123') ...
```
**Result:** 409 Conflict (PostgreSQL error 23505: duplicate key)

**Final Row Count:** 1 (idempotency verified)

✅ **Idempotency confirmed:** UNIQUE constraint rejects duplicates

---

## 5. Scripts Reference

See `verification_handoff/phase6/ALL_SCRIPTS_REFERENCE.md` for complete script documentation.

**Active Scripts:**
- `tools/ops/monitors/{LENS_ID}_health_worker.py` - Automated canary monitoring
- `tests/ci/{LENS_ID}_signed_flow_acceptance.py` - Signature validation tests
- `tests/stress/{LENS_ID}_actions_endpoints.py` - 0×500 verification

---

## 6. Rollout Readiness

✅ **All blocking requirements met:**
- Signature validation: strict enforcement (400/400/403/200)
- Stress testing: 0×500 across {TOTAL_STRESS_REQUESTS} requests
- Feature flags: fail-closed behavior confirmed
- Notifications: idempotency enforced (if applicable)

✅ **Evidence artifacts:**
- Full HTTP transcripts (sanitized JWTs)
- Status code verification
- Latency percentiles (P50/P95/P99)
- Before/after DB queries

✅ **Ready for Phase 1 (Staging Canary):**
- Enable feature flags on canary service
- Monitor for 24h (automated via health worker)
- If green, proceed to Phase 2 (Staging Full)

---

## Appendix: Testing Doctrine

All tests in this evidence package adhere to CelesteOS testing doctrine:

1. **Expected 4xx is success (when asserted)**
   - Role denial 403 (CREW): `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:799`

2. **500 is always failure**
   - Hard requirement: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:249`

3. **Evidence artifacts required**
   - Raw transcripts: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:815`

4. **Verdict thresholds**
   - P50/P95/P99, 0×500: `/Volumes/Backup/CELESTE/testing_success_ci:cd.md:708`

---

**Last Updated:** {DATE}
**Reviewed By:** {REVIEWER}
**Status:** {STATUS} (Ready for Canary / In Progress / Blocked)
