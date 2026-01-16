import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

test.describe('Diagnostic: Test User Exists in TENANT Supabase', () => {
  test('Check if x@alex-short.com exists in TENANT auth.users', async () => {
    const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL;
    const TENANT_SUPABASE_SERVICE_ROLE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;

    console.log('========================================');
    console.log('DIAGNOSTIC: User Existence Check');
    console.log('========================================');
    console.log(`TENANT_SUPABASE_URL: ${TENANT_SUPABASE_URL}`);
    console.log(`TEST_USER_EMAIL: ${TEST_USER_EMAIL}`);

    // Create Supabase admin client
    const supabase = createClient(TENANT_SUPABASE_URL!, TENANT_SUPABASE_SERVICE_ROLE_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    console.log('\n--- Checking auth.users table ---');

    // Query auth.users for the test user
    const { data: authUsers, error: authError } = await supabase.auth.admin.listUsers();

    if (authError) {
      console.log(`❌ Error querying auth.users: ${authError.message}`);
      throw new Error(`Failed to query auth.users: ${authError.message}`);
    }

    console.log(`Total users in auth.users: ${authUsers.users.length}`);

    // Find test user
    const testUser = authUsers.users.find(u => u.email === TEST_USER_EMAIL);

    if (testUser) {
      console.log(`✅ SUCCESS: User ${TEST_USER_EMAIL} EXISTS in TENANT Supabase`);
      console.log(`   User ID: ${testUser.id}`);
      console.log(`   Created: ${testUser.created_at}`);
      console.log(`   Email confirmed: ${testUser.email_confirmed_at ? 'YES' : 'NO'}`);
      console.log(`   Last sign in: ${testUser.last_sign_in_at || 'Never'}`);

      expect(testUser).toBeTruthy();
      expect(testUser.email_confirmed_at, 'Email must be confirmed').toBeTruthy();
    } else {
      console.log(`❌ FAILURE: User ${TEST_USER_EMAIL} DOES NOT EXIST in TENANT Supabase`);
      console.log('\nAll users in TENANT Supabase:');
      authUsers.users.forEach(u => {
        console.log(`  - ${u.email} (created: ${u.created_at})`);
      });

      throw new Error(`Test user ${TEST_USER_EMAIL} does not exist in TENANT Supabase auth.users table`);
    }
  });

  test('Try to authenticate test user with password', async () => {
    const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL;
    const TENANT_SUPABASE_ANON_KEY = process.env.TENANT_SUPABASE_ANON_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;

    console.log('========================================');
    console.log('DIAGNOSTIC: Authentication Test');
    console.log('========================================');

    // Create client with anon key (like frontend does)
    const supabase = createClient(TENANT_SUPABASE_URL!, TENANT_SUPABASE_ANON_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    console.log('Attempting to sign in with password...');

    const { data, error } = await supabase.auth.signInWithPassword({
      email: TEST_USER_EMAIL!,
      password: TEST_USER_PASSWORD!,
    });

    if (error) {
      console.log(`❌ AUTHENTICATION FAILED: ${error.message}`);
      console.log(`   Error code: ${error.status}`);
      console.log(`   Full error:`, JSON.stringify(error, null, 2));

      if (error.message.includes('Invalid login credentials')) {
        console.log('\n⚠️  This means:');
        console.log('   1. User exists but password is wrong, OR');
        console.log('   2. User does not exist, OR');
        console.log('   3. Email is not confirmed');
      }

      throw new Error(`Authentication failed: ${error.message}`);
    }

    console.log(`✅ SUCCESS: Authentication succeeded!`);
    console.log(`   User ID: ${data.user?.id}`);
    console.log(`   Email: ${data.user?.email}`);
    console.log(`   Access token: ${data.session?.access_token?.substring(0, 50)}...`);

    expect(data.user).toBeTruthy();
    expect(data.session).toBeTruthy();
  });

  test('Check if user exists in MASTER Supabase (for comparison)', async () => {
    const MASTER_SUPABASE_URL = process.env.MASTER_SUPABASE_URL;
    const MASTER_SUPABASE_SERVICE_ROLE_KEY = process.env.MASTER_SUPABASE_SERVICE_ROLE_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;

    console.log('========================================');
    console.log('DIAGNOSTIC: MASTER DB User Check');
    console.log('========================================');

    const supabase = createClient(MASTER_SUPABASE_URL!, MASTER_SUPABASE_SERVICE_ROLE_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    const { data: authUsers, error: authError } = await supabase.auth.admin.listUsers();

    if (authError) {
      console.log(`Error querying MASTER auth.users: ${authError.message}`);
      throw new Error(`Failed to query MASTER auth.users: ${authError.message}`);
    }

    const testUser = authUsers.users.find(u => u.email === TEST_USER_EMAIL);

    if (testUser) {
      console.log(`✅ User ${TEST_USER_EMAIL} EXISTS in MASTER Supabase`);
      console.log(`   User ID: ${testUser.id}`);
      console.log(`   Created: ${testUser.created_at}`);
    } else {
      console.log(`❌ User ${TEST_USER_EMAIL} DOES NOT EXIST in MASTER Supabase`);
    }
  });
});
