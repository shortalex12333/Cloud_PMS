# Phase 11.1: Decision Engine Service - EVIDENCE

**Date:** 2026-01-21
**Status:** CODE COMPLETE (Pending Deployment)

---

## Deliverables

### 1. Decision Engine Service

**File:** `apps/api/services/decision_engine.py`

```
- Loads E017_TRIGGER_CONTRACTS.yaml at startup
- Loads E019_STATE_GUARDS.yaml at startup
- Implements E018 confidence scoring formula:
  confidence = (intent * 0.4) + (entity * 0.4) + (situation * 0.2)
- Tier-specific thresholds:
  - PRIMARY: 0.50
  - CONDITIONAL: 0.60
  - RARE: 0.70
- Returns ActionDecision[] with:
  - action, allowed, tier, confidence
  - reasons[], breakdown{intent, entity, situation}
  - blocked_by{type, detail} when blocked
  - explanation (from template)
```

### 2. API Endpoint

**File:** `apps/api/routes/decisions_routes.py`

```
POST /v1/decisions
  - Requires JWT authentication
  - Request: detected_intents[], entities[], situation{}, environment
  - Response: execution_id, decisions[], allowed_count, blocked_count, timing_ms

GET /v1/decisions/health
  - Returns trigger_contracts_loaded count, state_guards_loaded boolean
```

### 3. Router Registration

**File:** `apps/api/pipeline_service.py` (lines 198-208)

```python
try:
    from routes.decisions_routes import router as decisions_router
    app.include_router(decisions_router)
    logger.info("✅ Decision Engine routes registered at /v1/decisions/*")
except Exception as e:
    logger.error(f"❌ Failed to register Decision Engine routes: {e}")
```

---

## Unit Test Evidence

**File:** `apps/api/tests/test_decision_engine.py`
**Result:** 17/17 PASSED

```
tests/test_decision_engine.py::TestDecisionEngineInit::test_engine_loads_trigger_contracts PASSED
tests/test_decision_engine.py::TestDecisionEngineInit::test_engine_loads_state_guards PASSED
tests/test_decision_engine.py::TestConfidenceScoring::test_full_match_scores_high PASSED
tests/test_decision_engine.py::TestConfidenceScoring::test_no_intent_scores_low PASSED
tests/test_decision_engine.py::TestConfidenceScoring::test_confidence_formula_weights PASSED
tests/test_decision_engine.py::TestThresholdRejection::test_primary_threshold_0_50 PASSED
tests/test_decision_engine.py::TestThresholdRejection::test_conditional_threshold_0_60 PASSED
tests/test_decision_engine.py::TestThresholdRejection::test_rare_threshold_0_70 PASSED
tests/test_decision_engine.py::TestStateGuards::test_close_wo_requires_in_progress PASSED
tests/test_decision_engine.py::TestStateGuards::test_close_wo_allowed_when_in_progress PASSED
tests/test_decision_engine.py::TestStateGuards::test_start_wo_requires_open PASSED
tests/test_decision_engine.py::TestForbiddenContexts::test_create_wo_from_fault_blocked_when_fault_has_wo PASSED
tests/test_decision_engine.py::TestForbiddenContexts::test_cancel_wo_requires_hod PASSED
tests/test_decision_engine.py::TestForbiddenContexts::test_cancel_wo_allowed_for_hod PASSED
tests/test_decision_engine.py::TestEvaluateDecisionsEntryPoint::test_returns_execution_id PASSED
tests/test_decision_engine.py::TestEvaluateDecisionsEntryPoint::test_returns_decision_counts PASSED
tests/test_decision_engine.py::TestEvaluateDecisionsEntryPoint::test_decisions_have_required_fields PASSED
```

---

## Runtime Evidence

### evaluate_decisions() Output

```
EVIDENCE: evaluate_decisions() output
============================================================
execution_id: fc8fabe1-1f43-4dd0-8232-d2102154399e
allowed_count: 7
blocked_count: 23

ALLOWED ACTIONS (sample):
  create_work_order_from_fault
    tier: conditional, confidence: 0.88
    breakdown: intent=0.7, entity=1.0, situation=1.0
    reasons: ['Partial intent match: repair ~ schedule_repair', "All required entities with IDs: ['fault']"]

  add_to_handover
    tier: primary, confidence: 0.6
    breakdown: intent=0.0, entity=1.0, situation=1.0

  acknowledge_fault
    tier: conditional, confidence: 0.6
    breakdown: intent=0.0, entity=1.0, situation=1.0

BLOCKED ACTIONS (sample):
  add_note_to_work_order
    tier: primary, confidence: 0.0
    blocked_by: {'type': 'forbidden', 'detail': 'No work order selected'}

  create_work_order
    tier: conditional, confidence: 0.0
    blocked_by: {'type': 'forbidden', 'detail': 'No equipment selected'}
```

### Confidence Formula Verification

For `create_work_order_from_fault` with confidence 0.88:
- intent = 0.7 (partial match "repair" ~ "schedule_repair")
- entity = 1.0 (fault ID confirmed)
- situation = 1.0 (no work order exists yet)

**Formula:** (0.7 * 0.4) + (1.0 * 0.4) + (1.0 * 0.2) = 0.28 + 0.40 + 0.20 = **0.88** ✓

---

## Route Import Verification

```
Testing route imports...
✅ decisions_routes imported successfully
   Router prefix: /v1/decisions
   Routes: ['/v1/decisions/', '/v1/decisions', '/v1/decisions/health']
✅ DecisionEngine initialized
   Trigger contracts: 30
   State guards loaded: True
✅ Router registered with FastAPI app
   Registered routes: ['/v1/decisions/', '/v1/decisions', '/v1/decisions/health']
```

---

## Production Status

**BLOCKED:** Endpoint returns 404 on production (pipeline-core.int.celeste7.ai)

**Reason:** Code not yet deployed to Render

**Required:** Git push + Render redeploy to activate endpoint

---

## Files Created/Modified

| File | Action |
|------|--------|
| `apps/api/services/decision_engine.py` | Created |
| `apps/api/routes/decisions_routes.py` | Created |
| `apps/api/pipeline_service.py` | Modified (added router registration) |
| `apps/api/tests/test_decision_engine.py` | Created |

---

## Phase 11.1 Checklist

| Item | Status |
|------|--------|
| Decision Engine loads E017 | ✅ |
| Decision Engine loads E019 | ✅ |
| Confidence scoring formula correct | ✅ |
| Tier thresholds enforced | ✅ |
| State guards block invalid transitions | ✅ |
| Forbidden contexts block actions | ✅ |
| Role-based permissions enforced | ✅ |
| API endpoint created | ✅ |
| Unit tests pass (17/17) | ✅ |
| Routes import successfully | ✅ |
| Production deployment | ⏳ Pending |

---

**Document:** PHASE_11_1_EVIDENCE.md
**Completed:** 2026-01-21
