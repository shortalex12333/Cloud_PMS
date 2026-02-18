import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { MediaRenderer } from '@/components/media/MediaRenderer';
import { DocumentCard } from '@/components/media/DocumentCard';
import { getAttachmentKind } from '@/components/media/fileUtils';

// ============================================================================
// TYPES
// ============================================================================

export type AttachmentKind = 'media' | 'document';

export interface Attachment {
  id: string;
  filename: string;
  /** Signed URL for display (media) or download (document) */
  url: string;
  /** MIME type — used by MediaRenderer and DocumentCard */
  mime_type: string;
  /** File size in bytes (required for DocumentCard size label) */
  size_bytes: number;
}

export interface AttachmentsSectionProps {
  attachments: Attachment[];
  onAddFile: () => void;
  canAddFile: boolean;
  /** Called when a document card is clicked — opens Document lens */
  onDocumentClick?: (fileId: string) => void;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// ATTACHMENTS SECTION
// ============================================================================

/**
 * AttachmentsSection — Renders media inline and documents as preview cards.
 *
 * Media files (.png, .jpg, .mp4, .heic, etc.): rendered inline via MediaRenderer
 * with max-height 240px, loading skeleton, error state, and lightbox on click.
 *
 * Document files (.pdf, .docx, etc.): rendered as DocumentCard (icon + filename
 * + size). Document cards open the Document lens on click.
 *
 * Uses SectionContainer for sticky header behavior.
 * Empty state is contextual and actionable.
 */
export function AttachmentsSection({
  attachments,
  onAddFile,
  canAddFile,
  onDocumentClick,
  stickyTop,
}: AttachmentsSectionProps) {
  // Partition attachments into media and documents using extension-based detection
  // (MIME unreliable from signed storage URLs — per STATE.md decision)
  const mediaItems = attachments.filter(
    (a) => getAttachmentKind(a.filename) === 'media'
  );
  const documentItems = attachments.filter(
    (a) => getAttachmentKind(a.filename) === 'document'
  );

  return (
    <SectionContainer
      title="Attachments"
      count={attachments.length > 0 ? attachments.length : undefined}
      action={
        canAddFile
          ? { label: '+ Add File', onClick: onAddFile }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {attachments.length === 0 ? (
        // Contextual empty state per UI_SPEC.md language rules
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No attachments. Add photos or documents to this work order.
          </p>
          {canAddFile && (
            <GhostButton
              onClick={onAddFile}
              className="mt-3"
            >
              + Add File
            </GhostButton>
          )}
        </div>
      ) : (
        <div>
          {/* Media: inline previews via MediaRenderer */}
          {mediaItems.length > 0 && (
            <div className="mb-3">
              {mediaItems.map((attachment) => (
                <MediaRenderer
                  key={attachment.id}
                  file={{
                    id: attachment.id,
                    url: attachment.url,
                    filename: attachment.filename,
                    mime_type: attachment.mime_type,
                    size_bytes: attachment.size_bytes,
                  }}
                  maxHeight={240}
                />
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
              {documentItems.map((attachment) => (
                <DocumentCard
                  key={attachment.id}
                  file={{
                    id: attachment.id,
                    url: attachment.url,
                    filename: attachment.filename,
                    mime_type: attachment.mime_type,
                    size_bytes: attachment.size_bytes,
                  }}
                  onClick={() => onDocumentClick?.(attachment.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

export default AttachmentsSection;
