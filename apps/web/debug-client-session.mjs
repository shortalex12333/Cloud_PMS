/**
 * Debug what session the Supabase client actually has
 */

import { chromium } from 'playwright';

async function debug() {
  console.log('=== DEBUG CLIENT SESSION STATE ===\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Navigate and wait for bootstrap
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);

  // Inject a script to check the Supabase client state
  // We need to expose our supabase instance to window
  const result = await page.evaluate(async () => {
    // The app should have supabase somewhere...
    // Let's try to make a query using the page's supabase instance
    // by triggering a component that uses it

    // Alternatively, we can check if there are any global exports
    // But since it's bundled, we likely can't access it directly

    // Instead, let's look at what auth events have occurred
    // by checking if AuthContext has the right user

    // Check if React DevTools or any debug info is available
    // @ts-ignore
    const reactRoot = document.getElementById('__next');

    // Get any exposed globals
    const globals = Object.keys(window).filter(k =>
      k.toLowerCase().includes('supabase') ||
      k.toLowerCase().includes('auth')
    );

    return {
      globals,
      hasReactRoot: !!reactRoot,
      // Can't directly access bundled modules
    };
  });

  console.log('Browser state:', result);

  // Let's take a different approach - check network requests
  // to see if the Authorization header is being sent

  console.log('\n2. Making a test request through the app...');

  // Trigger a component that makes a Supabase request
  // by adding a work order ID to the URL
  await page.goto('http://localhost:3000/?entity=work_order&id=2531d846-5753-4faa-a549-20a6dc2ade73', {
    waitUntil: 'networkidle',
  });

  // Wait and capture the request
  const requestHeaders = await page.evaluate(async () => {
    // Make a direct request to see what headers the bundled fetch would send
    // This won't help since we need to see what the Supabase client sends

    return 'Check network tab manually or add request interception';
  });

  console.log('Request info:', requestHeaders);

  // Let's intercept the actual request
  console.log('\n3. Intercepting Supabase requests...');

  // Set up route interception
  const interceptedRequests = [];
  await page.route('**/rest/v1/**', async (route) => {
    const request = route.request();
    interceptedRequests.push({
      url: request.url(),
      headers: request.headers(),
    });
    await route.continue();
  });

  // Navigate again to trigger requests
  await page.goto('http://localhost:3000/?entity=work_order&id=2531d846-5753-4faa-a549-20a6dc2ade73', {
    waitUntil: 'networkidle',
  });
  await page.waitForTimeout(5000);

  console.log('Intercepted requests:');
  for (const req of interceptedRequests) {
    console.log('  URL:', req.url);
    console.log('  Auth header:', req.headers['authorization'] || '(none)');
    console.log('');
  }

  await browser.close();
}

debug().catch(console.error);
