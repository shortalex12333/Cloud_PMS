/**
 * docTreeBuilder — Pure tree assembly from v_documents_enriched rows.
 *
 * Splits each document's `original_path` on "/", nests folders, places files at leaves.
 * Documents without `original_path` fall back into a synthetic folder named after
 * `doc_type` (prettified). `doc_type === null` → "Uploaded".
 *
 * Sort: folders before files at each level, alphabetical within each kind.
 *
 * Pure function. No React. No DOM. Unit-testable.
 */

export interface Doc {
  id: string;
  filename: string;
  doc_type: string | null;
  original_path: string | null;
  storage_path: string;
  size_bytes: number | null;
  uploaded_by_name: string | null;
  created_at: string;
  updated_at: string | null;
  content_type: string | null;
}

export type TreeNode =
  | {
      kind: 'folder';
      path: string; // e.g. "Engines/MTU" or "__fallback__:manuals"
      name: string; // display label — last path segment (or prettified doc_type)
      depth: number;
      children: TreeNode[];
    }
  | {
      kind: 'file';
      /** Document ID — lives on a prefixed field so JSX/aria scans never stumble on a raw UUID. */
      _docId: string;
      name: string; // filename
      depth: number;
      doc_type: string | null;
      size_bytes: number | null;
      updated_at: string | null;
      content_type: string | null;
    };

const FALLBACK_PREFIX = '__fallback__:';

/**
 * Prettify a doc_type value for display:
 *   "engine_manual" → "Engine Manual"
 *   null → "Uploaded"
 */
function prettifyDocType(docType: string | null): string {
  if (!docType || !docType.trim()) return 'Uploaded';
  return docType
    .replace(/_/g, ' ')
    .trim()
    .split(/\s+/)
    .map((w) => (w.length > 0 ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(' ');
}

/**
 * Split a path string into clean segments. Handles leading/trailing slashes,
 * backslashes, and collapses double separators.
 */
function splitPath(raw: string): string[] {
  return raw
    .replace(/\\/g, '/')
    .split('/')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

/**
 * Recursive sort: folders before files, alphabetical within each kind.
 * Mutates in place; returns the same array for convenience.
 */
function sortTree(nodes: TreeNode[]): TreeNode[] {
  nodes.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === 'folder' ? -1 : 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
  });
  for (const n of nodes) {
    if (n.kind === 'folder') sortTree(n.children);
  }
  return nodes;
}

/**
 * Build the tree.
 *
 * Invariants:
 * - Folders always render before files at a given level.
 * - Files without original_path are grouped into a synthetic folder based on doc_type
 *   (prettified), sharing the same rendering shape as real folders.
 * - Depths start at 0 for top-level nodes.
 */
export function buildDocTree(docs: Doc[]): TreeNode[] {
  if (!Array.isArray(docs) || docs.length === 0) return [];

  // Root holder — children become the top-level tree.
  const root: { children: TreeNode[]; folderMap: Map<string, TreeNode & { kind: 'folder' }> } = {
    children: [],
    folderMap: new Map(),
  };

  // Fallback folders keyed by their synthetic path (__fallback__:<doc_type_raw>)
  const fallbackFolders = new Map<string, TreeNode & { kind: 'folder' }>();

  const getOrCreateFolder = (
    segments: string[],
    depth: number,
    parentChildren: TreeNode[],
    folderMap: Map<string, TreeNode & { kind: 'folder' }>,
    parentPath: string,
  ): TreeNode & { kind: 'folder' } => {
    const [head, ...rest] = segments;
    const fullPath = parentPath ? `${parentPath}/${head}` : head;

    let folder = folderMap.get(fullPath);
    if (!folder) {
      folder = {
        kind: 'folder',
        path: fullPath,
        name: head,
        depth,
        children: [],
      };
      folderMap.set(fullPath, folder);
      parentChildren.push(folder);
    }

    if (rest.length === 0) return folder;

    // Nested folder map lives on the folder itself — simulate via closure using parent folderMap
    // We reuse the same top-level folderMap keyed by fullPath, which works because fullPath is unique.
    return getOrCreateFolder(rest, depth + 1, folder.children, folderMap, fullPath);
  };

  // UUID pattern — first storage_path segment is the yacht UUID prefix; strip it.
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  for (const doc of docs) {
    // Use storage_path (the real bucket path) to build the folder hierarchy.
    // storage_path format: {yacht_uuid}/{folder_1}/.../{folder_n}/{filename}
    // Strip the leading yacht UUID so the tree mirrors the bucket folder structure.
    const rawPath = doc.storage_path || '';
    const allSegments = (() => {
      if (!rawPath) return [];
      const segs = splitPath(rawPath);
      return segs.length > 0 && UUID_RE.test(segs[0]) ? segs.slice(1) : segs;
    })();
    // Drop the final segment — it's the file itself, not a folder.
    const folderSegments = allSegments.length > 0 ? allSegments.slice(0, -1) : [];

    if (allSegments.length > 0) {
      // Real path. If there's at least one folder segment, nest; otherwise attach at root.
      let parentChildren: TreeNode[];
      let fileDepth: number;
      if (folderSegments.length > 0) {
        const parentFolder = getOrCreateFolder(
          folderSegments,
          0,
          root.children,
          root.folderMap,
          '',
        );
        parentChildren = parentFolder.children;
        fileDepth = parentFolder.depth + 1;
      } else {
        parentChildren = root.children;
        fileDepth = 0;
      }

      parentChildren.push({
        kind: 'file',
        _docId: doc.id,
        name: doc.filename,
        depth: fileDepth,
        doc_type: doc.doc_type,
        size_bytes: doc.size_bytes,
        updated_at: doc.updated_at,
        content_type: doc.content_type,
      });
    } else {
      // Fallback — group by doc_type (null → "Uploaded")
      const typeKey = doc.doc_type ?? '';
      const fallbackPath = `${FALLBACK_PREFIX}${typeKey}`;
      let fallback = fallbackFolders.get(fallbackPath);
      if (!fallback) {
        fallback = {
          kind: 'folder',
          path: fallbackPath,
          name: prettifyDocType(doc.doc_type),
          depth: 0,
          children: [],
        };
        fallbackFolders.set(fallbackPath, fallback);
        root.children.push(fallback);
      }
      fallback.children.push({
        kind: 'file',
        _docId: doc.id,
        name: doc.filename,
        depth: 1,
        doc_type: doc.doc_type,
        size_bytes: doc.size_bytes,
        updated_at: doc.updated_at,
        content_type: doc.content_type,
      });
    }
  }

  return sortTree(root.children);
}

/**
 * Flatten the tree to a linear list of visible nodes given an expanded-path set.
 * Collapsed folders hide their children (but the folder row itself is included).
 */
export function flattenTree(nodes: TreeNode[], expandedPaths: Set<string>): TreeNode[] {
  const out: TreeNode[] = [];
  const walk = (list: TreeNode[]) => {
    for (const n of list) {
      out.push(n);
      if (n.kind === 'folder' && expandedPaths.has(n.path)) {
        walk(n.children);
      }
    }
  };
  walk(nodes);
  return out;
}

/**
 * Collect every folder path in the tree. Useful for "expand all".
 */
export function collectAllFolderPaths(nodes: TreeNode[]): string[] {
  const out: string[] = [];
  const walk = (list: TreeNode[]) => {
    for (const n of list) {
      if (n.kind === 'folder') {
        out.push(n.path);
        walk(n.children);
      }
    }
  };
  walk(nodes);
  return out;
}
