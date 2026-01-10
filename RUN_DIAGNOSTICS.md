# 🔍 How to Run Complete Document Access Diagnostics

This guide walks you through running 3 comprehensive diagnostic checks to identify why documents can't be accessed.

---

## Overview

You have 3 diagnostic tools:

1. **diagnostic_sql.sql** - Database configuration & data checks
2. **diagnostic_browser.js** - Frontend/browser console checks
3. **diagnostic_code_review.md** - Code logic analysis (read-only)

**Run all 3 for complete diagnosis.**

---

## DIAGNOSTIC 1: Database Checks (SQL)

### What It Checks
- RPC function configuration (`row_security = off`)
- User authentication & yacht assignment
- Document data existence (chunks & metadata)
- RLS policies
- Foreign key relationships

### How to Run

#### Step 1: Open Supabase SQL Editor
1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
2. Click **SQL Editor** in left sidebar
3. Click **New query**

#### Step 2: Update User ID Placeholders
Open `diagnostic_sql.sql` and find these lines:
```sql
v_user_id UUID := 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';  -- REPLACE THIS
```

Replace with your actual user ID from:
```sql
SELECT id, email FROM auth.users WHERE email = 'x@alex-short.com';
```

#### Step 3: Copy & Paste Script
1. Copy entire contents of `diagnostic_sql.sql`
2. Paste into Supabase SQL Editor
3. Click **Run** (or press Cmd/Ctrl+Enter)

#### Step 4: Copy Results
1. Wait for all checks to complete
2. Click **Results** tab at bottom
3. Copy ALL output
4. Save to file: `diagnostic_results_sql.txt`

### Expected Output
```
=== CHECK 1: RPC Function Configuration ===
✅ row_security is OFF

=== CHECK 2: User Authentication & Yacht Assignment ===
✅ User configured correctly

=== CHECK 3: Document Data Exists ===
✅ Chunks exist

... (more checks)
```

### Red Flags to Look For
- ❌ row_security NOT disabled
- ❌ No yacht_id assigned
- ❌ No chunks found for your yacht
- ❌ Missing storage_path in doc_metadata

---

## DIAGNOSTIC 2: Frontend Checks (Browser Console)

### What It Checks
- Supabase client initialization
- JWT session validity
- User profile & yacht assignment (from frontend perspective)
- Document chunks query with RLS
- RPC function execution
- Actual error messages from failed calls

### How to Run

#### Step 1: Login to App
1. Go to your app URL (Vercel deployment)
2. Login with your credentials
3. Wait for dashboard to load

#### Step 2: Open Browser Console
- **Chrome/Edge:** Press F12 or Cmd+Option+I (Mac) or Ctrl+Shift+I (Windows)
- **Firefox:** Press F12 or Cmd+Option+K (Mac) or Ctrl+Shift+K (Windows)
- **Safari:** Enable Developer menu, then Cmd+Option+C

#### Step 3: Paste Diagnostic Script
1. Click **Console** tab
2. Copy entire contents of `diagnostic_browser.js`
3. Paste into console
4. Press Enter

#### Step 4: Wait for Completion
Script will run all checks and print summary:
```
🔍 Starting Document Access Diagnostics...

=== CHECK 1: Supabase Client & Session ===
✅ Session found
  User ID: a35cad0b-...
  Email: x@alex-short.com
  Expires: [date]
  Status: ✅ Valid

... (more checks)

📊 DIAGNOSTIC SUMMARY
✅ PASSED CHECKS:
  ✅ 1.1 Session Valid
  ✅ 2.1 User Profile
  ...

❌ ERRORS:
  ❌ RPC: Document not found or access denied

💡 RECOMMENDATION:
🔍 Multiple issues detected - review errors above
```

#### Step 5: Copy Output
1. Right-click in console
2. Select "Save as..." or copy all text
3. Save to file: `diagnostic_results_browser.txt`

### Red Flags to Look For
- ❌ Session expired
- ❌ User not in auth_users_profiles
- ❌ No chunks found
- ❌ RPC error code P0001
- ❌ RPC: Possible RLS blocking

---

## DIAGNOSTIC 3: Code Review (Manual Analysis)

### What It Covers
- DocumentSituationView.tsx logic errors
- documentLoader.ts validation issues
- RPC function implementation flaws
- storage_path format mismatches

### How to Review

#### Step 1: Open Code Review Document
Read `diagnostic_code_review.md`

#### Step 2: Check Red Flags
Focus on the "RED FLAGS IDENTIFIED" section:

**🔴 High Severity:**
1. RPC error message too vague
2. Path format validation might reject valid paths

**⚠️ Medium Severity:**
3. No validation of metadata object
4. No caching of getYachtId()

#### Step 3: Run Recommended Tests
The document includes 3 quick tests at the bottom:

**Test 1: Check storage_path format**
```sql
-- Copy from diagnostic_code_review.md
-- Paste in Supabase SQL Editor
```

**Test 2: Verify RPC configuration**
```sql
-- Copy from diagnostic_code_review.md
-- Paste in Supabase SQL Editor
```

**Test 3: Test RPC with known chunk**
```javascript
// Copy from diagnostic_code_review.md
// Paste in browser console
```

---

## Collecting Results

### Create Summary Report

Create a file: `diagnostic_summary.txt`

```
=============================================================================
DOCUMENT ACCESS DIAGNOSTIC REPORT
Date: [today's date]
User: x@alex-short.com
=============================================================================

DIAGNOSTIC 1: SQL Results
-------------------------
[Paste output from diagnostic_sql.sql]

DIAGNOSTIC 2: Browser Console Results
--------------------------------------
[Paste output from diagnostic_browser.js]

DIAGNOSTIC 3: Code Review Tests
--------------------------------
Test 1 (storage_path format):
[Paste SQL results]

Test 2 (RPC configuration):
[Paste SQL results]

Test 3 (RPC with known chunk):
[Paste browser console results]

=============================================================================
SUMMARY OF ISSUES FOUND
=============================================================================
[ ] RPC missing row_security = off
[ ] User has no yacht_id assigned
[ ] No chunks in search_document_chunks
[ ] No documents in doc_metadata
[ ] storage_path format mismatch
[ ] RLS policies missing COALESCE fallback
[ ] Session expired
[ ] Other (describe): _______________

=============================================================================
```

---

## Interpreting Results

### Common Issue Patterns

#### Pattern 1: "❌ row_security NOT disabled"
**Cause:** Migration not deployed
**Fix:** Deploy RPC migration with `SET row_security = off`
**Files Affected:** Database function

#### Pattern 2: "❌ No yacht_id assigned"
**Cause:** User not configured in auth_users_profiles
**Fix:** Insert/update user record with yacht_id
**Files Affected:** Database table auth_users_profiles

#### Pattern 3: "❌ No chunks found"
**Cause:** Documents not indexed yet
**Fix:** Run document indexing pipeline
**Files Affected:** search_document_chunks table

#### Pattern 4: "❌ RPC: Document not found or access denied"
**Could Be:**
- Document doesn't exist (invalid chunk_id from search)
- Document exists but wrong yacht (security working)
- storage_path missing in doc_metadata

**Next Steps:**
- Check DIAGNOSTIC 1 results for doc_metadata.storage_path
- Check DIAGNOSTIC 3 Test 3 to verify chunk_id exists

#### Pattern 5: "❌ Invalid document path - yacht isolation check failed"
**Cause:** storage_path format doesn't match expected format
**Fix:** Check DIAGNOSTIC 3 Test 1 results
**Files Affected:** doc_metadata.storage_path or documentLoader.ts validation

#### Pattern 6: "❌ Session expired"
**Cause:** JWT token expired
**Fix:** Refresh page and login again
**Files Affected:** None (user action needed)

---

## What to Share for Help

If you need assistance, share:

1. ✅ `diagnostic_results_sql.txt` (database checks)
2. ✅ `diagnostic_results_browser.txt` (frontend checks)
3. ✅ Results from 3 code review tests
4. ✅ Any error messages from browser console when clicking "View Document"
5. ✅ Screenshot of the error shown to user

**Do NOT share:**
- ❌ Database passwords
- ❌ JWT tokens
- ❌ Service role keys
- ❌ User email addresses (can redact)

---

## Quick Start

**Fastest way to diagnose:**

```bash
# 1. Run SQL diagnostic (5 minutes)
# - Open Supabase SQL Editor
# - Paste diagnostic_sql.sql
# - Run and save output

# 2. Run browser diagnostic (2 minutes)
# - Login to app
# - Open console (F12)
# - Paste diagnostic_browser.js
# - Save output

# 3. Review code diagnostic (5 minutes)
# - Read diagnostic_code_review.md
# - Run 3 quick tests
# - Note any red flags

# Total time: ~12 minutes
```

---

## After Running Diagnostics

### Next Steps

1. **Review all outputs** for errors marked with ❌
2. **Identify primary issue** (most common: RPC config, missing yacht_id, or no data)
3. **Apply fix** based on issue pattern above
4. **Re-run diagnostics** to confirm fix worked
5. **Test document viewing** in app

### If All Checks Pass

If diagnostics show ✅ for everything:
- Document viewing SHOULD work
- Try clicking "View Document" in app
- If still fails, check browser Network tab for actual HTTP error
- Share Network tab screenshot for further diagnosis

---

## Files Reference

| File | Purpose | Where to Run |
|------|---------|--------------|
| `diagnostic_sql.sql` | Database checks | Supabase SQL Editor |
| `diagnostic_browser.js` | Frontend checks | Browser console (after login) |
| `diagnostic_code_review.md` | Code analysis | Read + run 3 tests |
| `DIAGNOSTIC_DOCUMENT_ACCESS.md` | Detailed check list | Reference guide |
| `RUN_DIAGNOSTICS.md` | This file | Instructions |

---

## Support

If diagnostics don't reveal the issue:
1. Run all 3 diagnostics
2. Collect all outputs
3. Note exact error message shown to user
4. Check browser Network tab (F12 → Network) for failed requests
5. Share diagnostic outputs + Network tab screenshot

**This will identify the exact root cause.**
