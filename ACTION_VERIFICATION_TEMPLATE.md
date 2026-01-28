# Action Verification Template

**Instructions for Engineers:**
1. Copy this template to `_VERIFICATION/{ACTION_NAME}_verification.md`
2. Reference the COMPLETE_ACTION_EXECUTION_CATALOG.md for expected behavior
3. Work through each section systematically
4. Mark items as you verify them
5. Document ALL findings (good and bad)

---

## Action Metadata

**Action ID:** `[action_name]`
**Date Started:** YYYY-MM-DD
**Date Completed:** [PENDING]
**Engineer:** [Your Name]
**Status:** 🔴 NOT STARTED | 🟡 IN PROGRESS | 🟢 COMPLETE

**Reference Documentation:**
- Catalog Entry: `_archive/misc/COMPLETE_ACTION_EXECUTION_CATALOG.md` (line: XXX)
- Handler Code: `apps/api/routes/p0_actions_routes.py` (line: XXX)
- Test Registry: `tests/fixtures/microaction_registry.ts` (line: XXX)

---

## 📋 VERIFICATION CHECKLIST

**Total Progress:** X/215 items (X%)

---

### 1️⃣ NATURAL LANGUAGE QUERY DETECTION (0/10)

**Reference:** Does user query correctly surface this action?

**Catalog Says:**
```
[Copy expected behavior from COMPLETE_ACTION_EXECUTION_CATALOG.md]
Example queries that should work:
- "..."
- "..."
```

#### Tests:

- [ ] **1.1** Direct command variations (10-20 queries)
  - **Test File:** `tests/e2e/nl_queries_{action_name}.spec.ts`
  - **Endpoint:** `POST /search`
  - **Expected:** Action in `actions[]` array with confidence > 0.8
  - **Status:** ⏳ PENDING | ✅ PASS | ❌ FAIL
  - **Notes:**
    ```
    [Document what you found]
    ```

- [ ] **1.2** Equipment-specific queries (if applicable)
  - **Query Example:** "create work order for generator"
  - **Expected:** Equipment ID extracted and populated
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.3** Fault-related queries (if applicable)
  - **Query Example:** "generator broken, make work order"
  - **Expected:** Fault context detected
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.4** Scheduled/PM queries (if applicable)
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **1.5** Negative cases (irrelevant queries)
  - **Query Example:** "show me weather"
  - **Expected:** This action NOT suggested
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.6** Response structure validation
  - **Expected Schema:**
    ```json
    {
      "actions": [{
        "action": "action_name",
        "label": "...",
        "confidence": 0.95,
        "payload_template": { ... }
      }]
    }
    ```
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.7** Typo/variation handling
  - **Examples:** "creat work order", "wo"
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.8** Multi-intent queries
  - **Example:** "generator broken, create wo and notify engineer"
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.9** Performance check
  - **Expected:** < 2 seconds
  - **Actual:** ___ ms
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **1.10** All NL tests documented and passing
  - **Test Suite Status:** ⏳ | ✅ | ❌
  - **Pass Rate:** X/X
  - **Notes:**

**Section Notes:**
```
[Document overall findings for NL detection]
```

---

### 2️⃣ FRONTEND CUSTOMER JOURNEY (0/12)

**Reference:** Can user complete action end-to-end in UI?

**Catalog Says:**
```
[Copy expected UI flow from catalog]
```

#### Tests:

- [ ] **2.1** Search → Action Button appears
  - **User Flow:** Type query → see button
  - **Status:** ⏳ | ✅ | ❌
  - **Screenshot:** [path or attach]
  - **Notes:**

- [ ] **2.2** Button Click → Form/Modal opens
  - **Pre-filled Fields:** [list expected]
  - **Status:** ⏳ | ✅ | ❌
  - **Screenshot:**
  - **Notes:**

- [ ] **2.3** Form validation (client-side)
  - **Required Fields:** [list]
  - **Validation Messages:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.4** Form submission → Loading state
  - **Button Behavior:** Shows spinner, disables
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.5** Success response → Confirmation
  - **Expected Message:** "..."
  - **Entity ID Shown:** Yes/No
  - **Status:** ⏳ | ✅ | ❌
  - **Screenshot:**
  - **Notes:**

- [ ] **2.6** Error response → User-friendly message
  - **400 Error Test:** [document]
  - **403 Error Test:** [document]
  - **500 Error Test:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.7** Follow-up actions suggested
  - **Expected Suggestions:** [list]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.8** Mobile responsive
  - **Tested On:** iPhone/Android
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.9** Accessibility
  - **Keyboard Nav:** Works/Broken
  - **Screen Reader:** Tested/Not Tested
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **2.10** Deep link support
  - **URL Format:** `/actions/{action_name}?param=value`
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **2.11** State persistence
  - **Draft Saved:** Yes/No
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **2.12** E2E Playwright test
  - **Test File:** `tests/e2e/journey_{action_name}.spec.ts`
  - **Status:** ⏳ | ✅ | ❌
  - **Pass Rate:** X/X
  - **Notes:**

**Section Notes:**
```
[Document overall findings for frontend journey]
```

---

### 3️⃣ BACKEND EXECUTION (0/15)

**Reference:** Does handler execute correctly?

**Catalog Says:**
```
[Copy handler spec from catalog:
- Tables Affected
- Row Operations
- Required Inputs
- Validation Rules]
```

#### Tests:

- [ ] **3.1** Handler exists and registered
  - **File:** `apps/api/routes/p0_actions_routes.py`
  - **Line Number:** XXX
  - **Action Aliases:** [e.g., "create_work_order", "create_wo"]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.2** Required field validation
  - **Catalog Says Required:** [list from catalog]
  - **Handler Validates:** [list from code]
  - **Match:** ✅ YES | ❌ NO
  - **Status:** ⏳ | ✅ | ❌
  - **Test Result:**
    ```bash
    # Missing required field
    curl -X POST /v1/actions/execute -d '{"action":"..."}'
    # Expected: 400 "Missing required field: X"
    # Actual: [document]
    ```
  - **Notes:**

- [ ] **3.3** Optional field handling
  - **Catalog Says Optional:** [list]
  - **Handler Defaults:** [document defaults]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.4** Field sanitization
  - **HTML in title:** `<script>alert('xss')</script>`
  - **Expected:** Stripped/Escaped
  - **Actual:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.5** Business logic validation
  - **Catalog Says:** [copy validation rules]
  - **Tested:**
    ```
    [Document test cases]
    ```
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.6** Authentication check
  - **No token:** Expected 401
  - **Expired token:** Expected 401
  - **Invalid token:** Expected 401
  - **Status:** ⏳ | ✅ | ❌
  - **Test Result:**

- [ ] **3.7** Authorization check (RBAC)
  - **Catalog Says Allowed Roles:** [list from catalog]
  - **Tested With:**
    - Engineer: ✅ | ❌
    - Captain: ✅ | ❌
    - Crew: ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.8** Yacht isolation (RLS)
  - **All queries include yacht_id:** ✅ | ❌
  - **Cross-yacht test:** [document result]
  - **Status:** ⏳ | ✅ | ❌
  - **Code Review:**
    ```python
    # Line XXX in handler:
    [paste relevant code]
    ```

- [ ] **3.9** Tenant routing
  - **tenant_key_alias resolved:** ✅ | ❌
  - **Correct DB client used:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.10** Error handling
  - **Try/catch exists:** ✅ | ❌
  - **Specific error messages:** ✅ | ❌
  - **Logs errors:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Code Review:**

- [ ] **3.11** Response format
  - **Expected Schema:**
    ```json
    {
      "status": "success",
      "result_id": "uuid",  // or action-specific field
      "message": "..."
    }
    ```
  - **Actual Schema:** [document]
  - **Match:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.12** Rate limiting
  - **Limit:** 30/min
  - **Test:** Made 31 requests in 60s
  - **Result:** Request #31 → 429
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.13** Request timeout
  - **Completes in:** ___ ms
  - **Expected:** < 5000ms
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **3.14** Idempotency (if applicable)
  - **Same request twice:** Creates duplicate? Yes/No
  - **Expected Behavior:** [document]
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **3.15** Handler unit test exists
  - **Test File:** `tests/unit/handlers/test_{action_name}.py`
  - **Exists:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

**Section Notes:**
```
[Document overall findings for backend execution]
```

---

### 4️⃣ DATABASE MUTATIONS (0/15)

**⚠️ CRITICAL:** HTTP 200 ≠ Verified Success

**You MUST verify actual database changes, not just HTTP status.**

**Catalog Says:**
```
Tables Affected:
[Copy from catalog]

Row Operations:
[Copy INSERT/UPDATE/DELETE statements]

Columns Modified:
[Copy column list]
```

#### Database Verification Steps:

- [ ] **4.1** Query BEFORE action
  - **SQL Query:**
    ```sql
    -- Before executing action
    SELECT * FROM [table_name] WHERE id = '[expected_id]';
    ```
  - **Result:** [paste or describe]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.2** Execute action via API
  - **Request:**
    ```bash
    curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "action": "action_name",
        "context": {"yacht_id": "...", "user_id": "..."},
        "payload": {...}
      }'
    ```
  - **HTTP Status:** ___ (e.g., 200)
  - **Response Body:** [paste]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.3** Query AFTER action
  - **SQL Query:**
    ```sql
    -- After executing action
    SELECT * FROM [table_name] WHERE id = '[entity_id_from_response]';
    ```
  - **Result:** [paste full row]
  - **Row Exists:** ✅ YES | ❌ NO
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.4** Cross-check: Catalog vs. Reality
  - **Catalog Says Table:** `[table_name]`
  - **Actually Written To:** `[actual_table_name]`
  - **Match:** ✅ | ❌

  - **Catalog Says Columns:** `[col1, col2, col3]`
  - **Actually Modified:** `[actual_columns]`
  - **Match:** ✅ | ❌

  - **Status:** ⏳ | ✅ | ❌
  - **Discrepancies:**
    ```
    [Document any differences]
    ```

- [ ] **4.5** Required fields populated
  - **yacht_id:** Present ✅ | Missing ❌
  - **created_by:** Present ✅ | Missing ❌
  - **created_at:** Present ✅ | Missing ❌
  - **[other required]:** [check each]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.6** Optional fields handled
  - **Catalog Says:** `description` defaults to ""
  - **Actual:** `description = "..."` or NULL
  - **Match:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.7** Default values applied
  - **Catalog Says:** `status = "planned"`
  - **Actual:** `status = "..."`
  - **Match:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **All Defaults:**
    ```
    [List expected vs actual defaults]
    ```

- [ ] **4.8** Field transformations
  - **Input:** `priority: "medium"`
  - **Stored:** `priority: "routine"` (example)
  - **Documented:** ✅ | ❌
  - **Expected:** ✅ | ❌ Unexpected
  - **Status:** ⏳ | ✅ | ❌
  - **All Transformations:**
    ```
    [Document all input → storage transformations]
    ```

- [ ] **4.9** Foreign key relationships
  - **equipment_id references pms_equipment.id:** ✅ | ❌
  - **Constraint enforced:** ✅ | ❌
  - **Test:** Try invalid FK → Expected: 400 or FK violation
  - **Result:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.10** Indexes used efficiently
  - **EXPLAIN ANALYZE:**
    ```sql
    EXPLAIN ANALYZE
    SELECT * FROM [table] WHERE yacht_id = '...' AND ...;
    ```
  - **Uses Index:** ✅ | ❌
  - **Execution Time:** ___ ms
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.11** Soft delete support
  - **deleted_at initially NULL:** ✅ | ❌
  - **Hard DELETE blocked:** ✅ | ❌
  - **Test Result:**
    ```sql
    DELETE FROM [table] WHERE id = '...';
    -- Expected: Error "Hard deletes not allowed"
    -- Actual: [document]
    ```
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.12** Concurrent access
  - **Test:** 2 users create at same time
  - **Result:** Both succeed? Race condition?
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.13** Read after write consistency
  - **Created entity immediately queryable:** ✅ | ❌
  - **Test:** Query 1ms after creation
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.14** Transaction boundaries
  - **Main mutation + audit log = atomic:** ✅ | ❌
  - **If audit fails, main rolled back:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **4.15** Mutation test passing
  - **Test File:** `tests/e2e/mutation_proof_{action_name}.spec.ts`
  - **Test Status:** ⏳ | ✅ | ❌
  - **Verifies:**
    - [ ] Query BEFORE
    - [ ] Execute action
    - [ ] Query AFTER
    - [ ] Assert row exists
    - [ ] Assert values correct
  - **Pass Rate:** X/X
  - **Notes:**

**Section Notes:**
```
⚠️ CRITICAL DISTINCTION:
- HTTP 200 = Handler didn't crash
- Verified Success = Database state changed as expected

Document BOTH:
1. HTTP response
2. Actual database state
```

---

### 5️⃣ AUDIT TRAIL (0/12)

**⚠️ CRITICAL:** Audit log is NOT optional. It's required for compliance.

**Catalog Says:**
```
Audit Trail:
[Copy from catalog what should be audited]
```

#### Audit Verification Steps:

- [ ] **5.1** Audit log entry created
  - **Query:**
    ```sql
    SELECT * FROM pms_audit_log
    WHERE entity_id = '[entity_id_from_action]'
    AND action = '[action_name]'
    ORDER BY created_at DESC
    LIMIT 1;
    ```
  - **Entry Found:** ✅ YES | ❌ NO
  - **Status:** ⏳ | ✅ | ❌
  - **Result:** [paste full audit row]
  - **Notes:**

- [ ] **5.2** Audit entry fields populated
  - **action:** Correct ✅ | Wrong ❌
  - **entity_type:** Correct ✅ | Wrong ❌
  - **entity_id:** Correct ✅ | Wrong ❌
  - **yacht_id:** Correct ✅ | Wrong ❌
  - **user_id:** Correct ✅ | Wrong ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Full Audit Row:**
    ```json
    [Paste full audit log JSON]
    ```

- [ ] **5.3** old_values captured
  - **For CREATE:** Should be `{}`
  - **For UPDATE:** Should be previous values
  - **For DELETE:** Should be full entity
  - **Actual:** [document]
  - **Correct:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.4** new_values captured
  - **Contains all key fields:** ✅ | ❌
  - **No sensitive data leaked:** ✅ | ❌
  - **Structure:**
    ```json
    {
      "field1": "value1",
      "field2": "value2",
      ...
    }
    ```
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.5** signature metadata
  - **signature.user_id:** Present ✅ | Missing ❌
  - **signature.timestamp:** Present ✅ | Missing ❌
  - **signature.execution_id:** Present ✅ | Missing ❌
  - **signature.action:** Matches action name ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Example:**
    ```json
    {
      "signature": {
        "user_id": "...",
        "timestamp": "2026-01-22T...",
        "execution_id": "...",
        "action": "action_name"
      }
    }
    ```

- [ ] **5.6** Additional metadata (if applicable)
  - **metadata.source:** [e.g., "manual" vs "from_fault"]
  - **metadata.raw_priority:** [before transformation]
  - **metadata.[custom]:** [document]
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **5.7** Audit log queryable
  - **Query all actions for entity:**
    ```sql
    SELECT action, created_at, user_id
    FROM pms_audit_log
    WHERE entity_type = 'work_order'
    AND entity_id = '[id]'
    ORDER BY created_at;
    ```
  - **Returns full history:** ✅ | ❌
  - **Performance:** ___ ms
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.8** Audit log immutable
  - **Test: Try UPDATE:**
    ```sql
    UPDATE pms_audit_log SET action = 'hacked' WHERE id = '...';
    ```
  - **Expected:** Error "Not allowed"
  - **Actual:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.9** Audit in same transaction as mutation
  - **If main mutation fails → no audit:** ✅ | ❌
  - **If audit fails → main rolled back:** ✅ | ❌
  - **Test Result:** [document]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.10** Compliance ready
  - **Meets ISO 9001:** ✅ | ❌ | Unknown
  - **Meets SOLAS:** ✅ | ❌ | Unknown
  - **Can export for regulators:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.11** Compared with other actions
  - **Action A has audit:** ✅
  - **Action B has audit:** ✅
  - **THIS action has audit:** ✅ | ❌
  - **Consistent:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **5.12** Audit test passing
  - **Test:** Mutation proof includes audit verification
  - **Test passes:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

**Section Notes:**
```
⚠️ CRITICAL: If audit log is missing, action is NOT DONE.
This is a blocker for production.

Evidence Required:
1. Screenshot of SQL query showing audit row
2. Full audit JSON pasted above
3. Proof of immutability (UPDATE blocked)
```

---

### 6️⃣ NEGATIVE TESTING & ERROR VALIDATION (0/25)

**⚠️ CRITICAL:** Testing errors is as important as testing success.

**Remember:** 400/404/403 are NOT failures - they're expected behavior.

**Catalog Says:**
```
Validation Rules:
[Copy from catalog]
```

#### Error Response Tests:

- [ ] **6.1** HTTP Status Code Accuracy
  - **Test each scenario:**
    | Scenario | Expected Status | Actual Status | Pass |
    |----------|----------------|---------------|------|
    | Valid request | 200 | ___ | ✅/❌ |
    | Missing required field | 400 | ___ | ✅/❌ |
    | Invalid field type | 400 | ___ | ✅/❌ |
    | No auth token | 401 | ___ | ✅/❌ |
    | Expired token | 401 | ___ | ✅/❌ |
    | No permission | 403 | ___ | ✅/❌ |
    | Entity not found | 404 | ___ | ✅/❌ |
    | Duplicate | 409 | ___ | ✅/❌ |
    | Rate limit | 429 | ___ | ✅/❌ |
    | Server error | 500 | ___ | ✅/❌ |
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **6.2** 400 Error Response Structure
  - **Test: Missing title**
    ```bash
    curl -X POST ... -d '{"action":"...","payload":{}}'
    ```
  - **Expected:**
    ```json
    {
      "detail": "Missing required field: title",
      "error_code": "VALIDATION_FAILED",
      "field": "title",
      "status": 400
    }
    ```
  - **Actual:** [paste]
  - **Match:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **6.3-6.10** [All error code tests - document each]
  - **[Copy sections from full template]**
  - **Status:** ⏳ | ✅ | ❌
  - **Test Results:**

- [ ] **6.11** Error messages are helpful
  - **Example Bad:** "Bad request"
  - **Example Good:** "title must be at least 3 characters"
  - **This Action:** [paste actual error message]
  - **Rating:** ✅ Helpful | ⚠️ OK | ❌ Unhelpful
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **6.12** Error messages don't leak secrets
  - **Test: Invalid equipment_id from different yacht**
  - **Bad Response:** "Equipment belongs to yacht 'Competitor Name'"
  - **Good Response:** "Equipment not found"
  - **Actual:** [paste]
  - **Leaks Data:** ✅ NO | ❌ YES
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **6.13-6.25** [Remaining error tests]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

**Section Notes:**
```
⚠️ REMEMBER:
- 200 = Success
- 400 = Expected validation failure (NOT a bug)
- 404 = Expected not found (NOT a bug)
- 500 = Unexpected error (IS a bug)

All expected errors (400, 404, 403, 409) MUST be tested.
```

---

### 7️⃣ INTEGRATION & CHAINING (0/12)

**Reference:** Does this action work with other actions?

- [ ] **7.1** Chained action workflow
  - **Workflow:** [action_a] → [THIS action] → [action_c]
  - **Test Result:** [document]
  - **Status:** ⏳ | ✅ | ❌ | N/A
  - **Notes:**

- [ ] **7.2** Action from search context
  - **User Flow:** Search → Card → Button → Form
  - **Pre-filled Correctly:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **7.3-7.12** [Other integration tests]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

**Section Notes:**
```
[Document integration findings]
```

---

### 8️⃣ PERFORMANCE & SCALABILITY (0/8)

**Reference:** How fast is this action?

- [ ] **8.1** Response time p50 < 500ms
  - **Measured:** ___ ms
  - **Pass:** ✅ | ❌
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

- [ ] **8.2-8.8** [Other performance tests]
  - **Status:** ⏳ | ✅ | ❌
  - **Notes:**

**Section Notes:**
```
[Document performance findings]
```

---

### 9️⃣ DEPLOYMENT & CI/CD (0/10)

**Reference:** Does this work in all environments?

- [ ] **9.1** Works in local dev
- [ ] **9.2** Works on Render
- [ ] **9.3** Works on Vercel
- [ ] **9.4-9.10** [Other deployment checks]

**Section Notes:**
```
[Document deployment findings]
```

---

### 🔟 DOCUMENTATION (0/8)

**Reference:** Is this action documented?

- [ ] **10.1** API docs updated
- [ ] **10.2** Handler commented
- [ ] **10.3-10.8** [Other docs]

**Section Notes:**
```
[Document documentation findings]
```

---

## 🚨 CRITICAL FINDINGS

**Blockers (Must Fix Before DONE):**
1. [Issue description] - **Priority:** CRITICAL
2. [Issue description] - **Priority:** HIGH

**Issues Found (Not Blockers):**
1. [Issue description] - **Priority:** MEDIUM
2. [Issue description] - **Priority:** LOW

**Discrepancies Between Catalog and Reality:**
| What | Catalog Says | Reality Is | Impact |
|------|--------------|------------|--------|
| Table name | `faults` | `pms_faults` | Must update catalog |
| Column name | `current_quantity` | `quantity_on_hand` | Must update handler |
| Default value | `status: 'open'` | `status: 'planned'` | Document transformation |

---

## ✅ DEFINITION OF DONE FOR THIS ACTION

**Action is DONE when:**

- [ ] All 215 checklist items completed
- [ ] HTTP 200 returns on valid input
- [ ] HTTP 400/404/403 return on invalid input (with helpful messages)
- [ ] Database mutation verified (not just 200 status)
- [ ] Audit log entry verified (not just assumed)
- [ ] All tests passing in CI/CD
- [ ] No critical blockers
- [ ] Deployed and smoke tested in production
- [ ] Documentation complete

**Current Status:** X/215 (X%)

**Estimated Completion Date:** [DATE]

---

## 📝 ACTION-SPECIFIC NOTES

**Unique Characteristics:**
```
[Document anything special about this action:
- Unusual behavior
- Special business rules
- Known limitations
- Related actions
- Historical context]
```

**Lessons Learned:**
```
[After completing verification, document:
- What went well
- What was confusing
- What could be improved
- Tips for next engineer]
```

**Questions/Uncertainties:**
```
[Document anything you're unsure about:
- Ambiguous requirements
- Conflicting documentation
- Missing information
- Need stakeholder input]
```

---

## 📎 ATTACHMENTS

**Test Files Created:**
- [ ] `tests/e2e/nl_queries_{action_name}.spec.ts`
- [ ] `tests/e2e/mutation_proof_{action_name}.spec.ts`
- [ ] `tests/e2e/journey_{action_name}.spec.ts`
- [ ] `tests/e2e/negative_{action_name}.spec.ts`

**SQL Queries Run:**
```sql
-- BEFORE query
[Paste query and result]

-- AFTER query
[Paste query and result]

-- Audit query
[Paste query and result]
```

**Screenshots:**
- [ ] UI search results
- [ ] Action button
- [ ] Form/modal
- [ ] Success message
- [ ] Error message
- [ ] Database row
- [ ] Audit log entry

**API Requests/Responses:**
```bash
# Success case
curl ...
# Response: [paste]

# Error case
curl ...
# Response: [paste]
```

---

## 🔄 VERSION HISTORY

| Date | Engineer | Changes | Status |
|------|----------|---------|--------|
| YYYY-MM-DD | [Name] | Started verification | 0% |
| YYYY-MM-DD | [Name] | Completed section 1-5 | 50% |
| YYYY-MM-DD | [Name] | Completed all sections | 100% |

---

**Template Version:** 2.0
**Last Updated:** 2026-01-22
**Reference:** `COMPLETE_ACTION_EXECUTION_CATALOG.md` (6584 lines)
