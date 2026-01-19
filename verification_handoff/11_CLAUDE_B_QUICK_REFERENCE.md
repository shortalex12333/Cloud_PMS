# 11_CLAUDE_B_QUICK_REFERENCE.md — Answers to Unasked Questions

**Purpose:** Fill gaps in the execution prompt so Claude B can start immediately without confusion.

---

## CRITICAL STARTUP CHECKLIST

Before ANY work, confirm you have:
- [ ] Access to Supabase Dashboard (for B001 fix)
- [ ] Access to Render Dashboard (for B001 fix)
- [ ] Ability to make curl requests to production
- [ ] Ability to take screenshots (for UI phases)

If ANY of these are blocked, STOP and escalate to human.

---

## B001 FIX PATH (EXACT STEPS)

You cannot proceed without fixing B001. Here's exactly how:

### Step 1: Get Supabase JWT Secret
```
1. Go to: https://supabase.com/dashboard
2. Select project: vzsohavtuotocgrfkfyd
3. Navigate: Project Settings → API
4. Find: "JWT Secret" (under "Project API keys")
5. Copy the secret value
```

### Step 2: Set in Render
```
1. Go to: https://dashboard.render.com
2. Find service: pipeline-core (or celeste-api)
3. Navigate: Environment → Environment Variables
4. Find or create: MASTER_SUPABASE_JWT_SECRET
5. Paste the JWT secret from Step 1
6. Click "Save Changes"
7. Trigger manual deploy (or wait for auto-deploy)
```

### Step 3: Verify Fix
```bash
# Login to get JWT
JWT=$(curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' | jq -r '.access_token')

# Test bootstrap (should return yacht context, not 401)
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json"
```

**Expected after fix:**
```json
{"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598", "status": "ACTIVE", ...}
```

**If still 401:** Redeploy failed or wrong secret copied. Retry from Step 1.

---

## KNOWN VALUES (DO NOT GUESS THESE)

| Item | Value |
|------|-------|
| Supabase Project ID | `vzsohavtuotocgrfkfyd` |
| Supabase URL | `https://vzsohavtuotocgrfkfyd.supabase.co` |
| Pipeline URL | `https://pipeline-core.int.celeste7.ai` |
| Production Frontend | `https://apps.celeste7.ai` |
| Test User Email | `x@alex-short.com` |
| Test User Password | `Password2!` |
| Test User ID | `a35cad0b-02ff-4287-b6e4-17c96fa6a424` |
| Test Yacht ID | `85fe1119-b04c-41ac-80f1-829d23322598` |
| Anon Key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE` |

**Service Key:** Available in Supabase Dashboard → Project Settings → API → `service_role` key
(Do NOT commit this key to files)

---

## EVIDENCE FILE NAMING

All evidence goes in: `/verification_handoff/evidence/`

Format: `{phase_id}_{short_description}.{ext}`

Examples:
- `01.01_login_response.json`
- `03.02_rls_positive_control.json`
- `06.04_email_thread_view.png`
- `08.15_add_to_handover_error.txt`

---

## PROGRESS FILE TEMPLATE

Create `/verification_handoff/CLAUDE_B_PROGRESS.md` with this structure:

```markdown
# CLAUDE_B_PROGRESS.md — Execution Log

## Session Start
**Date:** YYYY-MM-DD HH:MM
**Starting Phase:** XX.XX
**B001 Status:** BLOCKED / FIXED

---

## Phase XX.XX: [Phase Name]
**Started:** HH:MM
**Status:** PASSED / FAILED / BLOCKED
**Evidence:** `evidence/XX.XX_description.json`
**Notes:** [What happened]

---
```

Append each phase as you complete it. Never edit previous entries.

---

## UI TESTING METHOD

For phases requiring UI verification:

1. **Use browser** (or browser automation if available)
2. **Take screenshots** using system screenshot tool
3. **Save to evidence folder** with phase ID prefix
4. **Include console logs** if errors observed (copy text, save as .txt)

If you cannot access a browser:
- Mark UI phases as BLOCKED
- Document: "No browser access available"
- Continue with API-only phases

---

## DATABASE ACCESS

For SQL verification:

**Option A: Supabase Dashboard**
1. Go to Supabase Dashboard → SQL Editor
2. Run queries there
3. Screenshot or copy results

**Option B: curl with service key**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/{table}?select=*&limit=5" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

---

## ESCALATION PROTOCOL

"Escalate" means:

1. **STOP current work**
2. **Document the issue** in `03_KNOWN_BLOCKERS.md` with new ID (B007, B008, etc.)
3. **Update CLAUDE_B_PROGRESS.md** with blocked status
4. **Output message to human:** "BLOCKED: [issue]. Requires human intervention."
5. **Wait for human response** before continuing

Do NOT attempt workarounds for:
- Missing dashboard access
- Credentials not working
- Production site unreachable
- Evidence contradicting previous claims

---

## WHAT TO DO AFTER ALL 100 PHASES

When all phases are complete:

1. Create `/verification_handoff/FINAL_VERIFICATION_REPORT.md`
2. Include:
   - Summary: X PASSED, Y FAILED, Z BLOCKED
   - All remaining blockers
   - All fixed blockers
   - Recommendation: SHIP / DO NOT SHIP
3. Commit all evidence files
4. Output to human: "Verification complete. See FINAL_VERIFICATION_REPORT.md"

---

## THE 71 MICROACTIONS (Reference)

Located in: `apps/api/actions/action_registry.py`

Key actions to prioritize testing (P0):
1. `create_work_order`
2. `update_work_order`
3. `add_note_to_work_order`
4. `get_work_order_details`
5. `get_equipment_list`
6. `add_to_handover` (B005 - known issue)
7. `complete_work_order`
8. `assign_part_to_work_order`

Full inventory: Run `grep "action_id=" apps/api/actions/action_registry.py | wc -l` to confirm count.

---

## COMMON FAILURE PATTERNS

### "Invalid token: Signature verification failed"
→ B001 not fixed. Stop and fix B001.

### "relation does not exist"
→ B002 (missing table). Mark phase BLOCKED by B002.

### "PGRST202"
→ B003 (RPC mismatch). Mark phase BLOCKED by B003.

### Empty array `[]` when data expected
→ Check: Is this RLS working correctly (good) or data missing (bad)?
→ Verify by querying with service key. If service key returns data, RLS is correct.

### yacht_id is null
→ CRITICAL. Stop immediately. This should never happen after B001 fix.

---

## FILES YOU MUST READ (IN ORDER)

1. `00_EXEC_SUMMARY.md` - What's verified vs not
2. `01_SYSTEM_TRUTH_MAP.md` - Infrastructure facts
3. `02_EVIDENCE_LEDGER.md` - Existing evidence (don't redo)
4. `03_KNOWN_BLOCKERS.md` - Active blockers with code locations
5. `04_DO_NOT_TRUST_LIST.md` - Claims requiring your verification
6. `05_CODE_TO_DB_CROSSWALK.md` - What code expects vs what DB has
7. `06_TENANT_RESOLUTION_TRACE.md` - How yacht_id flows
8. `07_UX_DOCTRINE_CHECKLIST.md` - UI rules (hard requirements)
9. `08_10x10_EXECUTION_PLAN.md` - Your 100-phase plan
10. `10_EVIDENCE_INDEX.md` - Evidence already collected
11. `11_CLAUDE_B_QUICK_REFERENCE.md` - This file

---

## QUESTIONS ONLY HUMANS CAN ANSWER

If you need any of these, ask before proceeding:

1. "I need Render dashboard access to fix B001"
2. "I need the Supabase service_role key"
3. "I cannot access browser for UI testing"
4. "The test user credentials don't work"
5. "Production site is returning 5xx errors"

---

## START HERE

```
1. Read all files listed above (in order)
2. Attempt B001 fix (see exact steps above)
3. If B001 fix succeeds → Begin Phase 01.01
4. If B001 fix fails → STOP, escalate to human
```
