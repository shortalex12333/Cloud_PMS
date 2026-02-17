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
