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
import DocumentsTableList from '@/components/documents/DocumentsTableList';
import { filterDocs, type DocRich } from '@/components/documents/filterDocs';
import type { Doc } from '@/components/documents/docTreeBuilder';
import { FilterPanel } from '@/features/entity-list/components/FilterPanel';
import { DOCUMENT_FILTERS, type ActiveFilters } from '@/features/entity-list/types/filter-config';

/**
 * Three view modes for /documents:
 *   - tree   (default): folder hierarchy mirroring the storage bucket
 *   - list   (new, doc_cert_ux_change.md 2026-04-23): tabulated + sortable columns
 *   - search (implicit): active whenever the subbar query is non-empty
 *
 * The search mode pre-empts whichever explicit mode is chosen; cleared query
 * returns to the previous explicit mode.
 */
type DocsViewMode = 'tree' | 'list';
const VIEW_MODE_KEY = 'celeste:documents:viewMode';

function loadViewMode(): DocsViewMode {
  if (typeof window === 'undefined') return 'tree';
  try {
    const raw = window.sessionStorage.getItem(VIEW_MODE_KEY);
    if (raw === 'tree' || raw === 'list') return raw;
  } catch { /* ignore */ }
  return 'tree';
}

function persistViewMode(mode: DocsViewMode): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(VIEW_MODE_KEY, mode);
  } catch { /* ignore quota */ }
}

/**
 * Active-filter persistence — lives in sessionStorage so filter state
 * survives tab-local refreshes but is dropped on close. Matches the same
 * pattern used by the view-mode and table-sort state in this page.
 */
const FILTERS_KEY = 'celeste:documents:filters';

function loadFilters(): ActiveFilters {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.sessionStorage.getItem(FILTERS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as ActiveFilters) : {};
  } catch {
    return {};
  }
}

function persistFilters(filters: ActiveFilters): void {
  if (typeof window === 'undefined') return;
  try {
    if (Object.keys(filters).length === 0) {
      window.sessionStorage.removeItem(FILTERS_KEY);
    } else {
      window.sessionStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
    }
  } catch { /* ignore quota */ }
}

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
  // Filter-only columns (fed through to DocRich for client-side filterDocs)
  system_type?: string | null;
  oem?: string | null;
  model?: string | null;
  tags?: string[] | null;
  // Formatter fallbacks from the API (title, meta, etc.) — ignored here.
  [key: string]: unknown;
}

function toDoc(record: DocApiRecord): DocRich | null {
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
    // Filter-only fields (ignored by the tree builder, read by filterDocs)
    system_type: (record.system_type as string | null) ?? null,
    oem: (record.oem as string | null) ?? null,
    model: (record.model as string | null) ?? null,
    tags: Array.isArray(record.tags) ? (record.tags as string[]) : null,
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

  // View-mode state, persisted to sessionStorage
  const [viewMode, setViewMode] = React.useState<DocsViewMode>(() => loadViewMode());
  const handleViewModeChange = React.useCallback((mode: DocsViewMode) => {
    setViewMode(mode);
    persistViewMode(mode);
  }, []);

  // ── Filter state (list view only) ────────────────────────────────────────
  // Per CEO directive 2026-04-23 — rich filtration panel for /documents.
  // Spec coordinated with CERT04 + RECEIVING05 + SHOPPING_LIST (see
  // `docs/ongoing_work/certificates/CERTIFICATE_FILTER_SPEC_2026_04_23.md`).
  //
  // Filter application is CLIENT-SIDE here — the tree view already fetches the
  // full corpus (TREE_PAGE_SIZE=1000) upfront for folder assembly, so the list
  // view reuses that same in-memory data and runs `filterDocs()` over it. When
  // we eventually need true pagination (corpus > 1000 live rows), we'll migrate
  // to FilteredEntityList's server-side path that cert/receiving/shopping use.
  const [activeFilters, setActiveFilters] = React.useState<ActiveFilters>(() => loadFilters());
  const handleFilterChange = React.useCallback((next: ActiveFilters) => {
    setActiveFilters(next);
    persistFilters(next);
  }, []);

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
  // DocRich[] — includes the filter-only fields (system_type/oem/model/tags)
  // read by filterDocs() in list view. Tree code ignores the extras.
  const docsQuery = useQuery<DocRich[]>({
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
      const docs: DocRich[] = [];
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
      {/* View-mode toggle — hidden when search is active since the results view
          has its own layout that doesn't apply to the tree/list dichotomy. */}
      {!searchActive && (
        <div
          role="tablist"
          aria-label="Documents view mode"
          style={{
            display: 'flex',
            gap: 'var(--space-1)',
            padding: 'var(--space-3) var(--space-4)',
            borderBottom: '1px solid var(--border-sub)',
            background: 'var(--surface-base)',
            flexShrink: 0,
          }}
        >
          {(['tree', 'list'] as const).map((mode) => {
            const active = viewMode === mode;
            return (
              <button
                key={mode}
                role="tab"
                aria-selected={active}
                onClick={() => handleViewModeChange(mode)}
                style={{
                  padding: 'var(--space-1) var(--space-3)',
                  fontSize: 'var(--font-size-action)',
                  fontWeight: 'var(--font-weight-action)',
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  background: active ? 'var(--surface-hover)' : 'transparent',
                  border: '1px solid',
                  borderColor: active ? 'var(--border-sub)' : 'transparent',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'background var(--duration-fast) var(--ease-out)',
                }}
              >
                {mode}
              </button>
            );
          })}
        </div>
      )}

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
      ) : viewMode === 'list' ? (
        <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
          {/* Shared FilterPanel — same component cert/receiving/shopping use.
              Reads DOCUMENT_FILTERS from filter-config.ts. Categories are the
              canonical four (status-priority / dates / equipment-systems /
              properties); tokens are the canonical lens tokens — no new
              filter-scoped variables introduced. */}
          <FilterPanel
            filters={DOCUMENT_FILTERS}
            activeFilters={activeFilters}
            onChange={handleFilterChange}
            activeDomain="documents"
            totalCount={(docsQuery.data ?? []).length}
          />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <DocumentsTableList
              docs={filterDocs(docsQuery.data ?? [], activeFilters)}
              onSelect={(id) => handleSelect(id)}
              selectedDocId={selectedId}
              isLoading={docsQuery.isLoading}
            />
          </div>
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
