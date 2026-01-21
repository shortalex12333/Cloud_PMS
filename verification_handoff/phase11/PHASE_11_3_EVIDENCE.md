# Phase 11.3: Decision Audit Logging - EVIDENCE

**Date:** 2026-01-21
**Status:** CODE COMPLETE (Pending Deployment + Migration)

---

## Deliverables

### 1. Decision Audit Service

**File:** `apps/api/services/decision_audit_service.py`

```python
class DecisionAuditService:
    """
    Service for logging decision evaluations.

    Logs to decision_audit_log table with full context for:
    - Explainability: "Why was this action shown/hidden?"
    - Analytics: Confidence distribution, common blocks
    - Compliance: Full audit trail of AI decisions
    """

    def log_decisions(
        self,
        execution_id: str,
        yacht_id: str,
        user_id: str,
        user_role: str,
        detected_intents: List[str],
        entities: List[Dict],
        situation: Dict,
        environment: str,
        decisions: List[Dict],
        session_id: Optional[str] = None,
    ) -> int:
        """Log all decisions from a single evaluation."""
```

### 2. SQL Migration

**File:** `apps/api/migrations/20260121_create_decision_audit_log.sql`

```sql
CREATE TABLE IF NOT EXISTS decision_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    session_id UUID,
    user_role TEXT,
    action TEXT NOT NULL,
    decision TEXT NOT NULL,  -- 'show', 'hide', 'disable'
    tier TEXT,
    confidence_total FLOAT DEFAULT 0.0,
    confidence_intent FLOAT DEFAULT 0.0,
    confidence_entity FLOAT DEFAULT 0.0,
    confidence_situation FLOAT DEFAULT 0.0,
    reasons JSONB DEFAULT '[]'::jsonb,
    blocked_by TEXT,
    blocked_by_type TEXT,
    detected_intents JSONB DEFAULT '[]'::jsonb,
    entities JSONB DEFAULT '[]'::jsonb,
    situation JSONB DEFAULT '{}'::jsonb,
    environment TEXT DEFAULT 'at_sea'
);
```

### 3. Route Integration

**File:** `apps/api/routes/decisions_routes.py` (lines 204-223)

```python
# Log decisions to audit table (async, non-blocking)
try:
    tenant_key_alias = auth.get('tenant_key_alias')
    if tenant_key_alias:
        client = get_tenant_client(tenant_key_alias)
        audit_service = get_decision_audit_service(client)
        audit_service.log_decisions(
            execution_id=result["execution_id"],
            yacht_id=yacht_id,
            user_id=user_id,
            user_role=user_role,
            detected_intents=request.detected_intents,
            entities=entities_list,
            situation=request.situation,
            environment=request.environment,
            decisions=result["decisions"],
        )
except Exception as audit_error:
    # Don't fail the request if audit logging fails
    logger.warning(f"[decisions] Audit logging failed: {audit_error}")
```

---

## Unit Test Evidence

**File:** `apps/api/tests/test_decision_audit_service.py`
**Result:** 11/11 PASSED

```
tests/test_decision_audit_service.py::TestDecisionAuditEntry::test_entry_has_required_fields PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_decision_type_mapping_allowed PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_decision_type_mapping_blocked_threshold PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_decision_type_mapping_blocked_permission PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_decision_type_mapping_blocked_state_guard PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_sanitize_entities PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_log_decisions_batch_insert PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_log_decisions_handles_db_error PASSED
tests/test_decision_audit_service.py::TestDecisionAuditService::test_entry_has_execution_id_grouping PASSED
tests/test_decision_audit_service.py::TestGetDecisionAuditService::test_caches_service_per_client PASSED
tests/test_decision_audit_service.py::TestGetDecisionAuditService::test_different_clients_get_different_services PASSED
```

---

## Decision Type Mapping (E021)

| Condition | Decision Type | Description |
|-----------|---------------|-------------|
| `allowed: true` | `show` | Action is visible and clickable |
| `blocked_by.type: threshold` | `hide` | Action hidden (low confidence) |
| `blocked_by.type: forbidden` | `hide` | Action hidden (forbidden context) |
| `blocked_by.type: permission` | `disable` | Action visible but disabled |
| `blocked_by.type: state_guard` | `disable` | Action visible but disabled |

---

## Schema Compliance (E021)

Per E021 DecisionAuditLog interface:

| E021 Field | Table Column | Status |
|------------|--------------|--------|
| `timestamp` | `timestamp` | ✅ |
| `user_id` | `user_id` | ✅ |
| `yacht_id` | `yacht_id` | ✅ |
| `session_id` | `session_id` | ✅ |
| `action` | `action` | ✅ |
| `decision` | `decision` | ✅ |
| `confidence.total` | `confidence_total` | ✅ |
| `confidence.intent` | `confidence_intent` | ✅ |
| `confidence.entity` | `confidence_entity` | ✅ |
| `confidence.situation` | `confidence_situation` | ✅ |
| `reasons` | `reasons` | ✅ |
| `blocked_by` | `blocked_by` | ✅ |
| `context.detected_intent` | `detected_intents` | ✅ |
| `context.entities` | `entities` | ✅ |
| `context.situation` | `situation` | ✅ |

---

## Query Examples (Post-Deployment)

### Why was action hidden?

```sql
SELECT * FROM decision_audit_log
WHERE action = 'close_work_order'
  AND decision = 'hide'
  AND user_id = 'abc123'
ORDER BY timestamp DESC
LIMIT 10;
```

### Low confidence decisions

```sql
SELECT action, AVG(confidence_total) as avg_conf, COUNT(*) as count
FROM decision_audit_log
WHERE confidence_total < 0.6
GROUP BY action
ORDER BY count DESC;
```

### Blocked by state guard

```sql
SELECT action, blocked_by, COUNT(*) as count
FROM decision_audit_log
WHERE blocked_by_type = 'state_guard'
GROUP BY action, blocked_by
ORDER BY count DESC;
```

---

## Files Created/Modified

| File | Action |
|------|--------|
| `apps/api/services/decision_audit_service.py` | Created |
| `apps/api/migrations/20260121_create_decision_audit_log.sql` | Created |
| `apps/api/routes/decisions_routes.py` | Modified (added audit logging) |
| `apps/api/tests/test_decision_audit_service.py` | Created |

---

## Deployment Steps

1. **Run SQL migration** on tenant database:
   ```bash
   psql $TENANT_DATABASE_URL -f migrations/20260121_create_decision_audit_log.sql
   ```

2. **Deploy code** to Render (git push triggers auto-deploy)

3. **Verify** audit logging:
   ```bash
   curl -X POST https://pipeline-core.int.celeste7.ai/v1/decisions \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"detected_intents":["view"],"entities":[]}'
   ```

4. **Query audit log**:
   ```sql
   SELECT * FROM decision_audit_log ORDER BY timestamp DESC LIMIT 5;
   ```

---

## Phase 11.3 Checklist

| Item | Status |
|------|--------|
| DecisionAuditService created | ✅ |
| SQL migration file created | ✅ |
| Route integration added | ✅ |
| Unit tests pass (11/11) | ✅ |
| Decision type mapping correct | ✅ |
| E021 schema compliance | ✅ |
| Error handling (non-blocking) | ✅ |
| Migration deployed | ⏳ Pending |
| Production verification | ⏳ Pending |

---

**Document:** PHASE_11_3_EVIDENCE.md
**Completed:** 2026-01-21
