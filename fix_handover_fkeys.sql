-- Fix handover_items foreign key constraints
-- Run this on TENANT DB: vzsohavtuotocgrfkfyd.supabase.co

-- Drop the incorrect foreign key that references non-existent 'users' table
ALTER TABLE handover_items DROP CONSTRAINT IF EXISTS handover_items_finalized_by_fkey;

-- Add correct foreign key referencing auth_users_profiles
ALTER TABLE handover_items
ADD CONSTRAINT handover_items_finalized_by_fkey
FOREIGN KEY (finalized_by) REFERENCES auth_users_profiles(id);

-- Verify constraints
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table,
    a.attname AS column_name,
    af.attname AS referenced_column
FROM pg_constraint c
JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
JOIN pg_attribute af ON af.attnum = ANY(c.confkey) AND af.attrelid = c.confrelid
WHERE conrelid = 'handover_items'::regclass
  AND confrelid IS NOT NULL
ORDER BY conname;
