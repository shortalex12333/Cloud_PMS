-- Migration 014: user_accounts table for invited crew members
-- Applied to: MASTER Supabase (qvzmkaamzaqxpzbewjxe)
-- Purpose: Source-control the user_accounts table that was created ad-hoc.
--          This migration is idempotent — safe to re-run.
--
-- This table is the gateway auth.py reads on every API request:
--   lookup_tenant_for_user(user_id) → user_accounts → fleet_registry → auth_users_roles
--
-- Rows are written:
--   - By the onboarding owner on vessel setup (their own record, set to 'active')
--   - By /api/invite-users in celesteos-registration-windows immediately after
--     generate_link returns the new user UUID (before the email is sent)
--
-- The FK to auth.users ON DELETE CASCADE means rows are automatically cleaned up
-- if the auth user is deleted from Supabase.

CREATE TABLE IF NOT EXISTS public.user_accounts (
  id                    UUID          NOT NULL PRIMARY KEY
                                      REFERENCES auth.users(id) ON DELETE CASCADE,
  yacht_id              TEXT                                      -- FK added below
                                      REFERENCES public.fleet_registry(yacht_id)
                                      ON DELETE SET NULL,
  email                 TEXT          NOT NULL UNIQUE,
  display_name          TEXT,
  status                TEXT          DEFAULT 'pending'
                                      CHECK (status IN ('pending', 'active', 'suspended', 'disabled')),
  email_verified        BOOLEAN       DEFAULT FALSE,
  role                  TEXT          DEFAULT 'member',           -- informational only; auth.py uses tenant auth_users_roles
  fleet_vessel_ids      JSONB,                                    -- only populated for fleet manager accounts
  login_count           INTEGER       DEFAULT 0,
  failed_login_attempts INTEGER       DEFAULT 0,
  locked_until          TIMESTAMP,
  last_login            TIMESTAMP,
  created_at            TIMESTAMP     DEFAULT NOW(),
  updated_at            TIMESTAMPTZ   DEFAULT NOW()
);

-- Index for the frequent lookup pattern: .eq('id', user_id)
CREATE INDEX IF NOT EXISTS idx_user_accounts_id
  ON public.user_accounts (id);

-- Index for email uniqueness lookups
CREATE INDEX IF NOT EXISTS idx_user_accounts_email
  ON public.user_accounts (email);

-- Index for yacht membership queries (e.g. listing all users on a vessel)
CREATE INDEX IF NOT EXISTS idx_user_accounts_yacht
  ON public.user_accounts (yacht_id);

-- Notes:
-- • status='pending' → auth.py blocks login (lookup_tenant_for_user returns None)
-- • status='active'  → auth.py admits user and proceeds to tenant role lookup
-- • Invite flow writes status='active' directly — no separate activation step needed
-- • user_accounts.role is NOT used for access control — auth.py reads from
--   tenant auth_users_roles which is populated by the first-login bootstrap
--   in _bootstrap_tenant_user() (apps/api/middleware/auth.py)
