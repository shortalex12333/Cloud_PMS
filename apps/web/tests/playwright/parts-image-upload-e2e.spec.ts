/**
 * Parts Lens Image Upload MVP - E2E Journey Tests
 * ================================================
 *
 * Tests PR #195 (Image Upload) + PR #194 (RBAC Fix)
 *
 * Journeys:
 * 1. RBAC Fix: Crew creates work order (should succeed, not 403)
 * 2. Captain uploads part image
 * 3. HOD updates image description
 * 4. Captain deletes image (SIGNED action)
 * 5. Crew blocked from deleting image (403)
 *
 * Uses real parts from production database.
 */

import { test, expect, Page } from '@playwright/test';
import path from 'path';

// Test data - real parts from production
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
const TEST_PARTS = {
  TEAK_COMPOUND: '5dd34337-c4c4-41dd-9c6b-adf84af349a8',  // Teak Seam Compound
  WATER_PUMP: '2f452e3b-bf3e-464e-82d5-7d0bc849e6c0',     // Raw Water Pump Seal Kit
  CYLINDER_RING: '5543266b-2d8c-46a0-88e2-74a7ab403cdd',  // Cylinder Liner O-Ring Kit
};

// Test users - passwords from environment variables
const USERS = {
  CAPTAIN: {
    email: 'captain.tenant@alex-short.com',
    password: process.env.CAPTAIN_PASSWORD || '',
    userId: 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
    role: 'captain',
  },
  HOD: {
    email: 'hod.tenant@alex-short.com',
    password: process.env.HOD_PASSWORD || '',
    userId: '89b1262c-ff59-4591-b954-757cdf3d609d',
    role: 'chief_engineer',
  },
  CREW: {
    email: 'crew.tenant@alex-short.com',
    password: process.env.CREW_PASSWORD || '',
    userId: '2da12a4b-c0a1-4716-80ae-d29c90d98233',
    role: 'crew',
  },
};

const API_BASE = 'https://pipeline-core.int.celeste7.ai';
const WEB_BASE = process.env.WEB_BASE_URL || 'https://app.celeste7.ai';
const SUPABASE_URL = process.env.MASTER_SUPABASE_URL || 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const SUPABASE_ANON_KEY = process.env.MASTER_SUPABASE_ANON_KEY || '';

// Helper: Sign in user through Supabase Auth
async function signInUser(page: Page, email: string, password: string) {
  console.log(`  🔐 Signing in as ${email}...`);

  // Call Supabase Auth API directly
  const response = await page.request.post(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    headers: {
      'apikey': SUPABASE_ANON_KEY,
      'Content-Type': 'application/json',
    },
    data: {
      email,
      password,
    },
  });

  if (!response.ok()) {
    throw new Error(`Sign in failed: ${response.status()} - ${await response.text()}`);
  }

  const authData = await response.json();
  const accessToken = authData.access_token;
  const refreshToken = authData.refresh_token;

  // Set up Supabase session in localStorage
  await page.evaluateHandle(
    ({ token, refresh, user }) => {
      const session = {
        access_token: token,
        refresh_token: refresh,
        expires_at: Date.now() / 1000 + 3600,
        expires_in: 3600,
        token_type: 'bearer',
        user: user,
      };

      // Store in format expected by Supabase client
      localStorage.setItem(
        `sb-${window.location.hostname.split('.')[0]}-auth-token`,
        JSON.stringify(session)
      );
    },
    { token: accessToken, refresh: refreshToken, user: authData.user }
  );

  console.log(`  ✅ Signed in successfully (token expires in 60 minutes)`);
  return accessToken;
}

// Helper: Search for part via NLP
async function searchForPart(page: Page, query: string) {
  await page.goto(WEB_BASE);
  await page.waitForSelector('[data-testid="search-input"]', { timeout: 10000 });
  await page.fill('[data-testid="search-input"]', query);
  await page.press('[data-testid="search-input"]', 'Enter');
  await page.waitForSelector('[data-testid="search-results"]', { timeout: 10000 });
}

test.describe('Parts Image Upload MVP + RBAC Fix', () => {
  test.describe.configure({ mode: 'serial' });

  test('Journey 1: RBAC Fix - Crew creates DECK work order (PR #194)', async ({ page }) => {
    console.log('🧪 Testing CRITICAL RBAC fix (PR #194)');

    // Sign in as crew
    await signInUser(page, USERS.CREW.email, USERS.CREW.password);
    await page.goto(WEB_BASE);

    // Navigate to work orders
    await page.click('[data-testid="nav-work-orders"]');
    await page.waitForSelector('[data-testid="create-work-order-button"]');

    // Create new work order for DECK department
    await page.click('[data-testid="create-work-order-button"]');
    await page.waitForSelector('[data-testid="work-order-form"]');

    await page.fill('[data-testid="wo-title"]', 'E2E Test - Crew DECK Work Order');
    await page.selectOption('[data-testid="wo-department"]', 'deck');
    await page.selectOption('[data-testid="wo-priority"]', 'medium');
    await page.fill('[data-testid="wo-description"]', 'Testing RBAC fix - crew can create work orders');

    // Submit
    await page.click('[data-testid="wo-submit"]');

    // Should succeed (not 403)
    await page.waitForSelector('[data-testid="success-message"]', { timeout: 10000 });

    const successText = await page.textContent('[data-testid="success-message"]');
    expect(successText).toContain('Work order created');

    console.log('✅ RBAC Fix verified: Crew can create work orders');
  });

  test('Journey 2: Captain uploads part image via NLP search', async ({ page, context }) => {
    console.log('🧪 Testing image upload (Captain role)');

    // Sign in as captain
    await signInUser(page, USERS.CAPTAIN.email, USERS.CAPTAIN.password);

    // Search for part using NLP query
    await searchForPart(page, 'teak seam compound');

    // Click on first result
    await page.click('[data-testid="search-result"]:first-child');
    await page.waitForSelector('[data-testid="part-details"]');

    // Find and click upload image button
    await page.click('[data-testid="upload-part-image-button"]');
    await page.waitForSelector('[data-testid="image-upload-dialog"]');

    // Upload test image
    const testImagePath = path.join(__dirname, '..', '..', '..', '..', 'tmp', 'test-part-image.png');
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles(testImagePath);

    // Add description
    await page.fill('[data-testid="image-description"]', 'Teak compound - 1L container image');

    // Submit upload
    await page.click('[data-testid="confirm-upload"]');

    // Wait for success
    await page.waitForSelector('[data-testid="upload-success"]', { timeout: 15000 });

    // Verify image appears in UI
    await page.waitForSelector('[data-testid="part-image"]', { timeout: 5000 });
    const imageSrc = await page.getAttribute('[data-testid="part-image"]', 'src');
    expect(imageSrc).toContain('supabase.co/storage');
    expect(imageSrc).toContain(YACHT_ID); // Verify yacht isolation in path

    console.log('✅ Image uploaded successfully via frontend');
  });

  test('Journey 3: HOD updates image description', async ({ page }) => {
    console.log('🧪 Testing image metadata update (HOD role)');

    // Inject HOD JWT
    await signInUser(page, USERS.HOD.email, USERS.HOD.password);

    // Search for part with image
    await searchForPart(page, 'teak compound');
    await page.click('[data-testid="search-result"]:first-child');
    await page.waitForSelector('[data-testid="part-details"]');

    // Click edit image button
    await page.click('[data-testid="edit-image-button"]');
    await page.waitForSelector('[data-testid="image-edit-dialog"]');

    // Update description
    await page.fill('[data-testid="image-description"]', 'Updated: Teak compound for deck maintenance');

    // Save
    await page.click('[data-testid="save-image-changes"]');

    // Wait for success
    await page.waitForSelector('[data-testid="update-success"]', { timeout: 5000 });

    // Verify description updated
    const newDescription = await page.textContent('[data-testid="image-description-display"]');
    expect(newDescription).toContain('Updated: Teak compound');

    console.log('✅ Image description updated successfully');
  });

  test('Journey 4: Captain deletes image (SIGNED action)', async ({ page }) => {
    console.log('🧪 Testing image deletion (Captain - SIGNED action)');

    // Inject captain JWT
    await signInUser(page, USERS.CAPTAIN.email, USERS.CAPTAIN.password);

    // Navigate to part with image
    await searchForPart(page, 'teak compound');
    await page.click('[data-testid="search-result"]:first-child');
    await page.waitForSelector('[data-testid="part-details"]');

    // Click delete image button
    await page.click('[data-testid="delete-image-button"]');
    await page.waitForSelector('[data-testid="signature-dialog"]');

    // Provide signature (PIN + TOTP)
    await page.fill('[data-testid="pin-input"]', '1234');
    await page.fill('[data-testid="totp-input"]', '123456');
    await page.fill('[data-testid="delete-reason"]', 'E2E test - image deletion verification');

    // Confirm deletion
    await page.click('[data-testid="confirm-delete-with-signature"]');

    // Wait for success
    await page.waitForSelector('[data-testid="delete-success"]', { timeout: 10000 });

    // Verify image removed
    await expect(page.locator('[data-testid="part-image"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="no-image-placeholder"]')).toBeVisible();

    console.log('✅ Image deleted successfully (SIGNED action)');
  });

  test('Journey 5: Crew blocked from deleting image (403)', async ({ page }) => {
    console.log('🧪 Testing RBAC: Crew cannot delete images');

    // First upload image as captain
    await signInUser(page, USERS.CAPTAIN.email, USERS.CAPTAIN.password);
    await searchForPart(page, 'water pump seal kit');
    await page.click('[data-testid="search-result"]:first-child');
    await page.waitForSelector('[data-testid="part-details"]');

    // Quick upload
    await page.click('[data-testid="upload-part-image-button"]');
    const testImagePath = path.join(__dirname, '..', '..', '..', '..', 'tmp', 'test-part-image.png');
    await page.locator('input[type="file"]').setInputFiles(testImagePath);
    await page.click('[data-testid="confirm-upload"]');
    await page.waitForSelector('[data-testid="upload-success"]', { timeout: 10000 });

    // Now try to delete as crew (should be blocked)
    await signInUser(page, USERS.CREW.email, USERS.CREW.password);
    await page.reload();
    await page.waitForSelector('[data-testid="part-details"]');

    // Delete button should either not exist or be disabled
    const deleteButton = page.locator('[data-testid="delete-image-button"]');
    await expect(deleteButton).not.toBeVisible();

    console.log('✅ Crew correctly blocked from deleting images');
  });
});

test.describe('NLP Search → Document Surfacing', () => {
  test('Journey 6: Search for part by description, verify document content displayed', async ({ page }) => {
    console.log('🧪 Testing NLP search → document surfacing');

    // Inject HOD JWT
    await signInUser(page, USERS.HOD.email, USERS.HOD.password);
    await page.goto(WEB_BASE);

    // Natural language query
    await page.fill('[data-testid="search-input"]', 'raw water pump seal replacement parts');
    await page.press('[data-testid="search-input"]', 'Enter');

    // Wait for results
    await page.waitForSelector('[data-testid="search-results"]', { timeout: 10000 });

    // Verify results surface actual document content (not summaries)
    const firstResult = page.locator('[data-testid="search-result"]').first();
    await expect(firstResult).toBeVisible();

    // Click to see full document content
    await firstResult.click();
    await page.waitForSelector('[data-testid="document-content"]');

    // Verify document content is displayed (not summarized)
    const documentContent = await page.textContent('[data-testid="document-content"]');
    expect(documentContent).toBeTruthy();
    expect(documentContent!.length).toBeGreaterThan(100); // Full content, not summary

    // Verify actionable buttons present
    await expect(page.locator('[data-testid="action-buttons"]')).toBeVisible();

    console.log('✅ NLP search surfaced document content correctly');
  });
});

test.describe('Backend API Direct Tests', () => {
  test('API: Image upload endpoint returns presigned URL', async ({ request }) => {
    const response = await request.post(`${API_BASE}/v1/parts/upload-image`, {
      headers: {
        'Authorization': `Bearer ${USERS.CAPTAIN.jwt}`,
        'Content-Type': 'application/json',
      },
      data: {
        yacht_id: YACHT_ID,
        part_id: TEST_PARTS.TEAK_COMPOUND,
        file_name: 'test-image.png',
        mime_type: 'image/png',
        description: 'API test image',
      },
    });

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe('success');
    expect(body.presigned_upload_url).toContain('supabase.co/storage');
    expect(body.storage_path).toContain(YACHT_ID);

    console.log('✅ API: Upload endpoint working');
  });

  test('API: RBAC fix - Crew can create work order', async ({ request }) => {
    const response = await request.post(`${API_BASE}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${USERS.CREW.jwt}`,
        'Content-Type': 'application/json',
      },
      data: {
        action: 'create_work_order',
        context: { yacht_id: YACHT_ID },
        payload: {
          title: 'API Test - Crew Work Order',
          department: 'deck',
          priority: 'medium',
          description: 'Testing RBAC fix via API',
        },
      },
    });

    // Should be 200/201, not 403
    expect(response.status()).toBeLessThan(400);
    const body = await response.json();
    expect(body.status).toBe('success');

    console.log('✅ API: RBAC fix verified - Crew can create work orders');
  });
});
