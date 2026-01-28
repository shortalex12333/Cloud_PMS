# Streaming Search Security (Search-as-you-type, Stream-by-character)

You operate search streaming character-by-character. This creates **unique risk**:
- increased attack surface (many requests)
- metadata disclosure (existence of records)
- cache leakage if keys aren't tenant-scoped
- cost amplification and DoS potential

This document is the production-grade stance.

## Threats specific to streaming
1. Enumeration: attacker types prefixes to infer what exists.
2. Cross-tenant cache bleed: caching results without yacht_id/user_id/role in key.
3. Early streaming before authz: partial results leak before role resolved.
4. DoS: 1 user generates 1000 queries/min.
5. Sensitive preview leakage: snippet reveals classified content too early.

## Guardrails (server)
### A) Never stream until authz is locked
- Middleware must complete:
  - JWT verification
  - membership resolution
  - role resolution
  - yacht freeze check
before emitting *any* bytes.

### B) Minimum prefix length + debounce enforcement server-side
- Reject search < N chars with 200 + empty response (not error) to avoid side-channels.
- Enforce server-side debounce window:
  - If same user sends queries too frequently, return 429 or degrade to non-stream response.

### C) Rate limiting (layered)
- per IP
- per user_id
- per yacht_id (protect a yacht from internal misuse)
- include streaming connection count limits

### D) Cancellation required
- Client must cancel in-flight streams when query changes.
- Server should detect disconnect and stop DB work (important cost control).

### E) Two-phase streaming (recommended)
Phase 1 (fast, low sensitivity):
- return counts/categories only (e.g., “12 parts”, “3 work orders”), no snippets
Phase 2 (after stabilisation / explicit user pause):
- return detailed results with minimal snippet content appropriate to role

This reduces leakage while keeping UX responsive.

### F) Role-aware redaction
- Crew: titles only, no content preview
- HOD: limited snippet
- Manager/Captain: full preview where appropriate

### G) Cache key hygiene
Cache key must include:
- yacht_id
- user_id
- role
- normalized_query_hash
- dataset_version (optional)
Never cache across yachts.

### H) Vector search safety
If using embeddings/pgvector:
- Every vector row must include yacht_id
- Always filter by yacht_id before ordering by distance
- Do not allow “global nearest neighbors” queries across yacht_id

### I) Logging hygiene
- Do NOT log full query text by default (may contain sensitive terms).
- Log hashed query and length, not raw content.
- For debugging, allow opt-in sampling under incident controls.

## Guardrails (client)
- Debounce at 150–300ms
- Cancel previous streams
- Do not show sensitive previews until the query stabilizes
- Avoid autocompletes that reveal entity names without permission

## Success criteria
- Streaming never emits output before authz.
- A compromised user cannot infer other yachts' existence via timing or errors.
- Rate limits prevent flood.
- Cache never leaks cross-yacht data.
