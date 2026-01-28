# Work Order Lens - Comprehensive Review

**Reviewer**: Previous Session Claude (gold standard author)
**Date**: 2026-01-24
**Status**: DETAILED ANALYSIS COMPLETE

---

# EXECUTIVE SUMMARY

| Category | Score | Critical Issues |
|----------|-------|-----------------|
| **DB Truth Accuracy** | 6/10 | 4 critical schema errors |
| **RLS Analysis** | 5/10 | Wrong policy extraction, missing deployed policies |
| **Scope & Doctrine** | 9/10 | Excellent, minor wording |
| **Scenarios** | 9/10 | Strong, complete coverage |
| **SQL Correctness** | 7/10 | Uses non-existent columns |
| **Blocker Identification** | 7/10 | Some wrong, some missing |
| **Overall** | **7/10** | Needs revision before production |

---

# SECTION 1: DATABASE TRUTH ANALYSIS

## 1.1 Primary Table: pms_work_orders

### Verified Against: `/Volumes/Backup/CELESTE/database_schema.txt`

| Check | Agent Says | Actual DB | Status |
|-------|------------|-----------|--------|
| Column count | 29 | 29 | ✅ CORRECT |
| yacht_id nullable | NO | NO (blank = NOT NULL) | ✅ CORRECT |
| created_by nullable | NO | NO | ✅ CORRECT |
| status type | enum | public.work_order_status | ✅ CORRECT |
| type type | enum | public.work_order_type | ✅ CORRECT |
| priority type | enum | public.work_order_priority | ✅ CORRECT |

**PASS** - pms_work_orders schema correctly extracted.

---

## 1.2 Secondary Table: pms_work_order_notes

### CRITICAL ERROR FOUND

**Agent documented** (Phase 2, lines 103-115):
```
| Column | Type | Nullable | Notes |
| id | uuid | NO | PK |
| work_order_id | uuid | NO | FK |
| note_text | text | NO | |
| note_type | text | NO | general/progress/issue/resolution |
| metadata | jsonb | YES | |
| created_at | timestamptz | NO | |
| created_by | uuid | NO | |
**Total: 7 columns**
```

**Actual DB** (from database_schema.txt lines 2161-2169):
```
Table: pms_work_order_notes
  created_at       timestamp with time zone  nullable:
  created_by       uuid                      nullable:
  id               uuid                      nullable:
  metadata         jsonb                     nullable: YES
  note_text        text                      nullable:
  note_type        text                      nullable:
  work_order_id    uuid                      nullable:
**Total: 7 columns**
```

**ISSUE**: Agent documented correctly here, BUT in Phase 7 line 87-88, agent claims policy references `public.work_orders` (wrong table). This is WRONG.

**Actual deployed RLS** (from migration `20260122_000_deploy_missing_p0_tables.sql`):
```sql
CREATE POLICY "Service role full access"
    ON public.pms_work_order_notes FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated users can view notes"
    ON public.pms_work_order_notes FOR SELECT
    TO authenticated
    USING (true);
```

**BLOCKER CORRECTION NEEDED**:
- Agent's B5 blocker ("pms_work_order_notes references wrong table") is **INCORRECT**
- The ACTUAL issue is: **No yacht isolation at all** - any authenticated user can view any yacht's notes
- This is a REAL security gap but different from what agent documented

---

## 1.3 Secondary Table: pms_work_order_parts

### CRITICAL ERROR FOUND

**Agent documented** (Phase 2, lines 119-133):
- Shows `yacht_id` column as if it exists
- Shows 9 columns

**Actual DB** (from database_schema.txt lines 2171-2181):
```
Table: pms_work_order_parts
  created_at     timestamp with time zone  nullable: YES
  deleted_at     timestamp with time zone  nullable: YES
  deleted_by     uuid                      nullable: YES
  id             uuid                      nullable:
  notes          text                      nullable: YES
  part_id        uuid                      nullable:
  quantity       integer                   nullable: YES
  updated_at     timestamp with time zone  nullable: YES
  work_order_id  uuid                      nullable:
**Total: 9 columns**
```

**ISSUE**: Agent added `yacht_id` to the schema documentation but **this column does not exist**.

**Impact on Phase 7 RLS**:
- Agent's proposed RLS uses `yacht_id = public.get_user_yacht_id()` which would FAIL
- Must use subquery through pms_work_orders FK instead

---

## 1.4 Secondary Table: pms_work_order_history

**Agent documented** (Phase 2, lines 137-156): 14 columns including `yacht_id`

**Actual DB** (from database_schema.txt lines 2144-2159): 14 columns including `yacht_id`

**PASS** - Correctly documented. This table DOES have yacht_id (denormalized).

---

## 1.5 Missing Table: pms_part_usage

**Agent mentions** in Phase 4 (line 278) that Complete WO writes to `pms_part_usage`

**Issue**: This table exists in DB but was NOT documented in Phase 2 secondary tables.

**Actual DB** (from database_schema.txt lines 1768-1780):
```
Table: pms_part_usage
  equipment_id    uuid                      nullable: YES
  id              uuid                      nullable:
  metadata        jsonb                     nullable: YES
  notes           text                      nullable: YES
  part_id         uuid                      nullable:
  quantity        integer                   nullable:
  usage_reason    text                      nullable:
  used_at         timestamp with time zone  nullable:
  used_by         uuid                      nullable:
  work_order_id   uuid                      nullable: YES
  yacht_id        uuid                      nullable:
**Total: 11 columns**
```

**ACTION REQUIRED**: Add pms_part_usage to Phase 2 secondary tables documentation.

---

## 1.6 Field Classification Errors

**Phase 2, line 60-61**:
```
| **REQUIRED** | yacht_id, title, type, priority, status, created_by |
```

**WRONG**: `yacht_id`, `status`, and `created_by` are **BACKEND_AUTO**, not REQUIRED.
- `yacht_id` → comes from `public.get_user_yacht_id()`
- `status` → defaults to 'open' or 'draft'
- `created_by` → set from `auth.uid()`

**CORRECT Classification**:
```
| **REQUIRED** | title, type, priority |
| **BACKEND_AUTO** | id, yacht_id, wo_number, status, created_by, created_at, updated_at |
```

---

# SECTION 2: RLS POLICY ANALYSIS

## 2.1 pms_work_orders RLS

**Agent documented** (Phase 7 lines 78-81):
```sql
| "Users can view their yacht work orders" | SELECT | yacht_id IN (SELECT yacht_id FROM public.user_profiles...) | DEPLOYED |
| "Users can manage their yacht work orders" | ALL | Same | DEPLOYED |
```

**Verified in migration** `20260116_000_create_pms_core_tables.sql` lines 152-162:
```sql
CREATE POLICY "Users can view their yacht work orders"
    ON public.pms_work_orders FOR SELECT
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can manage their yacht work orders"
    ON public.pms_work_orders FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()
    ));
```

**PASS** - Agent correctly identified deployed RLS and legacy pattern blocker.

---

## 2.2 pms_work_order_notes RLS

**Agent documented** (Phase 7 lines 85-88):
> References `public.work_orders` (old table), NOT `public.pms_work_orders`

**WRONG** - The actual deployed policies from `20260122_000_deploy_missing_p0_tables.sql`:
```sql
CREATE POLICY "Service role full access"
    ON public.pms_work_order_notes FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Authenticated users can view notes"
    ON public.pms_work_order_notes FOR SELECT
    TO authenticated USING (true);
```

**REAL ISSUE**: No yacht isolation - any authenticated user can read any yacht's notes!

**Corrected Blocker**:
- B5 should be: "pms_work_order_notes has no yacht isolation - authenticated users can view ALL yachts' notes"
- This is a SECURITY HOLE, not a broken reference

---

## 2.3 pms_work_order_parts RLS

**Agent documented** (Phase 7 lines 103-105):
> Not found | - | - | **NO RLS**

**WRONG** - The actual deployed policies from `20260122_000_deploy_missing_p0_tables.sql`:
```sql
ALTER TABLE public.pms_work_order_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access"
    ON public.pms_work_order_parts FOR ALL
    TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Authenticated users can view parts"
    ON public.pms_work_order_parts FOR SELECT
    TO authenticated USING (true);
```

**REAL ISSUE**: Same as notes - no yacht isolation!

---

## 2.4 pms_work_order_history RLS

**Agent documented** (Phase 7 lines 107-111):
> Not found | - | - | **NO RLS**

**Likely CORRECT** - I did not find any RLS policies for this table in migrations.

---

## 2.5 RLS Analysis Summary

| Table | Agent Said | Reality | Error |
|-------|------------|---------|-------|
| pms_work_orders | Legacy pattern blocker | Correct | None |
| pms_work_order_notes | Wrong table reference blocker | Has policies but no yacht isolation | WRONG BLOCKER |
| pms_work_order_parts | No RLS | Has RLS but no yacht isolation | WRONG |
| pms_work_order_history | No RLS | Correct | None |

---

# SECTION 3: FUNCTION VERIFICATION

## 3.1 Verified Functions

| Function | Location in Migrations | Status |
|----------|------------------------|--------|
| `public.get_user_yacht_id()` | `00000000000004_02_p0_actions_tables_REVISED.sql:489` | ✅ DEPLOYED |
| `public.generate_wo_number(p_yacht_id)` | `00000000000004_02_p0_actions_tables_REVISED.sql:391` | ✅ DEPLOYED |
| `public.update_updated_at()` | `00000000000004_02_p0_actions_tables_REVISED.sql:615` | ✅ DEPLOYED |
| `public.deduct_part_inventory(...)` | `00000000000010_04_trust_accountability_tables.sql:249` | ✅ DEPLOYED |
| `public.get_user_role(p_user_id, p_yacht_id)` | `00000000000011_05_rename_auth_tables.sql:161` | ✅ DEPLOYED |
| `public.is_hod(p_user_id, p_yacht_id)` | `00000000000011_05_rename_auth_tables.sql:205` | ✅ DEPLOYED |

## 3.2 NOT Deployed Functions

| Function | Location | Status |
|----------|----------|--------|
| `cascade_wo_status_to_fault()` | `CUMULATIVE_SCHEMA_MIGRATIONS.sql:334` | ❌ NOT DEPLOYED |
| `user_has_role(TEXT[])` | `CUMULATIVE_SCHEMA_MIGRATIONS.sql:552` | ❌ NOT DEPLOYED |

**Note**: Agent correctly identified these as blockers in Phase 4 (B3) and Phase 8 (B8).

## 3.3 Alternative to user_has_role()

The function `public.is_hod()` EXISTS and could be used instead of the proposed `user_has_role()`:
```sql
-- EXISTS in 00000000000011_05_rename_auth_tables.sql:205
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
```

**Recommendation**: Phase 7 proposed RLS could use `public.is_hod()` instead of creating new `user_has_role()`.

---

# SECTION 4: SCOPE & DOCTRINE ANALYSIS

## 4.1 Phase 1 Review

**Strengths**:
- Excellent doctrine statement (7 points)
- Clear WO-First articulation
- Forbidden patterns well defined
- No dashboard/button leaks

**Issues**: None found.

**Score**: 9/10

---

## 4.2 Doctrine Violations in Later Phases

| Check | Phase | Status |
|-------|-------|--------|
| No "dashboard" word | All | ✅ PASS |
| No ambient buttons | 5 | ✅ PASS |
| Query-first maintained | 5 | ✅ PASS |
| Actions only after focus | 4, 5 | ✅ PASS |
| Signature invariant respected | 4, 6 | ✅ PASS |

---

# SECTION 5: SCENARIO ANALYSIS

## 5.1 Scenario Coverage

| Scenario | Traditional | Celeste | Reduction | Quality |
|----------|-------------|---------|-----------|---------|
| 1. Basic Lookup | 7 | 3 | 57% | ✅ Good |
| 2. My Work Orders | 7 | 4 | 43% | ✅ Good |
| 3. Create from Fault | 9 | 5 | 44% | ✅ Good |
| 4. Complete WO | 9 | 5 | 44% | ✅ Good |
| 5. WOs for Equipment | 7 | 4 | 43% | ✅ Good |
| 6. Add Note | 8 | 4 | 50% | ⚠️ Minor issue |
| 7. Reassign WO | 11 | 5 | 55% | ✅ Good |
| 8. Overdue WOs | 7 | 3 | 57% | ✅ Good |
| 9. Fault to WO | 7 | 3 | 57% | ✅ Good |
| 10. Archive WO | 10 | 6 | 40% | ✅ Good |

## 5.2 Scenario 6 Issue

**Phase 5, lines 385-388**:
```sql
INSERT INTO pms_work_order_notes
(work_order_id, note_text, note_type, created_by)
VALUES ([wo_id], 'cleaned and inspected winch...', 'progress', auth.uid());
```

**Issue**: Missing `created_at` column - should include `NOW()` or rely on DEFAULT.

**Verdict**: Minor - DEFAULT handles this.

---

# SECTION 6: SQL & APPLICATION ANALYSIS

## 6.1 Canonical Patterns

| Pattern | Usage in Phase 6 | Status |
|---------|------------------|--------|
| `public.get_user_yacht_id()` | All queries | ✅ CORRECT |
| `'{}'::jsonb` for signature | All audit inserts | ✅ CORRECT |
| entity_type from canonical list | 'work_order' | ✅ CORRECT |

## 6.2 SQL Errors

### Error 1: pms_work_order_notes yacht_id

**Phase 6, line 385-388** and **Phase 5**:
SQL assumes yacht isolation via the table, but the table doesn't enforce yacht isolation via column or RLS.

### Error 2: RLS Policy References Non-Existent Column

**Phase 7, lines 163-172** proposed policy:
```sql
CREATE POLICY "crew_select_work_order_parts" ON pms_work_order_parts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
        AND deleted_at IS NULL
    );
```

**Issue**: This is CORRECT approach (subquery through FK) but agent earlier claimed `pms_work_order_parts` has `yacht_id` column which is wrong.

---

# SECTION 7: BLOCKER ANALYSIS

## 7.1 Current Blockers (Agent's List)

| ID | Description | Accurate? | Correction |
|----|-------------|-----------|------------|
| B1 | Legacy RLS pattern on pms_work_orders | ✅ YES | - |
| B2 | Enum values undocumented | ⚠️ PARTIAL | Can verify from CHECK constraints in migrations |
| B3 | user_has_role() not deployed | ✅ YES | Could use existing `public.is_hod()` |
| B4 | No role-based RLS | ✅ YES | - |
| B5 | pms_work_order_notes wrong table ref | ❌ WRONG | Should be "no yacht isolation" |
| B6 | pms_work_order_parts no RLS | ❌ WRONG | Has RLS but no yacht isolation |
| B7 | pms_work_order_history no RLS | ✅ YES | - |
| B8 | cascade trigger not deployed | ✅ YES | - |

## 7.2 Missing Blockers

| ID | Description | Impact |
|----|-------------|--------|
| **B9** | pms_part_usage not documented in Phase 2 | Complete WO action references undocumented table |
| **B10** | pms_work_order_notes allows cross-yacht reads | SECURITY HOLE - any authenticated user can read any yacht's notes |
| **B11** | pms_work_order_parts allows cross-yacht reads | SECURITY HOLE |

---

# SECTION 8: REQUIRED CORRECTIONS

## 8.1 HIGH PRIORITY (Must Fix Before Production)

### 1. Fix pms_work_order_notes RLS understanding
- **Current**: Agent says policy references wrong table
- **Reality**: Policy exists but has NO yacht isolation
- **Action**: Update Phase 7 with correct deployed policies

### 2. Fix pms_work_order_parts RLS understanding
- **Current**: Agent says "No RLS"
- **Reality**: RLS enabled but no yacht isolation
- **Action**: Update Phase 7 with correct deployed policies

### 3. Add pms_part_usage to Phase 2
- **Current**: Missing from secondary tables
- **Action**: Add 11-column schema documentation

### 4. Fix field classifications
- **Current**: yacht_id, status, created_by listed as REQUIRED
- **Action**: Move to BACKEND_AUTO category

### 5. Remove phantom yacht_id from pms_work_order_parts
- **Current**: Agent shows yacht_id column that doesn't exist
- **Action**: Remove from Phase 2 schema

## 8.2 MEDIUM PRIORITY

### 6. Verify enum values
Run against production:
```sql
SELECT enumlabel FROM pg_enum
WHERE enumtypid = 'public.work_order_status'::regtype;
```

### 7. Consider using existing is_hod() function
Instead of creating new user_has_role(), leverage existing `public.is_hod()`.

### 8. Update B5, B6 blockers with correct descriptions

## 8.3 LOW PRIORITY

### 9. Add created_at to Scenario 6 SQL
### 10. Add RETURNING clauses to UPDATE statements

---

# SECTION 9: ACTIONABLE RECOMMENDATIONS

## For the Agent:

1. **Re-read database_schema.txt lines 2161-2181** for pms_work_order_notes and pms_work_order_parts actual columns

2. **Read migration 20260122_000_deploy_missing_p0_tables.sql** to see actual deployed RLS policies

3. **Add pms_part_usage** (database_schema.txt lines 1768-1780) to Phase 2 secondary tables

4. **Update Phase 7** with correct deployed RLS:
   - pms_work_order_notes: Service role full access + authenticated can view (NO yacht isolation!)
   - pms_work_order_parts: Same

5. **Update blockers** to reflect actual security issues (cross-yacht data access)

## For Production:

1. **Deploy yacht isolation** for pms_work_order_notes and pms_work_order_parts:
```sql
-- pms_work_order_notes needs yacht isolation via WO join
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;
CREATE POLICY "crew_select_work_order_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );
```

2. **Consider using existing is_hod()** instead of creating user_has_role()

---

# FINAL VERDICT

The Work Order Lens documentation is **structurally sound** with excellent scope, doctrine, and scenarios. However, there are **critical DB truth errors** that must be corrected before production use:

1. Wrong RLS policy extraction for 2 tables
2. Missing pms_part_usage table documentation
3. Phantom yacht_id column in pms_work_order_parts
4. Incorrect field classifications

**Recommended Action**: Return to Phase 2 and Phase 7, re-extract from actual database and migrations, then propagate corrections through Phase 8.

**Rating After Corrections**: 9/10

---

**END OF COMPREHENSIVE REVIEW**
