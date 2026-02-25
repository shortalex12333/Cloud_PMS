-- Migration: Add learned_keywords column to search_index
-- Description: Adds JSONB column to store learned query variations for adversarial learning
-- Idempotent: Safe to run multiple times

-- Add learned_keywords column if it doesn't exist
ALTER TABLE public.search_index
ADD COLUMN IF NOT EXISTS learned_keywords JSONB DEFAULT '[]'::jsonb;

-- Add index for efficient querying of learned keywords
CREATE INDEX IF NOT EXISTS idx_search_index_learned_keywords
    ON public.search_index USING GIN (learned_keywords);

-- Add comment
COMMENT ON COLUMN public.search_index.learned_keywords IS
'Learned query variations from counterfactual feedback loop (misspellings, semantic descriptions, colloquial terms)';

-- Verify the column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'search_index'
        AND column_name = 'learned_keywords'
    ) THEN
        RAISE NOTICE '✅ learned_keywords column exists';
    ELSE
        RAISE EXCEPTION '❌ learned_keywords column was not created';
    END IF;
END $$;

-- Example usage:
-- Update a single entity with learned keywords
/*
UPDATE public.search_index
SET learned_keywords = jsonb_build_array(
    'genrator',
    'gennie',
    'genset'
)
WHERE object_type = 'equipment'
AND search_text ILIKE '%generator%'
LIMIT 1;
*/

-- Query entities with learned keywords
/*
SELECT
    object_type,
    payload->>'name' as name,
    learned_keywords
FROM public.search_index
WHERE learned_keywords IS NOT NULL
AND jsonb_array_length(learned_keywords) > 0
LIMIT 10;
*/
