# Security Tables Setup - 4-Part Installation

## ✅ Run These in Order

### **Part 1: Cleanup** (30 seconds)
Drops old tables, creates extensions

```sql
-- Copy and run: setup_part1_cleanup.sql
```

### **Part 2: Tables** (1 minute)
Creates 5 tables with indexes

```sql
-- Copy and run: setup_part2_tables.sql
```

### **Part 3: Functions & RLS** (1 minute)
Creates 4 functions and 15 RLS policies

```sql
-- Copy and run: setup_part3_functions_rls.sql
```

### **Part 4: Demo Data** (30 seconds)
Inserts demo yacht and creates triggers

```sql
-- Copy and run: setup_part4_demo_data.sql
```

---

## 🚀 How to Run

### **Option 1: Supabase SQL Editor (Recommended)**

1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
2. Copy contents of `setup_part1_cleanup.sql`
3. Paste and click **"Run"**
4. Wait for success message
5. Repeat for parts 2, 3, 4

### **Option 2: psql (All at once)**

```bash
cd Cloud_PMS

export PGPASSWORD='PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw'

psql -h db.vzsohavtuotocgrfkfyd.supabase.co -U postgres -d postgres \
  -f database/setup_part1_cleanup.sql \
  -f database/setup_part2_tables.sql \
  -f database/setup_part3_functions_rls.sql \
  -f database/setup_part4_demo_data.sql
```

---

## 📋 Expected Output

### After Part 1:
```
✓ Part 1 Complete - Old tables dropped, extensions enabled
```

### After Part 2:
```
✓ Part 2 Complete - Created 5 tables with indexes
```

### After Part 3:
```
✓ Part 3 Complete - Created 4 functions and 15 RLS policies
```

### After Part 4:
```
════════════════════════════════════════════════════════════
✓ SETUP COMPLETE - ALL 4 PARTS DONE
════════════════════════════════════════════════════════════
Tables: 5 / 5
RLS Policies: 15
Yachts: 1

Demo yacht ID: 00000000-0000-0000-0000-000000000001
════════════════════════════════════════════════════════════
```

---

## 🔍 Verify Installation

```sql
-- Check tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures')
ORDER BY table_name;
-- Expected: 5 rows

-- Check demo yacht
SELECT id, name, signature FROM yachts;
-- Expected: 1 row

-- Check RLS
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');
-- Expected: All showing rowsecurity = true
```

---

## ❓ Troubleshooting

### If Part 1 fails:
- Ignore "does not exist" errors (they're expected if tables don't exist)
- Continue to Part 2

### If Part 2 fails with "already exists":
- Run Part 1 again first
- Or drop tables manually in Supabase dashboard

### If Part 3 fails:
- Check that Part 2 completed successfully
- Verify all 5 tables exist

### If Part 4 trigger creation fails:
- This is normal (auth.users restrictions)
- You'll need to create users manually
- See below for manual user creation

---

## 👤 Manual User Creation (If Triggers Failed)

### Step 1: Create Auth User
Dashboard → Authentication → Users → "Add user"
- Email: admin@yacht.com
- Password: (set your password)

### Step 2: Get User ID
Copy the UUID from the users list

### Step 3: Create Profile
```sql
INSERT INTO user_profiles (id, yacht_id, email, name)
VALUES (
    'paste-user-uuid-here',
    '00000000-0000-0000-0000-000000000001',  -- Demo yacht
    'admin@yacht.com',
    'Admin User'
);
```

### Step 4: Assign Role
```sql
INSERT INTO user_roles (user_id, yacht_id, role, assigned_by)
VALUES (
    'paste-user-uuid-here',
    '00000000-0000-0000-0000-000000000001',  -- Demo yacht
    'admin',
    'paste-user-uuid-here'  -- Self-assigned
);
```

---

## ✅ All Done!

After running all 4 parts, you'll have:
- 5 secure tables
- 16 optimized indexes
- 15 RLS policies
- 4 helper functions
- 1 demo yacht
- Auto-user-creation (if triggers worked)

**Ready for production!**
