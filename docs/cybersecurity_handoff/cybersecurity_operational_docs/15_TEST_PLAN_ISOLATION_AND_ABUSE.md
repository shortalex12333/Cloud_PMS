# Test Plan (Isolation, Abuse, Streaming)

## Isolation tests (must fail closed)
- Attempt to read record from yacht A using yacht B context → 404
- Attempt to update record from yacht A using yacht B context → 404/403
- Attempt to upload storage object to wrong yacht_id prefix → 403
- Attempt to generate signed URL for wrong prefix → 403
- Attempt to reference foreign ID in mutation payload → 404

## Role tests
- Crew can read, cannot mutate
- HOD can mutate allowed actions
- Manager/Captain can perform SIGNED actions with step-up
- Role expired (valid_until passed) → deny

## Streaming tests
- No bytes streamed before authz
- Prefix < N chars returns empty response
- Flood protection: 429 after threshold
- Cancel stream stops DB work
- Cache keys include yacht_id/user_id/role (verify no collision)

## Failure-mode tests
- Missing yacht_id in handler write → fail test
- Handler forgets ownership validation → test catches with randomized IDs
- Cache staleness after revoke → test checks TTL bound
