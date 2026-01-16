# 🚀 START HERE - Next Engineer Handover
## Outlook OAuth Email Integration for CelesteOS
## Date: 2026-01-16
## Status: ✅ OAUTH WORKING | ⏳ EMAIL SYNC NOT STARTED

---

## 📍 YOU ARE HERE

You're continuing work on **Microsoft Outlook Email Integration** for the CelesteOS yacht maintenance system.

**Current Stage:** OAuth is fully working. Next phase is building the email sync worker.

---

## ⚡ QUICK START (5 Minutes)

### 1. **Read These Documents (In Order):**

```bash
# Start with the executive summary
/HANDOVER_OUTLOOK_OAUTH_COMPLETE.md

# Then read the technical details
/OUTLOOK_OAUTH_STATUS_ENDPOINT_FIX.md

# If you need deep dive on bugs fixed
/OUTLOOK_OAUTH_FINAL_REPORT.md
```

### 2. **Verify OAuth Still Works:**

```bash
# Go to production
open https://app.celeste7.ai

# Login
Email: x@alex-short.com
Password: Password2!

# Navigate to Settings → Look for Outlook integration
# Should show: "✅ Connected" status
```

### 3. **Check Database:**

```bash
# Test user credentials
User ID: a0d66b00-581f-4d27-be6b-5b679d5cd347
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598

# Check tokens exist in TENANT DB
# Supabase: https://vzsohavtuotocgrfkfyd.supabase.co
# Run in SQL Editor:
SELECT user_id, yacht_id, token_purpose, scopes, token_expires_at, created_at
FROM auth_microsoft_tokens
WHERE user_id = 'a0d66b00-581f-4d27-be6b-5b679d5cd347';

# Should return: 1-2 rows (read and/or write tokens)
```

---

## 🎯 WHAT'S DONE

### ✅ **OAuth Backend (Python/Render)**
- [x] Token exchange endpoint: `POST /auth/outlook/exchange`
- [x] Status check endpoint: `GET /auth/outlook/status`
- [x] MASTER DB → TENANT DB lookup flow
- [x] Token storage in database
- [x] Error handling and logging
- [x] Deployed to: https://pipeline-core.int.celeste7.ai

### ✅ **OAuth Frontend (Next.js/Vercel)**
- [x] OAuth initiation flow
- [x] Callback handling
- [x] Status checking (proxies to Render)
- [x] Deployed to: https://app.celeste7.ai

### ✅ **Database Schema**
- [x] `auth_microsoft_tokens` table (stores tokens)
- [x] `email_watchers` table (sync status)
- [x] All column names verified
- [x] MASTER/TENANT architecture documented

### ✅ **Documentation**
- [x] Architecture diagrams
- [x] All bugs documented with fixes
- [x] API endpoints documented
- [x] Credentials reference
- [x] Testing instructions

---

## ⚠️ WHAT'S NOT DONE

### 1. **FK Constraint Removal (30 seconds - Optional)**

The `email_watchers` table has a foreign key constraint that blocks MASTER user_id insertion.

**To Fix:**
```sql
-- Run in TENANT DB SQL Editor
-- https://vzsohavtuotocgrfkfyd.supabase.co
ALTER TABLE email_watchers
DROP CONSTRAINT IF EXISTS email_watchers_user_id_fkey;
```

**Why:** MASTER user_id doesn't exist in TENANT auth.users table.

**Impact:** Low - OAuth works without this, just can't create watcher records.

---

### 2. **Email Sync Worker (Next Phase - Your Job!)**

**Goal:** Periodically fetch new emails from Outlook and store them.

**What You Need to Build:**

#### **A. Email Fetching Service**

```python
# /apps/api/workers/email_sync.py

import httpx
from datetime import datetime, timedelta

async def fetch_emails_for_user(user_id: str, yacht_id: str):
    """
    Fetch emails from Microsoft Graph API using stored tokens.

    Steps:
    1. Get access token from auth_microsoft_tokens
    2. Check if token expired (refresh if needed)
    3. Call Microsoft Graph: GET /me/messages
    4. Parse emails and store in email_messages table
    5. Update last_sync_at in email_watchers
    """
    pass

async def sync_all_watchers():
    """
    Background job: Sync emails for all active watchers.

    Query email_watchers WHERE sync_status = 'active'
    For each watcher, call fetch_emails_for_user()
    """
    pass
```

#### **B. Email Storage Schema**

Check if `email_messages` table exists. If not, create:

```sql
CREATE TABLE email_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    provider TEXT DEFAULT 'microsoft_graph',

    -- Microsoft Graph fields
    message_id TEXT NOT NULL,  -- Microsoft's unique ID
    conversation_id TEXT,      -- For threading

    -- Email content
    subject TEXT,
    body_preview TEXT,
    body_content TEXT,
    from_address TEXT,
    from_name TEXT,
    to_addresses JSONB,
    cc_addresses JSONB,

    -- Metadata
    received_at TIMESTAMPTZ,
    has_attachments BOOLEAN DEFAULT false,
    is_read BOOLEAN DEFAULT false,
    importance TEXT,

    -- Linking
    linked_work_order_id UUID REFERENCES pms_work_orders(id),
    linked_equipment_id UUID REFERENCES pms_equipment(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(provider, message_id, yacht_id)
);

CREATE INDEX idx_email_messages_user ON email_messages(user_id, yacht_id);
CREATE INDEX idx_email_messages_conversation ON email_messages(conversation_id);
CREATE INDEX idx_email_messages_received ON email_messages(received_at DESC);
```

#### **C. Microsoft Graph API Calls**

**Fetch Messages:**
```bash
GET https://graph.microsoft.com/v1.0/me/messages
  ?$top=50
  &$orderby=receivedDateTime desc
  &$select=id,subject,bodyPreview,from,toRecipients,receivedDateTime

Headers:
  Authorization: Bearer {access_token_from_db}
```

**Pagination:**
```python
# Microsoft Graph uses @odata.nextLink for pagination
response = await client.get(url)
data = response.json()
messages = data['value']
next_link = data.get('@odata.nextLink')
```

**Delta Sync (Incremental):**
```bash
# First sync
GET /me/messages/delta

# Subsequent syncs (use deltaLink from previous response)
GET {deltaLink}
```

#### **D. Token Refresh Logic**

```python
async def refresh_access_token(user_id: str, yacht_id: str, purpose: str):
    """
    Refresh expired access token using refresh token.

    Steps:
    1. Get refresh_token from auth_microsoft_tokens
    2. POST to Microsoft token endpoint
    3. Update auth_microsoft_tokens with new access_token
    4. Return new access_token
    """

    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"

    response = await httpx.post(token_url, data={
        'client_id': AZURE_APP_ID,
        'client_secret': AZURE_CLIENT_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    })

    # Update database with new tokens
    # ...
```

#### **E. Background Job Scheduler**

**Option 1: Render Cron Job**
```yaml
# render.yaml
services:
  - type: cron
    name: email-sync
    env: python
    schedule: "*/15 * * * *"  # Every 15 minutes
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python -m apps.api.workers.email_sync"
```

**Option 2: Python APScheduler**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(sync_all_watchers, 'interval', minutes=15)
scheduler.start()
```

---

### 3. **Email Threading (After Sync Works)**

**Goal:** Group related emails together.

**Use:** `conversation_id` from Microsoft Graph
- All emails in same thread have same `conversation_id`
- Group by this field when displaying

---

### 4. **Link Emails to Work Orders (After Threading)**

**Goal:** Automatically link emails to relevant work orders or equipment.

**Approaches:**

**A. Keyword Matching:**
```python
# Search email subject/body for work order numbers
import re

def find_work_order_id(email_text: str):
    # Match "WO-12345" or "#12345" patterns
    pattern = r'WO-(\d+)|#(\d+)'
    matches = re.findall(pattern, email_text)
    # Lookup in pms_work_orders
```

**B. AI/LLM Matching:**
```python
# Use Claude or GPT to analyze email content
# "Does this email relate to equipment X or work order Y?"
```

**C. Manual Linking:**
```python
# UI: User drags email to work order card
# POST /api/emails/{email_id}/link
# Body: { work_order_id: "..." }
```

---

## 🏗️ ARCHITECTURE YOU NEED TO KNOW

### **Database Split: MASTER vs TENANT**

```
MASTER DB (qvzmkaamzaqxpzbewjxe.supabase.co)
├─ Purpose: Authentication across all yachts
├─ Tables:
│  ├─ auth.users (Supabase auth)
│  └─ user_accounts (user → yacht mapping)
└─ User ID: a0d66b00-581f-4d27-be6b...

TENANT DB (vzsohavtuotocgrfkfyd.supabase.co)
├─ Purpose: Yacht-specific data
├─ Tables:
│  ├─ auth_microsoft_tokens (OAuth tokens)
│  ├─ email_watchers (sync status)
│  ├─ email_messages (emails)
│  ├─ pms_work_orders, pms_equipment, etc.
└─ Yacht ID: 85fe1119-b04c-41ac-80f1...
```

**Key Pattern:**
1. User authenticates via MASTER DB → get user_id
2. Query MASTER user_accounts → get yacht_id for user
3. Use yacht_id to get TENANT DB credentials
4. Query/Update TENANT DB for yacht-specific data

**In Your Code:**
```python
# Step 1: Get yacht_id from MASTER
master_supabase = get_master_supabase()
user_account = master_supabase.table('user_accounts').select('yacht_id').eq('id', user_id).execute()
yacht_id = user_account.data['yacht_id']

# Step 2: Get TENANT DB for that yacht
tenant_supabase = get_yacht_supabase(yacht_id)

# Step 3: Query/Update TENANT data
emails = tenant_supabase.table('email_messages').select('*').eq('yacht_id', yacht_id).execute()
```

---

## 🔑 CREDENTIALS & ACCESS

### **Azure OAuth Apps**

**READ App:**
- App ID: `41f6dc82-8127-4330-97e0-c6b26e6aa967`
- Scopes: Mail.Read, User.Read, Files.Read.All
- Client Secret: See `/Volumes/Backup/CELESTE/email_integration/client-secret.md`

**WRITE App:**
- App ID: `f0b8944b-8127-4f0f-8ed5-5487462df50c`
- Scopes: Mail.ReadWrite, Mail.Send, Calendars.ReadWrite
- Client Secret: See `/Volumes/Backup/CELESTE/email_integration/client-secret.md`

**Set in Render Environment Variables:**
```
AZURE_READ_APP_ID=...
AZURE_READ_CLIENT_SECRET=...
AZURE_WRITE_APP_ID=...
AZURE_WRITE_CLIENT_SECRET=...
```

### **Supabase Databases**

**MASTER DB:**
- URL: `https://qvzmkaamzaqxpzbewjxe.supabase.co`
- Service Key: (in `/Volumes/Backup/CELESTE/env vars/`)

**TENANT DB:**
- URL: `https://vzsohavtuotocgrfkfyd.supabase.co`
- Service Key: (in `/Volumes/Backup/CELESTE/env vars/`)

**Set in Render:**
```
MASTER_SUPABASE_URL=...
MASTER_SUPABASE_SERVICE_KEY=...
yTEST_YACHT_001_SUPABASE_URL=...
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=...
```

### **Test User**
```
Email: x@alex-short.com
Password: Password2!
User ID: a0d66b00-581f-4d27-be6b-5b679d5cd347
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

---

## 🧪 TESTING APPROACH

### 1. **Test OAuth Token Retrieval**

```python
# Test script: /apps/api/tests/test_email_fetch.py

async def test_fetch_with_real_token():
    # Get token from database
    token = get_token_from_db(user_id='a0d66b00...', purpose='read')

    # Try fetching emails
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://graph.microsoft.com/v1.0/me/messages?$top=10',
            headers={'Authorization': f'Bearer {token.microsoft_access_token}'}
        )

    assert response.status_code == 200
    data = response.json()
    print(f"Fetched {len(data['value'])} emails")
```

### 2. **Test Token Refresh**

```python
async def test_token_refresh():
    # Manually set token as expired
    # Try to fetch emails
    # Should auto-refresh token
    # Verify new token stored in DB
```

### 3. **Test Email Storage**

```python
async def test_email_storage():
    # Mock Microsoft Graph response
    # Parse and store in email_messages
    # Verify correct fields stored
    # Verify unique constraint works
```

---

## 📋 YOUR TASK BREAKDOWN

### **Phase 1: Email Fetching (Week 1)**

- [ ] Create `email_messages` table (if doesn't exist)
- [ ] Write `fetch_emails_for_user()` function
- [ ] Test with real OAuth token from database
- [ ] Handle pagination (fetch all emails, not just first page)
- [ ] Store emails in database
- [ ] Handle duplicates (use UNIQUE constraint on message_id)

### **Phase 2: Token Refresh (Week 1)**

- [ ] Write `refresh_access_token()` function
- [ ] Check token expiration before each fetch
- [ ] Auto-refresh if expired
- [ ] Update database with new token
- [ ] Test with expired token

### **Phase 3: Background Worker (Week 2)**

- [ ] Set up scheduler (cron or APScheduler)
- [ ] Write `sync_all_watchers()` function
- [ ] Query email_watchers for active users
- [ ] Loop through and sync each user
- [ ] Update last_sync_at after each sync
- [ ] Error handling (don't crash entire job if one user fails)

### **Phase 4: Delta Sync (Week 2)**

- [ ] Implement delta sync (only fetch new emails)
- [ ] Store deltaLink in email_watchers
- [ ] Use deltaLink for subsequent syncs
- [ ] Fallback to full sync if deltaLink expired

### **Phase 5: Email Threading (Week 3)**

- [ ] Group emails by conversation_id
- [ ] Create UI to display threaded emails
- [ ] Show email threads in work order context

### **Phase 6: Linking (Week 3-4)**

- [ ] Keyword matching for work order numbers
- [ ] Manual linking UI
- [ ] Optional: AI-based matching

---

## 🚨 COMMON PITFALLS

### 1. **Token Expiration**
- Access tokens expire in ~1 hour
- ALWAYS check expiration before using token
- Use refresh token to get new access token

### 2. **Rate Limiting**
- Microsoft Graph has rate limits
- Don't sync too frequently (15-30 min intervals)
- Handle 429 Too Many Requests errors

### 3. **MASTER vs TENANT Confusion**
- User authenticates via MASTER
- Tokens stored in TENANT
- Always lookup yacht_id first, then query TENANT

### 4. **Duplicate Emails**
- Use UNIQUE constraint on (provider, message_id, yacht_id)
- Handle conflicts gracefully (UPDATE instead of INSERT)

### 5. **Large Email Bodies**
- Email bodies can be huge
- Consider storing only bodyPreview for list view
- Fetch full body on-demand

---

## 📚 USEFUL RESOURCES

### **Microsoft Graph API Docs**
- Messages: https://learn.microsoft.com/en-us/graph/api/user-list-messages
- Delta Query: https://learn.microsoft.com/en-us/graph/delta-query-messages
- Pagination: https://learn.microsoft.com/en-us/graph/paging

### **OAuth 2.0 Token Refresh**
- https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow#refresh-the-access-token

### **Supabase Python Client**
- https://supabase.com/docs/reference/python/introduction

### **APScheduler (Background Jobs)**
- https://apscheduler.readthedocs.io/

---

## 🎯 SUCCESS CRITERIA

You're done when:

- [ ] Emails are automatically fetched every 15 minutes
- [ ] New emails appear in database
- [ ] Token refresh works automatically
- [ ] No duplicate emails stored
- [ ] Watcher status updates after each sync
- [ ] Can see emails in UI (threaded by conversation)
- [ ] Can manually link emails to work orders

---

## 🆘 IF YOU GET STUCK

### **OAuth Tokens Not Working?**
1. Check token hasn't expired: `SELECT token_expires_at FROM auth_microsoft_tokens`
2. Try refreshing token manually
3. Re-authorize via app.celeste7.ai if refresh fails

### **MASTER/TENANT Confusion?**
1. Re-read `OUTLOOK_OAUTH_FINAL_REPORT.md` section on architecture
2. Remember: Auth in MASTER, Data in TENANT

### **Microsoft Graph API Errors?**
1. Check scopes in token match required scopes
2. READ token for fetching, WRITE token for sending
3. Check Azure app permissions in Azure Portal

### **Database Errors?**
1. Verify table schema matches your code
2. Check TENANT DB, not MASTER DB
3. Look at migration: `supabase/migrations/20260116_remove_email_watchers_fk.sql`

---

## 📞 HANDOVER CONTACT

**Previous Work Done By:** Claude Sonnet 4.5
**Session Date:** 2026-01-16
**Git Commits:** 64be051, 5aaaccf, 4128412, ad82240, 3273554, 7e2ddab

**All Documentation In:**
- `/HANDOVER_OUTLOOK_OAUTH_COMPLETE.md` - Complete overview
- `/OUTLOOK_OAUTH_STATUS_ENDPOINT_FIX.md` - Status endpoint details
- `/OUTLOOK_OAUTH_FINAL_REPORT.md` - All bugs fixed
- `/SESSION_SUMMARY_STATUS_ENDPOINT_FIX.md` - Latest session summary

---

## ✅ FINAL CHECKLIST BEFORE YOU START

- [ ] Read `HANDOVER_OUTLOOK_OAUTH_COMPLETE.md`
- [ ] Verified OAuth works on app.celeste7.ai
- [ ] Checked tokens exist in database
- [ ] Understand MASTER vs TENANT architecture
- [ ] Have access to Render dashboard
- [ ] Have access to Supabase dashboards
- [ ] Have Azure app credentials
- [ ] Know where to find client secrets
- [ ] Created email_messages table (or verified it exists)
- [ ] Set up local development environment

---

## 🚀 READY TO START?

```bash
# 1. Test OAuth token retrieval
cd /Users/celeste7/Documents/Cloud_PMS/apps/api
python -m tests.test_email_fetch

# 2. Fetch your first email
# See Phase 1 tasks above

# 3. Deploy to Render when working locally
git add .
git commit -m "feat(email): Add email sync worker"
git push origin main
```

**Good luck! 🎉**

The hard part (OAuth) is done. Now you're just fetching emails and storing them. You've got this!
