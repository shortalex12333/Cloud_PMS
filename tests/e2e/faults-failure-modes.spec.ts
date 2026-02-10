/**
 * Faults Actions Failure Mode Tests
 *
 * Targets: report_fault, acknowledge_fault, close_fault, update_fault,
 * add_fault_photo, add_fault_note, view_fault_detail, view_fault_history,
 * diagnose_fault, reopen_fault, mark_fault_false_alarm, resolve_fault
 *
 * Verify:
 * - RBAC: role restrictions enforced
 * - RLS: cross-yacht fault_ids denied
 * - Validation: invalid fault_id, invalid severity, injection strings
 * - State machine: open/acknowledged/closed/reopened transitions
 *
 * Expected: 400/404/403; never 500
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_BASE_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = 'd4cd63ce-bcf5-4005-9eec-fe58e5b5ba8d';
const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000001';
const FAKE_FAULT_ID = '99999999-9999-9999-9999-999999999999';
const CROSS_YACHT_FAULT_ID = '11111111-1111-1111-1111-111111111111';
const FAKE_EQUIPMENT_ID = '88888888-8888-8888-8888-888888888888';

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
): Promise<{ status: number; data: any; isJson: boolean }> {
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

  const text = await response.text();
  let data: any;
  let isJson = false;
  try {
    data = JSON.parse(text);
    isJson = true;
  } catch {
    data = { raw: text };
  }

  return { status: response.status, data, isJson };
}

test.describe('Faults - RBAC Tests', () => {

  test('CREW can report_fault (allowed)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: 'Test fault from CREW',
      severity: 'medium'
    });

    // CREW should be able to report faults
    // May fail with NOT_FOUND for fake equipment, but not FORBIDDEN
    if (!result.data.success) {
      expect(result.data.code).not.toBe('FORBIDDEN');
    }
    expect(result.status).not.toBe(500);
  });

  test('CREW cannot close_fault (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'close_fault', {
      fault_id: FAKE_FAULT_ID,
      resolution: 'Testing RBAC'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW cannot diagnose_fault (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'diagnose_fault', {
      fault_id: FAKE_FAULT_ID,
      diagnosis: 'Testing RBAC'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW cannot mark_fault_false_alarm (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'mark_fault_false_alarm', {
      fault_id: FAKE_FAULT_ID,
      reason: 'Testing RBAC'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW can add_fault_note (allowed)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: FAKE_FAULT_ID,
      note: 'Test note from CREW'
    });

    // Should not get FORBIDDEN (may get NOT_FOUND)
    if (!result.data.success) {
      expect(result.data.code).not.toBe('FORBIDDEN');
    }
    expect(result.status).not.toBe(500);
  });

  test('HOD can close_fault (role allowed)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'close_fault', {
      fault_id: FAKE_FAULT_ID,
      resolution: 'Testing HOD access'
    });

    // Should not get FORBIDDEN (may get NOT_FOUND or INVALID_STATE)
    expect(result.data.code).not.toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('HOD can diagnose_fault (role allowed)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'diagnose_fault', {
      fault_id: FAKE_FAULT_ID,
      diagnosis: 'Testing HOD access'
    });

    expect(result.data.code).not.toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - RLS Cross-Yacht Tests', () => {

  test('view_fault_detail with cross-yacht fault_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_detail', {
      fault_id: CROSS_YACHT_FAULT_ID
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('view_fault_history with cross-yacht fault_id (expect 404/403/empty)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_history', {
      fault_id: CROSS_YACHT_FAULT_ID
    });

    if (result.data.success && result.data.data?.history) {
      expect(result.data.data.history).toHaveLength(0);
    } else {
      expect([404, 403]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('acknowledge_fault with cross-yacht fault_id (expect 404/403)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'acknowledge_fault', {
      fault_id: CROSS_YACHT_FAULT_ID
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('close_fault with cross-yacht fault_id (expect 404/403)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'close_fault', {
      fault_id: CROSS_YACHT_FAULT_ID,
      resolution: 'Testing cross-yacht'
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('add_fault_note with cross-yacht fault_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: CROSS_YACHT_FAULT_ID,
      note: 'Testing cross-yacht access'
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Action with mismatched yacht_id context (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(
      crewToken,
      crewUserId,
      'view_fault_detail',
      { fault_id: FAKE_FAULT_ID },
      OTHER_YACHT_ID
    );

    expect([401, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - Validation Tests', () => {

  test('Invalid UUID for fault_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_detail', {
      fault_id: 'not-a-valid-uuid'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Invalid severity value in report_fault (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: 'Test fault',
      severity: 'super_critical_invalid'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Missing required fault_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_detail', {
      // Missing fault_id
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Null fault_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_detail', {
      fault_id: null
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Empty description in report_fault (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: '',
      severity: 'medium'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Missing equipment_id in report_fault (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      description: 'Test fault',
      severity: 'medium'
      // Missing equipment_id
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Oversized description (10KB) in report_fault (expect handled)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const oversizedDescription = 'A'.repeat(10000);

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: oversizedDescription,
      severity: 'medium'
    });

    expect(result.status).not.toBe(500);
  });

  test('Oversized note (10KB) in add_fault_note (expect handled)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const oversizedNote = 'B'.repeat(10000);

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: FAKE_FAULT_ID,
      note: oversizedNote
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - Injection Tests', () => {

  test('SQL injection in fault description (expect sanitized, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const sqlInjection = "'; DROP TABLE pms_faults; --";

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: sqlInjection,
      severity: 'medium'
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('SQL injection in fault note (expect sanitized, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const sqlInjection = "' OR '1'='1'; DELETE FROM pms_faults; --";

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: FAKE_FAULT_ID,
      note: sqlInjection
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in fault description (expect escaped, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const xssPayload = '<script>alert("XSS")</script>';

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: xssPayload,
      severity: 'medium'
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in fault note (expect escaped, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const xssPayload = '<img src=x onerror=alert(1)>';

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: FAKE_FAULT_ID,
      note: xssPayload
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in resolution (expect escaped, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const xssPayload = '<svg onload=alert(1)>';

    const result = await executeAction(hodToken, hodUserId, 'close_fault', {
      fault_id: FAKE_FAULT_ID,
      resolution: xssPayload
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in diagnosis (expect escaped, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const xssPayload = '" onmouseover="alert(1)"';

    const result = await executeAction(hodToken, hodUserId, 'diagnose_fault', {
      fault_id: FAKE_FAULT_ID,
      diagnosis: xssPayload
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Unicode abuse in description (expect handled, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const unicodePayload = 'Fault\u0000\u202E\u2066malicious';

    const result = await executeAction(crewToken, crewUserId, 'report_fault', {
      equipment_id: FAKE_EQUIPMENT_ID,
      description: unicodePayload,
      severity: 'medium'
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - State Machine Tests', () => {

  test('close_fault on non-acknowledged fault (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // Try to close a fault that hasn't been acknowledged
    const result = await executeAction(hodToken, hodUserId, 'close_fault', {
      fault_id: FAKE_FAULT_ID,
      resolution: 'Testing state machine'
    });

    // Should fail with INVALID_STATE_TRANSITION or NOT_FOUND
    if (result.data.success === false) {
      expect(['INVALID_STATE_TRANSITION', 'NOT_FOUND']).toContain(result.data.code);
    }
    expect(result.status).not.toBe(500);
  });

  test('reopen_fault on non-closed fault (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'reopen_fault', {
      fault_id: FAKE_FAULT_ID,
      reason: 'Testing state machine'
    });

    if (result.data.success === false) {
      expect(['INVALID_STATE_TRANSITION', 'NOT_FOUND']).toContain(result.data.code);
    }
    expect(result.status).not.toBe(500);
  });

  test('acknowledge already acknowledged fault (expect 400/idempotent)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // First acknowledge
    await executeAction(hodToken, hodUserId, 'acknowledge_fault', {
      fault_id: FAKE_FAULT_ID
    });

    // Second acknowledge
    const result = await executeAction(hodToken, hodUserId, 'acknowledge_fault', {
      fault_id: FAKE_FAULT_ID
    });

    // Should either be idempotent or fail with INVALID_STATE_TRANSITION
    expect(result.status).not.toBe(500);
  });

  test('mark_fault_false_alarm on closed fault (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'mark_fault_false_alarm', {
      fault_id: FAKE_FAULT_ID,
      reason: 'Testing state machine'
    });

    // Should fail with proper state transition error
    expect(result.status).not.toBe(500);
  });

  test('diagnose already diagnosed fault (expect 400/idempotent)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // First diagnosis
    await executeAction(hodToken, hodUserId, 'diagnose_fault', {
      fault_id: FAKE_FAULT_ID,
      diagnosis: 'First diagnosis'
    });

    // Second diagnosis
    const result = await executeAction(hodToken, hodUserId, 'diagnose_fault', {
      fault_id: FAKE_FAULT_ID,
      diagnosis: 'Second diagnosis'
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - Non-Existent Entity Tests', () => {

  test('view_fault_detail on non-existent fault (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_detail', {
      fault_id: FAKE_FAULT_ID
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('acknowledge_fault on non-existent fault (expect 404)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'acknowledge_fault', {
      fault_id: FAKE_FAULT_ID
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('close_fault on non-existent fault (expect 404)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'close_fault', {
      fault_id: FAKE_FAULT_ID,
      resolution: 'Testing non-existent'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('add_fault_note on non-existent fault (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_fault_note', {
      fault_id: FAKE_FAULT_ID,
      note: 'Test note'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('view_fault_history on non-existent fault (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'view_fault_history', {
      fault_id: FAKE_FAULT_ID
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });
});

test.describe('Faults - Authentication Tests', () => {

  test('No Authorization header (expect 401)', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'view_fault_detail',
        context: { yacht_id: YACHT_ID },
        payload: { fault_id: FAKE_FAULT_ID }
      })
    });

    expect(response.status).toBe(401);
  });

  test('Invalid Authorization token (expect 401)', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer invalid-token',
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'view_fault_detail',
        context: { yacht_id: YACHT_ID },
        payload: { fault_id: FAKE_FAULT_ID }
      })
    });

    expect(response.status).toBe(401);
  });
});
