/**
 * Unit tests for the shared `EntityTableList` component.
 *
 * Focus: the GENERIC contracts every lens relies on. Per-lens column specs
 * (DOCUMENT_COLUMNS, CERTIFICATE_COLUMNS, etc.) live in each lens's own
 * module and get their own tests there. These tests use a tiny synthetic
 * `Row` type so the component's behaviour is exercised independently of
 * any specific lens.
 *
 * Contracts verified:
 *   - empty rows → empty-state copy
 *   - isLoading + empty → loading copy
 *   - one row per input, accessor drives the cell text
 *   - null / empty accessor returns render as em-dash
 *   - `render` slot overrides `accessor` for display (but sort uses sortAccessor)
 *   - click fires onSelect(id, yachtId)
 *   - Enter keydown on row fires onSelect
 *   - Enter/Space keydown on header toggles sort
 *   - aria-sort reflects current sort state
 *   - cycle: none → asc → desc → none
 *   - numeric column sorts numerically (not lexicographically)
 *   - nulls sort to END regardless of direction
 *   - sort state persisted per `domain` prop (celeste:<domain>:sort)
 *   - sort state restored on mount from sessionStorage
 *   - two tables with different `domain` props do NOT share sort state
 *   - selected row has aria-selected=true
 *   - compareValues helper is correct (null-end, numeric, string)
 */

import * as React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {
  EntityTableList,
  compareValues,
  type EntityTableColumn,
} from '@/features/entity-list/components/EntityTableList';

void React; // classic JSX runtime

// ── Fixtures ───────────────────────────────────────────────────────────────

interface Row {
  id: string;
  yachtId?: string;
  name: string;
  qty: number | null;
  dt?: string | null;
}

const BASE_COLUMNS: EntityTableColumn<Row>[] = [
  {
    key: 'name',
    label: 'Name',
    accessor: (r) => r.name,
    sortAccessor: (r) => r.name.toLowerCase(),
  },
  {
    key: 'qty',
    label: 'Qty',
    accessor: (r) => (r.qty ?? '') as string | number,
    sortAccessor: (r) => r.qty,
    align: 'right',
    mono: true,
  },
  {
    key: 'dt',
    label: 'Date',
    accessor: (r) => r.dt ?? '',
    sortAccessor: (r) => r.dt ?? null,
  },
];

function rowsByName(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll('tbody tr')).map(
    (r) => within(r as HTMLElement).getAllByRole('cell')[0].textContent?.trim() ?? '',
  );
}

beforeEach(() => {
  window.sessionStorage.clear();
});


// ── compareValues pure helper ──────────────────────────────────────────────

describe('compareValues', () => {
  it('numbers compared numerically', () => {
    expect(compareValues(10, 2, 'asc')).toBeGreaterThan(0);
    expect(compareValues(10, 2, 'desc')).toBeLessThan(0);
  });

  it('strings compared lexicographically', () => {
    expect(compareValues('banana', 'apple', 'asc')).toBeGreaterThan(0);
    expect(compareValues('banana', 'apple', 'desc')).toBeLessThan(0);
  });

  it('nulls sort to END regardless of direction', () => {
    expect(compareValues(null, 5, 'asc')).toBeGreaterThan(0);
    expect(compareValues(5, null, 'asc')).toBeLessThan(0);
    // Even DESC — nulls still at the end
    expect(compareValues(null, 5, 'desc')).toBeGreaterThan(0);
    expect(compareValues(5, null, 'desc')).toBeLessThan(0);
  });

  it('undefined treated like null', () => {
    expect(compareValues(undefined, 5, 'asc')).toBeGreaterThan(0);
    expect(compareValues(5, undefined, 'desc')).toBeLessThan(0);
  });

  it('null vs null → 0 (stable order)', () => {
    expect(compareValues(null, null, 'asc')).toBe(0);
  });
});


// ── Empty / loading states ─────────────────────────────────────────────────

describe('EntityTableList — empty / loading', () => {
  it('renders empty message when rows is empty', () => {
    render(
      <EntityTableList<Row>
        rows={[]}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    expect(screen.getByText('No results.')).toBeInTheDocument();
  });

  it('renders custom empty message', () => {
    render(
      <EntityTableList<Row>
        rows={[]}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
        emptyMessage="No widgets here."
      />
    );
    expect(screen.getByText('No widgets here.')).toBeInTheDocument();
  });

  it('renders loading message when isLoading and rows empty', () => {
    render(
      <EntityTableList<Row>
        rows={[]}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
        isLoading
        loadingMessage="Loading widgets…"
      />
    );
    expect(screen.getByText('Loading widgets…')).toBeInTheDocument();
  });
});


// ── Cell rendering ─────────────────────────────────────────────────────────

describe('EntityTableList — cell rendering', () => {
  const rows: Row[] = [
    { id: '1', name: 'Apple', qty: 5, dt: '2026-03-01' },
    { id: '2', name: 'Banana', qty: null, dt: null },
  ];

  it('renders one row per input', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2 data rows
  });

  it('accessor drives cell text', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.getByText('Banana')).toBeInTheDocument();
  });

  it('null / empty accessor returns render as em-dash', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    // Row 2 has null qty and null dt — two em-dashes expected
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
  });

  it('render slot overrides accessor for display only', () => {
    const withRender: EntityTableColumn<Row>[] = [
      {
        key: 'name',
        label: 'Name',
        accessor: (r) => r.name,
        // Custom renderer injects a badge
        render: (r) => <strong data-testid={`badge-${r.id}`}>{r.name.toUpperCase()}</strong>,
      },
    ];
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={withRender}
        onSelect={() => {}}
        domain="test"
      />
    );
    expect(screen.getByTestId('badge-1')).toHaveTextContent('APPLE');
    expect(screen.getByTestId('badge-2')).toHaveTextContent('BANANA');
  });
});


// ── Row interaction ────────────────────────────────────────────────────────

describe('EntityTableList — row interaction', () => {
  it('click fires onSelect(id, yachtId)', () => {
    const onSelect = vi.fn();
    render(
      <EntityTableList<Row>
        rows={[{ id: 'r1', yachtId: 'y1', name: 'A', qty: 1 }]}
        columns={BASE_COLUMNS}
        onSelect={onSelect}
        domain="test"
      />
    );
    fireEvent.click(screen.getByText('A').closest('tr')!);
    expect(onSelect).toHaveBeenCalledWith('r1', 'y1');
  });

  it('Enter keydown fires onSelect', () => {
    const onSelect = vi.fn();
    render(
      <EntityTableList<Row>
        rows={[{ id: 'r1', name: 'A', qty: 1 }]}
        columns={BASE_COLUMNS}
        onSelect={onSelect}
        domain="test"
      />
    );
    const row = screen.getByText('A').closest('tr')!;
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith('r1', undefined);
  });

  it('selectedId → aria-selected=true on matching row', () => {
    render(
      <EntityTableList<Row>
        rows={[
          { id: 'a', name: 'A', qty: 1 },
          { id: 'b', name: 'B', qty: 2 },
        ]}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
        selectedId="b"
      />
    );
    const rows = screen.getAllByRole('row').filter((r) => r.getAttribute('aria-selected') !== null);
    const selected = rows.find((r) => r.getAttribute('aria-selected') === 'true');
    expect(selected).toBeTruthy();
    expect(within(selected!).getByText('B')).toBeInTheDocument();
  });
});


// ── Sorting ────────────────────────────────────────────────────────────────

describe('EntityTableList — sort cycle', () => {
  const rows: Row[] = [
    { id: '1', name: 'Charlie', qty: 10 },
    { id: '2', name: 'Alpha',   qty: 5 },
    { id: '3', name: 'Bravo',   qty: 20 },
  ];

  it('headers toggle: none → asc → desc → none', () => {
    const { container } = render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    const hdr = screen.getByText('Name').closest('th')!;

    expect(hdr.getAttribute('aria-sort')).toBe('none');
    expect(rowsByName(container)).toEqual(['Charlie', 'Alpha', 'Bravo']);

    fireEvent.click(hdr);
    expect(hdr.getAttribute('aria-sort')).toBe('ascending');
    expect(rowsByName(container)).toEqual(['Alpha', 'Bravo', 'Charlie']);

    fireEvent.click(hdr);
    expect(hdr.getAttribute('aria-sort')).toBe('descending');
    expect(rowsByName(container)).toEqual(['Charlie', 'Bravo', 'Alpha']);

    fireEvent.click(hdr);
    expect(hdr.getAttribute('aria-sort')).toBe('none');
    expect(rowsByName(container)).toEqual(['Charlie', 'Alpha', 'Bravo']); // original
  });

  it('numeric column sorts numerically, not lexicographically', () => {
    const { container } = render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    fireEvent.click(screen.getByText('Qty').closest('th')!);
    // asc: 5, 10, 20 → Alpha (5), Charlie (10), Bravo (20)
    expect(rowsByName(container)).toEqual(['Alpha', 'Charlie', 'Bravo']);
  });

  it('nulls sort to END regardless of direction (via sortAccessor null)', () => {
    const withNulls: Row[] = [
      { id: '1', name: 'Has-10', qty: 10 },
      { id: '2', name: 'No-qty-a', qty: null },
      { id: '3', name: 'No-qty-b', qty: null },
    ];
    const { container } = render(
      <EntityTableList<Row>
        rows={withNulls}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );

    fireEvent.click(screen.getByText('Qty').closest('th')!); // asc
    expect(rowsByName(container)[0]).toBe('Has-10'); // non-null first

    fireEvent.click(screen.getByText('Qty').closest('th')!); // desc
    expect(rowsByName(container)[0]).toBe('Has-10'); // STILL first — nulls at end
  });

  it('keyboard accessible headers — Enter toggles sort', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="test"
      />
    );
    const hdr = screen.getByText('Name').closest('th')!;
    fireEvent.keyDown(hdr, { key: 'Enter' });
    expect(hdr.getAttribute('aria-sort')).toBe('ascending');
    fireEvent.keyDown(hdr, { key: ' ' });
    expect(hdr.getAttribute('aria-sort')).toBe('descending');
  });
});


// ── Sort-state persistence (per domain) ────────────────────────────────────

describe('EntityTableList — sort-state persistence', () => {
  const rows: Row[] = [
    { id: '1', name: 'Charlie', qty: 10 },
    { id: '2', name: 'Alpha',   qty: 5 },
    { id: '3', name: 'Bravo',   qty: 20 },
  ];

  it('persists under key `celeste:<domain>:sort`', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="widgets"
      />
    );
    fireEvent.click(screen.getByText('Name').closest('th')!);
    const raw = window.sessionStorage.getItem('celeste:widgets:sort');
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!)).toEqual({ key: 'name', dir: 'asc' });
  });

  it('restores sort state on mount', () => {
    window.sessionStorage.setItem(
      'celeste:widgets:sort',
      JSON.stringify({ key: 'name', dir: 'desc' })
    );
    const { container } = render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="widgets"
      />
    );
    expect(rowsByName(container)).toEqual(['Charlie', 'Bravo', 'Alpha']);
  });

  it('two tables with different `domain` do NOT share sort state', () => {
    const { unmount } = render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="widgets"
      />
    );
    fireEvent.click(screen.getByText('Name').closest('th')!);
    expect(window.sessionStorage.getItem('celeste:widgets:sort')).not.toBeNull();
    unmount();

    // Second table with a different domain should start unsorted
    const { container } = render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="gadgets"
      />
    );
    expect(rowsByName(container)).toEqual(['Charlie', 'Alpha', 'Bravo']);
    expect(window.sessionStorage.getItem('celeste:gadgets:sort')).toBeNull();
  });

  it('clearing back to none removes the sessionStorage key', () => {
    render(
      <EntityTableList<Row>
        rows={rows}
        columns={BASE_COLUMNS}
        onSelect={() => {}}
        domain="widgets"
      />
    );
    const hdr = screen.getByText('Name').closest('th')!;
    fireEvent.click(hdr); // asc
    fireEvent.click(hdr); // desc
    fireEvent.click(hdr); // none → removes key
    expect(window.sessionStorage.getItem('celeste:widgets:sort')).toBeNull();
  });
});
