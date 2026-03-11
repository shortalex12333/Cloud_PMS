/**
 * Hours of Rest (HoR) and Handover Test Fixtures
 *
 * Creates deterministic test data for HoR and Handover E2E testing.
 * Follows the pattern established in rbac-fixtures.ts and faults-seed.ts.
 *
 * Required Test Data:
 * 1. HoR records in various states (compliant, non-compliant)
 * 2. HoR warnings (active, dismissed, acknowledged)
 * 3. Monthly signoffs in various states (draft, pending, finalized)
 * 4. Crew schedule templates
 * 5. Handover records (with/without signatures)
 *
 * Actions that need these fixtures:
 * - verify_hours_of_rest (needs record_id)
 * - add_rest_period (needs record_id)
 * - dismiss_warning (needs warning_id)
 * - acknowledge_warning (needs warning_id)
 * - sign_monthly_signoff (needs signoff_id)
 * - create_crew_template (creates data)
 * - view_compliance_status (needs yacht context)
 * - apply_crew_template (needs template_id)
 * - acknowledge_handover (needs handover_id)
 * - sign_handover_outgoing (needs handover_id)
 * - sign_handover_incoming (needs handover_id with outgoing signature)
 * - export_handover (needs complete handover)
 *
 * @see e2e/shard-31-fragmented-routes/route-hours-of-rest.spec.ts
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for easy identification and cleanup
const TEST_PREFIX = 'E2E_HOR_TEST';

/**
 * Deterministic Test IDs
 * These UUIDs are fixed for E2E tests to allow deterministic assertions.
 */
export const HOR_TEST_IDS = {
  // HoR Records
  HOR_RECORD_COMPLIANT: 'hor00001-0001-4000-a000-000000000001',
  HOR_RECORD_NON_COMPLIANT: 'hor00002-0002-4000-a000-000000000002',
  HOR_RECORD_EDITABLE: 'hor00003-0003-4000-a000-000000000003',

  // HoR Warnings
  WARNING_ACTIVE: 'wrn00001-0001-4000-b000-000000000001',
  WARNING_DISMISSED: 'wrn00002-0002-4000-b000-000000000002',
  WARNING_ACKNOWLEDGED: 'wrn00003-0003-4000-b000-000000000003',
  WARNING_CRITICAL: 'wrn00004-0004-4000-b000-000000000004',

  // Monthly Signoffs
  SIGNOFF_DRAFT: 'sgn00001-0001-4000-c000-000000000001',
  SIGNOFF_PENDING_HOD: 'sgn00002-0002-4000-c000-000000000002',
  SIGNOFF_PENDING_MASTER: 'sgn00003-0003-4000-c000-000000000003',
  SIGNOFF_FINALIZED: 'sgn00004-0004-4000-c000-000000000004',

  // Crew Templates
  TEMPLATE_DEFAULT: 'tpl00001-0001-4000-d000-000000000001',
  TEMPLATE_CUSTOM: 'tpl00002-0002-4000-d000-000000000002',

  // Handover Records
  HANDOVER_NO_SIGNATURE: 'hnd00001-0001-4000-e000-000000000001',
  HANDOVER_OUTGOING_SIGNED: 'hnd00002-0002-4000-e000-000000000002',
  HANDOVER_FULLY_SIGNED: 'hnd00003-0003-4000-e000-000000000003',
  HANDOVER_FOR_EXPORT: 'hnd00004-0004-4000-e000-000000000004',

  // Test Users (from seed data)
  USER_CAPTAIN: 'b72c35ff-e309-4a19-a617-bfc706a78c0f',
  USER_CHIEF_ENG: '89b1262c-ff59-4591-b954-757cdf3d609d',
  USER_DECKHAND: '00000000-0000-4000-a000-000000000001',
} as const;

/**
 * Seed result interface
 */
export interface HoRSeedResult {
  success: boolean;
  horRecords: Array<{ id: string; user_id: string; record_date: string; is_compliant: boolean }>;
  warnings: Array<{ id: string; warning_type: string; status: string; severity: string }>;
  signoffs: Array<{ id: string; year_month: string; status: string }>;
  templates: Array<{ id: string; template_name: string; is_default: boolean }>;
  handovers: Array<{ id: string; entity_type: string; has_signatures: boolean }>;
  errors: string[];
}

/**
 * Create Supabase client
 */
function getClient(supabase?: SupabaseClient): SupabaseClient {
  return supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

/**
 * Seed an Hours of Rest record
 */
export async function seedHoRRecord(
  supabase?: SupabaseClient,
  options: {
    id?: string;
    userId?: string;
    recordDate?: string;
    isCompliant?: boolean;
    restPeriods?: Array<{ start: string; end: string }>;
  } = {}
): Promise<{ id: string; user_id: string; record_date: string; is_compliant: boolean } | null> {
  const client = getClient(supabase);

  const userId = options.userId || HOR_TEST_IDS.USER_DECKHAND;
  const recordDate = options.recordDate || new Date().toISOString().split('T')[0];
  const isCompliant = options.isCompliant ?? true;

  // Default rest periods: compliant (10h) or non-compliant (8h)
  const restPeriods = options.restPeriods || (isCompliant
    ? [{ start: '22:00', end: '06:00' }, { start: '13:00', end: '15:00' }] // 10h
    : [{ start: '23:00', end: '06:00' }, { start: '14:00', end: '15:00' }]  // 8h
  );

  const totalRest = isCompliant ? 10.0 : 8.0;

  const { data, error } = await client
    .from('pms_hours_of_rest')
    .upsert({
      id: options.id,
      yacht_id: TEST_YACHT_ID,
      user_id: userId,
      record_date: recordDate,
      rest_periods: restPeriods,
      total_rest_hours: totalRest,
      is_daily_compliant: isCompliant,
      is_weekly_compliant: true,
      notes: `${TEST_PREFIX}: ${isCompliant ? 'Compliant' : 'Non-compliant'} test record`,
    }, { onConflict: 'id' })
    .select('id, user_id, record_date, is_daily_compliant')
    .single();

  if (error) {
    console.error(`[HOR-SEED] Failed to seed HoR record: ${error.message}`);
    return null;
  }

  return {
    id: data.id,
    user_id: data.user_id,
    record_date: data.record_date,
    is_compliant: data.is_daily_compliant,
  };
}

/**
 * Seed an HoR Warning
 */
export async function seedHoRWarning(
  supabase?: SupabaseClient,
  options: {
    id?: string;
    userId?: string;
    warningType?: 'DAILY_REST' | 'WEEKLY_REST' | 'CONSECUTIVE_DAYS';
    status?: 'active' | 'dismissed' | 'acknowledged';
    severity?: 'low' | 'medium' | 'high' | 'critical';
    recordDate?: string;
  } = {}
): Promise<{ id: string; warning_type: string; status: string; severity: string } | null> {
  const client = getClient(supabase);

  const userId = options.userId || HOR_TEST_IDS.USER_DECKHAND;
  const warningType = options.warningType || 'DAILY_REST';
  const status = options.status || 'active';
  const severity = options.severity || 'medium';
  const recordDate = options.recordDate || new Date().toISOString().split('T')[0];

  const { data, error } = await client
    .from('pms_crew_hours_warnings')
    .upsert({
      id: options.id,
      yacht_id: TEST_YACHT_ID,
      user_id: userId,
      warning_type: warningType,
      severity,
      status,
      record_date: recordDate,
      violation_details: {
        required_hours: 10,
        actual_hours: severity === 'high' ? 6 : 8,
        shortfall: severity === 'high' ? 4 : 2,
      },
      message: `${TEST_PREFIX}: ${warningType} violation - ${severity} severity`,
    }, { onConflict: 'id' })
    .select('id, warning_type, status, severity')
    .single();

  if (error) {
    console.error(`[HOR-SEED] Failed to seed warning: ${error.message}`);
    return null;
  }

  return data;
}

/**
 * Seed a Monthly Signoff
 */
export async function seedMonthlySignoff(
  supabase?: SupabaseClient,
  options: {
    id?: string;
    userId?: string;
    yearMonth?: string;
    status?: 'draft' | 'pending_hod' | 'pending_master' | 'finalized';
    crewSignature?: object | null;
    hodSignature?: object | null;
    masterSignature?: object | null;
  } = {}
): Promise<{ id: string; year_month: string; status: string } | null> {
  const client = getClient(supabase);

  const userId = options.userId || HOR_TEST_IDS.USER_DECKHAND;
  const yearMonth = options.yearMonth || new Date().toISOString().slice(0, 7);
  const status = options.status || 'draft';

  const insertData: Record<string, unknown> = {
    id: options.id,
    yacht_id: TEST_YACHT_ID,
    user_id: userId,
    year_month: yearMonth,
    status,
  };

  if (options.crewSignature) {
    insertData.crew_signature = options.crewSignature;
  }
  if (options.hodSignature) {
    insertData.hod_signature = options.hodSignature;
  }
  if (options.masterSignature) {
    insertData.master_signature = options.masterSignature;
  }

  const { data, error } = await client
    .from('pms_hor_monthly_signoffs')
    .upsert(insertData, { onConflict: 'id' })
    .select('id, year_month, status')
    .single();

  if (error) {
    console.error(`[HOR-SEED] Failed to seed monthly signoff: ${error.message}`);
    return null;
  }

  return data;
}

/**
 * Seed a Crew Schedule Template
 */
export async function seedCrewTemplate(
  supabase?: SupabaseClient,
  options: {
    id?: string;
    templateName?: string;
    description?: string;
    isDefault?: boolean;
    scheduleTemplate?: object;
  } = {}
): Promise<{ id: string; template_name: string; is_default: boolean } | null> {
  const client = getClient(supabase);

  const templateName = options.templateName || `${TEST_PREFIX}_TEMPLATE`;
  const isDefault = options.isDefault ?? false;

  // Default 4-on/8-off schedule
  const scheduleTemplate = options.scheduleTemplate || {
    monday: [
      { start: '00:00', end: '04:00', type: 'work' },
      { start: '04:00', end: '12:00', type: 'rest' },
      { start: '12:00', end: '16:00', type: 'work' },
      { start: '16:00', end: '00:00', type: 'rest' },
    ],
    tuesday: [
      { start: '00:00', end: '04:00', type: 'work' },
      { start: '04:00', end: '12:00', type: 'rest' },
      { start: '12:00', end: '16:00', type: 'work' },
      { start: '16:00', end: '00:00', type: 'rest' },
    ],
    wednesday: [
      { start: '00:00', end: '04:00', type: 'work' },
      { start: '04:00', end: '12:00', type: 'rest' },
      { start: '12:00', end: '16:00', type: 'work' },
      { start: '16:00', end: '00:00', type: 'rest' },
    ],
    thursday: [
      { start: '00:00', end: '04:00', type: 'work' },
      { start: '04:00', end: '12:00', type: 'rest' },
      { start: '12:00', end: '16:00', type: 'work' },
      { start: '16:00', end: '00:00', type: 'rest' },
    ],
    friday: [
      { start: '00:00', end: '04:00', type: 'work' },
      { start: '04:00', end: '12:00', type: 'rest' },
      { start: '12:00', end: '16:00', type: 'work' },
      { start: '16:00', end: '00:00', type: 'rest' },
    ],
    saturday: [
      { start: '08:00', end: '12:00', type: 'work' },
    ],
    sunday: [],
  };

  const { data, error } = await client
    .from('pms_crew_normal_hours')
    .upsert({
      id: options.id,
      yacht_id: TEST_YACHT_ID,
      template_name: templateName,
      description: options.description || `${TEST_PREFIX} schedule template`,
      schedule_template: scheduleTemplate,
      is_default: isDefault,
    }, { onConflict: 'id' })
    .select('id, template_name, is_default')
    .single();

  if (error) {
    console.error(`[HOR-SEED] Failed to seed crew template: ${error.message}`);
    return null;
  }

  return data;
}

/**
 * Seed a Handover record
 */
export async function seedHandover(
  supabase?: SupabaseClient,
  options: {
    id?: string;
    entityType?: 'work_order' | 'fault' | 'equipment' | 'note';
    entityId?: string | null;
    summaryText?: string;
    category?: 'urgent' | 'in_progress' | 'completed' | 'watch' | 'fyi';
    priority?: number;
    addedBy?: string;
    outgoingSignature?: object | null;
    incomingSignature?: object | null;
  } = {}
): Promise<{ id: string; entity_type: string; has_signatures: boolean } | null> {
  const client = getClient(supabase);

  const entityType = options.entityType || 'note';
  const category = options.category || 'fyi';
  const priority = options.priority ?? 0;
  const addedBy = options.addedBy || HOR_TEST_IDS.USER_CAPTAIN;

  const insertData: Record<string, unknown> = {
    id: options.id,
    yacht_id: TEST_YACHT_ID,
    entity_type: entityType,
    entity_id: options.entityId,
    summary_text: options.summaryText || `${TEST_PREFIX}: Handover note for E2E testing`,
    category,
    priority,
    added_by: addedBy,
    added_at: new Date().toISOString(),
  };

  // Add signatures to metadata if provided
  if (options.outgoingSignature || options.incomingSignature) {
    insertData.metadata = {
      outgoing_signature: options.outgoingSignature || null,
      incoming_signature: options.incomingSignature || null,
    };
  }

  const { data, error } = await client
    .from('pms_handover')
    .upsert(insertData, { onConflict: 'id' })
    .select('id, entity_type, metadata')
    .single();

  if (error) {
    console.error(`[HOR-SEED] Failed to seed handover: ${error.message}`);
    return null;
  }

  const metadata = data.metadata as Record<string, unknown> || {};
  const hasSignatures = !!(metadata.outgoing_signature || metadata.incoming_signature);

  return {
    id: data.id,
    entity_type: data.entity_type,
    has_signatures: hasSignatures,
  };
}

/**
 * Main seeding function - creates all deterministic test data
 */
export async function seedHoRHandoverTestData(supabase?: SupabaseClient): Promise<HoRSeedResult> {
  const client = getClient(supabase);

  const errors: string[] = [];
  const horRecords: HoRSeedResult['horRecords'] = [];
  const warnings: HoRSeedResult['warnings'] = [];
  const signoffs: HoRSeedResult['signoffs'] = [];
  const templates: HoRSeedResult['templates'] = [];
  const handovers: HoRSeedResult['handovers'] = [];

  console.log('[HOR-SEED] Starting HoR and Handover test data seeding...');

  // ============================================================================
  // STEP 1: Clean up old test data
  // ============================================================================
  console.log('[HOR-SEED] Cleaning up old test data...');

  // Clean up in order of FK dependencies
  await client.from('pms_handover').delete().like('summary_text', `${TEST_PREFIX}%`);
  await client.from('pms_hor_monthly_signoffs').delete().in('id', [
    HOR_TEST_IDS.SIGNOFF_DRAFT,
    HOR_TEST_IDS.SIGNOFF_PENDING_HOD,
    HOR_TEST_IDS.SIGNOFF_PENDING_MASTER,
    HOR_TEST_IDS.SIGNOFF_FINALIZED,
  ]);
  await client.from('pms_crew_hours_warnings').delete().in('id', [
    HOR_TEST_IDS.WARNING_ACTIVE,
    HOR_TEST_IDS.WARNING_DISMISSED,
    HOR_TEST_IDS.WARNING_ACKNOWLEDGED,
    HOR_TEST_IDS.WARNING_CRITICAL,
  ]);
  await client.from('pms_hours_of_rest').delete().in('id', [
    HOR_TEST_IDS.HOR_RECORD_COMPLIANT,
    HOR_TEST_IDS.HOR_RECORD_NON_COMPLIANT,
    HOR_TEST_IDS.HOR_RECORD_EDITABLE,
  ]);
  await client.from('pms_crew_normal_hours').delete().in('id', [
    HOR_TEST_IDS.TEMPLATE_DEFAULT,
    HOR_TEST_IDS.TEMPLATE_CUSTOM,
  ]);

  // ============================================================================
  // STEP 2: Seed HoR Records
  // ============================================================================
  console.log('[HOR-SEED] Seeding HoR records...');

  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  // Compliant record
  const compliantRecord = await seedHoRRecord(client, {
    id: HOR_TEST_IDS.HOR_RECORD_COMPLIANT,
    userId: HOR_TEST_IDS.USER_DECKHAND,
    recordDate: yesterday.toISOString().split('T')[0],
    isCompliant: true,
  });
  if (compliantRecord) {
    horRecords.push(compliantRecord);
  } else {
    errors.push('Failed to create compliant HoR record');
  }

  // Non-compliant record
  const nonCompliantRecord = await seedHoRRecord(client, {
    id: HOR_TEST_IDS.HOR_RECORD_NON_COMPLIANT,
    userId: HOR_TEST_IDS.USER_DECKHAND,
    recordDate: new Date(today.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    isCompliant: false,
  });
  if (nonCompliantRecord) {
    horRecords.push(nonCompliantRecord);
  } else {
    errors.push('Failed to create non-compliant HoR record');
  }

  // Editable record (today)
  const editableRecord = await seedHoRRecord(client, {
    id: HOR_TEST_IDS.HOR_RECORD_EDITABLE,
    userId: HOR_TEST_IDS.USER_DECKHAND,
    recordDate: today.toISOString().split('T')[0],
    isCompliant: true,
  });
  if (editableRecord) {
    horRecords.push(editableRecord);
  } else {
    errors.push('Failed to create editable HoR record');
  }

  // ============================================================================
  // STEP 3: Seed HoR Warnings
  // ============================================================================
  console.log('[HOR-SEED] Seeding HoR warnings...');

  const warningsToCreate = [
    { id: HOR_TEST_IDS.WARNING_ACTIVE, status: 'active' as const, severity: 'medium' as const },
    { id: HOR_TEST_IDS.WARNING_DISMISSED, status: 'dismissed' as const, severity: 'low' as const },
    { id: HOR_TEST_IDS.WARNING_ACKNOWLEDGED, status: 'acknowledged' as const, severity: 'medium' as const },
    { id: HOR_TEST_IDS.WARNING_CRITICAL, status: 'active' as const, severity: 'high' as const },
  ];

  for (const warn of warningsToCreate) {
    const warning = await seedHoRWarning(client, warn);
    if (warning) {
      warnings.push(warning);
    } else {
      errors.push(`Failed to create warning: ${warn.id}`);
    }
  }

  // ============================================================================
  // STEP 4: Seed Monthly Signoffs
  // ============================================================================
  console.log('[HOR-SEED] Seeding monthly signoffs...');

  const currentMonth = today.toISOString().slice(0, 7);
  const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    .toISOString().slice(0, 7);

  // Draft signoff (current month)
  const draftSignoff = await seedMonthlySignoff(client, {
    id: HOR_TEST_IDS.SIGNOFF_DRAFT,
    yearMonth: currentMonth,
    status: 'draft',
  });
  if (draftSignoff) signoffs.push(draftSignoff);
  else errors.push('Failed to create draft signoff');

  // Pending HOD signoff (current month, crew signed)
  const pendingHodSignoff = await seedMonthlySignoff(client, {
    id: HOR_TEST_IDS.SIGNOFF_PENDING_HOD,
    yearMonth: currentMonth,
    userId: HOR_TEST_IDS.USER_CHIEF_ENG,
    status: 'pending_hod',
    crewSignature: {
      signed_at: new Date().toISOString(),
      ip_address: '192.168.1.100',
    },
  });
  if (pendingHodSignoff) signoffs.push(pendingHodSignoff);
  else errors.push('Failed to create pending HOD signoff');

  // Pending Master signoff (last month, crew + HOD signed)
  const pendingMasterSignoff = await seedMonthlySignoff(client, {
    id: HOR_TEST_IDS.SIGNOFF_PENDING_MASTER,
    yearMonth: lastMonth,
    status: 'pending_master',
    crewSignature: {
      signed_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      ip_address: '192.168.1.100',
    },
    hodSignature: {
      signed_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      signed_by: HOR_TEST_IDS.USER_CHIEF_ENG,
      ip_address: '192.168.1.101',
    },
  });
  if (pendingMasterSignoff) signoffs.push(pendingMasterSignoff);
  else errors.push('Failed to create pending master signoff');

  // Finalized signoff (last month)
  const finalizedSignoff = await seedMonthlySignoff(client, {
    id: HOR_TEST_IDS.SIGNOFF_FINALIZED,
    yearMonth: lastMonth,
    userId: HOR_TEST_IDS.USER_CAPTAIN,
    status: 'finalized',
    crewSignature: {
      signed_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      ip_address: '192.168.1.100',
    },
    hodSignature: {
      signed_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
      signed_by: HOR_TEST_IDS.USER_CHIEF_ENG,
      ip_address: '192.168.1.101',
    },
    masterSignature: {
      signed_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      signed_by: HOR_TEST_IDS.USER_CAPTAIN,
      ip_address: '192.168.1.102',
    },
  });
  if (finalizedSignoff) signoffs.push(finalizedSignoff);
  else errors.push('Failed to create finalized signoff');

  // ============================================================================
  // STEP 5: Seed Crew Templates
  // ============================================================================
  console.log('[HOR-SEED] Seeding crew templates...');

  const defaultTemplate = await seedCrewTemplate(client, {
    id: HOR_TEST_IDS.TEMPLATE_DEFAULT,
    templateName: `${TEST_PREFIX}_DEFAULT`,
    description: 'E2E Test Default Template',
    isDefault: false, // Don't override real defaults
  });
  if (defaultTemplate) templates.push(defaultTemplate);
  else errors.push('Failed to create default template');

  const customTemplate = await seedCrewTemplate(client, {
    id: HOR_TEST_IDS.TEMPLATE_CUSTOM,
    templateName: `${TEST_PREFIX}_CUSTOM`,
    description: 'E2E Test Custom Schedule',
    isDefault: false,
    scheduleTemplate: {
      monday: [{ start: '08:00', end: '18:00', type: 'work' }],
      tuesday: [{ start: '08:00', end: '18:00', type: 'work' }],
      wednesday: [{ start: '08:00', end: '18:00', type: 'work' }],
      thursday: [{ start: '08:00', end: '18:00', type: 'work' }],
      friday: [{ start: '08:00', end: '18:00', type: 'work' }],
      saturday: [],
      sunday: [],
    },
  });
  if (customTemplate) templates.push(customTemplate);
  else errors.push('Failed to create custom template');

  // ============================================================================
  // STEP 6: Seed Handover Records
  // ============================================================================
  console.log('[HOR-SEED] Seeding handover records...');

  // Handover with no signatures
  const noSigHandover = await seedHandover(client, {
    id: HOR_TEST_IDS.HANDOVER_NO_SIGNATURE,
    entityType: 'note',
    summaryText: `${TEST_PREFIX}: Unsigned handover note for testing`,
    category: 'fyi',
    priority: 1,
  });
  if (noSigHandover) handovers.push(noSigHandover);
  else errors.push('Failed to create unsigned handover');

  // Handover with outgoing signature only
  const outgoingSigHandover = await seedHandover(client, {
    id: HOR_TEST_IDS.HANDOVER_OUTGOING_SIGNED,
    entityType: 'note',
    summaryText: `${TEST_PREFIX}: Handover with outgoing signature`,
    category: 'in_progress',
    priority: 2,
    outgoingSignature: {
      signed_at: new Date().toISOString(),
      signed_by: HOR_TEST_IDS.USER_CHIEF_ENG,
      ip_address: '192.168.1.100',
    },
  });
  if (outgoingSigHandover) handovers.push(outgoingSigHandover);
  else errors.push('Failed to create outgoing-signed handover');

  // Fully signed handover
  const fullySigHandover = await seedHandover(client, {
    id: HOR_TEST_IDS.HANDOVER_FULLY_SIGNED,
    entityType: 'note',
    summaryText: `${TEST_PREFIX}: Fully signed handover note`,
    category: 'completed',
    priority: 3,
    outgoingSignature: {
      signed_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      signed_by: HOR_TEST_IDS.USER_CHIEF_ENG,
      ip_address: '192.168.1.100',
    },
    incomingSignature: {
      signed_at: new Date().toISOString(),
      signed_by: HOR_TEST_IDS.USER_DECKHAND,
      ip_address: '192.168.1.101',
    },
  });
  if (fullySigHandover) handovers.push(fullySigHandover);
  else errors.push('Failed to create fully-signed handover');

  // Handover for export testing
  const exportHandover = await seedHandover(client, {
    id: HOR_TEST_IDS.HANDOVER_FOR_EXPORT,
    entityType: 'note',
    summaryText: `${TEST_PREFIX}: Handover note ready for export`,
    category: 'urgent',
    priority: 5,
    outgoingSignature: {
      signed_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      signed_by: HOR_TEST_IDS.USER_CAPTAIN,
      ip_address: '192.168.1.102',
    },
    incomingSignature: {
      signed_at: new Date().toISOString(),
      signed_by: HOR_TEST_IDS.USER_CHIEF_ENG,
      ip_address: '192.168.1.100',
    },
  });
  if (exportHandover) handovers.push(exportHandover);
  else errors.push('Failed to create export handover');

  // ============================================================================
  // RESULT
  // ============================================================================
  const success = errors.length === 0;

  console.log('[HOR-SEED] Seeding complete:', {
    success,
    horRecords: horRecords.length,
    warnings: warnings.length,
    signoffs: signoffs.length,
    templates: templates.length,
    handovers: handovers.length,
    errors: errors.length > 0 ? errors : 'none',
  });

  return { success, horRecords, warnings, signoffs, templates, handovers, errors };
}

/**
 * Cleanup function - removes all HoR/Handover test data
 */
export async function cleanupHoRHandoverTestData(supabase?: SupabaseClient): Promise<void> {
  const client = getClient(supabase);

  console.log('[HOR-SEED] Cleaning up HoR and Handover test data...');

  // Clean up in order of FK dependencies
  await client.from('pms_handover').delete().like('summary_text', `${TEST_PREFIX}%`);
  await client.from('pms_crew_hours_warnings').delete().like('message', `${TEST_PREFIX}%`);
  await client.from('pms_hours_of_rest').delete().like('notes', `${TEST_PREFIX}%`);
  await client.from('pms_crew_normal_hours').delete().like('template_name', `${TEST_PREFIX}%`);

  // Clean by deterministic IDs
  await client.from('pms_hor_monthly_signoffs').delete().in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('sgn')));
  await client.from('pms_handover').delete().in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('hnd')));
  await client.from('pms_crew_hours_warnings').delete().in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('wrn')));
  await client.from('pms_hours_of_rest').delete().in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('hor')));
  await client.from('pms_crew_normal_hours').delete().in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('tpl')));

  console.log('[HOR-SEED] Cleanup complete');
}

/**
 * Verify test data exists and meets requirements
 */
export async function verifyHoRHandoverTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  status: {
    horRecords: boolean;
    warnings: boolean;
    signoffs: boolean;
    templates: boolean;
    handovers: boolean;
  };
  counts: {
    horRecords: number;
    warnings: number;
    signoffs: number;
    templates: number;
    handovers: number;
  };
  ids: typeof HOR_TEST_IDS;
}> {
  const client = getClient(supabase);

  const [
    { count: horCount },
    { count: warningsCount },
    { count: signoffsCount },
    { count: templatesCount },
    { count: handoversCount },
  ] = await Promise.all([
    client.from('pms_hours_of_rest').select('*', { count: 'exact', head: true }).like('notes', `${TEST_PREFIX}%`),
    client.from('pms_crew_hours_warnings').select('*', { count: 'exact', head: true }).like('message', `${TEST_PREFIX}%`),
    client.from('pms_hor_monthly_signoffs').select('*', { count: 'exact', head: true }).in('id', Object.values(HOR_TEST_IDS).filter(id => id.startsWith('sgn'))),
    client.from('pms_crew_normal_hours').select('*', { count: 'exact', head: true }).like('template_name', `${TEST_PREFIX}%`),
    client.from('pms_handover').select('*', { count: 'exact', head: true }).like('summary_text', `${TEST_PREFIX}%`),
  ]);

  const counts = {
    horRecords: horCount || 0,
    warnings: warningsCount || 0,
    signoffs: signoffsCount || 0,
    templates: templatesCount || 0,
    handovers: handoversCount || 0,
  };

  const status = {
    horRecords: counts.horRecords >= 3,
    warnings: counts.warnings >= 4,
    signoffs: counts.signoffs >= 4,
    templates: counts.templates >= 2,
    handovers: counts.handovers >= 4,
  };

  const valid = Object.values(status).every(v => v === true);

  return { valid, status, counts, ids: HOR_TEST_IDS };
}

/**
 * Get test ID helper
 */
export function getHoRTestId(key: keyof typeof HOR_TEST_IDS): string {
  return HOR_TEST_IDS[key];
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/hor-handover-fixtures.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedHoRHandoverTestData();
      break;
    case 'cleanup':
      await cleanupHoRHandoverTestData();
      break;
    case 'verify': {
      const result = await verifyHoRHandoverTestData();
      console.log('[HOR-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('HoR and Handover Test Fixtures');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/hor-handover-fixtures.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create HoR and Handover test data for E2E tests');
      console.log('  cleanup - Remove all HoR/Handover test data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Known-Good IDs for E2E Tests:');
      console.log('');
      console.log('HoR Records:');
      console.log('  HOR_RECORD_COMPLIANT:     ', HOR_TEST_IDS.HOR_RECORD_COMPLIANT);
      console.log('  HOR_RECORD_NON_COMPLIANT: ', HOR_TEST_IDS.HOR_RECORD_NON_COMPLIANT);
      console.log('  HOR_RECORD_EDITABLE:      ', HOR_TEST_IDS.HOR_RECORD_EDITABLE);
      console.log('');
      console.log('Warnings:');
      console.log('  WARNING_ACTIVE:           ', HOR_TEST_IDS.WARNING_ACTIVE);
      console.log('  WARNING_DISMISSED:        ', HOR_TEST_IDS.WARNING_DISMISSED);
      console.log('  WARNING_ACKNOWLEDGED:     ', HOR_TEST_IDS.WARNING_ACKNOWLEDGED);
      console.log('  WARNING_CRITICAL:         ', HOR_TEST_IDS.WARNING_CRITICAL);
      console.log('');
      console.log('Monthly Signoffs:');
      console.log('  SIGNOFF_DRAFT:            ', HOR_TEST_IDS.SIGNOFF_DRAFT);
      console.log('  SIGNOFF_PENDING_HOD:      ', HOR_TEST_IDS.SIGNOFF_PENDING_HOD);
      console.log('  SIGNOFF_PENDING_MASTER:   ', HOR_TEST_IDS.SIGNOFF_PENDING_MASTER);
      console.log('  SIGNOFF_FINALIZED:        ', HOR_TEST_IDS.SIGNOFF_FINALIZED);
      console.log('');
      console.log('Crew Templates:');
      console.log('  TEMPLATE_DEFAULT:         ', HOR_TEST_IDS.TEMPLATE_DEFAULT);
      console.log('  TEMPLATE_CUSTOM:          ', HOR_TEST_IDS.TEMPLATE_CUSTOM);
      console.log('');
      console.log('Handovers:');
      console.log('  HANDOVER_NO_SIGNATURE:    ', HOR_TEST_IDS.HANDOVER_NO_SIGNATURE);
      console.log('  HANDOVER_OUTGOING_SIGNED: ', HOR_TEST_IDS.HANDOVER_OUTGOING_SIGNED);
      console.log('  HANDOVER_FULLY_SIGNED:    ', HOR_TEST_IDS.HANDOVER_FULLY_SIGNED);
      console.log('  HANDOVER_FOR_EXPORT:      ', HOR_TEST_IDS.HANDOVER_FOR_EXPORT);
      process.exit(0);
  }
}

// Run CLI if executed directly
runCli().catch((err) => {
  console.error('[HOR-SEED] Error:', err);
  process.exit(1);
});
