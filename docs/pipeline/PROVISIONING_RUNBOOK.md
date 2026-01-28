User Provisioning & Mapping (MASTER → TENANT)
=============================================

Why
- The pipeline uses MASTER auth for JWTs and MASTER.user_accounts to route users to a tenant. The TENANT stores profiles/roles for RLS joins. You must set all three for tests to pass.

Steps (staging)
1) Create user in MASTER (admin API, service role):
   POST {MASTER_SUPABASE_URL}/auth/v1/admin/users
   Body: {"email":"user@...","password":"...","email_confirm":true}

2) Map user to tenant (MASTER.user_accounts):
   POST {MASTER_SUPABASE_URL}/rest/v1/user_accounts
   Body: {"id":"<MASTER_USER_ID>","email":"...","yacht_id":"<YACHT_ID>","display_name":"...","role":"chief_engineer","status":"active","email_verified":true}

3) Provision profile/role in TENANT:
   POST {TENANT_SUPABASE_URL}/rest/v1/auth_users_profiles
   Body: {"id":"<MASTER_USER_ID>","yacht_id":"<YACHT_ID>","email":"...","name":"...","is_active":true}

   POST {TENANT_SUPABASE_URL}/rest/v1/auth_users_roles
   Body: {"user_id":"<MASTER_USER_ID>","yacht_id":"<YACHT_ID>","role":"chief_engineer","is_active":true}

4) Obtain JWT from MASTER:
   POST {MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password
   Body: {"email":"...","password":"..."}

Notes
- Do not use service role JWTs for mutations; only user JWTs.
- For CI, this is automated in tests/ci/staging_certificates_acceptance.py (CREATE_USERS=true).

