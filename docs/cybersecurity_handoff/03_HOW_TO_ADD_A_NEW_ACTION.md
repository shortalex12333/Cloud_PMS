# How to Add a New Action Safely (Action Router)

## 1) Define the action in the registry
Required metadata:
- action_name
- group: READ | MUTATE | SIGNED | ADMIN
- allowed_roles (yacht-scoped)
- requires_step_up (bool)
- requires_signature (bool + schema)
- referenced_resource_types (for ownership validation)
- idempotent (bool) + idempotency_key requirement for writes
- logging redaction rules (query text? document content?)

## 2) Define a strict payload schema
- Validate types
- Validate lengths
- Disallow unknown fields (prevents sneaky bypass fields)

## 3) Enforce authorization in the standard order
Mandatory order:
1. Verify JWT
2. Resolve ACTIVE membership (MASTER)
3. Check yacht freeze / incident mode (MASTER)
4. Resolve role (TENANT) with valid_until checks
5. Validate action exists + role allowed
6. Validate payload schema
7. Ownership validation for every foreign ID
8. Step-up/signature gates
9. Execute handler
10. Write audit
11. Return response

## 4) Ownership validation (non-negotiable)
For each referenced ID:
- `SELECT id FROM <table> WHERE id=:id AND yacht_id=:ctx.yacht_id`
- If not found: return 404 (not 403)

## 5) Writes must be idempotent
- Require idempotency_key for MUTATE/SIGNED/ADMIN.
- Store idempotency records and return same result for repeats.

## 6) Audit
Write audit record with:
- request_id, idempotency_key
- actor_user_id, actor_role
- yacht_id
- action_name
- payload_hash (not raw payload if sensitive)
- outcome (allowed/denied/error)
- affected_record_ids (safe subset)

## 7) Tests (must be added)
- cross-yacht read/write attempt
- wrong role attempt
- missing ownership validation attempt (random ID)
- streaming: ensure no output before authz (if streamed)
- storage: ensure prefix validated (if storage touched)

## PR checklist
- [ ] action registry updated
- [ ] schema validated
- [ ] ownership checks added
- [ ] yacht_id injected from ctx
- [ ] idempotency implemented
- [ ] audit written
- [ ] tests added
- [ ] no sensitive logs
