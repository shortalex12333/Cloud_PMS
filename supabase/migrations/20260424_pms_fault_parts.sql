-- pms_fault_parts: junction table linking faults to spare parts
-- Applied to TENANT DB (vzsohavtuotocgrfkfyd) — see applier note below.
-- psql "postgresql://postgres.vzsohavtuotocgrfkfyd:<PASSWORD>@aws-0-eu-west-2.pooler.supabase.com:6543/postgres" \
--      -f supabase/migrations/20260424_pms_fault_parts.sql

CREATE TABLE IF NOT EXISTS public.pms_fault_parts (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fault_id    uuid NOT NULL REFERENCES public.pms_faults(id) ON DELETE CASCADE,
    part_id     uuid NOT NULL REFERENCES public.pms_parts(id) ON DELETE CASCADE,
    linked_by   uuid NOT NULL REFERENCES auth.users(id),
    notes       text,
    created_at  timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (fault_id, part_id)
);

-- RLS: yacht-scoped via fault_id → pms_faults.yacht_id
ALTER TABLE public.pms_fault_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "crew_can_view_fault_parts" ON public.pms_fault_parts
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.pms_faults f
            JOIN public.crew_roles cr ON cr.yacht_id = f.yacht_id
            WHERE f.id = pms_fault_parts.fault_id
              AND cr.user_id = auth.uid()
        )
    );

CREATE POLICY "engineers_can_link_parts" ON public.pms_fault_parts
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.pms_faults f
            JOIN public.crew_roles cr ON cr.yacht_id = f.yacht_id
            WHERE f.id = pms_fault_parts.fault_id
              AND cr.user_id = auth.uid()
              AND cr.role IN ('engineer','eto','chief_engineer','chief_officer','captain','manager')
        )
    );

CREATE POLICY "engineers_can_unlink_parts" ON public.pms_fault_parts
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.pms_faults f
            JOIN public.crew_roles cr ON cr.yacht_id = f.yacht_id
            WHERE f.id = pms_fault_parts.fault_id
              AND cr.user_id = auth.uid()
              AND cr.role IN ('engineer','eto','chief_engineer','chief_officer','captain','manager')
        )
    );

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fault_parts_fault_id ON public.pms_fault_parts(fault_id);
CREATE INDEX IF NOT EXISTS idx_fault_parts_part_id ON public.pms_fault_parts(part_id);
