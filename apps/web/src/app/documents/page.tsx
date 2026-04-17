'use client';

/**
 * Documents page — PR-D1.
 *
 * Two modes, driven by the shared Subbar search state:
 *   - Empty query  → <DocumentTree>  (folder hierarchy from v_documents_enriched)
 *   - Non-empty    → <DocumentsSearchResults>  (F1 search, spotlight row layout)
 *
 * In both modes, clicking a document opens <EntityDetailOverlay> with the
 * existing DocumentContent lens.
 *
 * Data: fetched from the Render API (/api/vessel/{id}/domain/documents/records)
 * with a high limit so the tree has the full corpus. Pagination is not
 * meaningful for a tree.
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { DocumentContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { useAuth } from '@/hooks/useAuth';
import { useShellContext } from '@/components/shell/ShellContext';
import { supabase } from '@/lib/supabaseClient';
import DocumentTree from '@/components/documents/DocumentTree';
import DocumentsSearchResults from '@/components/documents/DocumentsSearchResults';
import type { Doc } from '@/components/documents/docTreeBuilder';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const TREE_PAGE_SIZE = 1000;

/** Shape returned by /api/vessel/{id}/domain/documents/records. */
interface DocApiRecord {
  id?: string;
  filename?: string;
  doc_type?: string | null;
  original_path?: string | null;
  storage_path?: string | null;
  size_bytes?: number | null;
  uploaded_by_name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  content_type?: string | null;
  // Formatter fallbacks from the API (title, meta, etc.) — ignored here.
  [key: string]: unknown;
}

function toDoc(record: DocApiRecord): Doc | null {
  if (!record.id || typeof record.id !== 'string') return null;
  return {
    id: record.id,
    filename: (record.filename as string) || 'Untitled',
    doc_type: (record.doc_type as string | null) ?? null,
    original_path: (record.original_path as string | null) ?? null,
    storage_path: (record.storage_path as string) ?? '',
    size_bytes:
      typeof record.size_bytes === 'number' ? record.size_bytes : null,
    uploaded_by_name:
      typeof record.uploaded_by_name === 'string' ? record.uploaded_by_name : null,
    created_at: (record.created_at as string) ?? new Date(0).toISOString(),
    updated_at: (record.updated_at as string | null) ?? null,
    content_type: (record.content_type as string | null) ?? null,
  };
}

function LensContent() {
  return (
    <div className={lensStyles.root}>
      <DocumentContent />
    </div>
  );
}

function DocumentsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const { user } = useAuth();
  const shell = useShellContext();

  const yachtId = user?.yachtId ?? null;
  const vesselName = user?.yachtName ?? 'Vessel';

  const handleSelect = React.useCallback(
    (id: string, yachtIdArg?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtIdArg) params.set('yacht_id', yachtIdArg);
      router.push(`/documents?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/documents${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  // Fetch docs for the tree. Uses pipeline-core API with a large page size so
  // the entire vessel corpus is available for folder assembly.
  const docsQuery = useQuery<Doc[]>({
    queryKey: ['documents', 'tree', yachtId],
    enabled: !!yachtId,
    staleTime: 30_000,
    queryFn: async () => {
      if (!yachtId) return [];
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) throw new Error('Not authenticated');

      const params = new URLSearchParams();
      params.set('limit', String(TREE_PAGE_SIZE));
      params.set('offset', '0');
      params.set('sort', 'updated_at');

      const url = `${API_BASE}/api/vessel/${yachtId}/domain/documents/records?${params.toString()}`;
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error(`API ${response.status}: ${response.statusText}`);
      }
      const payload = await response.json();
      const records: DocApiRecord[] = payload.records || payload.items || [];
      const docs: Doc[] = [];
      for (const r of records) {
        const d = toDoc(r);
        if (d) docs.push(d);
      }
      return docs;
    },
  });

  const searchActive = shell.debouncedQuery.trim().length > 0;

  return (
    <div className="h-full bg-surface-base" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {searchActive ? (
        <DocumentsSearchResults
          query={shell.debouncedQuery}
          onSelect={(id) => handleSelect(id)}
        />
      ) : docsQuery.isLoading ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: 1,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              border: '2px solid var(--border-sub)',
              borderTopColor: 'var(--mark)',
              borderRadius: '50%',
            }}
            className="animate-spin"
          />
        </div>
      ) : docsQuery.error ? (
        <div
          style={{
            padding: '24px 16px',
            color: 'var(--red)',
            fontFamily: 'var(--font-sans)',
            fontSize: 13,
          }}
        >
          Failed to load documents.
        </div>
      ) : (
        <DocumentTree
          docs={docsQuery.data ?? []}
          selectedDocId={selectedId}
          onSelect={(id) => handleSelect(id)}
          vesselName={vesselName}
          yachtId={yachtId}
        />
      )}

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
          <div
            style={{
              width: '32px',
              height: '32px',
              border: '2px solid var(--border-sub)',
              borderTopColor: 'var(--mark)',
              borderRadius: '50%',
            }}
            className="animate-spin"
          />
        </div>
      }
    >
      <DocumentsPageContent />
    </React.Suspense>
  );
}
