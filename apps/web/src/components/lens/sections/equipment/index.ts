/**
 * Equipment Lens Section Components
 *
 * All section containers for the Equipment lens.
 * Each section uses SectionContainer for sticky header behavior via IntersectionObserver.
 */

export {
  SpecificationsSection,
  type SpecificationsSectionProps,
  type EquipmentSpecification,
} from './SpecificationsSection';

export {
  MaintenanceHistorySection,
  type MaintenanceHistorySectionProps,
  type MaintenanceHistoryEntry,
} from './MaintenanceHistorySection';

export {
  LinkedFaultsSection,
  type LinkedFaultsSectionProps,
  type LinkedFault,
} from './LinkedFaultsSection';

export {
  LinkedWorkOrdersSection,
  type LinkedWorkOrdersSectionProps,
  type LinkedWorkOrder,
} from './LinkedWorkOrdersSection';

export {
  DocumentsSection,
  type DocumentsSectionProps,
  type EquipmentDocument,
} from './DocumentsSection';

export {
  HoursLogSection,
  type HoursLogSectionProps,
  type HoursLogEntry,
} from './HoursLogSection';

export {
  StatusHistorySection,
  type StatusHistorySectionProps,
  type StatusHistoryEntry,
  type EquipmentStatus as StatusHistoryEquipmentStatus,
} from './StatusHistorySection';

export {
  EquipmentDocumentsSection,
  type EquipmentDocumentsSectionProps,
  type EquipmentDocumentFile,
  type EquipmentDocumentType,
} from './EquipmentDocumentsSection';
