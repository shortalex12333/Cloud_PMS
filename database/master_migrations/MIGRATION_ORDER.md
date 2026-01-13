# Master DB Migration Order

Execute these migrations in order on the **Master Supabase project** (qvzmkaamzaqxpzbewjxe).

## Prerequisites

1. Access to Supabase SQL Editor for master project
2. Backup of existing data (if any)

## Migration Order

| Order | File | Description |
|-------|------|-------------|
| 1 | `000_create_fleet_registry.sql` | Tenant registry table |
| 2 | `001_create_user_accounts.sql` | User → yacht mapping |
| 3 | `002_create_db_registry.sql` | Server-only tenant DB mapping |
| 4 | `003_create_security_events.sql` | Audit trail table |
| 5 | `004_create_get_my_bootstrap_rpc.sql` | Bootstrap RPC for frontend |
| 6 | `005_create_ensure_user_account_rpc.sql` | Account creation RPC |

## Execution

```sql
-- Run each file in order in Supabase SQL Editor
-- Check for ✅ success messages after each migration
```

## Rollback

To rollback (if needed):

```sql
-- WARNING: This will delete all data in these tables
DROP FUNCTION IF EXISTS public.ensure_user_account(TEXT, TEXT);
DROP FUNCTION IF EXISTS public.get_my_bootstrap();
DROP FUNCTION IF EXISTS public.log_security_event(TEXT, JSONB, TEXT);
DROP TYPE IF EXISTS public.bootstrap_result;
DROP TABLE IF EXISTS public.security_events;
DROP TABLE IF EXISTS public.db_registry;
DROP TABLE IF EXISTS public.user_accounts;
-- DO NOT drop fleet_registry if it contains existing data
```

## Post-Migration Verification

```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('fleet_registry', 'user_accounts', 'db_registry', 'security_events');

-- Check RPCs exist
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('get_my_bootstrap', 'ensure_user_account', 'log_security_event');

-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('fleet_registry', 'user_accounts', 'db_registry', 'security_events');
```
