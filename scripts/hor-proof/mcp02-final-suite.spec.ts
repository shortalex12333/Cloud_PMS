/**
 * HOURSOFREST_MCP02 — Final post-deploy pass
 * Covers PR #588 + S5/S7/S11 UI.
 */
import { test, expect, BrowserContext, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const SUPABASE_PROJECT_REF = 'qvzmkaamzaqxpzbewjxe';
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;
const PROOF_DIR = process.env.PROOF_DIR || '/tmp/hor_mcp02';

type Role = 'crew' | 'hod' | 'captain' | 'fleet';
const ROLES: Record<Role, { access: string; refresh: string; sub: string; email: string }> = {
  crew:    { access: process.env.CREW_ACCESS || '',  refresh: process.env.CREW_REFRESH || '',  sub: '4a66036f-899c-40c8-9b2a-598cee24a62f', email: 'engineer.test@alex-short.com' },
  hod:     { access: process.env.HOD_ACCESS || '',   refresh: process.env.HOD_REFRESH || '',   sub: '81c239df-f8ef-4bba-9496-78bf8f46733c', email: 'eto.test@alex-short.com' },
  captain: { access: process.env.CAP_ACCESS || '',   refresh: process.env.CAP_REFRESH || '',   sub: 'a35cad0b-02ff-4287-b6e4-17c96fa6a424', email: 'x@alex-short.com' },
  fleet:   { access: process.env.FLEET_ACCESS || '', refresh: process.env.FLEET_REFRESH || '', sub: 'f11f1247-b7bd-4017-bfe3-ebd3f8c9e871', email: 'fleet-test-1775570624@celeste7.ai' },
};

function writeStorageState(role: Role): string {
  const u = ROLES[role];
  if (!u.access || !u.refresh) throw new Error(`missing tokens for ${role}`);
  const session = {
    access_token: u.access, token_type: 'bearer', expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: u.refresh,
    user: { id: u.sub, email: u.email, aud: 'authenticated', role: 'authenticated' },
  };
  const state = { cookies: [], origins: [{ origin: BASE_URL, localStorage: [{ name: STORAGE_KEY, value: JSON.stringify(session) }] }] };
  fs.mkdirSync(PROOF_DIR, { recursive: true });
  const fp = path.join(PROOF_DIR, `storage-${role}.json`);
  fs.writeFileSync(fp, JSON.stringify(state, null, 2));
  return fp;
}

const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

function bootstrapFor(role: Role) {
  const u = ROLES[role];
  // Supabase auth roles → HoR frontend role mapping
  const roleMap: Record<Role, string> = { crew: 'crew', hod: 'chief_engineer', captain: 'captain', fleet: 'manager' };
  const isFleet = role === 'fleet';
  return {
    yacht_id: YACHT_ID,
    yacht_name: 'M/Y Test Vessel',
    tenant_key_alias: 'yTEST_YACHT_001',
    role: roleMap[role],
    status: 'active',
    user_id: u.sub,
    email: u.email,
    subscription_active: true,
    subscription_status: 'paid',
    subscription_plan: 'none',
    subscription_expires_at: null,
    is_fleet_user: isFleet,
    vessel_ids: [YACHT_ID],
    fleet_vessels: isFleet ? [{ id: YACHT_ID, name: 'M/Y Test Vessel' }] : null,
  };
}

function fakeMyWeek(userId: string, dept: string) {
  return {
    status: 'success',
    week_start: '2026-04-13', week_end: '2026-04-19',
    user_id: userId, department: dept,
    days: Array.from({ length: 7 }, (_, i) => {
      const d = `2026-04-${String(13 + i).padStart(2, '0')}`;
      return { id: `mock-${userId.slice(0,8)}-${i}`, record_date: d, work_periods: [], rest_periods: [], total_rest_hours: 24, total_work_hours: 0, is_daily_compliant: null, submitted: false, warnings: [] };
    }),
    compliance: { rolling_24h_rest: null, rolling_7day_rest: 91 },
    pending_signoff: null, templates: [],
  };
}

async function installMocks(page: Page, role: Role) {
  const u = ROLES[role];
  const dept = role === 'hod' ? 'engineering' : role === 'captain' ? 'deck' : role === 'fleet' ? 'fleet' : 'general';
  await page.route(/backend\.celeste7\.ai\/v1\/bootstrap/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(bootstrapFor(role)) });
  });
  await page.route(/backend\.celeste7\.ai\/email\/unread-count/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0 }) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/my-week/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fakeMyWeek(u.sub, dept)) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/month-status/, async r => {
    const url = new URL(r.request().url());
    const month = url.searchParams.get('month') || '2026-04';
    const [y, m] = month.split('-').map(Number);
    const daysInMonth = new Date(y, m, 0).getDate();
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      status: 'success', month,
      days: Array.from({ length: daysInMonth }, (_, i) => ({ date: `${month}-${String(i+1).padStart(2,'0')}`, submitted: false, is_compliant: null })),
    }) });
  });
  await page.route(/\/api\/v1\/hours-of-rest\/warnings/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true, data: { warnings: [] } }) });
  });
  await page.route(/\/api\/v1\/notifications/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'success', data: [] }) });
  });
  // HOD/captain/fleet compliance endpoints (department-status + vessel-compliance)
  await page.route(/\/hours-of-rest\/(department-status|vessel-compliance)/, async r => {
    await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      status: 'success', week_start: '2026-04-13',
      vessel_summary: { total_crew: 3, submitted_count: 0, compliant_count: 0 },
      departments: [{ department: dept, total_crew: 1, submitted_count: 0, compliant_count: 0, pending_warnings: 0, pending_signoff_count: 0, signoff_id: null, status: 'draft', hod_signed_at: null }],
      all_crew: [{ user_id: ROLES.crew.sub, name: 'Engineer Test', department: 'general', total_work_hours: 0, total_rest_hours: 24, days_submitted: 0, is_weekly_compliant: false, has_active_warnings: false, signoff_status: 'draft' }],
      crew: [{ user_id: ROLES.crew.sub, name: 'Engineer Test', signoff_status: 'draft', daily: [] }],
      analytics: { avg_work_hours: 0, violations_this_week: 0, violations_this_quarter: 0, compliance_pct: 0 },
      sign_chain: { all_hods_signed: false, captain_signed: false, fleet_manager_reviewed: false },
    }) });
  });
}

async function openHoR(browser: any, role: Role): Promise<{ context: BrowserContext; page: Page }> {
  const stateFile = writeStorageState(role);
  const context = await browser.newContext({ storageState: stateFile, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installMocks(page, role);
  await page.goto(`${BASE_URL}/hours-of-rest`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  // Wait for hydration — the main nav Calendar button or tab buttons should appear
  await page.locator('main button').first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(2500);
  return { context, page };
}

test('PR #588 — fleet: no Submit Week For Approval button', async ({ browser }) => {
  const { context, page } = await openHoR(browser, 'fleet');
  const submitWeekInMain = await page.locator('main button', { hasText: /submit week/i }).count();
  const mainButtons = await page.locator('main button').allTextContents();
  console.log(`[PR #588] fleet main buttons: ${JSON.stringify(mainButtons.slice(0, 30))}`);
  expect(submitWeekInMain, 'fleet MUST NOT see Submit Week').toBe(0);
  await context.close();
});

test('S7 — fleet read-only (no sign buttons)', async ({ browser }) => {
  const { context, page } = await openHoR(browser, 'fleet');
  const writeButtons = await page.locator('main button').filter({ hasText: /sign|submit|create|dismiss|acknowledge/i }).allTextContents();
  console.log(`[S7] fleet write buttons: ${JSON.stringify(writeButtons)}`);
  expect(writeButtons.length).toBe(0);
  await context.close();
});

test('S5 — HOD department tab', async ({ browser }) => {
  const { context, page } = await openHoR(browser, 'hod');
  const deptTab = page.locator('main button, main [role="tab"]').filter({ hasText: /department/i });
  const deptCount = await deptTab.count();
  console.log(`[S5] HOD dept-tab count: ${deptCount}`);
  expect(deptCount).toBeGreaterThan(0);
  await context.close();
});

test('Positive control — captain sees Submit Week', async ({ browser }) => {
  const { context, page } = await openHoR(browser, 'captain');
  const mainButtons = await page.locator('main button').allTextContents();
  const hasSubmitWeek = mainButtons.some(b => /submit week/i.test(b));
  console.log(`[positive ctrl] captain sees Submit Week: ${hasSubmitWeek}`);
  console.log(`[positive ctrl] captain buttons: ${JSON.stringify(mainButtons.slice(0, 20))}`);
  expect(hasSubmitWeek, 'captain should see Submit Week').toBe(true);
  await context.close();
});
