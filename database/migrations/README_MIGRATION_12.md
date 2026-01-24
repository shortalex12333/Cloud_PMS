# Migration 12: Multi-Yacht RLS Fix

**Status:** ⚠️ **READY TO TEST** (DO NOT APPLY TO PRODUCTION YET)

**Priority:** 🔥 **CRITICAL SECURITY FIX**

---

## Problem Being Solved

**Current system assumes one user = one yacht**, which breaks for:
- Shore managers accessing multiple yachts
- Fleet managers
- Support staff
- Anyone who needs multi-yacht access

**Security impact:** Users with roles on multiple yachts can only access the first yacht (determined by `user_profiles.yacht_id`), creating data blind spots and forcing workarounds.

---

## Solution

Replace single-yacht assumption with **role-based multi-yacht access**:

1. ✅ New function: `get_user_yacht_ids() → uuid[]` (array of accessible yachts)
2. ✅ New function: `has_yacht_access(yacht_id) → boolean` (fast RLS check)
3. ✅ Update all RLS policies to use multi-yacht functions
4. ✅ Add `yacht_id` immutability trigger (prevent row transfers)
5. ✅ Add `user_settings.default_yacht_id` for UX (NOT security)
6. ❌ Remove `user_profiles.yacht_id` (AFTER testing and code updates)

---

## Migration Sequence (SAFE)

### Phase 1: Apply Functions (Non-Breaking)
```bash
# Run migration up to STEP 4 (equipment table only)
psql <connection_string> -f 12_fix_multi_yacht_rls.sql
```

This creates:
- `get_user_yacht_ids()`
- `has_yacht_access()`
- `prevent_yacht_id_change()`
- `user_settings` table
- New RLS policies on `equipment` table **ONLY**

**Safe because:** Old function still exists, other tables unchanged.

---

### Phase 2: Test Multi-Yacht Access
```bash
# Run test script
psql <connection_string> -f test_multi_yacht_rls.sql
```

**Manual testing required:**
1. Create test user via Supabase Auth
2. Assign roles on 3 yachts (A, B, C)
3. Query equipment table via Supabase client (with JWT)
4. Verify user sees equipment from A, B, C (NOT D)
5. Test INSERT/UPDATE/DELETE enforcement
6. Test `yacht_id` immutability (should fail)

**Expected results:**
- ✅ User sees equipment from yachts A, B, C
- ✅ User cannot see equipment from yacht D
- ✅ User can INSERT to yacht A
- ✅ User cannot INSERT to yacht D
- ✅ User cannot UPDATE `yacht_id` (immutability enforced)
- ✅ User can UPDATE other fields on accessible equipment

---

### Phase 3: Apply to All Tables (After Testing)
```sql
-- Uncomment STEP 5 in migration file
-- Run migration again
psql <connection_string> -f 12_fix_multi_yacht_rls.sql
```

This applies the same RLS pattern to:
- `faults`
- `parts`
- `work_orders`
- `work_order_notes`
- (Add more tables as needed)

---

### Phase 4: Remove Old Function (After All Policies Updated)
```sql
-- Verify no policies reference old function:
SELECT schemaname, tablename, policyname, definition
FROM pg_policies
WHERE definition LIKE '%get_user_yacht_id()%';

-- If empty, uncomment STEP 6 and run:
DROP FUNCTION IF EXISTS public.get_user_yacht_id();
```

---

### Phase 5: Remove user_profiles.yacht_id (BREAKING CHANGE)

**Prerequisites:**
1. ✅ All RLS policies migrated
2. ✅ All application code updated to use `user_roles` instead
3. ✅ Multi-yacht testing complete
4. ✅ No code references `user_profiles.yacht_id`

```sql
-- Verify no policies reference yacht_id:
SELECT schemaname, tablename, policyname, definition
FROM pg_policies
WHERE definition LIKE '%user_profiles.yacht_id%';

-- If empty, uncomment STEP 7 and run:
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS yacht_id;
```

---

## Rollback Plan

If anything fails:

```sql
-- 1. Drop new functions
DROP FUNCTION IF EXISTS public.get_user_yacht_ids();
DROP FUNCTION IF EXISTS public.has_yacht_access(uuid);
DROP FUNCTION IF EXISTS public.prevent_yacht_id_change();

-- 2. Restore old function (if backed up)
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
  SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- 3. Restore old policies (keep backups!)

-- 4. Drop user_settings table
DROP TABLE IF EXISTS public.user_settings;

-- 5. Remove immutability triggers
DROP TRIGGER IF EXISTS trg_prevent_yacht_id_change ON public.equipment;
-- (repeat for other tables)
```

---

## Tables Updated

### ✅ Completed (Phase 1)
- `equipment` (test table)

### ⏳ Pending (Phase 3)
- `faults`
- `parts`
- `work_orders`
- `work_order_notes`
- `pms_equipment`
- `pms_parts`
- `pms_work_orders`
- `pms_faults`
- (Add more as discovered)

### ❌ Not Affected
- `yachts` (already has correct policy)
- `user_profiles` (own profile access only)
- `user_roles` (multi-yacht by design)
- `api_tokens` (own tokens only)

---

## Performance Impact

**Minimal to none:**

- `has_yacht_access()` is marked `STABLE` (result cached per query)
- Uses indexes: `user_roles(user_id, yacht_id, is_active)`
- Array-based approach faster than repeated joins
- `SET search_path = public` prevents function hijacking

**Monitoring:**
- Watch query performance on `equipment` after Phase 1
- If slow, add composite index: `(yacht_id, <frequently_filtered_column>)`

---

## Code Changes Required

**Before Phase 5 (removing `user_profiles.yacht_id`):**

1. ✅ Update any code reading `user_profiles.yacht_id`
   - Replace with query to `user_roles` for accessible yachts
   - Or use `user_settings.default_yacht_id` for UX defaults

2. ✅ Update frontend context switching
   - Use `user_settings.default_yacht_id` for selected yacht
   - Never trust client-side yacht selection for security

3. ✅ Update APIs that assume single yacht
   - Add `yacht_id` parameter where needed
   - Validate `yacht_id` against `has_yacht_access()`

---

## Testing Checklist

- [ ] Functions created successfully
- [ ] `equipment` table policies applied
- [ ] Test user created with roles on 3 yachts
- [ ] SELECT via API returns only accessible yachts
- [ ] INSERT to accessible yacht succeeds
- [ ] INSERT to inaccessible yacht fails (RLS error)
- [ ] UPDATE `yacht_id` fails (immutability error)
- [ ] UPDATE other fields succeeds
- [ ] DELETE from accessible yacht succeeds
- [ ] DELETE from inaccessible yacht fails
- [ ] Role deactivation immediately revokes access
- [ ] `user_settings.default_yacht_id` can be set/read
- [ ] All tables in Phase 3 updated
- [ ] Old function removed (Phase 4)
- [ ] `user_profiles.yacht_id` removed (Phase 5)

---

## Questions/Issues

**Report to:** GitHub Issues or Slack #engineering

**Contact:** See CLAUDE.md for project context

---

**Last Updated:** 2026-01-22
**Author:** Claude Sonnet 4.5 (following user security requirements)
**Reviewed By:** (pending)
