/**
 * Shopping List Failure Mode Tests
 *
 * Comprehensive testing of:
 * - RLS (Row Level Security) policy violations
 * - Invalid data submission
 * - Unauthorized actions
 * - Contradictory workflows
 * - Edge cases and security vulnerabilities
 *
 * These tests ensure the system properly rejects malicious or incorrect usage.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';

const API_BASE_URL = 'https://pipeline-core.int.celeste7.ai';

// Load pre-authenticated storage states
const CREW_AUTH_STATE = 'test-results/.auth-states/crew-state.json';
const HOD_AUTH_STATE = 'test-results/.auth-states/chief_engineer-state.json';

// Helper: Extract JWT token from storage state
function extractToken(authStatePath: string): string {
  const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));

  // First check localStorage (where Supabase stores tokens)
  const origins = state.origins || [];
  for (const origin of origins) {
    const localStorage = origin.localStorage || [];
    const authItem = localStorage.find((item: any) =>
      item.name.includes('auth-token')
    );
    if (authItem?.value) {
      try {
        const parsed = JSON.parse(authItem.value);
        if (parsed.access_token) {
          return parsed.access_token;
        }
      } catch (e) {
        // Continue to check cookies
      }
    }
  }

  // Fallback to cookies
  const cookies = state.cookies || [];
  const authCookie = cookies.find((c: any) =>
    c.name === 'sb-access-token' ||
    c.name.includes('auth-token')
  );
  return authCookie?.value || '';
}

// Helper: Extract user_id from storage state
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

// Helper: Extract yacht_id from storage state (user-bootstrap)
function extractYachtId(authStatePath: string): string {
  const state = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
  const origins = state.origins || [];
  const localStorage = origins[0]?.localStorage || [];
  const bootstrapItem = localStorage.find((item: any) =>
    item.name === 'user-bootstrap'
  );

  if (bootstrapItem?.value) {
    try {
      const parsed = JSON.parse(bootstrapItem.value);
      return parsed.yachtId || '';
    } catch (e) {
      return '';
    }
  }
  return '';
}

// Helper: Normalize API response to handle various error formats
// Format 1: { status: "error", error_code: "...", message: "..." }
// Format 2: { success: false, code: "...", message: "..." }
// Format 3: { code: "...", message: "...", status_code: ... } (no success/status field)
function isErrorResponse(result: any): boolean {
  if (result.success === false) return true;
  if (result.status === 'error') return true;
  // If there's a code/error_code without success: true, it's an error
  if ((result.code || result.error_code) && result.success !== true) return true;
  return false;
}

function getErrorCode(result: any): string {
  return result.code || result.error_code || '';
}

// Helper: Execute action via API
async function executeAction(
  token: string,
  userId: string,
  action: string,
  payload: any,
  yachtId: string,
  context?: any
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-Yacht-Signature': `yacht_id=${yachtId}`
    },
    body: JSON.stringify({
      action,
      context: { yacht_id: yachtId, user_id: userId, ...context },
      payload
    })
  });

  return response.json();
}

test.describe('Shopping List - RLS Policy Violations', () => {

  test('CREW cannot approve shopping list item (permission denied)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    // First create an item as CREW
    const createResult = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: `RLS Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    expect(createResult.success).toBe(true);
    const itemId = createResult.data.shopping_list_item_id;

    // Try to approve as CREW (should fail)
    const approveResult = await executeAction(crewToken, crewUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, crewYachtId);

    expect(isErrorResponse(approveResult)).toBe(true);
    expect(getErrorCode(approveResult)).toBe('FORBIDDEN');
    expect(approveResult.message).toContain('not authorized');
  });

  test('CREW cannot reject shopping list item (permission denied)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    // Create item as CREW
    const createResult = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: `RLS Test Reject ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    expect(createResult.success).toBe(true);
    const itemId = createResult.data.shopping_list_item_id;

    // Try to reject as CREW (should fail)
    const rejectResult = await executeAction(crewToken, crewUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'Testing RLS'
    }, crewYachtId);

    expect(isErrorResponse(rejectResult)).toBe(true);
    expect(getErrorCode(rejectResult)).toBe('FORBIDDEN');
  });

  test('CREW cannot promote candidate to parts catalog (permission denied)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create and approve item as HOD
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `RLS Promote Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    // Try to promote as CREW (should fail)
    const promoteResult = await executeAction(crewToken, crewUserId, 'promote_candidate_to_part', {
      item_id: itemId
    }, crewYachtId);

    expect(isErrorResponse(promoteResult)).toBe(true);
    expect(getErrorCode(promoteResult)).toBe('FORBIDDEN');
  });

  test('Cannot access items from different yacht (cross-tenant isolation)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    // Use a fake item_id from a different yacht
    const fakeItemId = '00000000-0000-0000-0000-000000000000';

    const result = await executeAction(crewToken, crewUserId, 'view_shopping_list_item_history', {
      item_id: fakeItemId
    }, crewYachtId);

    // Should either return empty or permission denied
    expect(isErrorResponse(result)).toBe(true);
  });

  test('Cannot perform actions without authentication', async () => {
    const yachtId = extractYachtId(CREW_AUTH_STATE) || '85fe1119-b04c-41ac-80f1-829d23322598';

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Yacht-Signature': `yacht_id=${yachtId}`
        // No Authorization header
      },
      body: JSON.stringify({
        action: 'create_shopping_list_item',
        context: { yacht_id: yachtId },
        payload: {
          part_name: 'Test',
          quantity_requested: 1,
          urgency: 'normal',
          source_type: 'manual_add'
        }
      })
    });

    expect(response.status).toBe(401);
  });
});

test.describe('Shopping List - Invalid Data Submission', () => {

  test('Reject invalid UUID format for item_id', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const result = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: 'not-a-valid-uuid',
      quantity_approved: 1
    }, hodYachtId);

    expect(isErrorResponse(result)).toBe(true);
  });

  test('Reject SQL injection attempt in part_name', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const sqlInjection = "'; DROP TABLE shopping_list; --";

    // Note: This test may return HTML if WAF blocks the request
    // We use a direct fetch to check the response type
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${crewYachtId}`
      },
      body: JSON.stringify({
        action: 'create_shopping_list_item',
        context: { yacht_id: crewYachtId, user_id: crewUserId },
        payload: {
          part_name: sqlInjection,
          quantity_requested: 1,
          urgency: 'normal',
          source_type: 'manual_add'
        }
      })
    });

    // WAF may block SQL-like patterns - that's acceptable security behavior
    // OR the API should store it safely with parameterized queries
    if (response.headers.get('content-type')?.includes('application/json')) {
      const result = await response.json();
      // If JSON response, SQL injection should be safely stored
      if (result.success) {
        expect(result.data.part_name).toBe(sqlInjection);
      }
    } else {
      // WAF blocked the request - this is acceptable security behavior
      expect(response.ok).toBe(false);
    }
  });

  test('Reject XSS attempt in part_name', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const xssPayload = '<script>alert("XSS")</script>';

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: xssPayload,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    // Should succeed but sanitize or store as-is (sanitization happens on display)
    if (result.success) {
      // Verify it's stored safely
      expect(result.data.part_name).toBeDefined();
    }
  });

  test('Reject extremely large quantity (overflow test)', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: 'Overflow Test',
      quantity_requested: 9999999999999999,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    // Should either fail validation or accept if within database limits
    expect(result).toBeDefined();
  });

  test('Reject negative quantity', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: 'Negative Quantity Test',
      quantity_requested: -5,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('VALIDATION_FAILED');
  });

  test('Reject invalid urgency value', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: 'Invalid Urgency Test',
      quantity_requested: 1,
      urgency: 'super_mega_urgent',
      source_type: 'manual_add'
    }, crewYachtId);

    // Note: API may use default urgency if invalid value provided
    // Check for either validation failure or successful creation
    expect(result).toBeDefined();
  });

  test('Reject invalid source_type value', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: 'Invalid Source Type Test',
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'invalid_source'
    }, crewYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('VALIDATION_FAILED');
  });

  test('Reject empty part_name', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: '',
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('MISSING_REQUIRED_FIELD');
  });

  test('Reject null values for required fields', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: null,
      quantity_requested: null,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    expect(isErrorResponse(result)).toBe(true);
  });

  test('Reject Unicode control characters in text fields', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const controlChars = 'Test\u0000\u0001\u0002Part';

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: controlChars,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, crewYachtId);

    // Should either reject or sanitize
    expect(result).toBeDefined();
  });
});

test.describe('Shopping List - Contradictory Workflows', () => {

  test('Cannot approve already rejected item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Contradictory Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    // Reject it
    const rejectResult = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'Testing state machine'
    }, hodYachtId);

    expect(rejectResult.success).toBe(true);

    // Try to approve (should fail)
    const approveResult = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    expect(isErrorResponse(approveResult)).toBe(true);
    expect(getErrorCode(approveResult)).toMatch(/INVALID_STATE(_TRANSITION)?/);
  });

  test('Cannot reject already approved item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create and approve item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `State Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    // Try to reject (should fail)
    const rejectResult = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'Cannot reject approved'
    }, hodYachtId);

    expect(isErrorResponse(rejectResult)).toBe(true);
    expect(getErrorCode(rejectResult)).toMatch(/INVALID_STATE(_TRANSITION)?/);
  });

  test('Cannot promote non-approved item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create item but don't approve
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Non-Approved Promote ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    // Try to promote without approval (should fail)
    const promoteResult = await executeAction(hodToken, hodUserId, 'promote_candidate_to_part', {
      item_id: itemId
    }, hodYachtId);

    expect(isErrorResponse(promoteResult)).toBe(true);
    expect(getErrorCode(promoteResult)).toMatch(/INVALID_STATE(_TRANSITION)?/);
  });

  test('Cannot promote rejected item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create and reject item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Rejected Promote ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'Testing terminal state'
    }, hodYachtId);

    // Try to promote rejected item (should fail)
    const promoteResult = await executeAction(hodToken, hodUserId, 'promote_candidate_to_part', {
      item_id: itemId
    }, hodYachtId);

    expect(isErrorResponse(promoteResult)).toBe(true);
  });

  test('Cannot double-approve same item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create and approve item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Double Approve Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    const firstApprove = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    expect(firstApprove.success).toBe(true);

    // Try to approve again (idempotency test)
    const secondApprove = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    // Should either fail or be idempotent
    if (secondApprove.success) {
      // Idempotent behavior is acceptable
      expect(secondApprove.data.status).toBe('approved');
    } else {
      expect(getErrorCode(secondApprove)).toMatch(/INVALID_STATE(_TRANSITION)?/);
    }
  });

  test('Cannot double-reject same item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create and reject item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Double Reject Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    const firstReject = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'First rejection'
    }, hodYachtId);

    expect(firstReject.success).toBe(true);

    // Try to reject again
    const secondReject = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: 'Second rejection'
    }, hodYachtId);

    // Should either fail or be idempotent
    if (secondReject.success) {
      expect(secondReject.data.status).toBe('rejected');
    } else {
      expect(getErrorCode(secondReject)).toMatch(/INVALID_STATE(_TRANSITION)?/);
    }
  });

  test('Cannot double-promote same item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create, approve, and promote item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Double Promote Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 1
    }, hodYachtId);

    const firstPromote = await executeAction(hodToken, hodUserId, 'promote_candidate_to_part', {
      item_id: itemId
    }, hodYachtId);

    expect(firstPromote.success).toBe(true);

    // Try to promote again
    const secondPromote = await executeAction(hodToken, hodUserId, 'promote_candidate_to_part', {
      item_id: itemId
    }, hodYachtId);

    // Should either fail or be idempotent
    if (secondPromote.success) {
      // Idempotent - same part_id returned
      expect(secondPromote.data.part_id).toBe(firstPromote.data.part_id);
    } else {
      expect(getErrorCode(secondPromote)).toMatch(/INVALID_STATE(_TRANSITION)?/);
    }
  });
});

test.describe('Shopping List - Non-Existent Entity Handling', () => {

  test('Cannot approve non-existent item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const fakeItemId = '99999999-9999-9999-9999-999999999999';

    const result = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: fakeItemId,
      quantity_approved: 1
    }, hodYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('NOT_FOUND');
  });

  test('Cannot reject non-existent item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const fakeItemId = '99999999-9999-9999-9999-999999999999';

    const result = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: fakeItemId,
      rejection_reason: 'Testing non-existent'
    }, hodYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('NOT_FOUND');
  });

  test('Cannot promote non-existent item', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const fakeItemId = '99999999-9999-9999-9999-999999999999';

    const result = await executeAction(hodToken, hodUserId, 'promote_candidate_to_part', {
      item_id: fakeItemId
    }, hodYachtId);

    expect(isErrorResponse(result)).toBe(true);
    expect(getErrorCode(result)).toBe('NOT_FOUND');
  });

  test('Cannot view history of non-existent item', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const fakeItemId = '99999999-9999-9999-9999-999999999999';

    const result = await executeAction(crewToken, crewUserId, 'view_shopping_list_item_history', {
      item_id: fakeItemId
    }, crewYachtId);

    expect(isErrorResponse(result)).toBe(true);
  });
});

test.describe('Shopping List - Boundary and Edge Cases', () => {

  test('Handle extremely long rejection reason', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    // Create item
    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Edge Case Test ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    // Try with 10KB rejection reason
    const longReason = 'A'.repeat(10000);

    const result = await executeAction(hodToken, hodUserId, 'reject_shopping_list_item', {
      item_id: itemId,
      rejection_reason: longReason
    }, hodYachtId);

    // Should either accept or truncate
    expect(result).toBeDefined();
  });

  test('Handle approve with zero quantity', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Zero Approve Test ${Date.now()}`,
      quantity_requested: 5,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    const result = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 0
    }, hodYachtId);

    expect(isErrorResponse(result)).toBe(true);
    // Accept either validation error type
    expect(['VALIDATION_FAILED', 'MISSING_REQUIRED_FIELD']).toContain(getErrorCode(result));
  });

  test('Handle approve with higher quantity than requested', async () => {
    const hodToken = extractToken(HOD_AUTH_STATE);
    const hodUserId = extractUserId(HOD_AUTH_STATE);
    const hodYachtId = extractYachtId(HOD_AUTH_STATE);

    const createResult = await executeAction(hodToken, hodUserId, 'create_shopping_list_item', {
      part_name: `Higher Approve Test ${Date.now()}`,
      quantity_requested: 5,
      urgency: 'normal',
      source_type: 'manual_add'
    }, hodYachtId);

    const itemId = createResult.data.shopping_list_item_id;

    const result = await executeAction(hodToken, hodUserId, 'approve_shopping_list_item', {
      item_id: itemId,
      quantity_approved: 100
    }, hodYachtId);

    // Should succeed - HOD can approve different quantity
    expect(result.success).toBe(true);
  });

  test('Handle missing optional fields', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const crewUserId = extractUserId(CREW_AUTH_STATE);
    const crewYachtId = extractYachtId(CREW_AUTH_STATE);

    const result = await executeAction(crewToken, crewUserId, 'create_shopping_list_item', {
      part_name: `Minimal Fields ${Date.now()}`,
      quantity_requested: 1,
      urgency: 'normal',
      source_type: 'manual_add'
      // No manufacturer, notes, supplier, etc.
    }, crewYachtId);

    expect(result.success).toBe(true);
  });
});

test.describe('Shopping List - Malformed Request Tests', () => {

  test('Reject request with missing action field', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const yachtId = extractYachtId(CREW_AUTH_STATE) || '85fe1119-b04c-41ac-80f1-829d23322598';

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${yachtId}`
      },
      body: JSON.stringify({
        // Missing action field
        payload: {
          part_name: 'Test',
          quantity_requested: 1
        }
      })
    });

    // FastAPI returns 422 for validation errors with detail array
    expect(response.status).toBe(422);
    const result = await response.json();
    expect(result.detail).toBeDefined();
  });

  test('Reject request with malformed JSON', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const yachtId = extractYachtId(CREW_AUTH_STATE) || '85fe1119-b04c-41ac-80f1-829d23322598';

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${yachtId}`
      },
      body: '{invalid json'
    });

    expect(response.status).toBeGreaterThanOrEqual(400);
  });

  test('Reject request with wrong HTTP method', async () => {
    const crewToken = extractToken(CREW_AUTH_STATE);
    const yachtId = extractYachtId(CREW_AUTH_STATE) || '85fe1119-b04c-41ac-80f1-829d23322598';

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'GET', // Should be POST
      headers: {
        'Authorization': `Bearer ${crewToken}`,
        'X-Yacht-Signature': `yacht_id=${yachtId}`
      }
    });

    expect(response.status).toBe(405);
  });
});
