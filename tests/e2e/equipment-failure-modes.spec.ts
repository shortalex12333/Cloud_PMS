/**
 * Equipment Actions Failure Mode Tests
 *
 * Targets: update_equipment_status, add_equipment_note, attach_file_to_equipment,
 * create_work_order_for_equipment, link_part_to_equipment, flag_equipment_attention,
 * decommission_equipment, record_equipment_hours, create_equipment, assign_parent_equipment,
 * archive_equipment, restore_archived_equipment, get_open_faults_for_equipment,
 * get_related_entities_for_equipment, decommission_and_replace_equipment
 *
 * Verify:
 * - RBAC: role restrictions enforced
 * - RLS: cross-yacht equipment_ids denied
 * - Validation: invalid equipment_id, invalid status values, injection strings
 * - State machine: decommission/archive transitions
 *
 * Expected: 400/404/403; never 500
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_BASE_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = 'd4cd63ce-bcf5-4005-9eec-fe58e5b5ba8d';
const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000001';
const FAKE_EQUIPMENT_ID = '99999999-9999-9999-9999-999999999999';
const CROSS_YACHT_EQUIPMENT_ID = '11111111-1111-1111-1111-111111111111';

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

test.describe('Equipment - RBAC Tests', () => {

  test('CREW cannot decommission_equipment (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'decommission_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      reason: 'Testing RBAC'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW cannot archive_equipment (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'archive_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW cannot create_equipment (expect 403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_equipment', {
      name: 'Test Equipment',
      category: 'Engine',
      location: 'Engine Room'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });

  test('CREW can add_equipment_note (read/note actions allowed)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: 'Test note from crew'
    });

    // Should either succeed or fail with NOT_FOUND (not FORBIDDEN)
    if (!result.data.success) {
      expect(result.data.code).not.toBe('FORBIDDEN');
    }
    expect(result.status).not.toBe(500);
  });

  test('HOD can decommission_equipment (role allowed)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'decommission_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      reason: 'Testing HOD access'
    });

    // Should not get FORBIDDEN (may get NOT_FOUND for fake ID)
    expect(result.data.code).not.toBe('FORBIDDEN');
    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - RLS Cross-Yacht Tests', () => {

  test('update_equipment_status with cross-yacht equipment_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      equipment_id: CROSS_YACHT_EQUIPMENT_ID,
      status: 'operational'
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('add_equipment_note with cross-yacht equipment_id (expect 404/403)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: CROSS_YACHT_EQUIPMENT_ID,
      note: 'Testing cross-yacht access'
    });

    expect([404, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('get_open_faults_for_equipment with cross-yacht equipment_id (expect 404/403/empty)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'get_open_faults_for_equipment', {
      equipment_id: CROSS_YACHT_EQUIPMENT_ID
    });

    if (result.data.success && result.data.data?.faults) {
      expect(result.data.data.faults).toHaveLength(0);
    } else {
      expect([404, 403]).toContain(result.status);
    }
    expect(result.status).not.toBe(500);
  });

  test('link_part_to_equipment with cross-yacht equipment_id (expect 404/403)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'link_part_to_equipment', {
      equipment_id: CROSS_YACHT_EQUIPMENT_ID,
      part_id: FAKE_EQUIPMENT_ID
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
      'get_open_faults_for_equipment',
      { equipment_id: FAKE_EQUIPMENT_ID },
      OTHER_YACHT_ID
    );

    expect([401, 403]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - Validation Tests', () => {

  test('Invalid UUID for equipment_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      equipment_id: 'not-a-valid-uuid',
      status: 'operational'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Invalid status value (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      equipment_id: FAKE_EQUIPMENT_ID,
      status: 'super_broken_invalid_status'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Missing required equipment_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      status: 'operational'
      // Missing equipment_id
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Null equipment_id (expect 400)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      equipment_id: null,
      status: 'operational'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Empty name in create_equipment (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'create_equipment', {
      name: '',
      category: 'Engine',
      location: 'Engine Room'
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Negative hours in record_equipment_hours (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'record_equipment_hours', {
      equipment_id: FAKE_EQUIPMENT_ID,
      hours: -100
    });

    expect(result.data.success).toBe(false);
    expect([400, 422]).toContain(result.status);
    expect(result.status).not.toBe(500);
  });

  test('Oversized note (10KB) in add_equipment_note (expect handled)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const oversizedNote = 'A'.repeat(10000);

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: oversizedNote
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - Injection Tests', () => {

  test('SQL injection in equipment note (expect sanitized, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const sqlInjection = "'; DROP TABLE pms_equipment; --";

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: sqlInjection
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in equipment note (expect escaped, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const xssPayload = '<script>alert("XSS")</script>';

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: xssPayload
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('SQL injection in equipment name (expect sanitized, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const sqlInjection = "Engine'; DELETE FROM pms_equipment; --";

    const result = await executeAction(hodToken, hodUserId, 'create_equipment', {
      name: sqlInjection,
      category: 'Engine',
      location: 'Engine Room'
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('XSS in decommission reason (expect escaped, no 500)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const xssPayload = '<img src=x onerror=alert(1)>';

    const result = await executeAction(hodToken, hodUserId, 'decommission_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      reason: xssPayload
    });

    expect(result.status).not.toBe(500);
    expect(result.isJson).toBe(true);
  });

  test('Unicode abuse in note (expect handled, no 500)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const unicodePayload = 'Test\u0000\u202E\u2066malicious';

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: unicodePayload
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - State Machine Tests', () => {

  test('restore_archived_equipment on non-archived equipment (expect 400)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'restore_archived_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID
    });

    // Should either fail with INVALID_STATE_TRANSITION or NOT_FOUND
    if (result.data.success === false) {
      expect(['INVALID_STATE_TRANSITION', 'NOT_FOUND']).toContain(result.data.code);
    }
    expect(result.status).not.toBe(500);
  });

  test('decommission already decommissioned equipment (expect 400/idempotent)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // First decommission
    await executeAction(hodToken, hodUserId, 'decommission_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      reason: 'First decommission'
    });

    // Second decommission
    const result = await executeAction(hodToken, hodUserId, 'decommission_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      reason: 'Second decommission'
    });

    // Should either be idempotent or fail with INVALID_STATE_TRANSITION
    expect(result.status).not.toBe(500);
  });

  test('archive already archived equipment (expect 400/idempotent)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    // First archive
    await executeAction(hodToken, hodUserId, 'archive_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID
    });

    // Second archive
    const result = await executeAction(hodToken, hodUserId, 'archive_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID
    });

    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - Non-Existent Entity Tests', () => {

  test('update_equipment_status on non-existent equipment (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'update_equipment_status', {
      equipment_id: FAKE_EQUIPMENT_ID,
      status: 'operational'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('add_equipment_note on non-existent equipment (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'add_equipment_note', {
      equipment_id: FAKE_EQUIPMENT_ID,
      note: 'Test note'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('link_part_to_equipment on non-existent equipment (expect 404)', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'link_part_to_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID,
      part_id: '88888888-8888-8888-8888-888888888888'
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });

  test('get_related_entities_for_equipment on non-existent equipment (expect 404)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'get_related_entities_for_equipment', {
      equipment_id: FAKE_EQUIPMENT_ID
    });

    expect(result.data.success).toBe(false);
    expect(result.data.code).toBe('NOT_FOUND');
    expect(result.status).not.toBe(500);
  });
});

test.describe('Equipment - Authentication Tests', () => {

  test('No Authorization header (expect 401)', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Yacht-Signature': `yacht_id=${YACHT_ID}`
      },
      body: JSON.stringify({
        action: 'update_equipment_status',
        context: { yacht_id: YACHT_ID },
        payload: { equipment_id: FAKE_EQUIPMENT_ID, status: 'operational' }
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
        action: 'update_equipment_status',
        context: { yacht_id: YACHT_ID },
        payload: { equipment_id: FAKE_EQUIPMENT_ID, status: 'operational' }
      })
    });

    expect(response.status).toBe(401);
  });
});
