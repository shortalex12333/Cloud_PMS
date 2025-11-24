-- 001_enable_pg_net_and_predictive_tables.sql
-- NOTE: predictive_state, predictive_insights, handover_items ALREADY EXIST
-- This migration only adds MISSING elements

-- 1. Enable HTTP extension (Supabase: pg_net) for trigger HTTP calls
create extension if not exists pg_net;

-- 2. Add unique constraint on predictive_state for UPSERT operations
-- The workflow uses ON CONFLICT (yacht_id, equipment_id)
create unique index if not exists idx_predictive_state_yacht_equipment
  on public.predictive_state (yacht_id, equipment_id);

-- 3. Add attention_flag column to equipment (if not exists)
alter table public.equipment
  add column if not exists attention_flag boolean default false;

alter table public.equipment
  add column if not exists attention_reason text;

alter table public.equipment
  add column if not exists attention_updated_at timestamptz;

create index if not exists idx_equipment_attention_flag
  on public.equipment (attention_flag) where attention_flag = true;

-- 4. Create notifications table (does not exist)
create table if not exists public.notifications (
  id            uuid primary key default gen_random_uuid(),
  yacht_id      uuid        not null,
  user_id       uuid        null,
  equipment_id  uuid        null,
  type          text        not null,     -- 'risk_alert', 'maintenance_due', etc.
  title         text        not null,
  message       text        not null,
  priority      text        not null default 'normal',  -- 'critical', 'high', 'normal', 'low'
  metadata      jsonb       default '{}'::jsonb,
  is_read       boolean     not null default false,
  read_at       timestamptz null,
  created_at    timestamptz not null default now()
);

create index if not exists idx_notifications_yacht_created
  on public.notifications (yacht_id, created_at desc);

create index if not exists idx_notifications_user_unread
  on public.notifications (user_id, is_read, created_at desc)
  where is_read = false;

-- 5. Create search_suggestions table (does not exist)
create table if not exists public.search_suggestions (
  id              uuid primary key default gen_random_uuid(),
  yacht_id        uuid        not null,
  equipment_id    uuid        null,
  suggestion_text text        not null,
  priority        integer     not null default 0,  -- higher = more prominent
  category        text        not null,            -- 'predictive_alert', 'recent', etc.
  metadata        jsonb       default '{}'::jsonb,
  expires_at      timestamptz null,
  created_at      timestamptz not null default now()
);

create index if not exists idx_search_suggestions_yacht_priority
  on public.search_suggestions (yacht_id, priority desc, created_at desc);

create index if not exists idx_search_suggestions_expires
  on public.search_suggestions (expires_at)
  where expires_at is not null;
