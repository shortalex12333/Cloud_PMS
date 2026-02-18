/**
 * Debug test for receiving lens API calls
 */

import { test, expect } from '@playwright/test';
import { loginAs } from './auth.helper';

const API_URL = 'https://pipeline-core.int.celeste7.ai';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function getJWT(page: any): Promise<string> {
  const jwt = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.includes('sb-')) {
        const value = localStorage.getItem(key);
        if (value) {
          try {
            const parsed = JSON.parse(value);
            return parsed.access_token || null;
          } catch {}
        }
      }
    }
    return null;
  });
  if (!jwt) throw new Error('JWT not found');
  return jwt;
}

async function apiCall(jwt: string, action: string, payload: any): Promise<any> {
  const response = await fetch(`${API_URL}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action,
      context: { yacht_id: YACHT_ID },
      payload,
    }),
  });

  const data = await response.json();
  return { status: response.status, data };
}

test('Debug: Rejection flow with detailed logging', async ({ page }) => {
  console.log('\n=== DEBUG: REJECTION FLOW ===\n');

  // Step 1: Login
  await loginAs(page, 'hod');
  const jwt = await getJWT(page);
  console.log('✓ Logged in as HOD (chief_engineer)');

  // Step 2: Create receiving
  console.log('\n--- CREATE RECEIVING ---');
  const createResult = await apiCall(jwt, 'create_receiving', {
    vendor_name: 'Debug Test Vendor',
    vendor_reference: `DEBUG-${Date.now()}`,
  });
  console.log('Create HTTP Status:', createResult.status);
  console.log('Create Response:', JSON.stringify(createResult.data, null, 2));

  if (createResult.status !== 200) {
    console.log('CREATE FAILED - stopping test');
    expect(createResult.status).toBe(200);
    return;
  }

  const receivingId = createResult.data.receiving_id;
  console.log('Receiving ID:', receivingId);

  // Step 3: Add item
  console.log('\n--- ADD ITEM ---');
  const itemResult = await apiCall(jwt, 'add_receiving_item', {
    receiving_id: receivingId,
    description: 'Debug Item',
    quantity_received: 1,
  });
  console.log('Add Item HTTP Status:', itemResult.status);
  console.log('Add Item Response:', JSON.stringify(itemResult.data, null, 2));

  // Step 4: Reject receiving
  console.log('\n--- REJECT RECEIVING ---');
  const rejectResult = await apiCall(jwt, 'reject_receiving', {
    receiving_id: receivingId,
    reason: 'Debug test rejection',
  });
  console.log('Reject HTTP Status:', rejectResult.status);
  console.log('Reject Response:', JSON.stringify(rejectResult.data, null, 2));

  // Verify
  expect(rejectResult.status).toBe(200);
  expect(rejectResult.data.status).toBe('success');
  expect(rejectResult.data.new_status).toBe('rejected');

  console.log('\n=== DEBUG COMPLETE ===\n');
});

test('Debug: Accept flow with signature', async ({ page }) => {
  console.log('\n=== DEBUG: ACCEPT FLOW WITH SIGNATURE ===\n');

  // Step 1: Login as captain
  await loginAs(page, 'captain');
  const jwt = await getJWT(page);
  console.log('✓ Logged in as Captain');

  // Step 2: Create receiving
  console.log('\n--- CREATE RECEIVING ---');
  const createResult = await apiCall(jwt, 'create_receiving', {
    vendor_name: 'Accept Test Vendor',
    vendor_reference: `ACCEPT-${Date.now()}`,
  });
  console.log('Create HTTP Status:', createResult.status);
  console.log('Create Response:', JSON.stringify(createResult.data, null, 2));

  if (createResult.status !== 200) {
    console.log('CREATE FAILED - stopping test');
    expect(createResult.status).toBe(200);
    return;
  }

  const receivingId = createResult.data.receiving_id;
  console.log('Receiving ID:', receivingId);

  // Step 3: Add item (required for acceptance)
  console.log('\n--- ADD ITEM ---');
  const itemResult = await apiCall(jwt, 'add_receiving_item', {
    receiving_id: receivingId,
    description: 'Accept Test Item',
    quantity_received: 5,
    unit_price: 100.00,
  });
  console.log('Add Item HTTP Status:', itemResult.status);
  console.log('Add Item Response:', JSON.stringify(itemResult.data, null, 2));

  // Step 4: Prepare acceptance
  console.log('\n--- PREPARE ACCEPTANCE ---');
  const prepareResult = await apiCall(jwt, 'accept_receiving', {
    receiving_id: receivingId,
    mode: 'prepare',
  });
  console.log('Prepare HTTP Status:', prepareResult.status);
  console.log('Prepare Response:', JSON.stringify(prepareResult.data, null, 2));

  // Step 5: Execute acceptance WITHOUT signature
  console.log('\n--- EXECUTE WITHOUT SIGNATURE ---');
  const noSigResult = await apiCall(jwt, 'accept_receiving', {
    receiving_id: receivingId,
    mode: 'execute',
  });
  console.log('No-Sig HTTP Status:', noSigResult.status);
  console.log('No-Sig Response:', JSON.stringify(noSigResult.data, null, 2));
  console.log('Expected: 400 SIGNATURE_REQUIRED');

  // Step 6: Execute acceptance WITH signature
  console.log('\n--- EXECUTE WITH SIGNATURE ---');
  const acceptResult = await apiCall(jwt, 'accept_receiving', {
    receiving_id: receivingId,
    mode: 'execute',
    signature: {
      signer_name: 'Captain Test',
      signer_role: 'captain',
      signer_id: 'test-user-id',
      timestamp: new Date().toISOString(),
      yacht_id: YACHT_ID,
      action: 'accept_receiving',
      entity_id: receivingId,
    },
  });
  console.log('Accept HTTP Status:', acceptResult.status);
  console.log('Accept Response:', JSON.stringify(acceptResult.data, null, 2));

  // Verify
  expect(acceptResult.status).toBe(200);
  expect(acceptResult.data.status).toBe('success');
  expect(acceptResult.data.new_status).toBe('accepted');

  console.log('\n=== DEBUG COMPLETE ===\n');
});
