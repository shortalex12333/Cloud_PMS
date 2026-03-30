'use client';

/**
 * PaginationFooter — Page-based pagination for domain list views
 *
 * Shows "Showing 1–50 of N" with page numbers.
 * Hidden when total ≤ 50 (no pagination needed).
 *
 * Spec: v3-v5-prompts.md §FRONTEND01 Task 4.4
 */

import * as React from 'react';

interface PaginationFooterProps {
  currentPage: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
}

export function PaginationFooter({
  currentPage,
  pageSize,
  totalCount,
  onPageChange,
}: PaginationFooterProps) {
  if (totalCount <= pageSize) return null;

  const totalPages = Math.ceil(totalCount / pageSize);
  const from = (currentPage - 1) * pageSize + 1;
  const to = Math.min(currentPage * pageSize, totalCount);

  // Generate page numbers (show max 5 pages with ellipsis)
  const pages: (number | '...')[] = [];
  if (totalPages <= 5) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push('...');
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push('...');
    pages.push(totalPages);
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        padding: '10px 16px',
        borderTop: '1px solid var(--border-faint)',
      }}
    >
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono, ui-monospace, monospace)', color: 'var(--txt-ghost)' }}>
        Showing {from}\u2013{to} of {totalCount}
      </span>

      <div style={{ display: 'flex', gap: 2, marginLeft: 8 }}>
        {/* Prev */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          style={{
            height: 22,
            padding: '0 6px',
            borderRadius: 3,
            border: '1px solid var(--border-sub)',
            background: 'var(--surface-el)',
            fontSize: 10,
            color: currentPage <= 1 ? 'var(--txt-ghost)' : 'var(--txt3)',
            cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
            opacity: currentPage <= 1 ? 0.4 : 1,
          }}
        >
          \u2190
        </button>

        {/* Page numbers */}
        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} style={{ fontSize: 10, color: 'var(--txt-ghost)', padding: '0 4px', display: 'flex', alignItems: 'center' }}>
              \u2026
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              style={{
                height: 22,
                minWidth: 22,
                padding: '0 4px',
                borderRadius: 3,
                border: `1px solid ${p === currentPage ? 'var(--mark-hover)' : 'var(--border-sub)'}`,
                background: p === currentPage ? 'var(--teal-bg)' : 'var(--surface-el)',
                fontSize: 10,
                fontFamily: 'var(--font-mono, ui-monospace, monospace)',
                color: p === currentPage ? 'var(--mark)' : 'var(--txt3)',
                cursor: 'pointer',
              }}
            >
              {p}
            </button>
          )
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          style={{
            height: 22,
            padding: '0 6px',
            borderRadius: 3,
            border: '1px solid var(--border-sub)',
            background: 'var(--surface-el)',
            fontSize: 10,
            color: currentPage >= totalPages ? 'var(--txt-ghost)' : 'var(--txt3)',
            cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
            opacity: currentPage >= totalPages ? 0.4 : 1,
          }}
        >
          \u2192
        </button>
      </div>
    </div>
  );
}
