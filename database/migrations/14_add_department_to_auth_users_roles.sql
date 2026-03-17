-- Migration 14: Add department to auth_users_roles
-- Date: 2026-03-13
-- Purpose: Enable HoD department-scoped ledger timeline queries
--
-- The department column is derived from role via trigger — never set manually.
-- Role → department mapping is the canonical truth for this yacht.

-- ================================================================
-- PART 1: Add department column to auth_users_roles
-- ================================================================

ALTER TABLE public.auth_users_roles
  ADD COLUMN IF NOT EXISTS department text;

-- Check constraint: only valid department values
ALTER TABLE public.auth_users_roles
  DROP CONSTRAINT IF EXISTS valid_department;
ALTER TABLE public.auth_users_roles
  ADD CONSTRAINT valid_department CHECK (
    department IN ('deck', 'engineering', 'interior', 'general')
  );

-- ================================================================
-- PART 2: Trigger to auto-derive department from role
-- ================================================================
-- Runs on INSERT and UPDATE. If department is not explicitly set,
-- it derives it from the role. This is the single source of truth.

CREATE OR REPLACE FUNCTION public.derive_department_from_role()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  -- Auto-derive department when:
  --   (a) it is not explicitly set on INSERT, OR
  --   (b) the role changes on UPDATE (promotion/demotion must update department)
  IF NEW.department IS NULL
     OR (TG_OP = 'UPDATE' AND NEW.role IS DISTINCT FROM OLD.role) THEN
    NEW.department := CASE NEW.role
      WHEN 'captain'        THEN 'deck'
      WHEN 'deck'           THEN 'deck'
      WHEN 'chief_engineer' THEN 'engineering'
      WHEN 'eto'            THEN 'engineering'
      WHEN 'manager'        THEN 'interior'
      WHEN 'interior'       THEN 'interior'
      WHEN 'crew'           THEN 'general'
      WHEN 'vendor'         THEN 'general'
      ELSE                       'general'
    END;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_derive_department ON public.auth_users_roles;
CREATE TRIGGER trg_derive_department
  BEFORE INSERT OR UPDATE ON public.auth_users_roles
  FOR EACH ROW
  EXECUTE FUNCTION public.derive_department_from_role();

-- ================================================================
-- PART 3: Backfill department for existing auth_users_roles rows
-- ================================================================

UPDATE public.auth_users_roles
SET department = CASE role
  WHEN 'captain'        THEN 'deck'
  WHEN 'deck'           THEN 'deck'
  WHEN 'chief_engineer' THEN 'engineering'
  WHEN 'eto'            THEN 'engineering'
  WHEN 'manager'        THEN 'interior'
  WHEN 'interior'       THEN 'interior'
  WHEN 'crew'           THEN 'general'
  WHEN 'vendor'         THEN 'general'
  ELSE                       'general'
END
WHERE department IS NULL;

-- ================================================================
-- PART 4: Backfill ledger_events.department from user_role
-- ================================================================
-- Historical rows have department=NULL. Backfill deterministically
-- from the user_role already stored in the row.

UPDATE public.ledger_events
SET department = CASE user_role
  WHEN 'captain'        THEN 'deck'
  WHEN 'deck'           THEN 'deck'
  WHEN 'chief_engineer' THEN 'engineering'
  WHEN 'eto'            THEN 'engineering'
  WHEN 'manager'        THEN 'interior'
  WHEN 'interior'       THEN 'interior'
  WHEN 'crew'           THEN 'general'
  WHEN 'vendor'         THEN 'general'
  ELSE                       'general'
END
WHERE department IS NULL
  AND user_role IS NOT NULL;

-- ================================================================
-- VERIFICATION
-- ================================================================

SELECT role, department, COUNT(*) AS row_count
FROM public.auth_users_roles
GROUP BY role, department
ORDER BY role;

SELECT 'migration 14 complete' AS status;
