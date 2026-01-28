-- Migration: Create pms_entity_links (deterministic relatedness links)

begin;

create table if not exists public.pms_entity_links (
  id uuid primary key default gen_random_uuid(),
  yacht_id uuid not null,
  source_entity_type text not null,
  source_entity_id uuid not null,
  target_entity_type text not null,
  target_entity_id uuid not null,
  link_type text not null default 'related',
  note text,
  created_by uuid not null,
  created_at timestamptz not null default now()
);

alter table public.pms_entity_links enable row level security;

create index if not exists idx_links_yacht_source on public.pms_entity_links (yacht_id, source_entity_type, source_entity_id);
create index if not exists idx_links_yacht_target on public.pms_entity_links (yacht_id, target_entity_type, target_entity_id);

-- RLS: deny by default
-- Note: is_hod() and is_manager() use no args (get context from auth.uid())
do $$ begin
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='pms_entity_links' and policyname='links_select_same_yacht'
  ) then
    create policy links_select_same_yacht on public.pms_entity_links
      for select using (yacht_id = public.get_user_yacht_id());
  end if;
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='pms_entity_links' and policyname='links_insert_hod_or_manager'
  ) then
    create policy links_insert_hod_or_manager on public.pms_entity_links
      for insert with check (
        yacht_id = public.get_user_yacht_id()
        and (public.is_hod(auth.uid(), public.get_user_yacht_id()) or public.is_manager(auth.uid(), public.get_user_yacht_id()))
      );
  end if;
  if not exists (
    select 1 from pg_policies where schemaname='public' and tablename='pms_entity_links' and policyname='links_delete_hod_or_manager'
  ) then
    create policy links_delete_hod_or_manager on public.pms_entity_links
      for delete using (
        yacht_id = public.get_user_yacht_id()
        and (public.is_hod(auth.uid(), public.get_user_yacht_id()) or public.is_manager(auth.uid(), public.get_user_yacht_id()))
      );
  end if;
end $$;

commit;
