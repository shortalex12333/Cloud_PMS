import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export type ReceivingDocType = 'invoice' | 'packing_slip' | 'photo' | 'other';

export interface ReceivingDocument {
  /** Document link UUID (backend only - do not render) */
  id: string;
  /** Yacht UUID (backend only - do not render) */
  yacht_id?: string;
  /** Receiving header UUID (backend only - do not render) */
  receiving_id?: string;
  /** Document metadata UUID (backend only - used for navigation) */
  document_id: string;
  /** Document type: invoice, packing_slip, photo, other (FRONTEND) */
  doc_type?: ReceivingDocType | null;
  /** Inline comment about this attachment (FRONTEND) */
  comment?: string | null;
  /** Created timestamp (FRONTEND) */
  created_at?: string;
  /** Document filename (from doc_metadata join) */
  filename?: string;
  /** File size in bytes (from doc_metadata join) */
  file_size?: number;
  /** MIME type (from doc_metadata join) */
  mime_type?: string;
  /** Signed URL for preview/download */
  url?: string;
  /** Thumbnail URL for images */
  thumbnail_url?: string;
  /** Called when user clicks to open document in Document lens */
  onDocumentClick?: () => void;
}

export interface ReceivingDocumentsSectionProps {
  documents: ReceivingDocument[];
  onAddDocument?: () => void;
  canAddDocument: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Map doc_type to human-readable label.
 */
function formatDocType(type?: ReceivingDocType | null): string {
  if (!type) return 'Document';
  const labels: Record<ReceivingDocType, string> = {
    invoice: 'Invoice',
    packing_slip: 'Packing Slip',
    photo: 'Photo',
    other: 'Other',
  };
  return labels[type] ?? 'Document';
}

/**
 * Format file size to human-readable string.
 */
function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format ISO date string to display format.
 */
function formatDate(isoString?: string): string {
  if (!isoString) return '';
  try {
    return new Date(isoString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoString;
  }
}

/**
 * Determine if the document is an image based on MIME type.
 */
function isImage(mimeType?: string): boolean {
  if (!mimeType) return false;
  return mimeType.startsWith('image/');
}

/**
 * Determine if the document is a PDF.
 */
function isPdf(mimeType?: string): boolean {
  return mimeType === 'application/pdf';
}

/**
 * Get document icon label (text-based, no emoji).
 */
function getDocIconLabel(mimeType?: string, docType?: ReceivingDocType | null): string {
  if (isPdf(mimeType)) return 'PDF';
  if (isImage(mimeType)) return 'IMG';
  if (docType === 'invoice') return 'INV';
  if (docType === 'packing_slip') return 'PKG';
  return 'DOC';
}

// ============================================================================
// DOCUMENT CARD
// ============================================================================

interface DocumentCardProps {
  doc: ReceivingDocument;
}

function DocumentCard({ doc }: DocumentCardProps) {
  const typeLabel = formatDocType(doc.doc_type);
  const sizeLabel = formatFileSize(doc.file_size);
  const dateLabel = formatDate(doc.created_at);
  const iconLabel = getDocIconLabel(doc.mime_type, doc.doc_type);
  const showImage = isImage(doc.mime_type) && (doc.thumbnail_url || doc.url);

  // Build metadata line
  const metaParts = [typeLabel, sizeLabel, dateLabel].filter(Boolean);
  const metaLine = metaParts.join(' · ');

  const handleClick = () => {
    if (doc.onDocumentClick) {
      // Navigate to Document lens
      doc.onDocumentClick();
    } else if (doc.url) {
      // Fallback: open in new tab
      window.open(doc.url, '_blank', 'noopener,noreferrer');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        // Row layout: 60px min height for image preview
        'flex items-center gap-4 px-5 py-3 min-h-[60px]',
        // Divider between cards
        'border-b border-surface-border-subtle last:border-b-0',
        // Interactive styling
        'cursor-pointer hover:bg-surface-hover transition-colors duration-fast',
        // Focus state for accessibility
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-interactive'
      )}
      aria-label={`Open document: ${doc.filename || typeLabel}`}
    >
      {/* Thumbnail or icon */}
      {showImage ? (
        <div className="w-12 h-12 rounded overflow-hidden flex-shrink-0 bg-surface-secondary">
          <img
            src={doc.thumbnail_url || doc.url}
            alt=""
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      ) : (
        <div
          className={cn(
            'w-12 h-12 rounded flex items-center justify-center flex-shrink-0',
            'bg-surface-elevated border border-surface-border',
            'text-[11px] font-bold text-txt-tertiary tracking-wide'
          )}
          aria-hidden="true"
        >
          {iconLabel}
        </div>
      )}

      {/* Document info */}
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-medium text-txt-primary leading-[1.4] truncate">
          {doc.filename || typeLabel}
        </p>
        {metaLine && (
          <p className="text-[12px] text-txt-tertiary mt-0.5">{metaLine}</p>
        )}
        {doc.comment && (
          <p className="text-[12px] text-txt-secondary mt-1 line-clamp-1 italic">
            "{doc.comment}"
          </p>
        )}
      </div>

      {/* Chevron indicator */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-4 h-4 text-txt-tertiary flex-shrink-0"
        aria-hidden="true"
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </div>
  );
}

// ============================================================================
// RECEIVING DOCUMENTS SECTION
// ============================================================================

/**
 * ReceivingDocumentsSection - Displays attached documents for a receiving record.
 *
 * Document types include:
 * - Invoice: scanned/photographed invoices
 * - Packing Slip: delivery manifests
 * - Photo: photos of received goods
 * - Other: miscellaneous attachments
 *
 * Each document card shows:
 * - Thumbnail (for images) or type icon (for PDFs/other)
 * - Filename or type label
 * - Document type, file size, upload date
 * - Optional comment (shown in italics)
 *
 * Clicking a document navigates to the Document lens or opens in new tab.
 *
 * Empty state: contextual, actionable.
 */
export function ReceivingDocumentsSection({
  documents,
  onAddDocument,
  canAddDocument,
  stickyTop,
}: ReceivingDocumentsSectionProps) {
  // Group counts for subtitle
  const invoiceCount = documents.filter((d) => d.doc_type === 'invoice').length;
  const packingSlipCount = documents.filter((d) => d.doc_type === 'packing_slip').length;
  const photoCount = documents.filter((d) => d.doc_type === 'photo').length;

  return (
    <SectionContainer
      title="Documents"
      count={documents.length > 0 ? documents.length : undefined}
      action={
        canAddDocument
          ? { label: '+ Add Document', onClick: onAddDocument ?? (() => {}) }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        // Contextual empty state
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No documents attached. Add invoices, packing slips, or photos.
          </p>
          {canAddDocument && onAddDocument && (
            <GhostButton onClick={onAddDocument} className="mt-3">
              + Add Document
            </GhostButton>
          )}
        </div>
      ) : (
        <>
          {/* Summary line showing document type breakdown */}
          {(invoiceCount > 0 || packingSlipCount > 0 || photoCount > 0) && (
            <div className="pb-2 text-[12px] text-txt-tertiary">
              {[
                invoiceCount > 0 && `${invoiceCount} invoice${invoiceCount !== 1 ? 's' : ''}`,
                packingSlipCount > 0 && `${packingSlipCount} packing slip${packingSlipCount !== 1 ? 's' : ''}`,
                photoCount > 0 && `${photoCount} photo${photoCount !== 1 ? 's' : ''}`,
              ]
                .filter(Boolean)
                .join(', ')}
            </div>
          )}
          <div className="-mx-4">
            {documents.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} />
            ))}
          </div>
        </>
      )}
    </SectionContainer>
  );
}

export default ReceivingDocumentsSection;
