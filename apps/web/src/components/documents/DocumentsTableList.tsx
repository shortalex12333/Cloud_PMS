'use client';

/**
 * DocumentsTableList — documents-specific column spec + thin wrapper around
 * the shared `EntityTableList` component.
 *
 * Original bespoke implementation (PR #664) was extracted into
 * `apps/web/src/features/entity-list/components/EntityTableList.tsx`
 * (PR feat/documents-entity-table-list) so every lens shares one renderer,
 * one sort-state schema, one set of tokens, one keyboard-nav contract. This
 * file now defines only:
 *
 *   1. `DOCUMENT_COLUMNS` — the column spec for documents (Filename, Type,
 *      System, OEM, Model, Uploaded by, Size, Created, Updated)
 *   2. A backward-compatible wrapper component so existing call sites
 *      (`<DocumentsTableList docs=… onSelect=… selectedDocId=… />`) keep
 *      working without migration.
 *
 * Everything non-documents-specific — sort cycle (asc → desc → unset),
 * aria-sort, keyboard nav, null-to-end sort semantics, sessionStorage
 * persistence, token-driven styling — lives in EntityTableList.
 */

import * as React from 'react';
import {
  EntityTableList,
  type EntityTableColumn,
} from '@/features/entity-list/components/EntityTableList';
import type { Doc } from './docTreeBuilder';

// ── Formatters (pure — exported for tests if needed) ────────────────────────

function formatSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.toISOString().slice(0, 10);
  } catch {
    return '—';
  }
}

// ── The Doc type may carry filter-only fields added by richer callers;
//    cast at the column-accessor level so we don't force `Doc` itself to
//    declare them. Matches the pattern in filterDocs.ts (DocRich). ─────────
type DocRichLike = Doc & {
  system_type?: string | null;
  oem?: string | null;
  model?: string | null;
};

// ── Column spec ────────────────────────────────────────────────────────────

export const DOCUMENT_COLUMNS: EntityTableColumn<DocRichLike>[] = [
  {
    key: 'filename',
    label: 'Filename',
    accessor: (d) => d.filename,
    sortAccessor: (d) => (d.filename ?? '').toLowerCase(),
    minWidth: 280,
    wrap: true,
    maxWidth: 420,
  },
  {
    key: 'doc_type',
    label: 'Type',
    accessor: (d) => d.doc_type ?? '',
    sortAccessor: (d) => (d.doc_type ?? '').toLowerCase() || null,
    minWidth: 120,
  },
  {
    key: 'system_type',
    label: 'System',
    accessor: (d) => d.system_type ?? '',
    sortAccessor: (d) => (d.system_type ?? '').toLowerCase() || null,
    minWidth: 120,
  },
  {
    key: 'oem',
    label: 'OEM',
    accessor: (d) => d.oem ?? '',
    sortAccessor: (d) => (d.oem ?? '').toLowerCase() || null,
    minWidth: 100,
  },
  {
    key: 'model',
    label: 'Model',
    accessor: (d) => d.model ?? '',
    sortAccessor: (d) => (d.model ?? '').toLowerCase() || null,
    mono: true,
    minWidth: 120,
  },
  {
    key: 'uploaded_by_name',
    label: 'Uploaded by',
    accessor: (d) => d.uploaded_by_name ?? '',
    sortAccessor: (d) => (d.uploaded_by_name ?? '').toLowerCase() || null,
    minWidth: 140,
  },
  {
    key: 'size_bytes',
    label: 'Size',
    accessor: (d) => formatSize(d.size_bytes),
    sortAccessor: (d) => d.size_bytes ?? null,
    align: 'right',
    mono: true,
    minWidth: 80,
  },
  {
    key: 'created_at',
    label: 'Created',
    accessor: (d) => formatDate(d.created_at),
    sortAccessor: (d) => d.created_at ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'updated_at',
    label: 'Updated',
    accessor: (d) => formatDate(d.updated_at),
    sortAccessor: (d) => d.updated_at ?? null,
    mono: true,
    minWidth: 110,
  },
];

// ── Backward-compatible wrapper ────────────────────────────────────────────

export interface DocumentsTableListProps {
  docs: DocRichLike[];
  onSelect: (id: string) => void;
  /** UUID of the currently-selected doc (highlighted row). */
  selectedDocId?: string | null;
  /** Optional loading state. */
  isLoading?: boolean;
}

export default function DocumentsTableList({
  docs,
  onSelect,
  selectedDocId,
  isLoading,
}: DocumentsTableListProps) {
  return (
    <EntityTableList<DocRichLike>
      rows={docs}
      columns={DOCUMENT_COLUMNS}
      onSelect={(id) => onSelect(id)}
      selectedId={selectedDocId ?? null}
      domain="documents"
      isLoading={isLoading}
      emptyMessage="No documents."
      loadingMessage="Loading documents…"
    />
  );
}
