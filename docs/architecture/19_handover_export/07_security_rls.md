# Security & RLS

## Row-Level Security Policies for Handover Export

This document defines the RLS policies enforcing yacht isolation and role-based access.

---

## Core Principle

**Backend authority, yacht isolation, immutable audit.**

Every handover table must:
1. Enforce yacht isolation via RLS
2. Prevent cross-tenant data access
3. Log all mutations to audit trail
4. Restrict sensitive operations by role

---

## RLS Policy Pattern

All handover tables use this standard policy pattern:

```sql
-- Enable RLS
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Service role bypass (backend operations)
ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;

-- Standard yacht isolation policy
CREATE POLICY "{table_name}_yacht_isolation"
ON {table_name}
FOR ALL
TO authenticated
USING (yacht_id = get_user_yacht_id());
```

The `get_user_yacht_id()` function:

```sql
CREATE OR REPLACE FUNCTION get_user_yacht_id()
RETURNS UUID
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_users_profiles
  WHERE id = auth.uid()
$$;
```

---

## Table-Specific Policies

### handovers

```sql
-- READ: Users can see handovers for their yacht
CREATE POLICY "handovers_select_yacht"
ON handovers FOR SELECT
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- INSERT: Users can create handovers for their yacht
CREATE POLICY "handovers_insert_yacht"
ON handovers FOR INSERT
TO authenticated
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Users can update handovers for their yacht
CREATE POLICY "handovers_update_yacht"
ON handovers FOR UPDATE
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only, managers only
CREATE POLICY "handovers_delete_manager"
ON handovers FOR DELETE
TO authenticated
USING (
    yacht_id = get_user_yacht_id()
    AND is_manager()
);
```

---

### handover_items

```sql
-- READ: Yacht isolation
CREATE POLICY "handover_items_select_yacht"
ON handover_items FOR SELECT
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- INSERT: Yacht isolation
CREATE POLICY "handover_items_insert_yacht"
ON handover_items FOR INSERT
TO authenticated
WITH CHECK (yacht_id = get_user_yacht_id());

-- UPDATE: Yacht isolation
CREATE POLICY "handover_items_update_yacht"
ON handover_items FOR UPDATE
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- DELETE: Soft delete only
CREATE POLICY "handover_items_delete_yacht"
ON handover_items FOR DELETE
TO authenticated
USING (yacht_id = get_user_yacht_id());
```

---

### handover_drafts

```sql
-- READ: Yacht isolation
CREATE POLICY "handover_drafts_select_yacht"
ON handover_drafts FOR SELECT
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- INSERT: Service role only (backend generates drafts)
CREATE POLICY "handover_drafts_insert_service"
ON handover_drafts FOR INSERT
TO service_role
WITH CHECK (true);

-- UPDATE: State transitions only via backend
CREATE POLICY "handover_drafts_update_service"
ON handover_drafts FOR UPDATE
TO service_role
USING (true);

-- DELETE: Never (signed drafts are permanent)
-- No delete policy = no deletes allowed
```

---

### handover_draft_sections

```sql
-- READ: Via draft yacht isolation
CREATE POLICY "handover_draft_sections_select"
ON handover_draft_sections FOR SELECT
TO authenticated
USING (
    draft_id IN (
        SELECT id FROM handover_drafts
        WHERE yacht_id = get_user_yacht_id()
    )
);

-- INSERT/UPDATE/DELETE: Service role only
CREATE POLICY "handover_draft_sections_modify_service"
ON handover_draft_sections FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

---

### handover_draft_items

```sql
-- READ: Via draft yacht isolation
CREATE POLICY "handover_draft_items_select"
ON handover_draft_items FOR SELECT
TO authenticated
USING (
    draft_id IN (
        SELECT id FROM handover_drafts
        WHERE yacht_id = get_user_yacht_id()
    )
);

-- INSERT/UPDATE: Service role only
CREATE POLICY "handover_draft_items_modify_service"
ON handover_draft_items FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

---

### handover_draft_edits

```sql
-- READ: Via draft yacht isolation
CREATE POLICY "handover_draft_edits_select"
ON handover_draft_edits FOR SELECT
TO authenticated
USING (
    draft_id IN (
        SELECT id FROM handover_drafts
        WHERE yacht_id = get_user_yacht_id()
    )
);

-- INSERT: Service role only (edits tracked by backend)
CREATE POLICY "handover_draft_edits_insert_service"
ON handover_draft_edits FOR INSERT
TO service_role
WITH CHECK (true);

-- UPDATE/DELETE: Never (immutable audit trail)
-- No policies = no modifications allowed
```

---

### handover_signoffs

```sql
-- READ: Via draft yacht isolation
CREATE POLICY "handover_signoffs_select"
ON handover_signoffs FOR SELECT
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- INSERT: Service role only (sign-off via backend)
CREATE POLICY "handover_signoffs_insert_service"
ON handover_signoffs FOR INSERT
TO service_role
WITH CHECK (true);

-- UPDATE/DELETE: Never (immutable record)
-- No policies = no modifications allowed
```

---

### handover_exports

```sql
-- READ: Yacht isolation
CREATE POLICY "handover_exports_select_yacht"
ON handover_exports FOR SELECT
TO authenticated
USING (yacht_id = get_user_yacht_id());

-- INSERT: Service role only (exports generated by backend)
CREATE POLICY "handover_exports_insert_service"
ON handover_exports FOR INSERT
TO service_role
WITH CHECK (true);

-- UPDATE: Status updates only, service role
CREATE POLICY "handover_exports_update_service"
ON handover_exports FOR UPDATE
TO service_role
USING (true);

-- DELETE: Never (permanent record)
```

---

### v_handover_export_items (View)

Views inherit RLS from underlying tables automatically.

```sql
-- Grant SELECT to authenticated (RLS on source tables applies)
GRANT SELECT ON v_handover_export_items TO authenticated;
GRANT SELECT ON v_handover_export_items TO service_role;
```

---

## Role-Based Access

### Role Check Functions

```sql
CREATE OR REPLACE FUNCTION is_manager()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth_users_profiles
    WHERE id = auth.uid()
    AND role IN ('captain', 'yacht_manager', 'chief_engineer', 'admin')
  )
$$;

CREATE OR REPLACE FUNCTION is_officer()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth_users_profiles
    WHERE id = auth.uid()
    AND role IN (
        'captain', 'yacht_manager', 'chief_engineer',
        'chief_stew', 'bosun', 'eto', 'purser'
    )
  )
$$;
```

### Role Restrictions

| Operation | Required Role |
|-----------|---------------|
| View handovers | Any authenticated |
| Create handover | Any authenticated |
| Edit draft | Any authenticated |
| Accept handover (outgoing) | Officer or higher |
| Sign handover (incoming) | Officer or higher |
| Export handover | Any authenticated |
| Delete handover | Manager only |

---

## Audit Logging

All sensitive operations log to `pms_audit_log`:

```sql
CREATE OR REPLACE FUNCTION log_handover_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO pms_audit_log (
        entity_type,
        entity_id,
        action,
        actor_id,
        yacht_id,
        old_values,
        new_values,
        created_at
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        auth.uid(),
        COALESCE(NEW.yacht_id, OLD.yacht_id),
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END,
        now()
    );
    RETURN COALESCE(NEW, OLD);
END;
$$;

-- Apply to sensitive tables
CREATE TRIGGER handover_drafts_audit
AFTER INSERT OR UPDATE OR DELETE ON handover_drafts
FOR EACH ROW EXECUTE FUNCTION log_handover_audit();

CREATE TRIGGER handover_signoffs_audit
AFTER INSERT ON handover_signoffs
FOR EACH ROW EXECUTE FUNCTION log_handover_audit();

CREATE TRIGGER handover_exports_audit
AFTER INSERT ON handover_exports
FOR EACH ROW EXECUTE FUNCTION log_handover_audit();
```

---

## Storage Security

### Supabase Storage Bucket

```sql
-- Create bucket for handover exports
INSERT INTO storage.buckets (id, name, public)
VALUES ('handover-exports', 'handover-exports', false);

-- RLS policy: yacht isolation via path prefix
CREATE POLICY "handover_exports_storage_access"
ON storage.objects FOR ALL
TO authenticated
USING (
    bucket_id = 'handover-exports'
    AND (storage.foldername(name))[1] = get_user_yacht_id()::text
);
```

### Storage Path Convention

```
{yacht_id}/handover/{draft_id}/{timestamp}.{format}

Example:
85fe1119-b04c-41ac-80f1-829d23322598/handover/abc123-def456.../2026-02-03T10-30-00Z.pdf
```

---

## Security Checklist

Before deployment, verify:

- [ ] All handover tables have RLS enabled
- [ ] `get_user_yacht_id()` function exists and works
- [ ] Service role policies exist for backend operations
- [ ] No DELETE policies on immutable tables (signoffs, edits)
- [ ] Audit triggers attached to sensitive tables
- [ ] Storage bucket has yacht isolation policy
- [ ] Role check functions return correct results

---

## Testing RLS

```sql
-- Test as authenticated user
SET LOCAL role TO authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "user-uuid-here"}';

-- Should return only user's yacht data
SELECT * FROM handovers;
SELECT * FROM handover_drafts;
SELECT * FROM v_handover_export_items;

-- Should fail (no delete policy)
DELETE FROM handover_signoffs WHERE id = 'any-id';
-- ERROR: permission denied

-- Reset
RESET role;
```

---
