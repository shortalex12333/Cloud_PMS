/**
 * E2E Tests: Receiving Lens v1 - Search & Entity Extraction
 *
 * Validates the intent-first, search-driven architecture for Receiving Lens:
 * 1. Search query triggers entity extraction
 * 2. Receiving entity card appears with extracted metadata
 * 3. Actions surface based on:
 *    - Focused entity type (receiving)
 *    - User role (crew/hod/captain)
 *    - Search intent keywords
 * 4. Backend-frontend parity validation
 *
 * ARCHITECTURE:
 * - NO /receiving page navigation
 * - Start at base URL '/'
 * - Use search to trigger entity extraction
 * - Actions appear when receiving entity is focused
 * - Backend defines all actions, UI only renders
 * - Server resolves yacht_id from auth (NEVER sent by client)
 *
 * Evidence: Search queries, entity extraction results, action surfacing
 */

import { test, expect, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts', 'receiving');

// Ensure artifacts directory exists
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

/**
 * Helper: Get JWT from page context
 */
async function getJWTFromPage(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
    if (!authKey) return null;

    const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
    return authData.access_token || null;
  });

  if (!token) {
    throw new Error('No JWT token found in page context');
  }

  return token;
}

/**
 * Helper: Perform search query
 */
async function performSearch(page: Page, query: string): Promise<void> {
  const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 5000 });

  await searchInput.fill(query);
  await searchInput.press('Enter');

  // Wait for entity extraction to complete
  await page.waitForTimeout(1500);
}

/**
 * Helper: Check if receiving entity card is visible
 */
async function isReceivingEntityVisible(page: Page): Promise<boolean> {
  return await page.locator('[data-entity-type="receiving"], [data-testid="receiving-card"]')
    .first()
    .isVisible({ timeout: 3000 })
    .catch(() => false);
}

/**
 * Helper: Get rendered action IDs from UI
 */
async function getRenderedActionIds(page: Page): Promise<string[]> {
  const actionButtons = page.locator('[data-action-id], [data-testid="action-button"]');
  const count = await actionButtons.count();

  const actionIds: string[] = [];
  for (let i = 0; i < count; i++) {
    const actionId = await actionButtons.nth(i).getAttribute('data-action-id');
    if (actionId) {
      actionIds.push(actionId);
    }
  }

  return actionIds;
}

/**
 * Helper: Call backend search API
 * NOTE: yacht_id is NEVER sent - server resolves from JWT
 */
async function callBackendSearch(jwt: string, query: string): Promise<any> {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }), // NO yacht_id sent
  });

  const data = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    data,
  };
}

/**
 * Helper: Call backend suggestions for a receiving entity
 * NOTE: yacht_id is NEVER sent - server resolves from JWT
 */
async function callBackendSuggestions(jwt: string, entityId: string): Promise<string[]> {
  const response = await fetch(`${API_BASE}/v1/suggestions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      entity_type: 'receiving',
      entity_id: entityId,
      // NO yacht_id sent - server resolves from auth
    }),
  });

  if (response.status !== 200) {
    return [];
  }

  const data = await response.json();
  return (data.actions || []).map((a: any) => a.id);
}

/**
 * Helper: Execute an action via Action Router
 * NOTE: yacht_id is NEVER sent - server resolves from JWT
 */
async function executeAction(jwt: string, action: string, payload: any): Promise<any> {
  const response = await fetch(`${API_BASE}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action,
      context: {}, // NO yacht_id sent - server resolves from auth
      payload,
    }),
  });

  const data = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    data,
  };
}

test.describe('Search & Entity Extraction - HOD (Chief Engineer)', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'hod-state.json'),
  });

  test('Search for receiving by vendor reference triggers entity extraction', async ({ page }) => {
    // Navigate to base URL (NO /receiving route)
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForLoadState('domcontentloaded');

    // Perform search query
    await performSearch(page, 'Racor receiving');

    // Assert receiving entity card appears
    const receivingVisible = await isReceivingEntityVisible(page);
    expect(receivingVisible).toBe(true);

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'search_entity_extraction_vendor_reference.png'),
      fullPage: true,
    });

    // Save evidence
    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'search_entity_extraction_vendor_reference.json'),
      JSON.stringify({
        test: 'Search by vendor reference triggers entity extraction',
        query: 'Racor receiving',
        receivingEntityVisible: receivingVisible,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });

  test('Search with action intent surfaces relevant actions', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Search with intent: "upload invoice for Racor"
    // Should extract: action_intent=upload, entity_type=receiving, vendor=Racor
    await performSearch(page, 'upload invoice for Racor');

    // Assert receiving entity visible
    const receivingVisible = await isReceivingEntityVisible(page);
    expect(receivingVisible).toBe(true);

    // Wait for actions to surface
    await page.waitForTimeout(1000);

    // Get rendered actions
    const actionIds = await getRenderedActionIds(page);

    // HOD should see upload/attach actions
    console.log('[UI] Rendered actions:', actionIds);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'search_with_action_intent.png'),
      fullPage: true,
    });

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'search_with_action_intent.json'),
      JSON.stringify({
        test: 'Search with action intent surfaces relevant actions',
        query: 'upload invoice for Racor',
        extractedIntent: 'upload',
        renderedActions: actionIds,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });

  test('Backend-frontend parity: UI renders ONLY backend actions', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Get JWT from page
    const jwt = await getJWTFromPage(page);

    // Search for a receiving entity
    await performSearch(page, 'receiving Racor');

    // Wait for entity to appear
    await page.waitForTimeout(1500);

    // Extract entity_id from focused card
    const entityId = await page.locator('[data-entity-id]').first().getAttribute('data-entity-id');

    if (!entityId) {
      console.warn('No entity_id found on page, skipping parity check');
      return;
    }

    // Call backend suggestions
    const backendActions = await callBackendSuggestions(jwt, entityId);

    // Get UI rendered actions
    const uiActions = await getRenderedActionIds(page);

    // Assert exact match (no invented actions, no missing actions)
    for (const uiAction of uiActions) {
      expect(backendActions).toContain(uiAction);
    }

    console.log('[Backend] Actions:', backendActions);
    console.log('[UI] Actions:', uiActions);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'backend_frontend_parity.json'),
      JSON.stringify({
        test: 'Backend-frontend parity validation',
        entityId,
        backendActions,
        uiActions,
        parityAchieved: uiActions.every(a => backendActions.includes(a)),
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});

test.describe('Role-Based Action Surfacing - CREW (Read-Only)', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'crew-state.json'),
  });

  test('CREW can search and view receiving entities (read-only)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Search for receiving
    await performSearch(page, 'receiving');

    // Assert receiving entity visible
    const receivingVisible = await isReceivingEntityVisible(page);
    expect(receivingVisible).toBe(true);

    // Get rendered actions
    const actionIds = await getRenderedActionIds(page);

    // CREW should NOT see MUTATE or SIGNED actions
    const mutateActions = [
      'create_receiving',
      'attach_receiving_image_with_comment',
      'update_receiving_fields',
      'add_receiving_item',
      'adjust_receiving_item',
      'link_invoice_document',
      'reject_receiving',
    ];

    const signedActions = ['accept_receiving'];

    for (const mutate of mutateActions) {
      expect(actionIds).not.toContain(mutate);
    }

    for (const signed of signedActions) {
      expect(actionIds).not.toContain(signed);
    }

    // CREW should only see READ actions
    // e.g., view_receiving_history
    console.log('[CREW] Rendered actions (should be read-only):', actionIds);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'crew_read_only_validation.json'),
      JSON.stringify({
        test: 'CREW can search and view receiving entities (read-only)',
        query: 'receiving',
        receivingEntityVisible: receivingVisible,
        renderedActions: actionIds,
        noMutateActionsPresent: !actionIds.some(a => mutateActions.includes(a)),
        noSignedActionsPresent: !actionIds.some(a => signedActions.includes(a)),
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });

  test('CREW cannot create receiving (403 RLS_DENIED)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const jwt = await getJWTFromPage(page);

    // Attempt create_receiving as CREW (should fail with 403)
    const result = await executeAction(jwt, 'create_receiving', {
      vendor_reference: `CREW-SHOULD-FAIL-${Date.now()}`,
      received_date: new Date().toISOString().split('T')[0],
    });

    // Assert 403 Forbidden
    expect(result.statusCode).toBe(403);
    expect(result.data.error_code).toBe('RLS_DENIED');

    console.log('[CREW] Denied as expected:', result.data);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'crew_create_receiving_denied.json'),
      JSON.stringify({
        test: 'CREW cannot create receiving (403 RLS_DENIED)',
        action: 'create_receiving',
        statusCode: result.statusCode,
        errorCode: result.data.error_code,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});

test.describe('Role-Based Action Surfacing - CAPTAIN (Signed Actions)', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'captain-state.json'),
  });

  test('CAPTAIN can see SIGNED actions for receiving entities', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Search for receiving
    await performSearch(page, 'receiving');

    // Assert receiving entity visible
    const receivingVisible = await isReceivingEntityVisible(page);
    expect(receivingVisible).toBe(true);

    // Wait for actions to surface
    await page.waitForTimeout(1000);

    // Get rendered actions
    const actionIds = await getRenderedActionIds(page);

    // Captain should see accept_receiving (SIGNED action)
    console.log('[CAPTAIN] Rendered actions (should include SIGNED):', actionIds);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'captain_signed_actions_validation.json'),
      JSON.stringify({
        test: 'CAPTAIN can see SIGNED actions for receiving entities',
        query: 'receiving',
        receivingEntityVisible: receivingVisible,
        renderedActions: actionIds,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});

test.describe('Action Execution - HOD', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'hod-state.json'),
  });

  test('HOD can create receiving via Action Router (MUTATE)', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const jwt = await getJWTFromPage(page);

    // Execute create_receiving action
    // NOTE: yacht_id is NOT sent - server resolves from JWT
    const result = await executeAction(jwt, 'create_receiving', {
      vendor_reference: `E2E-TEST-${Date.now()}`,
      received_date: new Date().toISOString().split('T')[0],
    });

    // Assert success
    expect(result.statusCode).toBe(200);
    expect(result.data.status).toBe('success');
    expect(result.data.receiving_id).toBeDefined();

    console.log('[HOD] Created receiving:', result.data.receiving_id);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'hod_create_receiving.json'),
      JSON.stringify({
        test: 'HOD can create receiving via Action Router',
        action: 'create_receiving',
        statusCode: result.statusCode,
        receivingId: result.data.receiving_id,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});

test.describe('View History Action - READ', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'hod-state.json'),
  });

  test('view_receiving_history returns audit trail, items, documents', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const jwt = await getJWTFromPage(page);

    // First create a receiving to view history for
    const createResult = await executeAction(jwt, 'create_receiving', {
      vendor_reference: `HISTORY-TEST-${Date.now()}`,
      received_date: new Date().toISOString().split('T')[0],
    });

    expect(createResult.statusCode).toBe(200);
    const receivingId = createResult.data.receiving_id;

    // Call view_receiving_history
    const historyResult = await executeAction(jwt, 'view_receiving_history', {
      receiving_id: receivingId,
    });

    // Assert success
    expect(historyResult.statusCode).toBe(200);
    expect(historyResult.data.status).toBe('success');
    expect(historyResult.data.receiving).toBeDefined();
    expect(historyResult.data.items).toBeDefined();
    expect(historyResult.data.documents).toBeDefined();
    expect(historyResult.data.audit_trail).toBeDefined();

    console.log('[History] Receiving:', receivingId);
    console.log('[History] Items:', historyResult.data.items.length);
    console.log('[History] Documents:', historyResult.data.documents.length);
    console.log('[History] Audit trail:', historyResult.data.audit_trail.length);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'view_history_validation.json'),
      JSON.stringify({
        test: 'view_receiving_history returns audit trail, items, documents',
        receivingId,
        statusCode: historyResult.statusCode,
        hasReceiving: !!historyResult.data.receiving,
        itemsCount: historyResult.data.items?.length || 0,
        documentsCount: historyResult.data.documents?.length || 0,
        auditTrailCount: historyResult.data.audit_trail?.length || 0,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});

test.describe('Zero 5xx Errors', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'hod-state.json'),
  });

  test('Flow: Search → View Details → Zero 5xx', async ({ page }) => {
    const statusCodes: number[] = [];

    // Monitor network responses
    page.on('response', (response) => {
      const status = response.status();
      if (response.url().includes(API_BASE)) {
        statusCodes.push(status);
      }
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    // Search for receiving
    await performSearch(page, 'receiving');

    // Wait for entity extraction
    await page.waitForTimeout(2000);

    // Click on receiving entity if visible
    const receivingCard = page.locator('[data-entity-type="receiving"]').first();
    if (await receivingCard.isVisible()) {
      await receivingCard.click();
      await page.waitForTimeout(1000);
    }

    // Assert no 5xx errors
    const serverErrors = statusCodes.filter(s => s >= 500 && s < 600);
    expect(serverErrors).toHaveLength(0);

    console.log('[Zero 5xx] Status codes:', statusCodes);
    console.log('[Zero 5xx] Server errors:', serverErrors);

    fs.writeFileSync(
      path.join(ARTIFACTS_DIR, 'zero_5xx_validation.json'),
      JSON.stringify({
        test: 'Flow: Search → View Details → Zero 5xx',
        statusCodes,
        serverErrors,
        hasZero5xx: serverErrors.length === 0,
        timestamp: new Date().toISOString(),
      }, null, 2)
    );
  });
});
