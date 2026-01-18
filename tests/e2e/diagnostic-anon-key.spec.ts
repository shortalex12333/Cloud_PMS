import { test, expect } from '@playwright/test';

// Skip: Requires real TENANT_SUPABASE_ANON_KEY (currently placeholder)
test.describe.skip('Diagnostic: Supabase Anon Key Validation', () => {
  test('Verify TENANT_SUPABASE_ANON_KEY can authenticate', async ({ page }) => {
    const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL;
    const TENANT_SUPABASE_ANON_KEY = process.env.TENANT_SUPABASE_ANON_KEY;
    const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;
    const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD;

    console.log('========================================');
    console.log('DIAGNOSTIC: Testing Supabase Anon Key');
    console.log('========================================');
    console.log(`TENANT_SUPABASE_URL: ${TENANT_SUPABASE_URL}`);
    console.log(`TENANT_SUPABASE_ANON_KEY (first 50 chars): ${TENANT_SUPABASE_ANON_KEY?.substring(0, 50)}...`);
    console.log(`TEST_USER_EMAIL: ${TEST_USER_EMAIL}`);

    // Decode the JWT to see what's inside
    if (TENANT_SUPABASE_ANON_KEY) {
      const parts = TENANT_SUPABASE_ANON_KEY.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
        console.log('JWT Payload:', JSON.stringify(payload, null, 2));
      }
    }

    // Test 1: Direct API call with anon key
    console.log('\n--- Test 1: Direct Supabase Auth API Call ---');
    const response = await fetch(`${TENANT_SUPABASE_URL}/auth/v1/token?grant_type=password`, {
      method: 'POST',
      headers: {
        'apikey': TENANT_SUPABASE_ANON_KEY!,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: TEST_USER_EMAIL,
        password: TEST_USER_PASSWORD,
      }),
    });

    const responseText = await response.text();
    console.log(`Response Status: ${response.status} ${response.statusText}`);
    console.log(`Response Body: ${responseText.substring(0, 200)}`);

    if (response.ok) {
      console.log('✅ SUCCESS: Anon key is VALID and can authenticate');
      const data = JSON.parse(responseText);
      expect(data.access_token).toBeTruthy();
    } else {
      console.log('❌ FAILURE: Anon key is INVALID or cannot authenticate');
      console.log('Full response:', responseText);

      // Test with service role key as comparison
      console.log('\n--- Test 2: Try with SERVICE_ROLE_KEY for comparison ---');
      const serviceRoleKey = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;
      const serviceResponse = await fetch(`${TENANT_SUPABASE_URL}/auth/v1/token?grant_type=password`, {
        method: 'POST',
        headers: {
          'apikey': serviceRoleKey!,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: TEST_USER_EMAIL,
          password: TEST_USER_PASSWORD,
        }),
      });

      const serviceText = await serviceResponse.text();
      console.log(`Service Key Response: ${serviceResponse.status} ${serviceResponse.statusText}`);
      console.log(`Service Key Body: ${serviceText.substring(0, 200)}`);

      throw new Error(`Anon key failed: ${responseText}`);
    }
  });

  test('Verify GitHub Actions TENANT_SUPABASE_ANON_KEY secret exists', async () => {
    const anonKey = process.env.TENANT_SUPABASE_ANON_KEY;

    console.log('========================================');
    console.log('DIAGNOSTIC: GitHub Secret Check');
    console.log('========================================');
    console.log(`TENANT_SUPABASE_ANON_KEY exists: ${!!anonKey}`);
    console.log(`TENANT_SUPABASE_ANON_KEY length: ${anonKey?.length || 0}`);

    expect(anonKey, 'TENANT_SUPABASE_ANON_KEY must be set').toBeTruthy();
    expect(anonKey?.length, 'TENANT_SUPABASE_ANON_KEY must be non-empty').toBeGreaterThan(0);

    // Decode and check role
    if (anonKey) {
      const parts = anonKey.split('.');
      expect(parts.length, 'TENANT_SUPABASE_ANON_KEY must be valid JWT').toBe(3);

      const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
      console.log(`JWT role: ${payload.role}`);
      console.log(`JWT ref: ${payload.ref}`);

      expect(payload.role, 'JWT role must be "anon", not "service_role"').toBe('anon');
    }
  });
});
