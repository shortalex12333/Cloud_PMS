/**
 * Parts Image Upload - Deployment v2026.02.09.003
 * PR #195: Image upload MVP (upload/update/delete endpoints)
 *
 * Tests:
 * 1. Any role can upload image to part
 * 2. Update/replace existing image
 * 3. Delete image from part
 * 4. Upload endpoint returns 401/422 (not 404)
 */

import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const API_URL = 'https://pipeline-core.int.celeste7.ai';
const APP_URL = process.env.APP_URL || 'https://your-app-url.com';

// Test users
const USERS = {
  CREW: {
    email: 'crew.tenant@alex-short.com',
    password: process.env.CREW_PASSWORD || '',
    role: 'crew'
  },
  HOD: {
    email: 'hod.tenant@alex-short.com',
    password: process.env.HOD_PASSWORD || '',
    role: 'hod'
  },
  CAPTAIN: {
    email: 'captain.tenant@alex-short.com',
    password: process.env.CAPTAIN_PASSWORD || '',
    role: 'captain'
  }
};

// Create test image if it doesn't exist
const TEST_IMAGE_PATH = path.join(__dirname, 'test-part-image.png');
if (!fs.existsSync(TEST_IMAGE_PATH)) {
  // Create a simple 1x1 PNG
  const png = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    'base64'
  );
  fs.writeFileSync(TEST_IMAGE_PATH, png);
}

test.describe('Parts Image Upload - UI Journey', () => {

  for (const [roleName, user] of Object.entries(USERS)) {
    test(`${roleName} can upload image to part`, async ({ page }) => {
      // Login
      await page.goto(APP_URL);
      await page.fill('input[type="email"]', user.email);
      await page.fill('input[type="password"]', user.password);
      await page.click('button[type="submit"]');

      await page.waitForURL(/.*dashboard/, { timeout: 10000 });

      // Navigate to Parts
      await page.goto(`${APP_URL}/parts`);

      // Open first part
      const firstPart = page.locator('[data-testid="part-item"]').first();
      await firstPart.click();

      // Look for "Upload Image" or image upload button
      const uploadButton = page.locator('button:has-text("Upload Image"), button:has-text("Add Image")');
      await expect(uploadButton).toBeVisible();

      // Click upload
      await uploadButton.click();

      // File input should appear
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(TEST_IMAGE_PATH);

      // Confirm upload
      const confirmButton = page.locator('button:has-text("Upload"), button:has-text("Confirm")');
      await confirmButton.click();

      // Should see success message or uploaded image
      await expect(
        page.locator('text=/uploaded|success/i, img[src*="part"]')
      ).toBeVisible({ timeout: 10000 });
    });
  }

  test('CREW can update/replace part image', async ({ page }) => {
    // Login as crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.CREW.email);
    await page.fill('input[type="password"]', USERS.CREW.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to part with existing image
    await page.goto(`${APP_URL}/parts`);
    const partWithImage = page.locator('[data-testid="part-item"]').first();
    await partWithImage.click();

    // Should see existing image
    const existingImage = page.locator('img[src*="part"]');
    await expect(existingImage).toBeVisible();

    // Click "Update Image" or "Replace"
    const updateButton = page.locator('button:has-text("Update"), button:has-text("Replace")');
    await updateButton.click();

    // Upload new image
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(TEST_IMAGE_PATH);

    // Confirm
    await page.locator('button:has-text("Upload"), button:has-text("Confirm")').click();

    // Should see updated image or success message
    await expect(page.locator('text=/updated|replaced/i')).toBeVisible({ timeout: 10000 });
  });

  test('CREW can delete part image', async ({ page }) => {
    // Login as crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.CREW.email);
    await page.fill('input[type="password"]', USERS.CREW.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to part with image
    await page.goto(`${APP_URL}/parts`);
    const partWithImage = page.locator('[data-testid="part-item"]').first();
    await partWithImage.click();

    // Should see existing image
    const existingImage = page.locator('img[src*="part"]');
    if (await existingImage.count() > 0) {
      // Click delete button
      const deleteButton = page.locator('button:has-text("Delete"), button[aria-label="Delete image"]');
      await deleteButton.click();

      // Confirm deletion
      await page.locator('button:has-text("Confirm"), button:has-text("Delete")').click();

      // Image should be removed
      await expect(existingImage).not.toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Parts Image Upload - API Endpoints', () => {

  test('Upload endpoint returns 401 for unauthenticated (not 404)', async ({ request }) => {
    // Call upload endpoint without auth
    const response = await request.post(`${API_URL}/v1/parts/upload-image`, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    // Should be 401 (unauthorized), NOT 404 (endpoint exists)
    expect(response.status()).toBe(401);
  });

  test('Upload endpoint returns 422 for missing data (not 404)', async ({ request }) => {
    // Login first
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.CREW.email,
        password: USERS.CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Call upload endpoint with auth but no file
    const response = await request.post(`${API_URL}/v1/parts/upload-image`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        part_id: 'test-part-id'
        // Missing: image file
      }
    });

    // Should be 422 (validation error), NOT 404
    expect(response.status()).toBe(422);
  });

  test('CREW can upload image via API', async ({ request }) => {
    // Login
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.CREW.email,
        password: USERS.CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Upload image
    const formData = {
      part_id: 'test-part-id',
      image: fs.createReadStream(TEST_IMAGE_PATH)
    };

    const response = await request.post(`${API_URL}/v1/parts/upload-image`, {
      headers: {
        'Authorization': `Bearer ${access_token}`
      },
      multipart: formData
    });

    // Should succeed
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('image_url');
  });

  test('CREW can update image via API', async ({ request }) => {
    // Login
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.CREW.email,
        password: USERS.CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Update image
    const formData = {
      part_id: 'test-part-id',
      image: fs.createReadStream(TEST_IMAGE_PATH)
    };

    const response = await request.put(`${API_URL}/v1/parts/update-image`, {
      headers: {
        'Authorization': `Bearer ${access_token}`
      },
      multipart: formData
    });

    // Should succeed
    expect(response.status()).toBe(200);
  });

  test('CREW can delete image via API', async ({ request }) => {
    // Login
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.CREW.email,
        password: USERS.CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Delete image
    const response = await request.delete(`${API_URL}/v1/parts/delete-image`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        part_id: 'test-part-id'
      }
    });

    // Should succeed
    expect(response.status()).toBe(200);
  });
});
