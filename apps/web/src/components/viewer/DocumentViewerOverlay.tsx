'use client';

/**
 * DocumentViewerOverlay - In-app document viewer for attachments
 *
 * Displays PDFs and images inline without downloading.
 * Fallback to download/Open in Outlook for unsupported types.
 * Uses portal to document.body for proper z-index layering.
 *
 * SOC-2 compliant: bytes streamed live, no storage at rest.
 */

import { useCallback, useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, Download, ExternalLink, FileText, Image as ImageIcon, File, MoreVertical, FileUp, Link2, Unlink } from 'lucide-react';

interface DocumentViewerOverlayProps {
  open: boolean;
  onClose: () => void;
  fileName: string;
  contentType: string;
  blobUrl: string;
  /** Optional: Outlook web link for "Open in Outlook" button */
  outlookUrl?: string;
  /** Optional: Download URL for fallback */
  downloadUrl?: string;
  /** Optional: Hide download button (default true). Set false for email attachments. */
  allowDownload?: boolean;
  /** Optional: Document ID for micro-actions (if saved to storage) */
  documentId?: string;
  /** Optional: Callback for micro-actions */
  onMicroAction?: (action: string, documentId: string) => void;
}

// Safe content types for inline viewing
const SAFE_PDF_TYPES = ['application/pdf'];
const SAFE_IMAGE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'image/tiff',
];

function getFileIcon(contentType: string) {
  if (SAFE_PDF_TYPES.some((t) => contentType.startsWith(t))) {
    return <FileText className="h-12 w-12 text-restricted-red-400" />;
  }
  if (SAFE_IMAGE_TYPES.some((t) => contentType.startsWith(t))) {
    return <ImageIcon className="h-12 w-12 text-celeste-accent-400" />;
  }
  return <File className="h-12 w-12 text-celeste-text-muted" />;
}

function canPreview(contentType: string): 'pdf' | 'image' | false {
  if (SAFE_PDF_TYPES.some((t) => contentType.startsWith(t))) {
    return 'pdf';
  }
  if (SAFE_IMAGE_TYPES.some((t) => contentType.startsWith(t))) {
    return 'image';
  }
  return false;
}

export default function DocumentViewerOverlay({
  open,
  onClose,
  fileName,
  contentType,
  blobUrl,
  outlookUrl,
  downloadUrl,
  allowDownload = true,
  documentId,
  onMicroAction,
}: DocumentViewerOverlayProps) {
  const [mounted, setMounted] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const actionsMenuRef = useRef<HTMLDivElement>(null);

  // Handle client-side mounting for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Reset errors when blobUrl changes
  useEffect(() => {
    setImageError(false);
    setPdfError(false);
  }, [blobUrl]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    if (open) {
      window.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when overlay is open
      document.body.style.overflow = 'hidden';
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = '';
      };
    }
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  const handleDownload = useCallback(() => {
    if (downloadUrl) {
      window.open(downloadUrl, '_blank');
    } else if (blobUrl) {
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  }, [blobUrl, downloadUrl, fileName]);

  const handleOpenInOutlook = useCallback(() => {
    if (outlookUrl) {
      window.open(outlookUrl, '_blank', 'noopener,noreferrer');
    }
  }, [outlookUrl]);

  // Close actions menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (actionsMenuRef.current && !actionsMenuRef.current.contains(e.target as Node)) {
        setShowActionsMenu(false);
      }
    };
    if (showActionsMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showActionsMenu]);

  // Micro-action handlers
  const handleMicroAction = useCallback((action: string) => {
    setShowActionsMenu(false);
    if (documentId && onMicroAction) {
      onMicroAction(action, documentId);
    }
  }, [documentId, onMicroAction]);

  // Don't render on server or if not mounted
  if (!mounted || typeof window === 'undefined') {
    return null;
  }

  if (!open) {
    return null;
  }

  const previewType = canPreview(contentType);

  const overlayContent = (
    <div
      className="fixed inset-0 z-[1100] bg-black/70 flex items-center justify-center"
      onClick={handleBackdropClick}
      data-testid="document-viewer-overlay"
    >
      <div className="absolute inset-4 md:inset-8 lg:inset-12 rounded-lg bg-surface-base overflow-hidden shadow-celeste-lg flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-elevated">
          <div className="flex items-center gap-3 min-w-0">
            {getFileIcon(contentType)}
            <div className="min-w-0">
              <div className="text-sm font-medium text-zinc-200 truncate">{fileName}</div>
              <div className="text-xs text-zinc-500">{contentType}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {outlookUrl && (
              <button
                onClick={handleOpenInOutlook}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-celeste-accent hover:bg-celeste-accent-hover text-celeste-text-title rounded-md transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                <span className="hidden sm:inline">Open in Outlook</span>
              </button>
            )}

            {allowDownload && (
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md transition-colors"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Download</span>
              </button>
            )}

            {/* Micro-actions dropdown (only if document is saved) */}
            {documentId && onMicroAction && (
              <div className="relative" ref={actionsMenuRef}>
                <button
                  onClick={() => setShowActionsMenu(!showActionsMenu)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-celeste-accent hover:bg-celeste-accent-hover text-celeste-text-title rounded-md transition-colors"
                  aria-label="Document actions"
                >
                  <MoreVertical className="h-4 w-4" />
                  <span className="hidden sm:inline">Actions</span>
                </button>

                {showActionsMenu && (
                  <div className="absolute right-0 top-full mt-1 w-56 bg-surface-elevated border border-surface-border rounded-lg shadow-xl z-50 py-1">
                    <button
                      onClick={() => handleMicroAction('add_to_handover')}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors"
                    >
                      <FileUp className="h-4 w-4 text-restricted-green-400" />
                      Add to Handover
                    </button>
                    <button
                      onClick={() => handleMicroAction('attach_to_work_order')}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors"
                    >
                      <Link2 className="h-4 w-4 text-celeste-accent-400" />
                      Attach to Work Order
                    </button>
                    <button
                      onClick={() => handleMicroAction('unlink_from_work_order')}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors"
                    >
                      <Unlink className="h-4 w-4 text-restricted-yellow-400" />
                      Unlink from Work Order
                    </button>
                  </div>
                )}
              </div>
            )}

            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 rounded-md transition-colors"
              aria-label="Close viewer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-zinc-900">
          {previewType === 'pdf' && !pdfError ? (
            <object
              data={blobUrl}
              type="application/pdf"
              className="w-full h-full min-h-[500px]"
              onError={() => setPdfError(true)}
            >
              <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                <FileText className="h-16 w-16 text-zinc-600 mb-4" />
                <p className="text-zinc-400 mb-4">
                  PDF preview not available in your browser.
                </p>
                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-celeste-text-title rounded-md"
                >
                  Download PDF
                </button>
              </div>
            </object>
          ) : previewType === 'image' && !imageError ? (
            <div className="flex items-center justify-center h-full p-4">
              <img
                src={blobUrl}
                alt={fileName}
                className="max-w-full max-h-full object-contain"
                onError={() => setImageError(true)}
              />
            </div>
          ) : (
            // Fallback for unsupported types or errors
            <div className="flex flex-col items-center justify-center h-full p-8 text-center">
              {getFileIcon(contentType)}
              <h3 className="text-lg font-medium text-zinc-300 mt-4 mb-2">
                Preview not available
              </h3>
              <p className="text-sm text-zinc-500 mb-6 max-w-md">
                This file type ({contentType}) cannot be previewed in the browser.
                {outlookUrl
                  ? ' You can open it in Outlook or download it.'
                  : ' You can download it to view.'}
              </p>
              <div className="flex gap-3">
                {outlookUrl && (
                  <button
                    onClick={handleOpenInOutlook}
                    className="flex items-center gap-2 px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-celeste-text-title rounded-md transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Open in Outlook
                  </button>
                )}
                {allowDownload && (
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-md transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(overlayContent, document.body);
}
