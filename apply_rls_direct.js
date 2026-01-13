#!/usr/bin/env node
/**
 * Apply Storage RLS Policy - Direct Execution
 * Uses Supabase SQL endpoint via fetch
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

const SQL_POLICY = `
CREATE POLICY IF NOT EXISTS "Users read yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);
`;

async function applyPolicy() {
  console.log('🔧 Attempting to apply RLS policy...\n');

  // Try method 1: Direct SQL execution via edge function
  console.log('Method 1: Trying edge function endpoint...');
  try {
    const response = await fetch(`${SUPABASE_URL}/functions/v1/sql`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY
      },
      body: JSON.stringify({ query: SQL_POLICY })
    });

    console.log('Status:', response.status);
    const data = await response.text();
    console.log('Response:', data);

    if (response.ok) {
      console.log('✅ SUCCESS via edge function!');
      return;
    }
  } catch (err) {
    console.log('❌ Edge function failed:', err.message);
  }

  // Try method 2: PostgREST query endpoint
  console.log('\nMethod 2: Trying PostgREST query endpoint...');
  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SERVICE_KEY}`,
        'apikey': SERVICE_KEY,
        'Prefer': 'return=representation'
      },
      body: JSON.stringify({ sql: SQL_POLICY })
    });

    console.log('Status:', response.status);
    const data = await response.json();
    console.log('Response:', JSON.stringify(data, null, 2));

    if (response.ok) {
      console.log('✅ SUCCESS via PostgREST!');
      return;
    }
  } catch (err) {
    console.log('❌ PostgREST failed:', err.message);
  }

  // Method 3: Show manual instructions
  console.log('\n' + '='.repeat(80));
  console.log('❌ Automatic execution failed');
  console.log('='.repeat(80));
  console.log('\n📋 MANUAL STEPS REQUIRED:\n');
  console.log('1. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new');
  console.log('\n2. Paste and run this SQL:\n');
  console.log(SQL_POLICY);
  console.log('\n3. You should see: "Success. No rows returned"\n');
  console.log('='.repeat(80));
}

applyPolicy().catch(console.error);
