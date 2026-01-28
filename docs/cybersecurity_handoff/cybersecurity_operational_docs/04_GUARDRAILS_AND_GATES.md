# Guardrails & Gates (Non-Negotiable)

These are the production-level rules that prevent $50m/yacht failures.

## 1) Tenant Context Guardrails
- **Never trust client-supplied yacht_id** for authorization.
- All requests must pass middleware that resolves:
  - user_id
  - membership(s)
  - selected yacht (validated)
  - yacht-scoped role (TENANT)
- Enforce a single `request_context` object injected into handlers:
  - { user_id, yacht_id, role, device_id?, membership_id, request_id }

## 2) Data Access Guardrails (TENANT)
- Every table must have `yacht_id` NOT NULL (except static lookups).
- Every query must include a yacht_id filter in code.
- Every write must set yacht_id from request_context, not payload.
- Every handler must validate ownership of all referenced record IDs:
  - If payload references {work_order_id}, first SELECT it by (id, yacht_id).
  - If not found → 404 (not 403), to avoid enumeration.

## 3) Storage Guardrails
- All object keys must start with: `{yacht_id}/...`
- Storage policies must validate foldername[1] == yacht_id
- On server, validate the key prefix before generating signed URLs.

## 4) Service Role Guardrails
- Service role usage is limited to backend.
- Split credentials by purpose (recommended):
  - provisioner (membership provisioning only)
  - reader (read-only operations)
  - writer (mutations)
  - auditor (write-only to audit logs)
- Implement “fail-closed” defaults: if role is missing → deny.

## 5) Authorization Guardrails
- TENANT.auth_users_roles is authoritative.
- MASTER may store requested role but cannot be the final authority.
- Role changes require:
  - step-up auth (TOTP/U2F) AND/OR
  - 2-person approval for captain/manager
- Roles should be time-bounded for contractors:
  - valid_until enforced in queries and helpers.

## 6) Error Handling Guardrails
- All client-induced failures → 4xx
- Never leak whether a record exists across yachts (use 404).
- Never stream partial sensitive output before authz is complete.

## 7) Caching Guardrails
- Cache keys must include: yacht_id + user_id + role + query_hash
- TTL must be short and bounded; revocation must clear caches.
- No shared global caches of search results across yachts.

## 8) Streaming Guardrails (Search as you type)
- Do not execute expensive search on every character.
- Enforce:
  - min prefix length
  - debounce windows
  - rate limits
  - cancellation
  - safe partial outputs (no sensitive doc previews in early stream)

See `07_STREAMING_SEARCH_SECURITY.md`.

## 9) Kill Switch Guardrail
- A per-yacht “freeze” flag in MASTER must stop all tenant mutations immediately.
- Add global “incident mode” to disable streaming and signed URL generation.

## 10) Evidence Guardrail (SOC2)
- Every control above must have:
  - an owner
  - a test
  - a log/audit artifact
