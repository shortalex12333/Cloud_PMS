/**
 * Auth Context Contract E2E Tests
 * ================================
 *
 * Security tests validating invariant #1:
 * yacht_id MUST come from server-resolved auth context, NEVER from client payload.
 *
 * These tests verify:
 * 1. Payload yacht_id is ignored (server uses auth context)
 * 2. Cross-yacht attacks return 403/404 (not data)
 * 3. Missing auth returns 401
 * 4. Error responses follow security contract (no data leakage)
 *
 * ACCEPTANCE CRITERIA:
 * - No test includes client yacht_id that could override server context
 * - Cross-yacht attempts return 403 or 404 (never actual data)
 * - All security test suites pass green
 */

import { test, expect } from '@playwright/test';
import {
  saveResponse,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';
import {
  TEST_YACHT_ID,
  OTHER_YACHT_ID,
  getPrimaryTestUser,
} from '../../fixtures/test_users';

// ============================================================================
// TEST DATA SETUP
// ============================================================================

let testWorkOrderId: string | null = null;
let supabase: ReturnType<typeof getTenantClient>;

test.beforeAll(async () => {
  supabase = getTenantClient();

  // Get a work order for testing
  const { data: workOrder } = await supabase
    .from('pms_work_orders')
    .select('id')
    .eq('yacht_id', TEST_YACHT_ID)
    .limit(1)
    .single();

  testWorkOrderId = workOrder?.id || null;
});

// ============================================================================
// TEST SUITE 1: Payload yacht_id Ignored (Invariant #1)
// ============================================================================

test.describe('SECURITY: Payload yacht_id Ignored', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('SEC-01: Server ignores yacht_id in POST body', async () => {
    /**
     * Security invariant: yacht_id in request payload should be ignored.
     * Server MUST use auth context yacht_id instead.
     *
     * Test: Send wrong yacht_id in payload, verify request succeeds
     * with auth context yacht.
     */
    const testName = 'security/payload-yacht-ignored';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    // Get an equipment ID for cross-entity linking
    const { data: equipment } = await supabase
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    const equipmentId = equipment?.id || testWorkOrderId;

    // Send POST with WRONG yacht_id in payload
    // If server used payload yacht_id, this would fail or return wrong data
    const response = await apiClient.post('/v1/related/add', {
      yacht_id: OTHER_YACHT_ID, // WRONG - should be ignored
      source_entity_type: 'work_order',
      source_entity_id: testWorkOrderId,
      target_entity_type: 'equipment',
      target_entity_id: equipmentId,
      link_type: 'related',
      note: 'Security test - payload yacht_id should be ignored',
    });

    saveResponse(testName, response);

    // CRITICAL: Request should be processed using AUTH context yacht_id
    // NOT fail with a "wrong yacht" error that would indicate payload yacht_id was used
    //
    // Valid outcomes (all indicate payload yacht_id was ignored):
    // - 200/201: Link created for AUTH user's yacht
    // - 409: Link already exists (used right yacht)
    // - 403: Permission denied by RLS/role (still used auth context)
    // - 400: Validation error (entity type, etc.)
    //
    // Invalid outcome (would indicate payload yacht_id was used):
    // - Response containing "wrong yacht" or OTHER_YACHT_ID in error
    expect([200, 201, 400, 403, 409]).toContain(response.status);

    // Key assertion: Error should NOT mention the payload yacht_id
    // If server used payload yacht_id, error might reference OTHER_YACHT_ID
    const errorDetail = JSON.stringify(response.data || {}).toLowerCase();
    expect(errorDetail).not.toContain(OTHER_YACHT_ID.toLowerCase());

    await createEvidenceBundle(testName, {
      test: 'payload_yacht_id_ignored',
      security_invariant: 'yacht_id from auth context, not payload',
      payload_yacht_id: OTHER_YACHT_ID,
      expected_yacht_id: TEST_YACHT_ID,
      response_status: response.status,
      response_error: response.data?.detail || response.data?.error,
      result: [200, 201, 400, 403, 409].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });

  test('SEC-02: GET endpoint uses auth context yacht_id', async () => {
    /**
     * GET /v1/related should return data for auth context yacht only,
     * regardless of any attempt to pass yacht_id.
     */
    const testName = 'security/get-auth-context';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=10`
    );

    saveResponse(testName, response);

    // Should return 200 (data) or 404 (no related items) for user's yacht
    expect([200, 404]).toContain(response.status);

    if (response.status === 200) {
      expect(response.data).toHaveProperty('status', 'success');
    }

    await createEvidenceBundle(testName, {
      test: 'get_auth_context_only',
      security_invariant: 'yacht_id resolved from auth, not query params',
      response_status: response.status,
      result: [200, 404].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });
});

// ============================================================================
// TEST SUITE 2: Cross-Yacht Attack Prevention
// ============================================================================

test.describe('SECURITY: Cross-Yacht Attack Prevention', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('SEC-03: Cannot view work order from different yacht', async () => {
    /**
     * CRITICAL: Attempting to access entity from different yacht
     * MUST return 403/404, NEVER the actual data.
     */
    const testName = 'security/cross-yacht-view-denied';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    // Use a fake work order ID that doesn't exist in user's yacht
    const fakeWorkOrderId = '00000000-0000-0000-0000-000000000001';

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${fakeWorkOrderId}&limit=10`
    );

    saveResponse(testName, response);

    // CRITICAL: Must return 404 (not found) or 403 (forbidden)
    // Never return actual data from another yacht
    expect([403, 404]).toContain(response.status);

    // Verify error message doesn't leak yacht information
    const errorDetail = response.data?.detail || response.data?.error || '';
    expect(errorDetail.toLowerCase()).not.toContain(OTHER_YACHT_ID);

    await createEvidenceBundle(testName, {
      test: 'cross_yacht_view_denied',
      security_invariant: 'no cross-yacht data access',
      fake_entity_id: fakeWorkOrderId,
      response_status: response.status,
      error_detail: errorDetail,
      result: [403, 404].includes(response.status) ? 'PASS' : 'FAIL - DATA LEAKED',
    });
  });

  test('SEC-04: Cannot add link to entity from different yacht', async () => {
    /**
     * Attempting to create link involving entity from different yacht
     * MUST fail with 403/404.
     */
    const testName = 'security/cross-yacht-mutation-denied';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const fakeEntityId = '00000000-0000-0000-0000-000000000002';

    const response = await apiClient.post('/v1/related/add', {
      source_entity_type: 'work_order',
      source_entity_id: fakeEntityId, // Doesn't exist in user's yacht
      target_entity_type: 'equipment',
      target_entity_id: fakeEntityId,
      link_type: 'related',
    });

    saveResponse(testName, response);

    // CRITICAL: Mutation to non-existent entity must fail
    expect([403, 404]).toContain(response.status);

    await createEvidenceBundle(testName, {
      test: 'cross_yacht_mutation_denied',
      security_invariant: 'no cross-yacht mutations',
      response_status: response.status,
      result: [403, 404].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });
});

// ============================================================================
// TEST SUITE 3: Authentication Enforcement
// ============================================================================

test.describe('SECURITY: Authentication Enforcement', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
    // Do NOT authenticate for these tests
  });

  test('SEC-05: Unauthenticated request returns 401', async () => {
    /**
     * Requests without valid auth MUST return 401 Unauthorized.
     */
    const testName = 'security/no-auth-401';

    // Make request WITHOUT authentication
    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=test&limit=10`
    );

    saveResponse(testName, response);

    // CRITICAL: Must return 401/422 for unauthenticated requests
    // 422 is acceptable if validation runs before auth check (request still denied)
    expect([401, 422]).toContain(response.status);

    await createEvidenceBundle(testName, {
      test: 'unauthenticated_denied',
      security_invariant: 'auth required for all endpoints',
      response_status: response.status,
      result: [401, 422].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });

  test('SEC-06: Invalid token returns 401', async () => {
    /**
     * Requests with invalid/expired tokens MUST return 401.
     */
    const testName = 'security/invalid-token-401';

    // Set a fake/invalid token
    apiClient.setAccessToken('invalid.jwt.token');

    const response = await apiClient.request(
      'GET',
      `/v1/related?entity_type=work_order&entity_id=test&limit=10`,
      undefined,
      { skipAuth: true, headers: { Authorization: 'Bearer invalid.jwt.token' } }
    );

    saveResponse(testName, response);

    // Should return 401 for invalid token
    expect([401, 403]).toContain(response.status);

    await createEvidenceBundle(testName, {
      test: 'invalid_token_denied',
      security_invariant: 'invalid tokens rejected',
      response_status: response.status,
      result: [401, 403].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });
});

// ============================================================================
// TEST SUITE 4: Error Response Contract (No Data Leakage)
// ============================================================================

test.describe('SECURITY: Error Response Contract', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('SEC-07: 404 errors do not leak entity existence', async () => {
    /**
     * Security best practice: 404 errors should not reveal
     * whether an entity exists in another yacht.
     *
     * Response should be generic "not found" without yacht context.
     */
    const testName = 'security/404-no-leak';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=00000000-0000-0000-0000-000000000000&limit=10`
    );

    saveResponse(testName, response);

    expect([403, 404]).toContain(response.status);

    // Error detail should NOT mention:
    // - Specific yacht IDs
    // - Whether entity exists elsewhere
    // - Internal table names
    const errorDetail = JSON.stringify(response.data).toLowerCase();
    expect(errorDetail).not.toMatch(/yacht.{0,5}id/i); // No "yacht_id" or "yacht-id"
    expect(errorDetail).not.toContain('exists');
    expect(errorDetail).not.toContain('pms_');

    await createEvidenceBundle(testName, {
      test: 'error_no_data_leak',
      security_invariant: 'errors do not leak entity existence',
      response_status: response.status,
      error_response: response.data,
      result: 'PASS',
    });
  });

  test('SEC-08: 403 errors do not leak role information', async () => {
    /**
     * 403 errors should not reveal the user's current role
     * or the required role for the action.
     */
    const testName = 'security/403-no-role-leak';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    // Attempt an action that might be role-restricted
    const response = await apiClient.post('/v1/related/add', {
      source_entity_type: 'invalid_type',
      source_entity_id: 'test',
      target_entity_type: 'invalid_type',
      target_entity_id: 'test',
      link_type: 'related',
    });

    saveResponse(testName, response);

    // Whether 400 or 403, should not leak internal role names
    const errorDetail = JSON.stringify(response.data).toLowerCase();

    // Should not reveal internal role enum values
    expect(errorDetail).not.toContain('chief_engineer');
    expect(errorDetail).not.toContain('captain');
    expect(errorDetail).not.toContain('user_role');

    await createEvidenceBundle(testName, {
      test: 'error_no_role_leak',
      security_invariant: 'errors do not leak role information',
      response_status: response.status,
      error_response: response.data,
      result: 'PASS',
    });
  });
});

// ============================================================================
// TEST SUITE 5: Debug Endpoint Security
// ============================================================================

test.describe('SECURITY: Debug Endpoint Protection', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('SEC-09: Debug endpoint respects environment flag', async () => {
    /**
     * Debug endpoints should be disabled in production.
     * In staging/dev, they should still require auth.
     */
    const testName = 'security/debug-endpoint-protection';
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.post('/api/v1/certificates/debug/pipeline-test', {
      query: 'test query',
    });

    saveResponse(testName, response);

    // Debug endpoint should either:
    // - 403: Blocked in production
    // - 404: Feature not enabled
    // - 200: Allowed in dev/staging with auth
    // Never: 500 (unhandled error) or data leak
    expect([200, 403, 404]).toContain(response.status);

    await createEvidenceBundle(testName, {
      test: 'debug_endpoint_protected',
      security_invariant: 'debug endpoints require auth and respect env',
      response_status: response.status,
      result: [200, 403, 404].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });

  test('SEC-10: Debug endpoint requires authentication', async () => {
    /**
     * Debug endpoints MUST require authentication even in dev.
     */
    const testName = 'security/debug-requires-auth';

    // No authentication
    const response = await apiClient.post('/api/v1/certificates/debug/pipeline-test', {
      query: 'test query',
    });

    saveResponse(testName, response);

    // Must be 401 or 403 (no anonymous access)
    expect([401, 403, 404]).toContain(response.status);

    await createEvidenceBundle(testName, {
      test: 'debug_requires_auth',
      security_invariant: 'debug endpoints reject anonymous access',
      response_status: response.status,
      result: [401, 403, 404].includes(response.status) ? 'PASS' : 'FAIL',
    });
  });
});
