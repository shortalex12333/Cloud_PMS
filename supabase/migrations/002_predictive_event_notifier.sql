-- 002_predictive_event_notifier.sql

-- Optional: store webhook URL in a setting so you don't hardcode it
-- Run once:
-- select set_config('app.predictive_webhook_url', 'https://api.celeste7.ai/webhook/internal/predictive-event', false);

create or replace function public.notify_predictive_event(
  p_event        text,
  p_yacht_id     uuid,
  p_equipment_id uuid
)
returns void
language plpgsql
security definer
as $$
declare
  v_url text;
  v_payload jsonb;
begin
  -- Resolve webhook URL from GUC; fallback if not set
  v_url := current_setting('app.predictive_webhook_url', true);

  if v_url is null or v_url = '' then
    -- Hard fallback – change to your actual n8n webhook
    v_url := 'https://api.celeste7.ai/webhook/internal/predictive-event';
  end if;

  if p_equipment_id is null or p_yacht_id is null then
    -- Nothing to do if we don't know which equipment
    return;
  end if;

  v_payload := jsonb_build_object(
    'event',        p_event,
    'yacht_id',     p_yacht_id,
    'equipment_id', p_equipment_id
  );

  perform
    net.http_post(
      url     => v_url,
      headers => '{"Content-Type": "application/json"}'::jsonb,
      body    => v_payload
    );

exception
  when others then
    -- Fail silently; prediction is best-effort, don't break writes
    perform pg_notify('predictive_errors',
      format('notify_predictive_event failed: %s', sqlerrm));
end;
$$;

-- Make sure your service_role (or whatever role n8n uses) can execute this if needed
grant execute on function public.notify_predictive_event(text, uuid, uuid) to postgres, service_role;
