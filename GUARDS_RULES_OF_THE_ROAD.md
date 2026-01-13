# GUARDS: RULES OF THE ROAD
**1 page. Memorize this. No excuses.**

---

## THE 4 RULES THAT NEVER BREAK

### 1. YACHT ISOLATION (G0.1)
**Every database query filters by user's yacht.**

```python
# ALWAYS
user = await get_user_profile(user_id)
if user["yacht_id"] != yacht_id:
    logger.critical(f"Yacht breach by {user_id}")
    raise Forbidden("Access denied")

# In EVERY query
.eq("yacht_id", yacht_id)
```

**Never accept yacht_id from client. Always derive from auth.**

---

### 2. AUTHENTICATION + ROLE (G0.2 + G0.3)
**Validate who + can they do this.**

```python
# WHO
user_id = params.get("user_id")
if not user_id:
    raise Unauthorized("Not authenticated")

# CAN THEY
allowed_roles = ["chief_engineer", "captain", "admin"]
if user["role"] not in allowed_roles:
    raise Forbidden(f"Role {user['role']} cannot {action_name}")
```

---

### 3. AUDIT EVERYTHING (G0.6)
**ALL mutations create audit log.**

```python
await create_audit_log(
    action=action_name,
    entity_type=entity_type,
    entity_id=entity_id,
    user_id=user_id,
    old_values=old_values,  # Before
    new_values=new_values,  # After
    situation_id=situation_id  # Context
)
```

**No mutation without audit. Ever.**

---

### 4. SITUATION FIRST (G0.9)
**MUTATE_HIGH requires situation_id.**

```python
# For ALL MUTATE_HIGH actions
situation_id = params.get("situation_id")
if not situation_id:
    raise ValidationError("situation_id required")

# Enforces: "Search is orientation, click is commitment"
# Prevents: Button soup
```

**No situation = no mutation.**

---

## THE G0/G1/G2 HIERARCHY

| Level | Meaning | Enforcement | Waiver |
|-------|---------|-------------|--------|
| **G0** | MANDATORY BLOCKER | Build fails | ❌ NEVER |
| **G1** | CRITICAL SAFETY | Build fails OR waiver | ✅ With expiry |
| **G2** | OPERATIONAL HARDENING | Tech debt | ✅ Always |
| **G3** | UX/CONVENIENCE | None | N/A |

---

## G0 CHECKLIST (9 guards - Know These)

Every handler must declare:

```python
GUARDS = {
    "G0.1": True,          # Yacht isolation
    "G0.2": True,          # Authentication
    "G0.3": True,          # Role check
    "G0.4": "conditional", # Transactions (if multi-table)
    "G0.5": False,         # Idempotency (not needed for this action)
    "G0.6": True,          # Audit trail
    "G0.7": "conditional", # State machine (if state-based)
    "G0.8": False,         # Signature (not required)
    "G0.9": True           # Situation ID (if MUTATE_HIGH)
}
```

**CI reads this dict. If you lie, build fails.**

---

## WHEN YOU NEED EACH GUARD

### MUTATE_HIGH (All Critical Operations)
**Required G0:** All 9 guards
- G0.1: Yacht isolation
- G0.2: Authentication
- G0.3: Role check
- G0.4: Atomic transactions
- G0.5: Idempotency
- G0.6: Audit trail
- G0.7: State machine
- G0.8: Signature (if value > threshold)
- G0.9: Situation ID

**Example:** commit_receiving_session, decommission_equipment, schedule_drydock

---

### MUTATE_MEDIUM (Most Operations)
**Required G0:** 1, 2, 3, 6
**Conditional G0:** 4 (if multi-table), 7 (if state-based)

**Example:** create_work_order, approve_shopping_item, update_equipment

---

### MUTATE_LOW (Simple Updates)
**Required G0:** 1, 2, 3, 6

**Example:** add_note, update_part, acknowledge_handover

---

### READ (Queries Only)
**Required G0:** 1, 2 only
**No audit log needed.**

**Example:** view_fault, search_parts, list_equipment

---

## THE 3 FUNCTIONS YOU MUST CALL

### 1. require_yacht_isolation(user_id, yacht_id)
Validates user belongs to yacht. Throws if breach.

### 2. require_role(user, allowed_roles)
Validates user has required role. Throws if insufficient.

### 3. create_audit_log(...)
Creates audit trail. Returns audit_id.

**If you don't call these, CI fails.**

---

## TRANSACTIONS: WHEN AND HOW

**If you touch >1 table, wrap in transaction:**

```python
async with self.db.transaction():
    # Update table A
    await self.db.table("table_a").update(...).execute()

    # Insert into table B
    await self.db.table("table_b").insert(...).execute()

    # Update table C
    await self.db.table("table_c").update(...).execute()

# All succeed or all roll back
```

**No partial state. Ever.**

---

## STATE MACHINES: THE PATTERN

```python
VALID_TRANSITIONS = {
    'draft': ['active', 'cancelled'],
    'active': ['completed', 'cancelled'],
    'completed': [],  # Terminal
    'cancelled': []   # Terminal
}

# Always validate
current = entity["status"]
new = params["status"]

if new not in VALID_TRANSITIONS.get(current, []):
    raise InvalidState(f"Cannot: {current} → {new}")
```

---

## WAIVERS (G1 Only)

**Format:** `waivers/{action_name}.md`

```markdown
# Waiver: {action_name}

Guard: G1.X - {guard_name}
Reason: {why we can't implement now}
Mitigation: {what we're doing instead}
Expiry: 2026-03-15
Owner: @engineer_github_handle

## Context
{Additional context}
```

**CI blocks if:**
- Waiver expired
- Waiver missing required fields
- Waiver for G0 item (NEVER allowed)

**Max waiver duration: 90 days**

---

## APPROVALS (For Dangerous Operations)

**Format:** `approvals/{action_name}.approval`

```
Product: @name 2026-01-12
Engineering: @name 2026-01-12
Security: @name 2026-01-12
```

**3 lines. 3 signatures. No meetings.**

**CI blocks implementation until file exists.**

---

## THE ONE THING TO REMEMBER

> **Freeze the frame, not the internals.**

**G0 scaffolding is locked:**
- Authentication check
- Yacht isolation
- Role validation
- Audit logging
- Transaction wrapper
- Situation context

**Everything else is flexible:**
- Business logic
- Validation details
- Error messages
- Follow-up actions

---

## QUICK REFERENCE

| Action Type | G0.1 | G0.2 | G0.3 | G0.4 | G0.5 | G0.6 | G0.7 | G0.8 | G0.9 |
|-------------|------|------|------|------|------|------|------|------|------|
| READ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MUTATE_LOW | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| MUTATE_MEDIUM | ✅ | ✅ | ✅ | ⚠️ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| MUTATE_HIGH | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |

**Legend:**
- ✅ Required
- ⚠️ Conditional (depends on operation)
- ❌ Not required

---

## CI COMMANDS

```bash
# Check compliance
python scripts/check_g0_compliance.py

# Check with verbose output
python scripts/check_g0_compliance.py --verbose

# Check specific file
python scripts/check_g0_compliance.py --file handlers/fault_mutation_handlers.py
```

**Exit codes:**
- 0 = Pass
- 1 = G0 violation (BLOCKS)
- 2 = G1 violation without waiver (BLOCKS)
- 3 = Script error

---

## COMMON MISTAKES

### ❌ DON'T:
```python
# Accepting yacht_id from client
yacht_id = params["yacht_id"]  # WRONG

# Skipping audit for "simple" updates
await self.db.table("parts").update(...)  # WRONG (no audit)

# Multi-table without transaction
await update_table_a()
await update_table_b()  # WRONG (no atomicity)
```

### ✅ DO:
```python
# Derive yacht_id from auth
user = await get_user_profile(user_id)
yacht_id = user["yacht_id"]

# Always audit
await update_entity(...)
await create_audit_log(...)

# Wrap in transaction
async with self.db.transaction():
    await update_table_a()
    await update_table_b()
```

---

## WHERE TO FIND MORE

- **Machine-readable spec:** `guards.yml`
- **CI script:** `scripts/check_g0_compliance.py`
- **Handler template:** `HANDLER_TEMPLATE.py`
- **Full appendix:** `GUARD_SEVERITY_TAXONOMY.md` (reference only)

---

**MEMORIZE THIS PAGE. FOLLOW IT. BUILD WILL ENFORCE IT.**

**Last Updated:** 2026-01-12
**Version:** 1.0
**Source of Truth:** `guards.yml`
