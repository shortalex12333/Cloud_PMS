/**
 * Direct test of add_to_handover endpoint
 * Provides curl-equivalent transcript for diagnosis
 */

import { login } from './tests/helpers/auth';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load .env.e2e.local
dotenv.config({ path: path.join(__dirname, '.env.e2e.local') });

const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

async function testAddToHandover() {
  try {
    console.log('='.repeat(80));
    console.log('DIRECT TEST: add_to_handover endpoint');
    console.log('='.repeat(80));
    console.log('');

    // Step 1: Login
    console.log('Step 1: Authenticating...');
    const tokens = await login('x@alex-short.com', 'Password2!');
    console.log(`✓ Token obtained (expires in ${Math.floor((tokens.expiresAt * 1000 - Date.now()) / 1000 / 60)} minutes)`);
    console.log('');

    // Step 2: Make request
    const url = `${API_BASE}/v1/actions/execute`;
    const payload = {
      action: 'add_to_handover',
      context: { yacht_id: TEST_YACHT_ID },
      payload: {
        entity_type: 'note',
        entity_id: null,
        summary_text: 'Direct Test: Testing add_to_handover with correct payload format',
        category: 'urgent',
        priority: 'high',
        presentation_bucket: 'Engineering',
        is_critical: true,
        requires_action: true,
        action_summary: 'Verify this payload works',
      },
    };

    console.log('Step 2: Making request...');
    console.log(`URL: POST ${url}`);
    console.log('Headers:');
    console.log(`  Authorization: Bearer ${tokens.accessToken.substring(0, 20)}...`);
    console.log('  Content-Type: application/json');
    console.log('');
    console.log('Request Body:');
    console.log(JSON.stringify(payload, null, 2));
    console.log('');
    console.log('-'.repeat(80));
    console.log('');

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${tokens.accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    console.log(`Response Status: ${response.status} ${response.statusText}`);
    console.log('Response Headers:');
    response.headers.forEach((value, key) => {
      console.log(`  ${key}: ${value}`);
    });
    console.log('');

    const responseText = await response.text();
    console.log('Response Body:');
    let responseJson;
    try {
      responseJson = JSON.parse(responseText);
      console.log(JSON.stringify(responseJson, null, 2));
    } catch {
      console.log(responseText);
    }
    console.log('');
    console.log('-'.repeat(80));
    console.log('');

    if (response.ok) {
      console.log('✓ Request succeeded');
      if (responseJson?.item_id) {
        console.log(`✓ Item created: ${responseJson.item_id}`);
      }
    } else {
      console.log('✗ Request failed');
      if (responseJson?.error_code) {
        console.log(`  Error Code: ${responseJson.error_code}`);
      }
      if (responseJson?.message) {
        console.log(`  Message: ${responseJson.message}`);
      }
      if (responseJson?.error) {
        console.log(`  Error: ${responseJson.error}`);
      }
    }

    console.log('');
    console.log('='.repeat(80));

    process.exit(response.ok ? 0 : 1);
  } catch (error) {
    console.error('');
    console.error('FATAL ERROR:');
    console.error(error);
    console.error('');
    process.exit(1);
  }
}

testAddToHandover();
