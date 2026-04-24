/**
 * Lens V2 — Section Components
 * All sections for entity lens views.
 */

export { NotesSection, type NoteItem, type NotesSectionProps } from './NotesSection';
export { AuditTrailSection, type AuditEvent, type AuditTrailSectionProps } from './AuditTrailSection';
export { AttachmentsSection, type AttachmentItem, type AttachmentsSectionProps } from './AttachmentsSection';
export { PartsSection, type PartItem, type PartsSectionProps } from './PartsSection';
export { ChecklistSection, type ChecklistItem, type ChecklistSectionProps } from './ChecklistSection';
export { DocRowsSection, type DocRowItem, type DocRowsSectionProps } from './DocRowsSection';
export { KVSection, type KVItem, type KVSectionProps } from './KVSection';
export { HistorySection, type HistoryPeriod, type HistorySectionProps } from './HistorySection';

// ── Shared components introduced for Certificate + Document lens redesign ──
// See: docs/ongoing_work/documents/DOCUMENT_LENS_REDESIGN_2026-04-23.md
// See: /Users/celeste7/Desktop/celeste-screenshots/doc_cert_ux_change.md
export { LensFileViewer, type LensFileViewerProps } from './LensFileViewer';
export {
  RelatedEquipmentSection,
  type RelatedEquipmentItem,
  type RelatedEquipmentSectionProps,
} from './RelatedEquipmentSection';
export {
  EquipmentPickerModal,
  type EquipmentPickerItem,
  type EquipmentPickerModalProps,
} from './EquipmentPickerModal';
export {
  RenewalHistorySection,
  SupersededBanner,
  type RenewalHistoryPeriod,
  type RenewalHistorySectionProps,
  type SupersededBannerProps,
} from './RenewalHistorySection';

// ── Cohort-shared image viewer (2026-04-24) ──
// 1 comment per image per CEO ruling → pms_attachments.description.
// Consumed by work-orders (PR-WO-4b) + equipment (PR-EQ-4) + future lenses.
export { LensImageViewer, type LensImage, type LensImageViewerProps } from './LensImageViewer';
