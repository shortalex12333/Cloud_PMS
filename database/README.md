# CelesteOS Database Setup

## 🚀 Quick Start

### Option 1: Run Complete Setup Script (Recommended)

1. **Copy the entire contents of `setup_complete.sql`**
2. **Open Supabase Dashboard → SQL Editor**
3. **Paste and click "Run"**
4. **Done!** All tables, functions, RLS policies created ✅

**File:** `database/setup_complete.sql` (373 lines, all-in-one)

---

## 📋 What Gets Created

### Tables
- ✅ `public.yachts` - Vessel information
- ✅ `public.user_profiles` - User data (linked to auth.users)
- ✅ `public.user_roles` - Role assignments (separate from profiles)
- ✅ `public.api_tokens` - Device/agent tokens
- ✅ `public.yacht_signatures` - Upload routing signatures

### Security
- ✅ Row Level Security (RLS) enabled on all tables
- ✅ Policies for user access control
- ✅ Helper functions: `get_user_role()`, `is_hod()`

### Extensions
- ✅ `uuid-ossp` - UUID generation
- ✅ `vector` - pgvector for embeddings
- ✅ `pg_trgm` - Text search optimization
- ✅ `btree_gin` - Multi-column indexes

### Sample Data
- ✅ Demo yacht (ID: `00000000-0000-0000-0000-000000000001`)

---

## 🧪 Create Test Users

After running the setup script, create test users:

### Step 1: Create Supabase Auth User

**Supabase Dashboard → Authentication → Users → Add User**
- Email: `test@yacht.com`
- Password: `YourPassword123`
- Auto-confirm: ✅

**Copy the User ID** (UUID shown in the user list)

### Step 2: Create User Profile

```sql
INSERT INTO public.user_profiles (id, yacht_id, email, name)
VALUES (
    '<auth-user-id>',  -- UUID from Step 1
    '00000000-0000-0000-0000-000000000001',  -- Demo yacht
    'test@yacht.com',
    'Test User'
);
```

### Step 3: Assign Role

```sql
-- For HOD (Head of Department) user:
INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
VALUES (
    '<auth-user-id>',
    '00000000-0000-0000-0000-000000000001',
    'chief_engineer',  -- or 'captain' or 'manager'
    '<auth-user-id>'
);

-- For regular crew:
INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
VALUES (
    '<auth-user-id>',
    '00000000-0000-0000-0000-000000000001',
    'crew',
    '<auth-user-id>'
);
```

---

## 🔐 Valid Roles

### HOD (Head of Department)
- `chief_engineer`
- `captain`
- `manager`

### Regular Users
- `eto`
- `vendor`
- `crew`
- `deck`
- `interior`

---

## 📖 Detailed Documentation

For comprehensive security architecture docs, see:
- **`SECURITY_ARCHITECTURE.md`** - Full security explanation
- **`migrations/01_core_tables_v2_secure.sql`** - Individual table definitions
- **`migrations/02_auth_sync_trigger.sql`** - Auto-sync triggers

---

## ⚠️ Troubleshooting

### "Permission denied for schema auth"

This is expected when creating triggers on `auth.users`. The setup script handles this gracefully.

**Workaround:** Create users manually using Steps 1-3 above.

### Tables already exist

If you run the script multiple times, it will skip existing tables (uses `IF NOT EXISTS`).

To completely reset:
```sql
DROP TABLE IF EXISTS public.yacht_signatures CASCADE;
DROP TABLE IF EXISTS public.api_tokens CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.yachts CASCADE;

-- Then run setup_complete.sql again
```

---

## ✅ Verification

After running the script, you should see:
```
✓ Created 5 tables
✓ Database setup complete!
```

Check tables exist:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

---

## 🎯 Next Steps

1. ✅ Run `setup_complete.sql`
2. ✅ Create test users (Steps 1-3 above)
3. ✅ Test login on frontend: `https://your-app.vercel.app/login`
4. ✅ Check console logs for auth flow
5. ✅ Create production yacht and users

---

## 📝 Notes

- **Frontend is already configured** to work with this schema
- **AuthContext queries** `user_profiles` and `user_roles` automatically
- **Build passes** ✅ and deployed to production branch
- **All committed** to branch: `claude/deploy-production-01TwqiaKXUk14frUXUPkVKTj`
