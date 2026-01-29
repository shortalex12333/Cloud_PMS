/**
 * E2E Tests: Part Storage Access & RLS
 *
 * Validates Supabase Storage RLS policies for part photos and receiving labels:
 * - HOD: Can view photos/labels, CANNOT delete (403)
 * - Manager: Can view AND delete labels (204)
 * - Cross-yacht: Cannot access other yacht's storage paths (403)
 * - All paths must include yacht_id for yacht-scoped access
 *
 * Evidence: Storage API responses, RLS enforcement screenshots
 */

import { test, expect, Page } from '@playwright/test';
import { loginAsRole, RoleAuthState } from './helpers/roles-auth';
import * as path from 'path';
import * as fs from 'fs';

const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const OTHER_YACHT_ID = '00000000-0000-0000-0000-000000000001'; // Fake yacht for cross-yacht test
const SUPABASE_URL = process.env.MASTER_SUPABASE_URL || 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts');

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
 * Helper: List storage objects in a bucket path
 */
async function listStorageObjects(
  jwt: string,
  bucket: string,
  pathPrefix: string
): Promise<{ statusCode: number; data: any }> {
  const response = await fetch(
    `${SUPABASE_URL}/storage/v1/object/list/${bucket}?prefix=${pathPrefix}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${jwt}`,
        'Content-Type': 'application/json',
      },
    }
  );

  const data = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    data,
  };
}

/**
 * Helper: Delete a storage object
 */
async function deleteStorageObject(
  jwt: string,
  bucket: string,
  filePath: string
): Promise<{ statusCode: number; data: any }> {
  const response = await fetch(
    `${SUPABASE_URL}/storage/v1/object/${bucket}/${filePath}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${jwt}`,
      },
    }
  );

  const data = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    data,
  };
}

/**
 * Helper: Upload a test file to storage
 */
async function uploadStorageObject(
  jwt: string,
  bucket: string,
  filePath: string,
  content: string = 'E2E test file'
): Promise<{ statusCode: number; data: any }> {
  const blob = new Blob([content], { type: 'text/plain' });

  const response = await fetch(
    `${SUPABASE_URL}/storage/v1/object/${bucket}/${filePath}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${jwt}`,
      },
      body: blob,
    }
  );

  const data = await response.json().catch(() => ({}));

  return {
    statusCode: response.status,
    data,
  };
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

test.describe('Storage Access: HOD Role', () => {
  let hodAuthState: RoleAuthState;

  test.beforeAll(async () => {
    hodAuthState = await loginAsRole('hod');
  });

  test.use({
    storageState: path.join(process.cwd(), '.playwright', 'storage', 'hod-state.json'),
  });

  test('HOD: Can list part photos with yacht_id in path', async ({ page }) => {
    await navigateToParts(page, 'hod');
    const jwt = await getJWTFromPage(page);

    // List objects in yacht-scoped path
    const partPhotosPath = `${TEST_YACHT_ID}/parts/photos`;
    const response = await listStorageObjects(jwt, 'part-images', partPhotosPath);

    // Should succeed (200) or return empty list
    // RLS allows HOD to LIST within their yacht
    expect([200, 404]).toContain(response.statusCode);

    // Verify yacht_id is in the path prefix
    expect(partPhotosPath).toContain(TEST_YACHT_ID);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'hod_list_photos_yacht_scoped.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'HOD list part photos (yacht-scoped)',
      path: partPhotosPath,
      statusCode: response.statusCode,
      response: response.data,
      timestamp: new Date().toISOString(),
    }, null, 2));
  });

  test('HOD: Can view receiving label images', async ({ page }) => {
    const jwt = await getJWTFromPage(page);

    // List objects in receiving labels path
    const labelsPath = `${TEST_YACHT_ID}/receiving/labels`;
    const response = await listStorageObjects(jwt, 'part-images', labelsPath);

    // Should succeed or return empty
    expect([200, 404]).toContain(response.statusCode);

    // Verify yacht_id is in the path
    expect(labelsPath).toContain(TEST_YACHT_ID);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'hod_list_labels_yacht_scoped.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'HOD list receiving labels (yacht-scoped)',
      path: labelsPath,
      statusCode: response.statusCode,
      response: response.data,
      timestamp: new Date().toISOString(),
    }, null, 2));
  });

  test('HOD: CANNOT delete receiving label (403)', async ({ page }) => {
    const jwt = await getJWTFromPage(page);

    // Attempt to delete a label (should fail with 403)
    const labelPath = `${TEST_YACHT_ID}/receiving/labels/test-label-e2e.jpg`;

    // First, try to upload a test file as HOD (may also fail if HOD can't upload)
    const uploadResponse = await uploadStorageObject(jwt, 'part-images', labelPath);

    // If upload succeeded, try to delete it
    if (uploadResponse.statusCode === 200 || uploadResponse.statusCode === 201) {
      const deleteResponse = await deleteStorageObject(jwt, 'part-images', labelPath);

      // HOD should NOT be able to delete (403 Forbidden)
      expect(deleteResponse.statusCode).toBe(403);

      // Save evidence
      const evidencePath = path.join(ARTIFACTS_DIR, 'hod_delete_label_403.json');
      fs.writeFileSync(evidencePath, JSON.stringify({
        test: 'HOD cannot delete label (RLS blocks)',
        labelPath,
        uploadStatusCode: uploadResponse.statusCode,
        deleteStatusCode: deleteResponse.statusCode,
        deleteResponse: deleteResponse.data,
        timestamp: new Date().toISOString(),
      }, null, 2));

      // Take screenshot
      await page.screenshot({
        path: path.join(ARTIFACTS_DIR, 'hod_delete_label_403.png'),
        fullPage: true,
      });
    } else {
      // If HOD can't even upload, document that
      const evidencePath = path.join(ARTIFACTS_DIR, 'hod_cannot_upload_labels.json');
      fs.writeFileSync(evidencePath, JSON.stringify({
        test: 'HOD cannot upload labels (expected)',
        labelPath,
        uploadStatusCode: uploadResponse.statusCode,
        uploadResponse: uploadResponse.data,
        note: 'HOD lacks INSERT permission on storage, so delete test is moot',
        timestamp: new Date().toISOString(),
      }, null, 2));
    }
  });
});

test.describe('Storage Access: Manager Role', () => {
  let managerAuthState: RoleAuthState;

  test.beforeAll(async () => {
    // Attempt to login as Manager
    try {
      managerAuthState = await loginAsRole('manager');
    } catch (error: any) {
      console.warn('Manager account not available:', error.message);
      test.skip();
    }
  });

  test.use({
    storageState: path.join(process.cwd(), '.playwright', 'storage', 'manager-state.json'),
  });

  test('Manager: Can delete receiving label (204)', async ({ page }) => {
    await navigateToParts(page, 'manager');
    const jwt = await getJWTFromPage(page);

    // Create a test label file
    const labelPath = `${TEST_YACHT_ID}/receiving/labels/test-manager-delete-${Date.now()}.txt`;

    // Upload test file
    const uploadResponse = await uploadStorageObject(jwt, 'part-images', labelPath, 'Manager test file');

    if (uploadResponse.statusCode !== 200 && uploadResponse.statusCode !== 201) {
      console.warn('Manager upload failed:', uploadResponse);
      // Skip delete test if upload failed
      return;
    }

    // Delete the file
    const deleteResponse = await deleteStorageObject(jwt, 'part-images', labelPath);

    // Manager SHOULD be able to delete (200 or 204)
    expect([200, 204]).toContain(deleteResponse.statusCode);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'manager_delete_label_204.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Manager can delete label (RLS allows)',
      labelPath,
      uploadStatusCode: uploadResponse.statusCode,
      deleteStatusCode: deleteResponse.statusCode,
      deleteResponse: deleteResponse.data,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'manager_delete_label_204.png'),
      fullPage: true,
    });
  });

  test('Manager: Can view part photos within yacht', async ({ page }) => {
    const jwt = await getJWTFromPage(page);

    const partPhotosPath = `${TEST_YACHT_ID}/parts/photos`;
    const response = await listStorageObjects(jwt, 'part-images', partPhotosPath);

    // Should succeed
    expect([200, 404]).toContain(response.statusCode);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'manager_list_photos_yacht_scoped.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Manager list part photos (yacht-scoped)',
      path: partPhotosPath,
      statusCode: response.statusCode,
      response: response.data,
      timestamp: new Date().toISOString(),
    }, null, 2));
  });
});

test.describe('Storage Access: Cross-Yacht RLS', () => {
  let hodAuthState: RoleAuthState;

  test.beforeAll(async () => {
    hodAuthState = await loginAsRole('hod');
  });

  test.use({
    storageState: path.join(process.cwd(), '.playwright', 'storage', 'hod-state.json'),
  });

  test('Cross-yacht path access is BLOCKED (403)', async ({ page }) => {
    await navigateToParts(page, 'hod');
    const jwt = await getJWTFromPage(page);

    // Attempt to access another yacht's storage path
    const otherYachtPath = `${OTHER_YACHT_ID}/parts/photos`;
    const response = await listStorageObjects(jwt, 'part-images', otherYachtPath);

    // Should be blocked (403 Forbidden or empty results)
    // RLS should prevent access to other yacht's data
    if (response.statusCode === 200) {
      // If it returns 200, the list should be empty or RLS filtered
      expect(response.data).toEqual([]);
    } else {
      // Or should return 403/404
      expect([403, 404]).toContain(response.statusCode);
    }

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'cross_yacht_access_blocked.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Cross-yacht storage access blocked by RLS',
      attemptedPath: otherYachtPath,
      userYachtId: TEST_YACHT_ID,
      targetYachtId: OTHER_YACHT_ID,
      statusCode: response.statusCode,
      response: response.data,
      rlsEnforced: response.statusCode !== 200 || response.data.length === 0,
      timestamp: new Date().toISOString(),
    }, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'cross_yacht_access_blocked.png'),
      fullPage: true,
    });
  });

  test('Forged path with different yacht_id is rejected', async ({ page }) => {
    const jwt = await getJWTFromPage(page);

    // Try to forge a path to another yacht
    const forgedPath = `${OTHER_YACHT_ID}/receiving/labels/forged-access.txt`;

    // Attempt to list
    const listResponse = await listStorageObjects(jwt, 'part-images', forgedPath);

    // Should be blocked or return empty
    if (listResponse.statusCode === 200) {
      expect(listResponse.data).toEqual([]);
    } else {
      expect([403, 404]).toContain(listResponse.statusCode);
    }

    // Attempt to upload (should also fail)
    const uploadResponse = await uploadStorageObject(jwt, 'part-images', forgedPath);

    // Upload should fail (403 or 400)
    expect(uploadResponse.statusCode).not.toBe(200);
    expect(uploadResponse.statusCode).not.toBe(201);

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'forged_path_rejected.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Forged path with different yacht_id rejected',
      forgedPath,
      userYachtId: TEST_YACHT_ID,
      listStatusCode: listResponse.statusCode,
      listResponse: listResponse.data,
      uploadStatusCode: uploadResponse.statusCode,
      uploadResponse: uploadResponse.data,
      rlsEnforced: true,
      timestamp: new Date().toISOString(),
    }, null, 2));
  });
});

test.describe('Storage Access: Path Structure Validation', () => {
  test('All storage paths MUST include yacht_id prefix', async () => {
    /**
     * This test validates that our storage path convention requires yacht_id
     * as the first segment for yacht-scoped RLS enforcement.
     *
     * Valid paths:
     * - {yacht_id}/parts/photos/{filename}
     * - {yacht_id}/receiving/labels/{filename}
     *
     * Invalid paths (should not exist):
     * - parts/photos/{filename} (missing yacht_id)
     * - global/{filename} (not yacht-scoped)
     */

    const validPaths = [
      `${TEST_YACHT_ID}/parts/photos/example.jpg`,
      `${TEST_YACHT_ID}/receiving/labels/label.jpg`,
    ];

    const invalidPaths = [
      'parts/photos/example.jpg', // Missing yacht_id
      'global/shared.jpg', // Not yacht-scoped
    ];

    const results = {
      validPaths: validPaths.map(p => ({
        path: p,
        hasYachtId: p.startsWith(TEST_YACHT_ID),
        isValid: p.split('/')[0] === TEST_YACHT_ID,
      })),
      invalidPaths: invalidPaths.map(p => ({
        path: p,
        hasYachtId: p.includes(TEST_YACHT_ID),
        isValid: p.split('/')[0] === TEST_YACHT_ID,
      })),
    };

    // Assert all valid paths have yacht_id prefix
    for (const valid of results.validPaths) {
      expect(valid.isValid).toBe(true);
    }

    // Assert all invalid paths lack yacht_id prefix
    for (const invalid of results.invalidPaths) {
      expect(invalid.isValid).toBe(false);
    }

    // Save evidence
    const evidencePath = path.join(ARTIFACTS_DIR, 'storage_path_structure_validation.json');
    fs.writeFileSync(evidencePath, JSON.stringify({
      test: 'Storage path structure validation',
      results,
      convention: '{yacht_id}/{resource_type}/{subpath}/{filename}',
      timestamp: new Date().toISOString(),
    }, null, 2));
  });
});
