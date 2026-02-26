Claude — clarification on our DB architecture (this is intentional, not a mistake):

We run a 2-DB gateway model:

1) MASTER Supabase project (AUTH + directory)
   - URL: https://qvzmkaamzaqxpzbewjxe.supabase.co
   - Purpose: user authentication + global directory/lookup
   - Used by: Vercel (apps/web) for login + session bootstrap
   - Data in master: users, account verification state, mapping of user_id -> yacht_id(s), role tier, and tenant connection info (or tenant slug/id)
   - IMPORTANT: Master is NOT where yacht operational data lives.

2) TENANT Supabase project (yacht operational data)
   - URL: https://vzsohavtuotocgrfkfyd.supabase.co
   - Purpose: yacht-specific data + actions + documents + indexes
   - Used by: Render backend (apps/api) for ALL read/mutate actions and search indexes.
   - The tenant DB is multi-tenant internally: tables are shared but separated by yacht_id (and user_id), with server-side filters/RLS.
   - i.e. “Tenant” here means “operational DB”, not “one DB per yacht” (at least in current setup).

Request flow (two-DB gateway):
- User signs in on Vercel against MASTER.
- Frontend receives JWT/session (master).
- Requests go to Render API.
- Render verifies the master JWT (MASTER_SUPABASE_JWT_SECRET) and resolves:
    user_id -> yacht_id + role tier + permissions
- Render then routes queries to TENANT DB (vzsohavtuotocgrfkfyd) and enforces yacht_id scoping on every query.
- Frontend should NOT directly talk to tenant DB for operational data; that is gated via Render.

About the mismatch you saw:
- If pipeline-core is connecting to qvzmkaamzaqxpzbewjxe (MASTER), that’s wrong for indexing/operational tables.
- The GIST index you created on vzsohavtuotocgrfkfyd (TENANT) is correct — but it will only help if pipeline-core is actually hitting TENANT.

Action items:
1) Confirm pipeline-core DB target:
   - Check env vars in Render (apps/api) and in pipeline-core process:
     - MASTER_SUPABASE_URL should be qvzmkaamzaqxpzbewjxe (auth only)
     - TENANT_SUPABASE_URL / <tenant>_SUPABASE_URL should be vzsohavtuotocgrfkfyd (operational)
   - If you see NEXT_PUBLIC_SUPABASE_URL in server code paths, that’s likely the bug (it points to master).

2) Apply index only where the operational tables live:
   - If pipeline-core queries operational tables (documents/chunks/entities/etc.), indexes must be on TENANT DB.
   - Only add indexes on MASTER if they’re for auth/directory lookup tables.

3) If you still need to add the same GIST index on MASTER:
   - That implies pipeline-core is incorrectly using MASTER for an operational table.
   - We should fix routing rather than duplicate indexes in MASTER.

In short:
- qvzmkaamzaqxpzbewjxe = MASTER (auth/directory)
- vzsohavtuotocgrfkfyd = TENANT (operational multi-tenant via yacht_id/user_id)
- Vercel uses MASTER for auth bootstrap.
- Render + pipeline-core should use TENANT for actions/data/indexing, and use MASTER only to validate JWT and resolve yacht_id/role.