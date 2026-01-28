# Integration Changes Required (Infra + Backend Comms)

This document translates security controls into concrete engineering changes.

## A) Replace manual provisioning with admin actions
- Build an internal “Crew Admin” UI that calls Action Router ADMIN actions:
  - invite_user
  - approve_membership
  - provision_membership
  - change_role
  - revoke_membership
  - freeze_yacht / unfreeze_yacht

### Why
Manual DB edits are the #1 insider + mistake pathway.

## B) Centralize request_context and forbid direct Supabase calls in handlers
- Middleware constructs request_context once.
- Handlers accept (request_context, payload) only.
- Any handler that reads yacht_id from payload fails review.

### Enforcement
- Lint rule / static check: disallow `payload['yacht_id']` usage.

## C) Streaming search architecture changes
- Move from “per-keystroke full search” to:
  1) fast suggest: counts/categories only
  2) stabilized query: full results
- Add server-side min prefix + rate limiting
- Add cancellation propagation
- Ensure streaming output starts only after membership+role resolved

## D) Cache and index changes
- Ensure cache key includes yacht_id+user_id+role
- Add query normalization to avoid cache poisoning
- Add composite indexes for yacht-scoped access patterns
- If using pgvector:
  - create index per table; always filter yacht_id

## E) Kill switch
- Add MASTER field `fleet_registry.is_frozen` or similar
- Middleware checks this before allowing MUTATE/SIGNED
- Optional: allow READ-only during incident mode

## F) Secrets/keys
- Remove any sensitive NEXT_PUBLIC vars
- Split service credentials by purpose (or document compensating controls)
- Add rotation runbook and scheduled rotation cadence

## G) Audit
- Implement append-only audit tables
- Ensure audit write failures fail the request (don’t silently drop)
- Provide export pipeline for forensics

## H) Production hardening
- Rate limits on all endpoints, extra tight on streaming
- Request size limits (prevent large payloads)
- Timeout budgets for DB calls
- Circuit breaker in Action Router for degraded mode
