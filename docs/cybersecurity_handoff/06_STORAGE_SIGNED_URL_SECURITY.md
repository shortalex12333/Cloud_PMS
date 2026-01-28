# Storage Signed URL Security

## Threat
If a signed URL can be generated for the wrong yacht prefix, you have an instant data leak.

## Rules
- Object keys must begin with `{ctx.yacht_id}/...`.
- Before signing any URL:
  - validate prefix == ctx.yacht_id
  - validate user role allows access to that object type
- Never accept a full key from the client without validation.

## Recommended: server-owned object references
Instead of the client supplying storage paths:
- Client supplies `document_id`
- Server looks up the true storage key by (document_id, yacht_id)
- Server signs that key
This eliminates path traversal.

## Audit
Log signed URL generation events:
- actor, yacht, document_id, operation (read/write), outcome
