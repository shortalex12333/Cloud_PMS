/**
 * Certificate Test Data Seed
 *
 * Creates deterministic test data for Certificate E2E testing.
 * Includes valid, expiring soon, and expired certificates for filter testing.
 *
 * IMPORTANT: Uses pms_certificates table with known test IDs for deterministic testing.
 *
 * Required Test States:
 * 1. Certificates with status 'valid' (not expiring soon)
 * 2. Certificates with status 'expiring_soon' (within 30 days)
 * 3. Certificates with status 'expired' (past expiry date)
 * 4. Certificates linked to equipment (for navigation tests)
 * 5. Certificates for BOTH yachts (isolation testing)
 *
 * Database Table: pms_certificates
 * Schema columns: id, yacht_id, equipment_id, certificate_name, certificate_type,
 *                 issuing_authority, issue_date, expiry_date, status, document_id
 *
 * @see e2e/shard-31-fragmented-routes/route-certificates.spec.ts
 * @see src/lib/filters/catalog.ts for filter definitions
 */

import { createClient } from '@supabase/supabase-js';
type SupabaseClient = ReturnType<typeof createClient>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

// Test yacht IDs - Yacht A is primary test tenant, Yacht B is for isolation testing
const YACHT_A_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const YACHT_B_ID = process.env.TEST_YACHT_ID_B || 'b5fe1119-b04c-41ac-80f1-829d23322599'; // Isolation test yacht

// Test data prefix for identification and cleanup
const TEST_PREFIX = 'CERT_E2E_TEST';

// =============================================================================
// DETERMINISTIC TEST CERTIFICATE IDs - USE THESE IN E2E TESTS
// =============================================================================
/**
 * Known certificate IDs for deterministic E2E testing.
 * Yacht A certificates for primary testing, Yacht B for isolation verification.
 */
export const CERTIFICATE_TEST_IDS = {
  // Yacht A - Valid certificates (not expiring within 30 days)
  YACHT_A_VALID_1: 'c4e00001-0000-0000-0000-000000000001',
  YACHT_A_VALID_2: 'c4e00002-0000-0000-0000-000000000002',

  // Yacht A - Expiring soon certificates (within 30 days)
  YACHT_A_EXPIRING_1: 'c4e00003-0000-0000-0000-000000000003',
  YACHT_A_EXPIRING_2: 'c4e00004-0000-0000-0000-000000000004',

  // Yacht A - Expired certificates
  YACHT_A_EXPIRED_1: 'c4e00005-0000-0000-0000-000000000005',
  YACHT_A_EXPIRED_2: 'c4e00006-0000-0000-0000-000000000006',

  // Yacht A - Certificate with linked equipment (for navigation tests)
  YACHT_A_WITH_EQUIPMENT: 'c4e00007-0000-0000-0000-000000000007',

  // Yacht A - Superseded certificate (historical)
  YACHT_A_SUPERSEDED: 'c4e00008-0000-0000-0000-000000000008',

  // Yacht B - Isolation test certificates (should NOT appear in Yacht A queries)
  YACHT_B_VALID_1: 'c4e00b01-0000-0000-0000-000000000001',
  YACHT_B_EXPIRING_1: 'c4e00b02-0000-0000-0000-000000000002',
  YACHT_B_EXPIRED_1: 'c4e00b03-0000-0000-0000-000000000003',
} as const;

/**
 * Export IDs for use in test files
 */
export const E2E_CERTIFICATE_IDS = CERTIFICATE_TEST_IDS;

/**
 * Certificate status values from DB schema
 */
export type CertificateStatus = 'valid' | 'expiring_soon' | 'expired' | 'superseded';

/**
 * Date helpers
 */
function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0]; // YYYY-MM-DD format
}

function daysAgo(days: number): string {
  return daysFromNow(-days);
}

/**
 * Seed result with stats
 */
export interface CertificateSeedResult {
  success: boolean;
  stats: {
    yachtACertificatesCreated: number;
    yachtBCertificatesCreated: number;
    totalCreated: number;
  };
  ids: {
    yachtA: string[];
    yachtB: string[];
  };
  errors: string[];
}

/**
 * Main seeding function - creates deterministic test certificate data
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns CertificateSeedResult with stats and IDs
 */
export async function seedCertificateTestData(supabase?: SupabaseClient): Promise<CertificateSeedResult> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const errors: string[] = [];
  const stats = {
    yachtACertificatesCreated: 0,
    yachtBCertificatesCreated: 0,
    totalCreated: 0,
  };
  const ids = {
    yachtA: [] as string[],
    yachtB: [] as string[],
  };

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[CERT-SEED] Cleaning up old test data...');

    // Delete test certificates by prefix
    await client
      .from('pms_certificates')
      .delete()
      .like('certificate_name', `${TEST_PREFIX}_%`);

    // Also delete by deterministic IDs
    const allTestIds = Object.values(CERTIFICATE_TEST_IDS);
    for (const id of allTestIds) {
      await client.from('pms_certificates').delete().eq('id', id);
    }

    // ==========================================================================
    // STEP 2: Get required foreign key references for Yacht A
    // ==========================================================================
    console.log('[CERT-SEED] Fetching required references for Yacht A...');

    // Get a valid equipment ID for Yacht A (for linked certificate tests)
    const { data: equipmentA, error: equipErrorA } = await client
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', YACHT_A_ID)
      .limit(1)
      .single();

    let equipmentIdA: string | null = null;
    if (equipErrorA || !equipmentA) {
      console.warn(`[CERT-SEED] Warning: No equipment found for Yacht A: ${equipErrorA?.message || 'No data'}`);
    } else {
      equipmentIdA = (equipmentA as { id: string; name: string }).id;
      console.log(`[CERT-SEED] Using equipment for Yacht A: ${(equipmentA as { id: string; name: string }).name}`);
    }

    // ==========================================================================
    // STEP 3: Seed Yacht A Certificates
    // ==========================================================================
    console.log('[CERT-SEED] Seeding Yacht A certificates...');

    const yachtACertificates = [
      // VALID certificates (expiring beyond 30 days)
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_VALID_1,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_VALID_1_Safety_Equipment`,
        certificate_type: 'safety_equipment',
        issuing_authority: 'MCA',
        certificate_number: 'E2E-MCA-001',
        issue_date: daysAgo(365), // Issued 1 year ago
        expiry_date: daysFromNow(180), // Expires in 6 months
        status: 'valid' as CertificateStatus,
        notes: 'Test valid certificate #1 for E2E testing',
        metadata: { test: true, category: 'valid' },
      },
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_VALID_2,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_VALID_2_Radio_License`,
        certificate_type: 'radio_license',
        issuing_authority: 'ITU',
        certificate_number: 'E2E-ITU-001',
        issue_date: daysAgo(180), // Issued 6 months ago
        expiry_date: daysFromNow(365), // Expires in 1 year
        status: 'valid' as CertificateStatus,
        notes: 'Test valid certificate #2 for E2E testing',
        metadata: { test: true, category: 'valid' },
      },

      // EXPIRING SOON certificates (within 30 days)
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_EXPIRING_1,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_EXPIRING_1_Fire_Safety`,
        certificate_type: 'fire_safety',
        issuing_authority: 'Lloyd\'s Register',
        certificate_number: 'E2E-LR-001',
        issue_date: daysAgo(335), // Issued almost a year ago
        expiry_date: daysFromNow(15), // Expires in 15 days
        status: 'expiring_soon' as CertificateStatus,
        notes: 'Test expiring certificate #1 - expires in 15 days',
        metadata: { test: true, category: 'expiring_soon' },
      },
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_EXPIRING_2,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_EXPIRING_2_Navigation_Equipment`,
        certificate_type: 'navigation_equipment',
        issuing_authority: 'DNV',
        certificate_number: 'E2E-DNV-001',
        issue_date: daysAgo(350),
        expiry_date: daysFromNow(7), // Expires in 7 days
        status: 'expiring_soon' as CertificateStatus,
        notes: 'Test expiring certificate #2 - expires in 7 days (urgent)',
        metadata: { test: true, category: 'expiring_soon', urgent: true },
      },

      // EXPIRED certificates
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_EXPIRED_1,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_EXPIRED_1_Liferaft`,
        certificate_type: 'liferaft_service',
        issuing_authority: 'Viking',
        certificate_number: 'E2E-VIK-001',
        issue_date: daysAgo(730), // Issued 2 years ago
        expiry_date: daysAgo(30), // Expired 30 days ago
        status: 'expired' as CertificateStatus,
        notes: 'Test expired certificate #1 - expired 30 days ago',
        metadata: { test: true, category: 'expired' },
      },
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_EXPIRED_2,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_EXPIRED_2_EPIRB`,
        certificate_type: 'epirb_registration',
        issuing_authority: 'NOAA',
        certificate_number: 'E2E-NOAA-001',
        issue_date: daysAgo(400),
        expiry_date: daysAgo(5), // Expired 5 days ago (recent)
        status: 'expired' as CertificateStatus,
        notes: 'Test expired certificate #2 - recently expired',
        metadata: { test: true, category: 'expired', recent_expiry: true },
      },

      // Certificate WITH LINKED EQUIPMENT (for navigation tests)
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_WITH_EQUIPMENT,
        yacht_id: YACHT_A_ID,
        equipment_id: equipmentIdA, // Linked to equipment
        certificate_name: `${TEST_PREFIX}_WITH_EQUIPMENT_Engine`,
        certificate_type: 'engine_certification',
        issuing_authority: 'MTU',
        certificate_number: 'E2E-MTU-001',
        issue_date: daysAgo(180),
        expiry_date: daysFromNow(180),
        status: 'valid' as CertificateStatus,
        notes: 'Test certificate linked to equipment - for navigation tests',
        metadata: { test: true, category: 'with_equipment', has_equipment_link: true },
      },

      // SUPERSEDED certificate (historical, should be excluded from active filters)
      {
        id: CERTIFICATE_TEST_IDS.YACHT_A_SUPERSEDED,
        yacht_id: YACHT_A_ID,
        certificate_name: `${TEST_PREFIX}_SUPERSEDED_Old_Safety`,
        certificate_type: 'safety_equipment',
        issuing_authority: 'MCA',
        certificate_number: 'E2E-MCA-OLD-001',
        issue_date: daysAgo(730), // Issued 2 years ago
        expiry_date: daysAgo(365), // Would have expired 1 year ago
        status: 'superseded' as CertificateStatus,
        notes: 'Test superseded certificate - replaced by newer version',
        metadata: { test: true, category: 'superseded', replaced_by: CERTIFICATE_TEST_IDS.YACHT_A_VALID_1 },
      },
    ];

    for (const cert of yachtACertificates) {
      const { data, error } = await client
        .from('pms_certificates')
        .upsert(cert, { onConflict: 'id' })
        .select('id')
        .single();

      if (error) {
        errors.push(`Yacht A Certificate ${cert.certificate_name}: ${error.message}`);
      } else {
        stats.yachtACertificatesCreated++;
        ids.yachtA.push(data.id);
      }
    }

    console.log(`[CERT-SEED] Created ${stats.yachtACertificatesCreated} Yacht A certificates`);

    // ==========================================================================
    // STEP 4: Seed Yacht B Certificates (Isolation Testing)
    // ==========================================================================
    console.log('[CERT-SEED] Seeding Yacht B certificates for isolation testing...');

    // Check if Yacht B exists in the database
    const { data: yachtB, error: yachtBError } = await client
      .from('yachts')
      .select('id')
      .eq('id', YACHT_B_ID)
      .single();

    if (yachtBError || !yachtB) {
      console.warn(`[CERT-SEED] Warning: Yacht B (${YACHT_B_ID}) not found - skipping isolation fixtures`);
      console.warn('  To enable isolation testing, create Yacht B or set TEST_YACHT_ID_B env var');
    } else {
      const yachtBCertificates = [
        // Yacht B - Valid certificate
        {
          id: CERTIFICATE_TEST_IDS.YACHT_B_VALID_1,
          yacht_id: YACHT_B_ID,
          certificate_name: `${TEST_PREFIX}_B_VALID_Safety`,
          certificate_type: 'safety_equipment',
          issuing_authority: 'MCA',
          certificate_number: 'E2E-MCA-B-001',
          issue_date: daysAgo(200),
          expiry_date: daysFromNow(165),
          status: 'valid' as CertificateStatus,
          notes: 'Yacht B test certificate - should NOT appear in Yacht A queries',
          metadata: { test: true, category: 'isolation_test', yacht: 'B' },
        },

        // Yacht B - Expiring certificate
        {
          id: CERTIFICATE_TEST_IDS.YACHT_B_EXPIRING_1,
          yacht_id: YACHT_B_ID,
          certificate_name: `${TEST_PREFIX}_B_EXPIRING_Radio`,
          certificate_type: 'radio_license',
          issuing_authority: 'ITU',
          certificate_number: 'E2E-ITU-B-001',
          issue_date: daysAgo(340),
          expiry_date: daysFromNow(20),
          status: 'expiring_soon' as CertificateStatus,
          notes: 'Yacht B expiring certificate - for isolation verification',
          metadata: { test: true, category: 'isolation_test', yacht: 'B' },
        },

        // Yacht B - Expired certificate
        {
          id: CERTIFICATE_TEST_IDS.YACHT_B_EXPIRED_1,
          yacht_id: YACHT_B_ID,
          certificate_name: `${TEST_PREFIX}_B_EXPIRED_Fire`,
          certificate_type: 'fire_safety',
          issuing_authority: 'Lloyd\'s Register',
          certificate_number: 'E2E-LR-B-001',
          issue_date: daysAgo(500),
          expiry_date: daysAgo(15),
          status: 'expired' as CertificateStatus,
          notes: 'Yacht B expired certificate - for isolation verification',
          metadata: { test: true, category: 'isolation_test', yacht: 'B' },
        },
      ];

      for (const cert of yachtBCertificates) {
        const { data, error } = await client
          .from('pms_certificates')
          .upsert(cert, { onConflict: 'id' })
          .select('id')
          .single();

        if (error) {
          errors.push(`Yacht B Certificate ${cert.certificate_name}: ${error.message}`);
        } else {
          stats.yachtBCertificatesCreated++;
          ids.yachtB.push(data.id);
        }
      }

      console.log(`[CERT-SEED] Created ${stats.yachtBCertificatesCreated} Yacht B certificates`);
    }

    // ==========================================================================
    // RESULT
    // ==========================================================================
    stats.totalCreated = stats.yachtACertificatesCreated + stats.yachtBCertificatesCreated;
    const success = errors.length === 0;

    console.log('[CERT-SEED] Seeding complete:', {
      success,
      stats,
      errors: errors.length > 0 ? errors : 'none',
    });

    return { success, stats, ids, errors };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(`Unexpected error: ${message}`);
    return { success: false, stats, ids, errors };
  }
}

/**
 * Cleanup function - removes all test certificate data
 */
export async function cleanupCertificateTestData(supabase?: SupabaseClient): Promise<void> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  console.log('[CERT-SEED] Cleaning up test data...');

  // Delete by prefix
  await client.from('pms_certificates').delete().like('certificate_name', `${TEST_PREFIX}_%`);

  // Delete by deterministic IDs
  const allTestIds = Object.values(CERTIFICATE_TEST_IDS);
  for (const id of allTestIds) {
    await client.from('pms_certificates').delete().eq('id', id);
  }

  console.log('[CERT-SEED] Cleanup complete');
}

/**
 * Verify test certificate data exists and meets requirements
 */
export async function verifyCertificateTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  counts: {
    yachtA: {
      valid: number;
      expiringSoon: number;
      expired: number;
      superseded: number;
      withEquipment: number;
    };
    yachtB: {
      total: number;
    };
  };
  isolationTest: {
    passed: boolean;
    details: string;
  };
}> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  // Count Yacht A certificates by status
  const [
    { count: validA },
    { count: expiringSoonA },
    { count: expiredA },
    { count: supersededA },
    { count: withEquipmentA },
    { count: totalB },
  ] = await Promise.all([
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_A_ID)
      .eq('status', 'valid'),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_A_ID)
      .eq('status', 'expiring_soon'),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_A_ID)
      .eq('status', 'expired'),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_A_ID)
      .eq('status', 'superseded'),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_A_ID)
      .not('equipment_id', 'is', null),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${TEST_PREFIX}_%`)
      .eq('yacht_id', YACHT_B_ID),
  ]);

  const counts = {
    yachtA: {
      valid: validA || 0,
      expiringSoon: expiringSoonA || 0,
      expired: expiredA || 0,
      superseded: supersededA || 0,
      withEquipment: withEquipmentA || 0,
    },
    yachtB: {
      total: totalB || 0,
    },
  };

  // Isolation test: Yacht B certificates should NOT appear in Yacht A queries
  const { data: leakedCerts } = await client
    .from('pms_certificates')
    .select('id, yacht_id')
    .like('certificate_name', `${TEST_PREFIX}_B_%`)
    .eq('yacht_id', YACHT_A_ID);

  const isolationPassed = !leakedCerts || leakedCerts.length === 0;

  // Validate requirements
  const valid =
    counts.yachtA.valid >= 2 &&
    counts.yachtA.expiringSoon >= 2 &&
    counts.yachtA.expired >= 2 &&
    counts.yachtA.withEquipment >= 1 &&
    isolationPassed;

  return {
    valid,
    counts,
    isolationTest: {
      passed: isolationPassed,
      details: isolationPassed
        ? 'No Yacht B certificates leaked to Yacht A'
        : `ISOLATION FAILURE: ${leakedCerts?.length} Yacht B certs found in Yacht A`,
    },
  };
}

/**
 * Get certificate by test ID for use in tests
 */
export function getCertificateTestId(key: keyof typeof CERTIFICATE_TEST_IDS): string {
  return CERTIFICATE_TEST_IDS[key];
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/certificates-seed.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedCertificateTestData();
      break;
    case 'cleanup':
      await cleanupCertificateTestData();
      break;
    case 'verify': {
      const result = await verifyCertificateTestData();
      console.log('[CERT-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Certificate Test Fixtures');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/certificates-seed.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create test certificate data');
      console.log('  cleanup - Remove all test certificate data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Test Yacht IDs:');
      console.log(`  Yacht A (primary): ${YACHT_A_ID}`);
      console.log(`  Yacht B (isolation): ${YACHT_B_ID}`);
      console.log('');
      console.log('Known Certificate IDs:');
      console.log(JSON.stringify(CERTIFICATE_TEST_IDS, null, 2));
      process.exit(0);
  }
}

// Run CLI if executed directly (ESM compatible)
runCli().catch((err) => {
  console.error('[CERT-SEED] Error:', err);
  process.exit(1);
});
