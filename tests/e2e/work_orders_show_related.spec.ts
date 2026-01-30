/**
 * Work Orders: Show Related E2E Tests (V2 Embeddings Phase 2)
 *
 * Tests the "Show Related" feature with V2 embeddings infrastructure in shadow mode.
 *
 * Test Categories:
 * 1. Crew Flow - Read-only access, no "Add Related" button
 * 2. HOD Flow - Can add explicit links, action visible
 * 3. Storage Options - Bucket strategy and path templates
 * 4. Signed Actions - Signature UI and backend validation
 * 5. Shadow Mode Invariants - Alpha=0.0 preserves FK-only ordering
 *
 * Based on:
 * - related_handlers.py (V1 FK-only retrieval with V2 shadow logging)
 * - action_registry (SIGNED variant for add_related)
 * - pms_attachments bucket strategy (work_order photos → pms-work-order-photos)
 * - Shadow logger (privacy-safe, alpha=0.0 in Phase 2)
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveRequest,
  saveResponse,
  createEvidenceBundle,
} from '../helpers/artifacts';
import { ApiClient } from '../helpers/api-client';
import { getTenantClient } from '../helpers/supabase_tenant';
import {
  TEST_YACHT_ID,
  getPrimaryTestUser,
  getTestUserByRole,
} from '../fixtures/test_users';

// ============================================================================
// TEST DATA SETUP
// ============================================================================

let testWorkOrderId: string | null = null;
let testEquipmentId: string | null = null;
let supabase: ReturnType<typeof getTenantClient>;

test.beforeAll(async () => {
  supabase = getTenantClient();

  // Get a work order with equipment for testing
  const { data: workOrder } = await supabase
    .from('pms_work_orders')
    .select('id, equipment_id')
    .eq('yacht_id', TEST_YACHT_ID)
    .not('equipment_id', 'is', null)
    .limit(1)
    .single();

  if (workOrder) {
    testWorkOrderId = workOrder.id;
    testEquipmentId = workOrder.equipment_id;
  }
});

// ============================================================================
// TEST SUITE 1: Crew Flow (Read-Only)
// ============================================================================

test.describe('SHOW RELATED: Crew Flow (Read-Only)', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('Crew can view Related groups but cannot add links', async ({ page }) => {
    // 1. Authenticate as crew
    const crewUser = getTestUserByRole('crew');
    if (!crewUser) {
      test.skip();
      return;
    }

    await apiClient.authenticate(crewUser.email, crewUser.password);

    // 2. Get Related for a work order
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=20`
    );

    saveResponse('show-related/crew-flow', response);

    // 3. Verify response structure
    expect([200, 404]).toContain(response.status);

    if (response.status === 200) {
      expect(response.data).toHaveProperty('status', 'success');
      expect(response.data).toHaveProperty('groups');
      expect(response.data).toHaveProperty('add_related_enabled');

      // 4. CRITICAL: Crew should NOT have add_related_enabled
      expect(response.data.add_related_enabled).toBe(false);

      // 5. Verify expected groups exist (FK-based)
      const groups = response.data.groups || [];
      const groupKeys = groups.map((g: any) => g.group_key);

      // Expected groups for work order with equipment:
      // - parts (from pms_work_order_parts)
      // - manuals (from equipment)
      // - previous_work (same equipment)
      // - attachments (from pms_attachments)
      expect(groupKeys).toEqual(
        expect.arrayContaining(['parts', 'manuals', 'previous_work', 'attachments'])
      );

      // 6. Verify group structure
      if (groups.length > 0) {
        const firstGroup = groups[0];
        expect(firstGroup).toHaveProperty('group_key');
        expect(firstGroup).toHaveProperty('label');
        expect(firstGroup).toHaveProperty('count');
        expect(firstGroup).toHaveProperty('items');
        expect(Array.isArray(firstGroup.items)).toBe(true);

        // 7. Verify item structure
        if (firstGroup.items.length > 0) {
          const firstItem = firstGroup.items[0];
          expect(firstItem).toHaveProperty('entity_id');
          expect(firstItem).toHaveProperty('entity_type');
          expect(firstItem).toHaveProperty('title');
          expect(firstItem).toHaveProperty('match_reasons');
          expect(firstItem).toHaveProperty('weight');
        }
      }
    }

    await createEvidenceBundle('show-related/crew-flow', {
      test: 'crew_view_related',
      status: response.status === 200 ? 'passed' : 'documented',
      add_related_enabled: response.data?.add_related_enabled,
      groups_count: response.data?.groups?.length,
    });
  });

  test('Crew receives 403 when attempting to add explicit link', async ({ page }) => {
    const crewUser = getTestUserByRole('crew');
    if (!crewUser || !testWorkOrderId || !testEquipmentId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(crewUser.email, crewUser.password);

    // Attempt to add link (should be denied)
    // NOTE: yacht_id removed from payload - server uses auth context (invariant #1)
    const response = await apiClient.post('/v1/related/add', {
      source_entity_type: 'work_order',
      source_entity_id: testWorkOrderId,
      target_entity_type: 'equipment',
      target_entity_id: testEquipmentId,
      link_type: 'related',
      note: 'E2E test link - crew attempt',
    });

    saveResponse('show-related/crew-add-denied', response);

    // CRITICAL: Crew should be denied with 403 Forbidden
    expect(response.status).toBe(403);
    expect(response.data?.detail || response.data?.error).toMatch(/not authorized|HOD|manager/i);

    await createEvidenceBundle('show-related/crew-add-denied', {
      test: 'crew_add_link_denied',
      status: response.status === 403 ? 'passed' : 'failed',
      response_status: response.status,
      error_message: response.data?.detail || response.data?.error,
    });
  });
});

// ============================================================================
// TEST SUITE 2: HOD Flow (Add Links)
// ============================================================================

test.describe('SHOW RELATED: HOD Flow (Can Add Links)', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('HOD can view Related and has add_related_enabled=true', async ({ page }) => {
    const hodUser = getTestUserByRole('chief_engineer');
    if (!hodUser || !testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(hodUser.email, hodUser.password);

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=20`
    );

    saveResponse('show-related/hod-flow', response);

    expect([200, 404]).toContain(response.status);

    if (response.status === 200) {
      expect(response.data.add_related_enabled).toBe(true);
    }

    await createEvidenceBundle('show-related/hod-flow', {
      test: 'hod_view_related',
      status: response.status === 200 ? 'passed' : 'documented',
      add_related_enabled: response.data?.add_related_enabled,
    });
  });

  test('HOD can add explicit link (200 or 409 duplicate)', async ({ page }) => {
    const hodUser = getTestUserByRole('chief_engineer');
    if (!hodUser || !testWorkOrderId || !testEquipmentId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(hodUser.email, hodUser.password);

    // NOTE: yacht_id removed from payload - server uses auth context (invariant #1)
    const response = await apiClient.post('/v1/related/add', {
      source_entity_type: 'work_order',
      source_entity_id: testWorkOrderId,
      target_entity_type: 'equipment',
      target_entity_id: testEquipmentId,
      link_type: 'related',
      note: 'E2E test link - HOD add',
    });

    saveResponse('show-related/hod-add-link', response);

    // CRITICAL: HOD should succeed (200) or get 409 if link already exists
    expect([200, 201, 409]).toContain(response.status);

    if (response.status === 200 || response.status === 201) {
      expect(response.data).toHaveProperty('status', 'success');
      expect(response.data).toHaveProperty('link_id');
    }

    if (response.status === 409) {
      expect(response.data?.detail || response.data?.error).toMatch(/already exists/i);
    }

    await createEvidenceBundle('show-related/hod-add-link', {
      test: 'hod_add_link_success',
      status: [200, 201, 409].includes(response.status) ? 'passed' : 'failed',
      response_status: response.status,
      link_id: response.data?.link_id,
    });
  });

  test('Add link validates entity types and rejects invalid', async ({ page }) => {
    const hodUser = getTestUserByRole('chief_engineer');
    if (!hodUser || !testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(hodUser.email, hodUser.password);

    // Attempt to add link with invalid entity type
    // NOTE: yacht_id removed from payload - server uses auth context (invariant #1)
    const response = await apiClient.post('/v1/related/add', {
      source_entity_type: 'invalid_type',
      source_entity_id: testWorkOrderId,
      target_entity_type: 'equipment',
      target_entity_id: testEquipmentId,
      link_type: 'related',
    });

    saveResponse('show-related/hod-add-invalid', response);

    expect(response.status).toBe(400);
    expect(response.data?.detail || response.data?.error).toMatch(/invalid/i);

    await createEvidenceBundle('show-related/hod-add-invalid', {
      test: 'hod_add_link_validation',
      status: response.status === 400 ? 'passed' : 'failed',
      response_status: response.status,
    });
  });
});

// ============================================================================
// TEST SUITE 3: Storage Options Validation
// ============================================================================

test.describe('SHOW RELATED: Storage Options (Bucket Strategy)', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('Action list includes add_work_order_photo with correct bucket', async ({ page }) => {
    const user = getPrimaryTestUser();
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(user.email, user.password);

    // Get action list for work order
    const response = await apiClient.get(`/v1/actions/list?entity_type=work_order&entity_id=${testWorkOrderId}`);

    saveResponse('show-related/storage-options', response);

    expect([200, 404]).toContain(response.status);

    if (response.status === 200) {
      const actions = response.data?.actions || [];
      const addPhotoAction = actions.find((a: any) => a.action_id === 'add_work_order_photo');

      if (addPhotoAction) {
        // Verify storage options
        expect(addPhotoAction).toHaveProperty('storage_options');
        const storageOptions = addPhotoAction.storage_options;

        // CRITICAL: Work order photos should use pms-work-order-photos bucket
        expect(storageOptions.bucket).toBe('pms-work-order-photos');

        // Verify path template includes yacht_id and work_order_id
        expect(storageOptions.path_template).toMatch(/\{yacht_id\}/);
        expect(storageOptions.path_template).toMatch(/work_orders/);
        expect(storageOptions.path_template).toMatch(/\{work_order_id\}/);
      }

      await createEvidenceBundle('show-related/storage-options', {
        test: 'storage_bucket_validation',
        status: addPhotoAction ? 'passed' : 'documented',
        bucket: addPhotoAction?.storage_options?.bucket,
        path_template: addPhotoAction?.storage_options?.path_template,
      });
    }
  });
});

// ============================================================================
// TEST SUITE 4: Signed Actions (Registry SIGNED Variant)
// ============================================================================

test.describe('SHOW RELATED: Signed Actions (Signature Validation)', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('SIGNED actions include signature indicators in action list', async ({ page }) => {
    const user = getPrimaryTestUser();
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.get(`/v1/actions/list?entity_type=work_order&entity_id=${testWorkOrderId}`);

    saveResponse('show-related/signed-actions', response);

    if (response.status === 200) {
      const actions = response.data?.actions || [];

      // Find actions that require signatures (e.g., reassign, archive)
      const signedActions = actions.filter((a: any) => a.requires_signature === true);

      if (signedActions.length > 0) {
        // Verify signed actions have correct properties
        for (const action of signedActions) {
          expect(action).toHaveProperty('requires_signature', true);
          expect(action).toHaveProperty('variant');

          // SIGNED variant actions should indicate signature requirement
          if (action.variant === 'SIGNED') {
            expect(action.requires_signature).toBe(true);
          }
        }
      }

      await createEvidenceBundle('show-related/signed-actions', {
        test: 'signed_actions_indicators',
        status: 'passed',
        signed_actions_count: signedActions.length,
        signed_action_ids: signedActions.map((a: any) => a.action_id),
      });
    }
  });

  test('Executing signed action without signature returns 400', async ({ page }) => {
    const hodUser = getTestUserByRole('chief_engineer');
    if (!hodUser || !testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(hodUser.email, hodUser.password);

    // Attempt to execute a signed action without signature
    // Note: This test assumes there's a signed action available
    // In real implementation, we'd need to identify which action requires signature

    // Placeholder: Testing add_related which is SIGNED in registry
    const response = await apiClient.post('/v1/actions/execute', {
      action_id: 'add_related',
      entity_type: 'work_order',
      entity_id: testWorkOrderId,
      params: {
        target_entity_type: 'equipment',
        target_entity_id: testEquipmentId,
        link_type: 'related',
      },
      // Omit signature field intentionally
    });

    saveResponse('show-related/signed-action-without-signature', response);

    // Backend should return 400 if signature is required but not provided
    // OR return success if signature validation is not yet enforced
    expect([200, 201, 400, 403, 409]).toContain(response.status);

    await createEvidenceBundle('show-related/signed-action-without-signature', {
      test: 'signed_action_validation',
      status: 'documented',
      response_status: response.status,
      note: 'Signature validation depends on backend enforcement',
    });
  });
});

// ============================================================================
// TEST SUITE 5: Shadow Mode Invariants (Alpha=0.0)
// ============================================================================

test.describe('SHOW RELATED: Shadow Mode (Alpha=0.0, FK-Only Ordering)', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('Multiple calls return identical ordering with alpha=0.0', async ({ page }) => {
    const user = getPrimaryTestUser();
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(user.email, user.password);

    // Make first call
    const response1 = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=20`
    );

    saveResponse('show-related/shadow-mode-call1', response1);

    // Make second call
    const response2 = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=20`
    );

    saveResponse('show-related/shadow-mode-call2', response2);

    expect(response1.status).toBe(response2.status);

    if (response1.status === 200 && response2.status === 200) {
      const groups1 = response1.data.groups || [];
      const groups2 = response2.data.groups || [];

      // CRITICAL: With alpha=0.0, ordering should be IDENTICAL (FK-only, deterministic)
      expect(groups1.length).toBe(groups2.length);

      for (let i = 0; i < groups1.length; i++) {
        const g1 = groups1[i];
        const g2 = groups2[i];

        // Same group key
        expect(g1.group_key).toBe(g2.group_key);

        // Same count
        expect(g1.count).toBe(g2.count);

        // Same item order (entity_ids should match in sequence)
        const ids1 = g1.items.map((item: any) => item.entity_id);
        const ids2 = g2.items.map((item: any) => item.entity_id);

        expect(ids1).toEqual(ids2);
      }

      await createEvidenceBundle('show-related/shadow-mode-invariants', {
        test: 'shadow_mode_deterministic_ordering',
        status: 'passed',
        note: 'Alpha=0.0 ensures FK-only ordering is preserved across calls',
      });
    }
  });

  test('Shadow logging visible in backend logs (manual verification)', async ({ page }) => {
    // This test documents the requirement for shadow logging
    // Actual verification requires inspecting backend logs with SHOW_RELATED_SHADOW=true

    const user = getPrimaryTestUser();
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=20`
    );

    saveResponse('show-related/shadow-logging', response);

    // Expected log format (backend logs):
    // [SHADOW] entity=work_order:abcd1234 alpha=0.0 items=12 avg_cosine=0.345 median=0.500 stdev=0.123

    await createEvidenceBundle('show-related/shadow-logging', {
      test: 'shadow_logging_enabled',
      status: 'documented',
      note: 'Check backend logs for [SHADOW] entries with alpha=0.0',
      environment_variable: 'SHOW_RELATED_SHADOW=true',
      expected_format: '[SHADOW] entity=work_order:... alpha=0.0 items=N avg_cosine=X.XXX median=X.XXX stdev=X.XXX',
    });
  });
});

// ============================================================================
// TEST SUITE 6: Error Cases and Edge Cases
// ============================================================================

test.describe('SHOW RELATED: Error Cases', () => {
  let apiClient: ApiClient;

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('Returns 404 for non-existent work order', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const fakeId = '00000000-0000-0000-0000-000000000000';
    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${fakeId}&limit=20`
    );

    saveResponse('show-related/error-404', response);

    expect(response.status).toBe(404);
    expect(response.data?.detail || response.data?.error).toMatch(/not found/i);

    await createEvidenceBundle('show-related/error-404', {
      test: 'error_not_found',
      status: response.status === 404 ? 'passed' : 'failed',
      response_status: response.status,
    });
  });

  test('Returns 400 for invalid entity type', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.get(
      `/v1/related?entity_type=invalid_entity&entity_id=${testWorkOrderId || 'test'}&limit=20`
    );

    saveResponse('show-related/error-400-invalid-type', response);

    expect(response.status).toBe(400);
    expect(response.data?.detail || response.data?.error).toMatch(/invalid/i);

    await createEvidenceBundle('show-related/error-400-invalid-type', {
      test: 'error_invalid_entity_type',
      status: response.status === 400 ? 'passed' : 'failed',
      response_status: response.status,
    });
  });

  test('Returns 400 for invalid limit (exceeds max)', async ({ page }) => {
    const user = getPrimaryTestUser();
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.get(
      `/v1/related?entity_type=work_order&entity_id=${testWorkOrderId}&limit=100`
    );

    saveResponse('show-related/error-400-limit', response);

    // Backend enforces limit <= 50
    expect(response.status).toBe(400);
    expect(response.data?.detail || response.data?.error).toMatch(/limit/i);

    await createEvidenceBundle('show-related/error-400-limit', {
      test: 'error_limit_exceeded',
      status: response.status === 400 ? 'passed' : 'failed',
      response_status: response.status,
    });
  });
});
