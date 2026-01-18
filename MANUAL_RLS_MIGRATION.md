# MANUAL ACTION REQUIRED: Apply RLS Migration

## Status: BLOCKER - Cannot be applied via CLI

## Why Manual?
- Supabase CLI migration history conflicts prevent `supabase db push`
- Direct psql connection requires Management API access token not available
- REST API doesn't expose arbitrary SQL execution

## How to Apply

1. Go to Supabase Dashboard: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
2. Navigate to SQL Editor
3. Copy and paste the contents of: `supabase/migrations/20260117_000_fix_rls_user_accounts_bug.sql`
4. Execute

## What This Fixes

7 tables have RLS policies that reference non-existent `user_accounts` table:
- pms_checklists
- pms_checklist_items
- pms_attachments
- pms_worklist_tasks
- pms_work_order_checklist
- handovers
- handover_items

The migration changes these to reference `auth_users_profiles` which exists.

## Verification After Applying

Run this SQL to verify:
```sql
SELECT tablename, policyname
FROM pg_policies
WHERE policyname LIKE 'yacht_isolation%'
ORDER BY tablename;
```

Expected: 28 rows (4 policies × 7 tables)

## Impact If Not Applied

- RLS policies will fail at runtime when accessing these tables
- Users may get permission denied errors
- Data isolation could be compromised
