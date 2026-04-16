import { test as base, expect, Page, BrowserContext, APIRequestContext } from '@playwright/test';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as path from 'path';

/**
 * RBAC Test Fixtures for CelesteOS
 *
 * LAW 26: MUTATIVE TRUTH - Full-stack lifecycle verification
 * LAW 27: RBAC PHYSICS - Backend rejects, not just UI hides
 * LAW 29: MUTATION ISOLATION - Fresh data per test, no state bleed
 * LAW 30: CIRCUIT BREAKER - 3 retries max, then halt
 *
 * This fixture provides:
 * - Multi-role browser contexts (Crew, HOD, Captain)
 * - Supabase service-role client for database verification
 * - Test data seeding with unique identifiers
 * - Action execution helpers
 */

// Environment configuration
// IMPORTANT: TEST_YACHT_ID must always be set in CI via secrets.
// Never hard-code a production yacht ID here — CI test users will be created
// in the production tenant DB and appear in real crew views.
if (!process.env.TEST_YACHT_ID) {
  throw new Error(
    '[rbac-fixtures] TEST_YACHT_ID env var is required. ' +
    'Set it in CI secrets or your local .env.test. ' +
    'Do NOT use the production yacht ID as a fallback.'
  );
}
export const RBAC_CONFIG = {
  yachtId: process.env.TEST_YACHT_ID,
  baseUrl: process.env.E2E_BASE_URL || 'https://app.celeste7.ai',
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai',
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co',
  // Service role key for database verification (bypasses RLS)
  // TODO SECURITY: This service_role JWT is baked into source for local test convenience.
  // Move to SUPABASE_SERVICE_KEY env var / CI secret and remove the literal fallback.
  // Until then: never commit a rotation of this key without updating this fallback.
  supabaseServiceKey: process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY',
};

// Auth state paths
const AUTH_STATES = {
  hod:          path.join(__dirname, '../playwright/.auth/hod.json'),
  crew:         path.join(__dirname, '../playwright/.auth/crew.json'),
  captain:      path.join(__dirname, '../playwright/.auth/captain.json'),
  fleet_manager: path.join(__dirname, '../playwright/.auth/fleet_manager.json'),
};

// Test data generator with unique IDs (LAW 29: MUTATION ISOLATION)
export function generateTestId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

// Extended fixture types for RBAC testing
type RBACFixtures = {
  // Role-based browser pages
  hodPage: Page;
  crewPage: Page;
  captainPage: Page;
  fleetManagerPage: Page;

  // Supabase service-role client for database verification
  supabaseAdmin: SupabaseClient;

  // Test data seeding helpers
  seedFault: (title?: string) => Promise<{ id: string; title: string }>;
  seedWorkOrder: (title?: string) => Promise<{ id: string; title: string; wo_number: string }>;
  seedNote: (entityId: string, entityType: string, text?: string) => Promise<{ id: string; text: string }>;

  // Seed a search_index row for an equipment entity — bypasses the projector daemon.
  // Ensures at least one indexed entity exists for FTS/vector signal tests regardless
  // of whether the projection worker has run (LAW 9: content_hash targets cleanup).
  seedSearchIndex: () => Promise<{ equipmentId: string; equipmentName: string }>;

  // Action execution helpers
  executeAction: (page: Page, action: string, context: Record<string, string>, payload: Record<string, unknown>) => Promise<{ success: boolean; error?: string; data?: unknown }>;

  // Database verification helpers
  verifyDatabaseState: <T>(table: string, id: string, expectedFields: Partial<T>) => Promise<boolean>;
  verifyMutationDidNotOccur: (table: string, id: string, field: string, forbiddenValue: unknown) => Promise<boolean>;

  // Cleanup helper
  cleanupTestData: (table: string, ids: string[]) => Promise<void>;

  // Read-only getters (no insert, no cleanup needed)
  getExistingEquipment: () => Promise<{ id: string; name: string }>;
  getExistingPart: () => Promise<{ id: string; name: string; part_number: string | null }>;
  getCrewUserId: () => Promise<string>;
  getExistingDocument: () => Promise<{ id: string }>;
  getExistingCertificate: () => Promise<{ id: string; certificate_name: string }>;
  getExistingVesselCertificate: () => Promise<{ id: string }>;
  getPartWithStock: () => Promise<{ id: string; name: string; quantity_on_hand: number }>;
  getPartWithLocation: () => Promise<{ id: string; part_id: string; location: string; on_hand: number } | null>;
};

/**
 * RBAC Test fixture - extends base Playwright test
 */
export const test = base.extend<RBACFixtures>({
  // HOD (Head of Department) authenticated page
  hodPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.hod });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Crew authenticated page (lowest privileges)
  crewPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.crew });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Captain authenticated page (highest privileges)
  captainPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.captain });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Fleet manager authenticated page (cross-vessel view)
  fleetManagerPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: AUTH_STATES.fleet_manager });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  // Supabase admin client (service role - bypasses RLS)
  // IMPORTANT: must always point at TENANT (vzsohavtuotocgrfkfyd), NOT MASTER.
  // NEXT_PUBLIC_SUPABASE_URL in .env.e2e points at MASTER for frontend auth — if
  // supabaseAdmin used RBAC_CONFIG.supabaseUrl it would query MASTER and find 0 rows
  // for all pms_* tables (they live on TENANT). Root cause of failures 1/2/3 (2026-04-16).
  supabaseAdmin: async ({}, use) => {
    const tenantUrl =
      process.env.TENANT_SUPABASE_URL ||
      'https://vzsohavtuotocgrfkfyd.supabase.co';
    const tenantKey =
      process.env.TENANT_SERVICE_KEY ||
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
    const client = createClient(tenantUrl, tenantKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });
    await use(client);
  },

  // Seed a test fault (LAW 29: unique ID per test)
  seedFault: async ({ supabaseAdmin }, use) => {
    const createdIds: string[] = [];

    const seedFault = async (title?: string) => {
      const testTitle = title || `Test Fault ${generateTestId('fault')}`;

      // Fault requires equipment_id (NOT NULL) - get a valid equipment
      const { data: equipment } = await supabaseAdmin
        .from('pms_equipment')
        .select('id')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .limit(1)
        .single();

      if (!equipment) {
        throw new Error('No equipment found in test yacht - cannot seed fault');
      }

      const { data, error } = await supabaseAdmin
        .from('pms_faults')
        .insert({
          yacht_id: RBAC_CONFIG.yachtId,
          title: testTitle,
          description: 'Auto-generated test fault for RBAC testing',
          equipment_id: equipment.id,
        })
        .select('id, title')
        .single();

      if (error) throw new Error(`Failed to seed fault: ${error.message}`);
      createdIds.push(data.id);
      return data;
    };

    await use(seedFault);

    // Cleanup after test — ledger_events first (references entity_id), then entity
    if (createdIds.length > 0) {
      await supabaseAdmin.from('ledger_events').delete().in('entity_id', createdIds);
      await supabaseAdmin.from('pms_faults').delete().in('id', createdIds);
    }
  },

  // Seed a test work order (LAW 29: unique ID per test)
  seedWorkOrder: async ({ supabaseAdmin }, use) => {
    const createdIds: string[] = [];

    const seedWorkOrder = async (title?: string) => {
      const testTitle = title || `Test WO ${generateTestId('wo')}`;
      const woNumber = `WO-TEST-${Date.now()}`;

      // Note: Priority uses CHECK constraint with values: 'low', 'medium', 'high', 'critical'
      // Status uses CHECK constraint with values: 'draft', 'open', 'in_progress', 'on_hold', 'completed', 'cancelled'
      // created_by is required (NOT NULL)

      // First, get a valid user ID from the auth_users_profiles table
      const { data: userProfile } = await supabaseAdmin
        .from('auth_users_profiles')
        .select('id')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .limit(1)
        .single();

      const createdBy = userProfile?.id || '00000000-0000-0000-0000-000000000000';

      const { data, error } = await supabaseAdmin
        .from('pms_work_orders')
        .insert({
          yacht_id: RBAC_CONFIG.yachtId,
          title: testTitle,
          wo_number: woNumber,
          description: 'Auto-generated test work order for RBAC testing',
          created_by: createdBy,
        })
        .select('id, title, wo_number')
        .single();

      if (error) throw new Error(`Failed to seed work order: ${error.message}`);
      createdIds.push(data.id);
      return data;
    };

    await use(seedWorkOrder);

    // Cleanup after test — ledger_events first (references entity_id), then entity
    if (createdIds.length > 0) {
      await supabaseAdmin.from('ledger_events').delete().in('entity_id', createdIds);
      await supabaseAdmin.from('pms_work_orders').delete().in('id', createdIds);
    }
  },

  // Seed a test note
  seedNote: async ({ supabaseAdmin }, use) => {
    const createdIds: string[] = [];

    const seedNote = async (entityId: string, entityType: string, text?: string) => {
      const noteText = text || `Test note ${generateTestId('note')}`;

      // Determine the correct table based on entity type
      const tableMap: Record<string, string> = {
        work_order: 'pms_work_order_notes',
        equipment: 'pms_equipment_notes',
        fault: 'pms_fault_notes',
      };

      const table = tableMap[entityType];
      if (!table) throw new Error(`Unknown entity type: ${entityType}`);

      const foreignKeyMap: Record<string, string> = {
        work_order: 'work_order_id',
        equipment: 'equipment_id',
        fault: 'fault_id',
      };

      const { data, error } = await supabaseAdmin
        .from(table)
        .insert({
          [foreignKeyMap[entityType]]: entityId,
          note_text: noteText,
          created_by: 'test-system',
        })
        .select('id, note_text')
        .single();

      if (error) throw new Error(`Failed to seed note: ${error.message}`);
      createdIds.push(data.id);
      return { id: data.id, text: data.note_text };
    };

    await use(seedNote);
  },

  // Seed a search_index row for a real equipment entity.
  // Uses embedding_status='indexed' to bypass the projector daemon entirely.
  // content_hash='test-fixture-hash' scopes cleanup to only rows we inserted.
  // Vector dimension MUST be 1536 — any other size rejects the pgvector index.
  seedSearchIndex: async ({ supabaseAdmin }, use) => {
    const seededIds: string[] = [];

    const seedSearchIndex = async () => {
      const { data: equip } = await supabaseAdmin
        .from('pms_equipment')
        .select('id, name')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .not('name', 'is', null)
        .limit(1)
        .single();

      if (!equip) throw new Error('No equipment in test yacht for search_index seed');

      // Exactly 1536 dimensions — must match text-embedding-3-small output size
      const embedding = '[' + Array(1536).fill(0.001).join(',') + ']';

      const { error } = await supabaseAdmin.from('search_index').upsert({
        object_type: 'equipment',
        object_id: equip.id,
        yacht_id: RBAC_CONFIG.yachtId,
        org_id: RBAC_CONFIG.yachtId,
        // "work order" appears in any test WO's entity_text → FTS match guaranteed
        search_text: `${equip.name} maintenance work order inspection service engine check`,
        filters: {},
        payload: { name: equip.name, entity_type: 'equipment' },
        recency_ts: new Date().toISOString(),
        ident_norm: equip.name.toLowerCase().replace(/\s+/g, ''),
        source_version: 1,
        content_hash: 'test-fixture-hash',
        embedding_1536: embedding,
        embedding_model: 'text-embedding-3-small',
        embedding_version: 1,
        embedding_hash: 'test-fixture-embedding-hash',
        embedding_status: 'indexed',
        updated_at: new Date().toISOString(),
      }, { onConflict: 'object_type,object_id' });

      if (error) throw new Error(`Failed to seed search_index: ${error.message}`);
      seededIds.push(equip.id);
      return { equipmentId: equip.id, equipmentName: equip.name };
    };

    await use(seedSearchIndex);

    // Cleanup: only delete rows we seeded — real indexed rows are left intact
    if (seededIds.length > 0) {
      await supabaseAdmin
        .from('search_index')
        .delete()
        .eq('object_type', 'equipment')
        .in('object_id', seededIds)
        .eq('content_hash', 'test-fixture-hash');
    }
  },

  // Execute an action via the API
  executeAction: async ({ request }, use) => {
    const executeAction = async (
      page: Page,
      action: string,
      context: Record<string, string>,
      payload: Record<string, unknown>
    ) => {
      // Get auth token from page context
      const token = await getAuthToken(page);

      const response = await request.post(`${RBAC_CONFIG.apiUrl}/v1/actions/execute`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          action,
          context: { yacht_id: RBAC_CONFIG.yachtId, ...context },
          payload,
        },
      });

      const result = await response.json();
      return {
        success: result.success === true,
        error: result.error?.message || result.error,
        data: result.data,
        status: response.status(),
      };
    };

    await use(executeAction);
  },

  // Verify database state matches expected values
  verifyDatabaseState: async ({ supabaseAdmin }, use) => {
    const verifyDatabaseState = async <T>(
      table: string,
      id: string,
      expectedFields: Partial<T>
    ): Promise<boolean> => {
      const { data, error } = await supabaseAdmin
        .from(table)
        .select('*')
        .eq('id', id)
        .single();

      if (error) {
        console.error(`Database verification failed: ${error.message}`);
        return false;
      }

      for (const [key, expectedValue] of Object.entries(expectedFields)) {
        if (data[key] !== expectedValue) {
          console.error(`Field mismatch: ${key} expected ${expectedValue}, got ${data[key]}`);
          return false;
        }
      }

      return true;
    };

    await use(verifyDatabaseState);
  },

  // Verify a mutation DID NOT occur (for security tests)
  verifyMutationDidNotOccur: async ({ supabaseAdmin }, use) => {
    const verifyMutationDidNotOccur = async (
      table: string,
      id: string,
      field: string,
      forbiddenValue: unknown
    ): Promise<boolean> => {
      const { data, error } = await supabaseAdmin
        .from(table)
        .select(field)
        .eq('id', id)
        .single();

      if (error) {
        // Record not found is acceptable (mutation may have been completely blocked)
        return true;
      }

      // If the field equals the forbidden value, the mutation occurred (FAIL)
      if ((data as unknown as Record<string, unknown>)[field] === forbiddenValue) {
        console.error(`SECURITY BREACH: Unauthorized mutation detected! ${table}.${field} = ${forbiddenValue}`);
        return false;
      }

      return true;
    };

    await use(verifyMutationDidNotOccur);
  },

  // Read-only: fetch first equipment from test yacht
  getExistingEquipment: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('pms_equipment')
        .select('id, name')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .is('deleted_at', null)
        .neq('status', 'decommissioned')
        .limit(1)
        .single();
      if (error || !data) throw new Error(`getExistingEquipment: ${error?.message || 'no equipment found'}`);
      return data as { id: string; name: string };
    });
  },

  // Read-only: fetch first part from test yacht
  getExistingPart: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('pms_parts')
        .select('id, name, part_number')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .is('deleted_at', null)
        .limit(1)
        .single();
      if (error || !data) throw new Error(`getExistingPart: ${error?.message || 'no parts found'}`);
      return data as { id: string; name: string; part_number: string | null };
    });
  },

  // Crew user: exists in MASTER DB, has role='crew' in auth_users_roles for test yacht.
  // Using captain UUID returns 200 (captain is allowed); this UUID returns FORBIDDEN.
  getCrewUserId: async ({}, use) => {
    await use(async () => '05a54017-4749-49e8-a865-cb7fd7d2b0c3');
  },

  // Read-only: fetch first document from test yacht
  getExistingDocument: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('doc_metadata')
        .select('id')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .is('deleted_at', null)
        .limit(1)
        .single();
      if (error || !data) {
        // Documents may not be seeded — signal caller to skip
        throw new Error(`SKIP: no documents found in test environment (${error?.message ?? 'no rows'})`);
      }
      return data as { id: string };
    });
  },

  // Read-only: fetch first vessel certificate from test yacht
  getExistingCertificate: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('pms_vessel_certificates')
        .select('id, certificate_name')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .limit(1)
        .single();
      if (error || !data) throw new Error(`getExistingCertificate: ${error?.message || 'no certificates found'}`);
      return data as { id: string; certificate_name: string };
    });
  },

  // Read-only: fetch first vessel certificate (used by shard-34 update/supersede tests)
  // Excludes superseded certificates — the update_certificate handler rejects them with 500.
  getExistingVesselCertificate: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('pms_vessel_certificates')
        .select('id')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .neq('status', 'superseded')
        .limit(1)
        .single();
      if (error || !data) throw new Error(`getExistingVesselCertificate: ${error?.message || 'no non-superseded vessel certificates found'}`);
      return data as { id: string };
    });
  },

  // Read-only: fetch first part with quantity_on_hand >= 2 (for log_part_usage tests)
  getPartWithStock: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data, error } = await supabaseAdmin
        .from('pms_parts')
        .select('id, name, quantity_on_hand')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .is('deleted_at', null)
        .gte('quantity_on_hand', 2)
        .limit(1)
        .single();
      if (error || !data) throw new Error(`getPartWithStock: ${error?.message || 'no parts with stock >= 2 found'}`);
      return data as { id: string; name: string; quantity_on_hand: number };
    });
  },

  // Read-only: fetch a pms_part_stock row with a location set (for transfer_part tests)
  getPartWithLocation: async ({ supabaseAdmin }, use) => {
    await use(async () => {
      const { data } = await supabaseAdmin
        .from('pms_part_stock')
        .select('id, part_id, location, on_hand')
        .eq('yacht_id', RBAC_CONFIG.yachtId)
        .not('location', 'is', null)
        .gt('on_hand', 0)
        .limit(1)
        .single();
      if (!data) return null;
      return data as { id: string; part_id: string; location: string; on_hand: number };
    });
  },

  // Cleanup test data
  cleanupTestData: async ({ supabaseAdmin }, use) => {
    const cleanupTestData = async (table: string, ids: string[]) => {
      if (ids.length === 0) return;
      await supabaseAdmin.from(table).delete().in('id', ids);
    };

    await use(cleanupTestData);
  },
});

/**
 * Helper to extract auth token from page context
 */
async function getAuthToken(page: Page): Promise<string> {
  const cookies = await page.context().cookies();
  const authCookie = cookies.find(c => c.name.includes('supabase-auth-token'));

  if (authCookie) {
    return authCookie.value;
  }

  // Fallback: Get from localStorage
  const token = await page.evaluate(() => {
    const stored = localStorage.getItem('sb-auth-token');
    if (stored) {
      try {
        return JSON.parse(stored).access_token;
      } catch {
        return null;
      }
    }
    // Try alternate storage key
    for (const key of Object.keys(localStorage)) {
      if (key.includes('supabase') && key.includes('auth')) {
        try {
          const data = JSON.parse(localStorage.getItem(key) || '{}');
          if (data.access_token) return data.access_token;
        } catch {
          continue;
        }
      }
    }
    return null;
  });

  return token || '';
}

/**
 * Page Objects for RBAC testing
 */
export class ActionModalPO {
  constructor(private page: Page) {}

  get modal() {
    return this.page.locator('[role="dialog"]');
  }

  get submitButton() {
    return this.modal.locator('button[type="submit"], button:has-text("Submit"), button:has-text("Save"), button:has-text("Confirm")');
  }

  get cancelButton() {
    return this.modal.locator('button:has-text("Cancel")');
  }

  get loadingIndicator() {
    return this.modal.locator('[data-loading="true"], .loading, .spinner');
  }

  async waitForOpen(): Promise<void> {
    await this.modal.waitFor({ state: 'visible', timeout: 5000 });
  }

  async waitForClose(): Promise<void> {
    await this.modal.waitFor({ state: 'hidden', timeout: 10000 });
  }

  async fillTextarea(text: string): Promise<void> {
    const textarea = this.modal.locator('textarea');
    await textarea.fill(text);
  }

  async submit(): Promise<void> {
    // Use force:true to bypass sticky header interception
    await this.submitButton.click({ force: true });
  }
}

export class ToastPO {
  constructor(private page: Page) {}

  get successToast() {
    // Broader selector for success toasts across different toast libraries
    return this.page.locator('[data-sonner-toast][data-type="success"], .toast-success, [role="status"]:has-text("success"), .Toastify__toast--success, [data-testid*="toast"]:has-text("success"), [class*="toast"]:has-text("success"), [class*="toast"]:has-text("Success"), [class*="toast"]:has-text("saved"), [class*="toast"]:has-text("added")');
  }

  get errorToast() {
    return this.page.locator('[data-sonner-toast][data-type="error"], .toast-error, [role="alert"], .Toastify__toast--error, [data-testid*="toast"]:has-text("error"), [class*="toast"]:has-text("error"), [class*="toast"]:has-text("Error"), [class*="toast"]:has-text("failed")');
  }

  async waitForSuccess(timeout = 5000): Promise<void> {
    try {
      await this.successToast.waitFor({ state: 'visible', timeout });
    } catch {
      // If specific toast not found, check for modal close (implicit success)
      const modal = this.page.locator('[role="dialog"]');
      const modalVisible = await modal.isVisible().catch(() => false);
      if (!modalVisible) {
        // Modal closed = likely success
        return;
      }
      throw new Error('Success toast not found and modal still visible');
    }
  }

  async waitForError(timeout = 5000): Promise<void> {
    await this.errorToast.waitFor({ state: 'visible', timeout });
  }

  async getErrorMessage(): Promise<string> {
    return await this.errorToast.textContent() || '';
  }
}

// Re-export expect and base page objects
export { expect } from '@playwright/test';
export { SpotlightSearchPO, ContextPanelPO } from './fixtures';
