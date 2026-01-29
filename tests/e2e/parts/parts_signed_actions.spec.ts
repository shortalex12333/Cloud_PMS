/**
 * E2E Tests: Signed Part Actions
 *
 * Validates that Captain can execute signed actions (write_off_part, adjust_stock_quantity)
 * with proper signature validation:
 * - Without signature: 400 validation error
 * - With valid signature (PIN/TOTP): 200 success
 *
 * Evidence: Network intercepts, screenshots of signature flows
 *
 * SECURITY MODEL (New):
 * - yacht_id is server-resolved from JWT auth (MASTER membership → TENANT role)
 * - NO client-provided yacht_id in action payloads
 * - SIGNED actions require signature (PIN/TOTP) from Captain/Manager
 * - Action Router enforces group permissions (READ/MUTATE/SIGNED/ADMIN)
 */

import { test, expect, Page } from '@playwright/test';
import { loginAsRole, RoleAuthState } from './helpers/roles-auth';
import * as path from 'path';
import * as fs from 'fs';

const TEST_PART_ID = process.env.TEST_PART_ID || '8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3';
const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts');

// Ensure artifacts directory exists
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

/**
 * Helper: Execute action via API
 */
async function executeActionViaAPI(
  jwt: string,
  action: string,
  payload: Record<string, any>,
  signature?: { type: string; value: string }
): Promise<{ statusCode: number; responseBody: any }> {
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${jwt}`,
    'Content-Type': 'application/json',
  };

  // NOTE: New security model - yacht_id derived from JWT auth, not client payload
  // Server resolves: MASTER membership → TENANT role → yacht_id from auth context
  const requestBody: any = {
    action,
    payload,
  };

  // Add signature if provided (for SIGNED-level actions)
  if (signature) {
    requestBody.signature = signature;
  }

  const response = await fetch(`${API_BASE}/v1/actions/execute`, {
    method: 'POST',
    headers,
    body: JSON.stringify(requestBody),
  });

  const body = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    responseBody: body,
  };
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
 * Helper: Navigate to parts page
 */
async function navigateToParts(page: Page, role: string): Promise<void> {
  await page.goto('/parts', { waitUntil: 'networkidle' });
  await page.waitForLoadState('domcontentloaded');

  const currentUrl = page.url();
  if (currentUrl.includes('/login')) {
    throw new Error(`Unexpected redirect to login for ${role}`);
  }
}

/**
 * Helper: Generate mock PIN signature for testing
 * In production, this would be the actual PIN from user input
 */
function generateMockPinSignature(): { type: string; value: string } {
  // This is a placeholder - in real tests, you'd need the actual PIN
  // For now, we'll test the negative case (without signature)
  // and document that positive signature tests require UI implementation
  return {
    type: 'pin',
    value: '123456', // Mock PIN - will likely fail in real scenario
  };
}

test.describe('Signed Actions (Captain)', () => {
  let captainAuthState: RoleAuthState;

  test.beforeAll(async () => {
    // Login as Captain once for all tests
    captainAuthState = await loginAsRole('captain');
  });

  test.use({
    // Use Captain storage state (saved by global-setup)
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'captain-state.json'),
  });

  test('write_off_part: Without signature (400)', async ({ page }) => {
    // Navigate to parts page
    await navigateToParts(page, 'captain');

    // Get JWT
    const jwt = await getJWTFromPage(page);

    // Execute write_off_part WITHOUT signature
    const response = await executeActionViaAPI(
      jwt,
      'write_off_part',
      {
        part_id: TEST_PART_ID,
        quantity: 1,
        reason: 'E2E Test - Damaged',
      }
      // No signature provided
    );

    // Assert 400 Bad Request (signature required)
    expect(response.statusCode).toBe(400);
    expect(response.responseBody).toHaveProperty('detail');

    // Verify error mentions signature
    const errorMessage = JSON.stringify(response.responseBody).toLowerCase();
    expect(
      errorMessage.includes('signature') ||
      errorMessage.includes('signed') ||
      errorMessage.includes('authorization')
    ).toBe(true);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'write_off_no_signature_400.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'write_off_part without signature',
      statusCode: response.statusCode,
      response: response.responseBody,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'write_off_no_signature_400.png'),
      fullPage: true,
    });
  });

  test('adjust_stock_quantity: Without signature (400)', async ({ page }) => {
    // Get JWT
    const jwt = await getJWTFromPage(page);

    // Execute adjust_stock_quantity WITHOUT signature
    const response = await executeActionViaAPI(
      jwt,
      'adjust_stock_quantity',
      {
        part_id: TEST_PART_ID,
        adjustment_quantity: 5,
        reason: 'E2E Test - Stock correction',
      }
      // No signature provided
    );

    // Assert 400 Bad Request (signature required)
    expect(response.statusCode).toBe(400);
    expect(response.responseBody).toHaveProperty('detail');

    // Verify error mentions signature
    const errorMessage = JSON.stringify(response.responseBody).toLowerCase();
    expect(
      errorMessage.includes('signature') ||
      errorMessage.includes('signed') ||
      errorMessage.includes('authorization')
    ).toBe(true);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'adjust_stock_no_signature_400.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'adjust_stock_quantity without signature',
      statusCode: response.statusCode,
      response: response.responseBody,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'adjust_stock_no_signature_400.png'),
      fullPage: true,
    });
  });

  test.skip('write_off_part: With PIN signature (200) - UI implementation pending', async ({ page }) => {
    /**
     * PENDING: This test requires the signature modal to be implemented in the UI.
     *
     * Expected flow:
     * 1. Click "Write Off" button
     * 2. Fill write-off form (quantity, reason)
     * 3. Submit form
     * 4. Signature modal appears
     * 5. Enter PIN (or TOTP)
     * 6. Submit signature
     * 7. Action executes with 200 response
     *
     * Test IDs needed:
     * - [data-testid="signature-modal"]
     * - [data-testid="signature-pin-input"]
     * - [data-testid="signature-totp-input"]
     * - [data-testid="signature-submit"]
     *
     * Once UI is implemented, remove .skip and implement:
     */

    await navigateToParts(page, 'captain');
    const jwt = await getJWTFromPage(page);

    // Search for part
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    await searchInput.fill('Engine Oil Filter');
    await searchInput.press('Enter');

    // Click write-off action
    const writeOffButton = page.locator('button[data-action-id="write_off_part"]').first();
    await writeOffButton.click();

    // Fill form
    const quantityInput = page.locator('[data-testid="quantity-input"]');
    await quantityInput.fill('1');

    const reasonInput = page.locator('[data-testid="reason-input"]');
    await reasonInput.fill('E2E Test - Damaged item');

    // Submit form (should trigger signature modal)
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Wait for signature modal
    const signatureModal = page.locator('[data-testid="signature-modal"]');
    await signatureModal.waitFor({ state: 'visible' });

    // Enter PIN
    const pinInput = page.locator('[data-testid="signature-pin-input"]');
    await pinInput.fill('123456'); // Use actual test PIN

    // Submit signature
    const signatureSubmit = page.locator('[data-testid="signature-submit"]');
    await signatureSubmit.click();

    // Wait for success toast
    const toast = page.locator('[data-testid="toast"], .toast, .notification').first();
    await toast.waitFor({ state: 'visible', timeout: 5000 });

    const toastText = await toast.textContent();
    expect(toastText?.toLowerCase()).toContain('success');

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'write_off_with_signature_200.png'),
      fullPage: true,
    });
  });

  test.skip('adjust_stock_quantity: With TOTP signature (200) - UI implementation pending', async ({ page }) => {
    /**
     * PENDING: This test requires the signature modal to be implemented in the UI.
     *
     * Expected flow:
     * 1. Click "Adjust Stock" button
     * 2. Fill adjustment form (adjustment_quantity, reason)
     * 3. Submit form
     * 4. Signature modal appears
     * 5. Enter TOTP code (or PIN)
     * 6. Submit signature
     * 7. Action executes with 200 response
     */

    await navigateToParts(page, 'captain');

    // Search for part
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    await searchInput.fill('Engine Oil Filter');
    await searchInput.press('Enter');

    // Click adjust stock action
    const adjustButton = page.locator('button[data-action-id="adjust_stock_quantity"]').first();
    await adjustButton.click();

    // Fill form
    const adjustmentInput = page.locator('[data-testid="adjustment-quantity-input"]');
    await adjustmentInput.fill('5');

    const reasonInput = page.locator('[data-testid="reason-input"]');
    await reasonInput.fill('E2E Test - Stock correction');

    // Submit form (should trigger signature modal)
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();

    // Wait for signature modal
    const signatureModal = page.locator('[data-testid="signature-modal"]');
    await signatureModal.waitFor({ state: 'visible' });

    // Enter TOTP
    const totpInput = page.locator('[data-testid="signature-totp-input"]');
    await totpInput.fill('123456'); // Use actual TOTP code

    // Submit signature
    const signatureSubmit = page.locator('[data-testid="signature-submit"]');
    await signatureSubmit.click();

    // Wait for success toast
    const toast = page.locator('[data-testid="toast"]').first();
    await toast.waitFor({ state: 'visible', timeout: 5000 });

    const toastText = await toast.textContent();
    expect(toastText?.toLowerCase()).toContain('success');

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'adjust_stock_with_signature_200.png'),
      fullPage: true,
    });
  });

  test('Signed actions: Backend validates signature requirement', async ({ page }) => {
    /**
     * This test confirms that the backend properly enforces signature requirements
     * for SIGNED-level actions, returning 400 when signature is missing.
     */

    const jwt = await getJWTFromPage(page);

    const signedActions = [
      {
        action: 'write_off_part',
        payload: { part_id: TEST_PART_ID, quantity: 1, reason: 'Test' },
      },
      {
        action: 'adjust_stock_quantity',
        payload: { part_id: TEST_PART_ID, adjustment_quantity: 1, reason: 'Test' },
      },
    ];

    const results: Array<{ action: string; statusCode: number; hasSignatureError: boolean }> = [];

    for (const scenario of signedActions) {
      const response = await executeActionViaAPI(
        jwt,
        scenario.action,
        scenario.payload
        // No signature
      );

      const errorMessage = JSON.stringify(response.responseBody).toLowerCase();
      const hasSignatureError =
        errorMessage.includes('signature') ||
        errorMessage.includes('signed') ||
        errorMessage.includes('authorization');

      results.push({
        action: scenario.action,
        statusCode: response.statusCode,
        hasSignatureError,
      });

      // Assert 400 and signature error
      expect(response.statusCode).toBe(400);
      expect(hasSignatureError).toBe(true);
    }

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'signed_actions_validation.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Signed actions - backend signature validation',
      results,
      allEnforced: results.every(r => r.statusCode === 400 && r.hasSignatureError),
      timestamp: new Date().toISOString(),
    }, null, 2));
  });
});
