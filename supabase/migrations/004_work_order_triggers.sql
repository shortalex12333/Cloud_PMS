-- 004_work_order_triggers.sql

create or replace function public.on_work_order_insert_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
begin
  perform public.notify_predictive_event(
    'wo_created',
    NEW.yacht_id,
    NEW.equipment_id
  );
  return NEW;
end;
$$;

drop trigger if exists trg_work_order_insert_predictive on public.work_orders;

create trigger trg_work_order_insert_predictive
after insert on public.work_orders
for each row
execute function public.on_work_order_insert_notify_predictive();


create or replace function public.on_work_order_update_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
declare
  status_changed boolean;
  due_changed    boolean;
begin
  status_changed := NEW.status is distinct from OLD.status;
  due_changed    := NEW.due_date is distinct from OLD.due_date;

  if status_changed or due_changed then
    perform public.notify_predictive_event(
      'wo_updated',
      NEW.yacht_id,
      NEW.equipment_id
    );
  end if;

  return NEW;
end;
$$;

drop trigger if exists trg_work_order_update_predictive on public.work_orders;

create trigger trg_work_order_update_predictive
after update on public.work_orders
for each row
execute function public.on_work_order_update_notify_predictive();
