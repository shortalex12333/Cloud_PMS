# Architecture (As-Built) + Trust Boundaries

## Components
- MASTER Supabase:
  - auth.users (GoTrue)
  - user_accounts (or memberships) — mapping user→yacht + status
  - fleet_registry — yacht metadata + tenant alias
- TENANT Supabase:
  - auth_users_profiles — mirrors MASTER user_id to yacht_id for joins/helpers
  - auth_users_roles — yacht-scoped roles (authoritative for authorization)
  - pms_* tables — yacht-scoped data with RLS
  - storage objects — path-scoped by yacht_id
- Render API:
  - middleware verifies JWT, resolves membership, resolves role
  - Action Router validates intent, runs handlers, writes audit

## Trust boundaries (where you must assume hostile input)
1. Browser client (untrusted)
2. Agent device (semi-trusted, but still compromised possible)
3. Public internet (hostile)
4. Render API (trusted execution boundary; must be hardened)
5. Supabase projects (trusted but misconfig possible)
6. CI/CD pipeline (high-trust; supply-chain risk)

## High-level data flow
User/Agent → MASTER auth → JWT → Render middleware:
- verify JWT
- resolve yacht membership from MASTER
- resolve yacht role from TENANT
Then: Action Router dispatches to handler → TENANT DB/storage → audit logs

## Key rule: where tenant context lives
Tenant context must be resolved server-side:
- do not accept yacht_id from client (except “selected yacht” pointer validated by membership)
- do not let client call TENANT PostgREST with MASTER JWT
- do not stream data before tenant context is locked

## Required invariants (auditable)
- All mutations set yacht_id explicitly
- All reads include yacht_id predicate (even if RLS exists)
- All object storage paths start with yacht_id
- Every handler re-validates ownership of referenced resource IDs
