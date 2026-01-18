import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';

// Skip: Requires real TENANT credentials (currently placeholder)
test.describe.skip('Diagnostic: RPC Function Location', () => {
  test('Check if get_my_bootstrap exists in TENANT Supabase', async () => {
    const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL;
    const TENANT_SUPABASE_SERVICE_ROLE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;

    console.log('========================================');
    console.log('DIAGNOSTIC: TENANT RPC Check');
    console.log('========================================');
    console.log(`TENANT_SUPABASE_URL: ${TENANT_SUPABASE_URL}`);

    const supabase = createClient(TENANT_SUPABASE_URL!, TENANT_SUPABASE_SERVICE_ROLE_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    // First authenticate
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: TEST_USER_EMAIL!,
      password: TEST_USER_PASSWORD!,
    });

    if (authError) {
      console.log(`⚠️  Auth failed in TENANT: ${authError.message}`);
      throw new Error(`Auth failed: ${authError.message}`);
    }

    console.log(`✅ Authenticated in TENANT Supabase`);

    // Try to call get_my_bootstrap
    console.log('\nTrying to call get_my_bootstrap RPC...');

    const { data: bootstrapData, error: bootstrapError } = await supabase.rpc('get_my_bootstrap');

    if (bootstrapError) {
      console.log(`❌ TENANT RPC FAILED: ${bootstrapError.message}`);
      console.log(`   Error code: ${bootstrapError.code}`);
      console.log(`   Error hint: ${bootstrapError.hint || 'N/A'}`);

      if (bootstrapError.message.includes('function') || bootstrapError.code === '42883') {
        console.log('\n🔍 DIAGNOSIS:');
        console.log('   get_my_bootstrap RPC does NOT exist in TENANT Supabase');
        console.log('   This explains why login hangs - bootstrap never completes!');
        console.log('\n📋 THE ISSUE:');
        console.log('   - Frontend uses TENANT Supabase (NEXT_PUBLIC_SUPABASE_URL)');
        console.log('   - But get_my_bootstrap RPC is in MASTER Supabase');
        console.log('   - After login, bootstrap tries to call non-existent RPC');
        console.log('   - Call fails/hangs → user never redirects');
      }

      throw new Error(`get_my_bootstrap does not exist in TENANT Supabase`);
    }

    console.log(`✅ TENANT RPC succeeded!`);
    console.log(`   Response:`, JSON.stringify(bootstrapData, null, 2));
  });

  test('Verify get_my_bootstrap exists in MASTER Supabase', async () => {
    const MASTER_SUPABASE_URL = process.env.MASTER_SUPABASE_URL;
    const MASTER_SUPABASE_ANON_KEY = process.env.MASTER_SUPABASE_ANON_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;

    console.log('========================================');
    console.log('DIAGNOSTIC: MASTER RPC Check');
    console.log('========================================');
    console.log(`MASTER_SUPABASE_URL: ${MASTER_SUPABASE_URL}`);

    const supabase = createClient(MASTER_SUPABASE_URL!, MASTER_SUPABASE_ANON_KEY!, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    // Authenticate
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: TEST_USER_EMAIL!,
      password: TEST_USER_PASSWORD!,
    });

    if (authError) {
      throw new Error(`Auth failed: ${authError.message}`);
    }

    console.log(`✅ Authenticated in MASTER Supabase`);

    // Call get_my_bootstrap
    console.log('\nCalling get_my_bootstrap RPC...');

    const { data: bootstrapData, error: bootstrapError } = await supabase.rpc('get_my_bootstrap');

    if (bootstrapError) {
      console.log(`❌ MASTER RPC FAILED: ${bootstrapError.message}`);
      throw new Error(`get_my_bootstrap failed in MASTER: ${bootstrapError.message}`);
    }

    console.log(`✅ MASTER RPC succeeded!`);
    console.log(`   Response:`, JSON.stringify(bootstrapData, null, 2));

    expect(bootstrapData).toBeTruthy();
    expect(bootstrapData.yacht_id).toBeTruthy();
  });
});
