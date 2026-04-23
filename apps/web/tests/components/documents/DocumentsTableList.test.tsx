/**
 * Unit tests for DocumentsTableList.
 *
 * Covers the contracts the component promises to callers of /documents:
 *  - Header clicks cycle sort: asc → desc → unset
 *  - aria-sort reflects current state
 *  - Row click fires onSelect(id)
 *  - Null / empty cells render '—' and sort to the end regardless of dir
 *  - Empty docs array renders the "No documents." empty state
 *  - Loading state shows a spinner line when docs are also empty
 *  - Selected row gets the teal-bg highlight
 *
 * No network, no DOM portals, no timers — pure React unit tests.
 */

import * as React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import DocumentsTableList from '@/components/documents/DocumentsTableList';
import type { Doc } from '@/components/documents/docTreeBuilder';

// Keep bundler happy under classic JSX runtime.
void React;

// ── Factory ────────────────────────────────────────────────────────────────
function doc(partial: Partial<Doc> & { id: string; filename: string }): Doc {
  return {
    id: partial.id,
    filename: partial.filename,
    doc_type: partial.doc_type ?? null,
    original_path: null,
    storage_path: '',
    size_bytes: partial.size_bytes ?? null,
    uploaded_by_name: partial.uploaded_by_name ?? null,
    created_at: partial.created_at ?? '2026-01-01T00:00:00Z',
    updated_at: partial.updated_at ?? null,
    content_type: null,
  };
}

beforeEach(() => {
  // Clean sessionStorage so sort-state persistence doesn't leak across tests
  window.sessionStorage.clear();
});


describe('DocumentsTableList — empty states', () => {
  it('renders "No documents." when docs is empty', () => {
    render(<DocumentsTableList docs={[]} onSelect={() => {}} />);
    expect(screen.getByText(/no documents/i)).toBeInTheDocument();
  });

  it('renders loading message when isLoading and docs empty', () => {
    render(<DocumentsTableList docs={[]} onSelect={() => {}} isLoading />);
    expect(screen.getByText(/loading documents/i)).toBeInTheDocument();
  });
});


describe('DocumentsTableList — row rendering', () => {
  it('renders one row per document with filename visible', () => {
    render(
      <DocumentsTableList
        docs={[
          doc({ id: 'd1', filename: 'alpha.pdf' }),
          doc({ id: 'd2', filename: 'bravo.pdf' }),
        ]}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('alpha.pdf')).toBeInTheDocument();
    expect(screen.getByText('bravo.pdf')).toBeInTheDocument();
  });

  it('renders em-dash for null/empty cells', () => {
    render(
      <DocumentsTableList
        docs={[doc({ id: 'd1', filename: 'a.pdf', size_bytes: null, uploaded_by_name: null })]}
        onSelect={() => {}}
      />
    );
    // At least 3 em-dashes (size, uploaded_by, updated_at all null)
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(3);
  });

  it('formats file size in human-readable units', () => {
    render(
      <DocumentsTableList
        docs={[
          doc({ id: 'd1', filename: 'tiny.txt', size_bytes: 500 }),
          doc({ id: 'd2', filename: 'medium.pdf', size_bytes: 2048 }),
          doc({ id: 'd3', filename: 'large.zip', size_bytes: 5 * 1024 * 1024 }),
        ]}
        onSelect={() => {}}
      />
    );
    expect(screen.getByText('500 B')).toBeInTheDocument();
    expect(screen.getByText('2.0 KB')).toBeInTheDocument();
    expect(screen.getByText('5.0 MB')).toBeInTheDocument();
  });

  it('fires onSelect when a row is clicked', () => {
    const onSelect = vi.fn();
    render(
      <DocumentsTableList
        docs={[doc({ id: 'd1', filename: 'a.pdf' })]}
        onSelect={onSelect}
      />
    );
    fireEvent.click(screen.getByText('a.pdf').closest('tr')!);
    expect(onSelect).toHaveBeenCalledWith('d1');
  });
});


describe('DocumentsTableList — sorting', () => {
  const docs = [
    doc({ id: 'd1', filename: 'charlie.pdf', size_bytes: 1000 }),
    doc({ id: 'd2', filename: 'alpha.pdf',   size_bytes: 500 }),
    doc({ id: 'd3', filename: 'bravo.pdf',   size_bytes: 2000 }),
  ];

  function filenameColumn(container: HTMLElement): string[] {
    return Array.from(container.querySelectorAll('tbody tr'))
      .map((row) => within(row as HTMLElement).getAllByRole('cell')[0].textContent?.trim() ?? '');
  }

  it('clicking filename header sorts asc then desc then unset', () => {
    const { container } = render(<DocumentsTableList docs={docs} onSelect={() => {}} />);

    const filenameHdr = screen.getByText('Filename').closest('th')!;

    // Initial — whatever order given (d1, d2, d3)
    expect(filenameColumn(container)).toEqual(['charlie.pdf', 'alpha.pdf', 'bravo.pdf']);
    expect(filenameHdr.getAttribute('aria-sort')).toBe('none');

    // First click — ASC
    fireEvent.click(filenameHdr);
    expect(filenameColumn(container)).toEqual(['alpha.pdf', 'bravo.pdf', 'charlie.pdf']);
    expect(filenameHdr.getAttribute('aria-sort')).toBe('ascending');

    // Second click — DESC
    fireEvent.click(filenameHdr);
    expect(filenameColumn(container)).toEqual(['charlie.pdf', 'bravo.pdf', 'alpha.pdf']);
    expect(filenameHdr.getAttribute('aria-sort')).toBe('descending');

    // Third click — unset
    fireEvent.click(filenameHdr);
    expect(filenameColumn(container)).toEqual(['charlie.pdf', 'alpha.pdf', 'bravo.pdf']);
    expect(filenameHdr.getAttribute('aria-sort')).toBe('none');
  });

  it('numeric column (size) sorts numerically, not alphabetically', () => {
    const { container } = render(<DocumentsTableList docs={docs} onSelect={() => {}} />);
    fireEvent.click(screen.getByText('Size').closest('th')!);

    // Ascending by size: 500 (alpha), 1000 (charlie), 2000 (bravo)
    expect(filenameColumn(container)).toEqual(['alpha.pdf', 'charlie.pdf', 'bravo.pdf']);
  });

  it('nulls sort to the end regardless of direction', () => {
    const withNulls = [
      doc({ id: 'd1', filename: 'has-size.pdf', size_bytes: 100 }),
      doc({ id: 'd2', filename: 'no-size-a.pdf', size_bytes: null }),
      doc({ id: 'd3', filename: 'no-size-b.pdf', size_bytes: null }),
    ];
    const { container } = render(<DocumentsTableList docs={withNulls} onSelect={() => {}} />);

    fireEvent.click(screen.getByText('Size').closest('th')!); // asc
    expect(filenameColumn(container)[0]).toBe('has-size.pdf'); // non-null first

    fireEvent.click(screen.getByText('Size').closest('th')!); // desc
    // Even DESC: the ONE non-null row is first; nulls are at the end
    expect(filenameColumn(container)[0]).toBe('has-size.pdf');
  });

  it('persists sort state to sessionStorage', () => {
    render(<DocumentsTableList docs={docs} onSelect={() => {}} />);
    fireEvent.click(screen.getByText('Filename').closest('th')!);
    const raw = window.sessionStorage.getItem('celeste:documents:sort');
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed).toEqual({ key: 'filename', dir: 'asc' });
  });

  it('restores sort state from sessionStorage on mount', () => {
    window.sessionStorage.setItem(
      'celeste:documents:sort',
      JSON.stringify({ key: 'filename', dir: 'desc' })
    );
    const { container } = render(<DocumentsTableList docs={docs} onSelect={() => {}} />);
    expect(filenameColumn(container)).toEqual(['charlie.pdf', 'bravo.pdf', 'alpha.pdf']);
  });
});


describe('DocumentsTableList — selection + a11y', () => {
  it('row with matching id gets aria-selected=true', () => {
    render(
      <DocumentsTableList
        docs={[doc({ id: 'd1', filename: 'a.pdf' }), doc({ id: 'd2', filename: 'b.pdf' })]}
        onSelect={() => {}}
        selectedDocId="d2"
      />
    );
    const rows = screen.getAllByRole('row').filter((r) => r.getAttribute('aria-selected') !== null);
    const selected = rows.find((r) => r.getAttribute('aria-selected') === 'true');
    expect(selected).toBeTruthy();
    expect(within(selected!).getByText('b.pdf')).toBeInTheDocument();
  });

  it('headers are keyboard-accessible (Enter triggers sort)', () => {
    const docs2 = [
      doc({ id: 'd1', filename: 'b.pdf' }),
      doc({ id: 'd2', filename: 'a.pdf' }),
    ];
    render(<DocumentsTableList docs={docs2} onSelect={() => {}} />);
    const hdr = screen.getByText('Filename').closest('th')!;
    hdr.focus();
    fireEvent.keyDown(hdr, { key: 'Enter' });
    expect(hdr.getAttribute('aria-sort')).toBe('ascending');
  });

  it('rows are keyboard-accessible (Enter fires onSelect)', () => {
    const onSelect = vi.fn();
    render(
      <DocumentsTableList docs={[doc({ id: 'd1', filename: 'a.pdf' })]} onSelect={onSelect} />
    );
    const row = screen.getByText('a.pdf').closest('tr')!;
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith('d1');
  });
});
