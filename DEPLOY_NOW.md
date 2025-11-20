# Deploy All Migrations - Quick Start

## Step 1: Install Supabase CLI (One Time)

### macOS
```bash
brew install supabase/tap/supabase
```

### Linux
```bash
curl -fsSL https://raw.githubusercontent.com/supabase/cli/main/scripts/install.sh | sh
```

### Windows
```powershell
scoop install supabase
```

## Step 2: Link to Your Project (One Time)

```bash
cd Cloud_PMS

# Login (opens browser)
supabase login

# Link to your project
supabase link --project-ref vzsohavtuotocgrfkfyd
# When prompted for password: PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw
```

## Step 3: Deploy Everything

```bash
./DEPLOY_ALL_MIGRATIONS.sh
```

**That's it!** The script will:
- ✅ Deploy all 21 migrations (000-020)
- ✅ Create all tables, indexes, functions, policies
- ✅ Set up storage buckets with hierarchical permissions
- ✅ Insert demo yacht
- ✅ Verify deployment success

## What Gets Deployed

### Core Schema (000-006)
- pgvector extension
- documents, embeddings, queries tables
- Search functions
- RLS policies
- Triggers

### Storage (007-010)
- Storage buckets (documents, raw-uploads)
- Storage helper functions
- Storage RLS policies
- Documents metadata RLS

### Hierarchical Storage (011-016)
- system_path column for directory structure
- role_directory_permissions table
- Hierarchical storage functions (10 functions)
- Directory-based RLS policies
- MIME restriction removal

### Security Tables (017-020)
- yachts table
- user_profiles table
- user_roles table
- api_tokens table
- yacht_signatures table
- Security helper functions
- RLS policies for all security tables
- Demo data + triggers

## After Deployment

1. **Verify in Supabase Dashboard**:
   - Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/editor
   - Check that tables exist: yachts, user_profiles, documents, embeddings, etc.

2. **Create demo user**:
   - Dashboard → Authentication → Users → Add user
   - Email: admin@yacht.com
   - Password: (your choice)

3. **Test Worker 4 upload**:
   - Run n8n workflow
   - Should now work without "bucket not found" or "MIME type" errors

## Troubleshooting

### "supabase: command not found"
Install CLI using commands in Step 1

### "Project not linked"
Run `supabase link --project-ref vzsohavtuotocgrfkfyd`

### "Migration already applied"
That's fine! Migrations are idempotent (safe to re-run)

### Want to see migration details?
```bash
supabase db status
```

---

**NO MORE MANUAL PASTING - Everything is automated! 🎉**
