import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function seedUsers() {
  const db = createClient(TENANT_URL, TENANT_SERVICE_KEY);

  console.log('Inserting test users into users table...\n');

  // Captain
  const { error: captainError } = await db
    .from('users')
    .upsert({
      id: 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
      yacht_id: YACHT_ID,
      email: 'captain.tenant@alex-short.com',
      name: 'Captain Test',
      role: 'captain',
      status: 'active',
    }, { onConflict: 'id' });

  if (captainError) {
    console.error('❌ Captain insert failed:', captainError);
  } else {
    console.log('✅ Captain inserted into users table');
  }

  // Chief Engineer
  const { error: ceError } = await db
    .from('users')
    .upsert({
      id: '89b1262c-ff59-4591-b954-757cdf3d609d',
      yacht_id: YACHT_ID,
      email: 'hod.tenant@alex-short.com',
      name: 'Chief Engineer Test',
      role: 'chief_engineer',
      status: 'active',
    }, { onConflict: 'id' });

  if (ceError) {
    console.error('❌ Chief Engineer insert failed:', ceError);
  } else {
    console.log('✅ Chief Engineer inserted into users table');
  }

  // Verify
  console.log('\n=== Verification ===');
  const { data: users } = await db
    .from('users')
    .select('id, email, name')
    .in('id', ['b72c35ff-e309-4a19-a617-bfc706a78c0f', '89b1262c-ff59-4591-b954-757cdf3d609d']);

  if (users) {
    console.log(`Found ${users.length} users:`);
    users.forEach((u: any) => {
      console.log(`  - ${u.email} (${u.id})`);
    });
  }
}

seedUsers().catch(console.error);
