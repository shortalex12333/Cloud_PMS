# Cache Key + Invalidation Spec

## Goal
Prevent cross-tenant cache bleed and ensure revocations take effect quickly.

## Canonical key format
`v1:{tenant_key_alias}:{yacht_id}:{user_id}:{role}:{endpoint}:{phase}:{query_hash}:{dataset_version}`

Requirements:
- yacht_id is required
- user_id is required
- role is required
- query_hash must be normalized and hashed

## TTL rules
- Streaming Phase 1: 30–120s
- Streaming Phase 2: 10–30s (shorter; more sensitive)
- Non-stream search: 30–120s
- Never cache signed URLs beyond their lifetime

## Revocation
- Prefer short TTL + “deny-by-default” membership checks
- If using explicit invalidation, provide:
  - `clear_cache_for_user(user_id)`
  - `clear_cache_for_yacht(yacht_id)`
- Role change or revoke must clear related keys or rely on TTL under 2 minutes

## Tests
- Ensure two different yachts cannot share a key
- Ensure role changes alter cache key
