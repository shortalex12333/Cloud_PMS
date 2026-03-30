'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { DocumentContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import type { EntityListResult } from '@/features/entity-list/types';

interface Document {
  id: string;
  filename?: string;
  doc_type?: string;
  oem?: string;
  model?: string;
  content_type?: string;
  source?: string;
  created_at: string;
  updated_at?: string;
}

function docAdapter(doc: Document): EntityListResult {
  const title = doc.filename || doc.id.slice(0, 8);
  const docType = doc.doc_type?.replace(/_/g, ' ') || 'Document';
  return {
    id: doc.id,
    type: 'doc_metadata',
    title,
    subtitle: `${docType}${doc.oem ? ` \u00b7 ${doc.oem}` : ''}${doc.model ? ` ${doc.model}` : ''}`,
    entityRef: doc.id.slice(0, 8),
    status: docType,
    statusVariant: 'open',
    severity: null,
    age: formatAge(doc.created_at),
  };
}

function formatAge(d: string): string {
  const days = Math.floor((Date.now() - new Date(d).getTime()) / 86_400_000);
  if (days < 1) return '<1d';
  if (days < 7) return `${days}d`;
  const date = new Date(d);
  return `${date.getDate()} ${date.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function LensContent() {
  return <div className={lensStyles.root}><DocumentContent /></div>;
}

function DocumentsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/documents?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/documents${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Document>
        domain="documents"
        queryKey={['documents']}
        table="doc_metadata"
        columns="id, filename, doc_type, oem, model, content_type, source, created_at, updated_at"
        adapter={docAdapter}
        filterConfig={[]}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No documents recorded"
        sortBy="created_at"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="document" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <DocumentsPageContent />
    </React.Suspense>
  );
}
