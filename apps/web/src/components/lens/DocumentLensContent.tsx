'use client';

/**
 * DocumentLensContent - Document detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /documents/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * Action gates follow the universal lens pattern: getAction returns null
 * when the server says the action is unavailable for this user/state.
 * Never inline getAction calls in JSX — store results as named consts.
 *
 * Download and "open in new tab" links are field-driven browser navigation,
 * not server actions — they do not go through executeAction.
 */

// No LensHeader — EntityLensPage's RouteLayout owns back/close navigation for this entity

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { RelatedEntitiesSection, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

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

export function DocumentLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Action consts
  const archiveAction = getAction('document.archive');
  const replaceAction = getAction('update_document');

  // Entity fields — try both top-level and payload sub-object
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const filename = ((entity?.filename ?? entity?.name ?? payload.filename) as string | undefined) ?? 'Document';
  const title = ((entity?.title ?? payload.title) as string | undefined) ?? filename;
  const description = (entity?.description ?? payload.description) as string | undefined;
  const mime_type = ((entity?.mime_type ?? payload.mime_type) as string | undefined) ?? 'application/octet-stream';
  const file_size = (entity?.file_size ?? payload.file_size) as number | undefined;
  const url = (entity?.url ?? entity?.file_url ?? payload.url ?? payload.file_url) as string | undefined;
  const thumbnail_url = (entity?.thumbnail_url ?? payload.thumbnail_url) as string | undefined;
  const created_at = (entity?.created_at ?? payload.created_at) as string | undefined;
  const created_by = (entity?.created_by ?? payload.created_by) as string | undefined;
  const classification = (entity?.classification ?? payload.classification) as string | undefined;
  const equipment_id = (entity?.equipment_id ?? payload.equipment_id) as string | undefined;
  const equipment_name = (entity?.equipment_name ?? payload.equipment_name) as string | undefined;
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  const docType = getDocumentTypeLabel(mime_type);
  const isMedia = isMediaType(mime_type);

  // Format file size
  let sizeDisplay = '—';
  if (file_size) {
    if (file_size < 1024) sizeDisplay = `${file_size} B`;
    else if (file_size < 1024 * 1024) sizeDisplay = `${(file_size / 1024).toFixed(1)} KB`;
    else sizeDisplay = `${(file_size / (1024 * 1024)).toFixed(1)} MB`;
  }

  // RelatedEntitiesSection navigation
  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) => {
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId));
    },
    [router]
  );

  const vitalSigns: VitalSign[] = [
    { label: 'Type', value: docType },
    { label: 'Size', value: sizeDisplay },
    { label: 'Classification', value: classification ?? 'General' },
    {
      label: 'Equipment',
      value: equipment_name ?? 'N/A',
      onClick: equipment_id ? () => handleNavigate('equipment', equipment_id) : undefined,
    },
    { label: 'Uploaded', value: created_at ? formatRelativeTime(created_at) : '—' },
  ];

  return (
    <>
      {/* No LensHeader — EntityLensPage's RouteLayout owns back/close navigation */}

      <VitalSignsRow signs={vitalSigns} />

      {/* field-driven browser links — not server actions */}
      {url && (
        <div className="mt-4 flex gap-3 flex-wrap">
          {/* field-driven browser link — not a server action */}
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            Open in New Tab
          </a>
          {/* field-driven browser link — not a server action */}
          <a
            href={url}
            download
            className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download
          </a>
        </div>
      )}

      <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

      {/* Document Preview */}
      <div className="mt-6">
        <SectionContainer title="Preview" stickyTop={56}>
          {!url ? (
            <p className="typo-body text-celeste-text-muted">No preview available.</p>
          ) : isMedia ? (
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
            <iframe
              src={url}
              title={title}
              className="w-full h-[600px] rounded-lg border border-surface-border"
            />
          ) : (
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
              {/* field-driven browser link — not a server action */}
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

      {related_entities.length > 0 && (
        <div className="mt-6">
          <RelatedEntitiesSection entities={related_entities} onNavigate={handleNavigate} stickyTop={56} />
        </div>
      )}

      {/* Server action buttons — rendered only when the backend includes them in available_actions */}
      {(archiveAction !== null || replaceAction !== null) && (
        <div className="mt-6 flex gap-3 pt-4 border-t border-surface-border flex-wrap">
          {replaceAction !== null && (
            <GhostButton
              onClick={() => executeAction('update_document')}
              disabled={replaceAction?.disabled ?? isLoading}
              title={replaceAction?.disabled_reason ?? undefined}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              Replace Document
            </GhostButton>
          )}
          {archiveAction !== null && (
            <GhostButton
              onClick={() => executeAction('document.archive')}
              disabled={archiveAction?.disabled ?? isLoading}
              title={archiveAction?.disabled_reason ?? undefined}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              Archive
            </GhostButton>
          )}
        </div>
      )}
    </>
  );
}
