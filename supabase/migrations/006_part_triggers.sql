-- 006_part_triggers.sql

create or replace function public.on_part_update_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
begin
  -- Only fire when quantity decreases and equipment_id is known
  if NEW.equipment_id is not null
     and NEW.quantity < OLD.quantity then

    perform public.notify_predictive_event(
      'part_used',
      NEW.yacht_id,
      NEW.equipment_id
    );
  end if;

  return NEW;
end;
$$;

drop trigger if exists trg_part_update_predictive on public.parts;

create trigger trg_part_update_predictive
after update on public.parts
for each row
execute function public.on_part_update_notify_predictive();
