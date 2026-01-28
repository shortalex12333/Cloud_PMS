-- Migration: Add SLA, criticality, due dates, activity, and soft-delete columns to pms_work_orders
-- Purpose: Support deterministic grouping (Overdue/Critical/Time-Consuming) and safe archive semantics

begin;

alter table if exists public.pms_work_orders
  add column if not exists due_at timestamptz,
  add column if not exists started_at timestamptz,
  add column if not exists estimated_duration_minutes integer,
  add column if not exists severity text,
  add column if not exists criticality_rank smallint,
  add column if not exists sla_priority text,
  add column if not exists last_activity_at timestamptz,
  add column if not exists deleted_at timestamptz,
  add column if not exists deleted_by uuid,
  add column if not exists deletion_reason text;

create index if not exists idx_wo_yacht_status_due on public.pms_work_orders (yacht_id, status, due_at);
create index if not exists idx_wo_yacht_criticality on public.pms_work_orders (yacht_id, criticality_rank nulls last);
create index if not exists idx_wo_last_activity on public.pms_work_orders (yacht_id, last_activity_at desc);

comment on column public.pms_work_orders.deleted_at is 'Soft delete timestamp; archived in UI, never hard-deleted';
comment on column public.pms_work_orders.deletion_reason is 'Human-readable reason for archive (ledger also stores)';

commit;

