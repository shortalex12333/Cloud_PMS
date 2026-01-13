/**
 * Master Bootstrap Contract Test
 *
 * Verifies the get_my_bootstrap RPC function on Master Supabase
 *
 * Contract:
 * - POST /rest/v1/rpc/get_my_bootstrap
 * - Requires: Authorization header with valid JWT
 * - Returns: { yacht_id, tenant_key_alias, role, status, ... }
 */

import { test, expect } from '@playwright/test';
import { login, getBootstrap } from '../helpers/auth';
import { saveArtifact, createEvidenceBundle } from '../helpers/artifacts';
import { verifyUserAccount, verifyFleetRegistry } from '../helpers/supabase_master';

test.describe('Master Bootstrap Contract', () => {
  test('Login returns valid JWT', async () => {
    const testName = 'contracts/login';

    const startTime = Date.now();
    const tokens = await login();
    const duration = Date.now() - startTime;

    // Verify token structure (without exposing full token)
    const tokenParts = tokens.accessToken.split('.');
    const isValidJwt = tokenParts.length === 3;

    // Save evidence (sanitized)
    saveArtifact('login_response.json', {
      timestamp: new Date().toISOString(),
      duration_ms: duration,
      has_access_token: !!tokens.accessToken,
      has_refresh_token: !!tokens.refreshToken,
      expires_at: tokens.expiresAt,
      token_valid_jwt_format: isValidJwt,
      token_prefix: tokens.accessToken.substring(0, 20) + '...',
    }, testName);

    createEvidenceBundle(testName, {
      response: {
        has_access_token: !!tokens.accessToken,
        duration_ms: duration,
      },
      assertions: [
        { name: 'Has access token', passed: !!tokens.accessToken },
        { name: 'Valid JWT format', passed: isValidJwt },
        { name: 'Has expiry', passed: tokens.expiresAt > 0 },
      ],
    });

    expect(tokens.accessToken).toBeTruthy();
    expect(isValidJwt).toBe(true);
    expect(tokens.expiresAt).toBeGreaterThan(Date.now() / 1000);
  });

  test('get_my_bootstrap returns yacht_id and tenant_key_alias', async () => {
    const testName = 'contracts/bootstrap';

    // First login
    const tokens = await login();

    // Then get bootstrap
    const startTime = Date.now();
    const bootstrap = await getBootstrap(tokens.accessToken);
    const duration = Date.now() - startTime;

    // Save evidence
    saveArtifact('bootstrap_response.json', {
      timestamp: new Date().toISOString(),
      duration_ms: duration,
      yacht_id: bootstrap.yachtId,
      tenant_key_alias: bootstrap.tenantKeyAlias,
      role: bootstrap.role,
      status: bootstrap.status,
    }, testName);

    // Validate expected fields
    const expectedYachtId = process.env.TEST_USER_YACHT_ID;
    const expectedTenantKey = process.env.TEST_USER_TENANT_KEY;

    const assertions = [
      {
        name: 'Has yacht_id',
        passed: !!bootstrap.yachtId,
        message: bootstrap.yachtId || 'missing',
      },
      {
        name: 'Has tenant_key_alias',
        passed: !!bootstrap.tenantKeyAlias,
        message: bootstrap.tenantKeyAlias || 'missing',
      },
      {
        name: 'Has role',
        passed: !!bootstrap.role,
        message: bootstrap.role || 'missing',
      },
      {
        name: 'Has status',
        passed: !!bootstrap.status,
        message: bootstrap.status || 'missing',
      },
      {
        name: 'yacht_id matches expected',
        passed: !expectedYachtId || bootstrap.yachtId === expectedYachtId,
        message: `Expected: ${expectedYachtId}, Got: ${bootstrap.yachtId}`,
      },
      {
        name: 'tenant_key_alias matches expected',
        passed: !expectedTenantKey || bootstrap.tenantKeyAlias === expectedTenantKey,
        message: `Expected: ${expectedTenantKey}, Got: ${bootstrap.tenantKeyAlias}`,
      },
    ];

    createEvidenceBundle(testName, {
      response: bootstrap,
      assertions,
    });

    expect(bootstrap.yachtId).toBeTruthy();
    expect(bootstrap.tenantKeyAlias).toBeTruthy();
    expect(bootstrap.role).toBeTruthy();
    expect(bootstrap.status).toBe('active');

    if (expectedYachtId) {
      expect(bootstrap.yachtId).toBe(expectedYachtId);
    }
    if (expectedTenantKey) {
      expect(bootstrap.tenantKeyAlias).toBe(expectedTenantKey);
    }
  });

  test('tenant_key_alias format is valid', async () => {
    const testName = 'contracts/tenant_key_format';

    const tokens = await login();
    const bootstrap = await getBootstrap(tokens.accessToken);

    // tenant_key_alias should be y<yacht_id>
    const expectedFormat = `y${bootstrap.yachtId}`;
    const matchesFormat = bootstrap.tenantKeyAlias === expectedFormat;

    saveArtifact('tenant_key_validation.json', {
      yacht_id: bootstrap.yachtId,
      tenant_key_alias: bootstrap.tenantKeyAlias,
      expected_format: expectedFormat,
      matches: matchesFormat,
    }, testName);

    createEvidenceBundle(testName, {
      response: {
        yacht_id: bootstrap.yachtId,
        tenant_key_alias: bootstrap.tenantKeyAlias,
      },
      assertions: [
        {
          name: 'tenant_key_alias matches y<yacht_id> format',
          passed: matchesFormat,
          message: `Expected: ${expectedFormat}, Got: ${bootstrap.tenantKeyAlias}`,
        },
      ],
    });

    expect(bootstrap.tenantKeyAlias).toBe(expectedFormat);
  });

  test('user_accounts table has test user', async () => {
    const testName = 'contracts/user_accounts';

    const email = process.env.TEST_USER_EMAIL;
    if (!email) {
      saveArtifact('skip_reason.json', { reason: 'TEST_USER_EMAIL not set' }, testName);
      test.skip();
      return;
    }

    const result = await verifyUserAccount(email);

    saveArtifact('user_account.json', {
      email,
      exists: result.exists,
      data: result.data,
    }, testName);

    createEvidenceBundle(testName, {
      dbAfter: result.data,
      assertions: [
        { name: 'User exists in user_accounts', passed: result.exists },
        { name: 'User status is active', passed: result.data?.status === 'active' },
      ],
    });

    expect(result.exists).toBe(true);
    expect(result.data?.status).toBe('active');
  });

  test('fleet_registry has yacht entry', async () => {
    const testName = 'contracts/fleet_registry';

    const yachtId = process.env.TEST_USER_YACHT_ID;
    if (!yachtId) {
      saveArtifact('skip_reason.json', { reason: 'TEST_USER_YACHT_ID not set' }, testName);
      test.skip();
      return;
    }

    const result = await verifyFleetRegistry(yachtId);

    saveArtifact('fleet_registry.json', {
      yacht_id: yachtId,
      exists: result.exists,
      data: result.data,
    }, testName);

    createEvidenceBundle(testName, {
      dbAfter: result.data,
      assertions: [
        { name: 'Fleet registry entry exists', passed: result.exists },
        { name: 'Fleet is active', passed: result.data?.active === true },
        { name: 'Has tenant_key_alias', passed: !!result.data?.tenant_key_alias },
      ],
    });

    expect(result.exists).toBe(true);
    expect(result.data?.active).toBe(true);
  });
});
