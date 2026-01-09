# Database Schema Justification: Trust & Accountability First

**Date:** 2026-01-09
**Context:** User feedback on trust being the slowest adoption barrier
**Principle:** "Black box" systems kill adoption. Auditing, accountability, clarity, and consent are paramount.

---

## User's Core Requirement

> "trust will be the reason for our slowest adoption of users, not feature. having a 'black box' that reads users, behaviour etc. is untrustworthy, no matter how good it is. we need to focus on the auditing, accountability, clarity, and no task auto-completed without consent."

**Translation:**
- ❌ NO behavioral tracking
- ❌ NO auto-execution without consent
- ❌ NO confidence scores or ML predictions
- ✅ YES complete audit trail (who, what, when)
- ✅ YES signature-based accountability
- ✅ YES transparency (preview before commit)

---

## Current Database State (from 01_core_tables_v2_secure.sql)

**Tables that ALREADY EXIST:**
```sql
✓ public.yachts                -- Each vessel using CelesteOS
✓ public.user_profiles         -- Minimal user data, linked to auth.users
✓ public.user_roles            -- RBAC role assignments (separated for security)
✓ public.api_tokens            -- Device tokens, API keys (not Supabase JWT)
✓ public.yacht_signatures      -- Yacht install signatures for upload routing
```

**Tables that DO NOT EXIST:**
- ❌ equipment
- ❌ faults
- ❌ work_orders
- ❌ parts / inventory
- ❌ audit_log
- ❌ handover
- ❌ any work order or maintenance tracking

**Evidence:** Handlers reference `get_table("equipment")`, `get_table("faults")`, etc. but these tables are not created in any migration file.

---

## Proposed Tables: Trust & Accountability Justification

### Category 1: AUDIT & ACCOUNTABILITY (Non-Negotiable for Trust)

#### 1. `audit_log` - **PARAMOUNT for user trust**

**Why this table is essential:**
- **Trust:** Users need to see WHO did WHAT and WHEN
- **Accountability:** Maritime regulations require audit trails
- **Transparency:** No "black box" - every mutation is logged
- **Forensics:** If something goes wrong, we can trace it

**Schema:**
```sql
CREATE TABLE public.audit_log (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    action TEXT NOT NULL,              -- e.g., 'create_work_order_from_fault'
    entity_type TEXT NOT NULL,          -- e.g., 'work_order', 'part_usage'
    entity_id UUID NOT NULL,            -- ID of created/modified entity
    user_id UUID NOT NULL,              -- WHO did it
    old_values JSONB,                   -- Previous state (transparency)
    new_values JSONB NOT NULL,          -- New state (transparency)
    signature JSONB NOT NULL,           -- {user_id, timestamp, ip_address}
    created_at TIMESTAMPTZ NOT NULL     -- WHEN it happened
);
```

**Why NOT use existing tables:**
- ❌ No existing audit table
- ❌ Cannot use user_roles table (different purpose - authorization, not auditing)
- ❌ Cannot use api_tokens table (different purpose - authentication, not auditing)

**Organizational naming:** `audit_log` (singular, matches existing pattern: `user_profiles`, `user_roles`)

**Trust impact:** **CRITICAL** - Without this, users have no visibility into who changed what.

---

### Category 2: CORE OPERATIONAL TABLES (Foundation for Transparency)

#### 2. `work_orders` - **PARAMOUNT for operational accountability**

**Why this table is essential:**
- **Accountability:** "Sign your name to say 'I did this work'"
- **Consent:** Work orders are explicitly created by users, not auto-generated
- **Transparency:** Every work order has clear status, assignee, completion notes
- **Audit trail:** Links to faults, equipment, parts, and signatures

**Schema:**
```sql
CREATE TABLE public.work_orders (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    number TEXT NOT NULL,               -- WO-2024-089 (human-readable)
    title TEXT NOT NULL,
    description TEXT,
    equipment_id UUID,                  -- What equipment?
    fault_id UUID,                      -- What fault triggered this?
    status TEXT NOT NULL,               -- Workflow: candidate → open → in_progress → completed
    assigned_to UUID,                   -- WHO is responsible?
    completed_by UUID,                  -- WHO signed off?
    completed_at TIMESTAMPTZ,           -- WHEN was it done?
    completion_notes TEXT,              -- WHAT was done? (transparency)
    created_by UUID NOT NULL,           -- WHO created it?
    created_at TIMESTAMPTZ NOT NULL     -- WHEN was it created?
);
```

**Why NOT use existing tables:**
- ❌ No existing work order table
- ❌ Cannot use yachts table (different entity)
- ❌ Cannot use user_profiles table (different entity)

**Organizational naming:** `work_orders` (plural, matches PostgreSQL conventions)

**Trust impact:** **CRITICAL** - Central entity for 5 out of 8 P0 actions. Without this, no operational accountability.

---

#### 3. `work_order_notes` - **Transparency & Communication**

**Why this table is essential:**
- **Transparency:** Notes provide context for WHY work was done
- **Communication:** Shift handovers, progress updates visible to all
- **Audit trail:** WHO added WHAT note WHEN

**Schema:**
```sql
CREATE TABLE public.work_order_notes (
    id UUID PRIMARY KEY,
    work_order_id UUID NOT NULL,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL,            -- general, progress, issue, resolution
    created_by UUID NOT NULL,           -- WHO added the note
    created_at TIMESTAMPTZ NOT NULL     -- WHEN was it added
);
```

**Why separate table instead of JSONB:**
- ✅ Queryable (find all notes by user, by date, by type)
- ✅ Auditable (each note is a separate row with timestamp)
- ✅ Transparent (can't hide notes in opaque JSON)

**Organizational naming:** `work_order_notes` (plural, descriptive)

**Trust impact:** **HIGH** - Provides transparency into work order progress.

---

#### 4. `work_order_parts` - **Transparency for Parts Planning**

**Why this table is essential:**
- **Transparency:** Shows what parts are NEEDED (shopping list)
- **NOT auto-deduction:** Parts are added manually, not automatically deducted
- **Consent:** User explicitly adds parts, no "black box" inventory changes

**Schema:**
```sql
CREATE TABLE public.work_order_parts (
    id UUID PRIMARY KEY,
    work_order_id UUID NOT NULL,
    part_id UUID NOT NULL,
    quantity INTEGER NOT NULL,
    notes TEXT,
    added_by UUID NOT NULL,             -- WHO added this part
    added_at TIMESTAMPTZ NOT NULL       -- WHEN was it added
);
```

**Why NOT use existing tables:**
- ❌ No existing junction table for work orders & parts
- ❌ Cannot store in work_orders.metadata JSONB (not queryable, not transparent)

**Organizational naming:** `work_order_parts` (plural, junction table pattern)

**Trust impact:** **MEDIUM** - Shows planning, no hidden inventory changes.

---

#### 5. `part_usage` - **CRITICAL for Inventory Accountability**

**Why this table is essential:**
- **Accountability:** WHO used WHAT part WHEN and WHY
- **Audit trail:** Every inventory deduction has a record
- **Transparency:** No "black box" inventory changes
- **Consent:** Parts are deducted only when user signs off on work order completion

**Schema:**
```sql
CREATE TABLE public.part_usage (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    part_id UUID NOT NULL,
    work_order_id UUID,                 -- Optional: if used for WO
    equipment_id UUID,                  -- Optional: what equipment
    quantity INTEGER NOT NULL,          -- How much was used
    usage_reason TEXT,                  -- WHY was it used
    notes TEXT,
    used_by UUID NOT NULL,              -- WHO used it
    used_at TIMESTAMPTZ NOT NULL        -- WHEN was it used
);
```

**Why separate table instead of columns on parts:**
- ✅ Event log pattern (each row = one deduction event)
- ✅ Complete history (can't be overwritten)
- ✅ Auditable (who used what, when)
- ✅ Queryable (usage stats, trends)

**Organizational naming:** `part_usage` (singular, event log pattern)

**Trust impact:** **CRITICAL** - Without this, inventory changes are a "black box".

---

#### 6. `handover` - **Communication & Shift Accountability**

**Why this table is essential:**
- **Communication:** Transparent shift handovers
- **Accountability:** WHO added WHAT to handover WHEN
- **Transparency:** No hidden notes, all handover items visible

**Schema:**
```sql
CREATE TABLE public.handover (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    entity_type TEXT NOT NULL,          -- work_order, fault, equipment, note
    entity_id UUID,                     -- Polymorphic reference
    summary_text TEXT NOT NULL,
    category TEXT,                      -- urgent, in_progress, completed, watch
    priority INTEGER,                   -- Display order
    added_by UUID NOT NULL,             -- WHO added to handover
    added_at TIMESTAMPTZ NOT NULL       -- WHEN was it added
);
```

**Why NOT use existing tables:**
- ❌ No existing handover table
- ❌ Cannot use work_order_notes (handover can reference faults, equipment, standalone notes)

**Organizational naming:** `handover` (singular, matches event log pattern)

**Trust impact:** **MEDIUM** - Provides transparency for shift communication.

---

### Category 3: CONDITIONAL TABLES (Check if Exist First)

#### 7. `equipment` - **IF NOT EXISTS**

**Check first:**
- Look for: `equipment`, `pms_equipment`, `machinery`, `assets`
- If exists: use existing table, don't recreate

**If doesn't exist, justification:**
- Required for work orders (what equipment is being worked on?)
- Required for faults (what equipment failed?)
- Minimal schema needed for MVP

**Organizational naming:**
- If `pms_equipment` exists → use that and add `pms_` prefix to all new tables
- If no prefix pattern → use `equipment`

---

#### 8. `faults` - **IF NOT EXISTS**

**Check first:**
- Look for: `faults`, `pms_faults`, `failures`, `issues`
- If exists: use existing table, don't recreate

**If doesn't exist, justification:**
- Required for P0 Action #2: create_work_order_from_fault
- Minimal schema needed for MVP

**Organizational naming:** Follow existing pattern (`faults` or `pms_faults`)

---

#### 9. `parts` - **IF NOT EXISTS (most likely exists as inventory)**

**Check first:**
- Look for: `parts`, `pms_parts`, `inventory`, `spares`, `stock`
- If exists: ADD COLUMNS instead of creating new table

**If exists, add columns:**
```sql
ALTER TABLE public.parts (or inventory)
ADD COLUMN IF NOT EXISTS last_counted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_counted_by UUID REFERENCES auth.users(id);
```

**Why add columns:**
- Required for P0 Action #6: check_stock_level
- Shows WHO counted stock WHEN (accountability)

**If doesn't exist, justification:**
- Required for parts-related P0 actions
- Minimal schema needed for MVP

**Organizational naming:** Follow existing pattern

---

## Comparison: Redundancy Check

### Are any EXISTING tables now redundant?

**NO.** The new tables are ADDITIVE, not replacements:

| Existing Table | Purpose | Still Needed? | Why? |
|----------------|---------|---------------|------|
| `yachts` | Vessel registry | ✅ YES | Work orders link to yachts via yacht_id |
| `user_profiles` | User identity | ✅ YES | Work orders link to users (created_by, assigned_to, completed_by) |
| `user_roles` | Authorization | ✅ YES | Determines who can create work orders, complete them, etc. |
| `api_tokens` | Authentication | ✅ YES | API access for P0 actions |
| `yacht_signatures` | Upload routing | ✅ YES | Unrelated to work orders |

**Conclusion:** **NO redundancy.** All existing tables serve different purposes.

---

## Naming Convention Decision

**Current analysis needed:**
1. Check if handlers use `get_table()` function with prefix mapping
2. Check if any tables use `pms_` prefix pattern
3. Follow established organizational pattern

**Recommendation:**
```python
# If pms_ pattern exists:
CREATE TABLE public.pms_work_orders ...
CREATE TABLE public.pms_work_order_notes ...
CREATE TABLE public.pms_part_usage ...
CREATE TABLE public.pms_audit_log ...
CREATE TABLE public.pms_handover ...

# If no prefix pattern:
CREATE TABLE public.work_orders ...
CREATE TABLE public.work_order_notes ...
CREATE TABLE public.part_usage ...
CREATE TABLE public.audit_log ...
CREATE TABLE public.handover ...
```

**Action:** Need to check actual Supabase database or handler code for `get_table()` implementation to determine naming.

---

## Summary: Trust-First Table Justifications

| Table | Trust Impact | Justification | Can Use Existing? |
|-------|--------------|---------------|-------------------|
| **audit_log** | 🔴 CRITICAL | Complete transparency - who did what, when | ❌ NO - doesn't exist |
| **work_orders** | 🔴 CRITICAL | Operational accountability - signed work completion | ❌ NO - doesn't exist |
| **work_order_notes** | 🟡 HIGH | Communication transparency | ❌ NO - doesn't exist |
| **work_order_parts** | 🟡 MEDIUM | Parts planning transparency | ❌ NO - doesn't exist |
| **part_usage** | 🔴 CRITICAL | Inventory accountability - no black box deductions | ❌ NO - doesn't exist |
| **handover** | 🟡 MEDIUM | Shift communication transparency | ❌ NO - doesn't exist |
| **equipment** | 🟢 CONDITIONAL | Foundation for work orders | ❓ CHECK FIRST |
| **faults** | 🟢 CONDITIONAL | Foundation for work orders | ❓ CHECK FIRST |
| **parts** | 🟢 CONDITIONAL | Foundation for inventory | ❓ CHECK FIRST (likely exists) |

---

## Next Actions

1. **Check actual database** to determine:
   - Which conditional tables (equipment, faults, parts) already exist
   - What naming pattern is used (pms_ prefix or not)

2. **Create revised migration** following naming pattern

3. **Document in migration comments:**
   - Why each table is essential for trust
   - Why existing tables cannot be used
   - Accountability/audit trail justification

---

## Trust Principles Applied

✅ **NO behavioral tracking** - No confidence scores, no evidence tables, no nudge systems
✅ **Complete audit trail** - Every mutation logged with user signature
✅ **Preview before commit** - All actions show side effects before execution
✅ **Explicit consent** - No auto-execution, every action requires user click
✅ **Transparency** - All changes visible in audit_log, no hidden mutations
✅ **Accountability** - Every record has created_by, completed_by, used_by fields

**Result:** Users can trust the system because there is NO "black box" - everything is auditable, transparent, and requires explicit consent.

---

**END OF JUSTIFICATION**
