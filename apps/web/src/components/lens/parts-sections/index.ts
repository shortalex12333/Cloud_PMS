/**
 * Parts Lens Section Components
 *
 * All four section containers for the Parts/Inventory lens.
 * Each section uses SectionContainer for sticky header behavior via IntersectionObserver.
 */

export {
  StockInfoSection,
  type StockInfoSectionProps,
} from './StockInfoSection';

export {
  TransactionHistorySection,
  type TransactionHistorySectionProps,
  type PartTransaction,
  type TransactionType,
} from './TransactionHistorySection';

export {
  LinkedEquipmentSection,
  type LinkedEquipmentSectionProps,
  type LinkedEquipment,
} from './LinkedEquipmentSection';

export {
  DocumentsSection,
  type DocumentsSectionProps,
  type PartDocument,
  type DocumentKind,
} from './DocumentsSection';
