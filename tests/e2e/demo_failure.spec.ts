/**
 * Demo Failure Test
 *
 * This test intentionally fails to demonstrate artifact capture on failure.
 * Skipped by default - run with: npx playwright test --project=demo-failure
 */

import { test, expect } from '@playwright/test';
import {
  saveScreenshot,
  saveArtifact,
  createEvidenceBundle,
} from '../helpers/artifacts';

test.describe('Demo Failure (skipped by default)', () => {
  // This test is skipped unless explicitly run with: npm run test:demo-failure
  test.skip();

  test('Intentional failure with artifact capture', async ({ page }) => {
    const testName = 'demo/intentional_failure';

    // Navigate to the app
    await page.goto('/');

    // Take screenshot before failure
    await saveScreenshot(page, testName, 'before_failure');

    // Save some mock data
    saveArtifact('request.json', {
      method: 'GET',
      url: page.url(),
      timestamp: new Date().toISOString(),
    }, testName);

    saveArtifact('response.json', {
      status: 200,
      body: { mock: 'This is mock data for demo' },
    }, testName);

    // Create evidence bundle
    createEvidenceBundle(testName, {
      request: { method: 'GET', url: page.url() },
      response: { status: 200, body: { mock: true } },
      assertions: [
        { name: 'This will pass', passed: true },
        { name: 'This will fail', passed: false, message: 'Intentional failure for demo' },
      ],
    });

    // Take screenshot at failure point
    await saveScreenshot(page, testName, 'at_failure');

    // This assertion intentionally fails
    expect(
      false,
      'This is an intentional failure to demonstrate artifact capture. ' +
      'Check test-results/artifacts/demo/intentional_failure/ for evidence files.'
    ).toBe(true);
  });

  test('Demo: What good evidence looks like', async ({ page }) => {
    const testName = 'demo/good_evidence';

    // This test passes but shows what complete evidence looks like

    await page.goto('/');
    await saveScreenshot(page, testName, 'page_loaded');

    // Simulate a full evidence capture
    saveArtifact('request.json', {
      timestamp: new Date().toISOString(),
      method: 'POST',
      url: 'https://pipeline-core.int.celeste7.ai/search',
      headers: { 'Authorization': 'Bearer xxx...', 'Content-Type': 'application/json' },
      body: { query: 'generator maintenance', limit: 5 },
    }, testName);

    saveArtifact('response.json', {
      timestamp: new Date().toISOString(),
      status: 200,
      body: {
        success: true,
        results: [
          { type: 'document', content: 'Generator maintenance procedure...' },
        ],
        total_count: 1,
      },
    }, testName);

    saveArtifact('db_before.json', {
      table: 'pms_work_orders',
      query: "SELECT * FROM pms_work_orders WHERE id = 'abc123'",
      result: { id: 'abc123', status: 'open', notes: null },
    }, testName);

    saveArtifact('db_after.json', {
      table: 'pms_work_orders',
      query: "SELECT * FROM pms_work_orders WHERE id = 'abc123'",
      result: { id: 'abc123', status: 'open', notes: 'Test note added' },
    }, testName);

    saveArtifact('audit_log.json', {
      table: 'audit_log',
      query: "SELECT * FROM audit_log WHERE entity_id = 'abc123' ORDER BY created_at DESC LIMIT 1",
      result: {
        id: 'xyz789',
        action: 'add_note',
        entity_type: 'work_order',
        entity_id: 'abc123',
        created_at: new Date().toISOString(),
      },
    }, testName);

    createEvidenceBundle(testName, {
      request: { method: 'POST', url: '/search' },
      response: { status: 200, body: { success: true } },
      dbBefore: { status: 'open', notes: null },
      dbAfter: { status: 'open', notes: 'Test note added' },
      auditLog: { action: 'add_note' },
      assertions: [
        { name: 'HTTP status 200', passed: true },
        { name: 'Success is true', passed: true },
        { name: 'Notes field updated', passed: true },
        { name: 'Audit log created', passed: true },
      ],
    });

    // This passes
    expect(true).toBe(true);

    console.log(`
    ===================================
    DEMO: Good Evidence Structure
    ===================================

    Check: test-results/artifacts/demo/good_evidence/

    Files created:
    - request.json    : Full HTTP request with headers
    - response.json   : Full HTTP response with body
    - db_before.json  : Database state before mutation
    - db_after.json   : Database state after mutation
    - audit_log.json  : Audit trail entry
    - evidence_bundle.json : Summary with all assertions

    This is the standard every test should meet.
    `);
  });
});
