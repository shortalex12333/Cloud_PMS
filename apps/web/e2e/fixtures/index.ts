/**
 * E2E Test Fixtures - Centralized exports
 *
 * This module exports all fixture seeding functions for E2E tests.
 */

export {
  seedQuickFilterTestData,
  cleanupQuickFilterTestData,
  verifyQuickFilterTestData,
  type SeedResult,
} from './quick-filters-seed';

export {
  seedFaultTestData,
  cleanupFaultTestData,
  verifyFaultTestData,
  getFaultTestId,
  FAULT_TEST_IDS,
  type FaultSeedResult,
} from './faults-seed';

export {
  // Fixture factories (for use with Playwright fixtures)
  createEquipmentFixture,
  createEquipmentNoteFixture,
  createEquipmentHoursFixture,
  // Query helpers
  getEquipmentByStatus,
  getEquipmentByAttentionFlag,
  getArchivedEquipment,
  // Standalone functions (for use outside Playwright)
  seedEquipmentStandalone,
  seedEquipmentNoteStandalone,
  recordEquipmentHoursStandalone,
  queryEquipmentByStatusStandalone,
  // Types
  type EquipmentStatus,
  type EquipmentCriticality,
  type SeedEquipmentOptions,
  type SeededEquipment,
  type SeedEquipmentNoteOptions,
  type SeededEquipmentNote,
  type RecordEquipmentHoursOptions,
  type SeededEquipmentHours,
} from './equipment-fixtures';

export {
  // Bulk seed/cleanup/verify functions
  seedReceivingTestData,
  cleanupReceivingTestData,
  verifyReceivingTestData,
  getReceivingTestId,
  // Fixture factories (for use with Playwright fixtures)
  createSeedReceivingFixture,
  createSeedLineItemFixture,
  createTransitionStateFixture,
  // Deterministic test IDs
  RECEIVING_TEST_IDS,
  // Types
  type ReceivingStatus,
  type LineItemCondition,
  type ReceivingSeedResult,
  type SeedReceivingParams,
  type SeedLineItemParams,
} from './receiving-fixtures';

export {
  // Bulk seed/cleanup/verify functions
  seedHoRHandoverTestData,
  cleanupHoRHandoverTestData,
  verifyHoRHandoverTestData,
  getHoRTestId,
  // Individual seed functions
  seedHoRRecord,
  seedHoRWarning,
  seedMonthlySignoff,
  seedCrewTemplate,
  seedHandover,
  // Deterministic test IDs
  HOR_TEST_IDS,
  // Types
  type HoRSeedResult,
} from './hor-handover-fixtures';

export {
  // Main seeding functions
  seedPartsTestData,
  cleanupPartsTestData,
  verifyPartsTestData,
  // Individual fixture functions
  seedPart,
  seedShoppingListItem,
  adjustStock,
  getPartWithStock,
  // ID getters
  getPartTestId,
  PARTS_TEST_IDS,
  // Types
  type PartSeedResult,
  type SeedPartOptions,
  type SeedShoppingListItemOptions,
} from './parts-fixtures';

export {
  // Main seeding functions
  seedDocumentTestData,
  cleanupDocumentTestData,
  verifyDocumentTestData,
  // Individual seeders
  seedDocument,
  seedCertificate,
  getCrewMemberId,
  // File upload helpers
  uploadTestFile,
  getDocumentUrl,
  getTestPdfContent,
  getTestImageContent,
  // ID getters
  getDocumentTestId,
  getCertificateActionTestId,
  // Fixture factories (for use with Playwright fixtures)
  createDocumentFixture,
  createCertificateFixture,
  // Constants
  DOCUMENT_TEST_IDS,
  E2E_DOCUMENT_IDS,
  CERTIFICATE_ACTION_TEST_IDS,
  E2E_CERTIFICATE_ACTION_IDS,
  // Types
  type DocumentSeedResult,
  type SeedDocumentOptions,
  type SeedCertificateOptions,
} from './document-fixtures';
