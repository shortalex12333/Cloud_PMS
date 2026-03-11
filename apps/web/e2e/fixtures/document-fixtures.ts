/**
 * Document & Certificate Test Fixtures
 *
 * Creates deterministic test data for Document and Certificate E2E testing.
 * Provides seeding helpers with automatic cleanup for RBAC action tests.
 *
 * IMPORTANT: Uses doc_metadata and pms_certificates tables with known test IDs.
 *
 * Required Test States:
 * 1. Documents with various file types (PDF, image, etc.)
 * 2. Documents linked to equipment
 * 3. Documents linked to certificates
 * 4. Certificates for both vessel and crew
 * 5. Crew members for crew certificate tests
 *
 * Actions that need these fixtures:
 * - delete_document (needs document_id)
 * - update_document (needs document_id)
 * - add_document_tags (needs document_id)
 * - get_document_url (needs document_id)
 * - update_certificate (needs certificate_id)
 * - link_document_to_certificate (needs both IDs)
 * - create_vessel_certificate (creates data)
 * - create_crew_certificate (needs crew_member_id)
 * - supersede_certificate (needs certificate_id)
 *
 * Database Tables:
 * - doc_metadata: id, yacht_id, filename, storage_path, content_type, source, tags, deleted_at
 * - pms_certificates: id, yacht_id, certificate_name, certificate_type, status, expiry_date, equipment_id, document_id
 * - auth_users_profiles: id, yacht_id, name (used for crew_member_id)
 *
 * @see e2e/shard-12-action-coverage/action-coverage-comprehensive.spec.ts
 */

import { createClient } from '@supabase/supabase-js';
// Use any for Supabase client to avoid strict typing issues with untyped database schema
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SupabaseClient = ReturnType<typeof createClient<any>>;

// Configuration
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';
const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test data prefix for identification and cleanup
const TEST_PREFIX = 'DOC_E2E_TEST';
const CERT_TEST_PREFIX = 'CERT_ACTION_E2E';

// =============================================================================
// DETERMINISTIC TEST IDs - USE THESE IN E2E TESTS
// =============================================================================

/**
 * Known document IDs for deterministic E2E testing.
 * These UUIDs are generated once and reused across test runs.
 */
export const DOCUMENT_TEST_IDS = {
  // PDF documents for general testing
  PDF_DOCUMENT_1: 'doc00001-0000-0000-0000-000000000001',
  PDF_DOCUMENT_2: 'doc00002-0000-0000-0000-000000000002',

  // Image documents
  IMAGE_DOCUMENT_1: 'doc00003-0000-0000-0000-000000000003',

  // Document for deletion tests (can be soft-deleted)
  DELETABLE_DOC: 'doc00004-0000-0000-0000-000000000004',

  // Document for update tests
  UPDATABLE_DOC: 'doc00005-0000-0000-0000-000000000005',

  // Document for tagging tests
  TAGGABLE_DOC: 'doc00006-0000-0000-0000-000000000006',

  // Document for certificate linking tests
  CERT_LINKABLE_DOC: 'doc00007-0000-0000-0000-000000000007',

  // Document linked to equipment
  EQUIPMENT_DOC: 'doc00008-0000-0000-0000-000000000008',
} as const;

/**
 * Known certificate IDs for action testing.
 * Separate from the route-testing certificates in certificates-seed.ts.
 */
export const CERTIFICATE_ACTION_TEST_IDS = {
  // Vessel certificate for update tests
  VESSEL_CERT_UPDATABLE: 'cert0001-0000-0000-0000-000000000001',

  // Vessel certificate for document linking
  VESSEL_CERT_LINKABLE: 'cert0002-0000-0000-0000-000000000002',

  // Vessel certificate for superseding tests (old cert)
  VESSEL_CERT_TO_SUPERSEDE: 'cert0003-0000-0000-0000-000000000003',

  // Crew certificate for update tests
  CREW_CERT_UPDATABLE: 'cert0004-0000-0000-0000-000000000004',

  // Certificate that supersedes another
  VESSEL_CERT_NEW: 'cert0005-0000-0000-0000-000000000005',
} as const;

/**
 * Export combined IDs for test files
 */
export const E2E_DOCUMENT_IDS = DOCUMENT_TEST_IDS;
export const E2E_CERTIFICATE_ACTION_IDS = CERTIFICATE_ACTION_TEST_IDS;

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export interface DocumentSeedResult {
  success: boolean;
  stats: {
    documentsCreated: number;
    certificatesCreated: number;
  };
  ids: {
    documents: string[];
    certificates: string[];
    crewMemberId: string | null;
  };
  errors: string[];
}

export interface SeedDocumentOptions {
  /** Custom ID (uses generated if not provided) */
  id?: string;
  /** Filename for the document */
  filename?: string;
  /** MIME type */
  contentType?: string;
  /** Document type classification */
  docType?: string;
  /** Tags array */
  tags?: string[];
  /** Equipment ID to link */
  equipmentId?: string;
  /** Whether this is a test document (adds prefix) */
  isTest?: boolean;
}

export interface SeedCertificateOptions {
  /** Custom ID (uses generated if not provided) */
  id?: string;
  /** Certificate name */
  name?: string;
  /** Certificate type (e.g., 'flag', 'class', 'safety', 'stcw') */
  certificateType?: string;
  /** Status: 'valid', 'expiring_soon', 'expired', 'superseded' */
  status?: 'valid' | 'expiring_soon' | 'expired' | 'superseded';
  /** Days until expiry (negative for expired) */
  expiresInDays?: number;
  /** Equipment ID to link */
  equipmentId?: string;
  /** Document ID to link */
  documentId?: string;
  /** Crew member ID (for crew certificates) */
  crewMemberId?: string;
  /** Is this a vessel or crew certificate */
  isCrewCert?: boolean;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Generate a unique test ID with timestamp
 */
function generateTestId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

/**
 * Date helper: days from now (positive) or ago (negative)
 */
function daysFromNow(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().split('T')[0]; // YYYY-MM-DD format
}

/**
 * Create a minimal test PDF content (base64 encoded)
 * This is a valid 1-page blank PDF for testing file uploads
 */
export function getTestPdfContent(): string {
  // Minimal valid PDF content (blank single page)
  const pdfContent = `%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer << /Size 4 /Root 1 0 R >>
startxref
188
%%EOF`;
  return Buffer.from(pdfContent).toString('base64');
}

/**
 * Create a minimal test PNG image (base64 encoded)
 * This is a 1x1 transparent PNG for testing image uploads
 */
export function getTestImageContent(): string {
  // 1x1 transparent PNG
  const pngBytes = Buffer.from([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, // PNG signature
    0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 dimensions
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, // bit depth, color type, etc.
    0x00, 0x00, 0x00, 0x0a, 0x49, 0x44, 0x41, 0x54, // IDAT chunk
    0x08, 0xd7, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, // compressed data
    0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, // IEND chunk
    0xae, 0x42, 0x60, 0x82,
  ]);
  return pngBytes.toString('base64');
}

// =============================================================================
// SEEDING FUNCTIONS
// =============================================================================

/**
 * Seed a single document for testing
 *
 * @param supabase - Supabase client
 * @param options - Document options
 * @returns Created document data
 */
export async function seedDocument(
  supabase: SupabaseClient,
  options: SeedDocumentOptions = {}
): Promise<{ id: string; filename: string; storagePath: string } | null> {
  const docId = options.id || `doc-${generateTestId('doc')}`;
  const filename = options.filename || `${TEST_PREFIX}_${Date.now()}.pdf`;
  const contentType = options.contentType || 'application/pdf';
  const storagePath = `${YACHT_ID}/documents/${docId}/${filename}`;

  const payload: Record<string, unknown> = {
    id: docId,
    yacht_id: YACHT_ID,
    filename,
    storage_path: storagePath,
    content_type: contentType,
    source: 'e2e_test',
  };

  if (options.docType) {
    payload.doc_type = options.docType;
  }
  if (options.tags) {
    payload.tags = options.tags;
  }
  if (options.equipmentId) {
    payload.equipment_ids = [options.equipmentId];
  }

  const { data, error } = await supabase
    .from('doc_metadata')
    .upsert(payload, { onConflict: 'id' })
    .select('id, filename, storage_path')
    .single();

  if (error || !data) {
    console.error(`[DOC-SEED] Failed to seed document: ${error?.message || 'No data returned'}`);
    return null;
  }

  return {
    id: data.id as string,
    filename: data.filename as string,
    storagePath: data.storage_path as string,
  };
}

/**
 * Seed a single certificate for action testing
 *
 * @param supabase - Supabase client
 * @param options - Certificate options
 * @returns Created certificate data
 */
export async function seedCertificate(
  supabase: SupabaseClient,
  options: SeedCertificateOptions = {}
): Promise<{ id: string; name: string; status: string } | null> {
  const certId = options.id || `cert-${generateTestId('cert')}`;
  const certName = options.name || `${CERT_TEST_PREFIX}_${Date.now()}`;
  const certType = options.certificateType || 'flag';
  const status = options.status || 'valid';
  const expiresInDays = options.expiresInDays ?? 180;

  const payload: Record<string, unknown> = {
    id: certId,
    yacht_id: YACHT_ID,
    certificate_name: certName,
    certificate_type: certType,
    issuing_authority: 'E2E Test Authority',
    certificate_number: `E2E-${Date.now()}`,
    issue_date: daysFromNow(-365), // Issued 1 year ago
    expiry_date: daysFromNow(expiresInDays),
    status,
    notes: 'Auto-generated for E2E action testing',
    metadata: { test: true, source: 'document-fixtures' },
  };

  if (options.equipmentId) {
    payload.equipment_id = options.equipmentId;
  }
  if (options.documentId) {
    payload.document_id = options.documentId;
  }
  if (options.crewMemberId) {
    payload.crew_member_id = options.crewMemberId;
  }

  const { data, error } = await supabase
    .from('pms_certificates')
    .upsert(payload, { onConflict: 'id' })
    .select('id, certificate_name, status')
    .single();

  if (error || !data) {
    console.error(`[DOC-SEED] Failed to seed certificate: ${error?.message || 'No data returned'}`);
    return null;
  }

  return {
    id: data.id as string,
    name: data.certificate_name as string,
    status: data.status as string,
  };
}

/**
 * Get a crew member ID for crew certificate tests
 * Returns an existing crew member from auth_users_profiles
 */
export async function getCrewMemberId(supabase: SupabaseClient): Promise<string | null> {
  const { data, error } = await supabase
    .from('auth_users_profiles')
    .select('id, name')
    .eq('yacht_id', YACHT_ID)
    .limit(1)
    .single();

  if (error || !data) {
    console.warn(`[DOC-SEED] No crew member found: ${error?.message || 'No data'}`);
    return null;
  }

  return data.id as string;
}

/**
 * Upload a test file to storage (for integration tests)
 * Note: This creates actual storage entries - use sparingly
 */
export async function uploadTestFile(
  supabase: SupabaseClient,
  options: {
    bucket?: string;
    path: string;
    content: string;
    contentType?: string;
  }
): Promise<{ path: string; url: string } | null> {
  const bucket = options.bucket || 'documents';
  const contentType = options.contentType || 'application/pdf';

  // Decode base64 content
  const fileBuffer = Buffer.from(options.content, 'base64');

  const { data, error } = await supabase.storage
    .from(bucket)
    .upload(options.path, fileBuffer, {
      contentType,
      upsert: true,
    });

  if (error) {
    console.error(`[DOC-SEED] Failed to upload file: ${error.message}`);
    return null;
  }

  // Get signed URL
  const { data: urlData } = await supabase.storage
    .from(bucket)
    .createSignedUrl(options.path, 3600); // 1 hour expiry

  return {
    path: data.path,
    url: urlData?.signedUrl || '',
  };
}

/**
 * Get a signed URL for a document
 */
export async function getDocumentUrl(
  supabase: SupabaseClient,
  storagePath: string,
  bucket: string = 'documents',
  expiresIn: number = 3600
): Promise<string | null> {
  const { data, error } = await supabase.storage
    .from(bucket)
    .createSignedUrl(storagePath, expiresIn);

  if (error) {
    console.error(`[DOC-SEED] Failed to get signed URL: ${error.message}`);
    return null;
  }

  return data?.signedUrl || null;
}

// =============================================================================
// MAIN SEEDING FUNCTION - Seeds all test data
// =============================================================================

/**
 * Main seeding function - creates all document and certificate test data
 *
 * @param supabase - Optional Supabase client (creates one if not provided)
 * @returns DocumentSeedResult with stats and IDs
 */
export async function seedDocumentTestData(supabase?: SupabaseClient): Promise<DocumentSeedResult> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const errors: string[] = [];
  const stats = {
    documentsCreated: 0,
    certificatesCreated: 0,
  };
  const ids = {
    documents: [] as string[],
    certificates: [] as string[],
    crewMemberId: null as string | null,
  };

  try {
    // ==========================================================================
    // STEP 1: Clean up old test data
    // ==========================================================================
    console.log('[DOC-SEED] Cleaning up old test data...');

    // Delete test documents by prefix
    await client
      .from('doc_metadata')
      .delete()
      .like('filename', `${TEST_PREFIX}_%`);

    // Delete test certificates by prefix
    await client
      .from('pms_certificates')
      .delete()
      .like('certificate_name', `${CERT_TEST_PREFIX}_%`);

    // Delete by deterministic IDs
    const allDocIds = Object.values(DOCUMENT_TEST_IDS);
    for (const id of allDocIds) {
      await client.from('doc_metadata').delete().eq('id', id);
    }

    const allCertIds = Object.values(CERTIFICATE_ACTION_TEST_IDS);
    for (const id of allCertIds) {
      await client.from('pms_certificates').delete().eq('id', id);
    }

    // ==========================================================================
    // STEP 2: Get required references
    // ==========================================================================
    console.log('[DOC-SEED] Fetching required references...');

    // Get a crew member ID for crew certificate tests
    ids.crewMemberId = await getCrewMemberId(client);
    if (ids.crewMemberId) {
      console.log(`[DOC-SEED] Using crew member ID: ${ids.crewMemberId}`);
    } else {
      console.warn('[DOC-SEED] No crew member found - crew certificate tests may fail');
    }

    // Get equipment ID for equipment-linked documents
    const { data: equipment } = await client
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', YACHT_ID)
      .limit(1)
      .single();

    const equipmentId = (equipment?.id as string) || null;
    if (equipmentId) {
      console.log(`[DOC-SEED] Using equipment ID: ${equipmentId}`);
    }

    // ==========================================================================
    // STEP 3: Seed Documents
    // ==========================================================================
    console.log('[DOC-SEED] Seeding documents...');

    const documentsToCreate = [
      // PDF documents for general testing
      {
        id: DOCUMENT_TEST_IDS.PDF_DOCUMENT_1,
        filename: `${TEST_PREFIX}_manual_1.pdf`,
        contentType: 'application/pdf',
        docType: 'manual',
        tags: ['e2e', 'manual'],
      },
      {
        id: DOCUMENT_TEST_IDS.PDF_DOCUMENT_2,
        filename: `${TEST_PREFIX}_specification_2.pdf`,
        contentType: 'application/pdf',
        docType: 'specification',
        tags: ['e2e', 'spec'],
      },

      // Image document
      {
        id: DOCUMENT_TEST_IDS.IMAGE_DOCUMENT_1,
        filename: `${TEST_PREFIX}_photo_1.png`,
        contentType: 'image/png',
        docType: 'photo',
        tags: ['e2e', 'photo'],
      },

      // Document for deletion tests
      {
        id: DOCUMENT_TEST_IDS.DELETABLE_DOC,
        filename: `${TEST_PREFIX}_deletable.pdf`,
        contentType: 'application/pdf',
        docType: 'misc',
        tags: ['e2e', 'deletable'],
      },

      // Document for update tests
      {
        id: DOCUMENT_TEST_IDS.UPDATABLE_DOC,
        filename: `${TEST_PREFIX}_updatable.pdf`,
        contentType: 'application/pdf',
        docType: 'misc',
        tags: ['e2e', 'updatable'],
      },

      // Document for tagging tests
      {
        id: DOCUMENT_TEST_IDS.TAGGABLE_DOC,
        filename: `${TEST_PREFIX}_taggable.pdf`,
        contentType: 'application/pdf',
        docType: 'misc',
        tags: [],
      },

      // Document for certificate linking
      {
        id: DOCUMENT_TEST_IDS.CERT_LINKABLE_DOC,
        filename: `${TEST_PREFIX}_cert_scan.pdf`,
        contentType: 'application/pdf',
        docType: 'certificate_scan',
        tags: ['e2e', 'certificate'],
      },

      // Document linked to equipment
      {
        id: DOCUMENT_TEST_IDS.EQUIPMENT_DOC,
        filename: `${TEST_PREFIX}_equipment_doc.pdf`,
        contentType: 'application/pdf',
        docType: 'equipment_manual',
        tags: ['e2e', 'equipment'],
        equipmentId: equipmentId || undefined,
      },
    ];

    for (const docConfig of documentsToCreate) {
      const result = await seedDocument(client, docConfig);
      if (result) {
        stats.documentsCreated++;
        ids.documents.push(result.id);
      } else {
        errors.push(`Document ${docConfig.filename}: Failed to create`);
      }
    }

    console.log(`[DOC-SEED] Created ${stats.documentsCreated} documents`);

    // ==========================================================================
    // STEP 4: Seed Certificates for Action Testing
    // ==========================================================================
    console.log('[DOC-SEED] Seeding certificates for action testing...');

    const certificatesToCreate = [
      // Vessel certificate for update tests
      {
        id: CERTIFICATE_ACTION_TEST_IDS.VESSEL_CERT_UPDATABLE,
        name: `${CERT_TEST_PREFIX}_Vessel_Updatable`,
        certificateType: 'flag',
        status: 'valid' as const,
        expiresInDays: 180,
      },

      // Vessel certificate for document linking
      {
        id: CERTIFICATE_ACTION_TEST_IDS.VESSEL_CERT_LINKABLE,
        name: `${CERT_TEST_PREFIX}_Vessel_Linkable`,
        certificateType: 'class',
        status: 'valid' as const,
        expiresInDays: 365,
      },

      // Vessel certificate for superseding (old cert to be superseded)
      {
        id: CERTIFICATE_ACTION_TEST_IDS.VESSEL_CERT_TO_SUPERSEDE,
        name: `${CERT_TEST_PREFIX}_Vessel_ToSupersede`,
        certificateType: 'safety',
        status: 'valid' as const,
        expiresInDays: 30, // Expiring soon
      },

      // New certificate that will supersede the old one
      {
        id: CERTIFICATE_ACTION_TEST_IDS.VESSEL_CERT_NEW,
        name: `${CERT_TEST_PREFIX}_Vessel_New`,
        certificateType: 'safety',
        status: 'valid' as const,
        expiresInDays: 365,
      },

      // Crew certificate for update tests
      {
        id: CERTIFICATE_ACTION_TEST_IDS.CREW_CERT_UPDATABLE,
        name: `${CERT_TEST_PREFIX}_Crew_Updatable`,
        certificateType: 'stcw',
        status: 'valid' as const,
        expiresInDays: 180,
        crewMemberId: ids.crewMemberId || undefined,
        isCrewCert: true,
      },
    ];

    for (const certConfig of certificatesToCreate) {
      const result = await seedCertificate(client, certConfig);
      if (result) {
        stats.certificatesCreated++;
        ids.certificates.push(result.id);
      } else {
        errors.push(`Certificate ${certConfig.name}: Failed to create`);
      }
    }

    console.log(`[DOC-SEED] Created ${stats.certificatesCreated} certificates`);

    // ==========================================================================
    // RESULT
    // ==========================================================================
    const success = errors.length === 0;

    console.log('[DOC-SEED] Seeding complete:', {
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
 * Cleanup function - removes all test document and certificate data
 */
export async function cleanupDocumentTestData(supabase?: SupabaseClient): Promise<void> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  console.log('[DOC-SEED] Cleaning up test data...');

  // Delete documents by prefix
  await client.from('doc_metadata').delete().like('filename', `${TEST_PREFIX}_%`);

  // Delete certificates by prefix
  await client.from('pms_certificates').delete().like('certificate_name', `${CERT_TEST_PREFIX}_%`);

  // Delete by deterministic IDs
  const allDocIds = Object.values(DOCUMENT_TEST_IDS);
  for (const id of allDocIds) {
    await client.from('doc_metadata').delete().eq('id', id);
  }

  const allCertIds = Object.values(CERTIFICATE_ACTION_TEST_IDS);
  for (const id of allCertIds) {
    await client.from('pms_certificates').delete().eq('id', id);
  }

  console.log('[DOC-SEED] Cleanup complete');
}

/**
 * Verify test data exists and meets requirements
 */
export async function verifyDocumentTestData(supabase?: SupabaseClient): Promise<{
  valid: boolean;
  counts: {
    documents: number;
    certificates: number;
    hasCrewMember: boolean;
  };
}> {
  const client = supabase || createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });

  const [
    { count: docCount },
    { count: certCount },
  ] = await Promise.all([
    client.from('doc_metadata')
      .select('*', { count: 'exact', head: true })
      .like('filename', `${TEST_PREFIX}_%`),
    client.from('pms_certificates')
      .select('*', { count: 'exact', head: true })
      .like('certificate_name', `${CERT_TEST_PREFIX}_%`),
  ]);

  // Check for crew member
  const crewMemberId = await getCrewMemberId(client);

  const counts = {
    documents: docCount || 0,
    certificates: certCount || 0,
    hasCrewMember: !!crewMemberId,
  };

  // Validate requirements
  const valid =
    counts.documents >= 8 &&
    counts.certificates >= 5 &&
    counts.hasCrewMember;

  return { valid, counts };
}

/**
 * Get document by test ID for use in tests
 */
export function getDocumentTestId(key: keyof typeof DOCUMENT_TEST_IDS): string {
  return DOCUMENT_TEST_IDS[key];
}

/**
 * Get certificate action test ID for use in tests
 */
export function getCertificateActionTestId(key: keyof typeof CERTIFICATE_ACTION_TEST_IDS): string {
  return CERTIFICATE_ACTION_TEST_IDS[key];
}

// =============================================================================
// PLAYWRIGHT FIXTURE HELPERS - For use with rbac-fixtures.ts
// =============================================================================

/**
 * Create a fixture-compatible document seeder with auto-cleanup
 * Use in Playwright test fixtures for automatic cleanup
 */
export function createDocumentFixture(supabase: SupabaseClient) {
  const createdIds: string[] = [];

  const seedDoc = async (options: SeedDocumentOptions = {}) => {
    const result = await seedDocument(supabase, options);
    if (result) {
      createdIds.push(result.id);
    }
    return result;
  };

  const cleanup = async () => {
    for (const id of createdIds) {
      await supabase.from('doc_metadata').delete().eq('id', id);
    }
    createdIds.length = 0;
  };

  return { seedDoc, cleanup, createdIds };
}

/**
 * Create a fixture-compatible certificate seeder with auto-cleanup
 * Use in Playwright test fixtures for automatic cleanup
 */
export function createCertificateFixture(supabase: SupabaseClient) {
  const createdIds: string[] = [];

  const seedCert = async (options: SeedCertificateOptions = {}) => {
    const result = await seedCertificate(supabase, options);
    if (result) {
      createdIds.push(result.id);
    }
    return result;
  };

  const cleanup = async () => {
    for (const id of createdIds) {
      await supabase.from('pms_certificates').delete().eq('id', id);
    }
    createdIds.length = 0;
  };

  return { seedCert, cleanup, createdIds };
}

// =============================================================================
// CLI Support - Run standalone with: npx ts-node e2e/fixtures/document-fixtures.ts
// =============================================================================

async function runCli(): Promise<void> {
  const command = process.argv[2];

  switch (command) {
    case 'seed':
      await seedDocumentTestData();
      break;
    case 'cleanup':
      await cleanupDocumentTestData();
      break;
    case 'verify': {
      const result = await verifyDocumentTestData();
      console.log('[DOC-SEED] Verification result:', JSON.stringify(result, null, 2));
      process.exit(result.valid ? 0 : 1);
    }
    default:
      console.log('Document & Certificate Test Fixtures');
      console.log('');
      console.log('Usage: npx ts-node e2e/fixtures/document-fixtures.ts [seed|cleanup|verify]');
      console.log('');
      console.log('Commands:');
      console.log('  seed    - Create test document and certificate data');
      console.log('  cleanup - Remove all test data');
      console.log('  verify  - Check test data exists and meets requirements');
      console.log('');
      console.log('Test Yacht ID:', YACHT_ID);
      console.log('');
      console.log('Known Document IDs:');
      console.log(JSON.stringify(DOCUMENT_TEST_IDS, null, 2));
      console.log('');
      console.log('Known Certificate Action IDs:');
      console.log(JSON.stringify(CERTIFICATE_ACTION_TEST_IDS, null, 2));
      process.exit(0);
  }
}

// Run CLI if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  runCli().catch((err) => {
    console.error('[DOC-SEED] Error:', err);
    process.exit(1);
  });
}
