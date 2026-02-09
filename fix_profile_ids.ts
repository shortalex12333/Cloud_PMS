import { createClient } from '@supabase/supabase-js';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function fixProfiles() {
  const db = createClient(TENANT_URL, TENANT_SERVICE_KEY);

  console.log('Fixing profile IDs to match master auth database...\n');

  // Step 1: Delete old captain profile
  console.log('1. Deleting old captain profile...');
  const { error: deleteCaptainError } = await db
    .from('auth_users_profiles')
    .delete()
    .eq('email', 'captain.tenant@alex-short.com');

  if (deleteCaptainError) {
    console.error('❌ Delete captain failed:', deleteCaptainError);
  } else {
    console.log('✅ Old captain profile deleted');
  }

  // Step 2: Delete old chief engineer profile
  console.log('2. Deleting old chief engineer profile...');
  const { error: deleteCEError } = await db
    .from('auth_users_profiles')
    .delete()
    .eq('email', 'hod.tenant@alex-short.com');

  if (deleteCEError) {
    console.error('❌ Delete chief engineer failed:', deleteCEError);
  } else {
    console.log('✅ Old chief engineer profile deleted');
  }

  // Step 3: Insert new captain profile with correct ID
  console.log('\n3. Inserting captain with correct ID...');
  const { error: insertCaptainError } = await db
    .from('auth_users_profiles')
    .insert({
      id: 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
      yacht_id: YACHT_ID,
      email: 'captain.tenant@alex-short.com',
      name: 'Captain Test',
      is_active: true,
    });

  if (insertCaptainError) {
    console.error('❌ Insert captain failed:', insertCaptainError);
  } else {
    console.log('✅ Captain profile created with correct ID');
  }

  // Step 4: Insert new chief engineer profile with correct ID
  console.log('4. Inserting chief engineer with correct ID...');
  const { error: insertCEError } = await db
    .from('auth_users_profiles')
    .insert({
      id: '89b1262c-ff59-4591-b954-757cdf3d609d',
      yacht_id: YACHT_ID,
      email: 'hod.tenant@alex-short.com',
      name: 'Chief Engineer Test',
      is_active: true,
    });

  if (insertCEError) {
    console.error('❌ Insert chief engineer failed:', insertCEError);
  } else {
    console.log('✅ Chief Engineer profile created with correct ID');
  }

  // Step 5: Verify
  console.log('\n=== Verification ===');
  const { data: captain } = await db
    .from('auth_users_profiles')
    .select('id, email')
    .eq('email', 'captain.tenant@alex-short.com')
    .single();

  const { data: ce } = await db
    .from('auth_users_profiles')
    .select('id, email')
    .eq('email', 'hod.tenant@alex-short.com')
    .single();

  console.log(`Captain: ${captain?.id} (expected: b72c35ff-e309-4a19-a617-bfc706a78c0f)`);
  console.log(`Match: ${captain?.id === 'b72c35ff-e309-4a19-a617-bfc706a78c0f' ? '✅' : '❌'}`);

  console.log(`Chief Engineer: ${ce?.id} (expected: 89b1262c-ff59-4591-b954-757cdf3d609d)`);
  console.log(`Match: ${ce?.id === '89b1262c-ff59-4591-b954-757cdf3d609d' ? '✅' : '❌'}`);
}

fixProfiles().catch(console.error);
