-- Migration: Create view v_my_work_orders_summary for deterministic grouping

begin;

create or replace view public.v_my_work_orders_summary as
with base as (
  select
    wo.yacht_id,
    wo.id as work_order_id,
    wo.title,
    wo.status,
    wo.due_at,
    wo.started_at,
    wo.estimated_duration_minutes,
    wo.severity,
    wo.criticality_rank,
    wo.sla_priority,
    wo.last_activity_at,
    (wo.due_at is not null and wo.due_at < now() and wo.status not in ('completed','cancelled','deferred')) as is_overdue,
    greatest(0, extract(day from (now() - coalesce(wo.due_at, now())))::int) as days_overdue,
    coalesce(wo.estimated_duration_minutes, 0) as est_minutes
  from public.pms_work_orders wo
  where wo.deleted_at is null
)
select *,
  case
    when is_overdue then 'overdue'
    when criticality_rank is not null and criticality_rank <= 3 then 'critical'
    when est_minutes >= 240 then 'time_consuming'
    else 'other'
  end as group_key
from base;

comment on view public.v_my_work_orders_summary is 'Partitions work orders into overdue/critical/time_consuming/other for the current yacht';

commit;

