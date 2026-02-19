import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export type DocumentKind = 'pdf' | 'image' | 'spreadsheet' | 'word' | 'other';

export interface PartDocument {
  id: string;
  /** Document filename */
  name: string;
  /** File type category */
  kind?: DocumentKind;
  /** File size in bytes */
  size_bytes?: number;
  /** Signed URL for download/preview */
  url?: string;
  /** Document category label (e.g. "MSDS", "Spec Sheet", "Manual") */
  category?: string;
  /** Upload timestamp */
  uploaded_at?: string;
  uploaded_by?: string;
}

export interface DocumentsSectionProps {
  documents: PartDocument[];
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Map document kind to a simple text icon / emoji-free label.
 * We use text abbreviations — no emoji per CLAUDE.md rules.
 */
function getDocumentIcon(kind?: DocumentKind): string {
  switch (kind) {
    case 'pdf':
      return 'PDF';
    case 'image':
      return 'IMG';
    case 'spreadsheet':
      return 'XLS';
    case 'word':
      return 'DOC';
    default:
      return 'FILE';
  }
}

// ============================================================================
// DOCUMENT CARD
// ============================================================================

interface DocumentCardProps {
  doc: PartDocument;
}

function DocumentCard({ doc }: DocumentCardProps) {
  const sizeLabel = formatFileSize(doc.size_bytes);
  const iconLabel = getDocumentIcon(doc.kind);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => {
        if (doc.url) window.open(doc.url, '_blank', 'noopener,noreferrer');
      }}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && doc.url) {
          e.preventDefault();
          window.open(doc.url, '_blank', 'noopener,noreferrer');
        }
      }}
      className={cn(
        // Row layout per DocCard spec: 48px min height
        'flex items-center gap-3 px-5 py-3 min-h-12',
        // Divider between cards
        'border-b border-surface-border-subtle last:border-b-0',
        // Interactive styling
        doc.url && 'cursor-pointer hover:bg-surface-elevated transition-colors duration-fast',
        !doc.url && 'cursor-default'
      )}
    >
      {/* File type icon — 40×40 rounded rectangle */}
      <div
        className={cn(
          'w-10 h-10 rounded flex items-center justify-center flex-shrink-0',
          'bg-surface-elevated border border-surface-border',
          'text-[11px] font-bold text-txt-tertiary tracking-wide'
        )}
        aria-hidden="true"
      >
        {iconLabel}
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-medium text-txt-primary leading-[1.4] truncate">
          {doc.name}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          {doc.category && (
            <span className="text-[12px] text-txt-tertiary leading-[1.4]">
              {doc.category}
            </span>
          )}
          {doc.category && sizeLabel && (
            <span className="text-txt-tertiary text-[12px]" aria-hidden="true">
              &middot;
            </span>
          )}
          {sizeLabel && (
            <span className="text-[12px] text-txt-tertiary leading-[1.4]">
              {sizeLabel}
            </span>
          )}
        </div>
      </div>

      {/* Chevron — only shown if document is downloadable */}
      {doc.url && (
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
      )}
    </div>
  );
}

// ============================================================================
// DOCUMENTS SECTION
// ============================================================================

/**
 * DocumentsSection - Spec sheets, MSDS, manuals and other documents for a part.
 *
 * Each document renders as a 48px card with icon, filename, category, and size.
 * Clicking opens the document in a new tab (if signed URL available).
 * Empty state: contextual message.
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function DocumentsSection({
  documents,
  stickyTop,
}: DocumentsSectionProps) {
  return (
    <SectionContainer
      title="Documents"
      count={documents.length > 0 ? documents.length : undefined}
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No documents attached. Upload spec sheets or MSDS to this part.
          </p>
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
