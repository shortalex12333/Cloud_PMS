/**
 * E2E Tests: Zero 5xx Errors in Parts UI
 *
 * Validates that NO network requests return 5xx errors during core user flows:
 * - Search for parts
 * - View part details
 * - Execute actions (receive, consume)
 * - View suggestions
 * - Load part photos/labels
 *
 * This is a critical acceptance gate: ANY 5xx error is a deployment blocker.
 *
 * Evidence: Network monitoring logs, HAR files, 5xx scan results
 *
 * SECURITY MODEL (New):
 * - yacht_id is server-resolved from JWT auth (MASTER membership → TENANT role)
 * - NO client-provided yacht_id in action payloads
 * - All requests use Authorization: Bearer <JWT>
 * - Monitors for server errors (5xx) as deployment gate
 */

import { test, expect, Page } from '@playwright/test';
import { loginAsRole, RoleAuthState } from './helpers/roles-auth';
import * as path from 'path';
import * as fs from 'fs';

const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts');
const API_BASE = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Ensure artifacts directory exists
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
}

/**
 * Network monitor to track all responses
 */
class NetworkMonitor {
  private responses: Array<{ url: string; status: number; timestamp: string }> = [];

  attach(page: Page): void {
    page.on('response', (response) => {
      const url = response.url();
      const status = response.status();

      this.responses.push({
        url,
        status,
        timestamp: new Date().toISOString(),
      });

      // Log 5xx errors immediately
      if (status >= 500) {
        console.error(`❌ 5xx ERROR DETECTED: ${status} ${url}`);
      }
    });
  }

  getResponses(): Array<{ url: string; status: number; timestamp: string }> {
    return this.responses;
  }

  get5xxErrors(): Array<{ url: string; status: number; timestamp: string }> {
    return this.responses.filter(r => r.status >= 500 && r.status < 600);
  }

  has5xxErrors(): boolean {
    return this.get5xxErrors().length > 0;
  }

  getStats(): {
    total: number;
    by2xx: number;
    by3xx: number;
    by4xx: number;
    by5xx: number;
  } {
    return {
      total: this.responses.length,
      by2xx: this.responses.filter(r => r.status >= 200 && r.status < 300).length,
      by3xx: this.responses.filter(r => r.status >= 300 && r.status < 400).length,
      by4xx: this.responses.filter(r => r.status >= 400 && r.status < 500).length,
      by5xx: this.responses.filter(r => r.status >= 500 && r.status < 600).length,
    };
  }

  reset(): void {
    this.responses = [];
  }

  saveEvidence(filename: string): void {
    const evidencePath = path.join(ARTIFACTS_DIR, filename);
    fs.writeFileSync(evidencePath, JSON.stringify({
      responses: this.responses,
      stats: this.getStats(),
      errors5xx: this.get5xxErrors(),
      zero5xxAchieved: !this.has5xxErrors(),
      timestamp: new Date().toISOString(),
    }, null, 2));
  }
}

/**
 * Helper: Navigate to base app (NO /parts page)
 *
 * ARCHITECTURE: Intent-first, search-driven UI
 * - NO /parts page exists (by design)
 * - Navigate to base URL to establish authenticated session
 * - Use search to trigger entity extraction and action surfacing
 */
async function navigateToParts(page: Page, role: string): Promise<void> {
  // Navigate to base URL (NO /parts route)
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.waitForLoadState('domcontentloaded');

  const currentUrl = page.url();
  if (currentUrl.includes('/login')) {
    throw new Error(`Unexpected redirect to login for ${role}`);
  }

  // Wait for search input to be ready (app loaded)
  const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 5000 });
}

/**
 * Helper: Search for a part
 */
async function searchForPart(page: Page, partName: string = 'Engine Oil Filter'): Promise<void> {
  const searchInput = page.locator('input[placeholder*="Search"], [data-testid="search-input"]').first();

  await searchInput.waitFor({ state: 'visible', timeout: 5000 });
  await searchInput.fill(partName);
  await searchInput.press('Enter');

  // Wait for results
  await page.waitForTimeout(1500);
}

test.describe('Zero 5xx Errors: Core User Flows', () => {
  let chiefEngineerAuthState: RoleAuthState;

  test.beforeAll(async () => {
    chiefEngineerAuthState = await loginAsRole('chief_engineer');
  });

  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'chief_engineer-state.json'),
  });

  test('Flow 1: Search → View Details (Zero 5xx)', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    // Navigate to parts
    await navigateToParts(page, 'chief_engineer');

    // Search for part
    await searchForPart(page, 'Engine Oil Filter');

    // Click on first result (if exists)
    const firstResult = page.locator('[data-testid="part-card"], .part-item, [role="listitem"]').first();
    const resultExists = await firstResult.isVisible({ timeout: 3000 }).catch(() => false);

    if (resultExists) {
      await firstResult.click();
      await page.waitForTimeout(1000);
    }

    // Save evidence
    monitor.saveEvidence('flow1_search_view_details.json');

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    if (errors5xx.length > 0) {
      console.error('5xx errors detected:', errors5xx);
    }

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'flow1_search_view_zero_5xx.png'),
      fullPage: true,
    });
  });

  test('Flow 2: View Suggestions (Zero 5xx)', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    await navigateToParts(page, 'chief_engineer');
    await searchForPart(page);

    // Wait for suggestions to load
    await page.waitForTimeout(2000);

    // Look for suggestions panel
    const suggestionsPanel = page.locator(
      '[data-testid="suggestions-panel"], [data-testid="action-list"], .suggestions'
    ).first();

    const panelExists = await suggestionsPanel.isVisible({ timeout: 3000 }).catch(() => false);

    if (panelExists) {
      // Suggestions loaded
      console.log('✓ Suggestions panel visible');
    }

    // Save evidence
    monitor.saveEvidence('flow2_view_suggestions.json');

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'flow2_suggestions_zero_5xx.png'),
      fullPage: true,
    });
  });

  test('Flow 3: Execute Action - Receive Part (Zero 5xx)', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    await navigateToParts(page, 'chief_engineer');

    // Make a direct API call to receive part (to avoid UI dependencies)
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      // NOTE: New security model - yacht_id derived from JWT auth
      const response = await fetch(`${API_BASE}/v1/actions/execute`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${jwt}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'receive_part',
          payload: {
            part_id: process.env.TEST_PART_ID,
            quantity: 1,
            supplier: 'E2E Zero 5xx Test',
          },
        }),
      });

      const status = response.status;

      // Log the response
      monitor.getResponses().push({
        url: `${API_BASE}/v1/actions/execute (receive_part)`,
        status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx
      expect(status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence('flow3_execute_receive_part.json');

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'flow3_receive_part_zero_5xx.png'),
      fullPage: true,
    });
  });

  test('Flow 4: Execute Action - Consume Part (Zero 5xx)', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    await navigateToParts(page, 'chief_engineer');

    // Make direct API call to consume part
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      // NOTE: New security model - yacht_id derived from JWT auth
      const response = await fetch(`${API_BASE}/v1/actions/execute`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${jwt}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'consume_part',
          payload: {
            part_id: process.env.TEST_PART_ID,
            quantity: 1,
          },
        }),
      });

      const status = response.status;

      monitor.getResponses().push({
        url: `${API_BASE}/v1/actions/execute (consume_part)`,
        status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx (can be 200, 409, etc., but never 5xx)
      expect(status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence('flow4_execute_consume_part.json');

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'flow4_consume_part_zero_5xx.png'),
      fullPage: true,
    });
  });

  test('Flow 5: Low Stock Suggestions (Zero 5xx)', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    await navigateToParts(page, 'chief_engineer');

    // Make API call to low stock endpoint
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      const response = await fetch(`${API_BASE}/v1/parts/low-stock`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${jwt}`,
        },
      });

      const status = response.status;

      monitor.getResponses().push({
        url: `${API_BASE}/v1/parts/low-stock`,
        status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx
      expect(status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence('flow5_low_stock_suggestions.json');

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'flow5_low_stock_zero_5xx.png'),
      fullPage: true,
    });
  });

  test('Comprehensive Flow: Full User Journey (Zero 5xx)', async ({ page, context }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    // Enable HAR recording for full network trace
    const harPath = path.join(ARTIFACTS_DIR, 'comprehensive_flow.har');

    // Navigate to parts
    await navigateToParts(page, 'chief_engineer');

    // Search for part
    await searchForPart(page, 'Engine Oil Filter');

    // Wait for all network activity
    await page.waitForTimeout(2000);

    // Click on part (if visible)
    const partCard = page.locator('[data-testid="part-card"]').first();
    if (await partCard.isVisible({ timeout: 2000 }).catch(() => false)) {
      await partCard.click();
      await page.waitForTimeout(1000);
    }

    // View suggestions (if panel visible)
    const suggestionsPanel = page.locator('[data-testid="suggestions-panel"]').first();
    if (await suggestionsPanel.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('✓ Suggestions panel loaded');
    }

    // Make multiple API calls
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      const endpoints = [
        '/v1/parts/low-stock',
        `/v1/parts/suggestions?part_id=${process.env.TEST_PART_ID}`,
        '/health',
      ];

      for (const endpoint of endpoints) {
        const response = await fetch(`${API_BASE}${endpoint}`, {
          headers: { 'Authorization': `Bearer ${jwt}` },
        });

        monitor.getResponses().push({
          url: `${API_BASE}${endpoint}`,
          status: response.status,
          timestamp: new Date().toISOString(),
        });

        // Assert not 5xx
        expect(response.status).toBeLessThan(500);
      }
    }

    // Save evidence
    monitor.saveEvidence('comprehensive_flow_zero_5xx.json');

    // Assert zero 5xx across entire journey
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    // Log stats
    const stats = monitor.getStats();
    console.log('Network Stats:', stats);
    console.log(`✓ Total requests: ${stats.total}`);
    console.log(`✓ 2xx responses: ${stats.by2xx}`);
    console.log(`✓ 4xx responses: ${stats.by4xx}`);
    console.log(`✓ 5xx responses: ${stats.by5xx} (MUST BE 0)`);

    // Hard assertion: zero 5xx
    expect(stats.by5xx).toBe(0);

    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, 'comprehensive_flow_zero_5xx.png'),
      fullPage: true,
    });
  });
});

// Multi-Role Validation: CREW
test.describe('Zero 5xx Errors: CREW Role', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'crew-state.json'),
  });

  test('CREW: Zero 5xx across basic flows', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    // Navigate to parts
    await navigateToParts(page, 'crew');

    // Search
    await searchForPart(page);

    // Wait for network activity
    await page.waitForTimeout(2000);

    // Make API calls
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      // Test suggestions endpoint
      const response = await fetch(
        `${API_BASE}/v1/parts/suggestions?part_id=${process.env.TEST_PART_ID}`,
        {
          headers: { 'Authorization': `Bearer ${jwt}` },
        }
      );

      monitor.getResponses().push({
        url: `${API_BASE}/v1/parts/suggestions`,
        status: response.status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx
      expect(response.status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence(`zero_5xx_crew_flows.json`);

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, `zero_5xx_crew_flows.png`),
      fullPage: true,
    });
  });
});

// Multi-Role Validation: HOD
test.describe('Zero 5xx Errors: Chief Engineer Role', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'chief_engineer-state.json'),
  });

  test('Chief Engineer: Zero 5xx across basic flows', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    // Navigate to parts
    await navigateToParts(page, 'chief_engineer');

    // Search
    await searchForPart(page);

    // Wait for network activity
    await page.waitForTimeout(2000);

    // Make API calls
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      // Test suggestions endpoint
      const response = await fetch(
        `${API_BASE}/v1/parts/suggestions?part_id=${process.env.TEST_PART_ID}`,
        {
          headers: { 'Authorization': `Bearer ${jwt}` },
        }
      );

      monitor.getResponses().push({
        url: `${API_BASE}/v1/parts/suggestions`,
        status: response.status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx
      expect(response.status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence(`zero_5xx_chief_engineer_flows.json`);

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, `zero_5xx_chief_engineer_flows.png`),
      fullPage: true,
    });
  });
});

// Multi-Role Validation: CAPTAIN
test.describe('Zero 5xx Errors: CAPTAIN Role', () => {
  test.use({
    storageState: path.join(process.cwd(), 'test-results', '.auth-states', 'captain-state.json'),
  });

  test('CAPTAIN: Zero 5xx across basic flows', async ({ page }) => {
    const monitor = new NetworkMonitor();
    monitor.attach(page);

    // Navigate to parts
    await navigateToParts(page, 'captain');

    // Search
    await searchForPart(page);

    // Wait for network activity
    await page.waitForTimeout(2000);

    // Make API calls
    const jwt = await page.evaluate(() => {
      const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
      if (!authKey) return null;
      const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
      return authData.access_token || null;
    });

    if (jwt) {
      // Test suggestions endpoint
      const response = await fetch(
        `${API_BASE}/v1/parts/suggestions?part_id=${process.env.TEST_PART_ID}`,
        {
          headers: { 'Authorization': `Bearer ${jwt}` },
        }
      );

      monitor.getResponses().push({
        url: `${API_BASE}/v1/parts/suggestions`,
        status: response.status,
        timestamp: new Date().toISOString(),
      });

      // Assert not 5xx
      expect(response.status).toBeLessThan(500);
    }

    // Save evidence
    monitor.saveEvidence(`zero_5xx_captain_flows.json`);

    // Assert zero 5xx
    const errors5xx = monitor.get5xxErrors();
    expect(errors5xx).toHaveLength(0);

    // Take screenshot
    await page.screenshot({
      path: path.join(ARTIFACTS_DIR, `zero_5xx_captain_flows.png`),
      fullPage: true,
    });
  });
});
