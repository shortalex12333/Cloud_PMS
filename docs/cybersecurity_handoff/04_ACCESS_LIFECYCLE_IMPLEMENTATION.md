# Access Lifecycle (Invite → Accept → Provision → Active → Revoke)

## Goal
Eliminate manual DB edits and make access changes auditable and safe.

## Master tables (recommended)
### memberships
- membership_id (uuid)
- user_id (uuid)
- yacht_id (uuid)
- status: INVITED | ACTIVE | REVOKED | LOCKED
- invited_by (uuid)
- approved_by (uuid, nullable)
- valid_until (timestamptz, nullable)
- created_at, updated_at
Constraints:
- UNIQUE(user_id, yacht_id)

### invites
- invite_id (uuid)
- membership_id
- token_hash (store hash only)
- expires_at
- used_at
- created_at

## Flow
1) Sponsor invites via ADMIN action
- create/link MASTER user
- create membership status=INVITED
- create invite token (one-time)
- send email

2) User accepts
- login to MASTER
- redeem token
- membership status=PENDING_PROVISION (or keep INVITED but mark used)

3) Provision (server-only ADMIN action)
- TENANT upsert profiles + roles
- membership status=ACTIVE
- audit

4) Revoke
- membership status=REVOKED
- TENANT roles deactivate
- caches invalidated / short TTL ensures effect
- audit

## Hard rules
- No direct writes to TENANT membership/role tables outside provisioning actions.
- Privileged roles (captain/manager) require approval gate.
- Contractors require valid_until.

## Tests
- provisioning is idempotent
- revoke denies within TTL
- cannot access TENANT if membership not ACTIVE
