/**
 * Work Order Lens Section Components
 *
 * All four section containers for the Work Order lens.
 * Each section uses SectionContainer for sticky header behavior via IntersectionObserver.
 */

export {
  NotesSection,
  type NotesSectionProps,
  type WorkOrderNote,
} from './NotesSection';

export {
  PartsSection,
  type PartsSectionProps,
  type WorkOrderPart,
  type PartStatus,
} from './PartsSection';

export {
  AttachmentsSection,
  type AttachmentsSectionProps,
  type Attachment,
  type AttachmentKind,
  getAttachmentKind,
} from './AttachmentsSection';

export {
  HistorySection,
  type HistorySectionProps,
  type AuditLogEntry,
} from './HistorySection';
