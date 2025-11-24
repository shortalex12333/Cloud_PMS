-- 001_enable_pg_net_and_predictive_tables.sql

-- 1. Enable HTTP extension (Supabase: pg_net)
create extension if not exists pg_net;

-- 2. Predictive state per equipment
create table if not exists public.predictive_state (
  yacht_id            uuid        not null,
  equipment_id        uuid        not null,
  risk_score          numeric(5,4) not null default 0.0,  -- 0.0000 - 1.0000
  confidence          numeric(5,4) not null default 0.0,
  contributing_factors jsonb      not null default '{}'::jsonb,
  last_calculated_at  timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  constraint predictive_state_pkey
    primary key (yacht_id, equipment_id),

  constraint predictive_state_equipment_fk
    foreign key (equipment_id) references public.equipment(id) on delete cascade
);

create index if not exists idx_predictive_state_risk_score
  on public.predictive_state (risk_score desc);

create index if not exists idx_predictive_state_last_calc
  on public.predictive_state (last_calculated_at desc);

-- 3. Predictive insights (event log)
create table if not exists public.predictive_insights (
  id              uuid primary key default gen_random_uuid(),
  yacht_id        uuid        not null,
  equipment_id    uuid        not null,
  insight_type    text        not null,      -- e.g. 'risk_alert'
  title           text        not null,
  description     text        not null,
  recommendation  text        not null,
  severity        text        not null,      -- 'high' | 'critical'
  metadata        jsonb       not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),

  constraint predictive_insights_equipment_fk
    foreign key (equipment_id) references public.equipment(id) on delete cascade
);

create index if not exists idx_predictive_insights_equipment
  on public.predictive_insights (equipment_id, created_at desc);

create index if not exists idx_predictive_insights_yacht
  on public.predictive_insights (yacht_id, created_at desc);

create index if not exists idx_predictive_insights_severity
  on public.predictive_insights (severity, created_at desc);

-- 4. Minimal hook for UI: flag on equipment
alter table public.equipment
  add column if not exists attention_flag boolean not null default false;

create index if not exists idx_equipment_attention_flag
  on public.equipment (attention_flag);

-- 5. Minimal hook for handover integration (if not already defined)
-- If handover_items table already exists, skip this.
create table if not exists public.handover_items (
  id            uuid primary key default gen_random_uuid(),
  yacht_id      uuid        not null,
  equipment_id  uuid        null,
  source_type   text        not null,      -- 'predictive_insight', 'fault', etc.
  source_id     uuid        not null,      -- id from predictive_insights / faults...
  title         text        not null,
  summary       text        not null,
  severity      text        null,
  created_at    timestamptz not null default now()
);

create index if not exists idx_handover_items_yacht_created
  on public.handover_items (yacht_id, created_at desc);

-- 6. Minimal notifications table (for future mobile / web alerts)
create table if not exists public.notifications (
  id            uuid primary key default gen_random_uuid(),
  yacht_id      uuid        not null,
  user_id       uuid        null,         -- null = generic/HOD-level
  equipment_id  uuid        null,
  type          text        not null,     -- 'predictive_risk', etc.
  title         text        not null,
  body          text        not null,
  severity      text        not null,
  is_read       boolean     not null default false,
  created_at    timestamptz not null default now()
);

create index if not exists idx_notifications_yacht_created
  on public.notifications (yacht_id, created_at desc);

create index if not exists idx_notifications_user_read
  on public.notifications (user_id, is_read, created_at desc);
