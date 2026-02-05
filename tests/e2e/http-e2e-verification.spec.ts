/**
 * HTTP E2E Verification - Full flow test
 *
 * Tests the complete HTTP path with real auth:
 * - /email/inbox
 * - /email/thread/:id
 * - /email/message/:id/render
 * - /email/message/:id/attachments/:aid/download
 * - /email/worker/status
 * - /email/thread/:id/links
 * - /api/integrations/outlook/status
 * - Error cases (404, not 500)
 */
import { test, expect } from '@playwright/test';

test.setTimeout(120000);

const API = 'https://pipeline-core.int.celeste7.ai';
const APP = 'https://app.celeste7.ai';

test('Full HTTP E2E Verification', async ({ page }) => {
  // Login and get token
  console.log('\n=== Step 1: Get JWT ===');
  await page.goto(`${APP}/login`);
  await page.fill('input[type="email"], input[name="email"]', 'x@alex-short.com');
  await page.fill('input[type="password"], input[name="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/app/, { timeout: 15000 });
  await page.waitForTimeout(2000);

  const token = await page.evaluate(() => {
    const keys = Object.keys(localStorage);
    for (const key of keys) {
      try {
        const data = JSON.parse(localStorage.getItem(key) || '{}');
        if (data.access_token) return data.access_token;
        if (data.currentSession?.access_token) return data.currentSession.access_token;
      } catch {}
    }
    return null;
  });

  if (!token) {
    console.log('ERROR: No auth token');
    expect(token).toBeTruthy();
    return;
  }
  console.log('Token obtained: YES');

  const headers = { 'Authorization': `Bearer ${token}` };

  // === Test /email/inbox ===
  console.log('\n=== Step 2: /email/inbox ===');
  const inboxRes = await page.request.get(`${API}/email/inbox`, { headers });
  console.log(`Status: ${inboxRes.status()}`);
  expect(inboxRes.status()).toBe(200);

  const inbox = await inboxRes.json();
  const threadCount = inbox.threads?.length || 0;
  console.log(`Threads: ${threadCount}`);
  expect(threadCount).toBeGreaterThanOrEqual(1);

  // Get a valid thread for further tests
  const testThread = inbox.threads[0];
  const threadId = testThread.id;
  console.log(`Test thread: ${threadId}`);

  // === Test /email/thread/:id (valid) ===
  console.log('\n=== Step 3: /email/thread/:id (valid) ===');
  const threadRes = await page.request.get(`${API}/email/thread/${threadId}`, { headers });
  console.log(`Status: ${threadRes.status()}`);
  expect(threadRes.status()).toBe(200);

  const thread = await threadRes.json();
  const messageCount = thread.messages?.length || 0;
  console.log(`Messages: ${messageCount}`);
  expect(messageCount).toBeGreaterThanOrEqual(1);

  // Get a message for render test
  const testMessage = thread.messages[0];
  const providerMsgId = testMessage.provider_message_id;
  console.log(`Provider message ID: ${providerMsgId?.substring(0, 30)}...`);

  // === Test /email/thread/:id (invalid - should be 404, not 500) ===
  console.log('\n=== Step 4: /email/thread/:id (invalid - expect 404) ===');
  const invalidThreadRes = await page.request.get(`${API}/email/thread/00000000-0000-0000-0000-000000000000`, { headers });
  console.log(`Status: ${invalidThreadRes.status()}`);
  const invalidBody = await invalidThreadRes.text();
  console.log(`Response: ${invalidBody.substring(0, 200)}`);
  expect(invalidThreadRes.status()).toBe(404); // NOT 500!

  // === Test /email/worker/status FIRST (to determine Outlook connection) ===
  console.log('\n=== Step 5: /email/worker/status ===');
  const workerRes = await page.request.get(`${API}/email/worker/status`, { headers });
  console.log(`Status: ${workerRes.status()}`);
  const workerBody = await workerRes.json();
  console.log(`Response: ${JSON.stringify(workerBody)}`);
  expect(workerRes.status()).toBe(200);
  expect(workerBody).toHaveProperty('sync_status');
  expect(workerBody).toHaveProperty('connected');

  const outlookConnected = workerBody.connected === true;
  console.log(`Outlook connected: ${outlookConnected}`);

  // === Test /email/message/:id/render ===
  console.log('\n=== Step 6: /email/message/:id/render ===');
  const encodedMsgId = encodeURIComponent(providerMsgId);
  const renderRes = await page.request.get(`${API}/email/message/${encodedMsgId}/render`, { headers });
  console.log(`Status: ${renderRes.status()}`);

  if (outlookConnected) {
    // If connected, expect 200
    if (renderRes.status() === 200) {
      const content = await renderRes.json();
      console.log(`Body type: ${content.body?.contentType}`);
      console.log(`Has attachments: ${content.has_attachments}`);
      console.log(`Attachments count: ${content.attachments?.length || 0}`);
      expect(content.body).toBeTruthy();
    } else {
      const errBody = await renderRes.text();
      console.log(`Error: ${errBody}`);
    }
    expect(renderRes.status()).toBe(200);
  } else {
    // If not connected, expect 401 (no token)
    const errBody = await renderRes.text();
    console.log(`Expected 401 (not connected): ${errBody.substring(0, 100)}`);
    expect(renderRes.status()).toBe(401);
  }

  // === Test /email/thread/:id/links (new endpoint) ===
  console.log('\n=== Step 7: /email/thread/:id/links ===');
  const linksRes = await page.request.get(`${API}/email/thread/${threadId}/links`, { headers });
  console.log(`Status: ${linksRes.status()}`);
  const linksBody = await linksRes.json();
  console.log(`Response: ${JSON.stringify(linksBody)}`);
  expect(linksRes.status()).toBe(200);
  expect(linksBody).toHaveProperty('links');
  expect(linksBody).toHaveProperty('total_count');

  // === Test /api/integrations/outlook/status (Vercel proxy) ===
  console.log('\n=== Step 8: /api/integrations/outlook/status ===');
  const outlookStatusRes = await page.request.get(`${APP}/api/integrations/outlook/status`, { headers });
  console.log(`Status: ${outlookStatusRes.status()}`);
  const outlookBody = await outlookStatusRes.json();
  console.log(`Response: ${JSON.stringify(outlookBody)}`);
  expect(outlookStatusRes.status()).toBe(200);
  expect(outlookBody).toHaveProperty('connected');

  // === Test attachment download (only if connected and have attachments) ===
  if (outlookConnected) {
    const renderContent = await (await page.request.get(`${API}/email/message/${encodedMsgId}/render`, { headers })).json();
    if (renderContent.attachments && renderContent.attachments.length > 0) {
      console.log('\n=== Step 9: /email/message/:id/attachments/:aid/download ===');
      const att = renderContent.attachments[0];
      const attId = encodeURIComponent(att.id);
      console.log(`Attachment: ${att.name} (${att.contentType})`);

      const downloadRes = await page.request.get(
        `${API}/email/message/${encodedMsgId}/attachments/${attId}/download`,
        { headers }
      );
      console.log(`Status: ${downloadRes.status()}`);
      console.log(`Content-Type: ${downloadRes.headers()['content-type']}`);
      console.log(`Content-Disposition: ${downloadRes.headers()['content-disposition']}`);

      // 200 for allowed types, 415 for disallowed
      expect([200, 415]).toContain(downloadRes.status());
    } else {
      console.log('\n=== Step 9: Skipped (no attachments) ===');
    }
  } else {
    console.log('\n=== Step 9: Skipped (Outlook not connected) ===');
  }

  // === Summary ===
  console.log('\n' + '='.repeat(60));
  console.log('VERIFICATION COMPLETE');
  console.log('='.repeat(60));
  console.log(`✓ /email/inbox: 200, ${threadCount} threads`);
  console.log(`✓ /email/thread/:id (valid): 200, ${messageCount} messages`);
  console.log(`✓ /email/thread/:id (invalid): 404 (not 500)`);
  console.log(`✓ /email/message/:id/render: ${outlookConnected ? '200' : '401 (not connected)'}`);
  console.log(`✓ /email/worker/status: 200, sync_status=${workerBody.sync_status}, connected=${outlookConnected}`);
  console.log(`✓ /email/thread/:id/links: 200, ${linksBody.total_count} links`);
  console.log(`✓ /api/integrations/outlook/status: 200, connected=${outlookBody.connected}`);
});
