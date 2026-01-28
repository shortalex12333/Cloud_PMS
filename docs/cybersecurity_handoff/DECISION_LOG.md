# Security Architecture Decision Log

## Purpose
This document records key architectural decisions made for the CelesteOS multi-tenant security model. Each decision includes rationale, alternatives considered, and implementation status.

---

## D-001: Dedicated MASTER Memberships Object

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Create a dedicated `memberships` table in MASTER DB with explicit status tracking.

### Statuses
```
INVITED → ACCEPTED → PROVISIONED → ACTIVE → SUSPENDED → REVOKED
```

### Rationale
- Single source of truth for access lifecycle
- Enables granular audit of invitation/acceptance/provisioning flow
- Supports time-bounded access (`valid_from`, `valid_until`)
- Allows suspension without full revocation

### Implementation
- MASTER table: `memberships`
- Fields: `user_id`, `yacht_id`, `status`, `invited_by`, `approved_by`, `invited_at`, `accepted_at`, `provisioned_at`, `valid_from`, `valid_until`
- Middleware checks `status = 'ACTIVE'` and date bounds

### TBD
- [ ] Confirm exact status transition rules with product
- [ ] Define max membership per user limit

---

## D-002: Two-Person Rule for Privileged Roles

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Privileged roles require 2-person approval: inviter cannot be approver.

### Privileged Roles
- `captain`
- `manager`
- `chief_engineer`

### Rationale
- Prevents single actor from granting themselves elevated access
- Required for SOC2 CC6.1 (access provisioning controls)
- Reduces insider threat risk

### Implementation
- `memberships.approved_by != memberships.invited_by` constraint
- UI blocks self-approval
- Audit logs both actors

### Edge Cases
- Fleet owner/first captain: Bootstrap with service account, logged
- Emergency access: Requires incident documentation

---

## D-003: Streaming Search Two-Phase Architecture

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Implement two-phase streaming search with role-aware redaction.

### Phase 1: Low-Sensitivity (Fast)
- Returns counts/categories only
- No snippets, no document titles for restricted roles
- Aggressive caching (TTL: 60s)
- Min prefix: 3 characters

### Phase 2: Detailed (After Debounce)
- Returns titles, metadata, snippets
- Role-aware snippet redaction (crew sees none)
- Shorter cache (TTL: 15s)
- Requires stabilized query

### Rate Limits
| Limit | Value |
|-------|-------|
| User burst | 10 req |
| User sustained | 2 req/sec |
| Yacht concurrency | 10 |
| Request timeout (P1) | 1.5s |
| Request timeout (P2) | 4s |

### Rationale
- Prevents keystroke-level DB queries
- Protects document metadata from enumeration
- Manages yacht-level resource contention

### Implementation
- `routes/search_streaming.py`
- `services/streaming_cache.py`
- Tests: `test_streaming_safety.py`, `test_streaming_cache_isolation.py`

---

## D-004: Cache Key Canonical Format

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
All cache keys MUST include tenant isolation fields.

### Canonical Format
```
v1:{tenant_key_alias}:{yacht_id}:{user_id}:{role}:{endpoint}:{phase}:{query_hash}:{dataset_version}
```

### Required Fields
- `yacht_id` - Tenant isolation
- `user_id` - User-specific results
- `role` - Role-aware responses
- `query_hash` - Normalized, hashed query

### TTL Rules
| Context | TTL |
|---------|-----|
| Streaming Phase 1 | 30-120s |
| Streaming Phase 2 | 10-30s |
| Non-stream search | 30-120s |
| Signed URLs | Never cache beyond lifetime |

### Rationale
- Prevents cross-tenant cache bleed
- Role changes invalidate cache
- Query hash prevents cache key manipulation

### Implementation
- `services/cache_key_builder.py`
- `build_streaming_cache_key()` function
- Tests: `test_streaming_cache_isolation.py`

---

## D-005: Caching Infrastructure

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Infrastructure Team

### Decision
Use Redis for production caching with explicit invalidation on revocation.

### Architecture
- Production: Redis (managed)
- Development: In-memory LRU
- Staging: Redis (shared)

### Invalidation
1. Short TTL (primary defense) - max 2 minutes
2. Explicit clear on:
   - Role change
   - Membership revocation
   - Yacht freeze

### Functions
```python
clear_cache_for_user(user_id)
clear_cache_for_yacht(yacht_id)
```

### TBD
- [ ] Redis cluster configuration
- [ ] Cache warming strategy

---

## D-006: Incident Mode (Kill Switch)

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Global incident mode disables sensitive operations fleet-wide.

### Controlled Features
| Feature | Incident Mode Effect |
|---------|---------------------|
| Streaming search | 503 disabled |
| Signed URLs | 503 disabled |
| All writes (MUTATE/SIGNED/ADMIN) | 503 disabled |
| READ actions | Allowed |

### Implementation
- MASTER table: `system_flags`
- Fields: `incident_mode`, `disable_streaming`, `disable_signed_urls`, `disable_writes`, `incident_reason`, `incident_started_at`, `incident_started_by`
- Middleware checks before every action
- All toggles audited to `security_events`

### Admin Actions
- `admin_enable_incident_mode` - ADMIN group, captain+ only
- `admin_disable_incident_mode` - ADMIN group, captain+ only
- `admin_get_system_flags` - READ group

### Tests
- `test_kill_switch.py` (23 tests)

---

## D-007: Key/Token Rotation Policy

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Establish rotation schedule for all secrets.

### Rotation Schedule
| Secret Type | Rotation Period | Notes |
|-------------|-----------------|-------|
| Supabase service keys | 90 days | Per environment |
| JWT signing keys | 90 days | Coordinated rollover |
| User tokens | 24 hours | Refresh token extends |
| API keys (external) | 90 days | With deprecation period |

### Implementation
- Secrets stored in environment variables
- No hardcoded secrets (CI gate enforces)
- Rotation procedure documented in `08_PRODUCTION_RUNBOOKS.md`

### TBD
- [ ] Automated rotation tooling
- [ ] Key escrow for DR

---

## D-008: Ownership Validation Pattern

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
All foreign IDs in mutations require ownership validation before operation.

### Validation Query
```sql
SELECT id FROM {table}
WHERE id = :entity_id
AND yacht_id = :ctx.yacht_id
```

### Response Rules
- Not found / wrong yacht: Return **404** (not 403)
- Reason: Prevent enumeration attacks

### Implementation
- `validators/ownership.py` - `ensure_owned()` function
- `@secure_action` decorator validates `validate_entities` list
- Entity-to-table mapping in `action_security.py`

### Tests
- `test_cross_yacht_attacks.py`
- `test_action_security.py`

---

## D-009: Error Message Hygiene

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
Error messages must not reveal internal details or enable enumeration.

### Rules
1. Never include table names in errors
2. Never include tenant aliases in errors
3. Use generic messages for authz failures
4. Use 404 for ownership failures (not 403)
5. Log detailed errors server-side only

### Standardized Codes
| Code | Status | Public Message |
|------|--------|----------------|
| NOT_FOUND | 404 | Resource not found |
| ROLE_NOT_ALLOWED | 403 | Insufficient permissions |
| YACHT_FROZEN | 403 | Yacht is frozen |
| MEMBERSHIP_INACTIVE | 403 | Access denied |

### Implementation
- `middleware/action_security.py` - `map_security_error_to_response()`
- `get_standard_error_codes()` function

---

## D-010: Signed URL Prefix Validation

**Status**: APPROVED
**Date**: 2026-01-28
**Owner**: Security Team

### Decision
All storage operations must validate yacht prefix before execution.

### Key Format
```
{yacht_id}/...
```

### Validation Points
1. Before creating signed upload URLs
2. Before creating signed download URLs
3. Before deleting objects

### Implementation
- `pipeline_service.py` - `/v1/documents/{document_id}/sign`
- Ownership check via `doc_metadata` with yacht_id filter
- Tests: `test_signed_url_security.py`

---

## Pending Decisions (TBD)

### TBD-001: Yacht Freeze Scope
- Should yacht freeze block ADMIN actions or only MUTATE/SIGNED?
- Current: Blocks MUTATE/SIGNED/ADMIN (conservative)

### TBD-002: Session Termination on Revoke
- Should active sessions be terminated immediately on revoke?
- Current: Rely on TTL (max 2 min)

### TBD-003: Multi-Yacht Users
- Support for users with access to multiple yachts
- Current: Single yacht per user

---

## Changelog

| Date | Decision | Change |
|------|----------|--------|
| 2026-01-28 | D-001 through D-010 | Initial documentation |
