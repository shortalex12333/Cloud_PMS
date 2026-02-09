import { login } from './tests/helpers/auth';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.join(__dirname, '.env.e2e.local') });

const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';
const DRAFT_ID = 'test-draft-123'; // Dummy ID, not actually used by backend

async function testFinalize() {
  try {
    console.log('Step 1: Authenticating as captain...');
    const tokens = await login('captain.tenant@alex-short.com', 'Password2!');
    console.log(`✓ Token obtained\n`);

    console.log('Step 2: Calling finalize endpoint...');
    const url = `${API_BASE}/v1/actions/handover/${DRAFT_ID}/finalize`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${tokens.accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    console.log(`Response Status: ${response.status} ${response.statusText}`);
    const responseText = await response.text();
    console.log('Response Body:');
    try {
      console.log(JSON.stringify(JSON.parse(responseText), null, 2));
    } catch {
      console.log(responseText);
    }

    process.exit(response.ok ? 0 : 1);
  } catch (error) {
    console.error('FATAL ERROR:', error);
    process.exit(1);
  }
}

testFinalize();
