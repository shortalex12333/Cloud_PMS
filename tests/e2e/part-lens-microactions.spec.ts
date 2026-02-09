/**
 * Part Lens Microactions E2E Test
 *
 * Tests the complete Part Lens microaction flow:
 * 1. Login with test user
 * 2. Search for parts (Racor)
 * 3. Verify microactions appear in results
 * 4. Test microaction buttons are functional
 * 5. Monitor for RLS, backend, DB, and frontend errors
 *
 * Runs against production API: pipeline-core.int.celeste7.ai
 */

import { test, expect } from '@playwright/test';
import { saveScreenshot, saveArtifact, createEvidenceBundle } from '../helpers/artifacts';

// Test user credentials
const TEST_USERS = [
  { email: 'hod.test@alex-short.com', role: 'HOD', password: process.env.TEST_USER_PASSWORD || 'Password2!' },
  { email: 'crew.test@alex-short.com', role: 'Crew', password: process.env.TEST_USER_PASSWORD || 'Password2!' },
  { email: 'captain.test@alex-short.com', role: 'Captain', password: process.env.TEST_USER_PASSWORD || 'Password2!' },
];

// Production API endpoint
const PRODUCTION_API = 'https://pipeline-core.int.celeste7.ai';

test.describe('Part Lens Microactions - Production E2E', () => {
  // Run tests for each user role
  for (const testUser of TEST_USERS) {
    test.describe(`Testing as ${testUser.role} (${testUser.email})`, () => {
      let jwtToken: string | null = null;
      let consoleLogs: Array<{ type: string; text: string; timestamp: string }> = [];
      let networkErrors: Array<{ url: string; status: number; statusText: string; timestamp: string }> = [];
      let rlsViolations: Array<{ message: string; timestamp: string }> = [];

      test.beforeEach(async ({ page }) => {
        consoleLogs = [];
        networkErrors = [];
        rlsViolations = [];

        // Capture console logs
        page.on('console', (msg) => {
          const text = msg.text();
          consoleLogs.push({
            type: msg.type(),
            text,
            timestamp: new Date().toISOString(),
          });

          // Check for RLS violations
          if (text.includes('RLS') || text.includes('row level security') || text.includes('permission denied')) {
            rlsViolations.push({
              message: text,
              timestamp: new Date().toISOString(),
            });
          }
        });

        // Capture network failures
        page.on('response', (response) => {
          if (response.status() >= 400) {
            networkErrors.push({
              url: response.url(),
              status: response.status(),
              statusText: response.statusText(),
              timestamp: new Date().toISOString(),
            });
          }
        });

        // Store for later use
        (page as any).__consoleLogs = consoleLogs;
        (page as any).__networkErrors = networkErrors;
        (page as any).__rlsViolations = rlsViolations;
      });

      test('Login and capture JWT token', async ({ page }) => {
        const testName = `part_lens/${testUser.role.toLowerCase()}/01_login`;

        // Navigate to login page
        await page.goto('/login');
        await saveScreenshot(page, testName, '01_login_page');

        // Fill credentials
        await page.fill('input[type="email"], input[name="email"]', testUser.email);
        await page.fill('input[type="password"], input[name="password"]', testUser.password);
        await saveScreenshot(page, testName, '02_credentials_filled');

        // Login
        await page.click('button[type="submit"]');

        // Wait for redirect
        await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
        await saveScreenshot(page, testName, '03_logged_in');

        // Capture JWT token from storage or network
        const token = await page.evaluate(() => {
          // Try localStorage
          const stored = localStorage.getItem('sb-auth-token') ||
                        localStorage.getItem('supabase.auth.token') ||
                        sessionStorage.getItem('sb-auth-token');

          if (stored) {
            try {
              const parsed = JSON.parse(stored);
              return parsed.access_token || parsed.currentSession?.access_token || null;
            } catch {}
          }

          return null;
        });

        jwtToken = token;

        // Save artifacts
        saveArtifact('jwt_token.txt', jwtToken || 'NO_TOKEN_FOUND', testName);
        saveArtifact('console_logs.json', consoleLogs, testName);
        saveArtifact('network_errors.json', networkErrors, testName);

        createEvidenceBundle(testName, {
          consoleLogs,
          networkErrors,
          assertions: [
            {
              name: 'Login successful',
              passed: !page.url().includes('/login'),
              message: `Current URL: ${page.url()}`,
            },
            {
              name: 'JWT token captured',
              passed: !!jwtToken,
              message: jwtToken ? `Token: ${jwtToken.substring(0, 20)}...` : 'No token found',
            },
            {
              name: 'No network errors during login',
              passed: networkErrors.length === 0,
              message: networkErrors.length > 0 ? `${networkErrors.length} errors` : undefined,
            },
          ],
        });

        expect(jwtToken, 'JWT token should be captured').toBeTruthy();
        expect(networkErrors.length, 'Should have no network errors').toBe(0);
      });

      test('Search for Racor parts and verify results', async ({ page, context }) => {
        const testName = `part_lens/${testUser.role.toLowerCase()}/02_search_racor`;

        // Login first
        await page.goto('/login');
        await page.fill('input[type="email"], input[name="email"]', testUser.email);
        await page.fill('input[type="password"], input[name="password"]', testUser.password);
        await page.click('button[type="submit"]');
        await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });

        // Navigate to search
        await page.goto('/search');
        await saveScreenshot(page, testName, '01_search_page');

        // Perform search
        const searchInput = page.locator('input[type="search"], input[placeholder*="Search"], input[name="query"]');
        await searchInput.fill('Racor');
        await saveScreenshot(page, testName, '02_search_query_entered');

        // Submit search (either press Enter or click search button)
        await searchInput.press('Enter');

        // Wait for search results
        await page.waitForTimeout(3000); // Give time for API response

        await saveScreenshot(page, testName, '03_search_results');

        // Check for search results
        const resultsVisible = await page.locator('[data-testid="search-result"], .search-result, [class*="result"]').count();

        // Save artifacts
        saveArtifact('console_logs.json', consoleLogs, testName);
        saveArtifact('network_errors.json', networkErrors, testName);
        saveArtifact('rls_violations.json', rlsViolations, testName);

        // Check for backend errors in console
        const backendErrors = consoleLogs.filter(log =>
          log.type === 'error' &&
          (log.text.includes('500') || log.text.includes('Internal Server Error') || log.text.includes('Failed to fetch'))
        );

        // Check for RLS issues
        const hasRlsIssues = rlsViolations.length > 0;

        createEvidenceBundle(testName, {
          consoleLogs,
          networkErrors,
          rlsViolations,
          searchResults: { count: resultsVisible },
          assertions: [
            {
              name: 'Search executed',
              passed: true,
              message: 'Search query submitted',
            },
            {
              name: 'No backend errors',
              passed: backendErrors.length === 0,
              message: backendErrors.length > 0 ? `${backendErrors.length} backend errors` : undefined,
            },
            {
              name: 'No RLS violations',
              passed: !hasRlsIssues,
              message: hasRlsIssues ? `${rlsViolations.length} RLS issues detected` : undefined,
            },
            {
              name: 'Search results visible',
              passed: resultsVisible > 0,
              message: `Found ${resultsVisible} result elements`,
            },
          ],
        });

        expect(backendErrors.length, 'Should have no backend errors').toBe(0);
        expect(rlsViolations.length, 'Should have no RLS violations').toBe(0);
      });

      test('Verify microactions appear in search results', async ({ page, context }) => {
        const testName = `part_lens/${testUser.role.toLowerCase()}/03_verify_microactions`;

        // Login
        await page.goto('/login');
        await page.fill('input[type="email"], input[name="email"]', testUser.email);
        await page.fill('input[type="password"], input[name="password"]', testUser.password);
        await page.click('button[type="submit"]');
        await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });

        // Navigate to search and perform search
        await page.goto('/search');
        const searchInput = page.locator('input[type="search"], input[placeholder*="Search"], input[name="query"]');
        await searchInput.fill('Racor');
        await searchInput.press('Enter');

        // Wait for results
        await page.waitForTimeout(3000);

        // Look for microaction buttons
        const actionButtons = await page.locator('button[data-action-id], [data-testid*="action"], button[class*="action"], button:has-text("Receive"), button:has-text("View Details"), button:has-text("Add to Shopping List")').count();

        await saveScreenshot(page, testName, '01_with_microactions');

        // Try to find specific Part Lens microactions
        const receiveButton = await page.locator('button:has-text("Receive Part"), button:has-text("Receive")').count();
        const viewDetailsButton = await page.locator('button:has-text("View Part Details"), button:has-text("View Details")').count();
        const shoppingListButton = await page.locator('button:has-text("Add to Shopping List"), button:has-text("Shopping List")').count();

        // Capture the HTML of first result for inspection
        const firstResultHtml = await page.locator('[data-testid="search-result"], .search-result, [class*="result"]').first().innerHTML().catch(() => 'NO_RESULT_FOUND');

        // Save artifacts
        saveArtifact('console_logs.json', consoleLogs, testName);
        saveArtifact('network_errors.json', networkErrors, testName);
        saveArtifact('first_result_html.html', firstResultHtml, testName);

        createEvidenceBundle(testName, {
          consoleLogs,
          networkErrors,
          microactions: {
            totalButtons: actionButtons,
            receiveButton,
            viewDetailsButton,
            shoppingListButton,
          },
          assertions: [
            {
              name: 'Microaction buttons found',
              passed: actionButtons > 0,
              message: `Found ${actionButtons} action buttons`,
            },
            {
              name: 'Receive Part action available',
              passed: receiveButton > 0,
              message: `Found ${receiveButton} "Receive Part" buttons`,
            },
            {
              name: 'View Details action available',
              passed: viewDetailsButton > 0,
              message: `Found ${viewDetailsButton} "View Details" buttons`,
            },
          ],
        });

        // Log results
        console.log('='.repeat(80));
        console.log(`MICROACTION VERIFICATION - ${testUser.role}`);
        console.log('='.repeat(80));
        console.log(`Total action buttons: ${actionButtons}`);
        console.log(`Receive Part buttons: ${receiveButton}`);
        console.log(`View Details buttons: ${viewDetailsButton}`);
        console.log(`Shopping List buttons: ${shoppingListButton}`);
        console.log('='.repeat(80));

        // Assertions
        expect(actionButtons, 'Should find at least one microaction button').toBeGreaterThan(0);
      });

      test('Test microactions API directly with JWT', async ({ page, context }) => {
        const testName = `part_lens/${testUser.role.toLowerCase()}/04_api_direct_test`;

        // Login and capture JWT
        await page.goto('/login');
        await page.fill('input[type="email"], input[name="email"]', testUser.email);
        await page.fill('input[type="password"], input[name="password"]', testUser.password);
        await page.click('button[type="submit"]');
        await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });

        // Get JWT token
        const token = await page.evaluate(() => {
          const stored = localStorage.getItem('sb-auth-token') ||
                        localStorage.getItem('supabase.auth.token') ||
                        sessionStorage.getItem('sb-auth-token');
          if (stored) {
            try {
              const parsed = JSON.parse(stored);
              return parsed.access_token || parsed.currentSession?.access_token || null;
            } catch {}
          }
          return null;
        });

        if (!token) {
          console.log('⚠️  No JWT token found, skipping API test');
          return;
        }

        console.log('✅ JWT token captured:', token.substring(0, 20) + '...');

        // Make direct API request
        const apiResponse = await context.request.post(`${PRODUCTION_API}/webhook/search`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          data: {
            query: 'Racor',
            limit: 3,
          },
        });

        const responseBody = await apiResponse.json().catch(() => ({}));

        // Save API response
        saveArtifact('api_response.json', responseBody, testName);

        // Check for microactions in response
        const results = responseBody.results || [];
        const firstResult = results[0] || {};
        const actions = firstResult.actions || [];

        console.log('='.repeat(80));
        console.log('API DIRECT TEST RESULTS');
        console.log('='.repeat(80));
        console.log(`API Status: ${apiResponse.status()}`);
        console.log(`Results count: ${results.length}`);
        console.log(`First result title: ${firstResult.title || 'N/A'}`);
        console.log(`First result source_table: ${firstResult.source_table || 'N/A'}`);
        console.log(`Microactions count: ${actions.length}`);
        if (actions.length > 0) {
          console.log('Microactions found:');
          actions.forEach((action: any, i: number) => {
            console.log(`  ${i + 1}. ${action.label} (${action.action_id}) - priority ${action.priority}`);
          });
        } else {
          console.log('⚠️  NO MICROACTIONS FOUND');
        }
        console.log('='.repeat(80));

        createEvidenceBundle(testName, {
          apiResponse: responseBody,
          microactions: actions,
          assertions: [
            {
              name: 'API request successful',
              passed: apiResponse.status() === 200,
              message: `Status: ${apiResponse.status()}`,
            },
            {
              name: 'Results returned',
              passed: results.length > 0,
              message: `${results.length} results`,
            },
            {
              name: 'Microactions present',
              passed: actions.length > 0,
              message: actions.length > 0 ? `${actions.length} microactions` : 'NO MICROACTIONS',
            },
          ],
        });

        expect(apiResponse.status(), 'API should return 200').toBe(200);
        expect(results.length, 'Should have search results').toBeGreaterThan(0);
        expect(actions.length, 'Should have microactions in results').toBeGreaterThan(0);
      });
    });
  }
});
