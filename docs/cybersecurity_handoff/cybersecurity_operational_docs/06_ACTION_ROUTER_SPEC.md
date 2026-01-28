# Action Router Specification (Production)

## You do NOT need an Action Router per action.
You need:
- One router
- A strict action registry
- Action groups by risk level

## Action groups
- READ: safe, no side effects
- MUTATE: write operations that change state
- SIGNED: high-risk operations requiring step-up auth + signature payload
- ADMIN: provisioning, role changes, kill switch, etc.

## Action registry (required fields)
Each action must declare:
- action_name
- group (READ/MUTATE/SIGNED/ADMIN)
- allowed_roles (per yacht)
- required_scopes (optional)
- requires_step_up (bool)
- requires_signature (bool + signature schema)
- resource_types referenced (for ownership validation)
- idempotency_key behavior (required for writes)

## Request contract
- Every request must include:
  - request_id (UUID)
  - idempotency_key (for writes)
  - action_name
  - payload (action-specific)
- Middleware injects request_context (server-trusted):
  - user_id, yacht_id, role, membership_id, device_id, ip, user_agent

## Execution algorithm (mandatory order)
1. Verify JWT (MASTER)
2. Resolve ACTIVE membership (MASTER)
3. Enforce yacht freeze flag (MASTER)
4. Resolve role (TENANT) and validate active/valid_until
5. Validate action exists and role allowed
6. Validate payload schema (strict)
7. Validate resource ownership (by selecting each referenced ID with yacht_id)
8. Enforce step-up/signature gates
9. Execute handler (writes set yacht_id from context)
10. Write audit event (payload hash + outcome)
11. Return response (4xx for client errors)

## Idempotency
- All MUTATE/SIGNED/ADMIN actions must use idempotency_key.
- Store idempotency records in TENANT (yacht-scoped) or MASTER (control-plane actions).

## Observability
- All actions emit structured logs:
  - action_name, yacht_id, user_id, outcome, latency, affected_records_count
