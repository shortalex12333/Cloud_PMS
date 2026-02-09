/**
 * Debug Supabase session detection
 */

import { chromium } from 'playwright';

async function debug() {
  console.log('=== DEBUG SUPABASE SESSION ===\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Listen for relevant logs
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('Supabase') || text.includes('Auth') || text.includes('session')) {
      console.log(`  [LOG] ${text}`);
    }
  });

  console.log('1. Navigate to page...');
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });

  console.log('\n2. Checking Supabase session in browser...');
  const sessionInfo = await page.evaluate(async () => {
    // Check localStorage
    const authKey = Object.keys(localStorage).find(k => k.includes('auth-token'));
    const stored = authKey ? JSON.parse(localStorage.getItem(authKey) || '{}') : null;

    // Check if Supabase client exists and what it reports
    // @ts-ignore
    if (typeof window !== 'undefined' && window.supabase) {
      // @ts-ignore
      const { data } = await window.supabase.auth.getSession();
      return {
        hasStoredSession: !!stored?.access_token,
        storedTokenExpiry: stored?.expires_at ? new Date(stored.expires_at * 1000).toISOString() : null,
        supabaseSession: data?.session ? {
          hasAccessToken: !!data.session.access_token,
          userId: data.session.user?.id,
          expiresAt: data.session.expires_at,
        } : null,
      };
    }

    return {
      hasStoredSession: !!stored?.access_token,
      storedTokenExpiry: stored?.expires_at ? new Date(stored.expires_at * 1000).toISOString() : null,
      supabaseSession: 'window.supabase not found',
    };
  });

  console.log('  Session info:', JSON.stringify(sessionInfo, null, 2));

  // Manually check if supabase.auth.getSession() works
  console.log('\n3. Calling supabase.auth.getSession() via page...');
  const getSessionResult = await page.evaluate(async () => {
    // Try to access the supabase client from the page's scope
    // This might not work if supabase is bundled and not exposed to window
    try {
      // Check localStorage directly
      const authKey = Object.keys(localStorage).find(k => k.includes('auth-token'));
      if (!authKey) return { error: 'No auth key in localStorage' };

      const stored = JSON.parse(localStorage.getItem(authKey) || '{}');
      if (!stored.access_token) return { error: 'No access_token in stored session' };

      // Make a test request with the token
      const response = await fetch('https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/user', {
        headers: {
          'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE',
          'Authorization': `Bearer ${stored.access_token}`,
        },
      });

      if (!response.ok) {
        return { error: `Auth endpoint returned ${response.status}`, body: await response.text() };
      }

      const user = await response.json();
      return { success: true, userId: user.id, email: user.email };
    } catch (e) {
      return { error: e.message };
    }
  });

  console.log('  getSession result:', JSON.stringify(getSessionResult, null, 2));

  await browser.close();
}

debug().catch(console.error);
