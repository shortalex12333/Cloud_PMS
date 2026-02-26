/**
 * Fault Test Data Seed (Task F4)
 *
 * Creates deterministic test data for Fault E2E testing.
 * Ensures all required fault states exist for acknowledge/close/reopen tests.
 *
 * Required Test Data:
 * 1. Fault in 'open' status (for acknowledge/close tests)
 * 2. Fault in 'closed' status (for reopen test)
 * 3. Fault with equipment_id set (all faults require this)
 * 4. Fault with notes attached
 *
 * @see e2e/shard-9-faults/faults.spec.ts
 * @see e2e/shard-31-fragmented-routes/route-faults.spec.ts
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for easy identification and cleanup
const TEST_PREFIX = 'E2E_FAULT_TEST';

/**
 * Deterministic Fault Test IDs
 * These UUIDs are fixed for E2E tests to allow deterministic assertions.
 * Using v4-like format but with recognizable patterns.
 */
export const FAULT_TEST_IDS = {
  // Fault in 'open' status - for acknowledge/close tests
  FAULT_OPEN: 'f4000001-0001-4000-a000-000000000001',

  // Fault in 'closed' status - for reopen tests
  FAULT_CLOSED: 'f4000002-0002-4000-a000-000000000002',

  // Fault in 'investigating' status - for status transition tests
  FAULT_INVESTIGATING: 'f4000003-0003-4000-a000-000000000003',

  // Fault with notes attached - for notes display/add tests
  FAULT_WITH_NOTES: 'f4000004-0004-4000-a000-000000000004',

  // Fault in 'resolved' status - for closed vs resolved distinction
  FAULT_RESOLVED: 'f4000005-0005-4000-a000-000000000005',

  // High severity fault - for severity filtering tests
  FAULT_CRITICAL: 'f4000006-0006-4000-a000-000000000006',

  // Related note IDs
  NOTE_FOR_FAULT: 'f4000101-0001-4000-b000-000000000001',
  NOTE_FOR_FAULT_2: 'f4000101-0002-4000-b000-000000000002',
} as const;

/**
 * Seed result with created data
 */
export interface FaultSeedResult {
  success: boolean;
  faults: {
    id: string;
    title: string;
    status: string;
    severity: string;
    hasNotes: boolean;
  }[];
  notes: {
    id: string;
    faultId: string;
    text: string;
  }[];
  errors: string[];
}

/**
 * Main seeding function - creates deterministic fault test data
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns FaultSeedResult with created data details
 */
export async function seedFaultTestData(supabase?: SupabaseClient): Promise<FaultSeedResult> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const errors: string[] = [];
  const createdFaults: FaultSeedResult['faults'] = [];
  const createdNotes: FaultSeedResult['notes'] = [];

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[FAULT-SEED] Cleaning up old test data...');

    // Delete notes first (FK constraint)
    await client
      .from('pms_notes')
      .delete()
      .like('text', `${TEST_PREFIX}%`);

    // Delete faults by ID (deterministic IDs)
    const faultIds = Object.values(FAULT_TEST_IDS).filter(id => id.startsWith('f4000'));
    for (const id of faultIds) {
      await client.from('pms_faults').delete().eq('id', id);
    }

    // Also cleanup by title prefix
    await client
      .from('pms_faults')
      .delete()
      .like('title', `${TEST_PREFIX}%`);

    // ==========================================================================
    // STEP 2: Get required foreign key references
    // ==========================================================================
    console.log('[FAULT-SEED] Fetching required references...');

    // Get a valid user ID for created_by fields
    const { data: userProfile, error: userError } = await client
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    if (userError || !userProfile) {
      errors.push(`Failed to get user profile: ${userError?.message || 'No user found'}`);
      return { success: false, faults: [], notes: [], errors };
    }

    const createdBy = (userProfile as { id: string }).id;

    // Get a valid equipment ID (faults require equipment_id NOT NULL)
    const { data: equipment, error: equipError } = await client
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    if (equipError || !equipment) {
      errors.push(`Failed to get equipment: ${equipError?.message || 'No equipment found'}`);
      return { success: false, faults: [], notes: [], errors };
    }

    const equipmentId = (equipment as { id: string; name: string }).id;
    const equipmentName = (equipment as { id: string; name: string }).name;

    console.log(`[FAULT-SEED] Using equipment: ${equipmentName} (${equipmentId})`);

    // ==========================================================================
    // STEP 3: Seed Faults
    // ==========================================================================
    console.log('[FAULT-SEED] Seeding faults...');

    // Fault status values from schema: open, investigating, work_ordered, resolved, closed, false_alarm
    // Severity enum: cosmetic, minor, major, critical, safety
    const faultsToCreate = [
      // 1. Fault in 'open' status - for acknowledge/close tests
      {
        id: FAULT_TEST_IDS.FAULT_OPEN,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_OPEN_STATUS`,
        fault_code: 'E2E-001',
        description: 'Test fault in OPEN status for acknowledge/close E2E tests',
        status: 'open',
        severity: 'minor',
        detected_at: new Date().toISOString(),
        metadata: { test_category: 'status_open', created_by: createdBy },
      },

      // 2. Fault in 'closed' status - for reopen tests
      {
        id: FAULT_TEST_IDS.FAULT_CLOSED,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_CLOSED_STATUS`,
        fault_code: 'E2E-002',
        description: 'Test fault in CLOSED status for reopen E2E tests',
        status: 'closed',
        severity: 'minor',
        detected_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
        resolved_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
        resolved_by: createdBy,
        metadata: { test_category: 'status_closed', created_by: createdBy },
      },

      // 3. Fault in 'investigating' status - for status transition tests
      {
        id: FAULT_TEST_IDS.FAULT_INVESTIGATING,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_INVESTIGATING_STATUS`,
        fault_code: 'E2E-003',
        description: 'Test fault in INVESTIGATING status for workflow tests',
        status: 'investigating',
        severity: 'major',
        detected_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
        metadata: { test_category: 'status_investigating', created_by: createdBy },
      },

      // 4. Fault with notes - for notes display/add tests
      {
        id: FAULT_TEST_IDS.FAULT_WITH_NOTES,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_WITH_NOTES`,
        fault_code: 'E2E-004',
        description: 'Test fault with attached notes for notes display/add E2E tests',
        status: 'open',
        severity: 'minor',
        detected_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
        metadata: { test_category: 'with_notes', created_by: createdBy },
      },

      // 5. Fault in 'resolved' status - for closed vs resolved distinction
      {
        id: FAULT_TEST_IDS.FAULT_RESOLVED,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_RESOLVED_STATUS`,
        fault_code: 'E2E-005',
        description: 'Test fault in RESOLVED status (different from closed)',
        status: 'resolved',
        severity: 'minor',
        detected_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10 days ago
        resolved_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
        resolved_by: createdBy,
        metadata: { test_category: 'status_resolved', created_by: createdBy },
      },

      // 6. Critical severity fault - for severity filtering/display tests
      {
        id: FAULT_TEST_IDS.FAULT_CRITICAL,
        yacht_id: TEST_YACHT_ID,
        equipment_id: equipmentId,
        title: `${TEST_PREFIX}_CRITICAL_SEVERITY`,
        fault_code: 'E2E-006',
        description: 'Test fault with CRITICAL severity for priority display tests',
        status: 'open',
        severity: 'critical',
        detected_at: new Date().toISOString(),
        metadata: { test_category: 'severity_critical', created_by: createdBy },
      },
    ];

    for (const fault of faultsToCreate) {
      const { data, error } = await client
        .from('pms_faults')
        .upsert(fault, { onConflict: 'id' })
        .select('id, title, status, severity')
        .single();

      if (error) {
        errors.push(`Failed to create fault ${fault.title}: ${error.message}`);
      } else if (data) {
        createdFaults.push({
          id: data.id,
          title: data.title,
          status: data.status,
          severity: data.severity,
          hasNotes: fault.id === FAULT_TEST_IDS.FAULT_WITH_NOTES,
        });
        console.log(`[FAULT-SEED] Created fault: ${data.title} (${data.status})`);
      }
    }

    // ==========================================================================
    // STEP 4: Seed Notes for FAULT_WITH_NOTES
    // ==========================================================================
    console.log('[FAULT-SEED] Seeding fault notes...');

    const notesToCreate = [
      {
        id: FAULT_TEST_IDS.NOTE_FOR_FAULT,
        yacht_id: TEST_YACHT_ID,
        fault_id: FAULT_TEST_IDS.FAULT_WITH_NOTES,
        text: `${TEST_PREFIX}_NOTE_1: Initial investigation notes - observed intermittent behavior`,
        note_type: 'general',
        created_by: createdBy,
        created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(), // 4 days ago
      },
      {
        id: FAULT_TEST_IDS.NOTE_FOR_FAULT_2,
        yacht_id: TEST_YACHT_ID,
        fault_id: FAULT_TEST_IDS.FAULT_WITH_NOTES,
        text: `${TEST_PREFIX}_NOTE_2: Follow-up check - issue persists under load conditions`,
        note_type: 'general',
        created_by: createdBy,
        created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
      },
    ];

    for (const note of notesToCreate) {
      const { data, error } = await client
        .from('pms_notes')
        .upsert(note, { onConflict: 'id' })
        .select('id, fault_id, text')
        .single();

      if (error) {
        errors.push(`Failed to create note: ${error.message}`);
      } else if (data) {
        createdNotes.push({
          id: data.id,
          faultId: data.fault_id,
          text: data.text,
        });
        console.log(`[FAULT-SEED] Created note for fault: ${data.fault_id}`);
      }
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[FAULT-SEED] Seeding complete:', {
      success,
      faultsCreated: createdFaults.length,
      notesCreated: createdNotes.length,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, faults: createdFaults, notes: createdNotes, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, faults: createdFaults, notes: createdNotes, errors };
  }
}

/**
 * Cleanup function - removes all test fault data
 */
export async function cleanupFaultTestData(supabase?: SupabaseClient): Promise<void> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  console.log('[FAULT-SEED] Cleaning up test data...');

  // Delete notes first (FK constraint)
  await client.from('pms_notes').delete().like('text', `${TEST_PREFIX}%`);

  // Delete faults by deterministic IDs
  const faultIds = Object.values(FAULT_TEST_IDS).filter(id => id.startsWith('f4000'));
  for (const id of faultIds) {
    await client.from('pms_faults').delete().eq('id', id);
  }

  // Also cleanup by title prefix
  await client.from('pms_faults').delete().like('title', `${TEST_PREFIX}%`);

  console.log('[FAULT-SEED] Cleanup complete');
}

/**
 * Verify fault test data exists and meets requirements
 */
export async function verifyFaultTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  status: {
    openFault: boolean;
    closedFault: boolean;
    investigatingFault: boolean;
    faultWithNotes: boolean;
    resolvedFault: boolean;
    criticalFault: boolean;
    notesExist: boolean;
  };
  ids: typeof FAULT_TEST_IDS;
}> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  // Check each required fault exists
  const [
    { data: openFault },
    { data: closedFault },
    { data: investigatingFault },
    { data: faultWithNotes },
    { data: resolvedFault },
    { data: criticalFault },
    { count: notesCount },
  ] = await Promise.all([
    client.from('pms_faults').select('id, status').eq('id', FAULT_TEST_IDS.FAULT_OPEN).single(),
    client.from('pms_faults').select('id, status').eq('id', FAULT_TEST_IDS.FAULT_CLOSED).single(),
    client.from('pms_faults').select('id, status').eq('id', FAULT_TEST_IDS.FAULT_INVESTIGATING).single(),
    client.from('pms_faults').select('id, status').eq('id', FAULT_TEST_IDS.FAULT_WITH_NOTES).single(),
    client.from('pms_faults').select('id, status').eq('id', FAULT_TEST_IDS.FAULT_RESOLVED).single(),
    client.from('pms_faults').select('id, status, severity').eq('id', FAULT_TEST_IDS.FAULT_CRITICAL).single(),
    client.from('pms_notes').select('*', { count: 'exact', head: true }).eq('fault_id', FAULT_TEST_IDS.FAULT_WITH_NOTES),
  ]);

  const status = {
    openFault: openFault?.status === 'open',
    closedFault: closedFault?.status === 'closed',
    investigatingFault: investigatingFault?.status === 'investigating',
    faultWithNotes: !!faultWithNotes,
    resolvedFault: resolvedFault?.status === 'resolved',
    criticalFault: criticalFault?.severity === 'critical',
    notesExist: (notesCount || 0) >= 2,
  };

  const valid = Object.values(status).every(v => v === true);

  return { valid, status, ids: FAULT_TEST_IDS };
}

/**
 * Get fault by test ID for use in tests
 */
export function getFaultTestId(key: keyof typeof FAULT_TEST_IDS): string {
  return FAULT_TEST_IDS[key];
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/faults-seed.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedFaultTestData();
      break;
    case 'cleanup':
      await cleanupFaultTestData();
      break;
    case 'verify': {
      const result = await verifyFaultTestData();
      console.log('[FAULT-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Fault Test Fixtures (Task F4)');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/faults-seed.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create fault test data for E2E tests');
      console.log('  cleanup - Remove all fault test data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Known-Good Fault IDs for E2E Tests:');
      console.log('  FAULT_OPEN (for acknowledge/close):', FAULT_TEST_IDS.FAULT_OPEN);
      console.log('  FAULT_CLOSED (for reopen):         ', FAULT_TEST_IDS.FAULT_CLOSED);
      console.log('  FAULT_INVESTIGATING:               ', FAULT_TEST_IDS.FAULT_INVESTIGATING);
      console.log('  FAULT_WITH_NOTES:                  ', FAULT_TEST_IDS.FAULT_WITH_NOTES);
      console.log('  FAULT_RESOLVED:                    ', FAULT_TEST_IDS.FAULT_RESOLVED);
      console.log('  FAULT_CRITICAL:                    ', FAULT_TEST_IDS.FAULT_CRITICAL);
      process.exit(0);
  }
}

// Run CLI if executed directly (ESM compatible)
runCli().catch((err) => {
  console.error('[FAULT-SEED] Error:', err);
  process.exit(1);
});
