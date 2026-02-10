/**
 * Inventory Actions Failure Mode Tests
 *
 * Targets: check_part_stock, view_part_details, view_part_usage_history, log_part_usage
 *
 * Verify:
 * - RBAC: CREW forbidden to mutate; HOD+ allowed where specified
 * - RLS: cross-yacht part_ids denied
 * - Validation: invalid part_id, negative quantity, oversized fields, injection strings
 *
 * Expected: 400/404/403; never 500
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_BASE_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = 'd4cd63ce-bcf5-4005-9eec-fe58e5b5ba8d';

// Cross-yacht ID for RLS testing (different yacht)
const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000001';

// Auth state paths
const CREW_AUTH_STATE = 'test-results/.auth-states/crew-state.json';
const HOD_AUTH_STATE = 'test-results/.auth-states/chief_engineer-state.json';

function extractToken(authStatePath: string): string {
  const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
  const cookies = state.cookies || [];
  const authCookie = cookies.find((c: any) =>
    c.name === 'sb-access-token' ||
    c.name === 'sb-zfvtdepqqyvmjvcqapfy-auth-token'
  );
  return authCookie?.value || '';
}

function extractUserId(authStatePath: string): string {
  const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
  const origins = state.origins || [];
  const localStorage = origins[0]?.localStorage || [];
  const authItem = localStorage.find((item: any) =>
    item.name.includes('auth-token')
  );

  if (authItem?.value) {
    try {
      const parsed = JSON.parse(authItem.value);
      return parsed.user?.id || parsed.currentUser?.id || '';
    } catch (e) {
      return '';
    }
  }
  return '';
}

async function executeAction(
  token: string,
  userId: string,
  action: string,
  payload: any,
  yachtId: string = YACHT_ID
): Promise<{ status: number; data: any }> {
  const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-Yacht-Signature': `yacht_id=${yachtId}`
    },
    body: JSON.stringify({
      action,
      context: { yacht_id: yachtId, user_id: userId },
      payload
    })
  });

  const data = await response.json();
  return { status: response.status, data };
}

test.describe('Inventory - RBAC Tests', () => {

  test('CREW cannot log_part_usage (expect 403/400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: 'routine maintenance'
    });

    // CREW should not be able to log usage - expect 403 FORBIDDEN
    expect(result.data.success).toBe(false);
    expect([400, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('HOD can log_part_usage (expect success or proper validation error)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: 'routine maintenance'
    });

    // HOD should be allowed, but may get 404 for non-existent part
    // Should NOT get 403 FORBIDDEN for role
    expect(result.data.code).not.toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });
});

test.describe('Inventory - RLS Cross-Yacht Tests', () => {

  test('check_part_stock with cross-yacht part_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    // Use a part_id that would belong to a different yacht
    const crossYachtPartId = '11111111-1111-1111-1111-111111111111';

    const result = await executeAction(crewToken, crewUserId, 'check_part_stock', {
      part_id: crossYachtPartId
    });

    // Should deny access to cross-yacht data
    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('view_part_details with cross-yacht part_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const crossYachtPartId = '11111111-1111-1111-1111-111111111111';

    const result = await executeAction(crewToken, crewUserId, 'view_part_details', {
      part_id: crossYachtPartId
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('view_part_usage_history with cross-yacht part_id (expect 404/403/empty)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const crossYachtPartId = '11111111-1111-1111-1111-111111111111';

    const result = await executeAction(crewToken, crewUserId, 'view_part_usage_history', {
      part_id: crossYachtPartId
    });

    // Should either deny access or return empty results
    if (result.data.success) {
      // If succeeds, should have empty history (RLS filtered)
      expect(result.data.data?.history || []).toHaveLength(0);
    } else {
      expect([404, 403]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('log_part_usage with cross-yacht part_id (expect 404/403)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const crossYachtPartId = '11111111-1111-1111-1111-111111111111';

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: crossYachtPartId,
      quantity: 1,
      usage_reason: 'testing RLS'
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Action with mismatched yacht_id context (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    // Try to execute action with different yacht in context
    const result = await executeAction(
      crewToken,
      crewUserId,
      'check_part_stock',
      { part_id: '99999999-9999-9999-9999-999999999999' },
      OTHER_YACHT_ID  // Different yacht
    );

    // Should deny - user doesn't belong to this yacht
    expect([401, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Inventory - Validation Tests', () => {

  test('Invalid UUID for part_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'check_part_stock', {
      part_id: 'not-a-valid-uuid'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Negative quantity in log_part_usage (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: -5,
      usage_reason: 'testing negative'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Zero quantity in log_part_usage (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 0,
      usage_reason: 'testing zero'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Missing required field part_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'check_part_stock', {
      // Missing part_id
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Null part_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'check_part_stock', {
      part_id: null
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Oversized usage_reason (10KB string) (expect 400 or truncate)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const oversizedReason = 'A'.repeat(10000);

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: oversizedReason
    });

    // Should either reject (400) or accept with truncation
    // MUST NOT be 500
    expect(result.status).not.toBe(500);
  });

  test('Oversized notes field (20KB string) (expect 400 or truncate)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const oversizedNotes = 'B'.repeat(20000);

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: 'test',
      notes: oversizedNotes
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Inventory - Injection Tests', () => {

  test('SQL injection in usage_reason (expect 400, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const sqlInjection = "'; DROP TABLE pms_parts; --";

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: sqlInjection
    });

    // Should either reject (400) or safely escape
    // MUST NOT be 500 (SQL error)
    expect(result.status).not.toBe(500);
  });

  test('SQL injection in notes field (expect 400, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const sqlInjection = "' OR '1'='1'; DELETE FROM pms_inventory_items; --";

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: 'test',
      notes: sqlInjection
    });

    expect(result.status).not.toBe(500);
  });

  test('XSS in usage_reason (expect escaped/sanitized, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const xssPayload = '<script>alert("XSS")</script>';

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: xssPayload
    });

    // Should either reject or escape (sanitize on display)
    expect(result.status).not.toBe(500);
  });

  test('XSS in notes field (expect escaped/sanitized, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const xssPayload = '<img src=x onerror=alert(1)>';

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: 'test',
      notes: xssPayload
    });

    expect(result.status).not.toBe(500);
  });

  test('CRLF injection attempt (expect sanitized, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const crlfPayload = 'test\r\nX-Injected-Header: malicious';

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: crlfPayload
    });

    expect(result.status).not.toBe(500);
  });

  test('Unicode abuse attempt (expect handled, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // NULL byte + unicode control chars + right-to-left override
    const unicodePayload = 'test\u0000\u202E\u2066malicious';

    const result = await executeAction(hodToken, hodUserId, 'log_part_usage', {
      part_id: '99999999-9999-9999-9999-999999999999',
      quantity: 1,
      usage_reason: unicodePayload
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Inventory - Authentication Tests', () => {

  test('No Authorization header (expect 401)', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
        // No Authorization header
      },
      body: JSON.stringify({
        action: 'check_part_stock',
        context: { yacht_id: YACHT_ID },
        payload: { part_id: '99999999-9999-9999-9999-999999999999' }
      })
    });

    expect(response.status).toBe(401);
  });

  test('Invalid Authorization token (expect 401)', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer invalid-token-here',
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'check_part_stock',
        context: { yacht_id: YACHT_ID },
        payload: { part_id: '99999999-9999-9999-9999-999999999999' }
      })
    });

    expect(response.status).toBe(401);
  });

  test('Expired token (expect 401)', async () => {
    // This is a valid JWT format but expired
    const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid';

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${expiredToken}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'check_part_stock',
        context: { yacht_id: YACHT_ID },
        payload: { part_id: '99999999-9999-9999-9999-999999999999' }
      })
    });

    expect(response.status).toBe(401);
  });
});

test.describe('Inventory - Edge Cases', () => {

  test('Non-existent action name (expect 400/404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'nonexistent_action_xyz', {
      part_id: '99999999-9999-9999-9999-999999999999'
    });

    expect([400, 404]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Empty action name (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, '', {
      part_id: '99999999-9999-9999-9999-999999999999'
    });

    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Malformed JSON body (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: '{invalid json here'
    });

    expect(response.status).toBe(400);
  });

  test('Wrong HTTP method GET (expect 405)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      }
    });

    expect([400, 405]).toContain(response.status);
  });

  test('Very large payload (1MB) (expect 413 or handled gracefully)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const largePayload = {
      part_id: '99999999-9999-9999-9999-999999999999',
      extra_data: 'X'.repeat(1000000)  // 1MB of data
    };

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'check_part_stock',
        context: { yacht_id: YACHT_ID, user_id: crewUserId },
        payload: largePayload
      })
    });

    // Should either reject (413/400) or handle gracefully
    expect(response.status).not.toBe(500);
  });
});
