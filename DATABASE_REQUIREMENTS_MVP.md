# Database Requirements Analysis - MVP P0 Actions

**Date:** 2026-01-08
**Purpose:** Identify what tables ACTUALLY exist vs what we NEED for MVP

---

## Current State Analysis

### ✅ Tables That ALREADY EXIST (from 01_core_tables_v2_secure.sql)

```sql
-- Core auth/user tables (EXIST)
- public.yachts
- public.user_profiles (links to auth.users)
- public.user_roles
- public.api_tokens
- public.yacht_signatures
```

### 🔍 Tables Referenced by Existing Handlers

From code analysis of `/apps/api/handlers/*.py`:

**Handlers reference these tables via `get_table()` or direct:**
- `equipment` (referenced)
- `faults` / `pms_faults` (referenced with prefix)
- `work_orders` / `pms_work_orders` (referenced with prefix)
- `parts` / `pms_parts` (referenced with prefix)
- `work_order_parts` (referenced)
- `checklist_items` (referenced)
- `attachments` (referenced)
- `audit_log` (referenced)
- `documents` / `document_chunks` (referenced)
- `predictive_state` (referenced)
- `sensor_readings` (referenced)
- `maintenance_templates` (referenced)
- `graph_edges` (referenced)
- `stock_transactions` (referenced)

**Conclusion:** The codebase EXPECTS these tables but they may not exist in migrations yet.

---

## What's Needed for MVP P0 Actions (8 Actions)

### Action Mapping to Tables:

| P0 Action | Required Tables | Already Exists? | New Columns Needed? |
|-----------|----------------|-----------------|---------------------|
| **1. show_manual_section** | documents, document_sections | Unknown | - |
| **2. create_work_order_from_fault** | faults, work_orders, equipment, audit_log | NO | - |
| **3. add_note_to_work_order** | work_orders, work_order_notes | NO | - |
| **4. add_part_to_work_order** | work_orders, parts, work_order_parts | NO | - |
| **5. mark_work_order_complete** | work_orders, parts, part_usage, audit_log | NO | - |
| **6. check_stock_level** | parts (+ usage stats) | NO | last_counted_at, last_counted_by |
| **7. log_part_usage** | parts, part_usage, audit_log | NO | - |
| **8. add_to_handover** | handover | NO | - |

---

## Decision: New Tables vs New Columns

### ❌ My Original Approach (Over-engineered)

I proposed 12 new tables in `02_p0_actions_tables.sql`:
- equipment
- faults
- work_orders
- work_order_notes
- parts
- work_order_parts
- part_usage
- documents
- document_sections
- handover
- attachments
- audit_log

### ✅ Better Approach (User's Recommendation)

**Check what ALREADY exists, then:**
1. Add new COLUMNS to existing tables where possible
2. Only create NEW tables where truly justified
3. Avoid duplication

---

## Revised Database Strategy

### Option A: Tables Already Exist Elsewhere

**Hypothesis:** These tables exist but in different migrations or weren't included in the migration files I read.

**Action Required:**
1. Query actual Supabase database to see what exists
2. Use `\dt` in psql or Supabase dashboard
3. Check for naming patterns: `pms_*` prefix vs plain names

### Option B: Minimal New Tables for MVP

**If tables DON'T exist, create ONLY what's essential:**

#### MUST HAVE (Core P0 Actions):

1. **work_orders** - NEW TABLE (justified)
   ```sql
   -- Core work order tracking
   id, yacht_id, number, title, description, equipment_id, fault_id,
   location, priority, status, assigned_to, created_by, created_at,
   completed_at, completed_by, completion_notes
   ```
   **Why new table:** Central entity for 5 P0 actions. No existing equivalent.

2. **audit_log** - NEW TABLE (justified)
   ```sql
   -- ALL mutations must be audited (non-negotiable for MVP)
   id, yacht_id, action, entity_type, entity_id, user_id,
   old_values, new_values, signature, created_at
   ```
   **Why new table:** Required for accountability. Every MUTATE action logs here.

3. **handover** - NEW TABLE (justified)
   ```sql
   -- P0 Action #8: add_to_handover
   id, yacht_id, entity_type, entity_id, summary_text,
   category, priority, added_by, added_at
   ```
   **Why new table:** New feature, no existing equivalent.

#### MAYBE EXIST (Check First):

4. **equipment** - CHECK IF EXISTS
   - Referenced by multiple handlers
   - If exists: no changes needed
   - If not: add minimal version

5. **faults** - CHECK IF EXISTS
   - Referenced by fault_handlers.py
   - If exists: no changes needed
   - If not: add minimal version

6. **parts** - CHECK IF EXISTS (may be `inventory` or `pms_parts`)
   - Referenced by inventory_handlers.py
   - If exists: ADD COLUMNS:
     - `last_counted_at TIMESTAMPTZ`
     - `last_counted_by UUID REFERENCES auth.users(id)`
   - These columns needed for P0 Action #6: check_stock_level

7. **documents** - CHECK IF EXISTS
   - Referenced by equipment_handlers.py as `document_chunks`
   - May already exist for RAG system

#### NEW JUNCTION/LOG TABLES:

8. **work_order_notes** - NEW TABLE (justified)
   ```sql
   -- P0 Action #3: add_note_to_work_order
   id, work_order_id, note_text, note_type, created_by, created_at
   ```
   **Why new table:** Simple log of notes. Could alternatively be:
   - **Option A:** Separate table (cleaner queries)
   - **Option B:** JSONB array on work_orders table (simpler schema)

   **Decision:** Keep separate table for queryability.

9. **work_order_parts** - NEW TABLE (justified)
   ```sql
   -- P0 Action #4: add_part_to_work_order (shopping list)
   id, work_order_id, part_id, quantity, notes, added_by, added_at
   ```
   **Why new table:** Junction table. Standard M:M pattern.

10. **part_usage** - NEW TABLE (justified)
    ```sql
    -- P0 Action #7: log_part_usage (inventory deduction audit)
    id, yacht_id, part_id, work_order_id, equipment_id,
    quantity, usage_reason, notes, used_by, used_at
    ```
    **Why new table:** Event log. Each row = inventory deduction event.
    **Alternative:** Could be in audit_log, but separate table is clearer.

#### NOT NEEDED FOR MVP:

❌ **document_sections** - Defer to later
❌ **attachments** - May already exist
❌ **sensor_readings** - Already exists for predictive
❌ **maintenance_templates** - Already exists
❌ **graph_edges** - Already exists for RAG

---

## Recommended Approach

### Step 1: Audit Existing Database

```sql
-- Run this query on Supabase:
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

### Step 2: Create ONLY Missing MVP Tables

**Absolute minimum for MVP:**
1. ✅ work_orders
2. ✅ work_order_notes
3. ✅ work_order_parts
4. ✅ part_usage
5. ✅ handover
6. ✅ audit_log

**Conditional (if don't exist):**
7. equipment (minimal: id, yacht_id, name, location, status)
8. faults (minimal: id, yacht_id, equipment_id, fault_code, title, severity, detected_at, resolved_at)
9. parts (minimal: id, yacht_id, name, part_number, quantity_on_hand, minimum_quantity, location)

### Step 3: Add Columns to Existing Tables (if tables exist)

If `parts` table exists:
```sql
ALTER TABLE public.parts
ADD COLUMN IF NOT EXISTS last_counted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_counted_by UUID REFERENCES auth.users(id);
```

---

## New Columns vs New Tables Decision Matrix

| Entity | New Table? | Justification |
|--------|-----------|---------------|
| **work_orders** | ✅ YES | Core entity, no alternative |
| **work_order_notes** | ✅ YES | Better than JSONB array for queries |
| **work_order_parts** | ✅ YES | Standard M:M junction table |
| **part_usage** | ✅ YES | Event log pattern, audit requirement |
| **handover** | ✅ YES | New feature, polymorphic references |
| **audit_log** | ✅ YES | Non-negotiable for accountability |
| **equipment** | ❓ MAYBE | Check if exists first |
| **faults** | ❓ MAYBE | Check if exists first |
| **parts** | ❓ MAYBE | Check if exists, add columns if so |
| **documents** | ❌ NO | Likely exists for RAG |
| **attachments** | ❌ NO | Likely exists |

---

## Why NOT Behavioral Tracking?

**User is correct - NOT NEEDED FOR MVP:**

❌ **Removed from design:**
- `situation_state` table
- `situation_evidence` table
- `confidence_scores` table
- `nudge_history` table
- `user_behavior_log` table

**Why removed:**
> "Behavioral is not needed for MVP, auditing, actioning etc. will be required"

✅ **What IS needed:**
- `audit_log` - Who did what, when (accountability)
- Action execution tracking (in audit_log)
- Signature capture (in audit_log.signature JSONB)

The situation state is purely **frontend UI state** (search_mode vs entity_view). No database tracking needed.

---

## Revised Migration Plan

### 02_p0_actions_tables.sql (MINIMAL)

```sql
-- Only create tables that DON'T exist
-- Check first with: SELECT * FROM information_schema.tables WHERE table_name = 'work_orders';

-- 1. Work Orders (CORE - NEW)
CREATE TABLE IF NOT EXISTS public.work_orders (...);

-- 2. Work Order Notes (JUNCTION - NEW)
CREATE TABLE IF NOT EXISTS public.work_order_notes (...);

-- 3. Work Order Parts (JUNCTION - NEW)
CREATE TABLE IF NOT EXISTS public.work_order_parts (...);

-- 4. Part Usage Log (EVENT LOG - NEW)
CREATE TABLE IF NOT EXISTS public.part_usage (...);

-- 5. Handover (NEW FEATURE - NEW)
CREATE TABLE IF NOT EXISTS public.handover (...);

-- 6. Audit Log (ACCOUNTABILITY - NEW)
CREATE TABLE IF NOT EXISTS public.audit_log (...);

-- 7-9. ONLY if they don't exist:
CREATE TABLE IF NOT EXISTS public.equipment (...);
CREATE TABLE IF NOT EXISTS public.faults (...);
CREATE TABLE IF NOT EXISTS public.parts (...);

-- Add columns to existing parts table (if it exists):
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parts') THEN
        ALTER TABLE public.parts
        ADD COLUMN IF NOT EXISTS last_counted_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS last_counted_by UUID REFERENCES auth.users(id);
    END IF;
END $$;
```

---

## Summary: What Changed

| Original Plan | Revised Plan | Reason |
|--------------|--------------|--------|
| 12 new tables | 6-9 new tables | Only create what's essential |
| Assumed nothing exists | Check first, add columns if possible | Leverage existing schema |
| Created behavioral tracking tables | ❌ Removed | Not needed for MVP |
| Created document_sections | ❌ Deferred | Not critical for MVP |
| Created attachments | ❌ Skip | Likely exists |

**Result:** Leaner, focused schema that supports P0 actions without over-engineering.

---

## Next Action Required

**Before implementing migration:**

```bash
# Connect to Supabase and run:
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN (
    'equipment', 'faults', 'work_orders', 'parts',
    'documents', 'attachments', 'audit_log'
)
ORDER BY table_name, ordinal_position;
```

**Then decide:**
- Which tables already exist → Add columns only
- Which tables missing → Create minimal version
- Remove any over-engineered additions

---

**END OF DATABASE REQUIREMENTS ANALYSIS**
