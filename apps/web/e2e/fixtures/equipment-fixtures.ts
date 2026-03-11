/**
 * Equipment Test Fixtures for RBAC E2E Testing
 *
 * Provides fixture functions for seeding and cleaning up equipment-related
 * test data during E2E tests. Follows the pattern established in rbac-fixtures.ts.
 *
 * LAW 29: MUTATION ISOLATION - Fresh data per test, no state bleed
 * - Each fixture tracks created IDs
 * - Auto-cleanup in afterAll
 * - Unique identifiers per test run
 *
 * Available Fixtures:
 * - seedEquipment: Creates equipment with auto-cleanup
 * - seedEquipmentNote: Creates note on equipment
 * - recordEquipmentHours: Records hours reading
 * - getEquipmentByStatus: Query equipment by operational status
 *
 * Usage in tests:
 * ```typescript
 * test('should update equipment status', async ({ seedEquipment, executeAction }) => {
 *   const equipment = await seedEquipment({ status: 'operational' });
 *   // ... test logic
 *   // Equipment auto-cleaned up after test
 * });
 * ```
 *
 * @see e2e/rbac-fixtures.ts for the extended test fixture
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Configuration - matches rbac-fixtures.ts
const RBAC_CONFIG = {
  yachtId: process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598',
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co',
  supabaseServiceKey: process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY',
};

/**
 * Equipment status values from DB schema
 */
export type EquipmentStatus = 'operational' | 'degraded' | 'failed' | 'maintenance' | 'decommissioned';

/**
 * Equipment criticality levels
 */
export type EquipmentCriticality = 'critical' | 'high' | 'medium' | 'low';

/**
 * Options for seeding equipment
 */
export interface SeedEquipmentOptions {
  name?: string;
  status?: EquipmentStatus;
  criticality?: EquipmentCriticality;
  attentionFlag?: boolean;
  attentionReason?: string;
  location?: string;
  manufacturer?: string;
  model?: string;
  serialNumber?: string;
  systemType?: string;
  archived?: boolean;
}

/**
 * Seeded equipment entity
 */
export interface SeededEquipment {
  id: string;
  name: string;
  status: EquipmentStatus;
  code: string;
  attention_flag: boolean;
  archived: boolean;
}

/**
 * Options for seeding equipment note
 */
export interface SeedEquipmentNoteOptions {
  noteText?: string;
  noteType?: 'general' | 'progress' | 'issue' | 'resolution';
}

/**
 * Seeded equipment note entity
 */
export interface SeededEquipmentNote {
  id: string;
  equipment_id: string;
  note_text: string;
}

/**
 * Options for recording equipment hours
 */
export interface RecordEquipmentHoursOptions {
  hours: number;
  readingDate?: Date;
  notes?: string;
}

/**
 * Seeded equipment hours reading
 */
export interface SeededEquipmentHours {
  id: string;
  equipment_id: string;
  hours: number;
  reading_date: string;
}

/**
 * Generate unique test ID (LAW 29: MUTATION ISOLATION)
 */
function generateTestId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

/**
 * Create a Supabase admin client
 */
function createAdminClient(): SupabaseClient {
  return createClient(
    RBAC_CONFIG.supabaseUrl,
    RBAC_CONFIG.supabaseServiceKey,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    }
  );
}

/**
 * Equipment fixture factory - creates seedEquipment function with auto-cleanup
 *
 * Pattern from rbac-fixtures.ts:
 * 1. Track created IDs
 * 2. Insert with yacht_id filter
 * 3. Auto-cleanup in afterAll
 * 4. Return the created entity
 *
 * @param supabaseAdmin - Supabase service-role client
 * @returns Tuple of [seedFunction, cleanupFunction]
 */
export function createEquipmentFixture(supabaseAdmin: SupabaseClient): [
  (options?: SeedEquipmentOptions) => Promise<SeededEquipment>,
  () => Promise<void>
] {
  const createdIds: string[] = [];

  const seedEquipment = async (options: SeedEquipmentOptions = {}): Promise<SeededEquipment> => {
    const testId = generateTestId('eq');
    const name = options.name || `Test Equipment ${testId}`;
    const code = `EQ-TEST-${Date.now()}`;

    const { data, error } = await supabaseAdmin
      .from('pms_equipment')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        name,
        code,
        description: 'Auto-generated test equipment for RBAC testing',
        status: options.status || 'operational',
        criticality: options.criticality || 'medium',
        attention_flag: options.attentionFlag || false,
        attention_reason: options.attentionReason || null,
        location: options.location || 'Test Location',
        manufacturer: options.manufacturer || 'Test Manufacturer',
        model: options.model || 'Test Model',
        serial_number: options.serialNumber || `SN-${testId}`,
        system_type: options.systemType || 'mechanical',
        archived: options.archived || false,
        metadata: { test: true, created_by: 'e2e-fixture' },
      })
      .select('id, name, status, code, attention_flag, archived')
      .single();

    if (error) {
      throw new Error(`Failed to seed equipment: ${error.message}`);
    }

    createdIds.push(data.id);
    return data as SeededEquipment;
  };

  const cleanup = async (): Promise<void> => {
    if (createdIds.length > 0) {
      // Delete related records first (FK constraints)
      // Delete faults linked to this equipment
      await supabaseAdmin
        .from('pms_faults')
        .delete()
        .in('equipment_id', createdIds);

      // Delete audit log entries for this equipment (notes, hours, etc.)
      await supabaseAdmin
        .from('pms_audit_log')
        .delete()
        .in('entity_id', createdIds)
        .eq('entity_type', 'equipment');

      // Delete the equipment
      await supabaseAdmin
        .from('pms_equipment')
        .delete()
        .in('id', createdIds);
    }
  };

  return [seedEquipment, cleanup];
}

/**
 * Equipment note fixture factory - creates seedEquipmentNote function with auto-cleanup
 *
 * NOTE: Equipment notes are stored in the pms_audit_log table via the add_equipment_note action.
 * This fixture creates an audit log entry directly for testing purposes.
 * For actual note creation, use the action API endpoint.
 *
 * @param supabaseAdmin - Supabase service-role client
 * @returns Tuple of [seedFunction, cleanupFunction]
 */
export function createEquipmentNoteFixture(supabaseAdmin: SupabaseClient): [
  (equipmentId: string, options?: SeedEquipmentNoteOptions) => Promise<SeededEquipmentNote>,
  () => Promise<void>
] {
  const createdIds: string[] = [];

  const seedEquipmentNote = async (
    equipmentId: string,
    options: SeedEquipmentNoteOptions = {}
  ): Promise<SeededEquipmentNote> => {
    const testId = generateTestId('eqnote');
    const noteText = options.noteText || `Test note ${testId}`;

    // Get a valid user ID for user_id field
    const { data: userProfile } = await supabaseAdmin
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    const userId = userProfile?.id || '00000000-0000-0000-0000-000000000000';

    // Equipment notes are stored in the audit log table
    const { data, error } = await supabaseAdmin
      .from('pms_audit_log')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        action: 'add_equipment_note',
        entity_type: 'equipment',
        entity_id: equipmentId,
        user_id: userId,
        signature: { user_id: userId, timestamp: new Date().toISOString(), ip_address: '127.0.0.1' },
        old_values: null,
        new_values: {
          note_text: noteText,
          note_type: options.noteType || 'general',
        },
        metadata: { test: true, created_by: 'e2e-fixture' },
      })
      .select('id')
      .single();

    if (error) {
      throw new Error(`Failed to seed equipment note: ${error.message}`);
    }

    createdIds.push(data.id);
    return {
      id: data.id,
      equipment_id: equipmentId,
      note_text: noteText,
    };
  };

  const cleanup = async (): Promise<void> => {
    if (createdIds.length > 0) {
      await supabaseAdmin
        .from('pms_audit_log')
        .delete()
        .in('id', createdIds);
    }
  };

  return [seedEquipmentNote, cleanup];
}

/**
 * Equipment hours fixture factory - creates recordEquipmentHours function with auto-cleanup
 *
 * NOTE: Equipment hours readings are stored in the pms_audit_log table via the record_equipment_hours action.
 * This fixture creates an audit log entry directly for testing purposes.
 * For actual hours recording, use the action API endpoint.
 *
 * @param supabaseAdmin - Supabase service-role client
 * @returns Tuple of [recordFunction, cleanupFunction]
 */
export function createEquipmentHoursFixture(supabaseAdmin: SupabaseClient): [
  (equipmentId: string, options: RecordEquipmentHoursOptions) => Promise<SeededEquipmentHours>,
  () => Promise<void>
] {
  const createdIds: string[] = [];

  const recordEquipmentHours = async (
    equipmentId: string,
    options: RecordEquipmentHoursOptions
  ): Promise<SeededEquipmentHours> => {
    // Get a valid user ID for user_id field
    const { data: userProfile } = await supabaseAdmin
      .from('auth_users_profiles')
      .select('id')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    const userId = userProfile?.id || '00000000-0000-0000-0000-000000000000';
    const readingDate = options.readingDate || new Date();
    const readingDateStr = readingDate.toISOString().split('T')[0];

    // Equipment hours are stored in the audit log table
    const { data, error } = await supabaseAdmin
      .from('pms_audit_log')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        action: 'record_equipment_hours',
        entity_type: 'equipment',
        entity_id: equipmentId,
        user_id: userId,
        signature: { user_id: userId, timestamp: new Date().toISOString(), ip_address: '127.0.0.1' },
        old_values: null,
        new_values: {
          reading: options.hours,
          reading_date: readingDateStr,
          notes: options.notes || null,
        },
        metadata: { test: true, created_by: 'e2e-fixture' },
      })
      .select('id')
      .single();

    if (error) {
      throw new Error(`Failed to record equipment hours: ${error.message}`);
    }

    createdIds.push(data.id);
    return {
      id: data.id,
      equipment_id: equipmentId,
      hours: options.hours,
      reading_date: readingDateStr,
    };
  };

  const cleanup = async (): Promise<void> => {
    if (createdIds.length > 0) {
      await supabaseAdmin
        .from('pms_audit_log')
        .delete()
        .in('id', createdIds);
    }
  };

  return [recordEquipmentHours, cleanup];
}

/**
 * Get equipment by operational status
 *
 * Queries existing equipment filtered by status. Useful for tests that need
 * equipment in a specific state without creating new records.
 *
 * @param supabaseAdmin - Supabase service-role client
 * @param status - Equipment status to filter by
 * @param limit - Maximum number of results (default: 1)
 * @returns Array of equipment matching the status
 */
export async function getEquipmentByStatus(
  supabaseAdmin: SupabaseClient,
  status: EquipmentStatus,
  limit: number = 1
): Promise<SeededEquipment[]> {
  const { data, error } = await supabaseAdmin
    .from('pms_equipment')
    .select('id, name, status, code, attention_flag, archived')
    .eq('yacht_id', RBAC_CONFIG.yachtId)
    .eq('status', status)
    .eq('archived', false)
    .limit(limit);

  if (error) {
    throw new Error(`Failed to get equipment by status: ${error.message}`);
  }

  return (data || []) as SeededEquipment[];
}

/**
 * Get equipment with attention flag
 *
 * @param supabaseAdmin - Supabase service-role client
 * @param flagged - Whether to get flagged (true) or non-flagged (false) equipment
 * @param limit - Maximum number of results (default: 1)
 * @returns Array of equipment matching the attention flag state
 */
export async function getEquipmentByAttentionFlag(
  supabaseAdmin: SupabaseClient,
  flagged: boolean = true,
  limit: number = 1
): Promise<SeededEquipment[]> {
  const { data, error } = await supabaseAdmin
    .from('pms_equipment')
    .select('id, name, status, code, attention_flag, archived')
    .eq('yacht_id', RBAC_CONFIG.yachtId)
    .eq('attention_flag', flagged)
    .eq('archived', false)
    .limit(limit);

  if (error) {
    throw new Error(`Failed to get equipment by attention flag: ${error.message}`);
  }

  return (data || []) as SeededEquipment[];
}

/**
 * Get archived equipment
 *
 * @param supabaseAdmin - Supabase service-role client
 * @param limit - Maximum number of results (default: 1)
 * @returns Array of archived equipment
 */
export async function getArchivedEquipment(
  supabaseAdmin: SupabaseClient,
  limit: number = 1
): Promise<SeededEquipment[]> {
  const { data, error } = await supabaseAdmin
    .from('pms_equipment')
    .select('id, name, status, code, attention_flag, archived')
    .eq('yacht_id', RBAC_CONFIG.yachtId)
    .eq('archived', true)
    .limit(limit);

  if (error) {
    throw new Error(`Failed to get archived equipment: ${error.message}`);
  }

  return (data || []) as SeededEquipment[];
}

// =============================================================================
// STANDALONE USAGE - For running outside of Playwright fixtures
// =============================================================================

/**
 * Standalone seed function for use outside Playwright
 *
 * Creates equipment and returns cleanup function.
 * Use when you need to seed data before tests start.
 *
 * @example
 * ```typescript
 * const { equipment, cleanup } = await seedEquipmentStandalone({ status: 'degraded' });
 * // ... use equipment.id in tests
 * await cleanup(); // Clean up when done
 * ```
 */
export async function seedEquipmentStandalone(
  options: SeedEquipmentOptions = {}
): Promise<{ equipment: SeededEquipment; cleanup: () => Promise<void> }> {
  const client = createAdminClient();
  const [seedEquipment, cleanup] = createEquipmentFixture(client);
  const equipment = await seedEquipment(options);
  return { equipment, cleanup };
}

/**
 * Standalone seed function for equipment notes
 */
export async function seedEquipmentNoteStandalone(
  equipmentId: string,
  options: SeedEquipmentNoteOptions = {}
): Promise<{ note: SeededEquipmentNote; cleanup: () => Promise<void> }> {
  const client = createAdminClient();
  const [seedEquipmentNote, cleanup] = createEquipmentNoteFixture(client);
  const note = await seedEquipmentNote(equipmentId, options);
  return { note, cleanup };
}

/**
 * Standalone function for recording equipment hours
 */
export async function recordEquipmentHoursStandalone(
  equipmentId: string,
  options: RecordEquipmentHoursOptions
): Promise<{ reading: SeededEquipmentHours; cleanup: () => Promise<void> }> {
  const client = createAdminClient();
  const [recordHours, cleanup] = createEquipmentHoursFixture(client);
  const reading = await recordHours(equipmentId, options);
  return { reading, cleanup };
}

/**
 * Standalone query for equipment by status
 */
export async function queryEquipmentByStatusStandalone(
  status: EquipmentStatus,
  limit: number = 1
): Promise<SeededEquipment[]> {
  const client = createAdminClient();
  return getEquipmentByStatus(client, status, limit);
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/equipment-fixtures.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];
  const arg = process.argv[3];

  switch (command) {
    case 'seed': {
      const status = (arg as EquipmentStatus) || 'operational';
      console.log(`[EQ-FIXTURE] Seeding equipment with status: ${status}`);
      const { equipment, cleanup } = await seedEquipmentStandalone({ status });
      console.log(`[EQ-FIXTURE] Created equipment: ${JSON.stringify(equipment, null, 2)}`);
      console.log('[EQ-FIXTURE] Run "cleanup" command to remove');
      break;
    }
    case 'query': {
      const status = (arg as EquipmentStatus) || 'operational';
      console.log(`[EQ-FIXTURE] Querying equipment with status: ${status}`);
      const equipment = await queryEquipmentByStatusStandalone(status, 5);
      console.log(`[EQ-FIXTURE] Found ${equipment.length} equipment:`);
      console.log(JSON.stringify(equipment, null, 2));
      break;
    }
    default:
      console.log('Usage: npx ts-node e2e/fixtures/equipment-fixtures.ts [seed|query] [status]');
      console.log('');
      console.log('Commands:');
      console.log('  seed [status]  - Create test equipment with given status');
      console.log('  query [status] - Find existing equipment by status');
      console.log('');
      console.log('Status values: operational, degraded, failed, maintenance, decommissioned');
      process.exit(0);
  }
}

// Run CLI if executed directly
if (require.main === module) {
  runCli().catch((err) => {
    console.error('[EQ-FIXTURE] Error:', err);
    process.exit(1);
  });
}
