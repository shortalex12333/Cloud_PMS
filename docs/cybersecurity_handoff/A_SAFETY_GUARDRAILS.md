# Safety Guardrails (One-page)

- server resolves yacht_id and role
- handlers validate ownership
- 404 for non-owned IDs
- no streaming before authz
- no client TENANT access
- tenant-safe cache keys
- validate storage prefix
- idempotency on writes
- audit everything
- kill switch ready
