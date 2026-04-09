# Equipment Lens v2 - PHASE 8: GAPS & MIGRATIONS

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 8 consolidates all identified gaps and defines migration scripts:
- Blockers requiring resolution
- Migration scripts in priority order
- Deployment checklist
- Verification procedures

---

## BLOCKER SUMMARY

### Critical (P0) - Must Fix Before Any Actions Work

| ID | Blocker | Affects | Status |
|----|---------|---------|--------|
| - | None identified | - | Equipment core RLS is deployed |

### High (P1) - Required for Full Functionality

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| B1 | `pms_notes` RLS verification | add_equipment_note | Verify policies deployed |
| B2 | `pms_attachments` RLS verification | attach_file_to_equipment | Verify policies deployed |
| B3 | Storage bucket write policies | File uploads | Verify documents bucket policies |
| B4 | `pms_notifications` table | Notification triggers | New table required |

### Medium (P2) - Important for Production

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| B5 | `is_hod()` helper verification | Update policies | Verify function exists |
| B6 | `is_manager()` helper verification | Delete policies | Verify function exists |

### Low (P3) - Nice to Have

| ID | Blocker | Affects | Resolution |
|----|---------|---------|------------|
| B7 | Performance indexes on notes/attachments | Query speed | Add indexes if needed |

---

## VERIFICATION SCRIPTS

Run these before determining migration needs:

### Check 1: Notes RLS

```sql
-- Check RLS enabled
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_notes';

-- Check policies
SELECT policyname, cmd FROM pg_policies WHERE tablename = 'pms_notes';
```

**Expected**: RLS enabled with SELECT/INSERT/UPDATE/DELETE policies.

### Check 2: Attachments RLS

```sql
-- Check RLS enabled
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_attachments';

-- Check policies
SELECT policyname, cmd FROM pg_policies WHERE tablename = 'pms_attachments';
```

**Expected**: RLS enabled with SELECT/INSERT/UPDATE/DELETE policies.

### Check 3: Storage Bucket Policies

```sql
-- Check storage policies for documents bucket
SELECT policyname, cmd
FROM pg_policies
WHERE schemaname = 'storage'
  AND tablename = 'objects'
ORDER BY policyname;
```

**Expected**: Policies for yacht-scoped SELECT/INSERT/UPDATE/DELETE on documents bucket.

### Check 4: Helper Functions

```sql
-- Check helpers exist
SELECT proname FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'get_user_role', 'is_hod', 'is_manager');
```

**Expected**: All 4 functions present.

### Check 5: Notifications Table

```sql
-- Check if notifications table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'pms_notifications'
);
```

**Expected**: May be false (new table).

---

## MIGRATION SCRIPTS

### Migration 001: Notes RLS (if needed)

**File**: `supabase/migrations/20260127_001_notes_rls.sql`

```sql
-- Enable RLS on pms_notes
ALTER TABLE pms_notes ENABLE ROW LEVEL SECURITY;

-- 1. SELECT: All authenticated users
CREATE POLICY "Users can view yacht notes"
ON pms_notes
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT: All crew can add notes
CREATE POLICY "Crew can add notes"
ON pms_notes
FOR INSERT
TO public
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- 3. UPDATE: Author or HOD
CREATE POLICY "Author or HOD can update notes"
ON pms_notes
FOR UPDATE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND (
        created_by = auth.uid()
        OR public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
);

-- 4. DELETE: Manager only
CREATE POLICY "Manager can delete notes"
ON pms_notes
FOR DELETE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- 5. Service role bypass
CREATE POLICY "Service role full access notes"
ON pms_notes
FOR ALL
TO service_role
USING (true);
```

### Migration 002: Attachments RLS (if needed)

**File**: `supabase/migrations/20260127_002_attachments_rls.sql`

```sql
-- Enable RLS on pms_attachments
ALTER TABLE pms_attachments ENABLE ROW LEVEL SECURITY;

-- 1. SELECT: All authenticated users
CREATE POLICY "Users can view yacht attachments"
ON pms_attachments
FOR SELECT
TO public
USING (yacht_id = public.get_user_yacht_id());

-- 2. INSERT: All crew can upload
CREATE POLICY "Crew can upload attachments"
ON pms_attachments
FOR INSERT
TO public
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- 3. UPDATE: Uploader or HOD
CREATE POLICY "Uploader or HOD can update attachments"
ON pms_attachments
FOR UPDATE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND (
        uploaded_by = auth.uid()
        OR public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
);

-- 4. DELETE: Manager only
CREATE POLICY "Manager can delete attachments"
ON pms_attachments
FOR DELETE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- 5. Service role bypass
CREATE POLICY "Service role full access attachments"
ON pms_attachments
FOR ALL
TO service_role
USING (true);
```

### Migration 003: Storage Write Policies (if needed)

**File**: `supabase/migrations/20260127_003_storage_write_policies.sql`

```sql
-- Equipment file uploads go to documents bucket
-- Path pattern: {yacht_id}/equipment/{equipment_id}/{filename}

-- 1. SELECT: Yacht-scoped read
CREATE POLICY "Yacht users can read documents"
ON storage.objects
FOR SELECT
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- 2. INSERT: All crew can upload to their yacht
CREATE POLICY "Crew can upload to yacht documents"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
);

-- 3. UPDATE: HOD can update
CREATE POLICY "HOD can update yacht documents"
ON storage.objects
FOR UPDATE
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- 4. DELETE: Manager only
CREATE POLICY "Manager can delete yacht documents"
ON storage.objects
FOR DELETE
TO public
USING (
    bucket_id = 'documents'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND public.is_manager()
);
```

### Migration 004: Notifications Table (NEW)

**File**: `supabase/migrations/20260127_004_create_notifications.sql`

```sql
-- Create notifications table for work reminders
CREATE TABLE IF NOT EXISTS pms_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yacht_registry(id),
    user_id UUID NOT NULL,  -- No FK to MASTER auth.users

    -- Classification
    topic TEXT NOT NULL,  -- e.g., 'equipment_critical_failure'
    source TEXT NOT NULL,  -- e.g., 'equipment', 'work_order', 'certificate'
    source_id UUID NOT NULL,  -- FK to source entity

    -- Content
    title TEXT NOT NULL,
    body TEXT,
    level TEXT NOT NULL DEFAULT 'info',  -- info, warning, critical

    -- Call to Action
    cta_action_id TEXT,  -- Action to execute when clicked
    cta_payload JSONB DEFAULT '{}'::jsonb,  -- Pre-filled action payload

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, sent, read, dismissed
    send_after TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_level CHECK (level IN ('info', 'warning', 'critical')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'sent', 'read', 'dismissed'))
);

-- Idempotency constraint: prevent duplicate notifications
CREATE UNIQUE INDEX idx_notifications_idempotency
ON pms_notifications (user_id, source, source_id, topic, date_trunc('day', send_after));

-- Performance indexes
CREATE INDEX idx_notifications_yacht_user ON pms_notifications (yacht_id, user_id);
CREATE INDEX idx_notifications_status ON pms_notifications (status) WHERE status = 'pending';
CREATE INDEX idx_notifications_source ON pms_notifications (source, source_id);

-- Enable RLS
ALTER TABLE pms_notifications ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- 1. SELECT: User can see their own notifications
CREATE POLICY "Users can view their notifications"
ON pms_notifications
FOR SELECT
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
);

-- 2. INSERT: Backend only (service role)
CREATE POLICY "Service role can create notifications"
ON pms_notifications
FOR INSERT
TO service_role
WITH CHECK (true);

-- 3. UPDATE: User can update their own (mark read/dismissed)
CREATE POLICY "Users can update their notifications"
ON pms_notifications
FOR UPDATE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
);

-- 4. DELETE: Manager only
CREATE POLICY "Manager can delete notifications"
ON pms_notifications
FOR DELETE
TO public
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- Updated_at trigger
CREATE TRIGGER update_notifications_updated_at
    BEFORE UPDATE ON pms_notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

### Migration 005: Notification Helper Function

**File**: `supabase/migrations/20260127_005_notification_helpers.sql`

```sql
-- Helper function to create equipment notifications
CREATE OR REPLACE FUNCTION notify_equipment_event(
    p_equipment_id UUID,
    p_topic TEXT,
    p_title TEXT,
    p_body TEXT,
    p_level TEXT DEFAULT 'info',
    p_cta_action_id TEXT DEFAULT NULL,
    p_recipient_roles TEXT[] DEFAULT ARRAY['chief_engineer']
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    _yacht_id UUID;
BEGIN
    _yacht_id := public.get_user_yacht_id();

    INSERT INTO pms_notifications (
        yacht_id, user_id,
        topic, source, source_id,
        title, body, level,
        cta_action_id, cta_payload,
        status, send_after
    )
    SELECT
        _yacht_id,
        aup.id,
        p_topic,
        'equipment',
        p_equipment_id,
        p_title,
        p_body,
        p_level,
        COALESCE(p_cta_action_id, 'focus_equipment'),
        jsonb_build_object('equipment_id', p_equipment_id),
        'pending',
        NOW()
    FROM auth_users_profiles aup
    WHERE aup.yacht_id = _yacht_id
      AND aup.role = ANY(p_recipient_roles)
      AND aup.is_active = true
      AND aup.id != auth.uid();  -- Don't notify self
END;
$$;
```

---

## DEPLOYMENT CHECKLIST

### Pre-Deploy

- [ ] Backup database
- [ ] Run verification scripts
- [ ] Identify which migrations are needed
- [ ] Test migrations on staging

### Deploy Order (only deploy what's needed)

1. [ ] Migration 001 (notes RLS) - if verification shows missing
2. [ ] Migration 002 (attachments RLS) - if verification shows missing
3. [ ] Migration 003 (storage policies) - if verification shows missing
4. [ ] Migration 004 (notifications table) - likely needed (NEW)
5. [ ] Migration 005 (notification helpers) - after 004

### Post-Deploy Verification

```sql
-- 1. Notes RLS
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_notes';
SELECT COUNT(*) FROM pg_policies WHERE tablename = 'pms_notes';

-- 2. Attachments RLS
SELECT relrowsecurity FROM pg_class WHERE relname = 'pms_attachments';
SELECT COUNT(*) FROM pg_policies WHERE tablename = 'pms_attachments';

-- 3. Storage policies
SELECT COUNT(*) FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects';

-- 4. Notifications table
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'pms_notifications');

-- 5. Helper function
SELECT EXISTS (SELECT FROM pg_proc WHERE proname = 'notify_equipment_event');
```

---

## ACCEPTANCE TESTS

### Test Category 1: Role & CRUD

| Test | Role | Action | Expected |
|------|------|--------|----------|
| T1.1 | deckhand | update_equipment_status | 403 |
| T1.2 | engineer | update_equipment_status | 200 |
| T1.3 | deckhand | add_equipment_note | 200 |
| T1.4 | engineer | create_work_order_for_equipment | 200 |
| T1.5 | deckhand | create_work_order_for_equipment | 403 |
| T1.6 | manager | decommission_equipment (signed) | 200 |
| T1.7 | chief_engineer | decommission_equipment | 403 |

### Test Category 2: Isolation & Storage

| Test | Scenario | Expected |
|------|----------|----------|
| T2.1 | Cross-yacht equipment read | 404 |
| T2.2 | Cross-yacht equipment update | 404/403 |
| T2.3 | File upload to correct path | 200 + path verified |
| T2.4 | File upload to wrong yacht path | 403 |

### Test Category 3: Edge Cases

| Test | Scenario | Expected |
|------|----------|----------|
| T3.1 | Invalid status value | 400 |
| T3.2 | Decommission already decommissioned | 409 |
| T3.3 | Status change on decommissioned | 400 |
| T3.4 | Decommission without signature | 400 |
| T3.5 | File too large (>25MB) | 400 |
| T3.6 | Invalid file type | 400 |

### Test Category 4: Audit Invariant

| Test | Scenario | Expected |
|------|----------|----------|
| T4.1 | Non-signed action audit | signature = {} |
| T4.2 | Signed action (decommission) audit | signature = {full JSON} |
| T4.3 | Audit entry has all required fields | Assert each field present |

### Test Category 5: Notifications

| Test | Scenario | Expected |
|------|----------|----------|
| T5.1 | Critical equipment failure | Notification created for chief_engineer |
| T5.2 | Note with requires_ack | Notification created |
| T5.3 | Crew role failure | No notification (not critical) |
| T5.4 | Idempotency | Second trigger doesn't duplicate |

---

## DOCKER TEST LOCATIONS

```
tests/docker/run_equipment_rls_tests.py
```

## STAGING CI LOCATIONS

```
tests/ci/staging_equipment_acceptance.py
.github/workflows/staging-equipment-acceptance.yml
```

---

## SUMMARY

### What's Ready

| Component | Status |
|-----------|--------|
| pms_equipment schema | ✅ Complete |
| pms_equipment RLS | ✅ Deployed |
| pms_equipment_parts_bom RLS | ✅ Deployed |
| Canonical helpers | ✅ Deployed (verify is_hod, is_manager) |

### What Needs Verification

| Component | Action |
|-----------|--------|
| pms_notes RLS | Run verification query |
| pms_attachments RLS | Run verification query |
| Storage bucket policies | Run verification query |

### What's New

| Component | Migration |
|-----------|-----------|
| pms_notifications table | Migration 004 |
| notify_equipment_event() | Migration 005 |

---

## NEXT STEPS

1. **Run verification queries** to determine actual migration needs
2. **Create missing migrations** based on verification results
3. **Proceed to implementation**:
   - Backend handlers (`apps/api/handlers/equipment_handlers.py`)
   - Registry entries (`apps/api/action_router/registry.py`)
   - Dispatcher routing (`apps/api/action_router/dispatchers/internal_dispatcher.py`)
4. **Write tests**:
   - Docker RLS tests
   - Staging acceptance tests
5. **Frontend integration**:
   - `useCelesteSearch.ts` - equipment domain detection
   - `SuggestedActions.tsx` - render equipment actions
   - `ActionModal.tsx` - equipment action forms

---

**END OF PHASE 8**
