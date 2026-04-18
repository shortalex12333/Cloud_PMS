'use client';

/**
 * DocumentTree — Folder/file tree view for a yacht's documents.
 *
 * Data comes pre-shaped from buildDocTree(). The tree listens to the shared
 * Subbar search via useShellContext(); when searchQuery is non-empty, the
 * parent page swaps this tree for <DocumentsSearchResults>, so this component
 * only handles the tree mode.
 *
 * Renders:
 * - Root row with vesselName (mono, 14px) — clickable toggles expand-all.
 * - Folder rows: chevron + folder icon + name + file-count badge. 44px min-h.
 * - File rows: depth indent (16px/level) + file icon + mono filename + meta.
 *
 * Keyboard: ↑/↓ moves selection, ← collapses folder / moves to parent folder,
 * → expands folder, Enter opens doc or toggles folder.
 *
 * sessionStorage cache per yacht_id: expanded paths, scrollTop, selectedDocId.
 *
 * No UUIDs in rendered DOM. Doc IDs live on data attributes where needed for
 * click routing; text content is always filename / folder name.
 */

import * as React from 'react';
import {
  ChevronRight,
  Folder,
  FileText,
  FileImage,
  FileSpreadsheet,
  FileArchive,
  FileCode,
  File as FileIcon,
  type LucideIcon,
} from 'lucide-react';
import {
  buildDocTree,
  collectAllFolderPaths,
  flattenTree,
  type Doc,
  type TreeNode,
} from './docTreeBuilder';
import styles from './DocumentTree.module.css';

// ── Types ───────────────────────────────────────────────────────────────────

interface DocumentTreeProps {
  docs: Doc[];
  selectedDocId: string | null;
  onSelect: (docId: string) => void;
  vesselName: string;
  /** Optional yacht id used to scope the sessionStorage cache. */
  yachtId?: string | null;
}

interface TreeSessionState {
  expandedPaths: string[];
  scrollTop: number;
  selectedDocId: string | null;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

const SESSION_KEY_PREFIX = 'documents_tree_view__';

function readSessionState(yachtId: string | null | undefined): TreeSessionState | null {
  if (!yachtId || typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(`${SESSION_KEY_PREFIX}${yachtId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<TreeSessionState>;
    return {
      expandedPaths: Array.isArray(parsed.expandedPaths) ? parsed.expandedPaths : [],
      scrollTop: typeof parsed.scrollTop === 'number' ? parsed.scrollTop : 0,
      selectedDocId: typeof parsed.selectedDocId === 'string' ? parsed.selectedDocId : null,
    };
  } catch {
    return null;
  }
}

function writeSessionState(
  yachtId: string | null | undefined,
  state: TreeSessionState,
): void {
  if (!yachtId || typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(
      `${SESSION_KEY_PREFIX}${yachtId}`,
      JSON.stringify(state),
    );
  } catch {
    // Ignore quota / private-mode errors
  }
}

/** content_type → icon. Marine docs are mostly PDFs, but cover common types. */
function iconForContentType(contentType: string | null | undefined): LucideIcon {
  if (!contentType) return FileIcon;
  const ct = contentType.toLowerCase();
  if (ct.startsWith('image/')) return FileImage;
  if (ct.includes('pdf')) return FileText;
  if (ct.includes('spreadsheet') || ct.includes('excel') || ct.includes('csv')) {
    return FileSpreadsheet;
  }
  if (ct.includes('zip') || ct.includes('archive') || ct.includes('compressed')) {
    return FileArchive;
  }
  if (ct.includes('json') || ct.includes('xml') || ct.includes('code')) return FileCode;
  if (ct.startsWith('text/')) return FileText;
  return FileIcon;
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes < 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(kb < 10 ? 1 : 0)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(mb < 10 ? 1 : 0)} MB`;
  return `${(mb / 1024).toFixed(1)} GB`;
}

function formatDateShort(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const days = Math.floor((Date.now() - d.getTime()) / 86_400_000);
  if (days < 1) return 'today';
  if (days < 7) return `${days}d ago`;
  return `${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function prettifyDocType(docType: string | null | undefined): string {
  if (!docType) return 'Uploaded';
  return docType
    .replace(/_/g, ' ')
    .split(' ')
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(' ');
}

/** Count file descendants of a folder, including nested. */
function countFiles(node: TreeNode): number {
  if (node.kind === 'file') return 1;
  let total = 0;
  for (const child of node.children) total += countFiles(child);
  return total;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function DocumentTree({
  docs,
  selectedDocId,
  onSelect,
  vesselName,
  yachtId,
}: DocumentTreeProps) {
  // Build tree from raw docs. Stable across re-renders unless docs change.
  const tree = React.useMemo(() => buildDocTree(docs), [docs]);

  // Restore cached state on mount (once per yachtId).
  const initialState = React.useMemo(
    () => readSessionState(yachtId),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [yachtId],
  );

  const [expandedPaths, setExpandedPaths] = React.useState<Set<string>>(() => {
    if (initialState?.expandedPaths && initialState.expandedPaths.length > 0) {
      return new Set(initialState.expandedPaths);
    }
    // Default: expand top-level folders so users see something.
    return new Set(
      tree.filter((n) => n.kind === 'folder').map((n) => (n as Extract<TreeNode, { kind: 'folder' }>).path),
    );
  });

  // When docs load later, widen the default expansion to top-level folders
  // if nothing was restored.
  React.useEffect(() => {
    if (initialState?.expandedPaths && initialState.expandedPaths.length > 0) return;
    if (tree.length === 0) return;
    setExpandedPaths((prev) => {
      if (prev.size > 0) return prev;
      const next = new Set<string>();
      for (const n of tree) {
        if (n.kind === 'folder') next.add(n.path);
      }
      return next;
    });
    // Only widen on fresh mount / first-docs-arrival; intentionally no tree dep loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs.length]);

  // Flatten to visible rows based on expanded state.
  const flat = React.useMemo(() => flattenTree(tree, expandedPaths), [tree, expandedPaths]);

  // Selection + focus index. Selection is a docId (string) for files; folders use path.
  const [focusIndex, setFocusIndex] = React.useState<number>(() => {
    const restoredId = initialState?.selectedDocId ?? selectedDocId ?? null;
    if (!restoredId) return 0;
    const idx = flat.findIndex((n) => n.kind === 'file' && n._docId === restoredId);
    return idx >= 0 ? idx : 0;
  });

  // Re-sync focusIndex when selectedDocId changes from outside (URL, overlay close).
  React.useEffect(() => {
    if (!selectedDocId) return;
    const idx = flat.findIndex((n) => n.kind === 'file' && n._docId === selectedDocId);
    if (idx >= 0 && idx !== focusIndex) setFocusIndex(idx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDocId]);

  // Refs — scroller for scrollTop persistence, row refs for focus scroll-into-view.
  const scrollerRef = React.useRef<HTMLDivElement | null>(null);
  const rowRefs = React.useRef<Array<HTMLDivElement | null>>([]);

  // Restore scroll position after first paint.
  React.useEffect(() => {
    if (initialState?.scrollTop && scrollerRef.current) {
      scrollerRef.current.scrollTop = initialState.scrollTop;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced persist — 150ms.
  const persistTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const persistState = React.useCallback(() => {
    if (!yachtId) return;
    if (persistTimer.current) clearTimeout(persistTimer.current);
    persistTimer.current = setTimeout(() => {
      writeSessionState(yachtId, {
        expandedPaths: Array.from(expandedPaths),
        scrollTop: scrollerRef.current?.scrollTop ?? 0,
        selectedDocId: selectedDocId ?? null,
      });
    }, 150);
  }, [yachtId, expandedPaths, selectedDocId]);

  React.useEffect(() => {
    persistState();
    return () => {
      if (persistTimer.current) clearTimeout(persistTimer.current);
    };
  }, [persistState]);

  // Toggle a single folder.
  const toggleFolder = React.useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  // Expand-all / collapse-all (triggered by root row click).
  const toggleExpandAll = React.useCallback(() => {
    const all = collectAllFolderPaths(tree);
    setExpandedPaths((prev) => {
      if (prev.size >= all.length) return new Set();
      return new Set(all);
    });
  }, [tree]);

  // Keyboard navigation.
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (flat.length === 0) return;
      const currentNode = flat[focusIndex];

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          setFocusIndex((i) => Math.min(flat.length - 1, i + 1));
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          setFocusIndex((i) => Math.max(0, i - 1));
          break;
        }
        case 'ArrowRight': {
          if (currentNode?.kind === 'folder') {
            e.preventDefault();
            if (!expandedPaths.has(currentNode.path)) {
              toggleFolder(currentNode.path);
            } else {
              // Already expanded — move into first child if any.
              setFocusIndex((i) => Math.min(flat.length - 1, i + 1));
            }
          }
          break;
        }
        case 'ArrowLeft': {
          if (currentNode?.kind === 'folder' && expandedPaths.has(currentNode.path)) {
            e.preventDefault();
            toggleFolder(currentNode.path);
          } else if (currentNode?.kind === 'file') {
            e.preventDefault();
            // Jump to the parent folder if we can find it in flat.
            for (let i = focusIndex - 1; i >= 0; i--) {
              const candidate = flat[i];
              if (candidate.kind === 'folder' && candidate.depth < currentNode.depth) {
                setFocusIndex(i);
                break;
              }
            }
          }
          break;
        }
        case 'Enter': {
          e.preventDefault();
          if (currentNode?.kind === 'folder') {
            toggleFolder(currentNode.path);
          } else if (currentNode?.kind === 'file') {
            onSelect(currentNode._docId);
          }
          break;
        }
        default:
          break;
      }
    },
    [flat, focusIndex, expandedPaths, toggleFolder, onSelect],
  );

  // Scroll focused row into view.
  React.useEffect(() => {
    const el = rowRefs.current[focusIndex];
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'nearest' });
    }
  }, [focusIndex]);

  // Persist scrollTop while user scrolls (debounced via the same timer).
  const handleScroll = React.useCallback(() => {
    persistState();
  }, [persistState]);

  // ── Render ──

  const totalFolders = collectAllFolderPaths(tree).length;
  const totalExpanded = expandedPaths.size;
  const allExpanded = totalFolders > 0 && totalExpanded >= totalFolders;

  // Update row refs array size.
  rowRefs.current.length = flat.length;

  return (
    <div className={styles.root} data-testid="documents-tree">
      <div
        className={styles.rootRow}
        onClick={toggleExpandAll}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleExpandAll();
          }
        }}
        aria-label={`${vesselName} — ${allExpanded ? 'collapse all' : 'expand all'}`}
        data-testid="document-tree-root"
      >
        <Folder size={16} className={styles.rootIcon} aria-hidden />
        <span className={styles.rootName}>{vesselName || 'Vessel'}</span>
        <span className={styles.rootCount}>{docs.length}</span>
      </div>

      <div
        className={styles.scroller}
        ref={scrollerRef}
        onScroll={handleScroll}
        onKeyDown={handleKeyDown}
        tabIndex={0}
        role="tree"
        aria-label="Documents tree"
      >
        {tree.length === 0 ? (
          <div className={styles.empty} data-testid="documents-tree-empty">
            No documents on this vessel yet.
          </div>
        ) : (
          flat.map((node, index) => (
            <TreeRow
              key={node.kind === 'folder' ? `folder:${node.path}` : `file:${node._docId}`}
              node={node}
              index={index}
              isFocused={index === focusIndex}
              isSelected={
                node.kind === 'file' &&
                selectedDocId != null &&
                node._docId === selectedDocId
              }
              expanded={node.kind === 'folder' ? expandedPaths.has(node.path) : false}
              fileCount={node.kind === 'folder' ? countFiles(node) : 0}
              onToggleFolder={toggleFolder}
              onSelectFile={onSelect}
              onFocus={setFocusIndex}
              setRef={(el) => {
                rowRefs.current[index] = el;
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}

// ── Row subcomponent ────────────────────────────────────────────────────────

interface TreeRowProps {
  node: TreeNode;
  index: number;
  isFocused: boolean;
  isSelected: boolean;
  expanded: boolean;
  fileCount: number;
  onToggleFolder: (path: string) => void;
  onSelectFile: (docId: string) => void;
  onFocus: (index: number) => void;
  setRef: (el: HTMLDivElement | null) => void;
}

const TreeRow = React.memo(function TreeRow({
  node,
  index,
  isFocused,
  isSelected,
  expanded,
  fileCount,
  onToggleFolder,
  onSelectFile,
  onFocus,
  setRef,
}: TreeRowProps) {
  const indent = node.depth * 16;

  if (node.kind === 'folder') {
    const rowClass = [styles.row, isFocused ? styles.rowFocused : ''].filter(Boolean).join(' ');
    return (
      <div
        ref={setRef}
        className={rowClass}
        style={{ paddingLeft: 8 + indent }}
        onClick={() => {
          onFocus(index);
          onToggleFolder(node.path);
        }}
        role="treeitem"
        aria-expanded={expanded}
        aria-selected={false}
        aria-level={node.depth + 1}
        data-testid={`doc-tree-folder-${node.path}`}
        data-tree-expanded={expanded ? "true" : "false"}
        data-node-id={node.path}
        data-depth={node.depth}
      >
        <span
          className={`${styles.chevron} ${expanded ? styles.chevronExpanded : ''}`}
          aria-hidden
        >
          <ChevronRight size={14} />
        </span>
        <Folder size={16} className={styles.icon} aria-hidden />
        <div className={styles.textWrap}>
          <span className={styles.folderName}>{node.name}</span>
        </div>
        <span className={styles.countBadge} aria-label={`${fileCount} files`}>
          {fileCount}
        </span>
      </div>
    );
  }

  const FileIconComponent = iconForContentType(node.content_type);
  const rowClass = [
    styles.row,
    isFocused ? styles.rowFocused : '',
    isSelected ? styles.rowSelected : '',
  ]
    .filter(Boolean)
    .join(' ');

  const subtitleParts: string[] = [];
  const prettyType = prettifyDocType(node.doc_type);
  if (prettyType) subtitleParts.push(prettyType);
  subtitleParts.push(formatBytes(node.size_bytes));
  subtitleParts.push(formatDateShort(node.updated_at));
  const subtitle = subtitleParts.join(' \u00b7 ');

  return (
    <div
      ref={setRef}
      className={rowClass}
      style={{ paddingLeft: 8 + indent }}
      onClick={() => {
        onFocus(index);
        onSelectFile(node._docId);
      }}
      role="treeitem"
      aria-selected={isSelected}
      aria-level={node.depth + 1}
      data-testid={`doc-tree-leaf-${node._docId}`}
      data-node-id={node._docId}
      data-depth={node.depth}
    >
      <span className={styles.chevronSpacer} aria-hidden />
      <FileIconComponent size={16} className={`${styles.icon} ${styles.iconFile}`} aria-hidden />
      <div className={styles.textWrap}>
        <span className={styles.fileName}>{node.name}</span>
        <span className={styles.fileSub}>{subtitle}</span>
      </div>
    </div>
  );
});
