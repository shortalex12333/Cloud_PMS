'use client';

/**
 * DocumentLensContent - Inner content for Document lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 *
 * Per rules.md: Documents are viewed in a full-screen lens, not downloaded.
 * Media files (images, videos) render inline.
 * Text documents (PDF, etc.) render with preview/viewer.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { useDocumentActions, useDocumentPermissions } from '@/hooks/useDocumentActions';
import { GhostButton } from '@/components/ui/GhostButton';

export interface DocumentLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function getDocumentTypeLabel(mimeType: string): string {
  if (mimeType.startsWith('image/')) return 'Image';
  if (mimeType.startsWith('video/')) return 'Video';
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'Spreadsheet';
  if (mimeType.includes('document') || mimeType.includes('word')) return 'Document';
  return 'File';
}

function isMediaType(mimeType: string): boolean {
  return mimeType.startsWith('image/') || mimeType.startsWith('video/');
}

export function DocumentLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: DocumentLensContentProps) {
  const actions = useDocumentActions(id);
  const perms = useDocumentPermissions();

  // Map data
  const filename = (data.filename as string) || (data.name as string) || 'Document';
  const title = (data.title as string) || filename;
  const description = data.description as string | undefined;
  const mime_type = (data.mime_type as string) || 'application/octet-stream';
  const file_size = data.file_size as number | undefined;
  const url = data.url as string | undefined;
  const thumbnail_url = data.thumbnail_url as string | undefined;
  const created_at = data.created_at as string | undefined;
  const created_by = data.created_by as string | undefined;
  const classification = data.classification as string | undefined;
  const equipment_id = data.equipment_id as string | undefined;
  const equipment_name = data.equipment_name as string | undefined;

  const docType = getDocumentTypeLabel(mime_type);
  const isMedia = isMediaType(mime_type);

  // Format file size
  let sizeDisplay = '—';
  if (file_size) {
    if (file_size < 1024) sizeDisplay = `${file_size} B`;
    else if (file_size < 1024 * 1024) sizeDisplay = `${(file_size / 1024).toFixed(1)} KB`;
    else sizeDisplay = `${(file_size / (1024 * 1024)).toFixed(1)} MB`;
  }

  const vitalSigns: VitalSign[] = [
    { label: 'Type', value: docType },
    { label: 'Size', value: sizeDisplay },
    { label: 'Classification', value: classification ?? 'General' },
    { label: 'Equipment', value: equipment_name ?? 'N/A', onClick: equipment_id && onNavigate ? () => onNavigate('equipment', equipment_id) : undefined },
    { label: 'Uploaded', value: created_at ? formatRelativeTime(created_at) : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Document" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            subtitle={filename !== title ? filename : undefined}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {perms.canDownload && url && (
          <div className="mt-4">
            <GhostButton
              onClick={() => window.open(url, '_blank')}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              Download
            </GhostButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Document Preview */}
        <div className="mt-6">
          <SectionContainer title="Preview" stickyTop={56}>
            {!url ? (
              <p className="typo-body text-celeste-text-muted">No preview available.</p>
            ) : isMedia ? (
              // Render media inline
              mime_type.startsWith('image/') ? (
                <img
                  src={url}
                  alt={title}
                  className="max-w-full rounded-lg"
                />
              ) : (
                <video
                  src={url}
                  controls
                  className="max-w-full rounded-lg"
                />
              )
            ) : mime_type === 'application/pdf' ? (
              // Render PDF in iframe
              <iframe
                src={url}
                title={title}
                className="w-full h-[600px] rounded-lg border border-surface-border"
              />
            ) : (
              // Link to open in new tab
              <div className="p-4 bg-surface-secondary rounded-lg">
                <p className="typo-body text-celeste-text-muted mb-3">
                  This file type cannot be previewed inline.
                </p>
                {thumbnail_url && (
                  <img
                    src={thumbnail_url}
                    alt={`${title} thumbnail`}
                    className="max-w-[200px] rounded mb-3"
                  />
                )}
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-celeste-blue hover:text-celeste-blue-hover typo-body"
                >
                  Open in new tab →
                </a>
              </div>
            )}
          </SectionContainer>
        </div>

        {description && (
          <div className="mt-6">
            <SectionContainer title="Description" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">{description}</p>
            </SectionContainer>
          </div>
        )}

        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 typo-body">
              <dt className="text-celeste-text-muted">Filename</dt>
              <dd className="text-celeste-text-primary break-all">{filename}</dd>
              <dt className="text-celeste-text-muted">MIME Type</dt>
              <dd className="text-celeste-text-primary">{mime_type}</dd>
              {created_by && (
                <>
                  <dt className="text-celeste-text-muted">Uploaded By</dt>
                  <dd className="text-celeste-text-primary">{created_by}</dd>
                </>
              )}
              {created_at && (
                <>
                  <dt className="text-celeste-text-muted">Upload Date</dt>
                  <dd className="text-celeste-text-primary">{new Date(created_at).toLocaleString()}</dd>
                </>
              )}
            </dl>
          </SectionContainer>
        </div>
      </main>
    </div>
  );
}

