# Manual RLS Migration Required - HOR Lens

## Issue
CRITICAL RLS bypass: CREW role can read CAPTAIN data. This must be fixed before deployment.

## Migration File
`migrations/011_hor_rls_policy_fixes_v2.sql`

## How to Apply

### Option 1: Supabase Dashboard (RECOMMENDED)
1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new
2. Copy entire contents of `migrations/011_hor_rls_policy_fixes_v2.sql`
3. Paste into SQL editor
4. Click "Run"
5. Verify no errors

### Option 2: psql Command Line
```bash
export PGPASSWORD='<your-db-password>'
psql -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -p 5432 \
     -U postgres \
     -d postgres \
     -f migrations/011_hor_rls_policy_fixes_v2.sql
```

## What This Migration Does

### Fixes RLS Bypass
- **Before**: All policies allowed ANY authenticated user to SELECT
- **After**: Deny-by-default with explicit role-based access

### New Policies (`pms_hours_of_rest`)

**SELECT Policies:**
- `pms_hor_crew_view_own`: Crew can ONLY see own records (`user_id = auth.uid()`)
- `pms_hor_hod_view_department`: HOD can see department records
- `pms_hor_captain_view_all`: Captain can see all records
- `pms_hor_manager_view_all`: Manager can see all records

**INSERT Policies:**
- `pms_hor_crew_insert_own`: Crew can insert own records
- `pms_hor_hod_insert_department`: HOD can insert for department
- `pms_hor_captain_insert_any`: Captain/Manager can insert for anyone

**UPDATE Policies:**
- `pms_hor_crew_update_own`: Crew can update own records
- `pms_hor_hod_update_department`: HOD can update department records
- `pms_hor_captain_update_any`: Captain/Manager can update any

**DELETE Policies:**
- `pms_hor_captain_delete_any`: Only Captain/Manager can delete

### Verification Query
After applying, run this to verify policies exist:

```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename LIKE 'pms_h%' OR tablename LIKE 'pms_crew%'
ORDER BY tablename, policyname;
```

Expected: 20+ policies across 4 tables

## Testing After Migration

Run this test to verify CREW cannot see CAPTAIN data:

```bash
# As CREW user
curl -X POST http://localhost:8080/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_hours_of_rest",
    "context": {
      "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
      "user_id": "'$CREW_USER_ID'",
      "role": "crew"
    },
    "payload": {
      "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
      "user_id": "'$CAPTAIN_USER_ID'"
    }
  }'

# Expected: {"data": {"records": []}} OR 403 Forbidden
# NOT: 6 captain records
```

## Status
- [ ] Migration applied to Supabase
- [ ] Verification query run
- [ ] CREW cannot see CAPTAIN data (tested)
- [ ] HOD can see department data (tested)
- [ ] CAPTAIN can see all data (tested)
