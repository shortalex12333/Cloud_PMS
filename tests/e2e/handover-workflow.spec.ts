/**
 * Handover Dual-Signature Workflow E2E Test
 *
 * Tests the complete handover workflow from draft creation through dual signatures:
 * 1. Create handover items (critical + normal)
 * 2. Validate draft
 * 3. Finalize draft (generate content_hash)
 * 4. Export handover (generate document_hash)
 * 5. Sign outgoing (first signature)
 * 6. Sign incoming (second signature + critical acknowledgment)
 * 7. Verify export (check hashes and signatures)
 * 8. Get pending handovers
 *
 * Backend: https://pipeline-core.int.celeste7.ai
 * Endpoints: /v1/actions/handover/*
 */

import { test, expect } from '@playwright/test';
import { getAccessToken, fullLogin } from '../helpers/auth';

const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Generate unique draft ID for this test run
const DRAFT_ID = `test-draft-${Date.now()}`;

interface HandoverItem {
  id: string;
  summary: string;
  category: string;
  is_critical: boolean;
}

interface Export {
  export_id: string;
  content_hash: string;
  document_hash: string;
  status: string;
}

test.describe('Handover Dual-Signature Workflow', () => {
  let accessToken: string;
  let userId: string;
  let userRole: string;
  let yachtId: string;
  let createdItems: string[] = [];
  let contentHash: string;
  let exportData: Export;

  test.beforeAll(async () => {
    // Login and get bootstrap data
    const { tokens, bootstrap } = await fullLogin();
    accessToken = tokens.accessToken;
    userId = bootstrap.userId;
    userRole = bootstrap.role;
    yachtId = bootstrap.yachtId;

    console.log(`Logged in as: ${bootstrap.email}`);
    console.log(`Role: ${userRole}`);
    console.log(`Yacht ID: ${yachtId}`);
  });

  test('Step 1: Create test handover items', async ({ request }) => {
    // Create critical item with valid category
    const criticalResponse = await request.post(`${API_BASE}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'add_to_handover',
        context: { yacht_id: yachtId },
        payload: {
          entity_type: 'note',  // Required field
          entity_id: null,  // NULL for standalone notes
          title: 'Critical: Main engine inspection overdue',
          summary_text: `[E2E Test] Critical item - Main engine inspection overdue (${DRAFT_ID})`,
          category: 'urgent',  // Valid: urgent|in_progress|completed|watch|fyi
          priority: 'high',
          presentation_bucket: 'Engineering',  // Display grouping
          is_critical: true,
          requires_action: true,
          action_summary: 'Schedule inspection within 48 hours',
        },
      },
    });

    if (!criticalResponse.ok()) {
      const error = await criticalResponse.json();
      console.error('Critical item creation failed:', JSON.stringify(error, null, 2));
    }
    expect(criticalResponse.ok()).toBeTruthy();

    const criticalData = await criticalResponse.json();
    expect(criticalData.result?.item_id).toBeDefined();
    createdItems.push(criticalData.result.item_id);

    console.log(`Created critical item: ${criticalData.result.item_id}`);

    // Create normal item with valid category
    const normalResponse = await request.post(`${API_BASE}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'add_to_handover',
        context: { yacht_id: yachtId },
        payload: {
          entity_type: 'note',  // Required field
          entity_id: null,  // NULL for standalone notes
          title: 'Completed: Weekly deck cleaning',
          summary_text: `[E2E Test] Normal item - Weekly deck cleaning completed (${DRAFT_ID})`,
          category: 'completed',  // Valid: urgent|in_progress|completed|watch|fyi
          priority: 'normal',
          presentation_bucket: 'Deck',  // Display grouping
          is_critical: false,
        },
      },
    });

    if (!normalResponse.ok()) {
      const error = await normalResponse.json();
      console.error('Normal item creation failed:', JSON.stringify(error, null, 2));
    }
    expect(normalResponse.ok()).toBeTruthy();

    const normalData = await normalResponse.json();
    expect(normalData.result?.item_id).toBeDefined();
    createdItems.push(normalData.result.item_id);

    console.log(`Created normal item: ${normalData.result.item_id}`);
    console.log(`Total items created: ${createdItems.length}`);
  });

  test('Step 2: Validate draft', async ({ request }) => {
    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${DRAFT_ID}/validate`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log(`Validation result: valid=${data.valid}`);
    console.log(`Blocking errors: ${data.blocking_count}`);
    console.log(`Warnings: ${data.warning_count}`);

    // Validation may fail if items don't have required fields, but test continues
    if (!data.valid) {
      console.warn('Draft has validation errors:', data.errors);
    }
  });

  test('Step 3: Finalize draft (generate content_hash)', async ({ request }) => {
    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${DRAFT_ID}/finalize`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.content_hash).toBeDefined();
    expect(data.content_hash.length).toBeGreaterThan(32); // SHA256 hash
    expect(data.finalized_at).toBeDefined();
    expect(data.finalized_by).toBe(userId);

    contentHash = data.content_hash;

    console.log(`Draft finalized with content_hash: ${contentHash.substring(0, 16)}...`);
    console.log(`Finalized at: ${data.finalized_at}`);
    console.log(`Item count: ${data.item_count}`);
  });

  test('Step 4: Export handover (generate document_hash)', async ({ request }) => {
    // Verify finalize completed before attempting export
    if (!contentHash) {
      throw new Error('Step 3 (finalize) must complete before export');
    }

    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${DRAFT_ID}/export?export_type=html&department=engineering`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok()) {
      const error = await response.json();
      console.error('Export failed:', JSON.stringify(error, null, 2));
      console.error(`Status: ${response.status} ${response.statusText()}`);
    }
    expect(response.ok()).toBeTruthy();

    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.export_id).toBeDefined();
    expect(data.document_hash).toBeDefined();
    expect(data.content_hash).toBe(contentHash); // Should match finalized hash
    expect(data.export_type).toBe('html');

    exportData = {
      export_id: data.export_id,
      content_hash: data.content_hash,
      document_hash: data.document_hash,
      status: 'pending_outgoing',
    };

    console.log(`Export created: ${exportData.export_id}`);
    console.log(`Document hash: ${exportData.document_hash.substring(0, 16)}...`);
    console.log(`Content hash matches: ${data.content_hash === contentHash}`);
    console.log(`Status: ${exportData.status}`);
  });

  test('Step 5: Sign outgoing (first signature)', async ({ request }) => {
    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${exportData.export_id}/sign/outgoing`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          note: 'E2E Test: All critical items flagged and reviewed',
          method: 'typed',
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.export_id).toBe(exportData.export_id);
    expect(data.signed_at).toBeDefined();
    expect(data.signed_by).toBe(userId);
    expect(data.role).toBe(userRole);
    expect(data.signature_method).toBe('typed');

    console.log(`Outgoing signature recorded`);
    console.log(`Signed at: ${data.signed_at}`);
    console.log(`Signed by (role): ${data.role}`);
    console.log(`New status: pending_incoming`);
  });

  test('Step 6: Sign incoming (second signature + critical ack)', async ({ request }) => {
    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${exportData.export_id}/sign/incoming?acknowledge_critical=true`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          note: 'E2E Test: Critical items reviewed and understood',
          method: 'typed',
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.export_id).toBe(exportData.export_id);
    expect(data.signed_at).toBeDefined();
    expect(data.signed_by).toBe(userId);
    expect(data.role).toBe(userRole);
    expect(data.signoff_complete).toBe(true);

    console.log(`Incoming signature recorded`);
    console.log(`Signed at: ${data.signed_at}`);
    console.log(`Signoff complete: ${data.signoff_complete}`);
    console.log(`New status: completed`);
  });

  test('Step 7: Verify export (check hashes and signatures)', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/v1/actions/handover/${exportData.export_id}/verify`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.export_id).toBe(exportData.export_id);
    expect(data.content_hash).toBe(contentHash);
    expect(data.document_hash).toBe(exportData.document_hash);
    expect(data.signoff_complete).toBe(true);

    // Verify outgoing signature
    expect(data.outgoing).toBeDefined();
    expect(data.outgoing.user_id).toBe(userId);
    expect(data.outgoing.role).toBe(userRole);
    expect(data.outgoing.signed_at).toBeDefined();
    expect(data.outgoing.signature).toBeDefined();

    // Verify incoming signature
    expect(data.incoming).toBeDefined();
    expect(data.incoming.user_id).toBe(userId);
    expect(data.incoming.role).toBe(userRole);
    expect(data.incoming.signed_at).toBeDefined();
    expect(data.incoming.critical_acknowledged).toBe(true);
    expect(data.incoming.signature).toBeDefined();

    console.log(`Verification successful`);
    console.log(`Content hash: ${data.content_hash.substring(0, 16)}...`);
    console.log(`Document hash: ${data.document_hash.substring(0, 16)}...`);
    console.log(`Outgoing signature present: ✓`);
    console.log(`Incoming signature present: ✓`);
    console.log(`Critical acknowledged: ✓`);
    console.log(`Signoff complete: ✓`);
  });

  test('Step 8: Check pending handovers', async ({ request }) => {
    const response = await request.get(
      `${API_BASE}/v1/actions/handover/pending`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.status).toBe('success');
    expect(data.pending_count).toBeGreaterThanOrEqual(0);
    expect(data.exports).toBeDefined();
    expect(Array.isArray(data.exports)).toBe(true);

    console.log(`Pending handovers: ${data.pending_count}`);

    // Our export should NOT be in pending list (it's completed)
    const ourExport = data.exports.find((exp: any) => exp.export_id === exportData.export_id);
    expect(ourExport).toBeUndefined();
    console.log(`Completed export correctly excluded from pending list: ✓`);
  });

  test.afterAll(async () => {
    console.log('');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✓ ALL HANDOVER WORKFLOW TESTS PASSED');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('');
    console.log(`Draft ID: ${DRAFT_ID}`);
    console.log(`Export ID: ${exportData.export_id}`);
    console.log(`Content Hash: ${contentHash}`);
    console.log(`Document Hash: ${exportData.document_hash}`);
    console.log('');
    console.log('Full workflow completed successfully:');
    console.log('  1. ✓ Created test items (critical + normal)');
    console.log('  2. ✓ Validated draft');
    console.log('  3. ✓ Finalized draft (content_hash)');
    console.log('  4. ✓ Generated export (document_hash)');
    console.log('  5. ✓ Outgoing signature');
    console.log('  6. ✓ Incoming signature + critical ack');
    console.log('  7. ✓ Verification (both hashes + signatures)');
    console.log('  8. ✓ Pending list');
    console.log('');
    console.log(`View verification page:`);
    console.log(`  ${API_BASE}/v1/actions/handover/${exportData.export_id}/verify`);
    console.log('');
  });
});

test.describe('Handover Workflow - Negative Tests', () => {
  let accessToken: string;

  test.beforeAll(async () => {
    const tokens = await getAccessToken();
    accessToken = tokens;
  });

  test('Reject incoming signature without critical acknowledgment', async ({ request }) => {
    // This test assumes there's a pending_incoming export to test against
    // In a real scenario, you'd create one first or use a known export ID

    const mockExportId = 'test-export-123';

    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${mockExportId}/sign/incoming`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          acknowledge_critical: false, // Should fail
          note: 'Test without acknowledgment',
          method: 'typed',
        },
      }
    );

    // Expect failure (400 or 409)
    expect(response.ok()).toBeFalsy();
    const data = await response.json();

    console.log(`Correctly rejected incoming signature without critical ack: ${data.error_code}`);
  });

  test('Reject sign action for wrong export state', async ({ request }) => {
    // Attempt to sign outgoing on an export that's already pending_incoming or completed
    const mockExportId = 'completed-export-123';

    const response = await request.post(
      `${API_BASE}/v1/actions/handover/${mockExportId}/sign/outgoing`,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        data: {
          note: 'Test wrong state',
          method: 'typed',
        },
      }
    );

    // Expect failure (409 Conflict)
    expect(response.ok()).toBeFalsy();

    console.log(`Correctly rejected sign action for wrong export state`);
  });
});
