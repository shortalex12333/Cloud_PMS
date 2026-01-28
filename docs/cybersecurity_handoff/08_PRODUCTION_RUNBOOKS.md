# Production Runbooks (What to do under pressure)

## A) Rotate keys (service credentials)
1) Put system in incident mode if compromise suspected
2) Rotate Render env vars
3) Rotate Supabase service keys
4) Confirm old keys no longer accepted
5) Audit and monitor denies/spikes

## B) Freeze a yacht (kill switch)
1) Set MASTER `is_frozen=true` for yacht_id
2) Middleware denies MUTATE/SIGNED/ADMIN
3) Streaming optional: disable for that yacht
4) Confirm denial within TTL window
5) Preserve logs for forensics

## C) Revoke a user
1) Set membership status=REVOKED in MASTER
2) Deactivate TENANT roles
3) Clear caches or wait bounded TTL
4) Confirm user receives 403 on next request

## D) Suspected leak (SEV0/SEV1)
1) Trigger global incident mode:
   - disable streaming
   - disable signed URL generation
   - freeze all writes
2) Export audit + logs
3) Identify scope: yachts, docs, actors
4) Patch and add test to prevent recurrence

## E) Adding a new yacht
1) Create fleet_registry entry
2) Provision tenant records/policies
3) Smoke test isolation and streaming behaviors
