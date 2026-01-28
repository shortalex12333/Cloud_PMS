# Access Lifecycle (How to Add Users Safely)

Manual DB edits are banned in production. The only safe path is an auditable workflow.

## Entities (recommended)
- memberships (MASTER): membership_id, user_id, yacht_id, status, invited_by, approved_by, created_at, valid_until
- invites (MASTER): invite_id, membership_id, one_time_token_hash, expires_at, used_at
- roles (TENANT): user_id, yacht_id, role, is_active, assigned_by, assigned_at, valid_until

## Workflow: Invite → Accept → Provision → Active
### 1) Sponsor invites user (admin UI → Action Router)
- Create or link MASTER auth user
- Create membership with status=INVITED
- Create invite token (one-time, expires)
- Send email (delivery is best-effort; token remains server-validated)

### 2) User accepts invite
- Logs into MASTER
- Redeems token → membership moves to PENDING_PROVISION

### 3) Provisioning (server-side only)
- Action Router provisions TENANT rows (idempotent upserts):
  - profiles upsert
  - roles insert/upsert
- membership becomes ACTIVE
- audit event written

### 4) Revocation
- membership status = REVOKED
- roles set inactive in TENANT
- cache cleared
- device tokens revoked if needed
- audit event written

## Safe defaults
- Default role = least privilege
- Contractors must have valid_until
- Captain/Manager requires approval gate
- Shore-side Celeste staff cannot assign privileged roles unilaterally

## Success criteria
- Adding user never requires DB console access.
- Provisioning is idempotent and retry-safe.
- Revocation takes effect within a bounded TTL.
