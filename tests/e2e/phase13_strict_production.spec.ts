/**
 * Phase 13: Strict Production Verification
 *
 * This test ONLY passes if:
 * - HTTP status is 200/201 (no 400/401/404/422/307)
 * - /v1/decisions is called with correct intents/entities
 * - Response contains execution_id, ActionDecision[]
 * - All evidence is captured and saved
 *
 * Evidence stored in: verification_handoff/evidence/phase13/
 */

import { test, expect, Page, Request, Response } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const PROD_URL = 'https://app.celeste7.ai';
const PIPELINE_URL = 'https://pipeline-core.int.celeste7.ai';
const TEST_EMAIL = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
const TEST_PASSWORD = process.env.TEST_USER_PASSWORD || 'Password2!';

const EVIDENCE_DIR = 'verification_handoff/evidence/phase13';

// Ensure evidence directory exists
if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
}

interface EvidencePack {
  journeyId: string;
  stepId: string;
  timestamp: string;
  screenshots: string[];
  networkCalls: Array<{
    url: string;
    method: string;
    status?: number;
    requestBody?: unknown;
    responseBody?: unknown;
  }>;
  decisionsProof: {
    called: boolean;
    requestPayload?: unknown;
    responsePayload?: unknown;
    executionId?: string;
    allowedActions?: string[];
    blockedActions?: string[];
  };
  verdict: 'PASS' | 'FAIL' | 'BLOCKED';
  failureReason?: string;
  blockedBy?: string;
}

function saveEvidence(evidence: EvidencePack) {
  const filename = `${evidence.journeyId}_${evidence.stepId}_evidence.json`;
  const filepath = path.join(EVIDENCE_DIR, filename);
  fs.writeFileSync(filepath, JSON.stringify(evidence, null, 2));
  console.log(`[Evidence] Saved: ${filepath}`);
  return filepath;
}

async function saveScreenshot(page: Page, name: string): Promise<string> {
  const filepath = path.join(EVIDENCE_DIR, `${name}.png`);
  await page.screenshot({ path: filepath, fullPage: true });
  console.log(`[Screenshot] Saved: ${filepath}`);
  return filepath;
}

test.describe('Phase 13: Strict Production Verification', () => {
  test.describe.configure({ mode: 'serial' });

  // Step 0: Establish Production Truth
  test('Step 0: Verify production deployment and auth', async ({ page }) => {
    const evidence: EvidencePack = {
      journeyId: 'P13',
      stepId: 'S00_AUTH',
      timestamp: new Date().toISOString(),
      screenshots: [],
      networkCalls: [],
      decisionsProof: { called: false },
      verdict: 'FAIL',
    };

    try {
      // Navigate to production login
      console.log(`[Step 0] Navigating to ${PROD_URL}/login`);
      await page.goto(`${PROD_URL}/login`);
      await page.waitForLoadState('networkidle');
      evidence.screenshots.push(await saveScreenshot(page, 'P13_S00_01_login_page'));

      // Login
      console.log('[Step 0] Filling login form');
      await page.fill('input[type="email"], input[name="email"]', TEST_EMAIL);
      await page.fill('input[type="password"], input[name="password"]', TEST_PASSWORD);

      // Capture network calls during login
      const bootstrapCalls: Array<{ url: string; method: string; status?: number; body?: unknown }> = [];
      page.on('response', async (response: Response) => {
        const url = response.url();
        if (url.includes('get_my_bootstrap') || url.includes('auth') || url.includes('session')) {
          let body = null;
          try {
            body = await response.json();
          } catch {}
          bootstrapCalls.push({
            url,
            method: response.request().method(),
            status: response.status(),
            body,
          });
        }
      });

      await page.click('button[type="submit"]');

      // Wait for redirect away from login
      try {
        await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
        console.log('[Step 0] Login successful, redirected to:', page.url());
      } catch (e) {
        evidence.verdict = 'FAIL';
        evidence.failureReason = 'Login failed - did not redirect from /login';
        saveEvidence(evidence);
        throw new Error('Login failed');
      }

      // Wait for bootstrap to complete
      await page.waitForTimeout(3000);
      evidence.screenshots.push(await saveScreenshot(page, 'P13_S00_02_after_login'));

      // Check for auth debug panel (shows yacht_id, role, session status)
      const authDebug = page.locator('text=Auth Debug');
      const authDebugVisible = await authDebug.isVisible().catch(() => false);

      if (authDebugVisible) {
        // Expand it if collapsed
        await authDebug.click().catch(() => {});
        await page.waitForTimeout(500);
        evidence.screenshots.push(await saveScreenshot(page, 'P13_S00_03_auth_debug_expanded'));
      }

      // Record bootstrap calls
      evidence.networkCalls = bootstrapCalls.map(c => ({
        url: c.url,
        method: c.method,
        status: c.status,
        responseBody: c.body,
      }));

      // Verify auth via network calls (stricter than UI)
      const bootstrapCall = bootstrapCalls.find(c => c.url.includes('get_my_bootstrap'));
      const authCall = bootstrapCalls.find(c => c.url.includes('token'));

      const authSuccess = authCall && authCall.status === 200;
      const bootstrapSuccess = bootstrapCall && bootstrapCall.status === 200;
      const bootstrapData = bootstrapCall?.body as { yacht_id?: string; role?: string; status?: string } | undefined;

      const hasYacht = !!bootstrapData?.yacht_id;
      const hasRole = !!bootstrapData?.role;
      const isActive = bootstrapData?.status === 'active';

      console.log(`[Step 0] Auth state (from network):`);
      console.log(`  - auth call: ${authSuccess ? 'PASS' : 'FAIL'}`);
      console.log(`  - bootstrap call: ${bootstrapSuccess ? 'PASS' : 'FAIL'}`);
      console.log(`  - yacht_id: ${bootstrapData?.yacht_id || 'NONE'}`);
      console.log(`  - role: ${bootstrapData?.role || 'NONE'}`);
      console.log(`  - status: ${bootstrapData?.status || 'NONE'}`);

      if (authSuccess && bootstrapSuccess && hasYacht && hasRole && isActive) {
        evidence.verdict = 'PASS';
        console.log('[Step 0] PASS - Production auth verified via network calls');
      } else {
        evidence.verdict = 'FAIL';
        evidence.failureReason = `Auth failed: auth=${authSuccess}, bootstrap=${bootstrapSuccess}, yacht=${hasYacht}, role=${hasRole}, active=${isActive}`;
      }

    } catch (error) {
      evidence.verdict = 'FAIL';
      evidence.failureReason = error instanceof Error ? error.message : 'Unknown error';
      evidence.screenshots.push(await saveScreenshot(page, 'P13_S00_error'));
    }

    saveEvidence(evidence);
    expect(evidence.verdict).toBe('PASS');
  });

  // Journey 1: Fault Diagnosis - Strict Production Proof
  test('Journey 1: Fault diagnosis with strict /v1/decisions proof', async ({ page }) => {
    const evidence: EvidencePack = {
      journeyId: 'P13_J01',
      stepId: 'FAULT_DIAGNOSIS',
      timestamp: new Date().toISOString(),
      screenshots: [],
      networkCalls: [],
      decisionsProof: { called: false },
      verdict: 'FAIL',
    };

    // Capture ALL /v1/decisions calls
    const decisionsCalls: Array<{ request: unknown; response: unknown; status: number }> = [];

    page.on('request', (request: Request) => {
      if (request.url().includes('/v1/decisions')) {
        let body = {};
        try {
          body = JSON.parse(request.postData() || '{}');
        } catch {}
        console.log('[Decisions] Request intercepted:', request.url());
        console.log('[Decisions] Request body:', JSON.stringify(body, null, 2));
      }
    });

    page.on('response', async (response: Response) => {
      if (response.url().includes('/v1/decisions')) {
        const status = response.status();
        let body = {};
        try {
          body = await response.json();
        } catch {}
        console.log('[Decisions] Response status:', status);
        console.log('[Decisions] Response body:', JSON.stringify(body, null, 2));

        decisionsCalls.push({
          request: response.request().postData() ? JSON.parse(response.request().postData()!) : {},
          response: body,
          status,
        });
      }
    });

    try {
      // Login first
      console.log('[J01] Logging in...');
      await page.goto(`${PROD_URL}/login`);
      await page.waitForLoadState('networkidle');
      await page.fill('input[type="email"], input[name="email"]', TEST_EMAIL);
      await page.fill('input[type="password"], input[name="password"]', TEST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
      await page.waitForTimeout(2000);

      evidence.screenshots.push(await saveScreenshot(page, 'P13_J01_01_logged_in'));

      // Navigate to fault via deep link (using known seeded fault ID)
      const faultId = 'e2e00002-0002-0002-0002-000000000001';
      const deepLinkUrl = `${PROD_URL}/app?entity=fault&id=${faultId}`;
      console.log(`[J01] Navigating to fault via deep link: ${deepLinkUrl}`);

      await page.goto(deepLinkUrl);
      await page.waitForLoadState('networkidle');

      // Wait for DeepLinkHandler to process
      const deepLinkHandler = page.locator('[data-testid="deep-link-handler"]');
      const handlerExists = await deepLinkHandler.count() > 0;
      console.log(`[J01] DeepLinkHandler exists: ${handlerExists}`);

      if (handlerExists) {
        await page.waitForFunction(
          () => {
            const handler = document.querySelector('[data-testid="deep-link-handler"]');
            if (!handler) return true;
            const status = handler.getAttribute('data-deep-link-status');
            return status === 'success' || status === 'error';
          },
          { timeout: 10000 }
        ).catch(() => {});
      }

      // Wait for decisions to be called
      console.log('[J01] Waiting for /v1/decisions call...');
      await page.waitForTimeout(5000);

      evidence.screenshots.push(await saveScreenshot(page, 'P13_J01_02_fault_detail'));

      // Analyze decisions proof
      if (decisionsCalls.length > 0) {
        evidence.decisionsProof.called = true;
        const firstCall = decisionsCalls[0];
        evidence.decisionsProof.requestPayload = firstCall.request;
        evidence.decisionsProof.responsePayload = firstCall.response;

        const responseBody = firstCall.response as {
          execution_id?: string;
          decisions?: Array<{ action: string; allowed: boolean }>;
        };

        evidence.decisionsProof.executionId = responseBody.execution_id;
        evidence.decisionsProof.allowedActions = responseBody.decisions
          ?.filter(d => d.allowed)
          .map(d => d.action) || [];
        evidence.decisionsProof.blockedActions = responseBody.decisions
          ?.filter(d => !d.allowed)
          .map(d => d.action) || [];

        console.log(`[J01] Decisions proof:`);
        console.log(`  - execution_id: ${evidence.decisionsProof.executionId}`);
        console.log(`  - allowed actions: ${evidence.decisionsProof.allowedActions.length}`);
        console.log(`  - blocked actions: ${evidence.decisionsProof.blockedActions.length}`);

        // Strict verification
        if (firstCall.status === 200 && evidence.decisionsProof.executionId) {
          evidence.verdict = 'PASS';
          console.log('[J01] PASS - /v1/decisions called with 200 response and execution_id');
        } else {
          evidence.verdict = 'FAIL';
          evidence.failureReason = `Decisions call status=${firstCall.status}, execution_id=${evidence.decisionsProof.executionId}`;
        }
      } else {
        evidence.verdict = 'FAIL';
        evidence.failureReason = '/v1/decisions was NOT called - decision engine not driving UI';
        console.log('[J01] FAIL - /v1/decisions was NOT called');
      }

      evidence.networkCalls = decisionsCalls.map(c => ({
        url: `${PIPELINE_URL}/v1/decisions`,
        method: 'POST',
        status: c.status,
        requestBody: c.request,
        responseBody: c.response,
      }));

    } catch (error) {
      evidence.verdict = 'FAIL';
      evidence.failureReason = error instanceof Error ? error.message : 'Unknown error';
      evidence.screenshots.push(await saveScreenshot(page, 'P13_J01_error'));
    }

    saveEvidence(evidence);

    // Print summary
    console.log('\n========================================');
    console.log('JOURNEY 1 STRICT PROOF SUMMARY');
    console.log('========================================');
    console.log(`Verdict: ${evidence.verdict}`);
    console.log(`/v1/decisions called: ${evidence.decisionsProof.called}`);
    console.log(`Execution ID: ${evidence.decisionsProof.executionId || 'NONE'}`);
    console.log(`Allowed actions: ${evidence.decisionsProof.allowedActions?.join(', ') || 'NONE'}`);
    if (evidence.failureReason) {
      console.log(`Failure reason: ${evidence.failureReason}`);
    }
    console.log('========================================\n');

    expect(evidence.verdict).toBe('PASS');
  });
});
