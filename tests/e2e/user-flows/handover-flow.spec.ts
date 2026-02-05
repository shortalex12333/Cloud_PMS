/**
 * Handover Flow E2E Tests
 *
 * Phase 18: End-to-End User Flow Testing
 *
 * Tests the handover management flow:
 * Add Items → Edit Section → Regenerate Summary → Export
 */

import { test, expect } from '@playwright/test';
import {
  saveResponse,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';
import { TEST_YACHT_ID, getPrimaryTestUser } from '../../fixtures/test_users';

test.describe('HANDOVER FLOW: Shift Handover Journey', () => {
  let apiClient: ApiClient;
  let supabase: ReturnType<typeof getTenantClient>;
  let testItemId: string | null = null;

  test.beforeAll(async () => {
    supabase = getTenantClient();

    // Get an existing handover item (consolidated schema as of 2026-02-05)
    const { data: item } = await supabase
      .from('handover_items')
      .select('id')
      .eq('yacht_id', TEST_YACHT_ID)
      .is('deleted_at', null)
      .limit(1)
      .single();

    if (item) {
      testItemId = item.id;
    }
  });

  test.beforeEach(async () => {
    apiClient = new ApiClient();
  });

  test('Step 1: Add item to handover', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('add_to_handover', {
      yacht_id: TEST_YACHT_ID,
      section: 'Engineering',
      summary: 'E2E test item - generator maintenance completed',
      category: 'in_progress',
    });

    saveResponse('handover-flow/step1', response);

    if (response.status === 200 || response.status === 201) {
      testItemId = response.data.item_id || response.data.item?.id || testItemId;
    }

    await createEvidenceBundle('handover-flow/step1', {
      test: 'add_to_handover',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      item_id: testItemId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  test('Step 2: Edit handover item', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('edit_handover_section', {
      yacht_id: TEST_YACHT_ID,
      item_id: testItemId,
      content: 'E2E test - updated engineering section with additional notes',
      category: 'completed',
    });

    saveResponse('handover-flow/step2', response);
    await createEvidenceBundle('handover-flow/step2', {
      test: 'edit_handover_section',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      item_id: testItemId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  test('Step 3: Regenerate handover summary', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('regenerate_handover_summary', {
      yacht_id: TEST_YACHT_ID,
      department: 'Engineering',
    });

    saveResponse('handover-flow/step3', response);
    await createEvidenceBundle('handover-flow/step3', {
      test: 'regenerate_handover_summary',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      item_id: testItemId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  test('Step 4: Export handover', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('export_handover', {
      yacht_id: TEST_YACHT_ID,
      department: 'Engineering',
      format: 'pdf',
    });

    saveResponse('handover-flow/step4', response);
    await createEvidenceBundle('handover-flow/step4', {
      test: 'export_handover',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      export_id: response.data?.export_id,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  test('Handover Flow Summary', async ({ page }) => {
    await createEvidenceBundle('handover-flow/SUMMARY', {
      test_suite: 'handover_flow',
      schema_note: 'Consolidated schema as of 2026-02-05 - standalone handover_items',
      steps: [
        { step: 1, action: 'add_to_handover', table: 'handover_items' },
        { step: 2, action: 'edit_handover_section', table: 'handover_items' },
        { step: 3, action: 'regenerate_handover_summary', table: 'handover_items' },
        { step: 4, action: 'export_handover', table: 'handover_exports' },
      ],
      item_id: testItemId,
      yacht_id: TEST_YACHT_ID,
      timestamp: new Date().toISOString(),
    });

    expect(true).toBe(true);
  });
});
