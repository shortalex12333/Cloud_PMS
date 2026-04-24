-- Migration: add resolved_by_work_order_id FK column to pms_faults
-- Owner: WORKORDER05 (PR-WO-6)
-- Applied: <manual — delete this file after running>
--
-- Why: when a work order linked to a fault reaches status=completed, the
-- close_work_order dispatcher now transitions the fault to status=resolved
-- and stamps this FK column so the bridge is auditable. Prior to this
-- migration the relationship was one-way (pms_work_orders.fault_id) and the
-- fault had no record of which WO resolved it.
--
-- Schema change is additive + nullable + indexed. No backfill needed — rows
-- predating the migration remain NULL.
--
-- Per /Users/celeste7/.claude/projects/-Users-celeste7/memory/feedback_migration_convention.md
-- migration files are temporary: apply to Supabase, verify, then DELETE this
-- file.

BEGIN;

ALTER TABLE public.pms_faults
  ADD COLUMN IF NOT EXISTS resolved_by_work_order_id uuid
  REFERENCES public.pms_work_orders(id) ON DELETE SET NULL;

-- Query hot path: "which faults did this WO close?" — rare enough that an
-- index is optional, but cheap to have given the column nullability skews
-- most rows away from the value. Partial index keeps the b-tree small.
CREATE INDEX IF NOT EXISTS idx_pms_faults_resolved_by_wo
  ON public.pms_faults (resolved_by_work_order_id)
  WHERE resolved_by_work_order_id IS NOT NULL;

COMMIT;

-- Verify (run in psql after apply):
--   SELECT column_name, data_type, is_nullable
--     FROM information_schema.columns
--    WHERE table_name = 'pms_faults' AND column_name = 'resolved_by_work_order_id';
--
--   \d public.pms_faults
