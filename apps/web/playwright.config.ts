import { defineConfig, devices } from '@playwright/test';

/**
 * CelesteOS Playwright Configuration
 *
 * LAW 11: MECHANICAL SYMPATHY (CONCURRENCY CONTROL)
 * - Workers limited to 2 to respect 512MB Docker container limits
 * - Chromium instances are memory-heavy (~80-150MB each)
 * - Sequential execution prevents OOM crashes
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify actual rendering, not just API responses
 * - Document viewer must successfully load signed URLs
 * - Data grids must render with correct metadata
 */

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const IS_CI = !!process.env.CI;

export default defineConfig({
  // Test directory structure
  testDir: './e2e',

  // Global timeout settings
  timeout: 60_000,  // 60 seconds per test
  expect: {
    timeout: 10_000,  // 10 seconds for assertions
  },

  // Retry failed tests (F1 search has cold-start latency that causes flaky first requests)
  retries: IS_CI ? 2 : 1,

  // LAW 11: Strict worker limits to prevent memory exhaustion
  workers: IS_CI ? 1 : 2,
  fullyParallel: false,  // Sequential shards, parallel within shard

  // Fail fast in CI
  forbidOnly: IS_CI,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'playwright-report/results.json' }],
    ['list'],  // Console output
  ],

  // Global setup - authentication state
  globalSetup: './e2e/global-setup.ts',

  // Shared settings for all projects
  use: {
    baseURL: BASE_URL,

    // Trace on first retry only (saves disk space)
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Strict mode - fail if multiple elements match
    strictLocators: true,

    // Action timeouts
    actionTimeout: 15_000,
    navigationTimeout: 30_000,

    // Viewport - standard desktop
    viewport: { width: 1440, height: 900 },

    // Authentication state from global setup
    storageState: './playwright/.auth/user.json',
  },

  // Test projects (shards)
  projects: [
    // =========================================================================
    // SHARD 0: Setup - No dependencies, runs first
    // =========================================================================
    {
      name: 'setup',
      testMatch: /global-setup\.ts/,
      use: {
        storageState: undefined,  // No prior auth
      },
    },

    // =========================================================================
    // SHARD 1: Authentication & Tenant Isolation (LAW 8)
    // =========================================================================
    {
      name: 'shard-1-auth',
      testDir: './e2e/shard-1-auth',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 2: Search Functionality (F1 Pipeline)
    // =========================================================================
    {
      name: 'shard-2-search',
      testDir: './e2e/shard-2-search',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 3: Document & Certificate Rendering (LAW 12)
    // =========================================================================
    {
      name: 'shard-3-documents',
      testDir: './e2e/shard-3-documents',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 4: Entity Lenses (Work Orders, Faults, Equipment)
    // =========================================================================
    {
      name: 'shard-4-entities',
      testDir: './e2e/shard-4-entities',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 5: Adversarial & Edge Cases
    // =========================================================================
    {
      name: 'shard-5-adversarial',
      testDir: './e2e/shard-5-adversarial',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 6: Email Integration
    // =========================================================================
    {
      name: 'shard-6-email',
      testDir: './e2e/shard-6-email',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 7: Equipment Lens Deep Testing
    // =========================================================================
    {
      name: 'shard-7-equipment',
      testDir: './e2e/shard-7-equipment',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 8: Work Order Lens Deep Testing
    // =========================================================================
    {
      name: 'shard-8-workorders',
      testDir: './e2e/shard-8-workorders',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 9: Fault Lens Deep Testing
    // =========================================================================
    {
      name: 'shard-9-faults',
      testDir: './e2e/shard-9-faults',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 10: Part/Inventory Lens Deep Testing
    // =========================================================================
    {
      name: 'shard-10-parts',
      testDir: './e2e/shard-10-parts',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 11: Extreme Case Search (Misspellings, Semantic, Fuzzy)
    // =========================================================================
    {
      name: 'shard-11-extremecases',
      testDir: './e2e/shard-11-extremecases',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // =========================================================================
    // SHARD 31: Fragmented Routes - Work Orders, Faults, Equipment, Inventory
    // Tests for the new /work-orders, /faults, /equipment, /inventory routes
    // =========================================================================
    {
      name: 'shard-31-fragmented-routes',
      testDir: './e2e/shard-31-fragmented-routes',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    // =========================================================================
    // SHARD 32: Ledger History & Audit Trail
    // =========================================================================
    {
      name: 'shard-32-ledger',
      testDir: './e2e/shard-32-ledger',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 33: Lens Actions (Stage 3 action mutation suite — Part 1)
    // =========================================================================
    {
      name: 'shard-33-lens-actions',
      testDir: './e2e/shard-33-lens-actions',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 34: Lens Actions (Stage 3 action mutation suite — Part 2, helpers)
    // =========================================================================
    {
      name: 'shard-34-lens-actions',
      testDir: './e2e/shard-34-lens-actions',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    // =========================================================================
    // SHARDS 35–47: Stage 3 domain action tests (Phase 4/5 migration coverage)
    // =========================================================================
    {
      name: 'shard-35-shopping-parts',
      testDir: './e2e/shard-35-shopping-parts',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-36-receiving',
      testDir: './e2e/shard-36-receiving',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-37-hours-of-rest',
      testDir: './e2e/shard-37-hours-of-rest',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-38-fault-actions',
      testDir: './e2e/shard-38-fault-actions',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-39-wo-equipment',
      testDir: './e2e/shard-39-wo-equipment',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-40-purchase-handover',
      testDir: './e2e/shard-40-purchase-handover',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-41-wo-extended',
      testDir: './e2e/shard-41-wo-extended',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-42-fault-equipment',
      testDir: './e2e/shard-42-fault-equipment',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-43-docs-certs',
      testDir: './e2e/shard-43-docs-certs',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-44-parts-shopping',
      testDir: './e2e/shard-44-parts-shopping',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-45-receiving-po',
      testDir: './e2e/shard-45-receiving-po',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-46-hor-extended',
      testDir: './e2e/shard-46-hor-extended',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-47-handover-misc',
      testDir: './e2e/shard-47-handover-misc',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'shard-48-attention-filters',
      testDir: './e2e/shard-48-attention-filters',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 49: Handover Export E2E (Phases A/B — microservice delegation)
    // Higher timeouts required: LLM pipeline (classify→group→merge) takes up to
    // 120s. Global actionTimeout (15s) is too short for POST /handover/export.
    // =========================================================================
    {
      name: 'shard-49-handover-export-e2e',
      testDir: './e2e/shard-49-handover-export-e2e',
      testMatch: '**/*.spec.ts',
      dependencies: ['setup'],
      timeout: 180_000,  // 3 min per test — LLM pipeline can take up to 120s
      use: {
        ...devices['Desktop Chrome'],
        actionTimeout: 150_000,  // 2.5 min for API calls (LLM pipeline)
      },
    },
    // =========================================================================
    // SHARD 50: Interface Pivot — Vessel Surface, Sidebar, Scope Tag, Auth
    // =========================================================================
    {
      name: 'shard-50-interface-pivot',
      testDir: './e2e/shard-50-interface-pivot',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 51: Fleet Verification — auth, vessel switching, overview, search
    // =========================================================================
    {
      name: 'shard-51-fleet-verification',
      testDir: './e2e/shard-51-fleet-verification',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // DOCUMENTS MVP — full frontend walkthrough (mirrors DOCUMENTS_MVP_CHEATSHEET.md)
    // =========================================================================
    {
      name: 'shard-52-documents-mvp',
      testDir: './e2e/shard-52-documents-mvp',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 52b: Handover Browser E2E — queue, draft CRUD, document, sign flows
    // =========================================================================
    {
      name: 'shard-52-handover-browser',
      testDir: './e2e/shard-52-handover-browser',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // CERTIFICATE E2E — list, lens, actions, role gating, register, DB verification
    // =========================================================================
    {
      name: 'shard-53-certificate-e2e',
      testDir: './e2e/shard-53-certificate-e2e',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'] },
    },
    // =========================================================================
    // SHARD 54: Handover UI (HANDOVER_TESTER) — MASTER-auth login path so
    // app.celeste7.ai recognises the session; storageState undefined to avoid
    // TENANT-signed JWTs from global-setup.
    // =========================================================================
    {
      name: 'shard-54-handover-tester-ui',
      testDir: './e2e/shard-54-handover-tester-ui',
      dependencies: ['setup'],
      timeout: 180_000,
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined,
      },
    },
  ],

  // Web server configuration (if running locally)
  webServer: process.env.E2E_NO_SERVER ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !IS_CI,
    timeout: 120_000,
  },
});
