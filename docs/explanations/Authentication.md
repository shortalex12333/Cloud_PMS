### Authentication 
⏺ Here's the full auth flow, step by step:

  1. User clicks "Sign in"

  Frontend calls Supabase Auth on the Master database:

  POST https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password
  Body: { email, password }

  ┌──────────┬─────────────────────────────────────────────────────────────────────────┐
  │   What   │                                  Value                                  │
  ├──────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Database │ Master Supabase (qvzmkaamzaqxpzbewjxe)                                  │
  ├──────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Table    │ auth.users (Supabase built-in, not visible in public schema)            │
  ├──────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Secret   │ NEXT_PUBLIC_SUPABASE_ANON_KEY — the anon JWT that allows the login call │
  └──────────┴─────────────────────────────────────────────────────────────────────────┘

  Returns: A JWT (access_token) + refresh_token. Supabase stores these in localStorage under sb-qvzmkaamzaqxpzbewjxe-auth-token. This JWT
  contains the user_id and is signed with the Master JWT secret.

  2. Frontend calls Bootstrap

  Immediately after login, AuthContext calls the Python backend:

  GET http://localhost:8000/v1/bootstrap
  Header: Authorization: Bearer <master_jwt>

  ┌─────────┬──────────────────────────────────────────────────────────────────────┐
  │  What   │                                Value                                 │
  ├─────────┼──────────────────────────────────────────────────────────────────────┤
  │ Backend │ Docker API on port 8000                                              │
  ├─────────┼──────────────────────────────────────────────────────────────────────┤
  │ Secret  │ SUPABASE_JWT_SECRET (on backend) — verifies the master JWT signature │
  └─────────┴──────────────────────────────────────────────────────────────────────┘

  Backend does:
  1. Decodes the JWT → extracts user_id
  2. Looks up user in Master DB → finds which yacht they belong to
  3. Looks up fleet_registry → gets yacht info + subscription status
  4. Returns: yacht_id, role, tenant_key_alias, subscription_status, subscription_plan, subscription_expires_at

  ┌─────────────────┬────────────────────────────────────────────────────────────────────────┐
  │      What       │                                 Value                                  │
  ├─────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Master DB table │ user_accounts (user→yacht mapping) + fleet_registry (yacht info)        │
  ├─────────────────┼────────────────────────────────────────────────────────────────────────┤
  │ Returns         │ yacht_id, role, tenantKeyAlias, subscription_status, subscription_plan │
  └─────────────────┴────────────────────────────────────────────────────────────────────────┘

  3. Frontend stores user context

  AuthContext builds a CelesteUser object:

  {
    id: "user-uuid",
    email: "x@alex-short.com",
    role: "captain",
    yachtId: "85fe1119-b04c-41ac-80f1-829d23322598",
    yachtName: "TEST_YACHT_001",
    tenantKeyAlias: "yTEST_YACHT_001",
    bootstrapStatus: "active",
    subscriptionActive: true,
    subscriptionStatus: "paid",
    subscriptionPlan: "professional",
  }

  2b. Subscription gate (between bootstrap and dashboard)

  The bootstrap response includes subscription fields from fleet_registry:
  - subscription_active: boolean (computed by backend: true if status is NULL, 'paid', or 'trial')
  - subscription_status: 'paid' | 'unpaid' | 'expired' | 'cancelled' | 'trial' (raw DB value, used for gate messages)
  - subscription_plan: 'none' | 'starter' | 'professional' | 'enterprise'
  - subscription_expires_at: ISO timestamp or null

  The backend computes subscription_active as a single boolean:
  - NULL status → true (legacy yachts, no enforcement)
  - 'paid' or 'trial' → true
  - 'unpaid', 'expired', 'cancelled' → false

  If subscription_active is false, the frontend shows a "Subscription Required"
  gate screen instead of the dashboard. The user stays authenticated but cannot
  access the app. Messages vary by subscription_status:

  - unpaid:    "Your vessel's subscription is awaiting payment..."
  - expired:   "Your subscription has expired. Contact Celeste to renew."
  - cancelled: "This subscription has been cancelled..."

  This is a frontend-only gate — the API does NOT block requests based on subscription.

  ┌──────────────────────┬────────────────────────────────────────────────────────────┐
  │ Field                │ Source                                                      │
  ├──────────────────────┼────────────────────────────────────────────────────────────┤
  │ subscription_active  │ Computed: status is NULL, 'paid', or 'trial'               │
  ├──────────────────────┼────────────────────────────────────────────────────────────┤
  │ subscription_status  │ fleet_registry.subscription_status (Master DB, raw)         │
  ├──────────────────────┼────────────────────────────────────────────────────────────┤
  │ subscription_plan    │ fleet_registry.subscription_plan (Master DB)                │
  ├──────────────────────┼────────────────────────────────────────────────────────────┤
  │ subscription_expires │ fleet_registry.subscription_expires_at (Master DB)          │
  └──────────────────────┴────────────────────────────────────────────────────────────┘

  4. All subsequent data calls go to Tenant DB

  Every Supabase query from the frontend hits the Tenant database:

  GET https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_faults?select=...
  Header: Authorization: Bearer <master_jwt>
  Header: apikey: <tenant_anon_key>

  ┌──────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
  │   What   │                                          Value                                           │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
  │ Database │ Tenant Supabase (vzsohavtuotocgrfkfyd)                                                   │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
  │ Secret   │ NEXT_PUBLIC_SUPABASE_ANON_KEY (tenant anon key)                                          │
  ├──────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
  │ Security │ RLS (Row Level Security) — every table has WHERE yacht_id = auth.uid() or similar policy │
  └──────────┴──────────────────────────────────────────────────────────────────────────────────────────┘

  The supabaseClient.ts is configured with the tenant URL and anon key — not the master.

  5. API calls go through Docker backend

  When the frontend calls the Python API (entity lens, signal, actions):

  GET http://localhost:8000/v1/entity/work_order/{id}
  Header: Authorization: Bearer <master_jwt>
  Header: X-Yacht-Signature: SHA-256(yacht_id + YACHT_SALT)  ← optional

  ┌───────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────┐
  │               What                │                                     Value                                     │
  ├───────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Backend verifies JWT with         │ SUPABASE_JWT_SECRET (master JWT secret)                                       │
  ├───────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Backend routes to tenant DB using │ tenantKeyAlias from the user lookup                                           │
  ├───────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────┤
  │ Optional extra check              │ YACHT_SALT — frontend and backend share this to verify yacht_id isn't spoofed │
  └───────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────┘

  6. Sign out

  await supabase.auth.signOut();  // Clears Supabase session from localStorage
  window.location.href = '/login'; // Hard redirect

  Clears the sb-*-auth-token from localStorage. No backend call needed.

  ---
  Summary: Secrets involved

  ┌───────────────────────────────┬─────────────────────────────────────────┬────────────────────────────────────┐
  │            Secret             │                Where Set                │              Purpose               │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ NEXT_PUBLIC_SUPABASE_URL      │ .env.local                              │ Tenant Supabase URL (data queries) │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ NEXT_PUBLIC_SUPABASE_ANON_KEY │ .env.local                              │ Tenant anon key (RLS-gated reads)  │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ NEXT_PUBLIC_API_URL           │ .env.local                              │ Python backend URL                 │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ NEXT_PUBLIC_YACHT_SALT        │ .env.local                              │ Shared secret for yacht signature  │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ SUPABASE_JWT_SECRET           │ Backend env                             │ Master JWT verification            │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ Master Supabase URL           │ Backend env                             │ User → yacht lookup                │
  ├───────────────────────────────┼─────────────────────────────────────────┼────────────────────────────────────┤
  │ Tenant DB credentials         │ Backend env (READ_DB_DSN, DATABASE_URL) │ Direct DB access for workers       │
  └───────────────────────────────┴─────────────────────────────────────────┴────────────────────────────────────┘

  The two databases

  ┌────────────────┬──────────────────────────────────┬─────────────────────────────────────────────────────┐
  │                │              Master              │                       Tenant                        │
  ├────────────────┼──────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ URL            │ qvzmkaamzaqxpzbewjxe.supabase.co │ vzsohavtuotocgrfkfyd.supabase.co                    │
  ├────────────────┼──────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Purpose        │ Auth + fleet registry + billing   │ All PMS data                                        │
  ├────────────────┼──────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Who queries it │ Backend only (bootstrap)         │ Frontend (Supabase client) + Backend (workers)      │
  ├────────────────┼──────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ Tables         │ auth.users, fleet mapping        │ pms_* tables (work orders, faults, equipment, etc.) │
  └────────────────┴──────────────────────────────────┴─────────────────────────────────────────────────────┘

