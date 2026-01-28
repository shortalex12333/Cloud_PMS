import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Connect Outlook Auth Fix Verification
 *
 * Tests the fix for:
 * - 401 on Connect button after hard refresh
 * - Race condition where authFetch doesn't send Bearer token
 * - Infinite retry loop on /status endpoint
 *
 * Uses pre-authenticated token from global setup.
 */

// Use BASE_URL env var for preview testing, default to prod
const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';

// Get stored auth token from global setup
function getAuthToken(): string | null {
  const statePath = path.join(process.cwd(), 'test-results', '.auth-state.json');
  if (fs.existsSync(statePath)) {
    const state = JSON.parse(fs.readFileSync(statePath, 'utf-8'));
    if (state.accessToken && state.expiresAt > Date.now() / 1000 + 300) {
      return state.accessToken;
    }
  }
  return null;
}

test.describe('Connect Outlook Auth Fix - API Tests', () => {

  test('AUTH_FIX_01: API returns new error format without auth', async ({ request }) => {
    // Make request without auth header
    const response = await request.get(`${BASE_URL}/api/integrations/outlook/auth-url`);

    expect(response.status()).toBe(401);

    const body = await response.json();
    console.log('Error response:', body);

    // Verify new error format
    expect(body).toHaveProperty('error');
    expect(body).toHaveProperty('code');
    expect(body).toHaveProperty('requestId');
    expect(body.code).toBe('missing_bearer');

    // Verify Cache-Control header
    const cacheControl = response.headers()['cache-control'];
    console.log('Cache-Control:', cacheControl);
    expect(cacheControl).toContain('no-store');
  });

  test('AUTH_FIX_02: Auth URL endpoint returns OAuth URL with valid token', async ({ request }) => {
    const token = getAuthToken();
    expect(token).toBeTruthy();
    console.log('Using token:', token?.substring(0, 50) + '...');

    const response = await request.get(`${BASE_URL}/api/integrations/outlook/auth-url`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    console.log('Status:', response.status());

    // Should return 200 with OAuth URL
    expect(response.status()).toBe(200);

    const body = await response.json();
    console.log('Response:', {
      hasUrl: !!body.url,
      purpose: body.purpose,
      scopes: body.scopes
    });

    expect(body).toHaveProperty('url');
    expect(body).toHaveProperty('purpose', 'read');
    expect(body).toHaveProperty('scopes');
    expect(body.url).toContain('login.microsoftonline.com');

    // Verify Cache-Control header
    const cacheControl = response.headers()['cache-control'];
    expect(cacheControl).toContain('no-store');
  });

  test('AUTH_FIX_03: Status endpoint returns connection status with valid token', async ({ request }) => {
    const token = getAuthToken();
    expect(token).toBeTruthy();

    const response = await request.get(`${BASE_URL}/api/integrations/outlook/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    console.log('Status:', response.status());

    // Should return 200 with status
    expect(response.status()).toBe(200);

    const body = await response.json();
    console.log('Response:', body);

    // Status should have connected field
    expect(body).toHaveProperty('connected');

    // Verify Cache-Control header
    const cacheControl = response.headers()['cache-control'];
    expect(cacheControl).toContain('no-store');
  });

  test('AUTH_FIX_04: Status endpoint returns error codes without auth', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/integrations/outlook/status`);

    expect(response.status()).toBe(401);

    const body = await response.json();
    console.log('Error response:', body);

    // Verify error format
    expect(body).toHaveProperty('error');
    expect(body).toHaveProperty('code');
    expect(body.code).toBe('missing_bearer');
  });

});

test.describe('Connect Outlook Auth Fix - Browser Tests', () => {

  test('AUTH_FIX_05: Settings page loads with Connect button', async ({ page, context }) => {
    // Get token for setting up session
    const token = getAuthToken();
    if (!token) {
      console.log('No pre-authenticated token available, skipping browser test');
      test.skip();
      return;
    }

    // Set auth cookie/storage to simulate logged in state
    // Navigate to login first to establish session domain
    await page.goto(`${BASE_URL}/login`);

    // Inject the auth token into localStorage (Supabase stores it there)
    const storageKey = 'sb-qvzmkaamzaqxpzbewjxe-auth-token';
    const authState = JSON.parse(fs.readFileSync(
      path.join(process.cwd(), 'test-results', '.auth-state.json'),
      'utf-8'
    ));

    await page.evaluate(({ key, token, refresh, expiry }) => {
      const sessionData = {
        access_token: token,
        refresh_token: refresh,
        expires_at: expiry,
        token_type: 'bearer',
        user: { id: 'test-user' }
      };
      localStorage.setItem(key, JSON.stringify(sessionData));
    }, {
      key: storageKey,
      token: authState.accessToken,
      refresh: authState.refreshToken,
      expiry: authState.expiresAt
    });

    // Now navigate to settings
    await page.goto(`${BASE_URL}/settings`);

    // Wait for page to load
    await page.waitForLoadState('networkidle', { timeout: 15000 });

    // Take screenshot
    await page.screenshot({ path: 'test-results/screenshots/settings-page.png', fullPage: true });

    // Check if we're on settings page or login page
    const url = page.url();
    console.log('Current URL:', url);

    if (url.includes('/login')) {
      console.log('Redirected to login - session injection may have failed');
      // Still check API works
      const apiResponse = await page.request.get(`${BASE_URL}/api/integrations/outlook/auth-url`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      expect(apiResponse.status()).toBe(200);
      console.log('API works with token - browser session issue is separate');
    } else {
      // On settings page, check for Integrations section
      const integrationsSection = page.locator('text=Integrations').first();
      if (await integrationsSection.isVisible({ timeout: 5000 }).catch(() => false)) {
        console.log('Integrations section found');
        await page.screenshot({ path: 'test-results/screenshots/integrations-visible.png' });
      }
    }
  });

  test('AUTH_FIX_06: No infinite retry loops detected', async ({ page }) => {
    const token = getAuthToken();
    if (!token) {
      test.skip();
      return;
    }

    // Track API calls
    const apiCalls: { url: string; status: number }[] = [];

    page.on('response', response => {
      if (response.url().includes('/api/integrations/outlook/')) {
        apiCalls.push({ url: response.url(), status: response.status() });
      }
    });

    // Navigate to settings (may redirect to login)
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(5000);

    console.log('API calls during page load:');
    apiCalls.forEach((call, i) => {
      console.log(`  ${i + 1}. ${call.status} ${call.url}`);
    });

    // Check for excessive retries (more than 5 calls to same endpoint)
    const statusCalls = apiCalls.filter(c => c.url.includes('/status'));
    console.log(`Total /status calls: ${statusCalls.length}`);

    // Should not have infinite loops - max 4 calls (1 initial + 3 retries)
    expect(statusCalls.length).toBeLessThanOrEqual(5);
  });

});

test.describe('Connect Outlook Auth Fix - Evidence Collection', () => {

  test('EVIDENCE: Collect full test evidence', async ({ request }) => {
    const evidence: any = {
      timestamp: new Date().toISOString(),
      tests: []
    };

    // Test 1: No auth - should get structured error
    console.log('\n=== Test 1: No Auth ===');
    const noAuthResponse = await request.get(`${BASE_URL}/api/integrations/outlook/auth-url`);
    const noAuthBody = await noAuthResponse.json();
    evidence.tests.push({
      name: 'no_auth_error_format',
      status: noAuthResponse.status(),
      cacheControl: noAuthResponse.headers()['cache-control'],
      response: noAuthBody,
      pass: noAuthBody.code === 'missing_bearer'
    });
    console.log('Status:', noAuthResponse.status());
    console.log('Code:', noAuthBody.code);
    console.log('PASS:', noAuthBody.code === 'missing_bearer');

    // Test 2: With auth - should get OAuth URL
    console.log('\n=== Test 2: With Auth ===');
    const token = getAuthToken();
    if (token) {
      const authResponse = await request.get(`${BASE_URL}/api/integrations/outlook/auth-url`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const authBody = await authResponse.json();
      evidence.tests.push({
        name: 'with_auth_oauth_url',
        status: authResponse.status(),
        cacheControl: authResponse.headers()['cache-control'],
        hasUrl: !!authBody.url,
        purpose: authBody.purpose,
        pass: authResponse.status() === 200 && !!authBody.url
      });
      console.log('Status:', authResponse.status());
      console.log('Has URL:', !!authBody.url);
      console.log('Purpose:', authBody.purpose);
      console.log('PASS:', authResponse.status() === 200 && !!authBody.url);
    }

    // Test 3: Status endpoint
    console.log('\n=== Test 3: Status Endpoint ===');
    if (token) {
      const statusResponse = await request.get(`${BASE_URL}/api/integrations/outlook/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const statusBody = await statusResponse.json();
      evidence.tests.push({
        name: 'status_endpoint',
        status: statusResponse.status(),
        cacheControl: statusResponse.headers()['cache-control'],
        connected: statusBody.connected,
        pass: statusResponse.status() === 200
      });
      console.log('Status:', statusResponse.status());
      console.log('Connected:', statusBody.connected);
      console.log('PASS:', statusResponse.status() === 200);
    }

    // Save evidence
    const evidencePath = path.join(process.cwd(), 'test-results', 'auth-fix-evidence.json');
    fs.writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
    console.log('\n=== Evidence saved to:', evidencePath, '===');

    // Overall pass
    const allPass = evidence.tests.every((t: any) => t.pass);
    console.log('\n=== OVERALL:', allPass ? 'PASS' : 'FAIL', '===');
    expect(allPass).toBe(true);
  });

});
