-- 005_note_triggers.sql

create or replace function public.on_note_insert_notify_predictive()
returns trigger
language plpgsql
security definer
as $$
begin
  -- Only relevant if note is bound to equipment
  if NEW.equipment_id is not null then
    perform public.notify_predictive_event(
      'note_added',
      NEW.yacht_id,
      NEW.equipment_id
    );
  end if;
  return NEW;
end;
$$;

drop trigger if exists trg_note_insert_predictive on public.notes;

create trigger trg_note_insert_predictive
after insert on public.notes
for each row
execute function public.on_note_insert_notify_predictive();
