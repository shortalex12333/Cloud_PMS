/**
 * PR #614 verification — post-deploy pass
 * Tests: zoom removal, calendar button, month nav, day click, HOD dept tab, captain submit week
 *
 * Mocks backend.celeste7.ai/v1/bootstrap + all HoR API calls so tests are immune
 * to Render free-tier hibernation. Real services not needed for PR #614 UI behaviour.
 *
 * Runs against app.celeste7.ai with pre-minted auth state from playwright/.auth/
 */
import { test, expect } from '@playwright/test';
import * as path from 'path';

const BASE_URL = 'https://app.celeste7.ai';
const AUTH_DIR = path.join(__dirname, '../../playwright/.auth');
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

function fakeDays(count: number, month: string) {
  return Array.from({ length: count }, (_, i) => {
    const d = String(i + 1).padStart(2, '0');
    return { date: `${month}-${d}`, submitted: i >= 12 && i <= 15, is_compliant: i >= 13 && i <= 15 ? true : null };
  });
}

async function installMocks(page: any, role = 'crew') {
  await page.route(/backend\.celeste7\.ai\/v1\/bootstrap/, async (route: any) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        status: 'active',  // processBootstrapData needs 'active' to update role
        yacht_id: YACHT_ID, yacht_name: 'M/Y Test Vessel', role,
        user_id: 'aaaaaaaa-0000-4000-8000-000000000001',
        email: `${role}@test.com`, subscription_active: true,
        subscription_status: 'paid', is_fleet_user: false,
        vessel_ids: [YACHT_ID], fleet_vessels: null,
      }),
    });
  });
  await page.route(/backend\.celeste7\.ai\/email\/unread-count/, async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/my-week/, async (route: any) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        status: 'success', week_start: '2026-04-13', week_end: '2026-04-19',
        days: Array.from({ length: 7 }, (_, i) => ({
          id: `aaaaaaaa-0000-4000-8000-00000000001${i}`,
          record_date: `2026-04-${String(13 + i).padStart(2, '0')}`,
          work_periods: [{ start: '10:00', end: '11:00', hours: 1 }],
          rest_periods: [], total_rest_hours: 23, total_work_hours: 1,
          is_daily_compliant: true, submitted: true, warnings: [],
        })),
        compliance: { rolling_24h_rest: 23, rolling_7day_rest: 91 },
        pending_signoff: null, templates: [],
      }),
    });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/month-status/, async (route: any) => {
    const url = new URL(route.request().url());
    const month = url.searchParams.get('month') || '2026-04';
    const [y, m] = month.split('-').map(Number);
    const daysInMonth = new Date(y, m, 0).getDate();
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ status: 'success', month, days: fakeDays(daysInMonth, month) }),
    });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/warnings/, async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { warnings: [] } }) });
  });
  await page.route(/\/api\/v1\/notifications/, async (route: any) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'success', data: [] }) });
  });
}

// ── 1. zoom:0.8 removed — shell fills viewport ────────────────────────────────
test('PR #614 (1) zoom removed — shell fills viewport', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'crew.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  await installMocks(page, 'crew');
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);

  const m = await page.evaluate(() => ({
    htmlZoom: getComputedStyle(document.documentElement).zoom,
    bodyZoom: getComputedStyle(document.body).zoom,
    vp: { w: window.innerWidth, h: window.innerHeight },
    sidebarBottom: document.querySelector('nav')?.getBoundingClientRect().bottom ?? 0,
  }));
  console.log(`[PR614-1] htmlZoom=${m.htmlZoom} vp=${m.vp.w}x${m.vp.h} sidebarBot=${m.sidebarBottom}`);
  expect(m.htmlZoom === '1' || m.htmlZoom === 'normal' || m.htmlZoom === '').toBe(true);
  expect(m.sidebarBottom).toBeGreaterThan(m.vp.h - 80);
  await ctx.close();
});

// ── 2+3. CALENDAR button exists + opens month grid ────────────────────────────
test('PR #614 (2+3) — CALENDAR button + opens calendar', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'crew.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  await installMocks(page, 'crew');
  const monthStatusHits: number[] = [];
  page.on('response', r => {
    if (r.url().includes('month-status')) monthStatusHits.push(r.status());
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const calBtn = page.locator('main button', { hasText: /calendar/i }).first();
  await calBtn.waitFor({ timeout: 30000 });

  const btnText = ((await calBtn.textContent()) || '').trim();
  const btnNorm = btnText.replace(/[^A-Za-z]/g, '').toUpperCase();
  console.log(`[PR614-2] button raw="${btnText}" norm="${btnNorm}"`);
  expect(btnNorm).toBe('CALENDAR');

  await calBtn.click();
  await page.waitForTimeout(2000);
  console.log(`[PR614-3] month-status hits: ${JSON.stringify(monthStatusHits)}`);
  expect(monthStatusHits.length, 'calendar open should fetch month-status').toBeGreaterThan(0);
  expect(monthStatusHits.every(s => s < 500)).toBe(true);

  const monthLabel = await page.getByText(/January|February|March|April|May|June|July|August|September|October|November|December/i).count();
  expect(monthLabel).toBeGreaterThan(0);
  await ctx.close();
});

// ── 4. Month navigation prev/next ─────────────────────────────────────────────
test('PR #614 (4) — month navigation prev/next', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'crew.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  await installMocks(page, 'crew');
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('main button', { hasText: /calendar/i }).first().waitFor({ timeout: 30000 });
  await page.locator('main button', { hasText: /calendar/i }).first().click();
  await page.waitForTimeout(2000);

  const labelBefore = ((await page.getByText(/^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i).first().textContent()) || '').trim();
  // Click ‹ (prev month) — ›  is disabled at current month (April 2026 = nowYM guard in code)
  const prevBtns = page.locator('button').filter({ hasText: /^‹$/ });
  await prevBtns.last().click();
  await page.waitForTimeout(1500);
  const labelAfter = ((await page.getByText(/^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i).first().textContent()) || '').trim();

  console.log(`[PR614-4] "${labelBefore}" → "${labelAfter}"`);
  expect(labelBefore).not.toBe(labelAfter);
  await ctx.close();
});

// ── 5. Day click changes week ──────────────────────────────────────────────────
test('PR #614 (5) — day click triggers week reload', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'crew.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  await installMocks(page, 'crew');
  const myWeekHits: number[] = [];
  page.on('response', r => {
    if (r.url().includes('/api/v1/hours-of-rest/my-week')) myWeekHits.push(r.status());
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('main button', { hasText: /calendar/i }).first().waitFor({ timeout: 30000 });
  await page.locator('main button', { hasText: /calendar/i }).first().click();
  await page.waitForTimeout(2000);

  const hitsBefore = myWeekHits.length;
  const dayData = await page.evaluate(() => {
    // Find the calendar grid that contains actual day buttons (not the M/T/W/T/F/S/S header row)
    const grids = Array.from(document.querySelectorAll('div[style*="grid-template-columns"]')) as HTMLElement[];
    const calGrids = grids.filter(g => /repeat\s*\(\s*7/.test(g.getAttribute('style') || ''));
    // The grid with buttons is the day-cell grid (the header-only grid has no buttons)
    const cal = calGrids.find(g => g.querySelectorAll('button').length > 0);
    if (!cal) return { err: `no grid (found ${calGrids.length} repeat-7 grids)` } as const;
    const btns = Array.from(cal.querySelectorAll('button')).filter(b => /^\s*\d{1,2}\s*$/.test((b as HTMLElement).innerText.trim()));
    const target = btns.find(b => (b as HTMLElement).innerText.trim() === '10') || btns[5];
    if (!target) return { err: 'no target day' } as const;
    const r = target.getBoundingClientRect();
    return { text: (target as HTMLElement).innerText.trim(), x: r.x + r.width / 2, y: r.y + r.height / 2 } as const;
  });
  console.log(`[PR614-5] day target: ${JSON.stringify(dayData)}`);
  if ('err' in dayData) throw new Error(dayData.err);

  await page.mouse.click(dayData.x, dayData.y);
  await page.waitForTimeout(3000);
  const newHits = myWeekHits.slice(hitsBefore);
  console.log(`[PR614-5] new my-week calls: ${newHits.length}`);
  expect(newHits.length).toBeGreaterThan(0);
  await ctx.close();
});

// ── S5. HOD sees department tab ────────────────────────────────────────────────
test('S5 — HOD sees department tab', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'hod.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  // isHODRole() checks ['chief_engineer','chief_officer','eto'] — NOT 'hod'
  await installMocks(page, 'eto');
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('text=/HOURS OF REST|THIS WEEK/i', { timeout: 30000 });
  await page.waitForTimeout(2500);

  const deptTab = page.locator('main button, main [role="tab"]').filter({ hasText: /department/i });
  const count = await deptTab.count();
  console.log(`[S5] HOD dept-tab count: ${count}`);
  expect(count).toBeGreaterThan(0);
  await ctx.close();
});

// ── Positive control. Captain sees Submit Week ─────────────────────────────────
test('Positive control — captain sees Submit Week', async ({ browser }) => {
  const ctx = await browser.newContext({
    storageState: path.join(AUTH_DIR, 'captain.json'),
    viewport: { width: 1440, height: 900 },
  });
  const page = await ctx.newPage();
  await installMocks(page, 'captain');
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('text=/HOURS OF REST|THIS WEEK/i', { timeout: 30000 });
  await page.waitForTimeout(2500);

  const buttons = await page.locator('main button').allTextContents();
  const hasSubmitWeek = buttons.some(b => /submit week/i.test(b));
  console.log(`[ctrl] captain Submit Week: ${hasSubmitWeek}`);
  console.log(`[ctrl] captain buttons: ${JSON.stringify(buttons.slice(0, 20))}`);
  expect(hasSubmitWeek).toBe(true);
  await ctx.close();
});
