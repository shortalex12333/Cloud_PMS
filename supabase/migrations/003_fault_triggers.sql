-- 003_fault_triggers.sql

create or replace function public.on_fault_insert_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
begin
  perform public.notify_predictive_event(
    'fault_created',
    NEW.yacht_id,
    NEW.equipment_id
  );
  return NEW;
end;
$$;

drop trigger if exists trg_fault_insert_predictive on public.faults;

create trigger trg_fault_insert_predictive
after insert on public.faults
for each row
execute function public.on_fault_insert_notify_predictive();


create or replace function public.on_fault_update_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
begin
  -- Only fire if status or severity changed (adjust columns to your schema)
  if (NEW.status is distinct from OLD.status)
     or (coalesce(NEW.severity, '') is distinct from coalesce(OLD.severity, ''))
  then
    perform public.notify_predictive_event(
      'fault_updated',
      NEW.yacht_id,
      NEW.equipment_id
    );
  end if;

  return NEW;
end;
$$;

drop trigger if exists trg_fault_update_predictive on public.faults;

create trigger trg_fault_update_predictive
after update on public.faults
for each row
execute function public.on_fault_update_notify_predictive();
