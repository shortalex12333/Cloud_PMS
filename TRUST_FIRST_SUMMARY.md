# Trust-First Database Design: Summary for Review

**Date:** 2026-01-09
**Your Core Requirement:** Trust is the adoption barrier, not features.

---

## What I've Created

### 1. **DATABASE_TRUST_JUSTIFICATION.md**
   - Justifies EVERY new table with the "trust lens"
   - Explains why each table is paramount for accountability
   - Shows why existing tables cannot be used
   - Proves zero redundancy

### 2. **DATABASE_NAMING_AND_TRUST_FINAL.md**
   - Complete analysis of naming conventions
   - Recommends `pms_` prefix for operational tables
   - Tier 1 (CRITICAL), Tier 2 (HIGH), Tier 3 (CONDITIONAL) classification
   - Implementation guide with `get_table()` function

### 3. **schema_mapping.py**
   - Created the missing file that handlers expect
   - Maps logical names (`work_orders`) to physical names (`pms_work_orders`)
   - Single source of truth for table naming

---

## Key Findings: Trust Principles Applied

### ✅ TIER 1: CRITICAL FOR TRUST (Cannot ship without these)

1. **`pms_audit_log`**
   - **Why paramount:** Users see WHO did WHAT WHEN
   - **Trust impact:** NO "black box" - complete transparency
   - **Without it:** Trust destroyed - no forensics, no accountability

2. **`pms_work_orders`**
   - **Why paramount:** Signed accountability - "I did this work"
   - **Trust impact:** NO auto-execution - user explicitly creates/completes
   - **Without it:** No operational accountability

3. **`pms_part_usage`**
   - **Why paramount:** Every inventory deduction has WHO/WHAT/WHEN/WHY
   - **Trust impact:** NO "black box" inventory changes
   - **Without it:** Inventory is untrustworthy

### ✅ TIER 2: HIGH FOR TRANSPARENCY

4. **`pms_work_order_notes`** - Communication transparency
5. **`pms_work_order_parts`** - Parts planning visibility
6. **`pms_handover`** - Shift communication accountability

### ✅ TIER 3: CONDITIONAL (Check if exist first)

7. **`pms_equipment`** - Foundation (if doesn't exist)
8. **`pms_faults`** - Foundation (if doesn't exist)
9. **`pms_parts`** - Foundation (if exists, ADD columns for accountability)

---

## Recommended Naming Convention: `pms_` Prefix

**Rationale:**
- Handlers expect `get_table("work_orders")` → `pms_work_orders`
- Separates operational (PMS) from knowledge (documents, RAG)
- Clear organizational boundary
- Follows existing pattern in codebase

**Pattern:**
```
Operational tables:  pms_work_orders, pms_audit_log, pms_parts
Knowledge tables:    documents, document_chunks, graph_edges
```

---

## Zero Redundancy Confirmed

| Existing Table | Still Needed? | Why? |
|----------------|---------------|------|
| `yachts` | ✅ **YES** | All pms_* tables link to yacht_id |
| `user_profiles` | ✅ **YES** | All created_by/assigned_to link here |
| `user_roles` | ✅ **YES** | Authorization for WHO can do WHAT |
| `api_tokens` | ✅ **YES** | Authentication for P0 actions |
| `yacht_signatures` | ✅ **YES** | Unrelated to work orders |

**Result:** 0 tables become redundant. All new tables are ADDITIVE.

---

## Next Steps (Your Decision)

### Option A: You want to check actual Supabase database first

**I can help you:**
1. Connect to Supabase and query `information_schema.tables`
2. Check if `pms_equipment`, `pms_faults`, `pms_parts` exist
3. Check if there's a different naming pattern
4. Adjust migration accordingly

### Option B: You want to proceed with recommended naming

**I will:**
1. Update `02_p0_actions_tables_REVISED.sql` to use `pms_` prefix
2. Add detailed trust justifications in migration comments
3. Create conditional logic (IF NOT EXISTS for equipment/faults/parts)
4. Ready for deployment to Supabase

### Option C: You want a different naming pattern

**Tell me:**
- What prefix or pattern you prefer
- I'll update everything to match

---

## Files Ready for Your Review

1. **`DATABASE_TRUST_JUSTIFICATION.md`** (Trust lens for each table)
2. **`DATABASE_NAMING_AND_TRUST_FINAL.md`** (Complete naming analysis)
3. **`schema_mapping.py`** (Table name resolver)
4. **`02_p0_actions_tables_REVISED.sql`** (Needs final naming update)

---

## What Makes This "Trust-First"

✅ **NO behavioral tracking** - Zero ML predictions, zero confidence scores
✅ **Complete audit trail** - `pms_audit_log` captures every mutation
✅ **Signed accountability** - WHO did WHAT is recorded
✅ **Preview before commit** - Users see changes before they happen
✅ **Explicit consent** - NO auto-execution without user click
✅ **Transparency** - old_values + new_values show exact changes
✅ **Communication** - Handover and notes visible to all

**Your quote:**
> "we need to focus on the auditing, accountability, clarity, and no task auto-completed without consent"

**This design delivers:**
- ✅ Auditing → `pms_audit_log`
- ✅ Accountability → created_by, completed_by, used_by on every table
- ✅ Clarity → Clear status, notes, transparent changes
- ✅ No auto-completion → Every action requires user click + signature

---

## Your Call

**What would you like me to do next?**

A) Check actual Supabase database to verify tables/naming?
B) Finalize migration with `pms_` prefix and deploy?
C) Use a different naming pattern?
D) Something else?

---

**Trust is paramount. I've designed every table to support that goal.**
