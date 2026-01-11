# Security Gaps for Yacht Fleet SaaS - Action Items

## Current Status: CORS is Fixed, But Not the Moat

You now have production-grade CORS. That's **step 1**, not the finish line.

This document identifies remaining security gaps critical for a multi-yacht fleet handling sensitive operational data.

---

## IMMEDIATE: Fix Signed URL Expiration 🔴 CRITICAL

### Current State (INSECURE)
**File:** `apps/web/src/lib/documentLoader.ts:94`

```typescript
createSignedUrl(storagePath, 3600); // 3600 seconds = 1 HOUR
```

### The Problem

**Signed URLs live for 1 hour.** That means:
- User opens PDF at 10:00 AM
- URL valid until 11:00 AM
- User can share URL with anyone during that hour
- Anyone with URL can access document (no further auth check)
- URL might be logged, cached, or stored in browser history

**Attack Scenarios:**
1. **Internal leak:** User screenshots URL and shares via Slack/WhatsApp
2. **Browser history:** URL visible in history for 90+ days
3. **Proxy logs:** Company proxies log all HTTPS URLs
4. **Accidental paste:** User pastes URL into wrong chat/email
5. **Mobile sync:** URL syncs to personal devices via browser sync

### Industry Standard (High-Security SaaS)

**Sensitive documents:** 60-300 seconds (1-5 minutes)
- Google Drive (view-only mode): 60 seconds
- Stripe (invoice PDFs): 300 seconds
- GitHub (private artifacts): 60 seconds

**Why short TTLs:**
- Limits exposure window
- Makes URL sharing useless (expires before recipient can act)
- Reduces risk from logs/history

### Fix

```typescript
// Short-lived signed URLs for yacht fleet security
createSignedUrl(storagePath, 120); // 120 seconds = 2 minutes
```

**2 minutes is enough to:**
- Load PDF in viewer
- Convert to blob URL (happens immediately)
- Original signed URL expires while user views blob

**After expiration:**
- Original URL useless
- Blob URL continues to work (same-origin, already loaded)
- If user refreshes, new signed URL generated

### Additional Hardening

**Add per-request audit log:**
```typescript
// Before creating signed URL
await auditLog({
  action: 'document_access',
  user_id: userId,
  yacht_id: yachtId,
  document_id: documentId,
  ip_address: getClientIP(),
  timestamp: Date.now(),
});
```

**Benefits:**
- Track who accessed what document when
- Detect suspicious access patterns
- Compliance requirement for yachts (crew changes, audits)
- Selling point for high-value clients

---

## HIGH: Verify Bucket is Private 🟡 HIGH

### Check Supabase Bucket Settings

**Required:**
```
Storage → documents bucket → Settings
- Public: ❌ MUST BE OFF
- RLS Enabled: ✅ MUST BE ON
```

**Test:**
```bash
# Try to access without auth (should fail)
curl -I 'https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/public/documents/...'
# Expected: 404 or 403
```

**If bucket is public:**
- Anyone can list files
- Anyone can guess file paths
- RLS policies ignored
- All yacht documents exposed

**Fix:** Make bucket private in Supabase Dashboard.

---

## HIGH: Per-Yacht Origin Strategy 🟡 HIGH

### Current State
All yachts share one domain: `app.celeste7.ai`

### Future Problem
You're building "multi-instance SaaS for high-value targets." Eventually:
- Yacht owner wants `fleet.luxuryyachtco.com`
- Another wants `ops.superyachtmanagement.com`
- You have 80 custom domains

**Don't end up with:**
```python
ALLOWED_ORIGINS = "https://app.celeste7.ai,https://yacht1.com,https://yacht2.com,..." # 80 domains
```

### Recommended Strategy

**Option A: Single Global Domain (Recommended)**
- All yachts use `app.celeste7.ai`
- Yacht context from JWT (yacht_id)
- Simplest, most maintainable
- **Use this unless custom domains are a sales requirement**

**Option B: Controlled Custom Domains**
If custom domains are required:
1. Store allowed domains in database (`yacht_custom_domains` table)
2. Load from database on startup, cache in memory
3. Log any additions/changes
4. Limit: 1-2 domains per yacht
5. Require domain verification (DNS TXT record)

```python
# Load from database
YACHT_DOMAINS = load_yacht_domains_from_db()
ALLOWED_ORIGINS = ["https://app.celeste7.ai", "https://staging.celeste7.ai"] + YACHT_DOMAINS
```

**Option C: Wildcard Subdomain (Dangerous)**
```python
# Allow *.celeste7.ai
# DON'T DO THIS - anyone can create subdomain and attack
```

**Decision:** Make this choice now before adding custom domains ad-hoc.

---

## HIGH: Rate Limiting 🟡 HIGH

### Endpoints That Need Rate Limits

**1. PDF Signed URL Generation**
- `/v1/documents/{id}/stream` or similar
- Limit: 60 requests/minute per user
- Why: Prevents bulk document download attacks

**2. Authentication Endpoints**
- `/auth/login`
- `/auth/refresh`
- Limit: 10 requests/minute per IP
- Why: Prevents brute force

**3. Search Endpoints**
- `/webhook/search`
- `/v1/search`
- Limit: 100 requests/minute per user
- Why: Prevents API abuse, LLM quota exhaustion

**4. Microaction Execution**
- `/v1/actions/execute`
- Limit: 30 requests/minute per user
- Why: Prevents automation abuse

### Implementation (FastAPI)

You already have SlowAPI in `microaction_service.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/v1/documents/{document_id}/stream")
@limiter.limit("60/minute")  # 60 requests per minute
async def stream_document(document_id: str, request: Request):
    ...
```

**Add to:**
- Pipeline service (doesn't have it yet)
- All sensitive endpoints

**Key function options:**
- `get_remote_address` - By IP (good for unauthenticated)
- Custom function - By user_id or yacht_id (better for authenticated)

---

## MEDIUM: Audit Logging 🟢 MEDIUM (But Yacht Selling Point)

### What to Log

**Document Access:**
```json
{
  "event": "document_access",
  "timestamp": "2026-01-11T10:30:00Z",
  "user_id": "uuid",
  "yacht_id": "uuid",
  "document_id": "uuid",
  "document_path": "manuals/engine/...",
  "ip_address": "1.2.3.4",
  "user_agent": "Mozilla...",
  "success": true
}
```

**Mutations (Work Orders, Equipment Changes):**
```json
{
  "event": "work_order_created",
  "timestamp": "2026-01-11T10:30:00Z",
  "user_id": "uuid",
  "yacht_id": "uuid",
  "entity_id": "work_order_uuid",
  "action": "create",
  "changes": {...}
}
```

**Failed Auth:**
```json
{
  "event": "auth_failure",
  "timestamp": "2026-01-11T10:30:00Z",
  "ip_address": "1.2.3.4",
  "reason": "invalid_jwt",
  "endpoint": "/webhook/search"
}
```

### Why This Matters for Yachts

**Compliance:**
- ISM Code audits require access logs
- Insurance requirements
- Crew change documentation

**Security:**
- Detect unauthorized access attempts
- Track who viewed/modified sensitive data
- Incident response

**Selling Point:**
- "Complete audit trail for compliance"
- "Track crew access to critical documents"
- "Incident forensics included"

### Implementation

**Simple: Database Table**
```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  event_type TEXT NOT NULL,
  user_id UUID,
  yacht_id UUID,
  entity_id UUID,
  metadata JSONB,
  ip_address TEXT,
  user_agent TEXT
);

CREATE INDEX idx_audit_yacht_time ON audit_log(yacht_id, timestamp DESC);
CREATE INDEX idx_audit_user_time ON audit_log(user_id, timestamp DESC);
```

**Better: Time-Series Database**
- Use ClickHouse, TimescaleDB, or Supabase Realtime
- Better performance for high-volume logging
- Efficient queries over time ranges

---

## MEDIUM: WAF and Anomaly Detection 🟢 MEDIUM

### Current State
No Web Application Firewall (WAF)

### What You Need Eventually

**Basic Protection (Now-ish):**
- Cloudflare Free Tier (easy win)
- DDoS protection included
- Bot detection
- SSL/TLS hardening

**Advanced Protection (Later):**
- Cloudflare WAF rules
- Rate limiting at edge
- IP reputation filtering
- Geo-blocking if needed

**Anomaly Detection (Later):**
- Unusual document access patterns
- Bulk downloads
- Off-hours access
- Geographic anomalies (crew suddenly in different country)

---

## LOW: Key Rotation Automation 🟢 LOW

### Current Secrets

**JWT Signing Keys:**
- Managed by Supabase (they rotate)
- ✅ No action needed

**YACHT_SALT:**
- Used for `X-Yacht-Signature`
- Currently: `process.env.NEXT_PUBLIC_YACHT_SALT`
- ❌ Never rotated

**Supabase API Keys:**
- Service role key
- Anon key
- ❌ Manual rotation only

### Recommendation

**For now:** Document rotation procedures

**Later:** Automate key rotation
- Rotate YACHT_SALT every 90 days
- Use versioned keys (accept last 2 versions during transition)
- Store in HashiCorp Vault or AWS Secrets Manager

---

## Deployment Checklist (After This Commit)

### CORS
- [ ] Browser preflight succeeds for all API routes
- [ ] `Access-Control-Allow-Origin` matches exact origin (not wildcard)
- [ ] `Vary` header includes `Origin` without removing other values
- [ ] No CORS errors in browser console

### Storage
- [ ] PDF loads via signed URL
- [ ] Range requests work (scroll through PDF pages)
- [ ] Bucket is **private** (not public)
- [ ] Signed URLs expire in 60-300 seconds (**TODO: FIX**)
- [ ] RLS policies enforce yacht isolation

### CSP
- [ ] No console errors for `frame-src` or `worker-src`
- [ ] PDF loads in iframe with blob URL
- [ ] No "This content is blocked" errors

### Auth
- [ ] All requests use `Authorization: Bearer` header
- [ ] No cookies sent to Render APIs
- [ ] JWT auto-refreshes on expiry
- [ ] 401 responses trigger re-auth flow

### Security Hardening
- [ ] Signed URLs shortened to 120 seconds (**TODO**)
- [ ] Rate limiting on sensitive endpoints (**TODO**)
- [ ] Audit logging for document access (**TODO**)
- [ ] Bucket verified private (**VERIFY NOW**)
- [ ] Per-yacht origin strategy decided (**DECIDE**)

---

## Summary: What's Done vs What Remains

### ✅ Done (This Commit)
1. CORS with bearer tokens (`allow_credentials=False`)
2. Stable domains only (no preview URLs)
3. Env var configuration with normalization
4. `Vary: Origin` header (append, not overwrite)
5. Preflight caching (1 hour)
6. Logging of allowed origins on startup

### 🔴 Critical (Do Next)
1. **Shorten signed URL expiration to 120 seconds**
2. **Verify Supabase bucket is private**

### 🟡 High Priority (This Week)
3. Add rate limiting to all sensitive endpoints
4. Decide per-yacht origin strategy
5. Add audit logging for document access

### 🟢 Important (This Month)
6. Set up basic WAF (Cloudflare free tier)
7. Document key rotation procedures
8. Add anomaly detection rules

---

## The Truth About "Industry Comparison"

**You match CORS best practices.** That's good.

**But Google/Stripe/GitHub also have:**
- WAF with custom rules
- Real-time anomaly detection
- Automated key rotation
- SOC 2 compliance
- Incident response playbooks
- 24/7 security monitoring
- Bug bounty programs

**CORS is the foundation, not the finish line.**

For a yacht fleet SaaS:
- Your customers are high-value targets
- Their data is operationally sensitive
- Security is a competitive advantage
- Breaches = lost customers + legal liability

**Build the rest of the moat incrementally, but build it.**

---

## Immediate Action Items (This Week)

### 1. Fix Signed URL TTL (30 min)
```typescript
// apps/web/src/lib/documentLoader.ts:94
createSignedUrl(storagePath, 120); // 2 minutes
```

### 2. Verify Bucket is Private (5 min)
- Check Supabase Dashboard → Storage → documents
- Ensure "Public" is OFF
- Test: Try accessing URL without auth

### 3. Add Rate Limiting to Pipeline Service (1 hour)
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_user_or_ip)
app.add_extension(limiter)

@app.post("/webhook/search")
@limiter.limit("100/minute")
async def search(...):
    ...
```

### 4. Decide Origin Strategy (15 min)
- Will you support custom domains per yacht?
- If yes, how will you manage them?
- If no, document "single global domain" as policy

### 5. Set Up Basic Audit Logging (2 hours)
```python
# Add audit_log table to database
# Log document access, auth failures, mutations
# Query logs via admin panel
```

---

**After these 5 items, you'll have:**
- Production-grade CORS ✅
- Short-lived signed URLs ✅
- Rate limiting ✅
- Audit trail ✅
- Clear origin strategy ✅

**That's a defensible security posture for yacht fleet SaaS.**
