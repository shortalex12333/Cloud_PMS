'use client';

/**
 * ReceivingPhotos - View attached photos/documents for a receiving event
 *
 * Action 6: view_receiving_photos (read-only escape hatch)
 * Purpose: View attached photos/documents
 * Allowed Roles: All Crew (read-only)
 * Tables Read: pms_receiving_documents
 *
 * This is a read-only component - no upload functionality.
 * Photo upload is handled by add_line_item with attached photo (separate action).
 */

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Image as ImageIcon, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchReceivingAttachments } from '../api';
import type { ReceivingAttachment } from '../types';
import { MediaRenderer } from '@/components/media/MediaRenderer';
import { DocumentCard } from '@/components/media/DocumentCard';
import { getAttachmentKind } from '@/components/media/fileUtils';

// ============================================================================
// TYPES
// ============================================================================

interface ReceivingPhotosProps {
  /** The receiving event ID to fetch attachments for */
  receivingId: string;
  /** JWT auth token */
  token: string;
  /** Optional callback when a document is clicked (e.g., to open document lens) */
  onDocumentClick?: (documentId: string) => void;
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

function PhotosSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-32 rounded-md bg-white/5 animate-pulse" />
      <div className="h-32 rounded-md bg-white/5 animate-pulse" />
    </div>
  );
}

// ============================================================================
// EMPTY STATE
// ============================================================================

function EmptyPhotos() {
  return (
    <div className="py-6 text-center">
      <ImageIcon className="mx-auto h-8 w-8 text-white/30 mb-2" />
      <p className="text-sm text-white/50">No photos or documents attached</p>
    </div>
  );
}

// ============================================================================
// ERROR STATE
// ============================================================================

function ErrorState({ error }: { error: Error }) {
  return (
    <div className="py-4 text-center">
      <p className="text-sm text-red-400">
        Failed to load attachments: {error.message}
      </p>
    </div>
  );
}

// ============================================================================
// ATTACHMENT ITEM
// ============================================================================

interface AttachmentItemProps {
  attachment: ReceivingAttachment;
  onDocumentClick?: (documentId: string) => void;
}

function AttachmentItem({ attachment, onDocumentClick }: AttachmentItemProps) {
  // Determine if this is a media file (image/video) or document
  const filename = attachment.document?.filename || `attachment-${attachment.id}`;
  const kind = getAttachmentKind(filename);

  // Get file metadata for rendering
  const file = {
    id: attachment.document_id,
    url: attachment.url || '',
    filename,
    mime_type: attachment.document?.mime_type || 'application/octet-stream',
    size_bytes: attachment.document?.size_bytes || 0,
  };

  // Doc type badge color
  const docTypeBadgeColors: Record<string, string> = {
    invoice: 'bg-blue-500/20 text-blue-300',
    packing_slip: 'bg-green-500/20 text-green-300',
    photo: 'bg-purple-500/20 text-purple-300',
    other: 'bg-white/10 text-white/60',
  };

  const badgeColor = docTypeBadgeColors[attachment.doc_type] || docTypeBadgeColors.other;

  return (
    <div className="mb-3 last:mb-0">
      {/* Doc type and comment header */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-0.5 text-xs rounded ${badgeColor}`}>
          {attachment.doc_type.replace(/_/g, ' ')}
        </span>
        {attachment.comment && (
          <span className="text-xs text-white/50 truncate">{attachment.comment}</span>
        )}
      </div>

      {/* Media or document rendering */}
      {kind === 'media' && file.url ? (
        <MediaRenderer file={file} maxHeight={200} />
      ) : (
        <DocumentCard
          file={file}
          onClick={() => onDocumentClick?.(attachment.document_id)}
        />
      )}
    </div>
  );
}

// ============================================================================
// RECEIVING PHOTOS COMPONENT
// ============================================================================

/**
 * ReceivingPhotos - Displays attached photos and documents for a receiving event.
 *
 * Features:
 * - Fetches attachments via view_receiving_history action
 * - Displays images inline with lightbox support (via MediaRenderer)
 * - Displays documents as cards (via DocumentCard)
 * - Shows doc type badges (invoice, packing_slip, photo, other)
 * - Collapsible section with count badge
 * - Read-only - no upload capability (that's a separate action)
 */
export function ReceivingPhotos({
  receivingId,
  token,
  onDocumentClick,
}: ReceivingPhotosProps) {
  const [isExpanded, setIsExpanded] = React.useState(true);

  // Fetch attachments
  const {
    data: attachments,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['receiving-attachments', receivingId],
    queryFn: () => fetchReceivingAttachments(receivingId, token),
    enabled: !!receivingId && !!token,
    staleTime: 30000, // 30 seconds
  });

  // Count for the header badge
  const count = attachments?.length || 0;

  return (
    <div className="border-t border-white/10 pt-4">
      {/* Section header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between py-2 text-left group"
      >
        <div className="flex items-center gap-2">
          <ImageIcon className="h-4 w-4 text-white/60" />
          <span className="text-sm font-medium text-white/80">
            Photos & Documents
          </span>
          {count > 0 && (
            <span className="px-1.5 py-0.5 text-xs rounded-full bg-white/10 text-white/60">
              {count}
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4 text-white/40 group-hover:text-white/60 transition-colors" />
        ) : (
          <ChevronDown className="h-4 w-4 text-white/40 group-hover:text-white/60 transition-colors" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="mt-2">
          {isLoading && <PhotosSkeleton />}
          {error && <ErrorState error={error as Error} />}
          {!isLoading && !error && count === 0 && <EmptyPhotos />}
          {!isLoading && !error && attachments && attachments.length > 0 && (
            <div>
              {attachments.map((attachment) => (
                <AttachmentItem
                  key={attachment.id}
                  attachment={attachment}
                  onDocumentClick={onDocumentClick}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ReceivingPhotos;
