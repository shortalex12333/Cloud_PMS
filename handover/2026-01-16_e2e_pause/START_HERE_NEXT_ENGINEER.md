# CelesteOS - Cloud PMS Project

## STARTING POINT

You are working on **CelesteOS**, a multi-tenant yacht maintenance management system with:
- **Frontend:** Next.js (Vercel) - https://app.celeste7.ai
- **Backend:** Python FastAPI (Render) - https://pipeline-core.int.celeste7.ai
- **Database:** Supabase PostgreSQL (MASTER for auth, TENANT for data)

**Your codebase is at:** `/Users/celeste7/Documents/Cloud_PMS`

## READ THIS FIRST

**Complete handover package is here:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS
cat handover/2026-01-16_e2e_pause/00_README.md
```

**That file contains:**
- What changed recently (last commits)
- Known-good vs unknown status
- Exact resume commands
- DO NOT TOUCH list
- Architecture notes

**For complete Q&A:** `cat handover/2026-01-16_e2e_pause/SNAPSHOT_SUMMARY.md`

## CURRENT STATUS (2026-01-16)

### ✅ WORKING:
- **Outlook OAuth:** ✅ FULLY WORKING - Real Microsoft tokens stored
  - Only needs: FK constraint removal (5-second SQL command)
  - See: `handover/2026-01-16_e2e_pause/OUTLOOK_INTEGRATION_HANDOVER.md`

- **Microactions:** 57 handlers implemented, tests passing
  - Contract tests: 16/16 passing
  - Frontend build: passing
  - Diagnostic tests: 4/4 passing locally

- **E2E Infrastructure:** Localhost CI setup, MASTER/TENANT config fixed

### ❓ UNKNOWN:
- E2E login tests: Previous runs timed out (fixes applied, status unknown)
- Run 21073217479: Was in progress when paused

### ⚠️ IMMEDIATE ACTIONS NEEDED:

**1. Check E2E Test Status:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS
gh run view 21073217479 --json status,conclusion
# If failed, download artifacts and investigate
```

**2. Remove Email Watchers FK Constraint:**
```sql
-- Run in Supabase Dashboard (TENANT DB: vzsohavtuotocgrfkfyd)
ALTER TABLE email_watchers
DROP CONSTRAINT IF EXISTS email_watchers_user_id_fkey;
```

**3. Test Email Fetch with Stored Token:**
```bash
# Get token from database, then:
curl "https://graph.microsoft.com/v1.0/me/messages?$top=10" \
  -H "Authorization: Bearer [TOKEN_FROM_auth_microsoft_tokens]"
```

## ARCHITECTURE (CRITICAL TO UNDERSTAND)

### MASTER vs TENANT Supabase:
```
MASTER DB (qvzmkaamzaqxpzbewjxe.supabase.co)
├─ auth.users (Supabase auth)
├─ user_accounts (user → yacht + role mapping)
└─ get_my_bootstrap() RPC
└─ Purpose: Authentication ONLY

TENANT DB (vzsohavtuotocgrfkfyd.supabase.co)
├─ pms_work_orders, pms_equipment, etc.
├─ auth_microsoft_tokens (OAuth tokens with MASTER user_id, no FK)
├─ email_watchers (sync status, FK needs removal)
└─ Purpose: Yacht-specific data
```

**Key:** Frontend uses MASTER for login, TENANT for data. User IDs from MASTER are used everywhere, even in TENANT tables.

## KEY FILES TO READ

**Handover Package (START HERE):**
```
handover/2026-01-16_e2e_pause/
├── 00_README.md                      ← Quick start
├── SNAPSHOT_SUMMARY.md               ← Complete Q&A
├── OUTLOOK_INTEGRATION_HANDOVER.md   ← OAuth status (WORKING!)
└── MANIFEST.md                       ← File listing
```

**Project Documentation:**
```
/CLAUDE.md                            ← Project memory & context
/COMPLETE_ACTION_EXECUTION_CATALOG.md ← All 57 microactions spec
/AUTONOMOUS_TESTING_GUIDE.md          ← Testing strategy
```

**Recent Work:**
```
/OUTLOOK_OAUTH_FINAL_REPORT.md        ← OAuth debugging (3 issues fixed)
/E2E_DIAGNOSIS_FINAL.md               ← E2E investigation
```

## CREDENTIALS & ACCESS

**DO NOT search for credentials in code.** All secrets are in:
```
handover/2026-01-16_e2e_pause/SECRETS_AND_ACCESS.md
```

That file contains:
- GitHub secret NAMES (not values - check GitHub secrets)
- Supabase dashboard links
- Test user email (password in GitHub secrets)
- Azure OAuth app IDs (secrets in Render env vars)

**All actual secret VALUES are redacted** - file tells you WHERE to find them.

## COMMON COMMANDS

```bash
# Check git status
cd /Users/celeste7/Documents/Cloud_PMS
git status
git log -5 --oneline

# Run tests
npm run test:unit           # Unit tests (Vitest)
npx playwright test         # E2E tests (Playwright)

# Check GitHub Actions
gh run list --limit 5
gh run view [RUN_ID] --log

# Start local development
cd apps/api && uvicorn pipeline_service:app --reload  # API on :8000
cd apps/web && npm run dev                             # Frontend on :3000

# Check deployments
curl https://pipeline-core.int.celeste7.ai/health  # Render API
curl https://app.celeste7.ai                       # Vercel frontend
```

## BACKUP & RESTORE

**Backup exists at:** `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/`

If you mess up, restore with:
```bash
cp -r /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS ~/Desktop/Cloud_PMS_restored
cd ~/Desktop/Cloud_PMS_restored
git log -1  # Should show: cdfa925 (OAuth docs commit)
```

## LESSONS FROM PREVIOUS WORK

**DO:**
- ✅ Read the handover docs FIRST before touching code
- ✅ Verify table/column names against actual database (don't trust code)
- ✅ Test with real authentication (not service keys that bypass RLS)
- ✅ Run E2E tests against localhost in CI, not production
- ✅ Understand MASTER (auth) → TENANT (data) architecture

**DON'T:**
- ❌ Commit actual secret values (JWT tokens, passwords, etc.)
- ❌ Force-push or rebase without asking
- ❌ Assume column names - verify in database
- ❌ Skip reading the handover package
- ❌ Test against production when you need to verify PR changes

## WHAT'S NEXT (PRIORITY ORDER)

**High Priority:**
1. Check E2E run 21073217479 status
2. Remove email_watchers FK constraint (if not done)
3. Test email fetch with stored OAuth token
4. Build email sync worker

**Medium Priority:**
5. Verify all 57 microactions wired up in frontend
6. Test production deployment end-to-end
7. Verify RLS policies with real user tokens

**Low Priority:**
8. Clean up old documentation files
9. Update README with latest architecture
10. Add frontend UX for OAuth connection status

## QUESTIONS YOU MIGHT HAVE

**Q: Where do I start?**
A: Read `handover/2026-01-16_e2e_pause/00_README.md` first. It has exact commands.

**Q: What's broken?**
A: E2E tests may still be timing out (check run 21073217479). OAuth FK constraint needs removal.

**Q: What's working?**
A: OAuth flow complete (real tokens stored), 57 microactions implemented, contract tests passing.

**Q: Where are secrets?**
A: GitHub secrets, Supabase dashboard, Render env vars. See `SECRETS_AND_ACCESS.md` for locations.

**Q: Can I merge to main?**
A: Check E2E status first. If passing, yes. If failing, fix before merging.

**Q: What if I break something?**
A: Restore from `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/`

## FINAL NOTE

This project has **complete handover documentation** because previous AI agents made mistakes by:
- Not reading existing docs
- Not verifying database schema
- Not understanding MASTER vs TENANT
- Not testing with real auth

**You have everything you need.** Read the handover package, follow the exact commands, and you'll be productive in 5 minutes.

**If confused:** Read `handover/2026-01-16_e2e_pause/SNAPSHOT_SUMMARY.md` - it answers literally everything.

---

**Ready to start? Run this:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS
cat handover/2026-01-16_e2e_pause/00_README.md
```
