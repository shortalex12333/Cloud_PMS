---
wave: 3
depends_on: [FE-01-01, FE-01-02, FE-01-03, FE-01-04, FE-01-05]
files_modified: []
autonomous: true
requirements: [WO-04, WO-05]
---

# Plan FE-01-06: Work Order E2E Tests + Verification

## Objective

Run comprehensive E2E tests for Work Order lens: crew user journey, HOD user journey, ledger verification, screenshot evidence.

## Tasks

<task id="1">
Create Playwright test file `apps/web/e2e/work-order-lens.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { login } from './helpers/auth';

test.describe('Work Order Lens', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'crew');
  });

  test('displays header with no UUID visible', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="search-input"]', 'generator');
    await page.click('[data-testid="search-result-work-order"]');

    // Verify lens opened
    await expect(page.locator('[data-testid="lens-header"]')).toBeVisible();

    // Verify no UUID in title
    const title = await page.locator('[data-testid="lens-title"]').textContent();
    expect(title).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/i);

    // Screenshot
    await page.screenshot({ path: 'evidence/wo-lens-header.png' });
  });

  test('vital signs row shows 5 indicators', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="search-input"]', 'generator');
    await page.click('[data-testid="search-result-work-order"]');

    const vitalSigns = page.locator('[data-testid="vital-signs-row"] > *');
    await expect(vitalSigns).toHaveCount(5);
  });

  test('sections have sticky headers', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="search-input"]', 'generator');
    await page.click('[data-testid="search-result-work-order"]');

    // Scroll to trigger sticky
    await page.evaluate(() => window.scrollTo(0, 500));

    const notesHeader = page.locator('[data-testid="section-notes-header"]');
    await expect(notesHeader).toHaveCSS('position', 'sticky');
  });
});
```
</task>

<task id="2">
Create crew user journey test:

```typescript
test('crew can add note to work order', async ({ page }) => {
  await login(page, 'crew');
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'generator');
  await page.click('[data-testid="search-result-work-order"]');

  // Add note
  await page.click('[data-testid="add-note-button"]');
  await page.fill('[data-testid="note-input"]', 'Test note from E2E');
  await page.click('[data-testid="submit-note"]');

  // Verify note appears
  await expect(page.locator('text=Test note from E2E')).toBeVisible();

  // Screenshot evidence
  await page.screenshot({ path: 'evidence/wo-crew-add-note.png' });
});
```
</task>

<task id="3">
Create HOD user journey test with signature:

```typescript
test('HOD can mark work order complete with signature', async ({ page }) => {
  await login(page, 'chief_engineer');
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'generator');
  await page.click('[data-testid="search-result-work-order"]');

  // Mark complete (requires signature)
  await page.click('[data-testid="mark-complete-button"]');

  // Signature prompt appears
  await expect(page.locator('[data-testid="signature-prompt"]')).toBeVisible();

  // Draw signature (simulate)
  const canvas = page.locator('[data-testid="signature-canvas"]');
  await canvas.click({ position: { x: 50, y: 50 } });
  await canvas.click({ position: { x: 150, y: 50 } });

  // Confirm
  await page.click('[data-testid="confirm-signature"]');

  // Verify status changed
  await expect(page.locator('[data-testid="status-pill"]')).toContainText('Complete');

  await page.screenshot({ path: 'evidence/wo-hod-complete.png' });
});
```
</task>

<task id="4">
Create ledger verification test:

```typescript
test('actions create ledger entries', async ({ page, request }) => {
  await login(page, 'crew');
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'generator');
  await page.click('[data-testid="search-result-work-order"]');

  // Get work order ID from URL or data attribute
  const workOrderId = await page.locator('[data-entity-id]').getAttribute('data-entity-id');

  // Add note
  await page.click('[data-testid="add-note-button"]');
  await page.fill('[data-testid="note-input"]', 'Ledger test note');
  await page.click('[data-testid="submit-note"]');

  // Wait for API
  await page.waitForResponse(resp => resp.url().includes('/action') && resp.status() === 200);

  // Verify ledger via API
  const response = await request.get(`/api/ledger?entity_id=${workOrderId}&action=add_note`);
  const ledger = await response.json();

  expect(ledger.entries.length).toBeGreaterThan(0);
  expect(ledger.entries[0].payload.content).toBe('Ledger test note');
});
```
</task>

<task id="5">
Run all tests and capture evidence:

```bash
cd apps/web && npx playwright test e2e/work-order-lens.spec.ts --reporter=html

# Copy screenshots to evidence folder
mkdir -p evidence/work-order
cp test-results/**/*.png evidence/work-order/
```
</task>

<task id="6">
Verify ledger entries in database:

```sql
SELECT action, actor_id, entity_type, entity_id, created_at, payload
FROM pms_audit_log
WHERE entity_type = 'work_order'
ORDER BY created_at DESC
LIMIT 10;
```

All test actions should appear with correct payload.
</task>

## Verification

```bash
# All E2E tests pass
cd apps/web && npx playwright test e2e/work-order-lens.spec.ts

# Evidence screenshots exist
ls evidence/work-order/

# Ledger entries exist (via Supabase query)
```

## must_haves

- [ ] E2E test file created
- [ ] Crew add note test passes
- [ ] HOD mark complete with signature test passes
- [ ] Ledger entries verified in DB
- [ ] Screenshot evidence captured
- [ ] All tests pass without flakiness
