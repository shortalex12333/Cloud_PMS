import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function seedProfiles() {
  const db = createClient(TENANT_URL, TENANT_SERVICE_KEY);
  const yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

  console.log('Inserting test user profiles into tenant database...\n');

  // Captain profile
  const captain = {
    id: 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
    yacht_id: yacht_id,
    email: 'captain.tenant@alex-short.com',
    name: 'Captain Test',
    is_active: true,
  };

  const { data: captainData, error: captainError } = await db
    .from('auth_users_profiles')
    .upsert(captain, { onConflict: 'id' })
    .select();

  if (captainError) {
    console.error('❌ Captain insert failed:', captainError);
  } else {
    console.log('✅ Captain profile inserted:', captain.email);
  }

  // Chief Engineer profile
  const chiefEngineer = {
    id: '89b1262c-ff59-4591-b954-757cdf3d609d',
    yacht_id: yacht_id,
    email: 'hod.tenant@alex-short.com',
    name: 'Chief Engineer Test',
    is_active: true,
  };

  const { data: ceData, error: ceError } = await db
    .from('auth_users_profiles')
    .upsert(chiefEngineer, { onConflict: 'id' })
    .select();

  if (ceError) {
    console.error('❌ Chief Engineer insert failed:', ceError);
  } else {
    console.log('✅ Chief Engineer profile inserted:', chiefEngineer.email);
  }

  // Verify
  console.log('\n=== Verification ===');
  const { data: profiles, error: verifyError } = await db
    .from('auth_users_profiles')
    .select('id, email, name')
    .eq('yacht_id', yacht_id);

  if (verifyError) {
    console.error('❌ Verification failed:', verifyError);
  } else {
    console.log(`Found ${profiles?.length || 0} profiles:`);
    profiles?.forEach((p: any) => {
      console.log(`  - ${p.email} (${p.user_id})`);
    });
  }
}

seedProfiles().catch(console.error);
