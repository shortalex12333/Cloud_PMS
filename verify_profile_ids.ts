import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function verifyProfiles() {
  const db = createClient(TENANT_URL, TENANT_SERVICE_KEY);

  console.log('Verifying captain and chief engineer profile IDs...\n');

  // Check captain
  const { data: captain, error: captainError } = await db
    .from('auth_users_profiles')
    .select('*')
    .eq('email', 'captain.tenant@alex-short.com')
    .single();

  if (captainError) {
    console.error('❌ Captain query failed:', captainError);
  } else {
    console.log('Captain profile:');
    console.log(`  ID: ${captain.id}`);
    console.log(`  Email: ${captain.email}`);
    console.log(`  Expected ID: b72c35ff-e309-4a19-a617-bfc706a78c0f`);
    console.log(`  Match: ${captain.id === 'b72c35ff-e309-4a19-a617-bfc706a78c0f' ? '✅ YES' : '❌ NO'}\n`);
  }

  // Check chief engineer
  const { data: ce, error: ceError } = await db
    .from('auth_users_profiles')
    .select('*')
    .eq('email', 'hod.tenant@alex-short.com')
    .single();

  if (ceError) {
    console.error('❌ Chief Engineer query failed:', ceError);
  } else {
    console.log('Chief Engineer profile:');
    console.log(`  ID: ${ce.id}`);
    console.log(`  Email: ${ce.email}`);
    console.log(`  Expected ID: 89b1262c-ff59-4591-b954-757cdf3d609d`);
    console.log(`  Match: ${ce.id === '89b1262c-ff59-4591-b954-757cdf3d609d' ? '✅ YES' : '❌ NO'}\n`);
  }
}

verifyProfiles().catch(console.error);
