/**
 * Unit tests for docTreeBuilder.
 *
 * Covers:
 * - Nested paths assemble into the expected folder hierarchy
 * - Files without original_path fall back to a synthetic folder per doc_type
 * - doc_type === null falls back to "Uploaded"
 * - Sort order: folders before files, alphabetical within each kind
 * - Empty input
 * - Single file (with and without original_path)
 * - Mixed: some paths, some fallbacks, multiple doc_types
 */

import { describe, it, expect } from 'vitest';
import {
  buildDocTree,
  flattenTree,
  collectAllFolderPaths,
  type Doc,
  type TreeNode,
} from '@/components/documents/docTreeBuilder';

// ── Factory helpers ─────────────────────────────────────────────────────────

function doc(partial: Partial<Doc> & { id: string; filename: string }): Doc {
  return {
    id: partial.id,
    filename: partial.filename,
    doc_type: partial.doc_type ?? null,
    original_path: partial.original_path ?? null,
    storage_path: partial.storage_path ?? `s3://bucket/${partial.id}`,
    size_bytes: partial.size_bytes ?? null,
    uploaded_by_name: partial.uploaded_by_name ?? null,
    created_at: partial.created_at ?? '2026-04-01T00:00:00Z',
    updated_at: partial.updated_at ?? null,
    content_type: partial.content_type ?? null,
  };
}

function onlyFolders(nodes: TreeNode[]): Array<{ path: string; name: string; depth: number }> {
  return nodes
    .filter((n): n is Extract<TreeNode, { kind: 'folder' }> => n.kind === 'folder')
    .map((n) => ({ path: n.path, name: n.name, depth: n.depth }));
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe('buildDocTree', () => {
  it('returns an empty array when given no docs', () => {
    expect(buildDocTree([])).toEqual([]);
  });

  it('returns an empty array when given non-array / nullish input', () => {
    // @ts-expect-error — exercising defensive branch
    expect(buildDocTree(null)).toEqual([]);
    // @ts-expect-error — exercising defensive branch
    expect(buildDocTree(undefined)).toEqual([]);
  });

  it('places a single file with no original_path under the prettified doc_type fallback folder', () => {
    const tree = buildDocTree([
      doc({
        id: 'aaaaaaaa-1111-2222-3333-444444444444',
        filename: 'mtu_service_manual.pdf',
        doc_type: 'engine_manual',
      }),
    ]);

    expect(tree).toHaveLength(1);
    const top = tree[0];
    expect(top.kind).toBe('folder');
    if (top.kind !== 'folder') throw new Error('expected folder');
    expect(top.name).toBe('Engine Manual');
    expect(top.path).toBe('__fallback__:engine_manual');
    expect(top.depth).toBe(0);
    expect(top.children).toHaveLength(1);
    expect(top.children[0].kind).toBe('file');
    if (top.children[0].kind !== 'file') throw new Error('expected file');
    expect(top.children[0].name).toBe('mtu_service_manual.pdf');
    expect(top.children[0].depth).toBe(1);
  });

  it('places a single file with a nested original_path into the correct folder chain', () => {
    const tree = buildDocTree([
      doc({
        id: 'file-1',
        filename: 'schematic.pdf',
        original_path: 'Engines/MTU/2000 Series/schematic.pdf',
      }),
    ]);

    expect(tree).toHaveLength(1);
    const engines = tree[0];
    if (engines.kind !== 'folder') throw new Error('expected folder');
    expect(engines.name).toBe('Engines');
    expect(engines.depth).toBe(0);
    expect(engines.children).toHaveLength(1);

    const mtu = engines.children[0];
    if (mtu.kind !== 'folder') throw new Error('expected folder');
    expect(mtu.name).toBe('MTU');
    expect(mtu.depth).toBe(1);
    expect(mtu.children).toHaveLength(1);

    const series = mtu.children[0];
    if (series.kind !== 'folder') throw new Error('expected folder');
    expect(series.name).toBe('2000 Series');
    expect(series.depth).toBe(2);
    expect(series.children).toHaveLength(1);

    const file = series.children[0];
    if (file.kind !== 'file') throw new Error('expected file');
    expect(file.name).toBe('schematic.pdf');
    expect(file.depth).toBe(3);
  });

  it('groups files in the same original_path folder together', () => {
    const tree = buildDocTree([
      doc({ id: 'f1', filename: 'b.pdf', original_path: 'Engines/a.pdf' }),
      doc({ id: 'f2', filename: 'a.pdf', original_path: 'Engines/b.pdf' }),
    ]);

    expect(tree).toHaveLength(1);
    const engines = tree[0];
    if (engines.kind !== 'folder') throw new Error('expected folder');
    expect(engines.children).toHaveLength(2);
    // Files are sorted alphabetically by filename
    expect(engines.children.map((c) => (c.kind === 'file' ? c.name : c.path))).toEqual([
      'a.pdf',
      'b.pdf',
    ]);
  });

  it('sorts folders before files at each level, alphabetical within each kind', () => {
    const tree = buildDocTree([
      doc({ id: 'f1', filename: 'zzz.pdf', original_path: 'zzz.pdf' }),
      doc({ id: 'f2', filename: 'alpha.pdf', original_path: 'Beta/alpha.pdf' }),
      doc({ id: 'f3', filename: 'beta.pdf', original_path: 'Alpha/beta.pdf' }),
      doc({ id: 'f4', filename: 'aaa.pdf', original_path: 'aaa.pdf' }),
    ]);

    // Top-level: Alpha (folder), Beta (folder), aaa.pdf (file), zzz.pdf (file)
    expect(tree.map((n) => (n.kind === 'folder' ? `F:${n.name}` : `f:${n.name}`))).toEqual([
      'F:Alpha',
      'F:Beta',
      'f:aaa.pdf',
      'f:zzz.pdf',
    ]);
  });

  it('groups files without original_path into fallback folders keyed by doc_type', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'invoice-01.pdf', doc_type: 'invoice' }),
      doc({ id: '2', filename: 'invoice-02.pdf', doc_type: 'invoice' }),
      doc({ id: '3', filename: 'drawing-01.pdf', doc_type: 'drawing' }),
    ]);

    const folderNames = onlyFolders(tree).map((f) => f.name);
    // Drawing < Invoice alphabetically
    expect(folderNames).toEqual(['Drawing', 'Invoice']);

    const invoiceFolder = tree.find(
      (n) => n.kind === 'folder' && n.name === 'Invoice',
    );
    if (!invoiceFolder || invoiceFolder.kind !== 'folder') throw new Error('expected folder');
    expect(invoiceFolder.children).toHaveLength(2);
    expect(invoiceFolder.children.map((c) => (c.kind === 'file' ? c.name : ''))).toEqual([
      'invoice-01.pdf',
      'invoice-02.pdf',
    ]);
  });

  it('uses "Uploaded" as the fallback folder name when doc_type is null', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'random.pdf', doc_type: null }),
    ]);
    expect(tree).toHaveLength(1);
    expect(tree[0].kind).toBe('folder');
    if (tree[0].kind !== 'folder') throw new Error('expected folder');
    expect(tree[0].name).toBe('Uploaded');
    expect(tree[0].path).toBe('__fallback__:');
  });

  it('handles a mixed set: real paths + fallbacks + multiple doc_types', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'engine.pdf', original_path: 'Manuals/engine.pdf' }),
      doc({ id: '2', filename: 'no-path-a.pdf', doc_type: 'manual' }),
      doc({ id: '3', filename: 'no-path-b.pdf', doc_type: null }),
      doc({ id: '4', filename: 'deck.pdf', original_path: 'Manuals/deck.pdf' }),
      doc({ id: '5', filename: 'drawing.pdf', original_path: 'Drawings/drawing.pdf' }),
      doc({ id: '6', filename: 'random-invoice.pdf', doc_type: 'invoice' }),
    ]);

    // Top-level folders should include: Drawings, Manuals (real paths), fallbacks
    const names = onlyFolders(tree).map((f) => f.name);
    // Sorted case-insensitively alphabetically
    expect(names).toEqual(['Drawings', 'Invoice', 'Manual', 'Manuals', 'Uploaded']);

    const manuals = tree.find((n) => n.kind === 'folder' && n.name === 'Manuals');
    if (!manuals || manuals.kind !== 'folder') throw new Error('expected folder');
    expect(manuals.children).toHaveLength(2);
    expect(manuals.children.map((c) => (c.kind === 'file' ? c.name : ''))).toEqual([
      'deck.pdf',
      'engine.pdf',
    ]);
  });

  it('normalises backslashes and collapses double slashes in original_path', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'a.pdf', original_path: 'A\\B//C/a.pdf' }),
    ]);
    const a = tree[0];
    if (a.kind !== 'folder') throw new Error('expected folder');
    expect(a.name).toBe('A');
    const b = a.children[0];
    if (b.kind !== 'folder') throw new Error('expected folder');
    expect(b.name).toBe('B');
    const c = b.children[0];
    if (c.kind !== 'folder') throw new Error('expected folder');
    expect(c.name).toBe('C');
    expect(c.children[0].kind).toBe('file');
  });

  it('tolerates empty strings in original_path by trimming them out', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'x.pdf', original_path: '/Engines//x.pdf' }),
    ]);
    expect(tree).toHaveLength(1);
    const engines = tree[0];
    if (engines.kind !== 'folder') throw new Error('expected folder');
    expect(engines.name).toBe('Engines');
    expect(engines.children[0].kind).toBe('file');
  });

  it('produces leaf files that carry file metadata straight through', () => {
    const updatedAt = '2026-04-15T12:00:00Z';
    const tree = buildDocTree([
      doc({
        id: 'x',
        filename: 'manual.pdf',
        original_path: 'a/manual.pdf',
        doc_type: 'manual',
        size_bytes: 12_345,
        updated_at: updatedAt,
        content_type: 'application/pdf',
      }),
    ]);
    const a = tree[0];
    if (a.kind !== 'folder') throw new Error('expected folder');
    const file = a.children[0];
    if (file.kind !== 'file') throw new Error('expected file');
    expect(file._docId).toBe('x');
    expect(file.doc_type).toBe('manual');
    expect(file.size_bytes).toBe(12_345);
    expect(file.updated_at).toBe(updatedAt);
    expect(file.content_type).toBe('application/pdf');
  });
});

describe('flattenTree', () => {
  it('returns only root-level rows when nothing is expanded', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'a.pdf', original_path: 'Engines/a.pdf' }),
      doc({ id: '2', filename: 'b.pdf', original_path: 'Deck/b.pdf' }),
    ]);
    const flat = flattenTree(tree, new Set());
    expect(flat.map((n) => (n.kind === 'folder' ? n.path : n.name))).toEqual(['Deck', 'Engines']);
  });

  it('walks into expanded folders', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'a.pdf', original_path: 'Engines/a.pdf' }),
      doc({ id: '2', filename: 'b.pdf', original_path: 'Deck/b.pdf' }),
    ]);
    const flat = flattenTree(tree, new Set(['Engines']));
    expect(flat.map((n) => (n.kind === 'folder' ? `F:${n.path}` : `f:${n.name}`))).toEqual([
      'F:Deck',
      'F:Engines',
      'f:a.pdf',
    ]);
  });
});

describe('collectAllFolderPaths', () => {
  it('collects every folder path, including nested and fallback', () => {
    const tree = buildDocTree([
      doc({ id: '1', filename: 'a.pdf', original_path: 'A/B/a.pdf' }),
      doc({ id: '2', filename: 'b.pdf', doc_type: 'manual' }),
    ]);
    const paths = collectAllFolderPaths(tree).sort();
    expect(paths).toEqual(['A', 'A/B', '__fallback__:manual'].sort());
  });
});
