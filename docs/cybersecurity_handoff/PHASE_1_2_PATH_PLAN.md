# Phase 1-2 Implementation Path Plan

**Generated**: 2026-01-28
**Branch**: security/phase-1-2-implementation (to be created)
**Status**: Local simulation ready

---

## Executive Summary

Local environment verified and operational:
- **Web**: typecheck ✓, lint ✓, 316 unit tests ✓
- **API**: 176 unit tests passed (26 failures due to DB dependencies)
- **Contracts**: 42 tests passed ✓
- **Docker**: Available for RLS tests

---

## Phase 1: Memberships & Admin Actions

### Files to Modify

#### 1. MASTER DB Schema (memberships table)
**Path**: `supabase/master_migrations/` (new file)
```
CREATE TABLE memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  yacht_id UUID NOT NULL,
  status TEXT CHECK (status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'REVOKED')),
  role TEXT,
  invited_by UUID,
  approved_by UUID,
  approved_at TIMESTAMPTZ,
  valid_from TIMESTAMPTZ DEFAULT now(),
  valid_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

**Files**:
- `database/master_migrations/010_create_memberships.sql` (NEW)
- `database/master_migrations/011_memberships_rls.sql` (NEW)

#### 2. Middleware Context Resolution
**Path**: `apps/api/middleware/auth.py`

**Changes needed**:
- Line 100-208: Refactor `lookup_tenant_for_user()` to query new `memberships` table
- Add membership status validation (ACTIVE only)
- Add `valid_until` expiry check
- Add freeze check from fleet_registry

**New module** (recommended):
- `apps/api/middleware/request_context.py` - Centralized context builder

#### 3. Action Registry - Admin Actions
**Path**: `apps/api/action_router/registry.py`

**New actions to add**:
```python
"invite_user": ActionDefinition(
    action_id="invite_user",
    variant=ActionVariant.ADMIN,
    allowed_roles=["captain", "manager"],
    requires_signature=True,
    signature_roles_required=["captain", "manager"],
    # ...
)

"approve_membership": ActionDefinition(...)
"revoke_membership": ActionDefinition(...)
"freeze_yacht": ActionDefinition(...)
```

#### 4. Admin Handlers
**Path**: `apps/api/handlers/admin_handlers.py` (NEW)

**Functions**:
- `invite_user()` - Creates PENDING membership
- `approve_membership()` - Sets ACTIVE, requires 2-person rule for privileged roles
- `revoke_membership()` - Sets REVOKED, clears tenant cache
- `freeze_yacht()` - Sets is_frozen on fleet_registry

---

## Phase 2: Ownership Validation Library & Idempotency

### Files to Modify

#### 1. Central Ownership Validation Module
**Path**: `apps/api/validators/ownership.py` (NEW)

```python
class OwnershipValidator:
    """
    Central ownership validation for all handlers.

    Usage:
        validator = OwnershipValidator(supabase_client, yacht_id)
        validator.validate_entity("equipment", equipment_id)  # Raises 404 if not owned
    """

    ENTITY_TABLE_MAP = {
        "equipment": "pms_equipment",
        "fault": "pms_faults",
        "work_order": "pms_work_orders",
        "part": "pms_parts",
        "document": "documents",
        "attachment": "pms_attachments",
        "note": "pms_notes",
        "checklist": "pms_checklists",
    }

    def validate_entity(self, entity_type: str, entity_id: str) -> Dict:
        """Validate entity ownership. Returns entity or raises 404."""

    def validate_multiple(self, entities: List[Tuple[str, str]]) -> List[Dict]:
        """Batch ownership validation."""
```

#### 2. Refactor Existing Handlers to Use Validator
**Files to update**:
- `apps/api/action_router/dispatchers/internal_dispatcher.py` (lines 200-400)
- `apps/api/handlers/fault_mutation_handlers.py`
- `apps/api/handlers/work_order_handlers.py`
- `apps/api/handlers/part_handlers.py`
- `apps/api/handlers/equipment_handlers.py`
- `apps/api/handlers/receiving_handlers.py`

**Pattern change**:
```python
# BEFORE (scattered in each handler)
result = supabase.table("pms_equipment").select("id").eq("id", eq_id).eq("yacht_id", yacht_id).execute()
if not result.data:
    raise ValueError("Equipment not found")

# AFTER (centralized)
from validators.ownership import OwnershipValidator
validator = OwnershipValidator(supabase, ctx.yacht_id)
equipment = validator.validate_entity("equipment", equipment_id)
```

#### 3. Idempotency Scaffolding
**Path**: `apps/api/middleware/idempotency.py` (NEW)

**Schema** (TENANT DB):
```sql
CREATE TABLE idempotency_keys (
  idempotency_key TEXT PRIMARY KEY,
  yacht_id UUID NOT NULL,
  action_id TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ DEFAULT now() + INTERVAL '24 hours'
);
```

**Module**:
```python
class IdempotencyManager:
    def check_or_create(self, key: str, yacht_id: str, action_id: str, request_hash: str) -> Optional[Dict]:
        """Returns cached response if exists, None if new request."""

    def store_response(self, key: str, response: Dict) -> None:
        """Store response for idempotent replay."""

    def cleanup_expired(self) -> int:
        """Remove expired keys (background job)."""
```

#### 4. Cache Key Builder
**Path**: `apps/api/utils/cache_keys.py` (NEW)

```python
def build_cache_key(
    yacht_id: str,
    user_id: str,
    role: str,
    endpoint: str,
    query_hash: str,
    phase: int = 1,
    tenant_key_alias: str = None,
    dataset_version: str = None
) -> str:
    """
    Build canonical cache key per spec.

    Format: v1:{tenant}:{yacht_id}:{user_id}:{role}:{endpoint}:{phase}:{query_hash}:{version}
    """
```

---

## Missing Tests (Cross-Yacht Fuzzing & Ownership Validation)

### 1. Cross-Yacht Attempt Tests (CRITICAL)
**Path**: `tests/security/test_cross_yacht_attacks.py` (NEW)

```python
class TestCrossYachtAttempts:
    """Fuzzing tests for cross-yacht access attempts."""

    def test_read_other_yacht_equipment_returns_404(self):
        """User A cannot read User B's equipment."""

    def test_write_other_yacht_equipment_returns_404(self):
        """User A cannot update User B's equipment."""

    def test_payload_yacht_id_ignored(self):
        """Payload yacht_id is ignored, ctx.yacht_id used."""

    def test_random_uuid_equipment_returns_404(self):
        """Random equipment ID returns 404, not 500."""

    def test_signed_action_other_yacht_returns_403(self):
        """SIGNED action on other yacht's entity returns 403."""
```

### 2. Ownership Validation Gap Tests
**Path**: `tests/security/test_ownership_validation.py` (NEW)

```python
class TestOwnershipValidation:
    """Tests for ownership validation library."""

    def test_validate_entity_owned_returns_entity(self):
        """Owned entity returns full record."""

    def test_validate_entity_not_owned_returns_404(self):
        """Not owned entity returns 404 (not 403)."""

    def test_validate_entity_nonexistent_returns_404(self):
        """Nonexistent ID returns 404."""

    def test_batch_validation_all_owned(self):
        """Batch validation passes for all owned."""

    def test_batch_validation_one_not_owned_fails_all(self):
        """Batch validation fails if any not owned."""
```

### 3. Idempotency Tests
**Path**: `tests/security/test_idempotency.py` (NEW)

```python
class TestIdempotency:
    """Tests for idempotency layer."""

    def test_duplicate_request_returns_same_response(self):
        """Same idempotency_key returns cached response."""

    def test_different_key_creates_new_record(self):
        """Different key creates new mutation."""

    def test_expired_key_allows_new_request(self):
        """Expired idempotency key allows re-execution."""

    def test_key_scoped_to_yacht(self):
        """Idempotency key is yacht-scoped."""
```

### 4. Membership Lifecycle Tests
**Path**: `tests/security/test_memberships.py` (NEW)

```python
class TestMembershipLifecycle:
    """Tests for membership state transitions."""

    def test_pending_user_cannot_access_api(self):
        """PENDING membership returns 403."""

    def test_active_user_can_access_api(self):
        """ACTIVE membership allows access."""

    def test_revoked_user_blocked_immediately(self):
        """REVOKED membership blocks within TTL."""

    def test_expired_membership_blocked(self):
        """valid_until exceeded returns 403."""

    def test_frozen_yacht_blocks_mutations(self):
        """is_frozen=true blocks MUTATE/SIGNED/ADMIN."""
```

### 5. Storage Signing Tests
**Path**: `tests/security/test_storage_signing.py` (NEW)

```python
class TestStorageSigning:
    """Tests for signed URL generation."""

    def test_sign_own_yacht_document_succeeds(self):
        """User can sign URL for own yacht's document."""

    def test_sign_other_yacht_document_returns_404(self):
        """Cross-yacht document signing returns 404."""

    def test_path_without_yacht_prefix_rejected(self):
        """Path without yacht_id prefix is rejected."""

    def test_signed_url_expires_correctly(self):
        """URL expiration matches TTL."""
```

---

## Blockers & Notes

### Current Blockers
1. **None critical** - Local facilities operational

### Minor Issues Observed
1. `tests/test_v2_search_endpoint.py` has `sys.exit(1)` on import failure (non-blocking)
2. Some API unit tests require live DB connection (expected for integration tests)
3. `.env.tenant1` missing `TENANT_SUPABASE_JWT_SECRET` (fixed in new `.env`)

### Docker RLS Tests
**Command**: `docker-compose -f docker-compose.test.yml up --build`
**Status**: Ready to run (Docker available)

### E2E Tests
**Command**: `npm run test:e2e` (headless)
**Status**: Ready to run (Playwright configured)

---

## Implementation Order

### Phase 1 (Memberships)
1. Create MASTER migrations for `memberships` table
2. Update `middleware/auth.py` to use memberships
3. Add admin actions to registry
4. Create admin handlers
5. Add membership lifecycle tests
6. Run full test suite

### Phase 2 (Ownership & Idempotency)
1. Create `validators/ownership.py`
2. Refactor handlers to use ownership validator
3. Create `middleware/idempotency.py` + migrations
4. Create `utils/cache_keys.py`
5. Add cross-yacht fuzzing tests
6. Add idempotency tests
7. Run full test suite + Docker RLS tests

---

## Test Checklist

| Test Category | File | Status |
|--------------|------|--------|
| Cross-yacht READ attempts | `test_cross_yacht_attacks.py` | TO CREATE |
| Cross-yacht WRITE attempts | `test_cross_yacht_attacks.py` | TO CREATE |
| Ownership validation | `test_ownership_validation.py` | TO CREATE |
| Idempotency | `test_idempotency.py` | TO CREATE |
| Membership lifecycle | `test_memberships.py` | TO CREATE |
| Storage signing | `test_storage_signing.py` | TO CREATE |
| Cache key isolation | `test_cache_keys.py` | TO CREATE |
| RLS yacht isolation | `yacht-isolation.test.ts` | EXISTS (42 tests) |
| Action router auth | `test_auth_middleware.py` | EXISTS |

---

## Verification Criteria

Before merging Phase 1-2:
- [ ] All existing tests pass (316 web, 176+ API, 42 contracts)
- [ ] New security tests pass (cross-yacht, ownership, idempotency)
- [ ] Docker RLS tests pass
- [ ] No secrets in logs
- [ ] Audit logging verified for all new actions
- [ ] Membership state transitions tested
- [ ] Freeze/incident mode tested
