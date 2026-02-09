/**
 * Work Orders RBAC - Deployment v2026.02.09.003
 * PR #194: Department-based RBAC for work orders
 *
 * Tests:
 * 1. CREW can close/mutate work orders in THEIR department
 * 2. CREW BLOCKED from other departments' work orders
 * 3. HOD (Engineering) can mutate ANY department
 * 4. CAPTAIN can mutate ANY department
 * 5. CAPTAIN + HOD can assign work orders
 * 6. CREW CANNOT assign work orders
 */

import { test, expect } from '@playwright/test';

const API_URL = 'https://pipeline-core.int.celeste7.ai';
const APP_URL = process.env.APP_URL || 'https://your-app-url.com';

// Test users
const USERS = {
  DECK_CREW: {
    email: 'crew.tenant@alex-short.com',
    password: process.env.CREW_PASSWORD || '',
    department: 'deck',
    role: 'crew'
  },
  HOD: {
    email: 'hod.tenant@alex-short.com',
    password: process.env.HOD_PASSWORD || '',
    department: 'engineering',
    role: 'hod'
  },
  CAPTAIN: {
    email: 'captain.tenant@alex-short.com',
    password: process.env.CAPTAIN_PASSWORD || '',
    role: 'captain'
  }
};

test.describe('Work Orders RBAC - Department Authority', () => {

  test('CREW can close work order in THEIR department', async ({ page }) => {
    // Login as deck crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.DECK_CREW.email);
    await page.fill('input[type="password"]', USERS.DECK_CREW.password);
    await page.click('button[type="submit"]');

    // Wait for auth
    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Find a DECK department work order (or create one first)
    const deckWorkOrder = page.locator('[data-department="deck"]').first();
    await deckWorkOrder.click();

    // Should see "Close Work Order" button enabled
    const closeButton = page.locator('button:has-text("Close")');
    await expect(closeButton).toBeVisible();
    await expect(closeButton).toBeEnabled();

    // Click close
    await closeButton.click();

    // Confirm closure
    await page.locator('button:has-text("Confirm")').click();

    // Should succeed - check for success message or status change
    await expect(page.locator('text=/closed|completed/i')).toBeVisible({ timeout: 5000 });
  });

  test('CREW BLOCKED from closing work order in OTHER department', async ({ page }) => {
    // Login as deck crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.DECK_CREW.email);
    await page.fill('input[type="password"]', USERS.DECK_CREW.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Find an ENGINEERING department work order
    const engineeringWorkOrder = page.locator('[data-department="engineering"]').first();

    if (await engineeringWorkOrder.count() > 0) {
      await engineeringWorkOrder.click();

      // Close button should be disabled OR hidden
      const closeButton = page.locator('button:has-text("Close")');

      if (await closeButton.count() > 0) {
        await expect(closeButton).toBeDisabled();
      } else {
        // Button not visible at all (preferred UX)
        await expect(closeButton).not.toBeVisible();
      }
    }
  });

  test('HOD (Engineering) can close work order in ANY department', async ({ page }) => {
    // Login as HOD
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.HOD.email);
    await page.fill('input[type="password"]', USERS.HOD.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Test closing DECK department work order (not HOD's department)
    const deckWorkOrder = page.locator('[data-department="deck"]').first();

    if (await deckWorkOrder.count() > 0) {
      await deckWorkOrder.click();

      // Close button should be enabled (cross-department authority)
      const closeButton = page.locator('button:has-text("Close")');
      await expect(closeButton).toBeVisible();
      await expect(closeButton).toBeEnabled();

      // Actually close it
      await closeButton.click();
      await page.locator('button:has-text("Confirm")').click();

      // Should succeed
      await expect(page.locator('text=/closed|completed/i')).toBeVisible({ timeout: 5000 });
    }
  });

  test('CAPTAIN can close work order in ANY department', async ({ page }) => {
    // Login as Captain
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.CAPTAIN.email);
    await page.fill('input[type="password"]', USERS.CAPTAIN.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Test closing any department work order
    const anyWorkOrder = page.locator('[data-testid="work-order-item"]').first();
    await anyWorkOrder.click();

    // Close button should be enabled (captain has full authority)
    const closeButton = page.locator('button:has-text("Close")');
    await expect(closeButton).toBeVisible();
    await expect(closeButton).toBeEnabled();
  });

  test('CAPTAIN can assign work orders', async ({ page }) => {
    // Login as Captain
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.CAPTAIN.email);
    await page.fill('input[type="password"]', USERS.CAPTAIN.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Open work order
    const workOrder = page.locator('[data-testid="work-order-item"]').first();
    await workOrder.click();

    // Should see "Assign" button
    const assignButton = page.locator('button:has-text("Assign")');
    await expect(assignButton).toBeVisible();
    await expect(assignButton).toBeEnabled();

    // Click assign
    await assignButton.click();

    // Select crew member from dropdown
    await page.locator('[data-testid="assignee-select"]').click();
    await page.locator('[data-testid="assignee-option"]').first().click();

    // Confirm
    await page.locator('button:has-text("Confirm")').click();

    // Should succeed
    await expect(page.locator('text=/assigned|updated/i')).toBeVisible({ timeout: 5000 });
  });

  test('HOD can assign work orders', async ({ page }) => {
    // Login as HOD
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.HOD.email);
    await page.fill('input[type="password"]', USERS.HOD.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Open work order
    const workOrder = page.locator('[data-testid="work-order-item"]').first();
    await workOrder.click();

    // Should see "Assign" button
    const assignButton = page.locator('button:has-text("Assign")');
    await expect(assignButton).toBeVisible();
    await expect(assignButton).toBeEnabled();
  });

  test('CREW CANNOT assign work orders', async ({ page }) => {
    // Login as crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.DECK_CREW.email);
    await page.fill('input[type="password"]', USERS.DECK_CREW.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to work orders
    await page.goto(`${APP_URL}/work-orders`);

    // Open work order in their department
    const deckWorkOrder = page.locator('[data-department="deck"]').first();
    await deckWorkOrder.click();

    // Assign button should NOT be visible or be disabled
    const assignButton = page.locator('button:has-text("Assign")');

    if (await assignButton.count() > 0) {
      await expect(assignButton).toBeDisabled();
    } else {
      await expect(assignButton).not.toBeVisible();
    }
  });
});

test.describe('Work Orders RBAC - API Level', () => {

  test('API: CREW can close work order in their department', async ({ request }) => {
    // Login to get JWT
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.DECK_CREW.email,
        password: USERS.DECK_CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Close work order (deck department - should succeed)
    const response = await request.post(`${API_URL}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        action: 'close_work_order',
        context: {
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
          user_id: 'crew-user-id',
          role: 'crew'
        },
        payload: {
          work_order_id: 'deck-work-order-id',
          department: 'deck'
        }
      }
    });

    expect(response.status()).toBe(200);
  });

  test('API: CREW BLOCKED from closing work order in other department', async ({ request }) => {
    // Login as deck crew
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.DECK_CREW.email,
        password: USERS.DECK_CREW.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Try to close engineering work order (should be blocked)
    const response = await request.post(`${API_URL}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        action: 'close_work_order',
        context: {
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
          user_id: 'crew-user-id',
          role: 'crew'
        },
        payload: {
          work_order_id: 'engineering-work-order-id',
          department: 'engineering'
        }
      }
    });

    expect(response.status()).toBe(403);

    const body = await response.json();
    expect(body.error_code).toMatch(/FORBIDDEN|RLS_DENIED/);
  });

  test('API: HOD can close work order in any department', async ({ request }) => {
    // Login as HOD
    const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
      headers: {
        'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
        'Content-Type': 'application/json'
      },
      data: {
        email: USERS.HOD.email,
        password: USERS.HOD.password
      }
    });

    const { access_token } = await loginResponse.json();

    // Close deck work order (cross-department - should succeed)
    const response = await request.post(`${API_URL}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        action: 'close_work_order',
        context: {
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
          user_id: 'hod-user-id',
          role: 'hod'
        },
        payload: {
          work_order_id: 'deck-work-order-id',
          department: 'deck'
        }
      }
    });

    expect(response.status()).toBe(200);
  });
});
