/**
 * Unit tests for filterDocs — the pure function that applies an
 * ActiveFilters map to a document list on the client side.
 *
 * Contracts covered:
 *   - empty filters → input returned unchanged
 *   - text filter → case-insensitive substring (ILIKE-style)
 *   - null field → excluded by a non-empty text filter
 *   - content_type_group → collapses MIME string into the 5-bucket enum
 *   - tags_text → matches any element of the ARRAY column (case-insensitive)
 *   - date-range → inclusive on both ends; open-ended from/to works
 *   - unknown filter key → ignored (forward-compat)
 *   - multiple filters → AND semantics across keys
 */

import { describe, it, expect } from 'vitest';
import { filterDocs, contentTypeGroup, type DocRich } from '@/components/documents/filterDocs';

function doc(partial: Partial<DocRich> & { id: string; filename: string }): DocRich {
  return {
    id: partial.id,
    filename: partial.filename,
    doc_type: partial.doc_type ?? null,
    original_path: partial.original_path ?? null,
    storage_path: partial.storage_path ?? '',
    size_bytes: partial.size_bytes ?? null,
    uploaded_by_name: partial.uploaded_by_name ?? null,
    created_at: partial.created_at ?? '2026-01-01T00:00:00Z',
    updated_at: partial.updated_at ?? null,
    content_type: partial.content_type ?? null,
    system_type: partial.system_type ?? null,
    oem: partial.oem ?? null,
    model: partial.model ?? null,
    tags: partial.tags ?? null,
  };
}


describe('filterDocs — no filters', () => {
  it('returns input unchanged when filters is empty', () => {
    const docs = [doc({ id: '1', filename: 'a.pdf' }), doc({ id: '2', filename: 'b.pdf' })];
    expect(filterDocs(docs, {})).toEqual(docs);
  });
});


describe('filterDocs — text fields (ILIKE-style)', () => {
  const docs = [
    doc({ id: '1', filename: 'a.pdf', oem: 'ABB', model: 'V100', uploaded_by_name: 'Alice' }),
    doc({ id: '2', filename: 'b.pdf', oem: 'MTU', model: '16V4000', uploaded_by_name: 'Bob' }),
    doc({ id: '3', filename: 'c.pdf', oem: null, model: null, uploaded_by_name: null }),
  ];

  it('oem: case-insensitive substring match', () => {
    expect(filterDocs(docs, { oem: 'abb' }).map(d => d.id)).toEqual(['1']);
    expect(filterDocs(docs, { oem: 'MTU' }).map(d => d.id)).toEqual(['2']);
    expect(filterDocs(docs, { oem: 't' }).map(d => d.id)).toEqual(['2']);   // MTU contains t
  });

  it('model: case-insensitive substring match', () => {
    expect(filterDocs(docs, { model: 'v100' }).map(d => d.id)).toEqual(['1']);
    expect(filterDocs(docs, { model: '4000' }).map(d => d.id)).toEqual(['2']);
  });

  it('uploaded_by_name: resolved-name filter', () => {
    expect(filterDocs(docs, { uploaded_by_name: 'ALI' }).map(d => d.id)).toEqual(['1']);
  });

  it('null field is filtered out by a non-empty text filter', () => {
    // doc 3 has null oem — should not match 'anything'
    expect(filterDocs(docs, { oem: 'anything' })).toHaveLength(0);
  });

  it('empty text filter is treated as "no filter"', () => {
    expect(filterDocs(docs, { oem: '' })).toHaveLength(3);
    expect(filterDocs(docs, { oem: '   ' })).toHaveLength(3);  // whitespace only
  });
});


describe('filterDocs — content_type_group (MIME bucket)', () => {
  const docs = [
    doc({ id: 'pdf',  filename: 'a.pdf',  content_type: 'application/pdf' }),
    doc({ id: 'img',  filename: 'a.png',  content_type: 'image/png' }),
    doc({ id: 'xls',  filename: 'a.xlsx', content_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
    doc({ id: 'doc',  filename: 'a.docx', content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
    doc({ id: 'csv',  filename: 'a.csv',  content_type: 'text/csv' }),
    doc({ id: 'zip',  filename: 'a.zip',  content_type: 'application/zip' }),
    doc({ id: 'none', filename: 'a.???',  content_type: null }),
  ];

  it('contentTypeGroup helper maps MIMEs to the 5 buckets', () => {
    expect(contentTypeGroup('application/pdf')).toBe('pdf');
    expect(contentTypeGroup('image/png')).toBe('image');
    expect(contentTypeGroup('image/jpeg')).toBe('image');
    expect(contentTypeGroup('application/vnd.ms-excel')).toBe('spreadsheet');
    expect(contentTypeGroup('text/csv')).toBe('spreadsheet');
    expect(contentTypeGroup('application/msword')).toBe('word');
    expect(contentTypeGroup('text/plain')).toBe('word');
    expect(contentTypeGroup('application/zip')).toBe('other');
    expect(contentTypeGroup(null)).toBe('other');
    expect(contentTypeGroup(undefined)).toBe('other');
  });

  it('filter by pdf returns only application/pdf', () => {
    expect(filterDocs(docs, { content_type_group: 'pdf' }).map(d => d.id)).toEqual(['pdf']);
  });

  it('filter by image returns image/*', () => {
    expect(filterDocs(docs, { content_type_group: 'image' }).map(d => d.id)).toEqual(['img']);
  });

  it('filter by spreadsheet returns excel + csv', () => {
    expect(filterDocs(docs, { content_type_group: 'spreadsheet' }).map(d => d.id).sort())
      .toEqual(['csv', 'xls']);
  });

  it('filter by word returns word docs', () => {
    expect(filterDocs(docs, { content_type_group: 'word' }).map(d => d.id)).toEqual(['doc']);
  });

  it('filter by other catches unknown/null MIMEs', () => {
    expect(filterDocs(docs, { content_type_group: 'other' }).map(d => d.id).sort())
      .toEqual(['none', 'zip']);
  });

  it('supports multi-select shape (string array)', () => {
    expect(filterDocs(docs, { content_type_group: ['pdf', 'image'] }).map(d => d.id).sort())
      .toEqual(['img', 'pdf']);
  });
});


describe('filterDocs — tags_text (ARRAY column)', () => {
  const docs = [
    doc({ id: '1', filename: 'a', tags: ['safety', 'bridge'] }),
    doc({ id: '2', filename: 'b', tags: ['engineering', 'Bridge-relocation'] }),
    doc({ id: '3', filename: 'c', tags: null }),
    doc({ id: '4', filename: 'd', tags: [] }),
  ];

  it('matches any tag containing the needle (case-insensitive)', () => {
    expect(filterDocs(docs, { tags_text: 'bridge' }).map(d => d.id).sort()).toEqual(['1', '2']);
    expect(filterDocs(docs, { tags_text: 'SAFETY' }).map(d => d.id)).toEqual(['1']);
  });

  it('null or empty tags array is filtered out by a non-empty needle', () => {
    expect(filterDocs(docs, { tags_text: 'bridge' }).map(d => d.id)).not.toContain('3');
    expect(filterDocs(docs, { tags_text: 'bridge' }).map(d => d.id)).not.toContain('4');
  });
});


describe('filterDocs — date range', () => {
  const docs = [
    doc({ id: 'early',  filename: 'a', created_at: '2026-01-15T00:00:00Z' }),
    doc({ id: 'mid',    filename: 'b', created_at: '2026-03-10T00:00:00Z' }),
    doc({ id: 'late',   filename: 'c', created_at: '2026-06-01T00:00:00Z' }),
    doc({ id: 'nodate', filename: 'd', created_at: '' }),
  ];

  it('filters by from+to range (inclusive)', () => {
    expect(
      filterDocs(docs, { created_at: { from: '2026-02-01', to: '2026-05-01' } }).map(d => d.id)
    ).toEqual(['mid']);
  });

  it('from only — no upper bound', () => {
    expect(
      filterDocs(docs, { created_at: { from: '2026-02-01', to: '' } }).map(d => d.id).sort()
    ).toEqual(['late', 'mid']);
  });

  it('to only — no lower bound', () => {
    expect(
      filterDocs(docs, { created_at: { from: '', to: '2026-02-01' } }).map(d => d.id)
    ).toEqual(['early']);
  });

  it('docs with empty dates are excluded from any date filter', () => {
    expect(
      filterDocs(docs, { created_at: { from: '2000-01-01', to: '2099-12-31' } }).map(d => d.id)
    ).not.toContain('nodate');
  });
});


describe('filterDocs — multi-filter AND semantics', () => {
  const docs = [
    doc({ id: '1', filename: 'a', oem: 'MTU', uploaded_by_name: 'Alice' }),
    doc({ id: '2', filename: 'b', oem: 'MTU', uploaded_by_name: 'Bob' }),
    doc({ id: '3', filename: 'c', oem: 'ABB', uploaded_by_name: 'Alice' }),
  ];

  it('AND across keys — only rows matching every filter kept', () => {
    expect(
      filterDocs(docs, { oem: 'MTU', uploaded_by_name: 'alice' }).map(d => d.id)
    ).toEqual(['1']);
  });
});


describe('filterDocs — forward compat', () => {
  it('unknown filter keys are ignored', () => {
    const docs = [doc({ id: '1', filename: 'a.pdf' })];
    expect(filterDocs(docs, { unknown_key: 'anything', another: 'xyz' } as never))
      .toHaveLength(1);
  });
});
