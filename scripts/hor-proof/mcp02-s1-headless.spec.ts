/**
 * HOURSOFREST_MCP02 — Scenario 1 final: PR #569 a+b+c
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const SUPABASE_PROJECT_REF = 'qvzmkaamzaqxpzbewjxe';
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;
const PROOF_DIR = process.env.PROOF_DIR || '/tmp/hor_mcp02';
const CREW = {
  access: process.env.CREW_ACCESS || '',
  refresh: process.env.CREW_REFRESH || '',
  sub: process.env.CREW_UID || '4a66036f-899c-40c8-9b2a-598cee24a62f',
  email: 'engineer.test@alex-short.com',
};

function writeStorageState(role: string, access: string, refresh: string, sub: string, email: string): string {
  if (!access || !refresh) throw new Error(`missing tokens for ${role}`);
  const sessionData = JSON.stringify({
    access_token: access, token_type: 'bearer', expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: refresh,
    user: { id: sub, email, aud: 'authenticated', role: 'authenticated' },
  });
  const state = { cookies: [], origins: [{ origin: BASE_URL, localStorage: [{ name: STORAGE_KEY, value: sessionData }] }] };
  fs.mkdirSync(PROOF_DIR, { recursive: true });
  const fp = path.join(PROOF_DIR, `storage-${role}.json`);
  fs.writeFileSync(fp, JSON.stringify(state, null, 2));
  return fp;
}

function fakeEditableWeek() {
  const weekStart = '2026-05-04';
  const dates = ['2026-05-04','2026-05-05','2026-05-06','2026-05-07','2026-05-08','2026-05-09','2026-05-10'];
  const ids = [
    'ffffffff-0000-4000-8000-000000000001','ffffffff-0000-4000-8000-000000000002',
    'ffffffff-0000-4000-8000-000000000003','ffffffff-0000-4000-8000-000000000004',
    'ffffffff-0000-4000-8000-000000000005','ffffffff-0000-4000-8000-000000000006',
    'ffffffff-0000-4000-8000-000000000007',
  ];
  return {
    status: 'success', week_start: weekStart, week_end: '2026-05-10',
    user_id: '4a66036f-899c-40c8-9b2a-598cee24a62f', department: 'general',
    days: dates.map((d, i) => ({
      id: ids[i], record_date: d, work_periods: [], rest_periods: [],
      total_rest_hours: 24, total_work_hours: 0,
      is_daily_compliant: null, daily_compliance_notes: null,
      location: null, voyage_type: null, submitted: false, warnings: [], updated_at: null,
    })),
    compliance: { rolling_24h_rest: null, rolling_7day_rest: 91 },
    pending_signoff: null, templates: [],
  };
}

test('MCP02 S1.1 — PR #569 b + c (real session)', async ({ browser }) => {
  const stateFile = writeStorageState('crew', CREW.access, CREW.refresh, CREW.sub, CREW.email);
  const context = await browser.newContext({ storageState: stateFile, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'networkidle', timeout: 45000 });
  // Wait for ANY hydrated content — either the week grid, a day label, or a scroll-able main
  try {
    await page.waitForFunction(() => {
      const main = document.querySelector('main');
      const txt = main?.textContent || '';
      return /Mon|Tue|Wed|Thu|Fri|Sat|Sun|week|WEEK/i.test(txt) && txt.length > 200;
    }, { timeout: 25000 });
  } catch {
    await page.screenshot({ path: path.join(PROOF_DIR, 'S1-1-stuck.png'), fullPage: true });
    const bodyText = (await page.textContent('body') || '').slice(0, 500);
    console.log(`[S1.1] stuck — body snippet: ${bodyText}`);
  }
  await page.waitForTimeout(2500);

  const layout = await page.evaluate(() => {
    const main = document.querySelector('main');
    const r = main?.getBoundingClientRect();
    const scrollers = Array.from(main?.querySelectorAll('*') || []).filter(el => {
      const cs = getComputedStyle(el);
      return cs.overflowY === 'auto' || cs.overflowY === 'scroll';
    }).map(el => ({ w: el.getBoundingClientRect().width, scrollH: (el as HTMLElement).scrollHeight, clientH: (el as HTMLElement).clientHeight }));
    return { mainW: r?.width ?? 0, vp: { w: window.innerWidth, h: window.innerHeight }, scrollers };
  });
  console.log(`[569b] mainW=${layout.mainW}px vp=${layout.vp.w}x${layout.vp.h}`);
  console.log(`[569c] scrollers[0]=${JSON.stringify(layout.scrollers[0])}`);
  await page.screenshot({ path: path.join(PROOF_DIR, 'S1-1-real-session.png'), fullPage: true });

  expect(layout.mainW).toBeGreaterThan(1000);
  expect(layout.scrollers.length).toBeGreaterThan(0);
  expect(layout.scrollers[0].clientH).toBeLessThan(layout.vp.h);

  await context.close();
});

test('MCP02 S1.2 — PR #569a (mocked editable week + forced /upsert failure)', async ({ browser }) => {
  const stateFile = writeStorageState('crew', CREW.access, CREW.refresh, CREW.sub, CREW.email);
  const context = await browser.newContext({ storageState: stateFile, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const consoleErrors: string[] = [];
  const apiHits: Array<{ url: string; body: any }> = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  await page.route(/\/hours-of-rest\/my-week/, async route => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify(fakeEditableWeek()),
    });
  });

  await page.route(/\/api\/v1\/hours-of-rest\/upsert/, async route => {
    const req = route.request();
    let bodyObj: any = null;
    try { bodyObj = JSON.parse(req.postData() || '{}'); } catch {}
    apiHits.push({ url: req.url(), body: bodyObj });
    if (req.method() === 'POST') {
      await route.fulfill({
        status: 400, contentType: 'application/json',
        body: JSON.stringify({
          status: 'error',
          error_code: 'LOCKED',
          message: 'MCP02-INJECTED: Simulated failure to verify PR #569a inline error surfacing path.',
        }),
      });
    } else { await route.continue(); }
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'networkidle', timeout: 45000 });
  await page.waitForSelector('text=/THIS WEEK|Week —/i', { timeout: 20000 });
  await page.waitForTimeout(2500);

  const tracks = await page.locator('.hor-track-bg').count();
  const notSubmittedCount = await page.getByText('Not submitted').count();
  console.log(`[S1.2] tracks=${tracks} notSubmitted=${notSubmittedCount}`);
  if (tracks === 0) throw new Error('mock did not produce editable tracks');

  const firstTrack = page.locator('.hor-track-bg').first();
  const box = await firstTrack.boundingBox();
  if (!box) throw new Error('track has no bounding box');
  await page.mouse.click(box.x + box.width * 0.4, box.y + box.height / 2);
  await page.waitForTimeout(800);

  const submitBtnCount = await page.locator('button', { hasText: /submit day/i }).count();
  console.log(`[S1.2] after track click: Submit Day count=${submitBtnCount}`);
  if (submitBtnCount === 0) throw new Error('no Submit Day button');

  await page.locator('button', { hasText: /submit day/i }).first().click();
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(PROOF_DIR, 'S1-2-after-submit.png'), fullPage: true });

  const dom = await page.evaluate(() => {
    const allText = (document.querySelector('main') as HTMLElement | null)?.innerText || '';
    return {
      containsMCP02Mark: /MCP02-INJECTED/.test(allText),
      containsMockMsg: /Simulated failure to verify PR #569a/.test(allText),
      containsWarningIcon: /⚠/.test(allText),
    };
  });
  console.log(`[S1.2] DOM inline-error check: MCP02-INJECTED=${dom.containsMCP02Mark}  ⚠=${dom.containsWarningIcon}`);
  const inlineErrorPresent = dom.containsMCP02Mark || dom.containsMockMsg;
  expect(inlineErrorPresent, 'PR #569a: inline error must surface on Submit Day API failure').toBeTruthy();

  await context.close();
});
