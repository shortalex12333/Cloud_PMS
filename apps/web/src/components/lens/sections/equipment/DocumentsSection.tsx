import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export interface EquipmentDocument {
  id: string;
  title: string;
  /** Document category: manual | certificate | datasheet | other */
  document_type?: string;
  /** File URL or signed storage URL */
  url?: string;
  /** File size in bytes */
  file_size?: number;
  uploaded_at?: string;
  uploaded_by?: string;
}

export interface DocumentsSectionProps {
  documents: EquipmentDocument[];
  canLinkDocument: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
  onLinkDocument?: () => void;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatDocumentType(type?: string): string {
  if (!type) return 'Document';
  const labels: Record<string, string> = {
    manual: 'Manual',
    certificate: 'Certificate',
    datasheet: 'Data Sheet',
    other: 'Other',
  };
  return labels[type] ?? type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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

// ============================================================================
// DOCUMENT CARD
// ============================================================================

interface DocumentCardProps {
  doc: EquipmentDocument;
}

function DocumentCard({ doc }: DocumentCardProps) {
  const meta = [
    formatDocumentType(doc.document_type),
    formatFileSize(doc.file_size),
    doc.uploaded_at ? formatDate(doc.uploaded_at) : undefined,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => doc.url && window.open(doc.url, '_blank', 'noopener,noreferrer')}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && doc.url) {
          window.open(doc.url, '_blank', 'noopener,noreferrer');
        }
      }}
      className="flex items-center gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px] hover:bg-surface-hover transition-colors cursor-pointer"
      aria-label={`Open document: ${doc.title}`}
    >
      {/* Document icon */}
      <div className="shrink-0 w-8 h-8 rounded flex items-center justify-center bg-surface-secondary">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="text-txt-tertiary"
        >
          <path
            d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M9 1v5h5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-medium text-txt-primary leading-[1.4] truncate">
          {doc.title}
        </p>
        {meta && (
          <p className="text-[12px] text-txt-tertiary mt-0.5">{meta}</p>
        )}
      </div>

      {/* External link indicator */}
      {doc.url && (
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="text-txt-tertiary shrink-0"
        >
          <path
            d="M5.5 2.5H2.5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-3M8 2.5h3.5m0 0v3.5m0-3.5L5.5 8.5"
            stroke="currentColor"
            strokeWidth="1.25"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </div>
  );
}

// ============================================================================
// DOCUMENTS SECTION
// ============================================================================

/**
 * DocumentsSection - Manuals and certificates linked to this equipment.
 *
 * Each document renders as a card that opens the file URL in a new tab.
 * canLinkDocument gates the "Link Document" action (HOD+).
 */
export function DocumentsSection({
  documents,
  canLinkDocument,
  stickyTop,
  onLinkDocument,
}: DocumentsSectionProps) {
  return (
    <SectionContainer
      title="Documents"
      count={documents.length > 0 ? documents.length : undefined}
      action={
        canLinkDocument
          ? { label: '+ Link Document', onClick: onLinkDocument ?? (() => {}) }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No documents attached. Manuals and certificates appear here.
          </p>
          {canLinkDocument && onLinkDocument && (
            <GhostButton onClick={onLinkDocument} className="mt-3">
              + Link Document
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="-mx-4">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default DocumentsSection;
