# Database Schema: Trust-First Design & Naming Conventions

**Date:** 2026-01-09
**Author:** Claude (based on user's trust requirements)
**Core Principle:** **Trust is the slowest adoption barrier. No "black box" systems.**

---

## Executive Summary: Why These Tables Are Paramount

Your statement is the foundation of this entire design:

> "trust will be the reason for our slowest adoption of users, not feature. having a 'black box' that reads users, behaviour etc. is untrustworthy, no matter how good it is. we need to focus on the auditing, accountability, clarity, and no task auto-completed without consent."

**Every table below exists for ONE reason:** **To make the system transparent, accountable, and trustworthy.**

---

## Current Naming Pattern Analysis

**From handlers code analysis:**

**Pattern 1: Prefixed tables** (via `get_table()` function)
```python
self.db.table(get_table("equipment"))      # → pms_equipment?
self.db.table(get_table("work_orders"))    # → pms_work_orders?
self.db.table(get_table("parts"))          # → pms_parts? or inventory?
self.db.table(get_table("faults"))         # → pms_faults?
```

**Pattern 2: Direct table references**
```python
self.db.table("document_chunks")           # No prefix
self.db.table("documents")                 # No prefix
self.db.table("predictive_state")          # No prefix
self.db.table("attachments")               # No prefix
self.db.table("graph_edges")               # No prefix
self.db.table("sensor_readings")           # No prefix
self.db.table("maintenance_templates")     # No prefix
```

**Analysis:**
- Core operational tables (equipment, faults, work_orders, parts) use `get_table()` → suggests **`pms_` prefix**
- RAG/ML/document tables are referenced directly → **no prefix**

**Recommended naming convention:**
```
Operational/transactional tables: pms_*
Document/knowledge tables: (no prefix)
```

---

## Proposed Schema with Organizational Naming

### Naming Convention Decision: **`pms_` prefix for operational tables**

**Rationale:**
1. Matches handler expectations (`get_table("work_orders")` → `pms_work_orders`)
2. Separates operational data (PMS = Planned Maintenance System) from other systems
3. Clear organizational boundary

---

## Tables: Trust & Accountability Justifications

### 🔴 TIER 1: CRITICAL FOR TRUST (Non-Negotiable)

---

#### Table 1: `pms_audit_log`

**Why this table is PARAMOUNT:**

| Trust Principle | How This Table Delivers |
|----------------|-------------------------|
| **No "black box"** | Every mutation is visible - no hidden changes |
| **Accountability** | WHO did WHAT is recorded with signature |
| **Transparency** | old_values + new_values show exact changes |
| **Maritime compliance** | Audit trails required by regulations |
| **Forensics** | If something breaks, we can trace who/what/when |

**Schema:**
```sql
CREATE TABLE public.pms_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),

    -- WHAT happened
    action TEXT NOT NULL,              -- e.g., 'create_work_order_from_fault'
    entity_type TEXT NOT NULL,          -- e.g., 'work_order', 'part_usage'
    entity_id UUID NOT NULL,            -- ID of thing that changed

    -- WHO did it
    user_id UUID NOT NULL REFERENCES auth.users(id),
    signature JSONB NOT NULL,           -- {user_id, timestamp, ip_address}

    -- WHAT changed (full transparency)
    old_values JSONB,                   -- State before (NULL for creates)
    new_values JSONB NOT NULL,          -- State after

    -- WHEN it happened
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pms_audit_log_yacht ON pms_audit_log(yacht_id, created_at DESC);
CREATE INDEX idx_pms_audit_log_user ON pms_audit_log(user_id, created_at DESC);
CREATE INDEX idx_pms_audit_log_entity ON pms_audit_log(entity_type, entity_id);
```

**Why NOT use existing tables:**
- ✗ No existing audit table
- ✗ Cannot use `user_roles` (authorization, not auditing)
- ✗ Cannot use `api_tokens` (authentication, not auditing)

**What would happen without this table:**
- ❌ Users don't know who changed what → **Trust destroyed**
- ❌ No forensics when things go wrong → **Blame game**
- ❌ No compliance → **Maritime regulations violated**

---

#### Table 2: `pms_work_orders`

**Why this table is PARAMOUNT:**

| Trust Principle | How This Table Delivers |
|----------------|-------------------------|
| **Accountability** | Signed completion: "I did this work" |
| **No auto-execution** | Work orders created by user click, not ML |
| **Transparency** | Clear status, assignee, completion notes |
| **Consent** | User explicitly creates, assigns, completes |

**Schema:**
```sql
CREATE TABLE public.pms_work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),

    -- Human-readable identifier
    number TEXT NOT NULL,               -- WO-2024-089

    -- WHAT needs to be done
    title TEXT NOT NULL,
    description TEXT,
    equipment_id UUID REFERENCES public.pms_equipment(id),
    fault_id UUID REFERENCES public.pms_faults(id),
    location TEXT,
    priority TEXT NOT NULL DEFAULT 'normal',

    -- WHO is responsible (accountability)
    created_by UUID NOT NULL REFERENCES auth.users(id),
    assigned_to UUID REFERENCES auth.users(id),

    -- Status (transparency - no hidden states)
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',      -- Created but not started
        'open',          -- Ready to work
        'in_progress',   -- Being worked on
        'pending_parts', -- Waiting for parts
        'completed',     -- Work done (signed off)
        'closed',        -- Archived
        'cancelled'      -- Cancelled
    )),

    -- Completion (signed accountability)
    completed_by UUID REFERENCES auth.users(id),
    completed_at TIMESTAMPTZ,
    completion_notes TEXT,              -- WHAT was done (transparency)

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, number)
);

CREATE INDEX idx_pms_wo_yacht ON pms_work_orders(yacht_id, status);
CREATE INDEX idx_pms_wo_assigned ON pms_work_orders(assigned_to) WHERE status NOT IN ('completed', 'closed', 'cancelled');
```

**Why NOT use existing tables:**
- ✗ No existing work order table
- ✗ Cannot store in `yachts` metadata (wrong entity, not queryable)
- ✗ Cannot store in `user_profiles` (wrong entity)

**What would happen without this table:**
- ❌ No way to track WHO did WHAT work → **No accountability**
- ❌ No signed completion → **No proof work was done**
- ❌ No transparency in work status → **Black box**

---

#### Table 3: `pms_part_usage`

**Why this table is PARAMOUNT:**

| Trust Principle | How This Table Delivers |
|----------------|-------------------------|
| **No "black box" inventory** | Every deduction has WHO/WHAT/WHEN/WHY |
| **Accountability** | User signs off on part usage |
| **Transparency** | Complete history - can't be hidden |
| **Audit trail** | Required for inventory reconciliation |

**Schema:**
```sql
CREATE TABLE public.pms_part_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),

    -- WHAT was used
    part_id UUID NOT NULL REFERENCES public.pms_parts(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),

    -- WHERE/WHY was it used (transparency)
    work_order_id UUID REFERENCES public.pms_work_orders(id),
    equipment_id UUID REFERENCES public.pms_equipment(id),
    usage_reason TEXT CHECK (usage_reason IN (
        'work_order',    -- Used for WO (most common)
        'maintenance',   -- Preventive maintenance
        'emergency',     -- Emergency repair
        'testing',       -- Testing/commissioning
        'other'          -- Other (explain in notes)
    )),
    notes TEXT,

    -- WHO used it (accountability)
    used_by UUID NOT NULL REFERENCES auth.users(id),

    -- WHEN was it used
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pms_part_usage_yacht ON pms_part_usage(yacht_id, used_at DESC);
CREATE INDEX idx_pms_part_usage_part ON pms_part_usage(part_id, used_at DESC);
CREATE INDEX idx_pms_part_usage_wo ON pms_part_usage(work_order_id);
```

**Why separate table instead of columns on `pms_parts`:**
- ✅ Event log pattern → Each row = one deduction event
- ✅ **Cannot be overwritten** → Permanent audit trail
- ✅ Complete history → Can calculate usage trends
- ✅ Queryable → "Who used what parts in last 30 days?"

**What would happen without this table:**
- ❌ Inventory changes are a "black box" → **Trust destroyed**
- ❌ No way to know WHO used parts → **No accountability**
- ❌ No audit trail → **Cannot reconcile inventory**

---

### 🟡 TIER 2: HIGH IMPORTANCE FOR TRANSPARENCY

---

#### Table 4: `pms_work_order_notes`

**Why this table matters for trust:**
- **Communication:** Progress visible to all shifts
- **Transparency:** Can't hide notes in opaque JSON
- **Audit trail:** WHO said WHAT WHEN

**Schema:**
```sql
CREATE TABLE public.pms_work_order_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'general' CHECK (note_type IN (
        'general', 'progress', 'issue', 'resolution'
    )),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Why separate table instead of JSONB array:**
- ✅ Queryable → Find all notes by user/date
- ✅ Transparent → Each note is visible row
- ✅ Auditable → Can't hide in JSON blob

---

#### Table 5: `pms_work_order_parts`

**Why this table matters for trust:**
- **Transparency:** Shows parts PLANNING (shopping list)
- **NOT auto-deduction:** Parts added manually, not by ML
- **Consent:** User explicitly adds parts

**Schema:**
```sql
CREATE TABLE public.pms_work_order_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID NOT NULL REFERENCES public.pms_work_orders(id) ON DELETE CASCADE,
    part_id UUID NOT NULL REFERENCES public.pms_parts(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    notes TEXT,
    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(work_order_id, part_id)
);
```

**Critical distinction:**
- `pms_work_order_parts` → **Shopping list** (what's needed)
- `pms_part_usage` → **Actual usage** (what was consumed)

**Why both tables:**
- Planning ≠ Reality
- Parts planned might not be used
- Parts used might not have been planned (emergency)

---

#### Table 6: `pms_handover`

**Why this table matters for trust:**
- **Communication:** Shift handovers visible to all
- **Accountability:** WHO added WHAT to handover
- **Transparency:** No hidden notes

**Schema:**
```sql
CREATE TABLE public.pms_handover (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),

    -- Polymorphic reference (can point to WO, fault, equipment, or standalone note)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'work_order', 'fault', 'equipment', 'note'
    )),
    entity_id UUID,  -- NULL if entity_type='note'

    summary_text TEXT NOT NULL,
    category TEXT CHECK (category IN (
        'urgent', 'in_progress', 'completed', 'watch', 'fyi'
    )),
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 5),

    added_by UUID NOT NULL REFERENCES auth.users(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 🟢 TIER 3: CONDITIONAL (Check if Exist)

---

#### Table 7: `pms_equipment` (if doesn't exist)

**Check first:** Look for existing table named `equipment`, `pms_equipment`, `machinery`, `assets`

**If exists:** Use existing table, don't recreate

**If doesn't exist, create minimal schema:**
```sql
CREATE TABLE public.pms_equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    location TEXT,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'operational',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(yacht_id, name)
);
```

---

#### Table 8: `pms_faults` (if doesn't exist)

**Check first:** Look for existing table

**If exists:** Use existing table

**If doesn't exist:**
```sql
CREATE TABLE public.pms_faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    equipment_id UUID REFERENCES public.pms_equipment(id),
    fault_code TEXT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'medium',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

#### Table 9: `pms_parts` (if doesn't exist - likely exists as `inventory`)

**Check first:** Look for `parts`, `pms_parts`, `inventory`, `spares`, `stock`

**If exists:** **ADD COLUMNS** instead of creating new table:
```sql
-- Add accountability columns for stock counting
ALTER TABLE public.pms_parts  -- or inventory, or whatever exists
ADD COLUMN IF NOT EXISTS last_counted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_counted_by UUID REFERENCES auth.users(id);

COMMENT ON COLUMN pms_parts.last_counted_at IS 'Accountability: WHEN was stock last counted';
COMMENT ON COLUMN pms_parts.last_counted_by IS 'Accountability: WHO counted stock';
```

**If doesn't exist:**
```sql
CREATE TABLE public.pms_parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    name TEXT NOT NULL,
    part_number TEXT,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER DEFAULT 0,
    unit TEXT DEFAULT 'ea',
    location TEXT,

    -- Accountability for stock counting
    last_counted_at TIMESTAMPTZ,
    last_counted_by UUID REFERENCES auth.users(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(yacht_id, part_number)
);
```

---

## Redundancy Analysis: Are Existing Tables Now Redundant?

### Answer: **NO. Zero redundancy.**

| Existing Table | Current Purpose | Still Needed After Migration? | Why? |
|----------------|----------------|------------------------------|------|
| `yachts` | Vessel registry | ✅ **YES - CRITICAL** | All pms_* tables link to yacht_id for multi-tenancy |
| `user_profiles` | User identity | ✅ **YES - CRITICAL** | All created_by, assigned_to, completed_by link here |
| `user_roles` | Authorization (RBAC) | ✅ **YES - CRITICAL** | Determines WHO can create/complete work orders |
| `api_tokens` | API authentication | ✅ **YES** | P0 action endpoints require authentication |
| `yacht_signatures` | Upload routing | ✅ **YES** | Unrelated to work orders - different system |

**Conclusion:**
- **0 tables become redundant**
- **All existing tables serve different purposes**
- **New tables are ADDITIVE, not replacements**

---

## Implementation: `get_table()` Function

**Create this file:** `apps/api/handlers/schema_mapping.py`

```python
"""
Schema Mapping: Table Name Resolution
======================================

Maps logical table names to physical table names with organizational prefix.
"""

# Table name mapping with pms_ prefix for operational tables
TABLE_MAP = {
    "equipment": "pms_equipment",
    "faults": "pms_faults",
    "work_orders": "pms_work_orders",
    "parts": "pms_parts",
    "work_order_notes": "pms_work_order_notes",
    "work_order_parts": "pms_work_order_parts",
    "part_usage": "pms_part_usage",
    "audit_log": "pms_audit_log",
    "handover": "pms_handover",
}

def get_table(logical_name: str) -> str:
    """
    Resolve logical table name to physical table name.

    Args:
        logical_name: Logical name like 'work_orders', 'parts'

    Returns:
        Physical table name like 'pms_work_orders', 'pms_parts'

    Example:
        >>> get_table("work_orders")
        'pms_work_orders'
        >>> get_table("parts")
        'pms_parts'
    """
    return TABLE_MAP.get(logical_name, logical_name)
```

**Why this approach:**
- ✅ Single source of truth for naming
- ✅ Easy to change prefix if needed
- ✅ Handlers use logical names (cleaner code)
- ✅ Physical names match organizational structure

---

## Migration File: Final Naming Convention

**File:** `database/migrations/02_pms_tables_trust_first.sql`

```sql
-- Migration: PMS Tables - Trust & Accountability First
-- =====================================================
--
-- DESIGN PRINCIPLE:
-- "Trust is the slowest adoption barrier. No 'black box' systems."
--
-- This migration creates tables for:
-- 1. Complete audit trail (WHO did WHAT WHEN)
-- 2. Signed accountability (users sign off on work)
-- 3. Transparent inventory (no hidden deductions)
-- 4. Clear communication (shift handovers)
--
-- Every table exists to build user trust through transparency.
-- =====================================================

-- TIER 1: CRITICAL FOR TRUST (audit_log, work_orders, part_usage)
-- TIER 2: HIGH FOR TRANSPARENCY (work_order_notes, work_order_parts, handover)
-- TIER 3: CONDITIONAL (equipment, faults, parts - check if exist first)

-- All tables use pms_ prefix to match organizational structure
-- and separate operational data from document/knowledge systems.
```

---

## Summary: Trust-First Table Justifications

| Table | Trust Impact | Why It Exists | Replaces Existing? |
|-------|--------------|---------------|-------------------|
| `pms_audit_log` | 🔴 **CRITICAL** | Complete transparency - no "black box" | ❌ NO |
| `pms_work_orders` | 🔴 **CRITICAL** | Signed accountability - "I did this work" | ❌ NO |
| `pms_part_usage` | 🔴 **CRITICAL** | Inventory transparency - every deduction visible | ❌ NO |
| `pms_work_order_notes` | 🟡 **HIGH** | Communication transparency | ❌ NO |
| `pms_work_order_parts` | 🟡 **HIGH** | Parts planning transparency | ❌ NO |
| `pms_handover` | 🟡 **MEDIUM** | Shift communication visibility | ❌ NO |
| `pms_equipment` | 🟢 **CONDITIONAL** | Foundation (if doesn't exist) | ❓ CHECK |
| `pms_faults` | 🟢 **CONDITIONAL** | Foundation (if doesn't exist) | ❓ CHECK |
| `pms_parts` | 🟢 **CONDITIONAL** | Foundation (if exists, add columns) | ❓ CHECK |

---

## Final Recommendation

**1. Adopt `pms_` prefix** for all operational tables to match organizational structure

**2. Create schema_mapping.py** with `get_table()` function for clean code

**3. In migration comments**, emphasize **trust justifications**:
   - "This table exists to show users WHO did WHAT WHEN"
   - "No 'black box' - complete transparency"
   - "Required for maritime compliance and accountability"

**4. Before running migration:**
   - Check if `pms_equipment`, `pms_faults`, `pms_parts` exist
   - If they exist, use them (don't recreate)
   - If `pms_parts` exists, add `last_counted_at` and `last_counted_by` columns

---

## Trust Principles Delivered

✅ **NO "black box"** → `pms_audit_log` shows every change
✅ **Complete accountability** → Every record has `created_by`, `completed_by`, `used_by`
✅ **Preview before commit** → All MUTATE actions show changes before execution
✅ **Explicit consent** → No auto-execution - user must click to commit
✅ **Transparency** → old_values + new_values in audit log
✅ **Communication** → Handover and notes tables for shift visibility

**Result:** Users can trust the system because **everything is auditable, nothing is hidden, and all actions require explicit consent**.

---

**END OF DOCUMENT**
