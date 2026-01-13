# CelesteOS Production Risks Assessment

**Date:** 2026-01-12
**Assessment Type:** End-to-End Pipeline Analysis
**Severity Scale:** CRITICAL > HIGH > MEDIUM > LOW

---

## CRITICAL RISKS

### RISK-001: IntentParser GPT Fallback Broken
**Severity:** CRITICAL
**Component:** `intent_parser.py`
**Impact:** 93% of user queries route to no handler

**Evidence:**
- 14/15 E2E test queries resulted in "NO HANDLER"
- IntentParser returns `find_document` with confidence=0.50 for most queries
- Confidence=0.50 indicates keyword fallback, not GPT parsing

**Example:**
```
Query: "diagnose E047 on main engine"
IntentParser: find_document (WRONG)
Module A:     diagnose_fault (CORRECT)
```

**Root Cause:**
- GPT-4o-mini not returning valid intent
- Keyword fallback defaults to `find_document` for ambiguous queries
- Handler routing depends ONLY on IntentParser, ignoring Module A

**Remediation:**
1. Add Module A (ActionDetector) results to routing decision
2. Tune GPT prompts in IntentParser
3. Improve keyword fallback specificity

---

### RISK-002: Handler Routing Ignores Module A
**Severity:** CRITICAL
**Component:** Handler routing logic (not centralized)
**Impact:** Accurate action detection is unused

**Evidence:**
- Module A correctly detected actions with 0.93-0.95 confidence
- Handler routing does not use Module A results
- Only IntentParser intent is checked for routing

**Example:**
```
Query: "open work order for generator maintenance"
Module A: create_work_order (0.95 confidence) - CORRECT
IntentParser: find_document - WRONG
Handler: None - NO ROUTING
```

**Remediation:**
1. Create unified routing that combines IntentParser + Module A
2. Use highest confidence signal for routing
3. Fallback chain: Module A (strict) > IntentParser > keyword fallback

---

### RISK-003: Mutation Actions Not Gated
**Severity:** CRITICAL
**Component:** Handler execution flow
**Impact:** Write operations could execute without confirmation

**Evidence:**
- E2E harness found no mutation gating in place
- Queries like "acknowledge the fault" have no confirmation flow
- n8n webhook routing not connected for P0/P1 mutations

**Affected Actions:**
- create_work_order
- acknowledge_fault
- add_fault_note
- add_work_order_note
- log_hours_of_rest
- order_parts

**Remediation:**
1. Route all mutation intents through n8n webhook
2. Implement confirmation dialog before execution
3. Add mutation audit logging

---

## HIGH RISKS

### RISK-004: No RAG Search for Entity-Only Queries
**Severity:** HIGH
**Component:** Pipeline orchestration
**Impact:** Users get no results for valid searches

**Evidence:**
- Query "MTU 16V4000 engine overheating" extracts entities but returns no handler
- Entity-only queries should trigger document/knowledge search
- No RAG pipeline integration observed in E2E testing

**Expected Behavior:**
```
Query: "MTU 16V4000 engine overheating"
Entities: brand:MTU, model:16V4000, symptom:ENGINE_OVERHEATING
Expected: Search documents/manuals for MTU 16V4000 overheating solutions
Actual: No handler, no response
```

**Remediation:**
1. Add search handler for entity-only queries
2. Connect RAG pipeline for document retrieval
3. Return relevant manual sections based on entities

---

### RISK-005: Situation Engine Not Triggered
**Severity:** HIGH
**Component:** `situation_engine.py`
**Impact:** Pattern detection (RECURRENT_SYMPTOM) not running

**Evidence:**
- SituationEngine has pattern detection for recurrent faults
- E2E tests show situations not being checked
- Role-aware recommendations not generated

**Remediation:**
1. Integrate SituationEngine into pipeline flow
2. Check for patterns after entity extraction
3. Add situation context to response payload

---

### RISK-006: Frontend Contract Undefined
**Severity:** HIGH
**Component:** Response formatting
**Impact:** Frontend may receive inconsistent payloads

**Evidence:**
- No canonical response schema documented
- Handler responses vary in structure
- Microaction payload format not standardized

**Remediation:**
1. Define canonical response schema
2. Add response validation before sending
3. Document frontend contract (see `frontend_contract_report.json`)

---

## MEDIUM RISKS

### RISK-007: GPT API Key Not Validated
**Severity:** MEDIUM
**Component:** `intent_parser.py`
**Impact:** Silent failure if API key invalid/expired

**Evidence:**
- IntentParser loads but GPT calls may be failing silently
- Fallback to keyword parsing masks API failures
- No API key validation at startup

**Remediation:**
1. Add API key validation on init
2. Log GPT API failures explicitly
3. Add health check endpoint for GPT connectivity

---

### RISK-008: Test Data Dependency
**Severity:** MEDIUM
**Component:** E2E test harness
**Impact:** Tests may fail on fresh database

**Evidence:**
- Tests depend on pre-existing data in database
- test_ids fetched at runtime
- No data seeding for consistent testing

**Remediation:**
1. Add test data seeding scripts
2. Use deterministic UUIDs for test entities
3. Clean up test data after runs

---

### RISK-009: Latency Not Monitored
**Severity:** MEDIUM
**Component:** Pipeline execution
**Impact:** Performance degradation undetected

**Evidence:**
- E2E tests show 62-499ms latency per query
- No latency thresholds or alerting
- GPT calls add variable latency

**Remediation:**
1. Add latency metrics collection
2. Set alerting thresholds
3. Add circuit breaker for slow GPT calls

---

## LOW RISKS

### RISK-010: Verbose Pattern Loading Logs
**Severity:** LOW
**Component:** `module_b_entity_extractor.py`
**Impact:** Noisy logs in production

**Evidence:**
```
Loaded 42,340 terms from 1330 equipment patterns
   - 1,128 core brands
   - 140 core equipment types
   ...
```

**Remediation:**
1. Move verbose logging to DEBUG level
2. Add LOG_LEVEL configuration

---

## Summary

| Severity | Count | Resolved |
|----------|-------|----------|
| CRITICAL | 3     | 0        |
| HIGH     | 3     | 0        |
| MEDIUM   | 3     | 0        |
| LOW      | 1     | 0        |
| **TOTAL**| **10**| **0**    |

---

## Recommended Priority Order

1. **RISK-001 + RISK-002:** Fix routing to use Module A results (same fix)
2. **RISK-003:** Add mutation gating (safety critical)
3. **RISK-004:** Add RAG search for entity queries (user experience)
4. **RISK-005:** Integrate SituationEngine (value-add)
5. **RISK-006:** Define frontend contract (stability)

---

## Test Coverage Status

| Component | Handler Tests | E2E Tests | Status |
|-----------|---------------|-----------|--------|
| P0 Handlers | Not in scope | Not tested | UNKNOWN |
| P1 Handlers | Not in scope | Not tested | UNKNOWN |
| P2 Handlers | 20/20 PASS | 0 routed | INCOMPLETE |
| P3 Handlers | 30/30 PASS | 1 routed | INCOMPLETE |
| Situations | 10/10 PASS | 0 routed | INCOMPLETE |
| IntentParser | N/A | 2/15 correct | FAILING |
| Module A | N/A | 6/6 correct | PASSING |
| Module B | N/A | 10/15 extracted | PASSING |
| RAG Pipeline | N/A | 0 tested | NOT INTEGRATED |

---

## Conclusion

**Handler isolation tests: 81/81 PASS**
**End-to-end pipeline tests: 1/15 SUCCESS**

The handlers work correctly in isolation, but the orchestration layer (intent parsing -> routing -> handler selection) is broken. Module A (verb-based action detection) is accurate but unused for routing. IntentParser (GPT-based) is defaulting to fallback mode.

**Production deployment risk: HIGH**

The system will not respond correctly to most user queries until routing is fixed.
