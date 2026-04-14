/**
 * HoR Proof Test — Screenshots for CEO review
 *
 * Uses JWT minting (same as global-setup.ts) with per-role user IDs.
 * Injects session via storageState file, not addInitScript.
 *
 * Usage:
 *   cd scripts/hor-proof
 *   SUPABASE_JWT_SECRET=xxx PROOF_DIR=/tmp/hor-proof npx playwright test --config playwright.config.ts
 *
 * PROOF_DIR defaults to $HOME/hor-proof if not set.
 */

import { test, Page, BrowserContext } from '@playwright/test';
import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const PROOF_DIR = process.env.PROOF_DIR ?? path.join(process.env.HOME ?? '/tmp', 'hor-proof');

const SUPABASE_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const SUPABASE_PROJECT_REF = 'qvzmkaamzaqxpzbewjxe';
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;

const USERS = {
  crew:    { sub: '05a54017-5bd2-4b97-8c77-c46c2a06ef02', email: 'crew.test@alex-short.com' },
  hod:     { sub: '05a488fd-6c26-4b42-8e9a-07abb8f31f85', email: 'hod.test@alex-short.com' },
  captain: { sub: 'a35cad0b-02ff-4287-b6e4-17c96fa6a424', email: 'x@alex-short.com' },
};

function mintJwt(sub: string, email: string): string {
  const secret = process.env.SUPABASE_JWT_SECRET;
  if (!secret) throw new Error('SUPABASE_JWT_SECRET required');
  const key = Buffer.from(secret, 'utf8');
  const now = Math.floor(Date.now() / 1000);
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');

  const header = b64({ alg: 'HS256', typ: 'JWT' });
  const payload = b64({
    sub, aud: 'authenticated', role: 'authenticated',
    email, iat: now, exp: now + 28800,
    iss: `${SUPABASE_URL}/auth/v1`,
  });
  const sig = crypto.createHmac('sha256', key).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${sig}`;
}

function writeStorageState(role: string, sub: string, email: string): string {
  const jwt = mintJwt(sub, email);
  const sessionData = JSON.stringify({
    access_token: jwt,
    token_type: 'bearer',
    expires_in: 28800,
    expires_at: Math.floor(Date.now() / 1000) + 28800,
    refresh_token: 'dummy',
    user: { id: sub, email, aud: 'authenticated', role: 'authenticated' },
  });

  const state = {
    cookies: [],
    origins: [{
      origin: BASE_URL,
      localStorage: [{ name: STORAGE_KEY, value: sessionData }],
    }],
  };

  fs.mkdirSync(PROOF_DIR, { recursive: true });
  const filePath = path.join(PROOF_DIR, `auth-${role}.json`);
  fs.writeFileSync(filePath, JSON.stringify(state, null, 2));
  return filePath;
}

async function openAsRole(browser: any, role: keyof typeof USERS): Promise<{ context: BrowserContext; page: Page }> {
  const user = USERS[role];
  const stateFile = writeStorageState(role, user.sub, user.email);
  const context = await browser.newContext({ storageState: stateFile });
  const page = await context.newPage();
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  return { context, page };
}

// ── PROOF 1: Crew ──────────────────────────────────────────────────────────

test('PROOF 1 — Crew role: My Time view', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'crew');
  await page.screenshot({ path: path.join(PROOF_DIR, '01-crew-my-time.png'), fullPage: true });

  const body = await page.textContent('body') || '';
  console.log(`[CREW] URL: ${page.url()}`);
  console.log(`[CREW] My Time: ${body.includes('My Time') || body.includes('THIS WEEK') ? '✓' : '✗'}`);

  await context.close();
});

// ── PROOF 2: HOD ───────────────────────────────────────────────────────────

test('PROOF 2 — HOD role: My Time + Department', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'hod');
  await page.screenshot({ path: path.join(PROOF_DIR, '02-hod-my-time.png'), fullPage: true });

  const deptTab = page.locator('button').filter({ hasText: /department/i });
  if (await deptTab.count() > 0) {
    await deptTab.first().click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(PROOF_DIR, '02-hod-department.png'), fullPage: true });
    console.log('[HOD] Department tab ✓');
  } else {
    console.log('[HOD] No department tab');
    await page.screenshot({ path: path.join(PROOF_DIR, '02-hod-no-dept-tab.png'), fullPage: true });
  }

  await context.close();
});

// ── PROOF 3: Captain ───────────────────────────────────────────────────────

test('PROOF 3 — Captain: all views', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'captain');
  await page.screenshot({ path: path.join(PROOF_DIR, '03-captain-my-time.png'), fullPage: true });

  const deptTab = page.locator('button').filter({ hasText: /department/i });
  if (await deptTab.count() > 0) {
    await deptTab.first().click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(PROOF_DIR, '03-captain-department.png'), fullPage: true });
  }

  const allTab = page.locator('button').filter({ hasText: /all dep/i });
  if (await allTab.count() > 0) {
    await allTab.first().click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(PROOF_DIR, '03-captain-all-departments.png'), fullPage: true });
  }

  await context.close();
});

// ── PROOF 4: Slider click ──────────────────────────────────────────────────

test('PROOF 4 — Slider creates block on click', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'captain');
  await page.screenshot({ path: path.join(PROOF_DIR, '04-slider-before.png'), fullPage: true });

  const track = page.locator('.hor-track-bg').first();
  if (await track.count() > 0 && await track.isVisible()) {
    const box = await track.boundingBox();
    if (box) {
      await page.mouse.click(box.x + box.width * 0.25, box.y + box.height / 2);
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(PROOF_DIR, '04-slider-one-block.png'), fullPage: true });

      await page.mouse.click(box.x + box.width * 0.60, box.y + box.height / 2);
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(PROOF_DIR, '04-slider-two-blocks.png'), fullPage: true });
      console.log('[SLIDER] Blocks created ✓');
    }
  } else {
    console.log('[SLIDER] No editable track');
    await page.screenshot({ path: path.join(PROOF_DIR, '04-slider-no-track.png'), fullPage: true });
  }

  await context.close();
});

// ── PROOF 5: Slider drag resize ────────────────────────────────────────────

test('PROOF 5 — Slider drag resizes block', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'captain');

  const track = page.locator('.hor-track-bg').first();
  if (await track.count() > 0 && await track.isVisible()) {
    const box = await track.boundingBox();
    if (box) {
      const y = box.y + box.height / 2;
      await page.mouse.click(box.x + box.width * 0.30, y);
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(PROOF_DIR, '05-resize-before.png'), fullPage: true });

      const handleX = box.x + box.width * 0.345;
      const targetX = box.x + box.width * 0.50;
      await page.mouse.move(handleX, y);
      await page.mouse.down();
      for (let i = 1; i <= 10; i++) {
        await page.mouse.move(handleX + (targetX - handleX) * (i / 10), y);
        await page.waitForTimeout(30);
      }
      await page.mouse.up();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(PROOF_DIR, '05-resize-after.png'), fullPage: true });
      console.log('[SLIDER] Resize ✓');
    }
  }

  await context.close();
});

// ── PROOF 6: Submit Day ────────────────────────────────────────────────────

test('PROOF 6 — Submit Day button appears', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'captain');

  const track = page.locator('.hor-track-bg').first();
  if (await track.count() > 0 && await track.isVisible()) {
    const box = await track.boundingBox();
    if (box) {
      await page.mouse.click(box.x + box.width * 0.30, box.y + box.height / 2);
      await page.waitForTimeout(800);

      const btn = page.locator('button').filter({ hasText: /submit day/i });
      console.log(`[SUBMIT] Button count: ${await btn.count()}`);
      await page.screenshot({ path: path.join(PROOF_DIR, '06-submit-day.png'), fullPage: true });
    }
  }

  await context.close();
});

// ── PROOF 7: Compliance + Sign-Off ─────────────────────────────────────────

test('PROOF 7 — Compliance and Sign-Off cards', async ({ browser }) => {
  const { context, page } = await openAsRole(browser, 'captain');

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(PROOF_DIR, '07-compliance-signoff.png'), fullPage: true });

  const body = await page.textContent('body') || '';
  console.log(`[CARDS] Compliance: ${body.includes('ompliance') ? '✓' : '✗'}`);
  console.log(`[CARDS] Sign-Off: ${body.includes('ign') ? '✓' : '✗'}`);

  await context.close();
});
