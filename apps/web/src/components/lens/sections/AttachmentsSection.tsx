import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export type AttachmentKind = 'media' | 'document';

export interface Attachment {
  id: string;
  filename: string;
  /** Signed URL for display (media) or download (document) */
  url: string;
  /** MIME type or inferred from extension */
  mime_type?: string;
  /** File size in bytes (optional, for display in document cards) */
  size_bytes?: number;
  /** Called when a document card is clicked — opens Document lens */
  onDocumentClick?: () => void;
}

export interface AttachmentsSectionProps {
  attachments: Attachment[];
  onAddFile: () => void;
  canAddFile: boolean;
}

// ============================================================================
// HELPERS
// ============================================================================

/** Media file extensions per UI_SPEC.md */
const MEDIA_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.mp4', '.heic', '.mov', '.webp', '.webm']);

/** Document file extensions per UI_SPEC.md */
const DOCUMENT_EXTENSIONS = new Set(['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.csv']);

/** Determine attachment kind from filename */
export function getAttachmentKind(filename: string): AttachmentKind {
  const ext = ('.' + filename.split('.').pop()?.toLowerCase()) as string;
  if (MEDIA_EXTENSIONS.has(ext)) return 'media';
  return 'document';
}

/** Format file size for display: "2.4 MB", "340 KB" */
function formatFileSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Get document icon character based on extension */
function getDocumentIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf': return '📄';
    case 'xlsx':
    case 'xls':
    case 'csv': return '📊';
    case 'docx':
    case 'doc': return '📝';
    case 'pptx':
    case 'ppt': return '📑';
    default: return '📎';
  }
}

// ============================================================================
// MEDIA ITEM (inline preview)
// ============================================================================

interface MediaItemProps {
  attachment: Attachment;
}

function MediaItem({ attachment }: MediaItemProps) {
  const ext = attachment.filename.split('.').pop()?.toLowerCase();
  const isVideo = ext === 'mp4' || ext === 'mov' || ext === 'webm';

  return (
    <div className="mb-3 last:mb-0">
      {isVideo ? (
        // Video: inline player, max-height 240px per UI_SPEC.md
        <video
          src={attachment.url}
          controls
          className={cn(
            'w-full rounded-md',
            // Max-height 240px per UI_SPEC.md proportions
            'max-h-[240px] object-contain',
            'bg-surface-base'
          )}
          aria-label={attachment.filename}
        />
      ) : (
        // Image: inline, maintain aspect ratio, max-height 240px per UI_SPEC.md
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={attachment.url}
          alt={attachment.filename}
          className={cn(
            'w-full rounded-md',
            'max-h-[240px] object-contain',
            'bg-surface-base'
          )}
          loading="lazy"
        />
      )}
      {/* Filename caption */}
      <p className="mt-1 text-[12px] text-txt-tertiary leading-[1.4] truncate">
        {attachment.filename}
      </p>
    </div>
  );
}

// ============================================================================
// DOCUMENT CARD (preview card with icon, filename, size)
// ============================================================================

interface DocumentCardProps {
  attachment: Attachment;
}

function DocumentCard({ attachment }: DocumentCardProps) {
  const icon = getDocumentIcon(attachment.filename);
  const sizeLabel = formatFileSize(attachment.size_bytes);

  const handleClick = () => {
    attachment.onDocumentClick?.();
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
        // File Preview Card spec from UI_SPEC.md:
        // background: var(--surface-primary)
        // border-radius: var(--radius-md) = 12px
        // padding: 12px 16px
        // height: 48px
        // display: flex, align-items: center, gap: 12px
        // cursor: pointer
        'flex items-center gap-3',
        'px-4 py-3 min-h-[48px]',
        'bg-surface-primary rounded-md',
        'cursor-pointer',
        // Hover: surface-hover
        'hover:bg-surface-hover transition-colors duration-150',
        // Focus state
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-md',
        'mb-2 last:mb-0'
      )}
    >
      {/* Icon: 20px, text-tertiary per UI_SPEC.md */}
      <span
        className="text-[20px] text-txt-tertiary flex-shrink-0"
        aria-hidden="true"
      >
        {icon}
      </span>

      {/* Filename + size */}
      <div className="flex-1 min-w-0">
        {/* Filename: 14px/500/var(--text-primary) per UI_SPEC.md */}
        <p className="text-[14px] font-medium text-txt-primary truncate leading-[1.4]">
          {attachment.filename}
        </p>
        {/* File size: 12px/400/var(--text-tertiary) per UI_SPEC.md */}
        {sizeLabel && (
          <p className="text-[12px] text-txt-tertiary leading-[1.4]">
            {sizeLabel}
          </p>
        )}
      </div>

      {/* Chevron indicator — opens Document lens */}
      <svg
        className="w-4 h-4 text-txt-tertiary flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

// ============================================================================
// ATTACHMENTS SECTION
// ============================================================================

/**
 * AttachmentsSection - Renders media inline and documents as preview cards.
 *
 * Media files (.png, .jpg, .mp4, .heic, etc.): rendered inline with max-height 240px.
 * Document files (.pdf, .docx, etc.): rendered as File Preview Card (icon + filename + size).
 * Document cards are clickable and open Document lens.
 *
 * Uses SectionContainer for sticky header behavior.
 * Empty state is contextual and actionable.
 */
export function AttachmentsSection({ attachments, onAddFile, canAddFile }: AttachmentsSectionProps) {
  // Partition attachments into media and documents
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
          {/* Media: inline previews */}
          {mediaItems.length > 0 && (
            <div className="mb-3">
              {mediaItems.map((attachment) => (
                <MediaItem key={attachment.id} attachment={attachment} />
              ))}
            </div>
          )}

          {/* Documents: preview cards */}
          {documentItems.length > 0 && (
            <div>
              {/* Separator between media and documents when both present */}
              {mediaItems.length > 0 && (
                <div className="border-t border-surface-border-subtle mb-3" />
              )}
              {documentItems.map((attachment) => (
                <DocumentCard key={attachment.id} attachment={attachment} />
              ))}
            </div>
          )}
        </div>
      )}
    </SectionContainer>
  );
}

export default AttachmentsSection;
