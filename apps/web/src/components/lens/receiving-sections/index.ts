/**
 * Receiving Lens Sections
 *
 * Child table sections for the Receiving lens:
 * - ReceivingLineItemsSection: displays pms_receiving_items (line items)
 * - ReceivingDocumentsSection: displays pms_receiving_documents (attachments)
 */

export {
  ReceivingLineItemsSection,
  type ReceivingLineItem,
  type ReceivingLineItemsSectionProps,
} from './ReceivingLineItemsSection';

export {
  ReceivingDocumentsSection,
  type ReceivingDocument,
  type ReceivingDocType,
  type ReceivingDocumentsSectionProps,
} from './ReceivingDocumentsSection';
