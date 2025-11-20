# Install Supabase CLI - Then I'll Push Everything

## Quick Install (Pick Your OS)

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
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

## After Install - Link to Your Project

```bash
# Login (opens browser)
supabase login

# Link to your project
supabase link --project-ref vzsohavtuotocgrfkfyd
# Password: PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw
```

## Then Tell Me "Done"

Once you've run those commands and linked the project, I'll immediately push:
1. All storage migrations (007-016)
2. Hierarchical storage functions
3. Any remaining security tables
4. Verify everything deployed correctly

**No more manual pasting - I'll handle everything via CLI.**

---

## What Happens Next

After you link the project, I'll run:
```bash
cd /home/user/Cloud_PMS
supabase db push
```

This will:
- ✅ Apply all migrations in order
- ✅ Show progress for each migration
- ✅ Automatically rollback on errors
- ✅ Verify deployment success
- ✅ No manual copy-paste

**Just install CLI + link project, then say "done" and I'll handle the rest.**
