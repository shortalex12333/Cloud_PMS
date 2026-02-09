# Architectural Debt: Error Code to HTTP Status Mapping

**Date**: 2026-02-08
**Priority**: P1 (Medium - affects UX but not security)
**Impact**: 20+ handlers returning wrong HTTP status codes

---

## Problem Statement

`ResponseBuilder.set_error()` defaults to HTTP 500 for ALL error codes, including client errors like NOT_FOUND, VALIDATION_ERROR, PERMISSION_DENIED.

**Result**: 87% of NOT_FOUND errors return HTTP 500 (should be 404)

---

## Root Cause

Two separate systems don't communicate:

1. **`middleware/action_security.py`** - Defines correct mappings:
   ```python
   "NOT_FOUND": {"status_code": 404}
   "PERMISSION_DENIED": {"status_code": 403}
   "VALIDATION_ERROR": {"status_code": 400}
   ```

2. **`actions/action_response_schema.py`** - Doesn't use them:
   ```python
   def set_error(code: str, message: str, status_code: int = 500):
       # Always defaults to 500 unless manually specified
   ```

---

## Current State Audit

### Handlers Returning WRONG Status Codes

```bash
# NOT_FOUND errors returning 500 (should be 404):
apps/api/handlers/certificate_handlers.py:273  # Vessel certificate
apps/api/handlers/certificate_handlers.py:317  # Crew certificate
apps/api/handlers/equipment_handlers.py:XXX    # Equipment
apps/api/handlers/fault_handlers.py:XXX        # Fault
# ... 16 more handlers
```

**Total**: 20 handlers affected

### Handlers Returning CORRECT Status Codes

```bash
# NOT_FOUND errors correctly returning 404:
apps/api/handlers/document_handlers.py:84   # Invalid document ID
apps/api/handlers/document_handlers.py:96   # Document not found
apps/api/handlers/document_handlers.py:103  # Deleted document
```

**Total**: 3 handlers (all Document Lens - just fixed today)

---

## Proposed Fix (ARCHITECTURAL)

### Option A: Auto-Map in ResponseBuilder (RECOMMENDED)

Modify `action_response_schema.py` to auto-map error codes:

```python
from middleware.action_security import get_standard_error_codes

class ResponseBuilder:
    def set_error(
        self,
        code: str,
        message: str,
        status_code: Optional[int] = None,  # Now optional
        field: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> "ResponseBuilder":
        """Set error with automatic status code mapping."""

        # Auto-map if not specified
        if status_code is None:
            error_mappings = get_standard_error_codes()
            status_code = error_mappings.get(code, {}).get("status_code", 500)
            # Fallback to 500 only for unknown error codes

        self._error = ErrorDetail(
            code=code,
            message=message,
            status_code=status_code,
            field=field,
            suggestions=suggestions
        ).to_dict()
        return self
```

**Benefits**:
- Fixes all 20 handlers automatically
- Single source of truth for error mappings
- Backwards compatible (manual status_code still works)
- No handler changes required

**Risks**:
- Low - fallback to 500 for unknown codes
- Existing manual status_codes override auto-mapping

---

### Option B: Update All Handlers Manually (NOT RECOMMENDED)

Add `status_code=404` to all 20 handlers.

**Drawbacks**:
- Error-prone (easy to forget in new handlers)
- Violates DRY principle
- No centralized mapping

---

## Implementation Plan

### Phase 1: Add Auto-Mapping (1 hour)

1. Import `get_standard_error_codes` in `action_response_schema.py`
2. Modify `ResponseBuilder.set_error()` to auto-map
3. Add unit tests for auto-mapping

### Phase 2: Verify All Lenses (2 hours)

1. Run E2E tests for each lens
2. Verify NOT_FOUND returns 404 (not 500)
3. Verify PERMISSION_DENIED returns 403
4. Verify VALIDATION_ERROR returns 400

### Phase 3: Document Contract (30 min)

Update error handling docs with canonical mappings.

---

## Error Code Standards (from action_security.py)

| Error Code | HTTP Status | Use Case |
|-----------|-------------|----------|
| `NOT_FOUND` | 404 | Resource doesn't exist or ownership failure |
| `PERMISSION_DENIED` | 403 | User lacks permission |
| `ROLE_NOT_ALLOWED` | 403 | User's role insufficient |
| `VALIDATION_ERROR` | 400 | Invalid input data |
| `IDEMPOTENCY_REQUIRED` | 400 | Missing idempotency key |
| `SIGNATURE_REQUIRED` | 400 | Missing signature for SIGNED action |
| `YACHT_FROZEN` | 403 | Yacht is frozen |
| `IDEMPOTENCY_CONFLICT` | 409 | Request already processed |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Why Default is 500 (Historical)

**Commit**: `987f4c5` (Jan 28, 2026)
**Purpose**: Added status_code field for Shopping List fixes
**Philosophy**: "Fail-safe" - better to return 500 than mislead with wrong 404/403

**Unintended Consequence**: Most handlers don't specify status_code → all return 500

---

## Security Implications

**Low Risk** - This is UX issue, not security:

- ✅ RLS still enforced (database level)
- ✅ JWT validation still works
- ✅ Permissions still checked
- ❌ HTTP status codes confusing (500 suggests server error, not client error)

**Does NOT affect**:
- Authentication (JWT still required)
- Authorization (permissions still enforced)
- Data isolation (RLS still active)

**Only affects**:
- HTTP status codes in error responses
- Client error handling logic
- Logging/monitoring (500s look like server failures)

---

## Recommendation

**Implement Option A** (auto-mapping) to fix all 20+ handlers at once.

**Priority**: P1 (after security fixes)
**Effort**: 3.5 hours total
**Impact**: Improves error contract compliance across all lenses

---

**Report Generated**: 2026-02-08
**Discovered During**: Document Lens E2E testing
**Related PR**: #169 (manual fix for Document Lens only)
