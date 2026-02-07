--
-- Search Role Bias Schema Upgrade
-- Adds object_type, bias_weight, is_active columns for clean v2 RPC usage
-- Backfills from legacy doc_type/bias columns
--

-- 1. Add new columns
ALTER TABLE public.search_role_bias ADD COLUMN IF NOT EXISTS object_type TEXT;
ALTER TABLE public.search_role_bias ADD COLUMN IF NOT EXISTS bias_weight NUMERIC DEFAULT 0.0;
ALTER TABLE public.search_role_bias ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- 2. Backfill object_type from lens (when lens matches object_type patterns)
UPDATE public.search_role_bias
SET object_type = CASE
    WHEN lens IN ('work_order', 'wo') THEN 'work_order'
    WHEN lens IN ('equipment', 'asset') THEN 'equipment'
    WHEN lens IN ('part', 'component') THEN 'part'
    WHEN lens = 'document' AND doc_type IS NOT NULL THEN 'document'
    WHEN lens = 'fault' THEN 'fault'
    WHEN lens = 'certificate' THEN 'certificate'
    ELSE lens
END
WHERE object_type IS NULL;

-- 3. Backfill bias_weight from bias
UPDATE public.search_role_bias
SET bias_weight = bias
WHERE bias_weight = 0.0 AND bias != 0.0;

-- 4. Set is_active = true for all existing rows
UPDATE public.search_role_bias
SET is_active = TRUE
WHERE is_active IS NULL;

-- 5. Add index for efficient lookup in RPC
CREATE INDEX IF NOT EXISTS idx_search_role_bias_lookup
ON public.search_role_bias (role, object_type, is_active)
WHERE is_active = TRUE;

-- 6. Add comments
COMMENT ON COLUMN public.search_role_bias.object_type IS 'Object type for L2.5 linking (work_order, equipment, part, etc.)';
COMMENT ON COLUMN public.search_role_bias.bias_weight IS 'Bias weight to apply to S_bias score (0.0-1.0)';
COMMENT ON COLUMN public.search_role_bias.is_active IS 'Whether this bias rule is active (for soft delete)';

-- 7. Seed additional role biases for L2.5 linking targets if not exists
INSERT INTO public.search_role_bias (role, lens, object_type, bias_weight, is_active)
VALUES
    -- Chief Engineer role biases for L2.5
    ('chief_engineer', 'work_order', 'work_order', 0.15, TRUE),
    ('chief_engineer', 'equipment', 'equipment', 0.10, TRUE),
    ('chief_engineer', 'part', 'part', 0.10, TRUE),
    ('chief_engineer', 'fault', 'fault', 0.15, TRUE),
    -- ETO role biases
    ('eto', 'work_order', 'work_order', 0.12, TRUE),
    ('eto', 'equipment', 'equipment', 0.15, TRUE),
    ('eto', 'part', 'part', 0.12, TRUE),
    -- Captain role biases for L2.5
    ('captain', 'work_order', 'work_order', 0.05, TRUE),
    ('captain', 'equipment', 'equipment', 0.05, TRUE),
    ('captain', 'certificate', 'certificate', 0.20, TRUE),
    -- Manager role biases
    ('manager', 'work_order', 'work_order', 0.10, TRUE),
    ('manager', 'part', 'part', 0.08, TRUE),
    ('manager', 'purchase_order', 'purchase_order', 0.15, TRUE)
ON CONFLICT (role, lens, doc_type, part_type) DO NOTHING;
