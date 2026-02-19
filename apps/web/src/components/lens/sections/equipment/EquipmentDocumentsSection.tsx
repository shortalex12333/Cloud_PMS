import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { MediaRenderer } from '@/components/media/MediaRenderer';
import { DocumentCard } from '@/components/media/DocumentCard';
import { getAttachmentKind, formatFileSize } from '@/components/media/fileUtils';

// ============================================================================
// TYPES
// ============================================================================

export type EquipmentDocumentType =
  | 'manual'
  | 'photo'
  | 'certificate'
  | 'diagram'
  | 'warranty'
  | 'general';

export interface EquipmentDocumentFile {
  id: string;
  /** File storage path */
  storage_path: string;
  /** Display filename */
  filename: string;
  /** Original filename at upload (optional) */
  original_filename?: string;
  /** MIME type for rendering */
  mime_type?: string;
  /** File size in bytes */
  file_size?: number;
  /** Document classification: manual | photo | certificate | diagram | warranty | general */
  document_type?: EquipmentDocumentType;
  /** Optional description */
  description?: string;
  /** Tags for categorization */
  tags?: string[];
  /** Who uploaded the file (display name) */
  uploaded_by?: string;
  /** When the file was uploaded */
  uploaded_at?: string;
  /** Signed URL for display/download (resolved by parent component) */
  url?: string;
}

export interface EquipmentDocumentsSectionProps {
  documents: EquipmentDocumentFile[];
  /** Whether user can upload new documents */
  canUpload?: boolean;
  /** Callback when "Add Document" button is clicked */
  onAddDocument?: () => void;
  /** Callback when a document card is clicked (opens Document lens) */
  onDocumentClick?: (documentId: string) => void;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DOCUMENT_TYPE_LABELS: Record<EquipmentDocumentType, string> = {
  manual: 'Manual',
  photo: 'Photo',
  certificate: 'Certificate',
  diagram: 'Diagram',
  warranty: 'Warranty',
  general: 'General',
};

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format timestamp to human-readable date.
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
 * Format document type to human-readable label.
 */
function formatDocumentType(type?: EquipmentDocumentType): string {
  if (!type) return 'Document';
  return DOCUMENT_TYPE_LABELS[type] ?? type.charAt(0).toUpperCase() + type.slice(1);
}

// ============================================================================
// DOCUMENT TYPE BADGE
// ============================================================================

interface DocumentTypeBadgeProps {
  type?: EquipmentDocumentType;
}

function DocumentTypeBadge({ type }: DocumentTypeBadgeProps) {
  if (!type) return null;

  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-secondary text-txt-tertiary font-medium uppercase tracking-[0.04em]">
      {formatDocumentType(type)}
    </span>
  );
}

// ============================================================================
// DOCUMENT ITEM (for non-media files with metadata)
// ============================================================================

interface DocumentItemProps {
  doc: EquipmentDocumentFile;
  onDocumentClick?: (documentId: string) => void;
}

function DocumentItem({ doc, onDocumentClick }: DocumentItemProps) {
  const meta = [
    formatDocumentType(doc.document_type),
    doc.file_size ? formatFileSize(doc.file_size) : undefined,
    doc.uploaded_at ? formatDate(doc.uploaded_at) : undefined,
  ]
    .filter(Boolean)
    .join(' · ');

  // If we have a signed URL, use DocumentCard for clickable preview
  if (doc.url && doc.mime_type) {
    return (
      <div className="mb-2 last:mb-0">
        <DocumentCard
          file={{
            id: doc.id,
            url: doc.url,
            filename: doc.filename,
            mime_type: doc.mime_type,
            size_bytes: doc.file_size || 0,
          }}
          onClick={() => onDocumentClick?.(doc.id)}
        />
        {/* Additional metadata below the card */}
        {(doc.description || doc.uploaded_by) && (
          <div className="px-4 pt-1 pb-2">
            {doc.description && (
              <p className="text-[12px] text-txt-secondary leading-[1.5]">
                {doc.description}
              </p>
            )}
            {doc.uploaded_by && (
              <p className="text-[11px] text-txt-tertiary mt-0.5">
                Uploaded by {doc.uploaded_by}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  // Fallback: simple row display for documents without signed URL
  return (
    <div className="flex items-start gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-11">
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

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-[14px] font-medium text-txt-primary leading-[1.4] truncate">
            {doc.filename}
          </p>
          <DocumentTypeBadge type={doc.document_type} />
        </div>
        {meta && (
          <p className="text-[12px] text-txt-tertiary leading-[1.4]">{meta}</p>
        )}
        {doc.description && (
          <p className="text-[12px] text-txt-secondary leading-[1.5] mt-1 line-clamp-2">
            {doc.description}
          </p>
        )}
        {doc.uploaded_by && (
          <p className="text-[11px] text-txt-tertiary mt-0.5">
            by {doc.uploaded_by}
          </p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MEDIA ITEM (for photos/videos with inline rendering)
// ============================================================================

interface MediaItemProps {
  doc: EquipmentDocumentFile;
}

function MediaItem({ doc }: MediaItemProps) {
  // Only render if we have a signed URL
  if (!doc.url || !doc.mime_type) {
    return (
      <div className="mb-3 p-4 bg-surface-secondary rounded-md">
        <p className="text-[13px] text-txt-secondary">{doc.filename}</p>
        <p className="text-[11px] text-txt-tertiary mt-1">Loading preview...</p>
      </div>
    );
  }

  return (
    <div className="mb-4 last:mb-0">
      <MediaRenderer
        file={{
          id: doc.id,
          url: doc.url,
          filename: doc.filename,
          mime_type: doc.mime_type,
          size_bytes: doc.file_size || 0,
        }}
        maxHeight={240}
      />
      {/* Additional metadata */}
      {(doc.description || doc.document_type || doc.uploaded_by) && (
        <div className="mt-1">
          <div className="flex items-center gap-2">
            <DocumentTypeBadge type={doc.document_type} />
            {doc.uploaded_at && (
              <span className="text-[11px] text-txt-tertiary">
                {formatDate(doc.uploaded_at)}
              </span>
            )}
          </div>
          {doc.description && (
            <p className="text-[12px] text-txt-secondary leading-[1.5] mt-1">
              {doc.description}
            </p>
          )}
          {doc.uploaded_by && (
            <p className="text-[11px] text-txt-tertiary mt-0.5">
              by {doc.uploaded_by}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// EQUIPMENT DOCUMENTS SECTION
// ============================================================================

/**
 * EquipmentDocumentsSection - Equipment documents, manuals, and photos.
 *
 * Renders different file types appropriately:
 * - Media files (photos, videos): Inline preview via MediaRenderer with lightbox
 * - Documents (PDFs, etc.): DocumentCard that opens Document lens on click
 *
 * Document types supported:
 * - manual: User manuals, operation guides
 * - photo: Equipment photos
 * - certificate: Compliance certificates
 * - diagram: Wiring diagrams, schematics
 * - warranty: Warranty documents
 * - general: Other documents
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function EquipmentDocumentsSection({
  documents,
  canUpload = false,
  onAddDocument,
  onDocumentClick,
  stickyTop,
}: EquipmentDocumentsSectionProps) {
  // Partition documents into media and non-media based on filename extension
  const mediaItems = documents.filter(
    (doc) => getAttachmentKind(doc.filename) === 'media'
  );
  const documentItems = documents.filter(
    (doc) => getAttachmentKind(doc.filename) === 'document'
  );

  // Group documents by type for better organization
  const groupedDocuments = React.useMemo(() => {
    const groups: Partial<Record<EquipmentDocumentType | 'other', EquipmentDocumentFile[]>> = {};

    documentItems.forEach((doc) => {
      const type = doc.document_type || 'general';
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type]!.push(doc);
    });

    return groups;
  }, [documentItems]);

  return (
    <SectionContainer
      title="Documents"
      count={documents.length > 0 ? documents.length : undefined}
      action={
        canUpload && onAddDocument
          ? { label: '+ Add Document', onClick: onAddDocument }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No documents attached. Manuals, certificates, and photos appear here.
          </p>
          {canUpload && onAddDocument && (
            <GhostButton onClick={onAddDocument} className="mt-3">
              + Add Document
            </GhostButton>
          )}
        </div>
      ) : (
        <div>
          {/* Media section: Photos and videos rendered inline */}
          {mediaItems.length > 0 && (
            <div className="mb-4">
              <h3 className="text-[11px] font-medium text-txt-tertiary uppercase tracking-[0.06em] mb-2">
                Photos & Media ({mediaItems.length})
              </h3>
              {mediaItems.map((doc) => (
                <MediaItem key={doc.id} doc={doc} />
              ))}
            </div>
          )}

          {/* Documents section: grouped by type */}
          {documentItems.length > 0 && (
            <div className={mediaItems.length > 0 ? 'pt-3 border-t border-surface-border-subtle' : ''}>
              {Object.entries(groupedDocuments).map(([type, docs]) => (
                <div key={type} className="mb-4 last:mb-0">
                  <h3 className="text-[11px] font-medium text-txt-tertiary uppercase tracking-[0.06em] mb-2">
                    {formatDocumentType(type as EquipmentDocumentType)} ({docs?.length || 0})
                  </h3>
                  <div className="-mx-4">
                    {docs?.map((doc) => (
                      <DocumentItem
                        key={doc.id}
                        doc={doc}
                        onDocumentClick={onDocumentClick}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

export default EquipmentDocumentsSection;
