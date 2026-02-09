# Parts Lens - Complete Test Suite & System Proof
## 6-Hour Comprehensive Testing & Validation

**Started:** Mon 9 Feb 2026 14:45 EST
**Deployment:** v2026.02.09.003 (commit: 4eb1cf6)
**Scope:** Parts Lens end-to-end validation, all journeys, all failure modes

---

## TEST EXECUTION STATUS

### ❌ BLOCKER: Test User Credentials Invalid

**Issue:** Password "Password2!" rejected by Supabase Auth

```
Sign in failed for captain.tenant@alex-short.com: HTTP 400
{"code":400,"error_code":"invalid_credentials","msg":"Invalid login credentials"}
```

**Impact:** Cannot test authenticated endpoints without valid credentials

**Options:**
1. Get correct passwords from user
2. Test with API tokens directly (if available)
3. Test unauthenticated endpoints only
4. Create comprehensive test framework for when credentials available

**Decision:** Proceed with comprehensive test framework + unauthenticated tests

---

## PARTS LENS COMPLETE TEST MATRIX

### 1. IMAGE UPLOAD ENDPOINTS

#### 1.1 POST /v1/parts/upload-image (Success Cases)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| Valid upload PNG | POST | Captain JWT | 100KB PNG, valid part_id | 200 + image_url | ⏳ BLOCKED |
| Valid upload JPEG | POST | Captain JWT | 500KB JPEG, valid part_id | 200 + image_url | ⏳ BLOCKED |
| Valid upload WebP | POST | HOD JWT | 200KB WebP, valid part_id | 200 + image_url | ⏳ BLOCKED |
| With description | POST | Captain JWT | PNG + description | 200 + metadata saved | ⏳ BLOCKED |
| With tags | POST | Captain JWT | PNG + tags array | 200 + tags saved | ⏳ BLOCKED |
| Overwrite existing | POST | Captain JWT | Upload to part with image | 200 + replaces old | ⏳ BLOCKED |

#### 1.2 POST /v1/parts/upload-image (Failure Cases)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| No auth | POST | None | Valid file | 401 Unauthorized | ✅ Can test |
| Expired JWT | POST | Expired token | Valid file | 401 Expired | ✅ Can test |
| Wrong yacht | POST | Valid JWT | part_id from different yacht | 403 Forbidden | ⏳ BLOCKED |
| Invalid part_id | POST | Valid JWT | Non-existent part_id | 404 Not Found | ⏳ BLOCKED |
| Invalid MIME | POST | Valid JWT | .txt file as image/png | 400 Bad Request | ⏳ BLOCKED |
| File too large | POST | Valid JWT | 100MB file | 413 Payload Too Large | ⏳ BLOCKED |
| Missing part_id | POST | Valid JWT | File but no part_id | 400 Bad Request | ✅ Can test |
| Missing file | POST | Valid JWT | part_id but no file | 400 Bad Request | ✅ Can test |
| Storage failure | POST | Valid JWT | (simulate storage down) | 500 Storage Error | 🔧 Need mock |

#### 1.3 POST /v1/parts/update-image (Success Cases)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| Update description | POST | HOD JWT | image_id + new description | 200 + updated | ⏳ BLOCKED |
| Clear description | POST | HOD JWT | image_id + empty description | 200 + cleared | ⏳ BLOCKED |
| Update tags | POST | Captain JWT | image_id + new tags | 200 + updated | ⏳ BLOCKED |

#### 1.4 POST /v1/parts/update-image (Failure Cases)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| No auth | POST | None | Valid image_id | 401 Unauthorized | ✅ Can test |
| No image exists | POST | Valid JWT | part with no image | 404 No image | ⏳ BLOCKED |
| Invalid image_id | POST | Valid JWT | Non-existent image_id | 404 Not Found | ⏳ BLOCKED |

#### 1.5 POST /v1/parts/delete-image (Success Cases - SIGNED)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| Valid delete | POST | Captain JWT | image_id + signature | 200 + deleted | ⏳ BLOCKED |
| With reason | POST | Captain JWT | image_id + signature + reason | 200 + audit logged | ⏳ BLOCKED |

#### 1.6 POST /v1/parts/delete-image (Failure Cases)

| Test Case | Method | Auth | Input | Expected | Status |
|-----------|--------|------|-------|----------|--------|
| No auth | POST | None | Valid image_id | 401 Unauthorized | ✅ Can test |
| Missing signature | POST | Captain JWT | image_id without signature | 400 Signature required | ⏳ BLOCKED |
| Wrong role | POST | Crew JWT | image_id + signature | 403 Forbidden | ⏳ BLOCKED |
| Invalid PIN | POST | Captain JWT | wrong PIN in signature | 401 Invalid signature | ⏳ BLOCKED |

---

### 2. NLP SEARCH / DOMAIN DETECTION

#### 2.1 Parts Domain Detection (Success Cases)

| Test Case | Query | Expected Domain | Expected Confidence | Status |
|-----------|-------|----------------|-------------------|--------|
| Brand + part | "caterpillar filter" | parts | 0.9 | ✅ Can test |
| Part number | "part number CAT-12345" | parts | 0.9 | ✅ Can test |
| Spare parts | "spare parts inventory" | parts | 0.9 | ✅ Can test |
| Low stock | "low stock items" | parts | 0.9 | ✅ Can test |
| **Marine teak** | "teak seam compound" | parts | 0.9 | ✅ Can test |
| **Marine antifouling** | "antifouling paint" | parts | 0.9 | ✅ Can test |
| **Marine sealant** | "sikaflex sealant" | parts | 0.9 | ✅ Can test |
| **Generic compound** | "deck compound" | parts | 0.9 | ✅ Can test |
| Filter type | "oil filter replacement" | parts | 0.9 | ✅ Can test |
| Bearing query | "main bearing inspection" | parts | 0.9 | ✅ Can test |

#### 2.2 Domain Detection (Failure/Edge Cases)

| Test Case | Query | Expected Domain | Expected Confidence | Status |
|-----------|-------|----------------|-------------------|--------|
| Vague query | "check something" | None (explore) | <0.6 | ✅ Can test |
| Ambiguous | "work on deck" | None or work_order | 0.6-0.7 | ✅ Can test |
| Empty query | "" | None | None | ✅ Can test |
| Only numbers | "12345" | None | None | ✅ Can test |
| Very long query | (500 chars) | varies | varies | ✅ Can test |

#### 2.3 Intent Detection

| Test Case | Query | Expected Intent | Expected Confidence | Status |
|-----------|-------|----------------|-------------------|--------|
| Question | "what parts are low stock?" | READ | 0.85 | ✅ Can test |
| Create action | "add new part to inventory" | CREATE | 0.85 | ✅ Can test |
| Update action | "update part quantity" | UPDATE | 0.85 | ✅ Can test |
| Status adjective | "accepted parts delivery" | READ | 0.95 | ✅ Can test |

---

### 3. RBAC / PERMISSIONS

#### 3.1 Work Order Creation (Crew RBAC Fix - PR #194)

| Test Case | Role | Department | WO Department | Expected | Status |
|-----------|------|------------|---------------|----------|--------|
| Crew creates DECK WO | crew | deck | deck | 200 Created | ⏳ BLOCKED |
| Crew creates ENG WO | crew | deck | engineering | 403 Forbidden | ⏳ BLOCKED |
| Crew no department | crew | NULL | deck | 403 No department | ⏳ BLOCKED |
| HOD creates any WO | chief_engineer | engineering | deck | 200 Created | ⏳ BLOCKED |
| Captain creates any WO | captain | NULL | any | 200 Created | ⏳ BLOCKED |

#### 3.2 Part Operations by Role

| Operation | Crew | Engineer | Chief_Engineer | Captain | Expected Status |
|-----------|------|----------|----------------|---------|----------------|
| view_part_details | ✅ | ✅ | ✅ | ✅ | ⏳ BLOCKED |
| upload_image | ❌ | ❌ | ✅ | ✅ | ⏳ BLOCKED |
| update_image | ❌ | ❌ | ✅ | ✅ | ⏳ BLOCKED |
| delete_image (SIGNED) | ❌ | ❌ | ❌ | ✅ | ⏳ BLOCKED |
| consume_part | ❌ | ✅ | ✅ | ✅ | ⏳ BLOCKED |
| adjust_stock (SIGNED) | ❌ | ❌ | ❌ | ✅ | ⏳ BLOCKED |

---

### 4. DATA VALIDATION & CONSTRAINTS

#### 4.1 Part Existence

| Test Case | part_id | yacht_id | Expected | Status |
|-----------|---------|----------|----------|--------|
| Valid part | TEAK_COMPOUND | correct yacht | Found | ⏳ BLOCKED |
| Wrong yacht | TEAK_COMPOUND | different yacht | 403/404 | ⏳ BLOCKED |
| Non-existent | invalid-uuid | correct yacht | 404 | ⏳ BLOCKED |
| Malformed UUID | "not-a-uuid" | correct yacht | 400 | ✅ Can test |

#### 4.2 MIME Type Validation

| Test Case | MIME Type | Expected | Status |
|-----------|-----------|----------|--------|
| image/png | Valid | 200 | ⏳ BLOCKED |
| image/jpeg | Valid | 200 | ⏳ BLOCKED |
| image/gif | Valid | 200 | ⏳ BLOCKED |
| image/webp | Valid | 200 | ⏳ BLOCKED |
| image/svg+xml | Invalid | 400 | ⏳ BLOCKED |
| application/pdf | Invalid | 400 | ⏳ BLOCKED |
| text/plain | Invalid | 400 | ⏳ BLOCKED |

---

### 5. STORAGE INTEGRATION

#### 5.1 Supabase Storage

| Test Case | Bucket | Path Template | Expected | Status |
|-----------|--------|---------------|----------|--------|
| Bucket exists | pms-part-photos | - | Confirmed | ✅ VERIFIED |
| Upload permission | pms-part-photos | {yacht_id}/parts/{part_id}/images/* | Allowed | ⏳ BLOCKED |
| Path isolation | pms-part-photos | yacht_id enforced | Verified | ⏳ BLOCKED |
| Public URL generation | pms-part-photos | get_public_url() works | URL returned | ⏳ BLOCKED |
| Timestamp naming | pms-part-photos | {timestamp}_{filename} | No collisions | ⏳ BLOCKED |

---

### 6. DATABASE OPERATIONS

#### 6.1 pms_parts Table Updates

| Test Case | Operation | Fields Updated | Expected | Status |
|-----------|-----------|----------------|----------|--------|
| Image upload | UPDATE | image_file_name, image_storage_path, image_bucket, image_mime_type, image_uploaded_at, image_uploaded_by | Success | ⏳ BLOCKED |
| Image update | UPDATE | image_description | Success | ⏳ BLOCKED |
| Image delete | UPDATE | All image_* fields NULL | Success | ⏳ BLOCKED |

#### 6.2 Audit Logging

| Test Case | Action | Signature | Expected | Status |
|-----------|--------|-----------|----------|--------|
| Upload image | upload_part_image | {} (non-signed) | Logged | ⏳ BLOCKED |
| Update image | update_part_image | {} (non-signed) | Logged | ⏳ BLOCKED |
| Delete image | delete_part_image | {pin, totp, role, ...} (SIGNED) | Logged with full signature | ⏳ BLOCKED |

---

### 7. IDEMPOTENCY & CONCURRENCY

#### 7.1 Work Order Idempotency

| Test Case | Scenario | Expected | Status |
|-----------|----------|----------|--------|
| Duplicate payload | Same title, dept, priority | 409 Conflict | ⏳ BLOCKED |
| Unique UUID | Different UUID each time | 200 Created | ⏳ BLOCKED |
| Expired idempotency | Same payload after 1 hour | 200 Created (new) | ⏳ BLOCKED |

#### 7.2 Concurrent Image Operations

| Test Case | Scenario | Expected | Status |
|-----------|----------|----------|--------|
| Simultaneous upload | 2 users upload to same part | Last write wins | ⏳ BLOCKED |
| Upload during update | Upload while update in progress | Both succeed | ⏳ BLOCKED |
| Delete during view | Delete while another user views | View gets old data or 404 | ⏳ BLOCKED |

---

### 8. ERROR HANDLING & EDGE CASES

#### 8.1 JWT Edge Cases

| Test Case | JWT Status | Expected | Status |
|-----------|-----------|----------|--------|
| Valid token | Active, not expired | 200 | ⏳ BLOCKED |
| Expired token | exp < now | 401 Expired | ✅ Can test |
| Invalid signature | Wrong secret | 401 Invalid | ✅ Can test |
| Malformed token | Not proper JWT format | 401 Malformed | ✅ Can test |
| Missing Bearer | No "Bearer " prefix | 401 Missing | ✅ Can test |
| Empty token | Bearer with empty string | 401 Empty | ✅ Can test |

#### 8.2 Network/Infrastructure Failures

| Test Case | Failure Type | Expected | Status |
|-----------|-------------|----------|--------|
| Database timeout | Query takes >30s | 504 Timeout | 🔧 Need mock |
| Storage unavailable | Supabase Storage down | 502 Bad Gateway | 🔧 Need mock |
| Tenant lookup fails | MASTER DB unavailable | 500 Tenant error | 🔧 Need mock |

---

## TEST IMPLEMENTATION PLAN

### Phase 1: Unauthenticated Tests (Can Run Now) ✅

```python
# Test 1: NLP Domain Detection (No Auth Required)
test_domain_detection_marine_parts()
test_domain_detection_edge_cases()
test_intent_detection()

# Test 2: API Error Responses (No Valid Auth)
test_upload_image_no_auth_401()
test_upload_image_invalid_jwt_401()
test_upload_image_malformed_jwt_400()
test_update_image_no_auth_401()
test_delete_image_no_auth_401()

# Test 3: Version/Health Endpoints
test_version_endpoint()
test_health_endpoint()

# Test 4: System Validation
run_validate_system_script()
```

### Phase 2: Authenticated Tests (Need Credentials) ⏳

```python
# Image Upload Success
test_upload_image_valid_png()
test_upload_image_valid_jpeg()
test_upload_image_with_description()
test_upload_image_overwrite()

# Image Upload Failures
test_upload_image_invalid_part_id()
test_upload_image_wrong_yacht()
test_upload_image_invalid_mime()
test_upload_image_file_too_large()

# Image Update
test_update_image_description()
test_update_image_no_image_exists()

# Image Delete (SIGNED)
test_delete_image_valid_signature()
test_delete_image_missing_signature()
test_delete_image_wrong_role()

# RBAC
test_crew_creates_deck_work_order()
test_crew_cannot_create_eng_work_order()
test_captain_deletes_image()
test_crew_cannot_delete_image()
```

### Phase 3: Integration Tests (Need Credentials) ⏳

```python
# Full Journeys
test_journey_upload_update_delete_cycle()
test_journey_search_upload_view()
test_journey_multiple_users_same_part()

# Concurrency
test_concurrent_upload_same_part()
test_concurrent_update_description()
```

---

## AUTOMATED TEST EXECUTION

### Tests Running Without Credentials

Creating test suite now...
