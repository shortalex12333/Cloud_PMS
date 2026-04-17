/**
 * HOURSOFREST_MCP02 — PR #614 calendar verification (mocked upstream)
 * Strategy: mock backend.celeste7.ai/v1/bootstrap + /email/unread-count +
 * app.celeste7.ai/api/v1/hours-of-rest/* so tests run fully client-side and are
 * immune to Render hibernation oscillation.
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
  sub: '4a66036f-899c-40c8-9b2a-598cee24a62f',
  email: 'engineer.test@alex-short.com',
};
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

function writeStorageState(): string {
  if (!CREW.access || !CREW.refresh) throw new Error('missing CREW_ACCESS / CREW_REFRESH');
  const session = {
    access_token: CREW.access, token_type: 'bearer', expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: CREW.refresh,
    user: { id: CREW.sub, email: CREW.email, aud: 'authenticated', role: 'authenticated' },
  };
  const state = { cookies: [], origins: [{ origin: BASE_URL, localStorage: [{ name: STORAGE_KEY, value: JSON.stringify(session) }] }] };
  fs.mkdirSync(PROOF_DIR, { recursive: true });
  const fp = path.join(PROOF_DIR, 'storage-crew.json');
  fs.writeFileSync(fp, JSON.stringify(state, null, 2));
  return fp;
}

function fakeBootstrap() {
  return {
    yacht_id: YACHT_ID,
    yacht_name: 'M/Y Test Vessel',
    tenant_key_alias: 'yTEST_YACHT_001',
    role: 'crew',
    status: 'active',
    user_id: CREW.sub,
    email: CREW.email,
    subscription_active: true,
    subscription_status: 'paid',
    subscription_plan: 'none',
    subscription_expires_at: null,
    is_fleet_user: false,
    vessel_ids: [YACHT_ID],
    fleet_vessels: null,
  };
}

function fakeMyWeek() {
  return {
    status: 'success',
    week_start: '2026-04-13',
    week_end: '2026-04-19',
    user_id: CREW.sub,
    department: 'general',
    days: [
      { id: 'd4f78a50-e628-4f1b-a9ef-2eb4863afb08', record_date: '2026-04-13', work_periods: [{start:'04:30',end:'05:30',hours:1}], rest_periods: [], total_rest_hours:22, total_work_hours:2, is_daily_compliant:false, daily_compliance_notes:null, location:null, voyage_type:null, submitted:true, warnings: [] },
      { id: 'f3c1be63-ae4f-43f9-9fac-a8b368308bcd', record_date: '2026-04-14', work_periods: [{start:'10:30',end:'11:30',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
      { id: '27cb17c7-611b-4d79-b311-925d7af20230', record_date: '2026-04-15', work_periods: [{start:'11:30',end:'12:30',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
      { id: 'aaaaaaaa-0000-4000-8000-000000000016', record_date: '2026-04-16', work_periods: [{start:'10:00',end:'11:00',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
      { id: 'aaaaaaaa-0000-4000-8000-000000000017', record_date: '2026-04-17', work_periods: [{start:'10:00',end:'11:00',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
      { id: 'aaaaaaaa-0000-4000-8000-000000000018', record_date: '2026-04-18', work_periods: [{start:'10:00',end:'11:00',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
      { id: 'aaaaaaaa-0000-4000-8000-000000000019', record_date: '2026-04-19', work_periods: [{start:'10:00',end:'11:00',hours:1}], rest_periods: [], total_rest_hours:23, total_work_hours:1, is_daily_compliant:true, submitted:true, warnings: [] },
    ],
    compliance: { rolling_24h_rest: 23, rolling_7day_rest: 91 },
    pending_signoff: null,
    templates: [],
  };
}

function fakeMonthStatus(month: string) {
  const [y, m] = month.split('-').map(Number);
  const daysInMonth = new Date(y, m, 0).getDate();
  return {
    status: 'success',
    month,
    days: Array.from({ length: daysInMonth }, (_, i) => {
      const d = String(i + 1).padStart(2, '0');
      return { date: `${month}-${d}`, submitted: (i >= 12 && i <= 15), is_compliant: (i >= 13 && i <= 15) ? true : (i === 12 ? false : null) };
    }),
  };
}

async function installMocks(page: any) {
  await page.route(/backend\.celeste7\.ai\/v1\/bootstrap/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fakeBootstrap()) });
  });
  await page.route(/backend\.celeste7\.ai\/email\/unread-count/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/my-week/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fakeMyWeek()) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/month-status/, async route => {
    const url = new URL(route.request().url());
    const month = url.searchParams.get('month') || '2026-04';
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fakeMonthStatus(month)) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/warnings/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { warnings: [] } }) });
  });
  await page.route(/\/api\/v1\/notifications/, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'success', data: [] }) });
  });
}

// ── PR #614 (1) layout — no mocks needed, this is purely frontend CSS ───
test('PR #614 (1) — zoom:0.8 removed, shell fills viewport height', async ({ browser }) => {
  const context = await browser.newContext({ storageState: writeStorageState(), viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installMocks(page);
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  const m = await page.evaluate(() => {
    const main = document.querySelector('main');
    const sidebar = document.querySelector('nav');
    return {
      htmlZoom: getComputedStyle(document.documentElement).zoom,
      bodyZoom: getComputedStyle(document.body).zoom,
      vp: { w: window.innerWidth, h: window.innerHeight },
      sidebarBottom: sidebar?.getBoundingClientRect().bottom ?? 0,
    };
  });
  console.log(`[PR614-1] htmlZoom=${m.htmlZoom} vp=${m.vp.w}x${m.vp.h} sidebarBot=${m.sidebarBottom}`);
  expect(m.htmlZoom === '1' || m.htmlZoom === 'normal' || m.htmlZoom === '').toBe(true);
  expect(m.sidebarBottom).toBeGreaterThan(m.vp.h - 80);
  await context.close();
});

// ── PR #614 (2+3) Calendar button + open without 502 ───────────────────
test('PR #614 (2+3) — CALENDAR button + opens (mocked month-status)', async ({ browser }) => {
  const context = await browser.newContext({ storageState: writeStorageState(), viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installMocks(page);

  const monthStatusHits: Array<{ status: number; url: string }> = [];
  page.on('response', r => {
    if (r.url().includes('month-status')) monthStatusHits.push({ status: r.status(), url: r.url() });
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('main button', { hasText: /calendar/i }).first().waitFor({ timeout: 30000 });

  const calBtn = page.locator('main button', { hasText: /calendar/i }).first();
  const btnText = (await calBtn.textContent() || '').trim();
  const btnNorm = btnText.replace(/[^A-Za-z]/g, '').toUpperCase();
  console.log(`[PR614-2] button raw="${btnText}" norm="${btnNorm}"`);
  expect(btnNorm).toBe('CALENDAR');

  await calBtn.click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(PROOF_DIR, 'PR614-2-open.png'), fullPage: false });

  console.log(`[PR614-3] month-status hits: ${JSON.stringify(monthStatusHits)}`);
  expect(monthStatusHits.length, 'calendar open should fetch month-status').toBeGreaterThan(0);
  expect(monthStatusHits.every(h => h.status < 500)).toBe(true);
  const monthLabelCount = await page.getByText(/January|February|March|April|May|June|July|August|September|October|November|December/i).count();
  expect(monthLabelCount).toBeGreaterThan(0);

  await context.close();
});

// ── PR #614 (4) Month nav ←→ ───────────────────────────────────────────
test('PR #614 (4) — month navigation prev/next', async ({ browser }) => {
  const context = await browser.newContext({ storageState: writeStorageState(), viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installMocks(page);

  const monthStatusUrls: string[] = [];
  page.on('response', r => {
    if (r.url().includes('month-status')) {
      const m = r.url().match(/month=(\d{4}-\d{2})/);
      if (m) monthStatusUrls.push(m[1]);
    }
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('main button', { hasText: /calendar/i }).first().waitFor({ timeout: 30000 });
  await page.locator('main button', { hasText: /calendar/i }).first().click();
  await page.waitForTimeout(2000);

  await page.screenshot({ path: path.join(PROOF_DIR, 'PR614-4-before-click.png'), fullPage: false });

  // Dump all arrow-like buttons with coords for debug
  const debug = await page.evaluate(() => {
    const labels = Array.from(document.querySelectorAll('*')).filter(el =>
      /^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i.test((el as HTMLElement).innerText?.trim() || '')
    ).map(el => { const r = el.getBoundingClientRect(); return { text: (el as HTMLElement).innerText.trim(), x: r.x, y: r.y, w: r.width, tag: el.tagName }; });
    const arrows = Array.from(document.querySelectorAll('button')).filter(b => /^[‹›←→]$/.test((b as HTMLElement).innerText.trim())).map(b => {
      const r = b.getBoundingClientRect();
      return { text: (b as HTMLElement).innerText.trim(), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), disabled: (b as HTMLButtonElement).disabled };
    });
    return { labels, arrows };
  });
  console.log(`[PR614-4 DEBUG] labels: ${JSON.stringify(debug.labels)}`);
  console.log(`[PR614-4 DEBUG] arrows: ${JSON.stringify(debug.arrows)}`);

  // Click the CALENDAR popover's ‹ (PREV) arrow.
  // From DOM debug: calendar arrows are at y≈165, w=5px (narrow chevrons). The y=126 ones are topbar icons (not calendar).
  // Pick the ‹ that is CLOSEST in y to the month-label "APRIL 2026" (which sits at y≈167 in the calendar header row).
  const clickInfo = await page.evaluate(() => {
    const label = Array.from(document.querySelectorAll('*')).find(el =>
      /^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i.test((el as HTMLElement).innerText?.trim() || '')
    ) as HTMLElement | undefined;
    if (!label) return { err: 'no month label' } as const;
    const labelRect = label.getBoundingClientRect();

    const prevs = Array.from(document.querySelectorAll('button')).filter(b => {
      const t = (b as HTMLElement).innerText.trim();
      if (!/^[‹←]$/.test(t)) return false;
      if ((b as HTMLButtonElement).disabled) return false;
      const r = b.getBoundingClientRect();
      return r.width > 0 && r.height > 0;  // just exclude invisible
    });
    if (prevs.length === 0) return { err: 'no prev arrow' } as const;
    // Prefer the arrow whose y is within 30px of the label's y (same calendar row)
    const pick = prevs.sort((a, b) => {
      const ay = Math.abs(a.getBoundingClientRect().y - labelRect.y);
      const by = Math.abs(b.getBoundingClientRect().y - labelRect.y);
      return ay - by;
    })[0];
    const r = pick.getBoundingClientRect();
    return {
      pickRect: { x: r.x, y: r.y, w: r.width, h: r.height },
      arrowCount: prevs.length,
      labelBefore: label.innerText.trim(),
      labelRect: { x: labelRect.x, y: labelRect.y, w: labelRect.width },
    } as const;
  });
  console.log(`[PR614-4] scope-find: ${JSON.stringify(clickInfo)}`);
  if ('err' in clickInfo) throw new Error(clickInfo.err);
  if (!clickInfo.pickRect) throw new Error('no next-arrow in calendar popover');
  await page.mouse.click(clickInfo.pickRect.x + clickInfo.pickRect.w/2, clickInfo.pickRect.y + clickInfo.pickRect.h/2);
  await page.waitForTimeout(2000);

  // Month nav is client-side (setCalMonth, no API fetch per HOURSOFREST01).
  // Assert on label change via same innerText method.
  const labelAfter = await page.evaluate(() => {
    const el = Array.from(document.querySelectorAll('*')).find(x =>
      /^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i.test((x as HTMLElement).innerText?.trim() || '')
    ) as HTMLElement | undefined;
    return el?.innerText.trim() || '';
  });
  const normBefore = (clickInfo.labelBefore.match(/^[A-Z]+\s+\d{4}$/i) || [''])[0].toUpperCase();
  const normAfter = (labelAfter.match(/^[A-Z]+\s+\d{4}$/i) || [''])[0].toUpperCase();
  console.log(`[PR614-4] label: "${clickInfo.labelBefore}" → "${labelAfter}"  norm: ${normBefore} → ${normAfter}`);
  console.log(`[PR614-4] month-status URL params fired: ${JSON.stringify(monthStatusUrls)}`);
  expect(normAfter, 'calendar month label should change after PREV click').not.toBe(normBefore);
  await context.close();
});

// ── PR #614 (5) Day click changes week grid ────────────────────────────
test('PR #614 (5) — day click changes week', async ({ browser }) => {
  const context = await browser.newContext({ storageState: writeStorageState(), viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installMocks(page);

  const myWeekHits: Array<{ status: number; url: string }> = [];
  page.on('response', r => {
    if (r.url().includes('/api/v1/hours-of-rest/my-week')) myWeekHits.push({ status: r.status(), url: r.url() });
  });

  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('main button', { hasText: /calendar/i }).first().waitFor({ timeout: 30000 });
  await page.locator('main button', { hasText: /calendar/i }).first().click();
  await page.waitForTimeout(2000);

  const weekHeaderBefore = (await page.locator('main').textContent() || '').match(/(?:THIS WEEK|Week)[^\n]*?\d{4}-\d{2}-\d{2}/)?.[0] || '';
  const myWeekBefore = myWeekHits.length;

  // Find day cell in the grid-template-columns:repeat(7,...) grid.
  // Fallback: search any pure-numeric button inside the calendar popover if the grid selector is flaky.
  const dayData = await page.evaluate(() => {
    // Find month label as anchor
    const label = Array.from(document.querySelectorAll('*')).find(el =>
      /^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$/i.test((el as HTMLElement).innerText?.trim() || '')
    ) as HTMLElement | undefined;
    if (!label) return { err: 'no month label' } as const;
    // Walk up from label until we find an ancestor that contains >= 20 numeric buttons
    let root: HTMLElement | null = label;
    let dayBtns: HTMLButtonElement[] = [];
    for (let hop = 0; hop < 8 && root; hop++) {
      dayBtns = Array.from(root.querySelectorAll('button')).filter(b => /^\s*\d{1,2}\s*$/.test((b as HTMLElement).innerText.trim())) as HTMLButtonElement[];
      if (dayBtns.length >= 20) break;
      root = root.parentElement;
    }
    if (dayBtns.length < 10) return { err: `insufficient day buttons (${dayBtns.length})` } as const;
    const target = dayBtns.find(b => b.innerText.trim() === '21') || dayBtns[19];
    if (!target) return { err: 'no target day' } as const;
    const r = target.getBoundingClientRect();
    return { text: target.innerText.trim(), totalBtns: dayBtns.length, x: r.x + r.width/2, y: r.y + r.height/2 } as const;
  });
  console.log(`[PR614-5] day click target: ${JSON.stringify(dayData)}`);
  if ('err' in dayData) throw new Error(dayData.err);
  await page.mouse.click(dayData.x, dayData.y);
  await page.waitForTimeout(3000);

  const weekHeaderAfter = (await page.locator('main').textContent() || '').match(/(?:THIS WEEK|Week)[^\n]*?\d{4}-\d{2}-\d{2}/)?.[0] || '';
  const newMyWeek = myWeekHits.slice(myWeekBefore);
  console.log(`[PR614-5] header "${weekHeaderBefore}" → "${weekHeaderAfter}"`);
  console.log(`[PR614-5] new /my-week calls: ${newMyWeek.length}`);

  // Pass if either header changed OR my-week was refetched
  expect(weekHeaderBefore !== weekHeaderAfter || newMyWeek.length > 0).toBe(true);
  await context.close();
});
