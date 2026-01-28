# Streaming Search Implementation Guide (Stream-by-character)

You stream search results character-by-character. That is a security *and* cost risk.

## Non-negotiables
1) Do not emit any bytes until authz is complete (JWT → membership → role → freeze).
2) Do not run full DB/vector searches on every keystroke.
3) Cancellation must stop DB work.

## Recommended pattern: two-phase streaming
### Phase 1: low-sensitivity, fast
- Return counts/categories only:
  - parts_count, work_orders_count, documents_count
- No snippets, no titles from documents if role forbids.
- Cache this aggressively (tenant-safe key).

### Phase 2: stabilized query (after debounce / explicit pause)
- Return detailed results:
  - titles, minimal metadata
  - role-aware snippets (crew may get none)

## Server-side enforcement
- min prefix length: e.g., 3
- per-user rate limit: e.g., 10 req/sec burst, 2 req/sec sustained (tune)
- per-yacht concurrency limit (protect yacht from internal abuse)
- request timeout budgets (e.g., 1.5s phase 1, 4s phase 2)
- log hashed query, not raw query

## Cancellation
- Client cancels previous stream when query changes.
- Server detects disconnect and aborts query work.

## Metadata leakage controls
- Use 404 for record fetch failures.
- Avoid error messages that differentiate “exists in another yacht”.
- Do not stream “found exact doc name” suggestions to low roles.

## Caching rules (critical)
Cache key MUST include:
- yacht_id
- user_id
- role
- query_hash
- phase (1 or 2)
- dataset_version (optional)

## Vector search rules
- Store yacht_id with vectors.
- Always filter by yacht_id before distance ordering.
