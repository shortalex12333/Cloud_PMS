# SECURITY INVARIANTS

**These are non-negotiable rules. Breaking them creates security vulnerabilities.**

Date: 2026-01-22

---

## WHAT CELESTEOS IS

**Single Postgres + RLS architecture**

One production Postgres instance with Row Level Security policies enforcing tenant isolation.

NOT:
- ❌ Per-tenant databases
- ❌ Application-level tenant filtering
- ❌ Shared tables without RLS

**Yacht = tenant**

The tenant boundary is `yacht_id`. All PMS data belongs to exactly one yacht.

NOT:
- ❌ Fleet = tenant
- ❌ Company = tenant
- ❌ User = tenant

**Users can belong to multiple yachts**

A user can have roles on multiple yachts simultaneously. Context switching handled by JWT claims.

NOT:
- ❌ One user = one yacht forever
- ❌ Users must leave one yacht to join another
- ❌ Cross-yacht access requires separate accounts

**Devices are first-class actors**

Devices (iPads, laptops) are revocable actors with tokens, scopes, and audit trails.

NOT:
- ❌ Devices share user credentials
- ❌ Devices have permanent access
- ❌ Device compromises are undetectable

---

## WHAT CELESTEOS IS NOT

**Not per-tenant databases**

There is ONE tenant database for all yachts. Isolation is via RLS, not separate databases.

**Implication:**
- SQL injection affects ALL yachts, not just one
- RLS policy bugs leak data across yachts
- Database performance affects ALL yachts

**Not credential-based installs**

There are no hardcoded credentials in device images or installers.

**Implication:**
- Devices MUST pair via secure pairing flow (NOT IMPLEMENTED YET)
- Devices MUST use revocable tokens
- Lost devices MUST be remotely revoked

**Not silent data merging**

The system does NOT silently merge data from multiple sources.

**Implication:**
- Conflicting equipment names = user must resolve
- Duplicate faults = user must merge manually
- Data integrity is explicit, never implicit

---

## INVARIANTS (Must Never Be Broken)

### I1: Yacht Isolation Enforced by RLS

**Rule:** Every PMS table MUST have RLS policies that filter by `yacht_id`.

**Enforcement:**
```sql
-- Example: equipment table
CREATE POLICY "Users can only see their yacht's equipment"
ON equipment FOR SELECT
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

**How to verify:**
```sql
-- Check all tables have RLS enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND rowsecurity = false;
-- Result must be empty OR only system tables
```

**If broken:**
- User from Yacht A sees Yacht B's equipment
- User from Yacht A modifies Yacht B's work orders
- Cross-yacht data leaks

**HOW TO BREAK (accidentally):**
```sql
-- NEVER DO THIS
ALTER TABLE equipment DISABLE ROW LEVEL SECURITY;

-- NEVER DO THIS
CREATE POLICY "Allow all" ON equipment USING (true);

-- NEVER DO THIS (no yacht_id filter)
CREATE POLICY "Allow all users" ON equipment USING (user_id IS NOT NULL);
```

**HOW TO FIX:**
```sql
-- Re-enable RLS
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;

-- Drop bad policy
DROP POLICY "Allow all" ON equipment;

-- Create correct policy
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);
```

---

### I2: No Plaintext Secrets Stored or Shown

**Rule:** API tokens, passwords, service role keys MUST NEVER be stored or returned in plaintext.

**Enforcement:**
- Tokens stored as bcrypt hashes in `api_tokens.token_hash`
- Service role keys stored in environment variables, NEVER in database
- JWTs validated, NEVER logged

**How to verify:**
```sql
-- Check api_tokens table has no plaintext column
SELECT column_name FROM information_schema.columns
WHERE table_name = 'api_tokens'
AND column_name IN ('token', 'token_plaintext', 'secret');
-- Result must be empty
```

**If broken:**
- Attacker with DB access steals all tokens
- Tokens appear in logs, leaked via error messages
- Service role keys committed to Git

**HOW TO BREAK (accidentally):**
```python
# NEVER DO THIS
db.table("api_tokens").insert({"token": plaintext_token})

# NEVER DO THIS
logger.info(f"Token: {plaintext_token}")

# NEVER DO THIS
return {"token": plaintext_token}
```

**HOW TO FIX:**
```python
# Hash tokens before storage
import bcrypt
token_hash = bcrypt.hashpw(plaintext_token.encode(), bcrypt.gensalt())
db.table("api_tokens").insert({"token_hash": token_hash.decode()})

# Never log tokens
logger.info("Token issued")  # Don't include token value

# Never return plaintext tokens
return {"token_id": token_id}  # Return ID, not token
```

---

### I3: No Mutation Without Auditability

**Rule:** Every database INSERT/UPDATE/DELETE MUST create an audit log entry.

**Enforcement:**
```python
# After successful mutation
audit_entry = {
    "action": "create_work_order",
    "entity_id": work_order_id,
    "yacht_id": yacht_id,
    "user_id": user_id,
    "old_values": {},
    "new_values": wo_data,
    "timestamp": datetime.utcnow().isoformat()
}
db.table("pms_audit_log").insert(audit_entry).execute()
```

**How to verify:**
```sql
-- Check audit log count matches mutation count
SELECT COUNT(*) FROM pms_audit_log
WHERE action = 'create_work_order';

SELECT COUNT(*) FROM pms_work_orders;
-- Counts should be roughly equal (allowing for pre-existing data)
```

**If broken:**
- WHO changed WHAT and WHEN is unknown
- Compliance violations (ISO 9001, SOLAS require audit trails)
- Debugging impossible (no history of changes)

**HOW TO BREAK (accidentally):**
```python
# NEVER DO THIS (no audit log)
db.table("pms_work_orders").insert(wo_data).execute()
return {"status": "success"}
```

**HOW TO FIX:**
```python
# Always create audit log after mutation
result = db.table("pms_work_orders").insert(wo_data).execute()
work_order_id = result.data[0]["id"]

# Create audit log
audit_entry = {...}
db.table("pms_audit_log").insert(audit_entry).execute()

return {"status": "success", "work_order_id": work_order_id}
```

**CURRENT STATUS:**
- ❌ Only 4/64 actions create audit logs
- ❌ 60/64 actions violate this invariant
- ⚠️ HIGH PRIORITY: Add audit logging to all mutation handlers

---

### I4: JWT Validation MUST Succeed Before Database Access

**Rule:** Every API request MUST validate JWT token BEFORE querying database.

**Enforcement:**
```python
# Validate JWT
jwt_payload = validate_jwt(request.headers["Authorization"])
yacht_id = jwt_payload["yacht_id"]
user_id = jwt_payload["sub"]

# Set session variable for RLS
db.rpc("set_yacht_context", {"yacht_id": yacht_id})

# Now safe to query
result = db.table("pms_work_orders").select("*").execute()
```

**How to verify:**
```python
# Test: Invalid JWT should return 401
response = requests.post("/v1/actions/execute",
    headers={"Authorization": "Bearer INVALID_TOKEN"},
    json={"action": "view_work_order", "payload": {...}}
)
assert response.status_code == 401
```

**If broken:**
- Unauthenticated users access PMS data
- Users from Yacht A access Yacht B data (RLS bypassed if session variable not set)
- Audit logs have wrong user_id

**HOW TO BREAK (accidentally):**
```python
# NEVER DO THIS (no JWT validation)
@router.post("/v1/actions/execute")
async def execute_action(request: Request):
    payload = await request.json()
    # ... query database without validating JWT ...
```

**HOW TO FIX:**
```python
# Always validate JWT first
@router.post("/v1/actions/execute")
async def execute_action(request: Request, jwt_payload: dict = Depends(validate_jwt)):
    yacht_id = jwt_payload["yacht_id"]
    user_id = jwt_payload["sub"]

    # Set session variable
    db.rpc("set_yacht_context", {"yacht_id": yacht_id})

    # Now safe to query
    ...
```

---

### I5: RLS Policies MUST Filter by Session Variable

**Rule:** RLS policies MUST use `current_setting('app.current_yacht_id')`, NOT JWT claims directly.

**Enforcement:**
```sql
-- CORRECT
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);

-- WRONG (JWT claims not accessible in RLS)
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = current_setting('request.jwt.claim.yacht_id')::uuid);
```

**How to verify:**
```sql
-- Check all RLS policies use session variable
SELECT schemaname, tablename, policyname, qual
FROM pg_policies
WHERE schemaname = 'public'
AND qual NOT LIKE '%current_setting%';
-- Review results - should only be system policies
```

**If broken:**
- RLS policies don't filter anything (all rows visible to all users)
- Cross-yacht data leaks

**HOW TO BREAK (accidentally):**
```sql
-- NEVER DO THIS (session variable not set)
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = 'hardcoded-yacht-id');

-- NEVER DO THIS (JWT claims not accessible)
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = auth.jwt()->>'yacht_id');
```

**HOW TO FIX:**
```sql
-- Always use session variable
CREATE POLICY "Yacht isolation" ON equipment
USING (yacht_id = current_setting('app.current_yacht_id')::uuid);

-- Backend MUST set session variable before queries
db.rpc("set_yacht_context", {"yacht_id": yacht_id})
```

---

### I6: Service Role Key MUST NEVER Be Exposed to Client

**Rule:** Supabase service role key MUST ONLY be used in backend, NEVER sent to frontend or mobile apps.

**Enforcement:**
- Service role key stored in backend environment variables
- Frontend uses anon key OR user JWTs only
- Service role key NEVER in client-side code, logs, or responses

**How to verify:**
```bash
# Check frontend code for service role key
grep -r "SUPABASE_SERVICE_ROLE_KEY" apps/web/
# Result must be empty

# Check if service role key in Git history
git log -S "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" --all
# Result must be empty OR only in .env.example
```

**If broken:**
- Attacker with service role key has FULL DATABASE ACCESS
- Can bypass ALL RLS policies
- Can read/write/delete ANY data from ANY yacht

**HOW TO BREAK (accidentally):**
```typescript
// NEVER DO THIS (frontend code)
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY  // NEVER DO THIS
);
```

**HOW TO FIX:**
```typescript
// Frontend uses anon key
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY  // Anon key is safe
);

// Backend uses service role key (never exposed)
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY  // Backend only
);
```

---

### I7: No SQL Injection via String Concatenation

**Rule:** Database queries MUST use parameterized queries, NEVER string concatenation.

**Enforcement:**
```python
# CORRECT (parameterized)
db.table("pms_work_orders").select("*").eq("id", work_order_id).execute()

# WRONG (string concatenation)
query = f"SELECT * FROM pms_work_orders WHERE id = '{work_order_id}'"
db.raw(query).execute()
```

**How to verify:**
```bash
# Check for raw SQL with f-strings
grep -rn 'f"SELECT' apps/api/
grep -rn 'f"INSERT' apps/api/
grep -rn 'f"UPDATE' apps/api/
grep -rn 'f"DELETE' apps/api/
# Result should be empty OR only in migration files
```

**If broken:**
- SQL injection attacks succeed
- Attacker reads/modifies/deletes ANY data from ANY yacht
- Attacker escalates privileges

**HOW TO BREAK (accidentally):**
```python
# NEVER DO THIS
query = f"SELECT * FROM pms_work_orders WHERE title = '{title}'"
result = db.raw(query).execute()
```

**HOW TO FIX:**
```python
# Always use Supabase query builder (auto-parameterizes)
result = db.table("pms_work_orders").select("*").eq("title", title).execute()
```

---

### I8: Tokens MUST Be Revocable

**Rule:** All API tokens MUST be stored in database with `is_revoked` flag. Revoked tokens MUST be rejected.

**Enforcement:**
```python
# Validate token
token_hash = hash_token(provided_token)
token_record = db.table("api_tokens").select("*").eq("token_hash", token_hash).single()

if token_record["is_revoked"]:
    raise HTTPException(status_code=401, detail="Token revoked")
```

**How to verify:**
```python
# Test: Revoked token should return 401
db.table("api_tokens").update({"is_revoked": True}).eq("id", token_id).execute()
response = requests.post("/v1/actions/execute",
    headers={"Authorization": f"Bearer {token}"},
    json={...}
)
assert response.status_code == 401
```

**If broken:**
- Lost/stolen devices retain access forever
- Compromised tokens can't be revoked
- No way to remotely disable a device

**HOW TO BREAK (accidentally):**
```python
# NEVER DO THIS (no revocation check)
if token_hash in valid_tokens:
    # ... grant access ...
```

**HOW TO FIX:**
```python
# Always check revocation status
token_record = db.table("api_tokens").select("*").eq("token_hash", token_hash).single()

if token_record["is_revoked"]:
    raise HTTPException(status_code=401, detail="Token revoked")
if token_record["expires_at"] and datetime.now() > token_record["expires_at"]:
    raise HTTPException(status_code=401, detail="Token expired")

# Token is valid, proceed
...
```

---

## ENFORCEMENT CHECKLIST

**Before ANY code merge:**

- [ ] All database queries use parameterized queries (no f-strings in SQL)
- [ ] All mutations create audit log entries
- [ ] JWT validated before database access
- [ ] Session variable set for RLS (via `set_yacht_context` RPC)
- [ ] No service role keys in client-side code
- [ ] All new tables have RLS policies with `yacht_id` filter
- [ ] Tokens checked for revocation before granting access

**Before ANY migration:**

- [ ] New tables have `yacht_id` column
- [ ] New tables have RLS policies
- [ ] RLS policies use `current_setting('app.current_yacht_id')`
- [ ] No `DISABLE ROW LEVEL SECURITY` statements (except system tables)

**Before ANY production deployment:**

- [ ] Run RLS test suite (verify yacht isolation works)
- [ ] Run audit log test suite (verify all mutations logged)
- [ ] Run token revocation test suite (verify revoked tokens rejected)
- [ ] Check logs for plaintext secrets (none should appear)

---

## THREAT MODEL

### Threat T1: Cross-Yacht Data Leak

**Attack:** User from Yacht A accesses Yacht B's data.

**Mitigation:**
- RLS policies filter by `yacht_id` (I1)
- JWT validation sets correct session variable (I4, I5)

**Detection:** RLS test suite, audit logs

---

### Threat T2: Compromised Service Role Key

**Attack:** Attacker obtains service role key, bypasses RLS, accesses all data.

**Mitigation:**
- Service role key NEVER exposed to client (I6)
- Service role key only in backend environment variables
- Backend has network-level access control (only backend can reach DB)

**Detection:** Monitor for service role key in Git, logs, client-side code

---

### Threat T3: SQL Injection

**Attack:** Attacker injects SQL via user input, exfiltrates data.

**Mitigation:**
- Parameterized queries only (I7)
- No string concatenation in SQL

**Detection:** Code review, automated scanning for f-strings in SQL

---

### Threat T4: Lost/Stolen Device

**Attack:** Device lost/stolen, attacker uses stored token to access yacht data.

**Mitigation:**
- Tokens stored in `api_tokens` table with revocation flag (I8)
- Admin revokes token remotely
- Token expiration (time-limited)

**Detection:** Audit logs show device usage, geolocation (if implemented)

---

### Threat T5: Audit Log Tampering

**Attack:** User deletes audit log entries to hide malicious actions.

**Mitigation:**
- Audit log table has RLS policies (users can INSERT but not DELETE)
- Only service role can delete audit logs
- Audit logs backed up to immutable storage (NOT IMPLEMENTED)

**Detection:** Audit log gaps (missing sequence numbers)

---

## CURRENT INVARIANT VIOLATIONS

**As of 2026-01-22:**

### Invariant I3 Violations: No Audit Logging

**Status:** 60/64 actions violate I3 (no audit log entries created).

**Actions missing audit logs:**
- create_work_order, assign_work_order, add_note, mark_fault_resolved, ... (60 total)

**Actions with audit logs:**
- acknowledge_fault, mark_work_order_complete, assign_work_order (only 4 confirmed)

**Impact:** HIGH - Compliance risk, debugging impossible, no change history.

**Fix:** Add audit logging to all 60 mutation handlers (see Agent 4 plan).

---

### Unknown Status: I1, I5 (RLS Policies)

**Status:** RLS policies exist, but not tested. Unknown if yacht isolation actually works.

**Impact:** HIGH - If RLS broken, cross-yacht data leaks occur.

**Fix:** Create RLS test suite (see Agent 4 plan, Pattern H2).

---

### Unknown Status: I8 (Token Revocation)

**Status:** `is_revoked` column exists, but no test confirms revoked tokens are rejected.

**Impact:** MEDIUM - Lost devices may retain access.

**Fix:** Create token revocation test.

---

## WHAT HAPPENS IF YOU IGNORE THESE INVARIANTS

**Ignore I1 (RLS):**
- Yacht A sees Yacht B's equipment, faults, work orders
- Data leak across customers
- Legal liability, contract violations

**Ignore I2 (Plaintext secrets):**
- Service role key leaked, attacker has full DB access
- All yachts compromised, not just one

**Ignore I3 (Audit logging):**
- WHO changed WHAT is unknown
- Compliance audits fail (ISO 9001, SOLAS)
- Debugging impossible

**Ignore I4 (JWT validation):**
- Unauthenticated users access PMS data
- RLS bypassed (session variable not set)

**Ignore I5 (RLS session variable):**
- RLS policies don't filter, all rows visible to all users
- Cross-yacht data leaks

**Ignore I6 (Service role key exposure):**
- Attacker bypasses ALL security (RLS, auth, audit)
- Full database access, read/write/delete anything

**Ignore I7 (SQL injection):**
- Attacker reads/modifies/deletes data from any yacht
- Attacker escalates privileges

**Ignore I8 (Token revocation):**
- Lost/stolen devices retain access forever
- No way to remotely disable compromised devices

---

**These invariants are the foundation of security. Do not break them.**
