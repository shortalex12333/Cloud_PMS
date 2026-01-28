# Schema Appendix (Mapped to Your Narrative)

## MASTER (Control Plane)
- auth.users (GoTrue) — identity
- user_accounts / memberships — user→yacht mapping and status
  Recommended:
  - membership_id (uuid)
  - user_id (uuid)
  - yacht_id (uuid)
  - status (invited|active|revoked|locked)
  - invited_by, approved_by
  - valid_until
  - created_at, updated_at
  Constraints:
  - UNIQUE(user_id, yacht_id)
- fleet_registry — yacht metadata + tenant alias
  - yacht_id, yacht_name, active, tenant_key_alias

## TENANT (Data Plane)
- auth_users_profiles
  - id (user_id), yacht_id, email, name, is_active, metadata, timestamps
- auth_users_roles
  - id, user_id, yacht_id, role, is_active, assigned_by, assigned_at, valid_until
  Constraints:
  - partial unique on (user_id, yacht_id) where is_active = true (optional)
- pms_* tables
  - MUST include yacht_id NOT NULL
  - RLS policies enforce yacht_id = get_user_yacht_id() (backstop)
- audit table (recommended)
  - id, yacht_id, actor_user_id, actor_role, action_name, payload_hash, outcome, created_at
- storage policies
  - foldername(name)[1] == yacht_id

## Helper function guidance
- Helpers can exist, but production enforcement is:
  - middleware context + handler validation
  - policies as backstop
