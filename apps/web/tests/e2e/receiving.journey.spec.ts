/**
 * Receiving Lens v1: Full Journey E2E Tests
 *
 * Tests the complete receiving workflow from creation to signed acceptance.
 *
 * Test Categories:
 * 1. HOD Flow - Create, upload, extract, accept with signature
 * 2. Crew Flow - Read-only, cannot mutate
 * 3. Image Upload - Proxy to image-processing with RLS
 * 4. Extraction - Advisory-only prepare mode (no auto-mutation)
 * 5. Signed Acceptance - PIN+TOTP validation
 * 6. Cross-Yacht Isolation - Wrong yacht JWT returns empty
 *
 * Security Invariants:
 * - yacht_id from auth (server-resolved), never client-provided
 * - RLS enforced via user JWT (no service key in request path)
 * - Signed actions require PIN+TOTP, write non-NULL signature to audit log
 * - Wrong-yacht access returns 200 [] (no data leakage)
 *
 * Based on:
 * - receiving_handlers.py (10 actions with RLS enforcement)
 * - action_router (validates yacht_id from auth vs context)
 * - pms_receiving RLS policies (get_user_yacht_id() + is_hod())
 * - image-processing (proxied upload with Authorization JWT)
 */

import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';
import { getTenantClient } from '../helpers/supabase_tenant';
import {
  TEST_YACHT_ID,
  getTestUserByRole,
} from '../fixtures/test_users';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = process.env.API_BASE_URL || 'https://pipeline-core.int.celeste7.ai';
const WEB_BASE_URL = process.env.WEB_BASE_URL || 'https://app.celeste7.ai';
const IMAGE_PROCESSOR_URL = process.env.IMAGE_PROCESSOR_URL || 'https://image-processing-givq.onrender.com';

// Test JWTs (from environment or test fixtures)
const HOD_JWT = process.env.HOD_JWT || process.env.CHIEF_ENGINEER_JWT;
const CAPTAIN_JWT = process.env.CAPTAIN_JWT || HOD_JWT;
const CREW_JWT = process.env.CREW_JWT;
const WRONG_YACHT_JWT = process.env.WRONG_YACHT_JWT;

// ============================================================================
// TEST DATA SETUP
// ============================================================================

let testReceivingId: string | null = null;
let testDocumentId: string | null = null;
let supabase: ReturnType<typeof getTenantClient>;
let apiClient: ApiClient;

test.beforeAll(async () => {
  if (!HOD_JWT) {
    throw new Error('HOD_JWT environment variable is required');
  }

  supabase = getTenantClient();
  apiClient = new ApiClient(API_BASE_URL);
});

// ============================================================================
// TEST 1: Smoke Test - Pages Load Without Errors
// ============================================================================

test.describe('Smoke Tests', () => {
  test('main page loads with no console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(WEB_BASE_URL);
    await expect(page).toHaveTitle(/Celeste/i);

    // Assert no console errors
    expect(consoleErrors, `Console errors detected: ${consoleErrors.join(', ')}`).toHaveLength(0);
  });

  test('login page loads with no console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(`${WEB_BASE_URL}/login`);

    // Assert no console errors
    expect(consoleErrors, `Console errors detected: ${consoleErrors.join(', ')}`).toHaveLength(0);
  });

  test('API health check returns healthy', async () => {
    const response = await fetch(`${API_BASE_URL}/health`);
    expect(response.status).toBe(200);

    const health = await response.json();
    expect(health.status).toBe('healthy');
    expect(health.pipeline_ready).toBe(true);
  });
});

// ============================================================================
// TEST 2: HOD Flow - Create Receiving
// ============================================================================

test.describe('HOD Flow: Create Receiving', () => {
  test('HOD can create receiving via Action Router', async () => {
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'create_receiving',
        context: {
          yacht_id: TEST_YACHT_ID, // Router validates this matches auth yacht_id
        },
        payload: {
          vendor_reference: `E2E-TEST-${Date.now()}`,
          vendor_name: 'Playwright Test Vendor',
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
    expect(result.receiving_id).toBeDefined();
    expect(result.receiving_status).toBe('draft');

    testReceivingId = result.receiving_id;
    console.log(`Created receiving: ${testReceivingId}`);
  });

  test('created receiving appears in database', async () => {
    expect(testReceivingId).not.toBeNull();

    const { data, error } = await supabase
      .from('pms_receiving')
      .select('*')
      .eq('id', testReceivingId)
      .eq('yacht_id', TEST_YACHT_ID)
      .single();

    expect(error).toBeNull();
    expect(data).toBeDefined();
    expect(data.status).toBe('draft');
    expect(data.yacht_id).toBe(TEST_YACHT_ID);
  });
});

// ============================================================================
// TEST 3: Image Upload (Proxy to image-processing)
// ============================================================================

test.describe('Image Upload', () => {
  test.skip('upload image via Cloud_PMS proxy to image-processing', async () => {
    // TODO: Implement after wiring proxy upload handler in Cloud_PMS
    // This test will:
    // 1. Create multipart form data with test image
    // 2. POST to Cloud_PMS /api/receiving/{receiving_id}/upload
    // 3. Cloud_PMS proxies to IMAGE_PROCESSOR_URL with Authorization JWT
    // 4. Assert document saved with correct storage_path
    // 5. Assert comment persisted in pms_receiving_documents

    expect(true).toBe(true); // Placeholder
  });
});

// ============================================================================
// TEST 4: Extraction (Advisory-Only Prepare Mode)
// ============================================================================

test.describe('Extraction Flow', () => {
  test('extract_receiving_candidates returns advisory results only', async () => {
    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'extract_receiving_candidates',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
          extraction_phase: 'prepare', // Advisory only
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
    expect(result.extraction_phase).toBe('prepare');
    expect(result.advisory_candidates).toBeDefined();

    // Verify NO auto-mutation: receiving should still be in draft status
    const { data: receiving } = await supabase
      .from('pms_receiving')
      .select('status')
      .eq('id', testReceivingId)
      .single();

    expect(receiving?.status).toBe('draft'); // NOT mutated by prepare
  });
});

// ============================================================================
// TEST 5: Signed Acceptance (PIN+TOTP Required)
// ============================================================================

test.describe('Signed Acceptance', () => {
  test('accept_receiving prepare returns confirmation token', async () => {
    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CAPTAIN_JWT}`, // Needs Captain role
      },
      body: JSON.stringify({
        action: 'accept_receiving',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
          signature_phase: 'prepare',
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
    expect(result.confirmation_token).toBeDefined();
    expect(result.signature_phase).toBe('prepare');
  });

  test.skip('accept_receiving execute requires PIN+TOTP signature', async () => {
    // TODO: Generate valid PIN+TOTP signature for test
    // This requires:
    // 1. Test user TOTP secret
    // 2. Generate current TOTP code
    // 3. Combine with PIN hash
    // 4. Call execute with signature payload

    expect(true).toBe(true); // Placeholder
  });
});

// ============================================================================
// TEST 6: Crew Flow - Read-Only Access
// ============================================================================

test.describe('Crew Flow: Read-Only', () => {
  test('crew can view receiving history', async () => {
    if (!CREW_JWT) {
      console.warn('CREW_JWT not set, skipping crew read test');
      return;
    }

    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CREW_JWT}`,
      },
      body: JSON.stringify({
        action: 'view_receiving_history',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
    expect(result.receiving).toBeDefined();
    expect(result.receiving.id).toBe(testReceivingId);
  });

  test('crew cannot create receiving (RLS denies)', async () => {
    if (!CREW_JWT) {
      console.warn('CREW_JWT not set, skipping crew mutation test');
      return;
    }

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CREW_JWT}`,
      },
      body: JSON.stringify({
        action: 'create_receiving',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          vendor_reference: `CREW-SHOULD-FAIL-${Date.now()}`,
        },
      }),
    });

    expect(response.status).toBe(403);

    const result = await response.json();
    expect(result.error_code).toBe('RLS_DENIED');
    expect(result.message.toLowerCase()).toContain('denied');
  });
});

// ============================================================================
// TEST 7: Cross-Yacht Isolation
// ============================================================================

test.describe('Cross-Yacht Isolation', () => {
  test('wrong-yacht JWT cannot access receiving data', async () => {
    if (!WRONG_YACHT_JWT) {
      console.warn('WRONG_YACHT_JWT not set, skipping isolation test');
      return;
    }

    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${WRONG_YACHT_JWT}`,
      },
      body: JSON.stringify({
        action: 'view_receiving_history',
        context: {
          yacht_id: TEST_YACHT_ID, // Different from JWT yacht_id
        },
        payload: {
          receiving_id: testReceivingId,
        },
      }),
    });

    // Expect 401 (auth rejection) or 403 (forbidden) or 200 with empty data (RLS filtering)
    expect([401, 403, 200]).toContain(response.status);

    if (response.status === 200) {
      const result = await response.json();
      // If 200, RLS should filter out the data (200 [] or NOT_FOUND)
      const hasData = result.receiving && Object.keys(result.receiving).length > 0;
      expect(hasData, 'Wrong-yacht JWT should not see receiving data').toBe(false);
    }
  });
});

// ============================================================================
// TEST 8: View History Returns Complete Data
// ============================================================================

test.describe('View History', () => {
  test('view_receiving_history returns all related data', async () => {
    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'view_receiving_history',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
    expect(result.receiving).toBeDefined();
    expect(result.items).toBeDefined();
    expect(result.documents).toBeDefined();
    expect(result.audit_trail).toBeDefined();

    // Verify received_by is UUID (not name - per spec)
    const receiving = result.receiving;
    expect(receiving.received_by).toBeDefined();
    if (receiving.received_by !== null) {
      expect(typeof receiving.received_by).toBe('string');
      expect(receiving.received_by).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    }
  });
});

// ============================================================================
// TEST 9: Storage Path Validation
// ============================================================================

test.describe('Storage Path Validation', () => {
  test('reject storage_path with "documents/" prefix', async () => {
    expect(testReceivingId).not.toBeNull();

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'attach_receiving_image_with_comment',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
          document_id: 'test-doc-123',
          storage_path: 'documents/invalid/path.jpg', // Invalid prefix
          comment: 'Should be rejected',
        },
      }),
    });

    expect(response.status).toBe(400);

    const result = await response.json();
    expect(result.error_code).toBe('INVALID_STORAGE_PATH');
    expect(result.message.toLowerCase()).toContain('documents/');
  });

  test('accept canonical storage_path', async () => {
    expect(testReceivingId).not.toBeNull();

    const validPath = `${TEST_YACHT_ID}/receiving/${testReceivingId}/test-image.jpg`;

    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'attach_receiving_image_with_comment',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {
          receiving_id: testReceivingId,
          document_id: `doc-${Date.now()}`,
          storage_path: validPath,
          doc_type: 'invoice',
          comment: 'Canonical path accepted',
        },
      }),
    });

    expect(response.status).toBe(200);

    const result = await response.json();
    expect(result.status).toBe('success');
  });
});

// ============================================================================
// TEST 10: Error Contract Validation
// ============================================================================

test.describe('Error Contract', () => {
  test('all error responses include error_code and message', async () => {
    // Test invalid action
    const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${HOD_JWT}`,
      },
      body: JSON.stringify({
        action: 'nonexistent_action',
        context: {
          yacht_id: TEST_YACHT_ID,
        },
        payload: {},
      }),
    });

    expect(response.status).toBeGreaterThanOrEqual(400);

    const result = await response.json();
    expect(result.error_code, 'Response must include error_code').toBeDefined();
    expect(result.message, 'Response must include message').toBeDefined();
    expect(typeof result.message).toBe('string');

    // Ensure no stack traces in error
    expect(result.message).not.toMatch(/Traceback|File "/);
  });
});

// ============================================================================
// CLEANUP
// ============================================================================

test.afterAll(async () => {
  // Clean up test data if needed
  if (testReceivingId) {
    console.log(`Test receiving ID: ${testReceivingId} (cleanup handled by DB cascade)`);
  }
});
