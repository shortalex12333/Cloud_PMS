# Invariants (Do Not Break)

## A) Context resolution
- `ctx.yacht_id` comes from MASTER membership resolution.
- `ctx.role` comes from TENANT `auth_users_roles` for that yacht.
- Payload may *suggest* a yacht (e.g., UI selection) but server must verify membership and derive ctx.

## B) Reads
- Always include yacht scope in code.
- Use 404 for “not found” when ownership fails to avoid enumeration.

## C) Writes
- Ignore any `yacht_id` in payload.
- Inject `yacht_id = ctx.yacht_id` into writes.
- Validate every referenced ID belongs to ctx.yacht before writing.

## D) Streaming
- Streaming endpoints must perform authz before sending headers/body chunks.
- Do not stream sensitive snippets early.

## E) Storage
- Key format is `{yacht_id}/...`.
- Validate prefix before:
  - creating signed upload URLs
  - creating signed download URLs
  - deleting objects

## F) Caching
- Key must include `yacht_id`, `user_id`, `role`.
- TTL must be bounded.
- Revocation and role changes must invalidate (or rely on short TTL).

## G) Service role
- Service role cannot be used outside server.
- Every service-role write path must call validators and write audit.

## H) Deny-by-default
- If role is missing/inactive/expired → deny.
- If membership is not ACTIVE → deny.
- If yacht is frozen → deny all MUTATE/SIGNED/ADMIN by default.

## Success criteria (production gate)
- Cross-yacht attempts always fail 4xx, never 500.
- No sensitive data appears in logs by default.
