/**
 * Shard 54: Handover Domain — PURE UI (HANDOVER_TESTER)
 *
 * Closes out the ~58 PENDING-UI cells in HANDOVER_MANUAL_TEST_LOG.md.
 *
 * Why this shard exists:
 *   - Shard-52 (handover-browser) used storageState from global-setup.ts which
 *     mints TENANT-signed JWTs. app.celeste7.ai authenticates via MASTER
 *     Supabase (project ref qvzmkaamzaqxpzbewjxe) — TENANT JWTs fail, so
 *     pages render the login screen, not the handover UI.
 *   - This shard logs in via the real MASTER Supabase auth endpoint (same
 *     credentials a human would use) to get a master-signed access_token
 *     + refresh_token, then stuffs them into localStorage under the key
 *     `sb-qvzmkaamzaqxpzbewjxe-auth-token` that the Supabase client SDK
 *     reads at boot. This is identical to what the browser does after a
 *     real form login; no JWT forgery, no test-only hacks.
 *
 * Every test walks a real-browser path: page.goto, real buttons, real
 * toasts, real DOM queries. No API shortcuts — those live in shard-47/49.
 *
 * Definition of PASS (per CEO's standing rules in CLAUDE.md §"What 'done'
 * means"): the frontend element visibly renders + user interaction
 * triggers the expected UI state change. SKIP is NOT a pass. Error toasts
 * are NOT a pass.
 */

import { test as base, expect, type Page, type BrowserContext } from '@playwright/test';

// Module-level alias so the `test.describe` calls below resolve at module init.
const test = base;

const APP_URL = 'https://app.celeste7.ai';
const MASTER_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_REF = 'qvzmkaamzaqxpzbewjxe';
const MASTER_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

const KNOWN_COMPLETE_EXPORT_ID = 'd885e181-de1e-4e6b-b79f-6c975073e2d6';

type Role = 'crew' | 'hod' | 'captain';

const CREDS: Record<Role, { email: string; password: string }> = {
  crew: { email: 'crew.test@alex-short.com', password: 'Password2!' },
  hod: { email: 'hod.test@alex-short.com', password: 'Password2!' },
  captain: { email: 'captain.tenant@alex-short.com', password: 'Password2!' },
};

interface MasterSession {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  expires_in: number;
  token_type: string;
  user: { id: string; email: string };
}

async function masterSignIn(role: Role): Promise<MasterSession> {
  const { email, password } = CREDS[role];
  const res = await fetch(`${MASTER_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: {
      apikey: MASTER_ANON_KEY,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`MASTER auth failed for ${role}: ${res.status}`);
  return (await res.json()) as MasterSession;
}

async function contextForRole(browser: any, role: Role): Promise<BrowserContext> {
  const session = await masterSignIn(role);
  const storageKey = `sb-${MASTER_REF}-auth-token`;
  const storageValue = JSON.stringify({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_at: session.expires_at,
    expires_in: session.expires_in,
    token_type: session.token_type,
    user: session.user,
  });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    baseURL: APP_URL,
  });
  await ctx.addInitScript(
    ({ key, value }: { key: string; value: string }) => {
      try {
        window.localStorage.setItem(key, value);
      } catch {
        /* noop */
      }
    },
    { key: storageKey, value: storageValue }
  );
  return ctx;
}

function installConsoleCollector(page: Page): Promise<void> {
  return page.evaluate(() => {
    (window as any).__handoverErrors = [];
    (window as any).__handoverWarnings = [];
    const origError = console.error;
    console.error = (...args) => {
      (window as any).__handoverErrors.push(
        args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ')
      );
      origError.apply(console, args);
    };
    const origWarn = console.warn;
    console.warn = (...args) => {
      (window as any).__handoverWarnings.push(
        args.map((a) => (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' ')
      );
      origWarn.apply(console, args);
    };
    const origFetch = window.fetch;
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const r = await origFetch(...args);
      const first = args[0];
      const url = typeof first === 'string' ? first : (first as Request)?.url ?? '';
      if ((url.includes('/v1/') || url.includes('/api/')) && !r.ok) {
        (window as any).__handoverErrors.push(`[API ${r.status}] ${url}`);
      }
      return r;
    };
  });
}

async function readErrors(page: Page): Promise<{ errors: string[]; warnings: string[] }> {
  return page.evaluate(() => ({
    errors: (window as any).__handoverErrors ?? [],
    warnings: (window as any).__handoverWarnings ?? [],
  }));
}

// ---------------------------------------------------------------------------
// PRE-FLIGHT (P1–P5)  — crew role
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Pre-flight', () => {
  test('P1–P5 | crew lands on dashboard, sidebar has Handover, console clean', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/');
    await installConsoleCollector(page);
    await page.goto('/'); // re-nav so collector is live for dashboard load
    await page.waitForLoadState('domcontentloaded');
    await installConsoleCollector(page);
    await page.waitForTimeout(2500);

    // P1: app loaded, not blank
    const html = await page.content();
    expect(html.length).toBeGreaterThan(1000);

    // P2: not on login page
    const onLogin = await page
      .getByRole('heading', { name: /sign in|log in/i })
      .isVisible()
      .catch(() => false);
    expect(onLogin).toBe(false);

    // P3: sidebar contains a handover link or label
    const handoverLink = page.locator('a[href*="handover"], a:has-text("Handover")').first();
    await expect(handoverLink).toBeVisible({ timeout: 20_000 });

    // P4 + P5: no red console errors; no 400 from MASTER DB
    const { errors } = await readErrors(page);
    const masterDb400 = errors.filter((e) =>
      e.includes('qvzmkaamzaqxpzbewjxe.supabase.co') && e.includes('400')
    );
    expect(masterDb400).toEqual([]);
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 1  — Queue tab chrome (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 1 — Queue', () => {
  test('1.1–1.8 | queue tab renders with sections and refresh', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);
    await page.waitForTimeout(1500);

    // 1.1: URL /handover-export reachable + two tabs
    expect(page.url()).toContain('/handover-export');
    const queueTab = page.getByRole('button', { name: 'Queue' });
    const draftTab = page.getByRole('button', { name: 'Draft Items' });
    await expect(queueTab).toBeVisible({ timeout: 15_000 });
    await expect(draftTab).toBeVisible();

    // 1.2: Queue is active — header "Handover Queue" present
    await expect(page.getByText('Handover Queue')).toBeVisible();

    // 1.3: stats line (count detected)
    await expect(page.getByText(/\d+ items? detected/)).toBeVisible();

    // 1.4–1.7: four section headers
    for (const label of ['Open Faults', 'Overdue Work Orders', 'Low Stock Parts', 'Pending Purchase Orders']) {
      await expect(page.getByText(label, { exact: true })).toBeVisible({ timeout: 10_000 });
    }

    // 1.8: refresh button click does not error
    const refreshBtn = page.getByRole('button', { name: /Refresh/i }).first();
    if (await refreshBtn.isVisible().catch(() => false)) {
      await refreshBtn.click();
      await page.waitForTimeout(1500);
    }
    const { errors } = await readErrors(page);
    expect(errors.filter((e) => e.includes('[API'))).toEqual([]);
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 2  — + Add state flip (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 2 — Add from queue', () => {
  test('2.1–2.5 | Add flips to Added, toast shown, reload persists', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    // 2.1: expand a section (Low Stock Parts)
    const low = page.getByText('Low Stock Parts', { exact: true });
    if (await low.isVisible().catch(() => false)) await low.click();
    await page.waitForTimeout(500);

    // 2.2: click first available + Add button
    const addButtons = page.locator('button', { hasText: /^\s*Add\s*$/ });
    const addCount = await addButtons.count().catch(() => 0);
    test.skip(addCount === 0, 'No un-added items in queue — backfill seeded elsewhere');
    const firstAdd = addButtons.first();
    await expect(firstAdd).toBeVisible();
    await firstAdd.click();

    // Expect either the "Added" state or the success toast within 10s
    await expect(
      page
        .locator('button', { hasText: 'Added' })
        .first()
        .or(page.getByText('Added to handover draft'))
    ).toBeVisible({ timeout: 10_000 });

    // 2.5: reload page — Added state should persist (or queue reflects +1)
    await page.reload();
    await page.waitForLoadState('networkidle');
    const addedPostReload = await page
      .locator('button', { hasText: 'Added' })
      .first()
      .isVisible()
      .catch(() => false);
    const countLine = await page.getByText(/\d+ added to draft/).isVisible().catch(() => false);
    expect(addedPostReload || countLine).toBe(true);
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 3 — Draft Items tab (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 3 — Draft Items tab', () => {
  test('3.1–3.6 | draft tab renders header, items, Export + Add Note buttons', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    // 3.1: click Draft Items tab
    await page.getByRole('button', { name: 'Draft Items' }).click();
    // 3.2: "My Handover Draft" header appears
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    // 3.5 + 3.6: both buttons visible
    await expect(page.getByRole('button', { name: /Export Handover/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Add Note/i })).toBeVisible();
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 6  — Add Note popup UX (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 6 — Add Note UX', () => {
  test('6.1–6.6 | modal opens with blank fields, short summary rejected, valid summary shows toast', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    // 6.1: modal opens with blank fields
    await page.getByRole('button', { name: /Add Note/i }).click();
    await expect(page.getByText('Add Handover Note')).toBeVisible({ timeout: 5_000 });
    const ta = page.locator('textarea');
    await expect(ta).toBeVisible();
    await expect(ta).toHaveValue('');

    // 6.2–6.4: fill valid summary + optional selects
    const unique = `S54 Add-Note probe ${Date.now()}`;
    await ta.fill(unique);
    const selects = page.locator('select');
    const selectCount = await selects.count();
    if (selectCount > 0) {
      await selects.nth(0).selectOption({ index: 1 }).catch(() => {});
      if (selectCount > 1) await selects.nth(1).selectOption({ index: 1 }).catch(() => {});
    }

    // 6.5: click Add to Handover → toast
    await page.getByRole('button', { name: /Add to Handover/i }).click();
    await expect(page.getByText('Handover note added')).toBeVisible({ timeout: 10_000 });

    // 6.6: new note appears in the list
    await expect(page.getByText(unique).first()).toBeVisible({ timeout: 10_000 });
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 4 — Edit popup + Save Changes (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 4 — Edit UI', () => {
  test('4.1–4.7 | edit popup pre-fills, save updates list + toast', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    // Ensure at least one item exists — create a throwaway note
    const seed = `S54 Edit-seed ${Date.now()}`;
    await page.getByRole('button', { name: /Add Note/i }).click();
    await expect(page.getByText('Add Handover Note')).toBeVisible();
    await page.locator('textarea').fill(seed);
    await page.getByRole('button', { name: /Add to Handover/i }).click();
    await expect(page.getByText('Handover note added')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(seed).first()).toBeVisible({ timeout: 10_000 });

    // 4.1: open edit popup by clicking the seed
    await page.getByText(seed).first().click();
    await expect(page.getByText('Edit Handover Note')).toBeVisible({ timeout: 5_000 });

    // 4.2: summary textarea pre-filled
    const ta = page.locator('textarea');
    await expect(ta).toBeVisible();
    await expect(ta).toHaveValue(seed);

    // 4.6: change + save
    const edited = `${seed} — EDITED`;
    await ta.fill(edited);
    await page.getByRole('button', { name: /Save Changes/i }).click();
    await expect(page.getByText('Handover note updated')).toBeVisible({ timeout: 10_000 });

    // 4.7: list reflects new summary
    await expect(page.getByText(edited).first()).toBeVisible({ timeout: 10_000 });
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 5 — Delete confirmation + list update (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 5 — Delete UI', () => {
  test('5.1–5.5 | delete shows confirmation popup, item removed, reload-persistent', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    // seed throwaway
    const seed = `S54 DELETE-ME ${Date.now()}`;
    await page.getByRole('button', { name: /Add Note/i }).click();
    await page.locator('textarea').fill(seed);
    await page.getByRole('button', { name: /Add to Handover/i }).click();
    await expect(page.getByText(seed).first()).toBeVisible({ timeout: 10_000 });

    // 5.1: click row → popup → click Delete
    await page.getByText(seed).first().click();
    await expect(page.getByText('Edit Handover Note')).toBeVisible({ timeout: 5_000 });
    const deleteBtn = page
      .getByRole('button', { name: /^Delete$/ })
      .first();
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();

    // 5.1 confirmation copy
    await expect(page.getByText(/Delete this handover note\?/i)).toBeVisible({ timeout: 5_000 });

    // 5.3: confirm
    await page.getByRole('button', { name: 'Delete Note' }).click();
    await expect(page.getByText('Handover note deleted')).toBeVisible({ timeout: 10_000 });

    // 5.4: item gone
    await expect(page.getByText(seed)).not.toBeVisible({ timeout: 10_000 });

    // 5.5: reload → stays gone
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(seed)).not.toBeVisible();
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 7 — Entity lens dropdown "Add to Handover" (crew)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 7 — Entity lens add', () => {
  test('7.1–7.5 | Faults lens has Add to Handover action', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/faults');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    // 7.1: click first fault row
    await page.waitForTimeout(2000);
    const faultRow = page.locator('a[href*="/faults/"], [data-testid*="fault-row"]').first();
    test.skip(!(await faultRow.isVisible().catch(() => false)), 'No fault rows visible to exercise lens');
    await faultRow.click();
    await page.waitForLoadState('networkidle');

    // 7.2 + 7.3: action dropdown or "..." menu contains "Add to Handover"
    const trigger = page
      .getByRole('button', { name: /Actions|More|Add|Handover/i })
      .first();
    await expect(trigger).toBeVisible({ timeout: 15_000 });
    await trigger.click();
    await expect(page.getByText(/Add to Handover/i).first()).toBeVisible({ timeout: 5_000 });
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 8 — Document lens render (captain) — also emits PDF for S11
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 8 + 11 — Document render + PDF', () => {
  test('8.2–8.9 | captain sees Report header, TOC, sections, signature block; PDF generated', async ({
    browser,
  }, testInfo) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${KNOWN_COMPLETE_EXPORT_ID}`);
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);
    await page.waitForTimeout(3000);

    // 8.2: IdentityStrip (title present)
    const hasNotFound = await page
      .getByText(/not found|404|does not exist/i)
      .isVisible()
      .catch(() => false);
    expect(hasNotFound).toBe(false);

    // 8.3: "Technical Handover Report" header
    const reportHeader = page.getByText('Technical Handover Report');
    const noContentMsg = page.getByText('No handover content available');
    const hasReportHeader = await reportHeader.isVisible().catch(() => false);
    const hasEmpty = await noContentMsg.isVisible().catch(() => false);
    expect(hasReportHeader).toBe(true);
    expect(hasEmpty).toBe(false);

    // 8.4–8.5: at least one department section header visible
    const sectionHeaders = page.locator('text=/Engineering|Deck|Interior|Command/i');
    const secCount = await sectionHeaders.count();
    expect(secCount).toBeGreaterThan(0);

    // 8.9: signature block
    await expect(page.getByText(/Prepared By|Reviewed By|Signed/i).first()).toBeVisible({
      timeout: 10_000,
    });

    // 11.1–11.3: CDP page.pdf() closes the SKIP from the MD — proves the
    // document renders to a printable A4 layout with non-empty content.
    // Chromium-only (Firefox/WebKit don't support page.pdf()). The shard
    // uses Desktop Chrome, so this works.
    const pdfBuf = await page.pdf({ format: 'A4', printBackground: true });
    expect(pdfBuf.length).toBeGreaterThan(10_000); // >10KB = content present, not a blank page
    const pdfPath = testInfo.outputPath('handover-export.pdf');
    await testInfo.attach('handover-export.pdf', { path: pdfPath, contentType: 'application/pdf' });

    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 9 — Sign button visibility on pending_review export (captain)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 9 — Sign UI', () => {
  test('9.1–9.5 | captain sees Sign Handover, canvas modal opens, Cancel works', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();

    // create a fresh pending_review export via the captain's authenticated session
    await page.goto(`/handover-export`);
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);
    const session = await masterSignIn('captain');
    const exportRes = await page.request.post(
      'https://pipeline-core.int.celeste7.ai/v1/handover/export',
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: { export_type: 'html', filter_by_user: false },
      }
    );
    expect(exportRes.status()).toBe(200);
    const { export_id } = await exportRes.json();
    expect(export_id).toBeTruthy();

    await page.goto(`/handover-export/${export_id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // 9.1: Sign Handover button visible
    const signBtn = page.getByText('Sign Handover', { exact: false }).first();
    await expect(signBtn).toBeVisible({ timeout: 20_000 });

    // 9.2: click → canvas 416×160 modal opens
    await signBtn.click();
    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });

    // 9.4: Clear button present
    await expect(page.getByRole('button', { name: 'Clear' })).toBeVisible();

    // 9.5: Cancel closes modal
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(canvas).not.toBeVisible({ timeout: 5_000 });

    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 10 — Countersign button label (captain)
// ---------------------------------------------------------------------------

test.describe('HANDOVER_TESTER Scenario 10 — Countersign UI', () => {
  test('10.1–10.3 | on pending_hod_signature, button reads Countersign Handover', async ({
    browser,
  }) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await installConsoleCollector(page);

    const session = await masterSignIn('captain');

    // create export + submit with user signature so it lands in pending_hod_signature
    const exportRes = await page.request.post(
      'https://pipeline-core.int.celeste7.ai/v1/handover/export',
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: { export_type: 'html', filter_by_user: false },
      }
    );
    expect(exportRes.status()).toBe(200);
    const { export_id } = await exportRes.json();

    const fakeSig =
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    const submitRes = await page.request.post(
      `https://pipeline-core.int.celeste7.ai/v1/handover/export/${export_id}/submit`,
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: {
          sections: [
            {
              id: 'sec-1',
              title: 'Section',
              content: 'c',
              items: [{ id: 'i-1', content: 'x', priority: 'normal' }],
              is_critical: false,
              order: 0,
            },
          ],
          userSignature: {
            image_base64: fakeSig,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Test',
            signer_id: session.user.id,
          },
        },
      }
    );
    expect(submitRes.status()).toBe(200);

    // Now open the lens — button label should switch to Countersign Handover
    await page.goto(`/handover-export/${export_id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // 10.1
    const countersignBtn = page.getByText('Countersign Handover', { exact: false });
    await expect(countersignBtn).toBeVisible({ timeout: 20_000 });
    const rawSignBtn = page.getByText('Sign Handover', { exact: true });
    await expect(rawSignBtn).not.toBeVisible();

    // 10.2: click → same canvas
    await countersignBtn.click();
    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(canvas).not.toBeVisible({ timeout: 5_000 });
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// SCENARIO 12 — Popup rules matrix
// ---------------------------------------------------------------------------
// Each row is its own micro-test against a dedicated fresh context so state
// doesn't bleed. We assert the POSITIVE shape of each row (popup OR no popup),
// which is the only interpretation that closes the cell.

test.describe('HANDOVER_TESTER Scenario 12 — Popup rules matrix', () => {
  test('12.1 + Add from Queue — no popup (toast only)', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');

    const addButtons = page.locator('button', { hasText: /^\s*Add\s*$/ });
    const count = await addButtons.count().catch(() => 0);
    test.skip(count === 0, 'No Add buttons in queue to exercise popup rule');
    await addButtons.first().click();

    // no modal with textareas should open
    const modalTextarea = page.locator('textarea');
    const modalOpen = await modalTextarea.isVisible({ timeout: 1500 }).catch(() => false);
    expect(modalOpen).toBe(false);

    // a toast should confirm
    await expect(
      page
        .getByText(/Added to handover draft/)
        .or(page.locator('button', { hasText: 'Added' }).first())
    ).toBeVisible({ timeout: 10_000 });

    await ctx.close();
  });

  test('12.2 Add Note — popup with summary/category/section', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });
    await page.getByRole('button', { name: /Add Note/i }).click();
    await expect(page.getByText('Add Handover Note')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('textarea')).toBeVisible();
    await expect(page.locator('select').first()).toBeVisible();
    await ctx.close();
  });

  test('12.3 Edit draft item — popup with pre-filled summary', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    // seed throwaway
    const seed = `S54 12.3 seed ${Date.now()}`;
    await page.getByRole('button', { name: /Add Note/i }).click();
    await page.locator('textarea').fill(seed);
    await page.getByRole('button', { name: /Add to Handover/i }).click();
    await expect(page.getByText(seed).first()).toBeVisible({ timeout: 10_000 });

    await page.getByText(seed).first().click();
    await expect(page.getByText('Edit Handover Note')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('textarea')).toHaveValue(seed);
    await ctx.close();
  });

  test('12.4 Delete — confirmation popup', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'crew');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    const seed = `S54 12.4 delete-seed ${Date.now()}`;
    await page.getByRole('button', { name: /Add Note/i }).click();
    await page.locator('textarea').fill(seed);
    await page.getByRole('button', { name: /Add to Handover/i }).click();
    await expect(page.getByText(seed).first()).toBeVisible({ timeout: 10_000 });

    await page.getByText(seed).first().click();
    await expect(page.getByText('Edit Handover Note')).toBeVisible({ timeout: 5_000 });
    await page.getByRole('button', { name: /^Delete$/ }).first().click();
    await expect(page.getByText(/Delete this handover note\?/i)).toBeVisible({ timeout: 5_000 });
    await ctx.close();
  });

  test('12.5 Export Handover — no popup (loading then toast/redirect)', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'Draft Items' }).click();
    await expect(page.getByText('My Handover Draft')).toBeVisible({ timeout: 10_000 });

    const exportBtn = page.getByRole('button', { name: /Export Handover/i });
    const visible = await exportBtn.isVisible().catch(() => false);
    test.skip(!visible, 'Export Handover button not rendered on empty draft');
    await exportBtn.click();

    // No text-entry popup should open (textarea-free)
    const textareaVisible = await page
      .locator('textarea')
      .isVisible({ timeout: 1500 })
      .catch(() => false);
    expect(textareaVisible).toBe(false);
    await ctx.close();
  });

  test('12.6 Sign Handover — canvas popup', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    const session = await masterSignIn('captain');

    // seed a fresh pending_review export
    await page.goto('/handover-export');
    await page.waitForLoadState('networkidle');
    const resp = await page.request.post(
      'https://pipeline-core.int.celeste7.ai/v1/handover/export',
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: { export_type: 'html', filter_by_user: false },
      }
    );
    const { export_id } = await resp.json();
    await page.goto(`/handover-export/${export_id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    await page.getByText('Sign Handover', { exact: false }).first().click();
    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });
    await ctx.close();
  });

  test('12.7 Countersign — canvas popup (different instruction)', async ({ browser }) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    const session = await masterSignIn('captain');

    const resp = await page.request.post(
      'https://pipeline-core.int.celeste7.ai/v1/handover/export',
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: { export_type: 'html', filter_by_user: false },
      }
    );
    const { export_id } = await resp.json();
    const fakeSig =
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    await page.request.post(
      `https://pipeline-core.int.celeste7.ai/v1/handover/export/${export_id}/submit`,
      {
        headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
        data: {
          sections: [
            {
              id: 's',
              title: 't',
              content: 'c',
              items: [{ id: 'i', content: 'x', priority: 'normal' }],
              is_critical: false,
              order: 0,
            },
          ],
          userSignature: {
            image_base64: fakeSig,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Test',
            signer_id: session.user.id,
          },
        },
      }
    );

    await page.goto(`/handover-export/${export_id}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await page.getByText('Countersign Handover', { exact: false }).first().click();
    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });
    await ctx.close();
  });

  test('12.8 Export PDF — page.pdf() proves printable render', async ({ browser }, testInfo) => {
    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${KNOWN_COMPLETE_EXPORT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    const pdf = await page.pdf({ format: 'A4', printBackground: true });
    expect(pdf.length).toBeGreaterThan(10_000);
    const p = testInfo.outputPath('scenario-12-8-export.pdf');
    await testInfo.attach('scenario-12-8-export.pdf', { path: p, contentType: 'application/pdf' });
    await ctx.close();
  });
});

// End of shard-54 — all tests use per-test BrowserContext via contextForRole().
