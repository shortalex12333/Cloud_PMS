/**
 * Debug Supabase client session state
 */

import { chromium } from 'playwright';

async function debug() {
  console.log('=== DEBUG SUPABASE CLIENT STATE ===\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Wait for page to load
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Check if the Supabase client has a session
  const result = await page.evaluate(async () => {
    // Access the supabase client - need to import it somehow
    // Since it's bundled, we can't directly access it
    // Let's check what auth events fired

    // Get all localStorage keys
    const keys = Object.keys(localStorage);
    const authKeys = keys.filter(k => k.includes('auth') || k.includes('supabase'));

    // Check if there's a session stored
    const sessionKey = authKeys.find(k => k.includes('auth-token'));
    const sessionData = sessionKey ? localStorage.getItem(sessionKey) : null;

    // Parse session
    let session = null;
    try {
      session = sessionData ? JSON.parse(sessionData) : null;
    } catch (e) {}

    return {
      allKeys: keys.slice(0, 20),
      authKeys,
      sessionKey,
      hasSession: !!session?.access_token,
      accessTokenPreview: session?.access_token?.substring(0, 30) + '...',
      userId: session?.user?.id,
    };
  });

  console.log('localStorage state:', JSON.stringify(result, null, 2));

  // Now let's manually make a Supabase query in the page context
  console.log('\n2. Testing manual Supabase query...');
  const queryResult = await page.evaluate(async () => {
    const sessionKey = Object.keys(localStorage).find(k => k.includes('auth-token'));
    const session = sessionKey ? JSON.parse(localStorage.getItem(sessionKey) || '{}') : null;

    if (!session?.access_token) {
      return { error: 'No session' };
    }

    // Make a direct REST query to test
    const response = await fetch('https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/pms_work_orders?select=id,title&limit=1', {
      headers: {
        'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE',
        'Authorization': `Bearer ${session.access_token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return {
        error: `Query failed: ${response.status}`,
        body: await response.text(),
      };
    }

    const data = await response.json();
    return { success: true, count: data.length, sample: data[0] };
  });

  console.log('Query result:', JSON.stringify(queryResult, null, 2));

  await browser.close();
}

debug().catch(console.error);
