# Crew Lens v3 - RLS Policies

**Version**: 3.0
**Date**: 2026-01-30
**Security Model**: Deny-by-default with precise role-based access

---

## Security Principles

1. **Deny-by-default**: No access unless explicitly granted
2. **Self-only mutations**: Crew can only INSERT/UPDATE own HoR records
3. **HOD department reads**: HOD can SELECT department crew, but cannot UPDATE daily entries
4. **Captain yacht-wide reads**: Captain can SELECT all yacht crew
5. **Sign-off separation**: HOD/Captain mutations happen via `pms_hor_monthly_signoffs`, not daily HoR
6. **Yacht isolation**: All policies enforce `yacht_id = current_yacht_id` via GUC
7. **Audit all mutations**: Triggers log to `pms_audit_log`

---

## Role Helper Functions

### Function: `public.is_hod()`

**Purpose**: Check if current user has HOD role

```sql
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth.users
  JOIN auth_users_roles ON auth_users_roles.user_id = auth.users.id
  WHERE auth.users.id = auth.uid()
    AND auth_users_roles.is_active = TRUE
    AND auth_users_roles.yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  RETURN user_role IN ('chief_engineer', 'chief_officer', 'chief_steward', 'purser');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

### Function: `public.is_captain()`

**Purpose**: Check if current user is captain or manager

```sql
CREATE OR REPLACE FUNCTION public.is_captain()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth.users
  JOIN auth_users_roles ON auth_users_roles.user_id = auth.users.id
  WHERE auth.users.id = auth.uid()
    AND auth_users_roles.is_active = TRUE
    AND auth_users_roles.yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  RETURN user_role IN ('captain', 'manager');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

### Function: `public.is_manager()`

**Purpose**: Check if current user is manager (alias for is_captain)

```sql
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN public.is_captain();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

### Function: `public.get_user_department()`

**Purpose**: Get department for a user based on role

```sql
CREATE OR REPLACE FUNCTION public.get_user_department(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth_users_roles
  WHERE user_id = p_user_id
    AND is_active = TRUE
    AND yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  -- Map role to department
  IF user_role LIKE '%engineer%' THEN
    RETURN 'engineering';
  ELSIF user_role IN ('chief_officer', 'officer', 'deckhand', 'bosun') THEN
    RETURN 'deck';
  ELSIF user_role LIKE '%steward%' THEN
    RETURN 'interior';
  ELSIF user_role IN ('chef', 'sous_chef', 'galley_hand') THEN
    RETURN 'galley';
  ELSE
    RETURN 'general';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

### Function: `public.is_same_department()`

**Purpose**: Check if two users are in the same department

```sql
CREATE OR REPLACE FUNCTION public.is_same_department(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN public.get_user_department(auth.uid()) = public.get_user_department(p_user_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

---

## Table: `pms_hours_of_rest`

### Current Problem

**Existing policies** (too permissive):
```sql
-- BAD: Grants access to ALL users on same yacht
CREATE POLICY yacht_isolation ON pms_hours_of_rest
  FOR ALL
  USING (yacht_id = current_setting('request.yacht_id', TRUE)::UUID);

CREATE POLICY user_own_records ON pms_hours_of_rest
  FOR ALL
  USING (user_id = auth.uid());
```

**Issue**: With `OR` semantics, any user on the same yacht can see all HoR records (privacy violation).

---

### Fixed Policies

**Drop existing policies**:
```sql
DROP POLICY IF EXISTS yacht_isolation ON pms_hours_of_rest;
DROP POLICY IF EXISTS user_own_records ON pms_hours_of_rest;
DROP POLICY IF EXISTS hod_department_access ON pms_hours_of_rest;
DROP POLICY IF EXISTS captain_yacht_access ON pms_hours_of_rest;
```

**Enable RLS**:
```sql
ALTER TABLE pms_hours_of_rest ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_hours_of_rest FORCE ROW LEVEL SECURITY;
```

---

#### Policy 1: SELECT (Read Access)

**Who can SELECT**:
- Self: Always
- HOD: Department crew on same yacht
- Captain/Manager: All yacht crew

```sql
CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest
  FOR SELECT
  USING (
    -- Yacht isolation (mandatory for all)
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      -- Self-access
      user_id = auth.uid()
      OR
      -- HOD department access
      (public.is_hod() AND public.is_same_department(user_id))
      OR
      -- Captain/Manager yacht-wide access
      public.is_captain()
    )
  );
```

**Test Cases**:
```sql
-- Crew can see own records
SELECT * FROM pms_hours_of_rest WHERE user_id = auth.uid();  -- ✓ Returns own records

-- Crew CANNOT see other crew
SELECT * FROM pms_hours_of_rest WHERE user_id != auth.uid();  -- ✓ Returns 0 rows (403)

-- HOD can see department crew
-- (Assumes current user is chief_engineer, viewing another engineer)
SELECT * FROM pms_hours_of_rest WHERE user_id = 'engineer_uuid';  -- ✓ Returns records

-- HOD CANNOT see other departments
-- (Assumes current user is chief_engineer, viewing steward)
SELECT * FROM pms_hours_of_rest WHERE user_id = 'steward_uuid';  -- ✓ Returns 0 rows

-- Captain can see all yacht crew
SELECT * FROM pms_hours_of_rest;  -- ✓ Returns all yacht records
```

---

#### Policy 2: INSERT (Create Records)

**Who can INSERT**:
- Self ONLY: user_id must equal auth.uid()
- yacht_id must equal current yacht

```sql
CREATE POLICY pms_hours_of_rest_insert ON pms_hours_of_rest
  FOR INSERT
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

**Test Cases**:
```sql
-- Crew can insert own records
INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, ...)
VALUES (current_yacht_id, auth.uid(), '2026-01-30', '[...]', ...);  -- ✓ Success

-- Crew CANNOT insert for others (even HOD/Captain)
INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, ...)
VALUES (current_yacht_id, 'other_user_uuid', '2026-01-30', ...);  -- ✗ 403 Forbidden

-- HOD CANNOT insert for crew
-- (HOD mutations happen via pms_hor_monthly_signoffs)
INSERT INTO pms_hours_of_rest (yacht_id, user_id, ...)
VALUES (current_yacht_id, 'crew_uuid', ...);  -- ✗ 403 Forbidden
```

---

#### Policy 3: UPDATE (Modify Records)

**Who can UPDATE**:
- Self ONLY: Can only update own records
- HOD/Captain CANNOT update daily entries (mutations via sign-off table)

```sql
CREATE POLICY pms_hours_of_rest_update ON pms_hours_of_rest
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

**Test Cases**:
```sql
-- Crew can update own records
UPDATE pms_hours_of_rest
SET rest_periods = '[...]', updated_at = NOW()
WHERE user_id = auth.uid() AND record_date = '2026-01-30';  -- ✓ Success

-- Crew CANNOT update others
UPDATE pms_hours_of_rest
SET rest_periods = '[...]'
WHERE user_id = 'other_uuid';  -- ✗ 0 rows updated (403)

-- HOD CANNOT update crew daily entries
-- (Even if SELECT policy allows viewing)
UPDATE pms_hours_of_rest
SET rest_periods = '[...]'
WHERE user_id = 'crew_uuid';  -- ✗ 0 rows updated (403)
```

---

#### Policy 4: DELETE (Denied)

**Who can DELETE**: NO ONE

```sql
-- No DELETE policy = deny all deletes
-- If soft delete needed, use UPDATE to set is_active = FALSE
```

**Test Cases**:
```sql
-- Anyone trying to delete
DELETE FROM pms_hours_of_rest WHERE id = 'any_uuid';  -- ✗ 403 Forbidden
```

---

## Table: `pms_hor_monthly_signoffs`

### Purpose

Separate table for multi-level sign-offs:
- Crew monthly signature
- HOD monthly signature (for department)
- Captain final sign-off (for yacht)

---

### Policies

#### Policy 1: SELECT

**Who can SELECT**:
- Self: Own sign-off records
- HOD: Department crew sign-offs
- Captain: All yacht sign-offs

```sql
CREATE POLICY pms_hor_monthly_signoffs_select ON pms_hor_monthly_signoffs
  FOR SELECT
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR
      (public.is_hod() AND public.is_same_department(user_id))
      OR
      public.is_captain()
    )
  );
```

---

#### Policy 2: INSERT

**Who can INSERT**:
- Crew: Can create own sign-off record (status='pending')
- System/Backend: Via handler only

```sql
CREATE POLICY pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs
  FOR INSERT
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    AND status = 'pending'  -- Crew can only create pending records
  );
```

---

#### Policy 3: UPDATE

**Who can UPDATE**:
- **Crew signing**: Can update own record to add `crew_signature` (status: pending → crew_signed)
- **HOD signing**: Can update department crew records to add `hod_signature` (status: crew_signed → hod_signed)
- **Captain signing**: Can update all yacht records to add `master_signature` (status: hod_signed → finalized)

```sql
-- Crew can sign own month
CREATE POLICY pms_hor_monthly_signoffs_update_crew_sign ON pms_hor_monthly_signoffs
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    AND status = 'pending'
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    AND status = 'crew_signed'
    AND crew_signature IS NOT NULL
  );

-- HOD can sign department crew months
CREATE POLICY pms_hor_monthly_signoffs_update_hod_sign ON pms_hor_monthly_signoffs
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND public.is_hod()
    AND public.is_same_department(user_id)
    AND status = 'crew_signed'
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND status = 'hod_signed'
    AND hod_user_id = auth.uid()
    AND hod_signature IS NOT NULL
  );

-- Captain can finalize all yacht crew months
CREATE POLICY pms_hor_monthly_signoffs_update_master_sign ON pms_hor_monthly_signoffs
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND public.is_captain()
    AND status = 'hod_signed'
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND status = 'finalized'
    AND master_user_id = auth.uid()
    AND master_signature IS NOT NULL
  );
```

---

#### Policy 4: DELETE (Denied)

```sql
-- No DELETE policy = deny all
```

---

## Table: `pms_crew_normal_hours`

### Purpose

Work schedule templates for auto-population of HoR records.

---

### Policies

#### Policy 1: SELECT

**Who can SELECT**:
- Self: Own templates
- HOD: Department crew templates (read-only, for reference)
- Captain: All yacht templates

```sql
CREATE POLICY pms_crew_normal_hours_select ON pms_crew_normal_hours
  FOR SELECT
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR
      (public.is_hod() AND public.is_same_department(user_id))
      OR
      public.is_captain()
    )
  );
```

---

#### Policy 2: INSERT

**Who can INSERT**:
- Self ONLY

```sql
CREATE POLICY pms_crew_normal_hours_insert ON pms_crew_normal_hours
  FOR INSERT
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

---

#### Policy 3: UPDATE

**Who can UPDATE**:
- Self ONLY

```sql
CREATE POLICY pms_crew_normal_hours_update ON pms_crew_normal_hours
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

---

#### Policy 4: DELETE

**Who can DELETE**:
- Self ONLY (soft delete via is_active = FALSE preferred)

```sql
CREATE POLICY pms_crew_normal_hours_delete ON pms_crew_normal_hours
  FOR DELETE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

---

## Table: `pms_crew_hours_warnings`

### Purpose

Track overtime warnings, violations, and crew acknowledgments/dismissals.

---

### Policies

#### Policy 1: SELECT

**Who can SELECT**:
- Self: Own warnings
- HOD: Department crew warnings
- Captain: All yacht warnings

```sql
CREATE POLICY pms_crew_hours_warnings_select ON pms_crew_hours_warnings
  FOR SELECT
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR
      (public.is_hod() AND public.is_same_department(user_id))
      OR
      public.is_captain()
    )
  );
```

---

#### Policy 2: INSERT

**Who can INSERT**:
- System/Backend ONLY (via trigger or handler)
- Crew CANNOT manually insert warnings

```sql
-- No INSERT policy for users
-- Warnings inserted by backend via service role
```

---

#### Policy 3: UPDATE

**Who can UPDATE**:
- Crew: Can acknowledge/dismiss own warnings

```sql
CREATE POLICY pms_crew_hours_warnings_update ON pms_crew_hours_warnings
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    -- Crew can only update status and dismissal fields
    AND (acknowledged_by = auth.uid() OR dismissed_by = auth.uid())
  );
```

---

#### Policy 4: DELETE (Denied)

```sql
-- No DELETE policy = deny all
-- Warnings are permanent audit records
```

---

## GUC (Session Variables) Pattern

### Setting Yacht ID

**Middleware** (apps/api/middleware/yacht_isolation.py):

```python
async def set_yacht_context(request: Request, call_next):
    # Extract yacht_id from JWT or yacht code
    yacht_id = get_yacht_id_from_jwt(request)

    # Set GUC for this request session
    db = request.state.db
    db.execute(text(f"SET request.yacht_id = '{yacht_id}'"))

    response = await call_next(request)
    return response
```

**SQL Function Usage**:

```sql
-- In RLS policies
current_setting('request.yacht_id', TRUE)::UUID

-- In handlers
SELECT current_setting('request.yacht_id', TRUE)::UUID;
```

---

## Audit Trigger (All Mutations)

### Trigger Function

```sql
CREATE OR REPLACE FUNCTION audit_hor_mutation()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO pms_audit_log (
    table_name,
    record_id,
    action,
    user_id,
    yacht_id,
    before_state,
    after_state,
    created_at
  ) VALUES (
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    TG_OP,  -- 'INSERT', 'UPDATE', 'DELETE'
    auth.uid(),
    current_setting('request.yacht_id', TRUE)::UUID,
    CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
    NOW()
  );

  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

### Attach Triggers

```sql
-- pms_hours_of_rest
CREATE TRIGGER trigger_audit_pms_hours_of_rest
  AFTER INSERT OR UPDATE OR DELETE ON pms_hours_of_rest
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();

-- pms_hor_monthly_signoffs
CREATE TRIGGER trigger_audit_pms_hor_monthly_signoffs
  AFTER INSERT OR UPDATE ON pms_hor_monthly_signoffs
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();

-- pms_crew_normal_hours
CREATE TRIGGER trigger_audit_pms_crew_normal_hours
  AFTER INSERT OR UPDATE OR DELETE ON pms_crew_normal_hours
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();

-- pms_crew_hours_warnings
CREATE TRIGGER trigger_audit_pms_crew_hours_warnings
  AFTER INSERT OR UPDATE ON pms_crew_hours_warnings
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();
```

---

## Migration Script

### File: `migrations/001_fix_hor_rls_policies.sql`

```sql
-- ============================================================================
-- Migration: Fix Hours of Rest RLS Policies
-- Date: 2026-01-30
-- Purpose: Replace permissive policies with precise role-based access
-- ============================================================================

BEGIN;

-- 1. Create helper functions
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth_users_roles
  WHERE user_id = auth.uid()
    AND is_active = TRUE
    AND yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  RETURN user_role IN ('chief_engineer', 'chief_officer', 'chief_steward', 'purser');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.is_captain()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth_users_roles
  WHERE user_id = auth.uid()
    AND is_active = TRUE
    AND yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  RETURN user_role IN ('captain', 'manager');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.get_user_department(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM auth_users_roles
  WHERE user_id = p_user_id
    AND is_active = TRUE
    AND yacht_id = current_setting('request.yacht_id', TRUE)::UUID
  LIMIT 1;

  IF user_role LIKE '%engineer%' THEN RETURN 'engineering';
  ELSIF user_role IN ('chief_officer', 'officer', 'deckhand', 'bosun') THEN RETURN 'deck';
  ELSIF user_role LIKE '%steward%' THEN RETURN 'interior';
  ELSIF user_role IN ('chef', 'sous_chef', 'galley_hand') THEN RETURN 'galley';
  ELSE RETURN 'general';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

CREATE OR REPLACE FUNCTION public.is_same_department(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN public.get_user_department(auth.uid()) = public.get_user_department(p_user_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- 2. Drop old permissive policies
DROP POLICY IF EXISTS yacht_isolation ON pms_hours_of_rest;
DROP POLICY IF EXISTS user_own_records ON pms_hours_of_rest;
DROP POLICY IF EXISTS hod_department_access ON pms_hours_of_rest;
DROP POLICY IF EXISTS captain_yacht_access ON pms_hours_of_rest;

-- 3. Enable RLS
ALTER TABLE pms_hours_of_rest ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_hours_of_rest FORCE ROW LEVEL SECURITY;

-- 4. Create new precise policies
CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest
  FOR SELECT
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR
      (public.is_hod() AND public.is_same_department(user_id))
      OR
      public.is_captain()
    )
  );

CREATE POLICY pms_hours_of_rest_insert ON pms_hours_of_rest
  FOR INSERT
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );

CREATE POLICY pms_hours_of_rest_update ON pms_hours_of_rest
  FOR UPDATE
  USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  )
  WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );

-- 5. Create audit trigger
CREATE OR REPLACE FUNCTION audit_hor_mutation()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO pms_audit_log (
    table_name, record_id, action, user_id, yacht_id,
    before_state, after_state, created_at
  ) VALUES (
    TG_TABLE_NAME,
    COALESCE(NEW.id, OLD.id),
    TG_OP,
    auth.uid(),
    current_setting('request.yacht_id', TRUE)::UUID,
    CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
    CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
    NOW()
  );
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_audit_pms_hours_of_rest
  AFTER INSERT OR UPDATE OR DELETE ON pms_hours_of_rest
  FOR EACH ROW EXECUTE FUNCTION audit_hor_mutation();

COMMIT;
```

---

## Testing RLS Policies

### Test Suite Location

**File**: `tests/docker/run_hor_rls_tests.py`

### Test Cases

```python
def test_crew_can_view_own_hor(crew_user, db):
    """Crew can SELECT own HoR records"""
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == crew_user.id
    ).all()
    assert len(records) > 0

def test_crew_cannot_view_others_hor(crew_user, other_crew_user, db):
    """Crew CANNOT SELECT other crew HoR"""
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == other_crew_user.id
    ).all()
    assert len(records) == 0  # RLS blocks

def test_hod_can_view_department(hod_user, dept_crew_user, db):
    """HOD can SELECT department crew HoR"""
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == dept_crew_user.id
    ).all()
    assert len(records) > 0

def test_hod_cannot_view_other_departments(hod_user, other_dept_crew, db):
    """HOD CANNOT SELECT other department crew"""
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == other_dept_crew.id
    ).all()
    assert len(records) == 0  # RLS blocks

def test_captain_can_view_all_yacht(captain_user, db):
    """Captain can SELECT all yacht crew HoR"""
    records = db.query(pms_hours_of_rest).all()
    assert len(records) > 0  # All yacht crew

def test_crew_can_insert_own_hor(crew_user, db):
    """Crew can INSERT own HoR"""
    record = pms_hours_of_rest(
        yacht_id=crew_user.yacht_id,
        user_id=crew_user.id,
        record_date=date.today(),
        rest_periods=[{"start": "22:00", "end": "06:00", "hours": 8.0}],
        total_rest_hours=8.0
    )
    db.add(record)
    db.commit()  # Should succeed

def test_crew_cannot_insert_for_others(crew_user, other_crew_user, db):
    """Crew CANNOT INSERT for other crew"""
    with pytest.raises(InsufficientPrivilege):
        record = pms_hours_of_rest(
            yacht_id=crew_user.yacht_id,
            user_id=other_crew_user.id,  # ✗ Different user
            record_date=date.today(),
            rest_periods=[{"start": "22:00", "end": "06:00", "hours": 8.0}],
            total_rest_hours=8.0
        )
        db.add(record)
        db.commit()

def test_hod_cannot_update_crew_daily_entries(hod_user, crew_user, db):
    """HOD CANNOT UPDATE crew daily HoR entries"""
    record = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == crew_user.id
    ).first()

    with pytest.raises(InsufficientPrivilege):
        record.rest_periods = [{"start": "23:00", "end": "07:00", "hours": 8.0}]
        db.commit()
```

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase - RLS Policies Complete
**Next**: INFRA_AUDIT.md
