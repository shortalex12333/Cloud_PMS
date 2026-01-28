# Architecture Overview (Self-contained)

MASTER:
- auth.users (identity and JWT issuance)
- user_accounts/memberships (user→yacht mapping + status)
- fleet_registry (yacht metadata + tenant_key_alias + freeze flags)

TENANT:
- auth_users_profiles (mirror ids for joins/helpers)
- auth_users_roles (authoritative yacht roles)
- pms_* tables (yacht-scoped)
- storage (keys prefixed by yacht_id)
- RLS as backstop

Render Action Router:
- central policy enforcement
- server-side execution
- audit emission
