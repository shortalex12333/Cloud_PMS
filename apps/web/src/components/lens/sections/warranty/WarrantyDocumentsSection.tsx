/**
 * WarrantyDocumentsSection — Documents section for Warranty Claims.
 *
 * Displays warranty-related documents (certificates, claims, correspondence)
 * from the pms-warranty-docs storage bucket.
 *
 * Per rules.md file rendering:
 * - Media files (.png, .jpg, .mp4): render directly via MediaRenderer
 * - Document files (.pdf, .doc): render as DocumentCard, open in Document lens
 *
 * Document types:
 * - certificate: warranty certificates, proof of purchase
 * - claim: claim forms, damage reports, photos
 * - correspondence: vendor emails, responses
 */

'use client';

import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { MediaRenderer } from '@/components/media/MediaRenderer';
import { DocumentCard } from '@/components/media/DocumentCard';
import { getAttachmentKind } from '@/components/media/fileUtils';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

export type WarrantyDocumentType = 'certificate' | 'claim' | 'correspondence' | 'other';

export interface WarrantyDocument {
  id: string;
  /** Document display name */
  document_name: string;
  /** Document category for badge display */
  document_type: WarrantyDocumentType;
  /** Upload timestamp */
  upload_date: string;
  /** Signed URL for media preview or download */
  file_url: string;
  /** MIME type for rendering decision */
  mime_type: string;
  /** File size in bytes */
  file_size: number;
  /** Original filename (for extension detection) */
  filename?: string;
}

export interface WarrantyDocumentsSectionProps {
  documents: WarrantyDocument[];
  onAddDocument: () => void;
  canAddDocument: boolean;
  /** Called when a document card is clicked - opens Document lens */
  onDocumentClick?: (documentId: string) => void;
  /** Top offset for sticky header (56 when inside lens to clear fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function getDocumentTypeBadgeStyles(type: WarrantyDocumentType): {
  bg: string;
  text: string;
  label: string;
} {
  switch (type) {
    case 'certificate':
      return {
        bg: 'bg-[var(--celeste-green)]/10',
        text: 'text-[var(--celeste-green)]',
        label: 'Certificate',
      };
    case 'claim':
      return {
        bg: 'bg-[var(--celeste-accent)]/10',
        text: 'text-[var(--celeste-accent)]',
        label: 'Claim',
      };
    case 'correspondence':
      return {
        bg: 'bg-[var(--celeste-yellow)]/10',
        text: 'text-[var(--celeste-yellow)]',
        label: 'Correspondence',
      };
    default:
      return {
        bg: 'bg-surface-secondary',
        text: 'text-txt-tertiary',
        label: 'Document',
      };
  }
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
// DOCUMENT TYPE BADGE
// ============================================================================

interface DocumentTypeBadgeProps {
  type: WarrantyDocumentType;
  className?: string;
}

function DocumentTypeBadge({ type, className }: DocumentTypeBadgeProps) {
  const styles = getDocumentTypeBadgeStyles(type);

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium',
        styles.bg,
        styles.text,
        className
      )}
    >
      {styles.label}
    </span>
  );
}

// ============================================================================
// MEDIA ITEM (for inline rendering)
// ============================================================================

interface MediaItemProps {
  document: WarrantyDocument;
}

function MediaItem({ document }: MediaItemProps) {
  return (
    <div className="mb-3 last:mb-0">
      {/* Document type badge */}
      <div className="flex items-center gap-2 mb-2">
        <DocumentTypeBadge type={document.document_type} />
        <span className="text-[12px] text-txt-tertiary">
          {formatDate(document.upload_date)}
        </span>
      </div>

      {/* Media renderer */}
      <MediaRenderer
        file={{
          id: document.id,
          url: document.file_url,
          filename: document.filename || document.document_name,
          mime_type: document.mime_type,
          size_bytes: document.file_size,
        }}
        maxHeight={240}
      />

      {/* Document name caption */}
      <p className="mt-1 text-[12px] text-txt-secondary leading-[1.4]">
        {document.document_name}
      </p>
    </div>
  );
}

// ============================================================================
// DOCUMENT ITEM (for preview card rendering)
// ============================================================================

interface DocumentItemProps {
  document: WarrantyDocument;
  onClick?: () => void;
}

function DocumentItem({ document, onClick }: DocumentItemProps) {
  return (
    <div className="mb-2 last:mb-0">
      {/* Document type badge + date row */}
      <div className="flex items-center gap-2 mb-1.5">
        <DocumentTypeBadge type={document.document_type} />
        <span className="text-[12px] text-txt-tertiary">
          {formatDate(document.upload_date)}
        </span>
      </div>

      {/* Document card - opens Document lens on click */}
      <DocumentCard
        file={{
          id: document.id,
          url: document.file_url,
          filename: document.filename || document.document_name,
          mime_type: document.mime_type,
          size_bytes: document.file_size,
        }}
        onClick={onClick ?? (() => {})}
      />
    </div>
  );
}

// ============================================================================
// WARRANTY DOCUMENTS SECTION
// ============================================================================

/**
 * WarrantyDocumentsSection - Displays documents attached to warranty claims.
 *
 * Renders media files inline (images/videos) and document files as preview cards
 * that open in the Document lens. Each document shows a type badge for categorization.
 *
 * Storage: pms-warranty-docs bucket at {yacht_id}/claims/{claim_id}/{filename}
 */
export function WarrantyDocumentsSection({
  documents,
  onAddDocument,
  canAddDocument,
  onDocumentClick,
  stickyTop,
}: WarrantyDocumentsSectionProps) {
  // Partition documents into media and non-media using extension-based detection
  const mediaItems = documents.filter((doc) => {
    const filename = doc.filename || doc.document_name;
    return getAttachmentKind(filename) === 'media';
  });

  const documentItems = documents.filter((doc) => {
    const filename = doc.filename || doc.document_name;
    return getAttachmentKind(filename) === 'document';
  });

  return (
    <SectionContainer
      title="Documents"
      count={documents.length > 0 ? documents.length : undefined}
      action={
        canAddDocument
          ? { label: '+ Add Document', onClick: onAddDocument }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {documents.length === 0 ? (
        // Empty state
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No documents attached. Add warranty certificates, claim forms, or correspondence.
          </p>
          {canAddDocument && (
            <GhostButton onClick={onAddDocument} className="mt-3">
              + Add Document
            </GhostButton>
          )}
        </div>
      ) : (
        <div>
          {/* Media: inline previews via MediaRenderer */}
          {mediaItems.length > 0 && (
            <div className="mb-4">
              {mediaItems.map((doc) => (
                <MediaItem key={doc.id} document={doc} />
              ))}
            </div>
          )}

          {/* Documents: preview cards via DocumentCard */}
          {documentItems.length > 0 && (
            <div>
              {/* Separator between media and documents when both present */}
              {mediaItems.length > 0 && (
                <div className="border-t border-surface-border-subtle mb-3" />
              )}
              {documentItems.map((doc) => (
                <DocumentItem
                  key={doc.id}
                  document={doc}
                  onClick={() => onDocumentClick?.(doc.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

export default WarrantyDocumentsSection;
