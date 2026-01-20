/**
 * B001 Regression Test: JWT Verification Secret Priority
 *
 * This test ensures that the backend uses MASTER Supabase JWT secret first,
 * not TENANT secret. This is critical because:
 *
 * 1. Frontend authenticates against MASTER Supabase (qvzmkaamzaqxpzbewjxe.supabase.co)
 * 2. MASTER Supabase signs JWTs with its own secret
 * 3. Backend must verify with MASTER secret first
 *
 * If this test fails, the site will be completely broken (B001 regression).
 *
 * Fix commit: a19afcf
 */

import { test, expect } from '@playwright/test';

// Environment configuration
const MASTER_SUPABASE_URL = process.env.MASTER_SUPABASE_URL || 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_SUPABASE_ANON_KEY = process.env.MASTER_SUPABASE_ANON_KEY || '';
const PIPELINE_URL = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const TEST_EMAIL = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
const TEST_PASSWORD = process.env.TEST_USER_PASSWORD || 'Password2!';

test.describe('B001 Regression: JWT Verification Priority', () => {
  let accessToken: string;

  test.beforeAll(async ({ request }) => {
    // Get JWT from MASTER Supabase
    const loginResponse = await request.post(
      `${MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password`,
      {
        headers: {
          'apikey': MASTER_SUPABASE_ANON_KEY,
          'Content-Type': 'application/json',
        },
        data: {
          email: TEST_EMAIL,
          password: TEST_PASSWORD,
        },
      }
    );

    expect(loginResponse.ok(), 'Login to MASTER Supabase should succeed').toBeTruthy();

    const loginData = await loginResponse.json();
    accessToken = loginData.access_token;
    expect(accessToken, 'Should receive access token from MASTER Supabase').toBeTruthy();
  });

  test('GATE-B001-001: Bootstrap accepts MASTER Supabase JWT', async ({ request }) => {
    /**
     * This is the critical test for B001.
     *
     * If bootstrap returns 401 "Signature verification failed", it means
     * the backend is NOT using MASTER_SUPABASE_JWT_SECRET first.
     *
     * Expected: 200 OK with yacht_id
     * Failure mode: 401 "Invalid token: Signature verification failed"
     */
    const response = await request.post(`${PIPELINE_URL}/v1/bootstrap`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    // This is the key assertion
    expect(
      response.status(),
      'Bootstrap must accept MASTER Supabase JWT (B001 regression check)'
    ).toBe(200);

    const data = await response.json();

    // Verify response structure
    expect(data.yacht_id, 'Response must include yacht_id').toBeTruthy();
    expect(data.user_id, 'Response must include user_id').toBeTruthy();
    expect(data.role, 'Response must include role').toBeTruthy();
  });

  test('GATE-B001-002: Search accepts MASTER Supabase JWT', async ({ request }) => {
    /**
     * Secondary verification: Search endpoint also requires JWT verification.
     * If this fails with 401, B001 has regressed.
     */
    const response = await request.post(`${PIPELINE_URL}/webhook/search`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        query: 'test',
      },
    });

    expect(
      response.status(),
      'Search must accept MASTER Supabase JWT (B001 regression check)'
    ).toBe(200);

    const data = await response.json();
    expect(data.success, 'Search response must indicate success').toBe(true);
  });

  test('GATE-B001-003: Verify JWT issuer is MASTER', async () => {
    /**
     * Verify that the JWT we're testing with is actually from MASTER Supabase.
     * This ensures our test is valid.
     */
    // Decode JWT payload (no verification, just extract claims)
    const parts = accessToken.split('.');
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());

    expect(
      payload.iss,
      'JWT must be issued by MASTER Supabase'
    ).toContain('qvzmkaamzaqxpzbewjxe.supabase.co');
  });

  test('GATE-B001-004: Expired/invalid JWT is rejected (negative control)', async ({ request }) => {
    /**
     * Verify that invalid JWTs are still rejected.
     * This ensures the verification is actually happening.
     */
    const response = await request.post(`${PIPELINE_URL}/v1/bootstrap`, {
      headers: {
        'Authorization': 'Bearer invalid.jwt.token',
        'Content-Type': 'application/json',
      },
    });

    expect(
      response.status(),
      'Invalid JWT should be rejected with 401'
    ).toBe(401);
  });

  test('GATE-B001-005: Missing Authorization header is rejected', async ({ request }) => {
    /**
     * Verify that requests without Authorization header are rejected.
     */
    const response = await request.post(`${PIPELINE_URL}/v1/bootstrap`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Should be 401 or 422 (missing field)
    expect(
      [401, 422].includes(response.status()),
      'Missing Authorization should be rejected'
    ).toBeTruthy();
  });
});

/**
 * Code Verification Test
 *
 * This test reads the actual auth.py file and verifies the secret priority.
 * Run this as a pre-commit hook or CI check.
 */
test.describe('B001 Code Verification', () => {
  test('auth.py uses MASTER secret first in decode_jwt()', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const authPyPath = path.join(process.cwd(), 'apps/api/middleware/auth.py');

    // Skip if file doesn't exist (CI without full repo)
    if (!fs.existsSync(authPyPath)) {
      test.skip();
      return;
    }

    const content = fs.readFileSync(authPyPath, 'utf-8');

    // Check 1: secrets_to_try list exists
    expect(
      content.includes('secrets_to_try'),
      'auth.py must use secrets_to_try list pattern'
    ).toBeTruthy();

    // Check 2: MASTER is added first
    const masterFirstPattern = /secrets_to_try\.append\(\('MASTER',\s*MASTER_SUPABASE_JWT_SECRET\)\)/;
    expect(
      masterFirstPattern.test(content),
      'MASTER secret must be added to secrets_to_try first'
    ).toBeTruthy();

    // Check 3: Comment explains the priority
    expect(
      content.includes('MASTER first') || content.includes('MASTER secret first'),
      'Code must have comment explaining MASTER-first priority'
    ).toBeTruthy();

    // Check 4: Old bug pattern is NOT present
    const oldBugPattern = /secret\s*=\s*TENANT_SUPABASE_JWT_SECRET\s+or\s+MASTER_SUPABASE_JWT_SECRET/;
    expect(
      !oldBugPattern.test(content),
      'Old bug pattern (TENANT first) must NOT be present'
    ).toBeTruthy();
  });
});
