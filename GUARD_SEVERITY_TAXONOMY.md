# GUARD SEVERITY TAXONOMY
**Version:** 1.0
**Date:** 2026-01-12
**Purpose:** Classify all 72 guards by enforcement level to prevent pattern drift

---

## PHILOSOPHY

Guards are not all equal. Some are **existential** (yacht isolation). Others are **nice-to-have** (friendly error messages).

Without severity tiers:
- Engineers won't know what's non-negotiable
- Reviewers won't know what to block PRs on
- "Just this once" shortcuts will creep in
- Security will degrade over 6 months

**This document is the enforcement backbone.**

---

## SEVERITY LEVELS

### G0 — MANDATORY BLOCKERS
**Enforcement:** Build MUST fail without these. Reject PR.
**Applies to:** All MUTATE_HIGH, most MUTATE_MEDIUM, some MUTATE_LOW
**Rationale:** These prevent catastrophic system failures

**If missing → BLOCK DEPLOYMENT**

### G1 — CRITICAL SAFETY
**Enforcement:** MUST exist, but can ship with controlled debt
**Applies to:** MUTATE_HIGH, core workflows
**Rationale:** Operational safety, can be added with waiver

**If missing → REQUIRES WRITTEN WAIVER in PR**

### G2 — OPERATIONAL HARDENING
**Enforcement:** Recommended, shipped without = tracked as tech debt
**Applies to:** All actions
**Rationale:** Production readiness, monitoring

**If missing → SHIP ALLOWED, but tracked**

### G3 — UX/CONVENIENCE
**Enforcement:** Optional, nice-to-have
**Applies to:** All actions
**Rationale:** User experience improvements

**If missing → NO ACTION REQUIRED**

---

## G0 — MANDATORY BLOCKERS (8 guards)

### G0.1: Tenant/Yacht Isolation (A2)
**CRITICAL SECURITY BOUNDARY**

Every database query MUST:
- Filter by `yacht_id` derived from authenticated user's profile
- NEVER accept `yacht_id` from client parameters
- NEVER infer context without validation
- Log critical security violations on breach attempts

```python
# MANDATORY PATTERN - DO NOT MODIFY
user = await self.db.table("user_profiles").select(
    "yacht_id, role, full_name"
).eq("id", user_id).single().execute()

if not user.data or user.data["yacht_id"] != yacht_id:
    logger.critical(
        f"SECURITY VIOLATION: Yacht isolation breach by {user_id}. "
        f"Attempted: {yacht_id}, Actual: {user.data['yacht_id']}"
    )
    builder.set_error("FORBIDDEN", "Access denied")
    return builder.build()

# ALL queries must include:
.eq("yacht_id", yacht_id)
```

**Test:** Attempt to access different yacht's data → MUST fail
**Failure Mode:** Cross-yacht data contamination (CATASTROPHIC)

---

### G0.2: Authentication Gate (A1)
**WHO IS THIS?**

Every handler MUST:
- Validate `user_id` exists and is authenticated
- Reject `null`, `undefined`, or missing user context
- Verify session is valid and not expired

```python
# MANDATORY PATTERN
user_id = params.get("user_id")
if not user_id or user_id == "undefined":
    builder.set_error("UNAUTHORIZED", "User not authenticated")
    return builder.build()

session = await getSession(user_id)
if not session or session.expired:
    builder.set_error("UNAUTHORIZED", "Session expired")
    return builder.build()
```

**Test:** Call without user_id → MUST fail
**Failure Mode:** Unauthenticated operations (CRITICAL)

---

### G0.3: Role-Based Access Control (A3)
**CAN THEY DO THIS?**

Every MUTATE action MUST:
- Define explicit allowed roles (from action catalog)
- Check user's role against allowed list
- Enforce conditional permissions (e.g., 2nd Engineer limits)

```python
# MANDATORY PATTERN
allowed_roles = ["chief_engineer", "captain", "admin"]  # From catalog
if user["role"] not in allowed_roles:
    builder.set_error(
        "FORBIDDEN",
        f"Role '{user['role']}' cannot perform {action_name}. "
        f"Required: {', '.join(allowed_roles)}"
    )
    return builder.build()
```

**Test:** Attempt with insufficient role → MUST fail
**Failure Mode:** Privilege escalation (CRITICAL)

---

### G0.4: Atomic Transaction Boundary (T1)
**ALL OR NOTHING**

Multi-table mutations MUST:
- Wrap in single transaction
- Roll back ALL changes on any failure
- Never leave partial state

```python
# MANDATORY PATTERN for multi-table writes
try:
    # BEGIN transaction (implicit in Supabase)

    # 1. Update table A
    await self.db.table("table_a").update(...).execute()

    # 2. Insert into table B
    await self.db.table("table_b").insert(...).execute()

    # 3. Update table C
    await self.db.table("table_c").update(...).execute()

    # COMMIT (implicit on success)
except Exception as e:
    # ROLLBACK (automatic on exception)
    logger.error(f"Transaction failed: {e}")
    raise
```

**Test:** Force failure mid-transaction → NO partial data
**Failure Mode:** Inconsistent database state (CATASTROPHIC)

---

### G0.5: Idempotency / Replay Safety (T2)
**CAN THIS BE RETRIED SAFELY?**

Critical operations (imports, commits, financial) MUST:
- Accept idempotency key
- Check if operation already completed
- Return existing result if duplicate request

```python
# MANDATORY PATTERN for MUTATE_HIGH
idempotency_key = params.get("idempotency_key")
if not idempotency_key:
    builder.set_error("VALIDATION_FAILED", "idempotency_key required")
    return builder.build()

# Check if already processed
existing = await self.db.table("operations").select("*").eq(
    "idempotency_key", idempotency_key
).eq("yacht_id", yacht_id).single().execute()

if existing.data:
    # Return existing result, do not re-execute
    return existing.data["result"]
```

**Test:** Submit same operation twice → MUST return same result
**Failure Mode:** Duplicate financial transactions, inventory corruption

---

### G0.6: Immutable Audit Trail (S3)
**APPEND-ONLY EVENT LOG**

Every MUTATE action MUST:
- Create `pms_audit_log` entry
- Include: actor, timestamp, old_values, new_values, action hash
- Never update or delete audit records

```python
# MANDATORY PATTERN - ALL MUTATIONS
await self.db.table("pms_audit_log").insert({
    "id": str(uuid.uuid4()),
    "yacht_id": yacht_id,
    "action": action_name,
    "entity_type": entity_type,
    "entity_id": entity_id,
    "user_id": user_id,
    "user_name": user["full_name"],
    "user_role": user["role"],
    "old_values": old_values,  # JSONB snapshot before
    "new_values": new_values,  # JSONB snapshot after
    "changes_summary": f"{user['full_name']} {action_description}",
    "risk_level": risk_level,  # "low", "medium", "high"
    "signature": signature if required else None,
    "created_at": datetime.now(timezone.utc).isoformat()
}).execute()
```

**Test:** Every mutation must create audit entry
**Failure Mode:** No accountability, regulatory failure

---

### G0.7: State Machine Enforcement (B1)
**NO INVALID TRANSITIONS**

State-based actions MUST:
- Validate current state before transition
- Use explicit state transition map
- Reject invalid transitions

```python
# MANDATORY PATTERN
VALID_TRANSITIONS = {
    'reported': ['acknowledged', 'false_alarm'],
    'acknowledged': ['diagnosed', 'false_alarm'],
    'diagnosed': ['work_created', 'closed'],
    'work_created': ['work_completed'],
    'work_completed': ['closed'],
    'closed': ['reopened'],
    'false_alarm': []  # Terminal
}

current_status = entity["status"]
new_status = params["status"]

valid = VALID_TRANSITIONS.get(current_status, [])
if new_status not in valid:
    builder.set_error(
        "INVALID_STATE",
        f"Cannot transition from {current_status} to {new_status}"
    )
    return builder.build()
```

**Test:** Attempt invalid transition → MUST fail
**Failure Mode:** Corrupted workflow states

---

### G0.8: Signature / Countersign (where required)
**HIGH-VALUE ACCOUNTABILITY**

MUTATE_HIGH actions with signature requirement MUST:
- Validate signature_data present when required
- Store signature with audit trail
- Enforce signature thresholds (e.g., >$1000)

```python
# MANDATORY PATTERN (when signature_required = true)
signature_data = params.get("signature_data")

# Check if signature required by value threshold
if total_value > signature_threshold and not signature_data:
    builder.set_error(
        "SIGNATURE_REQUIRED",
        f"Signature required for {action_name} over ${signature_threshold:,.2f}"
    )
    return builder.build()

# Validate signature structure
if signature_data:
    if not signature_data.get("signature"):
        builder.set_error("VALIDATION_FAILED", "Invalid signature format")
        return builder.build()
```

**Test:** High-value operation without signature → MUST fail
**Failure Mode:** Unauthorized high-risk operations

---

## G1 — CRITICAL SAFETY (11 guards)

### G1.1: Concurrency Control (C1)
**Optimistic Locking**

```python
# Row version check before update
current_version = entity["version"]
update_result = await self.db.table("table").update({
    "field": new_value,
    "version": current_version + 1
}).eq("id", entity_id).eq("version", current_version).execute()

if not update_result.data:
    builder.set_error("CONFLICT", "Entity modified by another user")
    return builder.build()
```

**Applies to:** MUTATE_MEDIUM, MUTATE_HIGH on frequently updated entities

---

### G1.2: Deduplication Checks (B3)
**Prevent Duplicate Creation**

```python
# Check for existing entity with same natural key
existing = await self.db.table("parts").select("id").eq(
    "manufacturer_part_number", part_number
).eq("manufacturer", manufacturer).eq("yacht_id", yacht_id).execute()

if existing.data:
    builder.set_error("DUPLICATE", f"Part already exists: {existing.data[0]['id']}")
    return builder.build()
```

**Applies to:** CREATE operations (add_part, add_equipment, etc.)

---

### G1.3: Input Schema Validation (D1, D4, D5, D6)
**Strict Type & Format Validation**

```python
# Required fields
required = ["field1", "field2", "field3"]
missing = [f for f in required if not params.get(f)]
if missing:
    builder.set_error("VALIDATION_FAILED", f"Missing: {', '.join(missing)}")
    return builder.build()

# String length limits
if len(params["description"]) > 5000:
    builder.set_error("VALIDATION_FAILED", "Description too long (max 5000 chars)")
    return builder.build()

# Numeric ranges
if params["quantity"] <= 0:
    builder.set_error("VALIDATION_FAILED", "Quantity must be > 0")
    return builder.build()

# Date validation
if params["due_date"] < datetime.now():
    builder.set_error("VALIDATION_FAILED", "Due date cannot be in the past")
    return builder.build()
```

**Applies to:** All MUTATE actions

---

### G1.4: SQL Injection Prevention (D2)
**Parameterized Queries Only**

```python
# NEVER do this:
query = f"SELECT * FROM parts WHERE name = '{user_input}'"

# ALWAYS use Supabase client (auto-parameterized):
result = await self.db.table("parts").select("*").eq("name", user_input).execute()
```

**Applies to:** All database operations

---

### G1.5: XSS Prevention (D3)
**Sanitize User Input**

```python
import bleach

# For rich text fields
sanitized = bleach.clean(
    params["description"],
    tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li'],
    strip=True
)

# For plain text (strip all HTML)
sanitized = bleach.clean(params["text"], tags=[], strip=True)
```

**Applies to:** Text fields stored in database

---

### G1.6: Immutability Enforcement (B5)
**Prevent Modification of Committed Records**

```python
# Check if entity is in immutable state
IMMUTABLE_STATES = ["committed", "closed", "archived"]
if entity["status"] in IMMUTABLE_STATES:
    builder.set_error(
        "IMMUTABLE",
        f"Cannot modify {entity_type} in {entity['status']} state"
    )
    return builder.build()
```

**Applies to:** Update/delete operations on state-based entities

---

### G1.7: Referential Integrity (I2, I5)
**Validate Foreign Keys Exist**

```python
# Before creating entity, validate all foreign keys
part = await self.db.table("parts").select("id").eq(
    "id", params["part_id"]
).eq("yacht_id", yacht_id).single().execute()

if not part.data:
    builder.set_error("NOT_FOUND", f"Part not found: {params['part_id']}")
    return builder.build()
```

**Applies to:** All operations with foreign keys

---

### G1.8: Sensitive Data Redaction (S2)
**Never Log Secrets**

```python
# Before logging, redact sensitive fields
safe_params = {k: v for k, v in params.items() if k not in [
    'password', 'api_key', 'secret', 'token', 'signature_data'
]}

logger.info(f"Processing {action_name}: {safe_params}")
```

**Applies to:** All logging operations

---

### G1.9: Rate Limiting (C3)
**Prevent Abuse**

```python
# Check recent action count
recent_count = await self.db.table("pms_audit_log").select(
    "count"
).eq("user_id", user_id).eq("action", action_name).gte(
    "created_at", (datetime.now() - timedelta(hours=1)).isoformat()
).execute()

if recent_count.data[0]["count"] > 100:
    builder.set_error("RATE_LIMITED", "Too many requests. Try again later.")
    return builder.build()
```

**Applies to:** Public-facing endpoints, bulk operations

---

### G1.10: Compensating Actions (instead of destructive updates)
**Preserve History**

```python
# Instead of DELETE
await self.db.table("entity").update({
    "deleted_at": datetime.now().isoformat(),
    "deleted_by": user_id
}).eq("id", entity_id).execute()

# Instead of UPDATE (for critical fields)
await self.db.table("entity_history").insert({
    "entity_id": entity_id,
    "old_value": old_value,
    "new_value": new_value,
    "changed_by": user_id
}).execute()
```

**Applies to:** Delete operations, critical field updates

---

### G1.11: SECURITY DEFINER Functions Locked (A2 extension)
**Privileged Functions Cannot Be Called Directly**

```sql
-- RPC functions that bypass RLS MUST check permissions internally
CREATE OR REPLACE FUNCTION commit_receiving_session(...)
RETURNS json
SECURITY DEFINER  -- Bypasses RLS
AS $$
BEGIN
    -- MUST validate yacht isolation internally
    IF NOT EXISTS (
        SELECT 1 FROM user_profiles
        WHERE id = auth.uid()
        AND yacht_id = _yacht_id
    ) THEN
        RAISE EXCEPTION 'Access denied';
    END IF;

    -- ... rest of function
END;
$$ LANGUAGE plpgsql;

-- Prevent direct calls
REVOKE EXECUTE ON FUNCTION commit_receiving_session FROM authenticated;
```

**Applies to:** All SECURITY DEFINER functions

---

## G2 — OPERATIONAL HARDENING (8 guards)

### G2.1: Structured Metrics (M1)
**Performance Tracking**

```python
start_time = time.time()

try:
    # ... action execution

    duration = time.time() - start_time
    await self.db.table("pms_metrics").insert({
        "action": action_name,
        "duration_ms": duration * 1000,
        "status": "success",
        "yacht_id": yacht_id
    }).execute()
except Exception as e:
    duration = time.time() - start_time
    await self.db.table("pms_metrics").insert({
        "action": action_name,
        "duration_ms": duration * 1000,
        "status": "error",
        "error_type": type(e).__name__
    }).execute()
```

**Applies to:** All actions (especially MUTATE_HIGH)

---

### G2.2: Query Timeouts (P1)
**Prevent Runaway Queries**

```python
# Set statement timeout
await self.db.rpc('set_query_timeout', {'timeout_ms': 30000}).execute()

# Execute query
result = await self.db.table("large_table").select("*").execute()
```

**Applies to:** Complex queries, aggregations

---

### G2.3: Result Set Limits (P2)
**Prevent Memory Overflow**

```python
# Always paginate large results
result = await self.db.table("parts").select("*").range(
    offset, offset + limit - 1
).execute()

# Maximum page size
MAX_PAGE_SIZE = 1000
if limit > MAX_PAGE_SIZE:
    limit = MAX_PAGE_SIZE
```

**Applies to:** List/search operations

---

### G2.4: Retry Policy + Dead Letter Queue (T3)
**Handle Transient Failures**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_external_api():
    # ... API call
    pass

# If all retries fail, log to DLQ
try:
    await call_external_api()
except Exception as e:
    await self.db.table("dead_letter_queue").insert({
        "action": action_name,
        "payload": params,
        "error": str(e),
        "retries_exhausted": True
    }).execute()
```

**Applies to:** External API calls, background jobs

---

### G2.5: Partial Failure Reporting (H1)
**Per-Row Error Details**

```python
# For bulk operations
results = {
    "success": [],
    "failed": [],
    "total": len(items)
}

for item in items:
    try:
        result = await process_item(item)
        results["success"].append(result)
    except Exception as e:
        results["failed"].append({
            "item": item,
            "error": str(e)
        })

return results
```

**Applies to:** Bulk import, batch operations

---

### G2.6: Background Job Isolation (separation from API)
**Long-Running Tasks Don't Block Requests**

```python
# Enqueue background job instead of blocking
job_id = str(uuid.uuid4())
await self.db.table("background_jobs").insert({
    "id": job_id,
    "type": "process_document_chunks",
    "payload": params,
    "status": "queued"
}).execute()

# Return job ID immediately
builder.set_data({"job_id": job_id, "status": "processing"})
```

**Applies to:** Document processing, bulk imports, reports

---

### G2.7: Health Checks (M2)
**System Availability Monitoring**

```python
# /health endpoint
async def health_check():
    checks = {}

    # Database connectivity
    try:
        await self.db.table("yachts").select("count").limit(1).execute()
        checks["database"] = "healthy"
    except:
        checks["database"] = "unhealthy"

    # Storage availability
    try:
        await self.storage.list("pms-documents")
        checks["storage"] = "healthy"
    except:
        checks["storage"] = "unhealthy"

    return checks
```

**Applies to:** System-level monitoring

---

### G2.8: Action Tracing (M3)
**Distributed Tracing for Multi-Action Flows**

```python
# Create trace context
trace_id = params.get("trace_id") or str(uuid.uuid4())

# Log with trace context
logger.info(f"[{trace_id}] Starting {action_name}")

# Pass to nested actions
nested_params = {**params, "trace_id": trace_id}
await nested_action(nested_params)

logger.info(f"[{trace_id}] Completed {action_name}")
```

**Applies to:** Multi-step workflows

---

## G3 — UX/CONVENIENCE (7 guards)

### G3.1: Friendly Error Messages (H3)
**User-Readable Errors**

```python
# Instead of: "FK constraint violation"
builder.set_error(
    "VALIDATION_FAILED",
    "This work order cannot be deleted because it has associated parts. "
    "Please remove the parts first."
)
```

---

### G3.2: Smart Suggestions (follow-up actions)
**What Can User Do Next?**

```python
builder.add_action(AvailableAction(
    action_id="view_work_order",
    label="View Work Order",
    entity_type="work_order",
    entity_id=work_order_id
))
```

---

### G3.3: Smart Defaults
**Pre-fill Common Values**

```python
# Default priority based on severity
if not params.get("priority"):
    if params.get("severity") == "critical":
        params["priority"] = "high"
```

---

### G3.4: UI Hints (in response)
**Guide User Actions**

```python
builder.set_message(
    "Fault reported successfully. An engineer will acknowledge it shortly.",
    Severity.SUCCESS
)
```

---

### G3.5: Progress Indicators (for long operations)
**Real-Time Feedback**

```python
# Update job status periodically
await self.db.table("background_jobs").update({
    "progress_percent": 45,
    "progress_message": "Processing row 450 of 1000"
}).eq("id", job_id).execute()
```

---

### G3.6: Batch Operation Previews
**Show What Will Happen**

```python
# For bulk delete
preview = {
    "items_to_delete": len(items),
    "affected_entities": {
        "work_orders": 3,
        "shopping_list_items": 5
    }
}
builder.set_data(preview)
```

---

### G3.7: Contextual Help Text
**In-App Documentation**

```python
builder.set_data({
    "help_text": "Committing this session will update inventory. This cannot be undone.",
    "learn_more_url": "/docs/receiving-process"
})
```

---

## ENFORCEMENT MECHANISMS

### 1. Handler Template with G0 Checklist

Every new handler file MUST include:

```python
"""
{Action Name} Handler
=====================

G0 COMPLIANCE CHECKLIST (MANDATORY):
- [ ] G0.1: Yacht isolation (A2)
- [ ] G0.2: Authentication gate (A1)
- [ ] G0.3: Role-based access (A3)
- [ ] G0.4: Atomic transactions (T1) [if multi-table]
- [ ] G0.5: Idempotency (T2) [if MUTATE_HIGH]
- [ ] G0.6: Audit trail (S3)
- [ ] G0.7: State machine (B1) [if state-based]
- [ ] G0.8: Signature (if required)

G1 COMPLIANCE (Required with waiver if missing):
- [ ] G1.1: Concurrency control (C1)
- [ ] G1.3: Input validation (D1-D6)
- [ ] G1.6: Immutability check (B5)
- [ ] G1.7: Foreign key validation (I2)
"""
```

---

### 2. CI Check Script (Basic)

```python
# scripts/check_g0_compliance.py
import re
import sys

G0_PATTERNS = {
    "yacht_isolation": r'yacht_id.*!=.*yacht_id',
    "auth_check": r'if not user_id',
    "role_check": r'allowed_roles.*=',
    "audit_log": r'pms_audit_log.*insert'
}

def check_handler_file(filepath):
    with open(filepath) as f:
        content = f.read()

    missing = []
    for guard, pattern in G0_PATTERNS.items():
        if not re.search(pattern, content):
            missing.append(guard)

    return missing

# Run on all *_mutation_handlers.py files
# Fail CI if G0 guards missing in MUTATE_HIGH handlers
```

---

### 3. PR Review Template

```markdown
## Handler Review Checklist

### G0 Guards (BLOCK if missing)
- [ ] Yacht isolation implemented correctly
- [ ] Authentication validated
- [ ] Role check present and correct
- [ ] Audit log entry created
- [ ] Transaction boundaries correct (if multi-table)

### G1 Guards (Require waiver if missing)
- [ ] Input validation comprehensive
- [ ] Foreign keys validated
- [ ] State transitions valid
- [ ] Concurrency handled (if needed)

### Tests
- [ ] Yacht isolation test (different yacht_id)
- [ ] Role enforcement test (insufficient role)
- [ ] Audit log creation verified
```

---

## MAPPING TO EXISTING CATALOG

### Guard ID Cross-Reference

| Old ID | New Severity | Guard Name |
|--------|--------------|------------|
| A1 | G0.2 | Authentication |
| A2 | G0.1 | Yacht Isolation |
| A3 | G0.3 | Role-Based Access |
| A4 | A3 extension | Conditional Permissions |
| B1 | G0.7 | State Transitions |
| B2 | G1.7 | Entity Existence |
| B3 | G1.2 | Duplicate Prevention |
| B4 | G1.7 | Dependency Checks |
| B5 | G1.6 | Immutability |
| C1 | G1.1 | Optimistic Locking |
| C2 | G1.1 | Operation Locks |
| C3 | G1.9 | Rate Limiting |
| T1 | G0.4 | Atomic Transactions |
| T2 | G0.5 | Idempotency |
| T3 | G2.4 | Retry + DLQ |
| D1 | G1.3 | Input Sanitization |
| D2 | G1.4 | SQL Injection Prevention |
| D3 | G1.5 | XSS Prevention |
| D4-D6 | G1.3 | Format Validation |
| E1-E3 | G2.4 | External Dependencies |
| F1-F5 | G1.3 | File Upload Validation |
| H1 | G2.5 | Error Classification |
| H2 | G0.6 extension | Comprehensive Logging |
| H3 | G3.1 | User-Friendly Errors |
| S1-S2 | G1.8 | CSRF + Data Redaction |
| S3 | G0.6 | Audit Logging |
| S4-S5 | G1.9 | Brute Force + CSP |
| I1-I5 | G1.3, G1.7 | Data Integrity |
| P1-P5 | G2.2, G2.3 | Performance |
| M1-M3 | G2.1, G2.7, G2.8 | Monitoring |

---

## LOCK THIS NOW

**DO NOT:**
- Simplify G0 patterns "for speed"
- Skip G0 checks "just this once"
- Remove guards to "improve UX"
- Let engineers debate G0 requirements

**DO:**
- Freeze G0 pattern from `commit_receiving_session`
- Require G0 checklist in every handler file header
- Add CI check for G0 patterns
- Train all engineers on severity levels

---

**This taxonomy is CANONICAL.**
**G0 guards are NON-NEGOTIABLE.**
**Enforcement begins immediately.**

**Last Updated:** 2026-01-12
**Version:** 1.0 - LOCKED
