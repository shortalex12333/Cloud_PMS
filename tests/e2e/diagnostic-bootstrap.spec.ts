import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

test.describe('Diagnostic: Bootstrap Flow', () => {
  test('Check if get_my_bootstrap RPC works', async () => {
    const MASTER_SUPABASE_URL = process.env.MASTER_SUPABASE_URL;
    const MASTER_SUPABASE_ANON_KEY = process.env.MASTER_SUPABASE_ANON_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;

    console.log('========================================');
    console.log('DIAGNOSTIC: Bootstrap RPC Test');
    console.log('========================================');

    // Step 1: Authenticate to get session
    const supabase = createClient(MASTER_SUPABASE_URL!, MASTER_SUPABASE_ANON_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    console.log('Step 1: Authenticating...');
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: TEST_USER_EMAIL!,
      password: TEST_USER_PASSWORD!,
    });

    if (authError) {
      console.log(`❌ Auth failed: ${authError.message}`);
      throw new Error(`Authentication failed: ${authError.message}`);
    }

    console.log(`✅ Authenticated as ${authData.user.email}`);
    console.log(`   Access token: ${authData.session.access_token.substring(0, 50)}...`);

    // Step 2: Call get_my_bootstrap RPC
    console.log('\nStep 2: Calling get_my_bootstrap RPC...');

    const { data: bootstrapData, error: bootstrapError } = await supabase.rpc('get_my_bootstrap');

    if (bootstrapError) {
      console.log(`❌ Bootstrap RPC failed: ${bootstrapError.message}`);
      console.log(`   Error code: ${bootstrapError.code}`);
      console.log(`   Full error:`, JSON.stringify(bootstrapError, null, 2));
      throw new Error(`get_my_bootstrap failed: ${bootstrapError.message}`);
    }

    console.log(`✅ Bootstrap RPC succeeded!`);
    console.log(`   Response:`, JSON.stringify(bootstrapData, null, 2));

    // Validate bootstrap data structure
    expect(bootstrapData, 'Bootstrap data should exist').toBeTruthy();
    expect(bootstrapData.yacht_id, 'Should have yacht_id').toBeTruthy();
    expect(bootstrapData.tenant_key_alias, 'Should have tenant_key_alias').toBeTruthy();

    console.log('\n✅ All bootstrap checks passed');
    console.log(`   Yacht ID: ${bootstrapData.yacht_id}`);
    console.log(`   Tenant Key: ${bootstrapData.tenant_key_alias}`);
    console.log(`   Bootstrap Status: ${bootstrapData.bootstrap_status || 'N/A'}`);
  });

  test('Simulate full login + bootstrap flow', async () => {
    const MASTER_SUPABASE_URL = process.env.MASTER_SUPABASE_URL;
    const MASTER_SUPABASE_ANON_KEY = process.env.MASTER_SUPABASE_ANON_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;
    const TEST_USER_YACHT_ID = process.env.TEST_USER_YACHT_ID;

    console.log('========================================');
    console.log('DIAGNOSTIC: Full Login Flow Simulation');
    console.log('========================================');

    const supabase = createClient(MASTER_SUPABASE_URL!, MASTER_SUPABASE_ANON_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    // Step 1: Login
    console.log('Step 1: Login...');
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: TEST_USER_EMAIL!,
      password: TEST_USER_PASSWORD!,
    });

    expect(authError, 'Login should succeed').toBeNull();
    console.log(`✅ Login succeeded`);

    // Step 2: Get bootstrap
    console.log('\nStep 2: Get bootstrap...');
    const { data: bootstrapData, error: bootstrapError } = await supabase.rpc('get_my_bootstrap');

    expect(bootstrapError, 'Bootstrap should succeed').toBeNull();
    console.log(`✅ Bootstrap succeeded`);

    // Step 3: Verify yacht_id matches
    console.log('\nStep 3: Verify yacht_id...');
    console.log(`   Expected: ${TEST_USER_YACHT_ID}`);
    console.log(`   Received: ${bootstrapData.yacht_id}`);

    expect(bootstrapData.yacht_id).toBe(TEST_USER_YACHT_ID);
    console.log(`✅ Yacht ID matches`);

    // Step 4: Check if yacht is active
    console.log('\nStep 4: Check yacht status...');
    const bootstrapStatus = bootstrapData.bootstrap_status;
    const yachtName = bootstrapData.yacht_name;

    console.log(`   Bootstrap Status: ${bootstrapStatus || 'active (default)'}`);
    console.log(`   Yacht Name: ${yachtName || 'N/A'}`);

    if (bootstrapStatus === 'pending') {
      console.log('⚠️  WARNING: Bootstrap status is PENDING');
      console.log('   This means user account is not activated yet');
      console.log('   Login page will show "Awaiting Activation" screen');
      throw new Error('Bootstrap status is pending - user not activated');
    }

    if (bootstrapStatus === 'inactive') {
      console.log('⚠️  WARNING: Bootstrap status is INACTIVE');
      console.log('   This means yacht is not active');
      console.log('   Login page will show "Yacht Inactive" screen');
      throw new Error('Bootstrap status is inactive - yacht not active');
    }

    console.log(`✅ Bootstrap status is OK (user should be able to access app)`);

    // Summary
    console.log('\n========================================');
    console.log('SIMULATION SUMMARY');
    console.log('========================================');
    console.log(`✅ Login: SUCCESS`);
    console.log(`✅ Bootstrap: SUCCESS`);
    console.log(`✅ Yacht ID: ${bootstrapData.yacht_id}`);
    console.log(`✅ Tenant Key: ${bootstrapData.tenant_key_alias}`);
    console.log(`✅ Status: ${bootstrapStatus || 'active'}`);
    console.log(`\n👍 User should be able to login and access app`);
  });
});
