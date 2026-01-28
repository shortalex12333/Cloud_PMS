# Work Order Lens - PHASE 7: RLS & Security Matrix

**Status**: COMPLETE
**Created**: 2026-01-24

---

## BLOCKERS CARRIED FORWARD

| ID | Blocker | Impact | Resolution |
|----|---------|--------|------------|
| **B1** | Legacy RLS pattern | All policies use `user_profiles` subquery instead of `public.get_user_yacht_id()` | Migration required |
| **B3** | `user_has_role()` function not deployed | Role-based policies cannot be enforced at DB level | Deploy function |
| **B4** | No role-based RLS policies | All users can do all operations within yacht | Deploy role-based policies |

---

## 7.1 Role Hierarchy (from ranks.md)

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

## 7.2 Role × Action Matrix

### Deployed (Current State)

| Role | View WO | Create WO | Update WO | Complete WO | Reassign WO | Archive WO |
|------|---------|-----------|-----------|-------------|-------------|------------|
| **All Crew** | ✅ Own yacht | ✅ Own yacht | ✅ Own yacht | ✅ Own yacht | ✅ Own yacht | ✅ Own yacht |

**Note**: Current RLS only enforces yacht isolation, NOT role-based access.

### Proposed (Target State)

| Role | View WO | Create WO | Update WO | Complete WO | Reassign WO | Archive WO |
|------|---------|-----------|-----------|-------------|-------------|------------|
| **Captain** | ✅ All | ✅ | ✅ All | ✅ All | ✅ + Sign | ✅ + Sign |
| **Chief Officer** | ✅ All | ✅ | ✅ All | ✅ Dept | ✅ + Sign | ✅ + Sign |
| **Chief Engineer** | ✅ All | ✅ | ✅ Dept | ✅ Dept | ✅ + Sign | ✅ + Sign |
| **Chief Steward** | ✅ All | ✅ | ✅ Dept | ✅ Dept | ✅ + Sign | ✅ + Sign |
| **ETO** | ✅ All | ✅ | ✅ Dept | ✅ Dept | ❌ | ❌ |
| **2nd Engineer** | ✅ All | ✅ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| **Bosun** | ✅ All | ✅ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| **Deckhand** | ✅ All | ❌ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |
| **Steward** | ✅ All | ❌ | ✅ Assigned | ✅ Assigned | ❌ | ❌ |

**Legend**:
- ✅ All = All WOs on yacht
- ✅ Dept = Department WOs only
- ✅ Assigned = Only WOs assigned to them
- ✅ + Sign = Requires signature

---

## 7.3 Deployed RLS Policies

### Table: `pms_work_orders`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| "Users can view their yacht work orders" | SELECT | `yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())` | DEPLOYED |
| "Users can manage their yacht work orders" | ALL | `yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())` | DEPLOYED |

### Table: `pms_work_order_notes`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| "Users can view notes on their yacht's work orders" | SELECT | `EXISTS (SELECT 1 FROM public.work_orders WHERE id = work_order_notes.work_order_id AND yacht_id = public.get_user_yacht_id())` | DEPLOYED |
| "Users can add notes to their yacht's work orders" | INSERT | Same check | DEPLOYED |

**Note**: This references `public.work_orders` (old table), NOT `public.pms_work_orders`.

### Table: `pms_work_order_checklist`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| "yacht_isolation_select" | SELECT | `yacht_id = public.get_user_yacht_id()` | DEPLOYED |
| "yacht_isolation_insert" | INSERT | `yacht_id = public.get_user_yacht_id()` | DEPLOYED |
| "yacht_isolation_update" | UPDATE | `yacht_id = public.get_user_yacht_id()` | DEPLOYED |
| "yacht_isolation_delete" | DELETE | `yacht_id = public.get_user_yacht_id()` | DEPLOYED |

### Table: `pms_work_order_parts`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| Not found | - | - | **NO RLS** |

### Table: `pms_work_order_history`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| Not found | - | - | **NO RLS** |

### Table: `pms_audit_log`

| Policy Name | Cmd | Condition | Status |
|-------------|-----|-----------|--------|
| "Users can view audit log for their yacht" | SELECT | `yacht_id = public.get_user_yacht_id()` | DEPLOYED |
| "Service role can insert audit log entries" | INSERT | `auth.jwt()->>'role' = 'service_role'` | DEPLOYED |

---

## 7.4 Policy Gaps

| Table | Gap | Severity | Migration Required |
|-------|-----|----------|-------------------|
| `pms_work_orders` | No role-based restrictions | HIGH | Yes |
| `pms_work_orders` | No soft-delete filter in SELECT | MEDIUM | Yes |
| `pms_work_orders` | Uses legacy `user_profiles` pattern | HIGH | Yes |
| `pms_work_order_notes` | References wrong table | HIGH | Yes |
| `pms_work_order_parts` | No RLS at all | HIGH | Yes |
| `pms_work_order_history` | No RLS at all | HIGH | Yes |

---

## 7.5 Proposed RLS Policies

### Helper Function Required

```sql
-- MUST DEPLOY FIRST
CREATE OR REPLACE FUNCTION public.user_has_role(required_roles TEXT[])
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth_users_profiles
    WHERE id = auth.uid()
    AND role = ANY(required_roles)
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

### Table: `pms_work_orders`

```sql
-- Drop legacy policies
DROP POLICY IF EXISTS "Users can view their yacht work orders" ON pms_work_orders;
DROP POLICY IF EXISTS "Users can manage their yacht work orders" ON pms_work_orders;

-- SELECT: All crew can view, exclude soft-deleted
CREATE POLICY "crew_select_work_orders" ON pms_work_orders
    FOR SELECT
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
    );

-- INSERT: Engineers+ can create
CREATE POLICY "engineers_insert_work_orders" ON pms_work_orders
    FOR INSERT
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.user_has_role(ARRAY[
            'captain', 'chief_officer', 'chief_engineer', 'eto',
            'chief_steward', 'purser', '2nd_engineer', '2nd_officer',
            'bosun', 'head_chef'
        ])
    );

-- UPDATE: Assigned or HoD can update
CREATE POLICY "crew_update_work_orders" ON pms_work_orders
    FOR UPDATE
    USING (
        yacht_id = public.get_user_yacht_id()
        AND deleted_at IS NULL
        AND (
            assigned_to = auth.uid()
            OR public.user_has_role(ARRAY[
                'captain', 'chief_officer', 'chief_engineer', 'eto',
                'chief_steward', 'purser'
            ])
        )
    )
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
    );

-- Service role bypass
CREATE POLICY "service_role_full_access" ON pms_work_orders
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

### Table: `pms_work_order_parts`

```sql
ALTER TABLE pms_work_order_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_select_wo_parts" ON pms_work_order_parts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
        AND deleted_at IS NULL
    );

CREATE POLICY "engineers_insert_wo_parts" ON pms_work_order_parts
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );
```

### Table: `pms_work_order_history`

```sql
ALTER TABLE pms_work_order_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_select_wo_history" ON pms_work_order_history
    FOR SELECT
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY "system_insert_wo_history" ON pms_work_order_history
    FOR INSERT
    TO service_role
    WITH CHECK (true);
```

---

## 7.6 Storage RLS (Separate from DB RLS)

### Bucket: `work-order-attachments`

| Policy | Operation | Condition | Status |
|--------|-----------|-----------|--------|
| Read | SELECT | `bucket_id = 'work-order-attachments' AND (storage.foldername(name))[1] = yacht_id::text` | **VERIFY** |
| Write | INSERT | Same + authenticated | **VERIFY** |
| Delete | DELETE | Same + HoD role | **VERIFY** |

**Note**: Storage RLS is defined in Supabase dashboard, not in migrations. Verify configuration.

---

## 7.7 Action × RLS Cross-Reference

| Action | Table Written | Policy Name | Enforced? |
|--------|---------------|-------------|-----------|
| Create WO | pms_work_orders | "Users can manage..." (legacy) | ⚠️ Yacht only |
| Update WO | pms_work_orders | "Users can manage..." (legacy) | ⚠️ Yacht only |
| Complete WO | pms_work_orders | "Users can manage..." (legacy) | ⚠️ Yacht only |
| Complete WO | pms_work_order_history | NONE | ❌ NO RLS |
| Complete WO | pms_part_usage | Via function (service role) | ✅ OK |
| Add Note | pms_work_order_notes | Via WO join (old table ref) | ⚠️ BROKEN |
| Reassign WO | pms_work_orders | "Users can manage..." | ⚠️ No role check |
| Archive WO | pms_work_orders | "Users can manage..." | ⚠️ No role check |
| All | pms_audit_log | Service role only | ✅ OK |

---

## 7.8 Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Yacht isolation on all tables | ⚠️ | Legacy pattern on main table |
| Role-based access control | ❌ | Not enforced at DB level |
| Soft-delete filter in SELECT | ❌ | Not present |
| Signature verification | N/A | Application level |
| Service role bypass | ✅ | Present on audit_log |
| Storage bucket isolation | ❓ | Verify in dashboard |

---

## 7.9 Migration Priority

| Priority | Item | Reason |
|----------|------|--------|
| **P1** | Deploy `user_has_role()` function | Prerequisite for role-based RLS |
| **P1** | Fix pms_work_order_notes policy | Currently broken (wrong table ref) |
| **P2** | Add RLS to pms_work_order_parts | No RLS = security hole |
| **P2** | Add RLS to pms_work_order_history | No RLS = security hole |
| **P2** | Replace legacy RLS on pms_work_orders | Standardize on canonical function |
| **P3** | Add role-based policies | Business logic enforcement |
| **P3** | Add soft-delete filter | Data hygiene |

---

## PHASE 7 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 7.1 Role hierarchy documented | ✅ |
| 7.2 Role × Action matrix built | ✅ |
| 7.3 Deployed policies extracted | ✅ |
| 7.4 Policy gaps identified | ✅ |
| 7.5 Proposed policies written | ✅ |
| 7.6 Storage RLS documented | ✅ |
| 7.7 Action × RLS cross-reference | ✅ |
| 7.8 Security checklist completed | ✅ |
| 7.9 Migration priorities defined | ✅ |

**Proceeding to Phase 8: Migration & Gap Report**
