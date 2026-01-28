/**
 * Email Body Render E2E Tests - Live Data
 *
 * Tests email body rendering using actual emails from the user's inbox.
 * No specific test emails required - uses search API to find real messages.
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const BACKEND_URL = process.env.BACKEND_URL || 'https://pipeline-core.int.celeste7.ai';

// Get auth token from global setup
let authToken: string;

test.beforeAll(async ({ request }) => {
  // Read cached token from global setup
  const fs = await import('fs');
  const path = await import('path');

  const authStatePath = path.join(process.cwd(), 'test-results', '.auth-state.json');

  if (fs.existsSync(authStatePath)) {
    const authState = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
    authToken = authState.accessToken;
  } else {
    // Fallback: mint token directly
    const supabaseUrl = process.env.MASTER_SUPABASE_URL || 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
    const supabaseKey = process.env.MASTER_SUPABASE_ANON_KEY;

    if (!supabaseKey) {
      throw new Error('No auth token available - run global setup first or set MASTER_SUPABASE_ANON_KEY');
    }

    const loginResp = await request.post(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
      headers: { 'apikey': supabaseKey, 'Content-Type': 'application/json' },
      data: {
        email: process.env.TEST_USER_EMAIL || 'x@alex-short.com',
        password: process.env.TEST_USER_PASSWORD || 'Password2!'
      }
    });

    const loginData = await loginResp.json();
    authToken = loginData.access_token;
  }

  if (!authToken) {
    throw new Error('Failed to obtain auth token');
  }
});

test.describe('Email Body Render - API Level', () => {

  test('Search returns emails from inbox', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/email/search?q=*&limit=5`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.results).toBeDefined();
    expect(data.results.length).toBeGreaterThan(0);

    console.log(`Found ${data.results.length} emails`);
    console.log(`First email subject: ${data.results[0]?.subject}`);
  });

  test('Thread endpoint returns messages', async ({ request }) => {
    // First get a thread_id from search
    const searchResp = await request.get(`${BACKEND_URL}/email/search?q=*&limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(searchResp.status()).toBe(200);
    const searchData = await searchResp.json();

    if (searchData.results.length === 0) {
      test.skip('No emails in inbox');
      return;
    }

    const threadId = searchData.results[0].thread_id;
    expect(threadId).toBeDefined();

    // Get thread
    const threadResp = await request.get(`${BACKEND_URL}/email/thread/${threadId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(threadResp.status()).toBe(200);

    const threadData = await threadResp.json();
    expect(threadData.messages).toBeDefined();
    expect(threadData.messages.length).toBeGreaterThan(0);

    console.log(`Thread has ${threadData.messages.length} messages`);
  });

  test('Render endpoint returns message body with encoded ID', async ({ request }) => {
    // Get a message with provider_message_id
    const searchResp = await request.get(`${BACKEND_URL}/email/search?q=*&limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    const searchData = await searchResp.json();
    if (searchData.results.length === 0) {
      test.skip('No emails in inbox');
      return;
    }

    const threadId = searchData.results[0].thread_id;

    // Get thread to get provider_message_id
    const threadResp = await request.get(`${BACKEND_URL}/email/thread/${threadId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    const threadData = await threadResp.json();
    const providerMessageId = threadData.messages[0].provider_message_id;

    expect(providerMessageId).toBeDefined();
    console.log(`Provider message ID: ${providerMessageId.substring(0, 50)}...`);

    // CRITICAL: Encode the provider ID (may contain +, /, =)
    const encodedId = encodeURIComponent(providerMessageId);

    // Render the message
    const renderResp = await request.get(`${BACKEND_URL}/email/message/${encodedId}/render`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(renderResp.status()).toBe(200);

    const renderData = await renderResp.json();
    expect(renderData.body).toBeDefined();
    expect(renderData.body.content).toBeDefined();
    expect(renderData.body.contentType).toMatch(/html|text/i);

    console.log(`Body content type: ${renderData.body.contentType}`);
    console.log(`Body length: ${renderData.body.content.length} chars`);
  });

  test('Attachments endpoint returns list', async ({ request }) => {
    // Get a message_id
    const searchResp = await request.get(`${BACKEND_URL}/email/search?q=*&limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    const searchData = await searchResp.json();
    if (searchData.results.length === 0) {
      test.skip('No emails in inbox');
      return;
    }

    const messageId = searchData.results[0].message_id;
    expect(messageId).toBeDefined();

    // Get attachments list
    const attResp = await request.get(`${BACKEND_URL}/email/message/${messageId}/attachments`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(attResp.status()).toBe(200);

    const attData = await attResp.json();
    expect(attData.attachments).toBeDefined();

    console.log(`Attachments count: ${attData.attachments.length}`);
  });

  test('Focus endpoint returns context', async ({ request }) => {
    // Get a message_id
    const searchResp = await request.get(`${BACKEND_URL}/email/search?q=*&limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    const searchData = await searchResp.json();
    if (searchData.results.length === 0) {
      test.skip('No emails in inbox');
      return;
    }

    const messageId = searchData.results[0].message_id;

    // Get focus/context
    const focusResp = await request.get(`${BACKEND_URL}/email/focus/${messageId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    expect(focusResp.status()).toBe(200);

    const focusData = await focusResp.json();
    expect(focusData.subject).toBeDefined();

    console.log(`Focus subject: ${focusData.subject}`);
    console.log(`Has entities: ${!!focusData.extracted_entities}`);
  });
});

test.describe('Email Body Render - Error Cases', () => {

  test('Render without auth returns error (401 or 422)', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/email/message/fake-id/render`);

    // Backend may return 401 (unauthorized) or 422 (validation error for missing auth)
    expect([401, 422]).toContain(response.status());
  });

  test('Render with invalid ID returns error', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/email/message/invalid-message-id-12345/render`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    // Backend may return 400, 404, or 500 for invalid IDs
    // The key is it shouldn't be 200 (success)
    expect(response.status()).not.toBe(200);
  });

  test('Search without auth returns error (401 or 422)', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/email/search?q=test`);

    // Backend may return 401 (unauthorized) or 422 (validation error for missing auth)
    expect([401, 422]).toContain(response.status());
  });
});

test.describe('Email Body Render - Full Flow', () => {

  test('Complete flow: Search → Thread → Render', async ({ request }) => {
    // 1. Search
    const searchResp = await request.get(`${BACKEND_URL}/email/search?q=certificate&limit=3`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    expect(searchResp.status()).toBe(200);

    const searchData = await searchResp.json();
    console.log(`Search found ${searchData.results.length} results for "certificate"`);

    if (searchData.results.length === 0) {
      // Try broader search
      const broadSearch = await request.get(`${BACKEND_URL}/email/search?q=*&limit=3`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      const broadData = await broadSearch.json();

      if (broadData.results.length === 0) {
        test.skip('No emails in inbox');
        return;
      }

      searchData.results = broadData.results;
    }

    // 2. Get thread
    const threadId = searchData.results[0].thread_id;
    const threadResp = await request.get(`${BACKEND_URL}/email/thread/${threadId}`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    expect(threadResp.status()).toBe(200);

    const threadData = await threadResp.json();
    console.log(`Thread "${threadData.latest_subject}" has ${threadData.messages.length} messages`);

    // 3. Render each message
    for (const msg of threadData.messages.slice(0, 2)) {
      const encodedId = encodeURIComponent(msg.provider_message_id);

      const renderResp = await request.get(`${BACKEND_URL}/email/message/${encodedId}/render`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });

      expect(renderResp.status()).toBe(200);

      const renderData = await renderResp.json();
      console.log(`  Message from ${msg.from_display_name}: ${renderData.body.contentType}, ${renderData.body.content.length} chars`);

      // Verify body has content
      expect(renderData.body.content.length).toBeGreaterThan(0);
    }

    console.log('Full flow complete!');
  });
});
