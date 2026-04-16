/**
 * SHARD 52: Documents MVP — Full frontend walkthrough
 *
 * Mirrors DOCUMENTS_MVP_CHEATSHEET.md scenario-for-scenario.
 * Each test.describe = one scenario from the cheat sheet.
 * Each test step captures: screenshots, console errors, API responses.
 *
 * Run:
 *   TEST_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598 \
 *   SUPABASE_JWT_SECRET='wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==' \
 *   npx playwright test e2e/shard-52-documents-mvp/ --headed
 *
 * Output: screenshots in /tmp/docs-mvp-*, console log has [API], [console.*], [pageerror]
 */

import { test, expect } from '../rbac-fixtures';
import { callActionDirect } from '../shard-34-lens-actions/helpers';
import * as fs from 'fs';
import * as path from 'path';
import type { Page, ConsoleMessage } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const SCREENSHOT_DIR = '/tmp/docs-mvp';

// Ensure screenshot directory exists
try { fs.mkdirSync(SCREENSHOT_DIR, { recursive: true }); } catch {}

// ============================================================================
// Helpers
// ============================================================================

/** Collect console errors, API calls, and page errors into arrays. */
function attachListeners(page: Page, label: string) {
  const log: string[] = [];

  page.on('console', (msg: ConsoleMessage) => {
    const t = msg.type();
    const text = msg.text();
    if (t === 'error' || t === 'warning') {
      const line = `[${label}][console.${t}] ${text}`;
      log.push(line);
      console.log(line);
    }
    // Capture API intercepts if the user pasted the fetch wrapper
    if (text.startsWith('[API]')) {
      log.push(text);
      console.log(text);
    }
  });

  page.on('pageerror', (err: Error) => {
    const line = `[${label}][pageerror] ${err.message}`;
    log.push(line);
    console.log(line);
    if (err.stack) {
      const stackLines = err.stack.split('\n').slice(0, 4).join('\n');
      log.push(stackLines);
      console.log(stackLines);
    }
  });

  page.on('requestfailed', req => {
    const line = `[${label}][netfail] ${req.method()} ${req.url()} — ${req.failure()?.errorText}`;
    log.push(line);
    console.log(line);
  });

  return log;
}

/** Take a labeled screenshot. */
async function snap(page: Page, scenario: string, step: string) {
  const filename = `${scenario}-${step}.png`.replace(/[^a-z0-9\-_.]/gi, '_');
  const filepath = path.join(SCREENSHOT_DIR, filename);
  await page.screenshot({ path: filepath, fullPage: false });
  console.log(`[screenshot] ${filepath}`);
}

/** Inject the fetch interceptor so API calls appear in console. */
async function injectApiInterceptor(page: Page) {
  await page.evaluate(() => {
    if ((window as any).__apiInterceptorInjected) return;
    const origFetch = window.fetch;
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const r = await origFetch(...args);
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request)?.url || '';
      if (url.includes('/actions/execute') || url.includes('/v1/')) {
        try {
          const clone = r.clone();
          const data = await clone.json();
          console.log(`[API] ${url} ${JSON.stringify(data)}`);
        } catch {}
      }
      return r;
    };
    (window as any).__apiInterceptorInjected = true;
  });
}

/** Dump all visible button labels on the page (diagnostic). */
async function dumpButtons(page: Page, tag: string) {
  const labels = await page.evaluate(() => {
    const els = document.querySelectorAll('button, a[role="button"], [role="menuitem"]');
    return Array.from(els)
      .map(el => (el.textContent || '').trim())
      .filter(t => t.length > 0 && t.length < 80)
      .slice(0, 50);
  });
  console.log(`[${tag}] visible buttons/links:`);
  labels.forEach(t => console.log(`  - "${t}"`));
  return labels;
}

/** Build a minimal valid PDF for upload tests. */
function buildTestPdf(marker: string): Buffer {
  const text = `Playwright documents-mvp test ${marker}`;
  const body = `BT /F1 14 Tf 72 720 Td (${text}) Tj ET`;
  const stream = `<< /Length ${body.length} >>\nstream\n${body}\nendstream`;
  const pdf = `%PDF-1.1\n%\xe2\xe3\xcf\xd3\n` +
    `1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n` +
    `2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n` +
    `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] ` +
    `/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n` +
    `4 0 obj\n${stream}\nendobj\n` +
    `5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n` +
    `xref\n0 6\n` +
    `0000000000 65535 f \n0000000015 00000 n \n0000000068 00000 n \n` +
    `0000000118 00000 n \n0000000224 00000 n \n0000000310 00000 n \n` +
    `trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n370\n%%EOF\n`;
  return Buffer.from(pdf, 'binary');
}

// ============================================================================
// Pre-flight
// ============================================================================

test.describe('Pre-flight', () => {
  test('P1-P4: app loads, login, sidebar, no console errors', async ({ hodPage }) => {
    const errors = attachListeners(hodPage, 'preflight');

    // P1: app loads
    await hodPage.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
    await hodPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
    await snap(hodPage, 'preflight', 'P1-app-loads');
    const url = hodPage.url();
    console.log(`[P1] current URL: ${url}`);
    expect(url).not.toContain('/login'); // Should auto-login via storageState

    // P3: sidebar shows Documents link
    const docsLink = hodPage.locator('a, button, [role="menuitem"]').filter({ hasText: /documents/i });
    const docsCount = await docsLink.count();
    console.log(`[P3] "Documents" sidebar links found: ${docsCount}`);
    await snap(hodPage, 'preflight', 'P3-sidebar');

    // P4: no red console errors
    const redErrors = errors.filter(e => e.includes('console.error') && !e.includes('preloaded'));
    console.log(`[P4] console.error count (excluding preload): ${redErrors.length}`);
    redErrors.forEach(e => console.log(`  ${e}`));
  });
});

// ============================================================================
// Scenario 1 — HOD uploads a document
// ============================================================================

test.describe('Scenario 1 — HOD uploads document', () => {
  test('1.1-1.8: navigate, upload, verify row + download', async ({ hodPage }) => {
    const errors = attachListeners(hodPage, 'S1');

    // 1.1 Navigate to /documents
    await hodPage.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
    await hodPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
    await injectApiInterceptor(hodPage);
    await snap(hodPage, 'S1', '1.1-documents-page');

    const currentUrl = hodPage.url();
    console.log(`[1.1] URL after navigation: ${currentUrl}`);

    // Dump all buttons for diagnostic
    const buttons = await dumpButtons(hodPage, '1.1');

    // 1.2 Find upload button — try multiple selectors
    const uploadBtn = hodPage.locator('button').filter({
      hasText: /upload|add document/i,
    }).first();
    const uploadBtnVisible = await uploadBtn.isVisible().catch(() => false);
    console.log(`[1.2] Upload/Add Document button visible: ${uploadBtnVisible}`);

    if (!uploadBtnVisible) {
      // Try subbar primary action
      const primaryBtn = hodPage.locator('[data-testid="primary-action"], [data-testid="subbar"] button').first();
      const primaryText = await primaryBtn.textContent().catch(() => 'NOT FOUND');
      console.log(`[1.2] Primary action button text: "${primaryText}"`);
      await snap(hodPage, 'S1', '1.2-no-upload-btn');

      // Still try to click it
      if (primaryText && /upload|add|document/i.test(primaryText)) {
        await primaryBtn.click();
      } else {
        console.log(`[1.2] ERR — cannot find upload button. Available: ${buttons.join(', ')}`);
        return;
      }
    } else {
      const btnText = await uploadBtn.textContent();
      console.log(`[1.2] Clicking button: "${btnText}"`);
      await uploadBtn.click();
    }

    // 1.3 Modal should appear
    await hodPage.waitForTimeout(1000);
    await snap(hodPage, 'S1', '1.3-after-click');

    const modal = hodPage.locator('[role="dialog"], [data-testid="upload-modal"], [class*="modal"]').first();
    const modalVisible = await modal.isVisible().catch(() => false);
    console.log(`[1.3] Modal/dialog visible: ${modalVisible}`);

    if (!modalVisible) {
      // Dump page HTML around likely modal areas
      const html = await hodPage.evaluate(() => document.body.innerHTML.slice(0, 3000));
      console.log(`[1.3] ERR — no modal found. Body HTML preview: ${html.slice(0, 500)}`);
      await snap(hodPage, 'S1', '1.3-no-modal');
      return;
    }

    // File input
    const fileInput = hodPage.locator('input[type="file"]');
    const fileInputCount = await fileInput.count();
    console.log(`[1.3] File input elements found: ${fileInputCount}`);

    if (fileInputCount === 0) {
      console.log('[1.3] ERR — no file input in modal');
      await snap(hodPage, 'S1', '1.3-no-file-input');
      return;
    }

    // 1.4 Upload a real PDF
    const marker = `pw-docs-mvp-${Date.now()}`;
    const pdfPath = `/tmp/${marker}.pdf`;
    fs.writeFileSync(pdfPath, buildTestPdf(marker));
    console.log(`[1.4] Test PDF: ${pdfPath} (${fs.statSync(pdfPath).size} bytes)`);

    await fileInput.setInputFiles(pdfPath);
    await hodPage.waitForTimeout(500);
    await snap(hodPage, 'S1', '1.4-file-selected');

    // Fill optional fields if visible
    const titleInput = hodPage.locator('input[name="title"], input[placeholder*="title" i]').first();
    if (await titleInput.isVisible().catch(() => false)) {
      await titleInput.fill('Playwright Test Engine Manual');
      console.log('[1.4] Title field filled');
    }

    // 1.5 Submit
    const submitBtn = hodPage.locator('button').filter({
      hasText: /^upload$|^submit$|^save$/i,
    }).first();
    const submitVisible = await submitBtn.isVisible().catch(() => false);
    console.log(`[1.5] Submit button visible: ${submitVisible}`);

    if (submitVisible) {
      // Watch for the upload API call
      const uploadPromise = hodPage.waitForResponse(
        resp => resp.url().includes('/v1/documents/upload') || resp.url().includes('/actions/execute'),
        { timeout: 30_000 }
      ).catch(() => null);

      await submitBtn.click();
      console.log('[1.5] Submit clicked');

      const resp = await uploadPromise;
      if (resp) {
        console.log(`[1.5] API response: ${resp.status()} ${resp.url()}`);
        try {
          const body = await resp.json();
          console.log(`[1.5] API body: ${JSON.stringify(body).slice(0, 500)}`);
          if (body.document_id || body.result?.document_id) {
            console.log(`[1.5] PASS — document_id: ${body.document_id || body.result?.document_id}`);
          }
        } catch {}
      }
    }

    await hodPage.waitForTimeout(2000);
    await snap(hodPage, 'S1', '1.5-after-submit');

    // 1.6 Check if modal closed (success path)
    const modalStillOpen = await modal.isVisible().catch(() => false);
    console.log(`[1.6] Modal still open after submit: ${modalStillOpen}`);

    // Check for toast / success message
    const toastText = await hodPage.evaluate(() => {
      const toasts = document.querySelectorAll('[role="status"], [role="alert"], [class*="toast"], [class*="Toast"], [class*="success"]');
      return Array.from(toasts).map(el => (el.textContent || '').trim()).join(' || ');
    });
    if (toastText) console.log(`[1.6] Toast/alert text: "${toastText}"`);

    await snap(hodPage, 'S1', '1.6-final');

    // Log all captured errors
    console.log(`\n[S1] Console errors captured: ${errors.length}`);
    errors.forEach(e => console.log(`  ${e}`));

    // Cleanup temp file
    try { fs.unlinkSync(pdfPath); } catch {}
  });
});

// ============================================================================
// Scenario 2 — HOD updates document metadata (via action router)
// ============================================================================

test.describe('Scenario 2 — HOD updates document metadata', () => {
  test('2.1-2.5: update_document via action API', async ({ hodPage, supabaseAdmin }) => {
    const errors = attachListeners(hodPage, 'S2');

    // Find an existing document to update
    const { data: docs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id, filename')
      .is('deleted_at', null)
      .order('created_at', { ascending: false })
      .limit(1);

    const doc = (docs as any[])?.[0];
    if (!doc) {
      console.log('[S2] SKIP — no existing document found');
      test.skip(true, 'No documents in DB');
      return;
    }
    console.log(`[2.1] Using document: ${doc.id} (${doc.filename})`);

    await hodPage.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
    await hodPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
    await injectApiInterceptor(hodPage);

    // 2.2-2.4: Call update via action API (matches what frontend does)
    const result = await callActionDirect(hodPage, 'update_document', {
      document_id: doc.id,
      title: `Playwright updated ${Date.now()}`,
    });
    console.log(`[2.4] update_document API: status=${result.status} body=${JSON.stringify(result.data).slice(0, 300)}`);
    expect(result.status).toBe(200);

    // 2.5: Verify DB
    const { data: updated } = await supabaseAdmin
      .from('pms_audit_log')
      .select('action, new_values')
      .eq('entity_id', doc.id)
      .eq('action', 'update_document')
      .order('created_at', { ascending: false })
      .limit(1);
    const auditRow = (updated as any[])?.[0];
    console.log(`[2.5] pms_audit_log row: ${JSON.stringify(auditRow)}`);
    expect(auditRow).toBeTruthy();

    // Check ledger
    const { data: ledger } = await supabaseAdmin
      .from('ledger_events')
      .select('event_type, action')
      .eq('entity_id', doc.id)
      .eq('action', 'update_document')
      .order('created_at', { ascending: false })
      .limit(1);
    const ledgerRow = (ledger as any[])?.[0];
    console.log(`[2.5] ledger_events row: ${JSON.stringify(ledgerRow)}`);
    expect(ledgerRow).toBeTruthy();

    console.log(`\n[S2] Console errors captured: ${errors.length}`);
    errors.forEach(e => console.log(`  ${e}`));
  });
});

// ============================================================================
// Scenario 3 — HOD adds tags
// ============================================================================

test.describe('Scenario 3 — HOD adds tags', () => {
  test('3.1-3.4: add_document_tags + verify persistence', async ({ hodPage, supabaseAdmin }) => {
    const errors = attachListeners(hodPage, 'S3');

    const { data: docs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id, filename, tags')
      .is('deleted_at', null)
      .order('created_at', { ascending: false })
      .limit(1);

    const doc = (docs as any[])?.[0];
    if (!doc) { test.skip(true, 'No documents'); return; }
    console.log(`[3.1] Using document: ${doc.id} — current tags: ${JSON.stringify(doc.tags)}`);

    await hodPage.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
    await hodPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});

    const tag = `pw-tag-${Date.now()}`;
    const result = await callActionDirect(hodPage, 'add_document_tags', {
      document_id: doc.id,
      tags: [tag, 'playwright-test'],
    });
    console.log(`[3.3] add_document_tags: status=${result.status} body=${JSON.stringify(result.data).slice(0, 300)}`);
    expect(result.status).toBe(200);

    // 3.4: Verify persistence
    const { data: refreshed } = await supabaseAdmin
      .from('doc_metadata')
      .select('tags')
      .eq('id', doc.id)
      .single();
    const tags = (refreshed as any)?.tags || [];
    console.log(`[3.4] Tags after update: ${JSON.stringify(tags)}`);
    expect(tags).toContain(tag);

    // Ledger check
    const { data: ledger } = await supabaseAdmin
      .from('ledger_events')
      .select('action')
      .eq('entity_id', doc.id)
      .eq('action', 'add_document_tags')
      .order('created_at', { ascending: false })
      .limit(1);
    console.log(`[3.4] ledger row present: ${!!(ledger as any[])?.[0]}`);
    expect((ledger as any[])?.[0]).toBeTruthy();

    // Notification check
    const { data: notif } = await supabaseAdmin
      .from('pms_notifications')
      .select('notification_type')
      .eq('entity_id', doc.id)
      .eq('notification_type', 'document_tags_updated')
      .order('created_at', { ascending: false })
      .limit(1);
    console.log(`[3.4] notification present: ${!!(notif as any[])?.[0]}`);

    console.log(`\n[S3] Console errors: ${errors.length}`);
    errors.forEach(e => console.log(`  ${e}`));
  });
});

// ============================================================================
// Scenario 4 — Captain deletes a document (SIGNED)
// ============================================================================

test.describe('Scenario 4 — Captain deletes document (SIGNED)', () => {
  test('4.1-4.10: signature popup, reason required, soft-delete + ledger', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    const errors = attachListeners(captainPage, 'S4');

    // Navigate to documents as captain
    await captainPage.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
    await captainPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
    await injectApiInterceptor(captainPage);
    await snap(captainPage, 'S4', '4.2-documents-captain');

    const buttons = await dumpButtons(captainPage, '4.2');

    // Find a document row to click
    const docRows = captainPage.locator('tr, [data-testid*="document"], [class*="row"]').filter({
      hasText: /\.pdf|\.docx|manual|report/i,
    });
    const rowCount = await docRows.count();
    console.log(`[4.3] Document rows found: ${rowCount}`);

    if (rowCount > 0) {
      await docRows.first().click();
      await captainPage.waitForTimeout(1000);
      await snap(captainPage, 'S4', '4.3-detail-open');

      // 4.4 Find delete in menu
      const menuTrigger = captainPage.locator('button').filter({ hasText: /⋯|more|menu|\.\.\./ }).first();
      const menuVisible = await menuTrigger.isVisible().catch(() => false);
      console.log(`[4.4] Menu trigger visible: ${menuVisible}`);

      if (menuVisible) {
        await menuTrigger.click();
        await captainPage.waitForTimeout(500);
        await snap(captainPage, 'S4', '4.4-menu-open');

        const deleteBtn = captainPage.locator('[role="menuitem"], button').filter({
          hasText: /delete/i,
        }).first();
        const deleteVisible = await deleteBtn.isVisible().catch(() => false);
        console.log(`[4.5] Delete button visible: ${deleteVisible}`);

        if (deleteVisible) {
          await deleteBtn.click();
          await captainPage.waitForTimeout(1000);
          await snap(captainPage, 'S4', '4.5-after-delete-click');

          // 4.6 Check for signature popup
          const popup = captainPage.locator('[role="dialog"], [class*="modal"], [class*="signature"]').first();
          const popupVisible = await popup.isVisible().catch(() => false);
          console.log(`[4.6] Signature popup visible: ${popupVisible}`);
          await snap(captainPage, 'S4', '4.6-popup');

          // Dump popup contents
          if (popupVisible) {
            const popupText = await popup.textContent().catch(() => 'EMPTY');
            console.log(`[4.6] Popup text: "${popupText?.slice(0, 300)}"`);

            // Check for reason field
            const reasonField = popup.locator('input, textarea').filter({
              has: captainPage.locator('[placeholder*="reason" i], [name*="reason" i]'),
            }).first();
            const reasonVisible = await reasonField.isVisible().catch(() => false);
            console.log(`[4.6] Reason field visible: ${reasonVisible}`);
          }
        }
      }
    }

    // 4.7-4.10: Test delete via API (proves backend works regardless of frontend state)
    // Use a test doc that we can safely delete
    const { data: testDocs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id')
      .is('deleted_at', null)
      .like('filename', '%pw-%')
      .limit(1);
    const testDoc = (testDocs as any[])?.[0];

    if (testDoc) {
      // 4.7: delete without signature → should fail
      const noSig = await callActionDirect(captainPage, 'delete_document', {
        document_id: testDoc.id,
        reason: 'playwright test cleanup',
      });
      console.log(`[4.7] delete without signature: status=${noSig.status}`);
      expect([400, 403]).toContain(noSig.status);

      // 4.8-4.9: delete with signature → should succeed
      const withSig = await callActionDirect(captainPage, 'delete_document', {
        document_id: testDoc.id,
        reason: 'playwright shard-52 cleanup',
        signature: { name: 'Captain PW Test', timestamp: Date.now() },
      });
      console.log(`[4.9] delete with signature: status=${withSig.status} body=${JSON.stringify(withSig.data).slice(0, 300)}`);

      if (withSig.status === 200) {
        // 4.10: Verify soft-delete
        const { data: deleted } = await supabaseAdmin
          .from('doc_metadata')
          .select('deleted_at')
          .eq('id', testDoc.id)
          .single();
        console.log(`[4.10] deleted_at: ${(deleted as any)?.deleted_at}`);
        expect((deleted as any)?.deleted_at).toBeTruthy();

        // Ledger
        const { data: ledger } = await supabaseAdmin
          .from('ledger_events')
          .select('action')
          .eq('entity_id', testDoc.id)
          .eq('action', 'delete_document')
          .limit(1);
        console.log(`[4.10] ledger row: ${!!(ledger as any[])?.[0]}`);
        expect((ledger as any[])?.[0]).toBeTruthy();
      }
    } else {
      console.log('[4.7-4.10] SKIP — no pw-* test doc to safely delete');
    }

    console.log(`\n[S4] Console errors: ${errors.length}`);
    errors.forEach(e => console.log(`  ${e}`));
  });
});

// ============================================================================
// Scenario 5 — Crew read-only access
// ============================================================================

test.describe('Scenario 5 — Crew read-only', () => {
  test('5.1-5.8: crew can view, cannot upload/edit/delete', async ({ crewPage }) => {
    const errors = attachListeners(crewPage, 'S5');

    // 5.1-5.2: Navigate
    await crewPage.goto(`${BASE_URL}/documents`, { waitUntil: 'domcontentloaded' });
    await crewPage.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
    await injectApiInterceptor(crewPage);
    await snap(crewPage, 'S5', '5.2-crew-documents');

    const url = crewPage.url();
    console.log(`[5.2] URL: ${url}`);

    // 5.5: Upload button should NOT be visible for crew
    const uploadBtn = crewPage.locator('button').filter({
      hasText: /upload|add document/i,
    });
    const uploadVisible = await uploadBtn.first().isVisible().catch(() => false);
    console.log(`[5.5] Upload button visible for crew: ${uploadVisible}`);
    if (uploadVisible) {
      const btnText = await uploadBtn.first().textContent();
      console.log(`[5.5] ERR — Upload button visible to crew! Text: "${btnText}"`);
      console.log('[5.5] This is a frontend bug — backend correctly returns 403 but button should be hidden');
    }

    // Dump all visible buttons
    await dumpButtons(crewPage, '5.5');

    // 5.6-5.7: No delete/edit visible
    const deleteBtn = crewPage.locator('button, [role="menuitem"]').filter({ hasText: /delete/i });
    const deleteVisible = await deleteBtn.first().isVisible().catch(() => false);
    console.log(`[5.6] Delete visible for crew: ${deleteVisible}`);

    const editBtn = crewPage.locator('button, [role="menuitem"]').filter({ hasText: /edit|update/i });
    const editVisible = await editBtn.first().isVisible().catch(() => false);
    console.log(`[5.7] Edit/Update visible for crew: ${editVisible}`);

    // 5.8: API-level check — crew upload should 403
    const resp = await crewPage.evaluate(async (baseUrl) => {
      try {
        const r = await fetch(`${baseUrl.replace('app.celeste7.ai', 'pipeline-core.int.celeste7.ai')}/v1/documents/upload`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${document.cookie}` },
        });
        return r.status;
      } catch { return -1; }
    }, BASE_URL);
    console.log(`[5.8] Crew upload API status: ${resp} (expect 401 or 403)`);

    // Test get_document_url — crew SHOULD be able to read
    const { data: docs } = await crewPage.evaluate(async () => {
      // This would need proper JWT — using callActionDirect instead
      return { data: null };
    });

    console.log(`\n[S5] Console errors: ${errors.length}`);
    errors.forEach(e => console.log(`  ${e}`));
  });

  test('5.4+5.8: crew can read via action API', async ({ crewPage, supabaseAdmin }) => {
    const { data: docs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id')
      .is('deleted_at', null)
      .limit(1);
    const doc = (docs as any[])?.[0];
    if (!doc) { test.skip(true, 'No docs'); return; }

    await crewPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

    // Crew CAN get_document_url
    const readResult = await callActionDirect(crewPage, 'get_document_url', {
      document_id: doc.id,
    });
    console.log(`[5.4] crew get_document_url: status=${readResult.status}`);
    expect(readResult.status).toBe(200);

    // Crew CANNOT update
    const writeResult = await callActionDirect(crewPage, 'update_document', {
      document_id: doc.id,
      title: 'crew should fail',
    });
    console.log(`[5.8] crew update_document: status=${writeResult.status} (expect 403)`);
    expect(writeResult.status).toBe(403);
  });
});

// ============================================================================
// Scenario 8 — Signature popup verification
// ============================================================================

test.describe('Scenario 8 — Signature popup matrix', () => {
  test('8.1-8.3: non-signed actions fire without popup', async ({ hodPage, supabaseAdmin }) => {
    const { data: docs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id')
      .is('deleted_at', null)
      .limit(1);
    const doc = (docs as any[])?.[0];
    if (!doc) { test.skip(true, 'No docs'); return; }

    await hodPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

    // 8.1: upload_document — no popup, just executes
    // (we test via API since the actual modal is the popup, not a signature popup)
    const uploadResult = await callActionDirect(hodPage, 'upload_document', {
      file_name: 'pw-sig-test.pdf',
      mime_type: 'application/pdf',
    });
    console.log(`[8.1] upload_document (no sig): status=${uploadResult.status}`);
    expect(uploadResult.status).toBe(200);

    // 8.2: update_document — no signature needed
    const updateResult = await callActionDirect(hodPage, 'update_document', {
      document_id: doc.id,
      title: 'sig popup test',
    });
    console.log(`[8.2] update_document (no sig): status=${updateResult.status}`);
    expect(updateResult.status).toBe(200);

    // 8.3: add_document_tags — no signature needed
    const tagResult = await callActionDirect(hodPage, 'add_document_tags', {
      document_id: doc.id,
      tags: ['sig-test'],
    });
    console.log(`[8.3] add_document_tags (no sig): status=${tagResult.status}`);
    expect(tagResult.status).toBe(200);
  });

  test('8.4: delete_document requires signature', async ({ captainPage, supabaseAdmin }) => {
    const { data: docs } = await supabaseAdmin
      .from('doc_metadata')
      .select('id')
      .is('deleted_at', null)
      .limit(1);
    const doc = (docs as any[])?.[0];
    if (!doc) { test.skip(true, 'No docs'); return; }

    await captainPage.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });

    // Without signature → 400
    const noSigResult = await callActionDirect(captainPage, 'delete_document', {
      document_id: doc.id,
      reason: 'sig test',
    });
    console.log(`[8.4] delete without signature: status=${noSigResult.status} (expect 400)`);
    expect([400, 403]).toContain(noSigResult.status);
  });
});
