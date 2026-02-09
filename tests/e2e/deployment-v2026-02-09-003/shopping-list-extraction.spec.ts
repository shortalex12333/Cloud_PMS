/**
 * Shopping List Entity Extraction - Deployment v2026.02.09.003
 * PR #197: Shopping list entity extraction fixes
 *
 * Tests:
 * 1. Create shopping list item with description
 * 2. System extracts entities (quantity, part type, manufacturer)
 * 3. User can confirm/edit extracted entities
 * 4. Item saved with structured data
 * 5. All roles can create shopping list items
 */

import { test, expect } from '@playwright/test';

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

// Test descriptions with expected extractions
const TEST_ITEMS = [
  {
    description: 'Need 2x oil filters for Caterpillar engine',
    expected: {
      quantity: 2,
      part_type: 'oil filter',
      manufacturer: 'Caterpillar'
    }
  },
  {
    description: '5 spark plugs NGK standard',
    expected: {
      quantity: 5,
      part_type: 'spark plug',
      manufacturer: 'NGK'
    }
  },
  {
    description: 'Hydraulic hose 10m Eaton',
    expected: {
      quantity: 10,
      unit: 'm',
      part_type: 'hydraulic hose',
      manufacturer: 'Eaton'
    }
  }
];

test.describe('Shopping List Entity Extraction - UI Journey', () => {

  for (const [roleName, user] of Object.entries(USERS)) {
    test(`${roleName} can create shopping list item with entity extraction`, async ({ page }) => {
      // Login
      await page.goto(APP_URL);
      await page.fill('input[type="email"]', user.email);
      await page.fill('input[type="password"]', user.password);
      await page.click('button[type="submit"]');

      await page.waitForURL(/.*dashboard/, { timeout: 10000 });

      // Navigate to Shopping List
      await page.goto(`${APP_URL}/shopping-list`);

      // Click "Add Item" or "Create"
      const addButton = page.locator('button:has-text("Add"), button:has-text("Create")');
      await addButton.click();

      // Enter description
      const descriptionInput = page.locator('textarea[name="description"], input[name="description"]');
      await descriptionInput.fill(TEST_ITEMS[0].description);

      // Trigger extraction (might be on blur or explicit button)
      await descriptionInput.blur();

      // OR click "Extract" button if it exists
      const extractButton = page.locator('button:has-text("Extract")');
      if (await extractButton.count() > 0) {
        await extractButton.click();
      }

      // Wait for extraction to complete
      await page.waitForTimeout(2000);

      // Should see extracted entities
      const quantityField = page.locator('input[name="quantity"]');
      await expect(quantityField).toHaveValue(String(TEST_ITEMS[0].expected.quantity));

      const partTypeField = page.locator('input[name="part_type"]');
      await expect(partTypeField).toHaveValue(TEST_ITEMS[0].expected.part_type);

      const manufacturerField = page.locator('input[name="manufacturer"]');
      await expect(manufacturerField).toHaveValue(TEST_ITEMS[0].expected.manufacturer);

      // Confirm/Save
      await page.locator('button:has-text("Save"), button:has-text("Confirm")').click();

      // Should see item in list
      await expect(page.locator(`text="${TEST_ITEMS[0].description}"`)).toBeVisible({ timeout: 5000 });
    });
  }

  test('CREW can edit extracted entities before saving', async ({ page }) => {
    // Login as crew
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.CREW.email);
    await page.fill('input[type="password"]', USERS.CREW.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to Shopping List
    await page.goto(`${APP_URL}/shopping-list`);

    // Create new item
    await page.locator('button:has-text("Add"), button:has-text("Create")').click();

    // Enter description
    const descriptionInput = page.locator('textarea[name="description"], input[name="description"]');
    await descriptionInput.fill(TEST_ITEMS[1].description);
    await descriptionInput.blur();

    // Wait for extraction
    await page.waitForTimeout(2000);

    // Edit the extracted quantity
    const quantityField = page.locator('input[name="quantity"]');
    await quantityField.clear();
    await quantityField.fill('10'); // Change from 5 to 10

    // Edit manufacturer
    const manufacturerField = page.locator('input[name="manufacturer"]');
    await manufacturerField.clear();
    await manufacturerField.fill('NGK Premium');

    // Save
    await page.locator('button:has-text("Save"), button:has-text("Confirm")').click();

    // Should see item with edited values
    await expect(page.locator('text=/10.*NGK Premium/i')).toBeVisible({ timeout: 5000 });
  });

  test('Entity extraction handles complex descriptions', async ({ page }) => {
    // Login as HOD
    await page.goto(APP_URL);
    await page.fill('input[type="email"]', USERS.HOD.email);
    await page.fill('input[type="password"]', USERS.HOD.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/, { timeout: 10000 });

    // Navigate to Shopping List
    await page.goto(`${APP_URL}/shopping-list`);

    // Create item with complex description
    await page.locator('button:has-text("Add"), button:has-text("Create")').click();

    const descriptionInput = page.locator('textarea[name="description"], input[name="description"]');
    await descriptionInput.fill(TEST_ITEMS[2].description);
    await descriptionInput.blur();

    // Wait for extraction
    await page.waitForTimeout(2000);

    // Should extract quantity with unit
    const quantityField = page.locator('input[name="quantity"]');
    await expect(quantityField).toHaveValue(String(TEST_ITEMS[2].expected.quantity));

    // Should extract part type
    const partTypeField = page.locator('input[name="part_type"]');
    await expect(partTypeField).toHaveValue(TEST_ITEMS[2].expected.part_type);

    // Should extract manufacturer
    const manufacturerField = page.locator('input[name="manufacturer"]');
    await expect(manufacturerField).toHaveValue(TEST_ITEMS[2].expected.manufacturer);
  });
});

test.describe('Shopping List Entity Extraction - API', () => {

  test('API extracts entities from description', async ({ request }) => {
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

    // Create shopping list item
    const response = await request.post(`${API_URL}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        action: 'create_shopping_list_item',
        context: {
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
          user_id: 'crew-user-id',
          role: 'crew'
        },
        payload: {
          description: TEST_ITEMS[0].description,
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598'
        }
      }
    });

    expect(response.status()).toBe(200);

    const body = await response.json();

    // Should have extracted entities
    expect(body).toHaveProperty('extracted_quantity', TEST_ITEMS[0].expected.quantity);
    expect(body).toHaveProperty('extracted_part_type');
    expect(body.extracted_part_type.toLowerCase()).toContain('oil filter');
    expect(body).toHaveProperty('extracted_manufacturer');
    expect(body.extracted_manufacturer.toLowerCase()).toContain('caterpillar');
  });

  test('API handles missing/unclear entities gracefully', async ({ request }) => {
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

    // Create item with vague description
    const response = await request.post(`${API_URL}/v1/actions/execute`, {
      headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
      },
      data: {
        action: 'create_shopping_list_item',
        context: {
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
          user_id: 'crew-user-id',
          role: 'crew'
        },
        payload: {
          description: 'Need some parts for the engine',
          yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598'
        }
      }
    });

    // Should still succeed even if extraction finds nothing
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toHaveProperty('description', 'Need some parts for the engine');
    // Extracted fields might be null/empty - that's ok
  });

  test('All roles can create shopping list items', async ({ request }) => {
    for (const [roleName, user] of Object.entries(USERS)) {
      // Login
      const loginResponse = await request.post(`${API_URL}/auth/v1/token?grant_type=password`, {
        headers: {
          'apikey': process.env.MASTER_SUPABASE_ANON_KEY || '',
          'Content-Type': 'application/json'
        },
        data: {
          email: user.email,
          password: user.password
        }
      });

      const { access_token } = await loginResponse.json();

      // Create shopping list item
      const response = await request.post(`${API_URL}/v1/actions/execute`, {
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'Content-Type': 'application/json'
        },
        data: {
          action: 'create_shopping_list_item',
          context: {
            yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
            user_id: 'user-id',
            role: user.role
          },
          payload: {
            description: `Test item from ${roleName}`,
            yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598'
          }
        }
      });

      expect(response.status()).toBe(200);
    }
  });
});
