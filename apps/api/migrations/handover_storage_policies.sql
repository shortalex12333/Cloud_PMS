-- Storage RLS Policies for handover-exports bucket
-- Run this via Supabase Dashboard SQL Editor (requires supabase_admin privileges)

-- Users can read exports from their own yacht
CREATE POLICY "Users read yacht handover exports"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'handover-exports'
    AND (storage.foldername(name))[1] = (
        SELECT (auth_users_profiles.yacht_id)::text
        FROM auth_users_profiles
        WHERE auth_users_profiles.id = auth.uid()
    )
);

-- Service role has full access for backend uploads
CREATE POLICY "Service role full access to handover exports"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'handover-exports')
WITH CHECK (bucket_id = 'handover-exports');
