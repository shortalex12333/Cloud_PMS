# Work Order Lens v2 - PHASE 7: RLS Security Matrix

**Status**: COMPLETE
**Source**: Production Database Snapshot (2026-01-24)
**Created**: 2026-01-24

---

## 7.1 Role Hierarchy

### Tier 1: HoD (Heads of Department)
- Captain
- Chief Officer
- Chief Engineer
- ETO (Electro-Technical Officer)
- Chief Steward / Purser

### Tier 2: Senior Crew
- 2nd Officer
- 2nd Engineer
- Bosun
- Head Chef
- Head Housekeeper

### Tier 3: Junior Crew
- Deckhand
- Steward/Stewardess
- Junior Engineer
- Crew Chef

---

## 7.2 Production RLS Policies

### pms_work_orders (Primary Table)

**RLS**: ✅ ENABLED
**Pattern**: CANONICAL (`get_user_yacht_id()`)

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| Users can view work orders | SELECT | public | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| Engineers can create work orders | INSERT | public | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Engineers can update work orders | UPDATE | public | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Managers can delete work orders | DELETE | public | `yacht_id = get_user_yacht_id() AND is_manager()` | ✅ CANONICAL + ROLE |
| Service role full access | ALL | service_role | `true` | ✅ SERVICE_ROLE |

**Roles with Create/Update**: chief_engineer, eto, deck, interior, manager

---

### pms_work_order_checklist

**RLS**: ✅ ENABLED
**Pattern**: MIXED (functionally secure but inconsistent)

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| yacht_isolation_select | SELECT | authenticated | JWT claims OR auth_users_profiles subquery | ⚠️ MIXED |
| yacht_isolation_insert | INSERT | authenticated | JWT claims OR auth_users_profiles subquery | ⚠️ MIXED |
| yacht_isolation_update | UPDATE | authenticated | JWT claims OR auth_users_profiles subquery | ⚠️ MIXED |
| yacht_isolation_delete | DELETE | authenticated | JWT claims OR auth_users_profiles subquery | ⚠️ MIXED |
| users_view | SELECT | authenticated | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| users_insert | INSERT | authenticated | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| users_update | UPDATE | authenticated | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| users_delete | DELETE | authenticated | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| service_role_bypass | ALL | service_role | `true` | ✅ SERVICE_ROLE |

**Note**: Has duplicate policies with different patterns. Functionally secure but needs cleanup.

---

### pms_work_order_notes

**RLS**: ✅ ENABLED
**Pattern**: ❌ CROSS-YACHT LEAKAGE

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| Authenticated users can view notes | SELECT | authenticated | `USING (true)` | ❌ **SECURITY HOLE** |
| Service role full access | ALL | service_role | `true` | ✅ SERVICE_ROLE |
| pms_work_order_notes_yacht_isolation | ALL | public | Uses `app.current_yacht_id` setting | ⚠️ NON-CANONICAL |

**BLOCKER B1**: The `USING (true)` policy means ANY authenticated user can read ALL notes from ALL yachts.

---

### pms_work_order_parts

**RLS**: ✅ ENABLED
**Pattern**: ❌ CROSS-YACHT LEAKAGE (policy conflict)

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| Authenticated users can view parts | SELECT | authenticated | `USING (true)` | ❌ **SECURITY HOLE** |
| Engineers can manage work order parts | ALL | public | Via join to pms_work_orders | ✅ SECURE |
| Users can view work order parts | SELECT | public | Via join to pms_work_orders | ✅ SECURE |
| Service role full access | ALL | service_role | `true` | ✅ SERVICE_ROLE |

**BLOCKER B2**: The `USING (true)` policy bypasses the secure join-based policies. PostgreSQL RLS uses OR semantics for SELECT - if ANY policy passes, access is granted.

---

### pms_work_order_history

**RLS**: ✅ ENABLED
**Pattern**: CANONICAL (`get_user_yacht_id()`)

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| Users can view work order history | SELECT | public | `yacht_id = get_user_yacht_id()` | ✅ CANONICAL |
| Engineers can add history | INSERT | public | `yacht_id = get_user_yacht_id() AND get_user_role() IN [...]` | ✅ CANONICAL + ROLE |
| Service role full access | ALL | service_role | `true` | ✅ SERVICE_ROLE |

**Roles with INSERT**: chief_engineer, eto, deck, interior

---

### pms_part_usage

**RLS**: ✅ ENABLED
**Pattern**: ❌ CROSS-YACHT LEAKAGE

| Policy | Operation | Roles | Condition | Security |
|--------|-----------|-------|-----------|----------|
| Authenticated users can view usage | SELECT | authenticated | `USING (true)` | ❌ **SECURITY HOLE** |
| Service role full access | ALL | service_role | `true` | ✅ SERVICE_ROLE |
| pms_part_usage_yacht_isolation | ALL | public | Uses `app.current_yacht_id` setting | ⚠️ NON-CANONICAL |

**BLOCKER B3**: The `USING (true)` policy means ANY authenticated user can read ALL part usage from ALL yachts.

---

## 7.3 Role × Action Matrix

### Current State (Production)

| Role | View WO | Create WO | Update WO | Complete WO | Reassign WO | Archive WO |
|------|---------|-----------|-----------|-------------|-------------|------------|
| Captain | ✅ | ❓ | ✅ | ✅ | ✅ | ✅ |
| Chief Engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ETO | ✅ | ✅ | ✅ | ✅ | ❓ | ❓ |
| Chief Steward | ✅ | ❓ | ❓ | ❓ | ❓ | ❓ |
| 2nd Engineer | ✅ | ❓ | ✅ | ✅ | ❌ | ❌ |
| Deckhand | ✅ | ❓ | ❓ | ❓ | ❌ | ❌ |

**Legend**: ✅ = Allowed, ❌ = Denied, ❓ = Unclear from current policies

### Target State (Recommended)

| Role | View WO | Create WO | Update WO | Complete WO | Reassign | Archive |
|------|---------|-----------|-----------|-------------|----------|---------|
| Captain | ✅ All | ✅ | ✅ All | ✅ All | ✅+Sign | ✅+Sign |
| Chief Engineer | ✅ All | ✅ | ✅ Dept | ✅ Dept | ✅+Sign | ✅+Sign |
| Chief Steward | ✅ All | ✅ | ✅ Dept | ✅ Dept | ✅+Sign | ✅+Sign |
| ETO | ✅ All | ✅ | ✅ Dept | ✅ Dept | ❌ | ❌ |
| 2nd Engineer | ✅ All | ✅ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| Bosun | ✅ All | ✅ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| Deckhand | ✅ All | ❌ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| Steward | ✅ All | ❌ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |

---

## 7.4 Security Holes Summary

| Table | Issue | Impact | Severity |
|-------|-------|--------|----------|
| pms_work_order_notes | `USING (true)` SELECT | Any user sees all yachts' notes | CRITICAL |
| pms_work_order_parts | `USING (true)` SELECT | Any user sees all yachts' part assignments | CRITICAL |
| pms_part_usage | `USING (true)` SELECT | Any user sees all yachts' part usage | CRITICAL |

### Attack Scenario

1. User A is crew on Yacht A
2. User A authenticates to Supabase
3. User A queries `pms_work_order_notes`
4. Due to `USING (true)`, User A sees notes from Yacht B, C, D...
5. Sensitive maintenance information (faults, repairs) exposed

---

## 7.5 Action × RLS Cross-Reference

| Action | Table | Policy Used | Enforced? |
|--------|-------|-------------|-----------|
| View WO | pms_work_orders | Users can view... | ✅ Yacht isolated |
| Create WO | pms_work_orders | Engineers can create... | ✅ Yacht + role |
| Update WO | pms_work_orders | Engineers can update... | ✅ Yacht + role |
| Complete WO | pms_work_orders | Engineers can update... | ✅ Yacht + role |
| Complete WO | pms_work_order_history | Engineers can add... | ✅ Yacht + role |
| Complete WO | pms_part_usage | Authenticated... (true) | ❌ **NO ISOLATION** |
| Add Note | pms_work_order_notes | Authenticated... (true) | ❌ **NO ISOLATION** |
| Reassign WO | pms_work_orders | Engineers can update... | ✅ Yacht + role |
| Archive WO | pms_work_orders | Managers can delete... | ✅ Yacht + role |

---

## 7.6 Required Migrations

### Priority 1: Critical Security

**B1**: Fix pms_work_order_notes
```sql
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;

CREATE POLICY "crew_select_work_order_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
            AND wo.deleted_at IS NULL
        )
    );
```

**B2**: Fix pms_work_order_parts
```sql
DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

-- Keep "Users can view work order parts" policy (already secure)
```

**B3**: Fix pms_part_usage
```sql
DROP POLICY IF EXISTS "Authenticated users can view usage" ON pms_part_usage;

CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());
```

### Priority 2: Cleanup

Consolidate pms_work_order_checklist policies to use only canonical pattern.

---

## 7.7 Storage RLS (If Applicable)

### Bucket: work-order-attachments

| Operation | Condition | Status |
|-----------|-----------|--------|
| Read | yacht_id in path | VERIFY |
| Write | authenticated + yacht_id | VERIFY |
| Delete | HoD role | VERIFY |

**Note**: Storage RLS is configured in Supabase dashboard, not migrations.

---

## PHASE 7 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 7.1 Role hierarchy documented | ✅ |
| 7.2 Production policies extracted | ✅ |
| 7.3 Role × Action matrix | ✅ |
| 7.4 Security holes identified | ✅ |
| 7.5 Action × RLS cross-reference | ✅ |
| 7.6 Required migrations documented | ✅ |
| All `USING (true)` policies flagged | ✅ |

**Proceeding to Phase 8: Gaps & Migrations**
