/**
 * Parts Lens Section Components
 *
 * Section containers for the Parts/Inventory lens:
 * 1. StockInfoSection - Current stock, min/max, reorder point, unit cost
 * 2. TransactionHistorySection - Inventory transaction ledger (pms_inventory_transactions)
 * 3. UsageLogSection - Part usage history with work order/equipment links (pms_part_usage)
 * 4. LinkedEquipmentSection - Equipment that uses this part
 * 5. DocumentsSection - Spec sheets, MSDS, manuals
 *
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

export {
  UsageLogSection,
  type UsageLogSectionProps,
  type PartUsageEntry,
  type UsageReason,
} from './UsageLogSection';
