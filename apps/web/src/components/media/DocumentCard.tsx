'use client';

/**
 * DocumentCard — Preview card for document files.
 *
 * Per UI_SPEC.md File Preview Card spec:
 * - background: var(--surface-primary)
 * - border-radius: var(--radius-md) = 12px
 * - padding: 12px 16px
 * - height: 48px
 * - display: flex, align-items: center, gap: 12px
 * - cursor: pointer
 * - Left: document icon (📄 for PDF, 📝 for DOCX, etc.)
 * - Middle: filename (truncated), file size formatted
 * - Right: chevron → opens Document lens
 * - Hover: surface-hover background
 *
 * All semantic tokens, zero raw hex values.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { formatFileSize, getDocumentIcon } from './fileUtils';

// ============================================================================
// TYPES
// ============================================================================

export interface DocumentFile {
  id: string;
  /** Signed URL for download (not shown to user) */
  url: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface DocumentCardProps {
  file: DocumentFile;
  /** Called when card is clicked — opens Document lens with file ID */
  onClick: () => void;
  className?: string;
}

// ============================================================================
// DOCUMENT CARD
// ============================================================================

/**
 * DocumentCard — Clickable preview card that opens the Document lens.
 *
 * Usage:
 * ```tsx
 * <DocumentCard
 *   file={file}
 *   onClick={() => openDocumentLens(file.id)}
 * />
 * ```
 */
export function DocumentCard({ file, onClick, className }: DocumentCardProps) {
  const icon = getDocumentIcon(file.filename);
  const sizeLabel = formatFileSize(file.size_bytes);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'file-preview-card',
        // Focus ring
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive',
        'mb-2 last:mb-0',
        className
      )}
    >
      {/* Document icon — 20px, txt-tertiary per UI_SPEC.md */}
      <span
        className="text-[20px] text-txt-tertiary flex-shrink-0"
        aria-hidden="true"
      >
        {icon}
      </span>

      {/* Filename + size */}
      <div className="flex-1 min-w-0">
        {/* Filename: 14px/500/txt-primary, truncated per UI_SPEC.md */}
        <p className="text-[14px] font-medium text-txt-primary truncate leading-[1.4]">
          {file.filename}
        </p>
        {/* File size: 12px/400/txt-tertiary per UI_SPEC.md */}
        <p className="text-[12px] text-txt-tertiary leading-[1.4]">
          {sizeLabel}
        </p>
      </div>

      {/* Chevron — signals "opens Document lens" */}
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

