-- Migration: add system_id + system_name + running-hours columns to pms_work_orders
-- Owner: WORKORDER05 (PR-WO-7)
-- Applied: <manual — delete this file after running>
--
-- Why: UX sheet /Users/celeste7/Desktop/lens_card_upgrades.md:354-356.
--
--   1. `system_id` + `system_name` — the parent system the equipment is part
--      of (propulsion, HVAC, electrical, navigation, etc). Denormalised
--      because the UI frequently needs the label without an extra join, and
--      because pms_equipment is itself self-referential (equipment.parent_id)
--      so resolving "system" is an N-up tree walk otherwise.
--
--   2. `running_hours_current` + `running_hours_checkpoint` +
--      `running_hours_required` — rotating machinery (engines, generators,
--      HVAC compressors, winches) is scheduled against running hours, not
--      calendar dates. Adding all three columns to every WO (not just
--      rotating-machinery ones) and defaulting `running_hours_required` to
--      false matches the CEO's MVP rule (spec line 356):
--        "We **cannot** run script for 'if work order contain motor, crane,
--         engine, then list hours'. This is wrong and forbidden. Instead we
--         need to add to all work orders, and leave blank if not required,
--         or mark as 'not required' via user."
--
-- Schema change is additive + nullable / defaulted. No backfill needed.
--
-- Per feedback_migration_convention.md: apply to Supabase, verify, then
-- DELETE this file.

BEGIN;

-- ── System linkage (denormalised for frontend ergonomics) ──────────────────
ALTER TABLE public.pms_work_orders
  ADD COLUMN IF NOT EXISTS system_id uuid
    REFERENCES public.pms_equipment(id) ON DELETE SET NULL;

ALTER TABLE public.pms_work_orders
  ADD COLUMN IF NOT EXISTS system_name text;

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_system_id
  ON public.pms_work_orders (system_id)
  WHERE system_id IS NOT NULL;

-- ── Running-hours (rotating machinery) ─────────────────────────────────────
ALTER TABLE public.pms_work_orders
  ADD COLUMN IF NOT EXISTS running_hours_required boolean NOT NULL DEFAULT false;

ALTER TABLE public.pms_work_orders
  ADD COLUMN IF NOT EXISTS running_hours_current numeric(12, 2);

ALTER TABLE public.pms_work_orders
  ADD COLUMN IF NOT EXISTS running_hours_checkpoint numeric(12, 2);

-- Sanity constraints — negative values are nonsensical.
ALTER TABLE public.pms_work_orders
  DROP CONSTRAINT IF EXISTS pms_work_orders_running_hours_current_nonneg;
ALTER TABLE public.pms_work_orders
  ADD CONSTRAINT pms_work_orders_running_hours_current_nonneg
  CHECK (running_hours_current IS NULL OR running_hours_current >= 0);

ALTER TABLE public.pms_work_orders
  DROP CONSTRAINT IF EXISTS pms_work_orders_running_hours_checkpoint_nonneg;
ALTER TABLE public.pms_work_orders
  ADD CONSTRAINT pms_work_orders_running_hours_checkpoint_nonneg
  CHECK (running_hours_checkpoint IS NULL OR running_hours_checkpoint >= 0);

COMMIT;

-- Verify (run in psql after apply):
--   SELECT column_name, data_type, is_nullable, column_default
--     FROM information_schema.columns
--    WHERE table_name = 'pms_work_orders'
--      AND column_name IN (
--        'system_id', 'system_name',
--        'running_hours_required', 'running_hours_current', 'running_hours_checkpoint'
--      )
--    ORDER BY column_name;
