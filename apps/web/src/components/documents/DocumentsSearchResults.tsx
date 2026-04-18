'use client';

/**
 * DocumentsSearchResults — renders the /v2/search results for the Documents
 * domain as a list of <SpotlightResultRow>. The tree is hidden while a query
 * is active.
 *
 * Wires into the existing Celeste search pipeline (F1 SSE via pipeline-core,
 * with /api/search/fallback as L2). Debounced to 140ms by useCelesteSearch
 * internally — we pass the query through and let the hook do its thing.
 *
 * Clicking a result routes through `onSelect(docId)` so the parent page can
 * open <EntityDetailOverlay>, same as the tree's click handler.
 */

import * as React from 'react';
import SpotlightResultRow from '@/components/spotlight/SpotlightResultRow';
import { useAuth } from '@/hooks/useAuth';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';

interface DocumentsSearchResultsProps {
  query: string;
  onSelect: (docId: string) => void;
}

const DOMAIN_OBJECT_TYPES = ['document', 'search_document_chunks'];

export default function DocumentsSearchResults({
  query,
  onSelect,
}: DocumentsSearchResultsProps) {
  const { user } = useAuth();
  const yachtId = user?.yachtId ?? null;

  const { results, isLoading, error, handleQueryChange } = useCelesteSearch(
    yachtId,
    DOMAIN_OBJECT_TYPES,
  );

  // Kick the search when query changes. useCelesteSearch already debounces
  // at 140ms (fast typing) / 80ms (slow typing).
  React.useEffect(() => {
    handleQueryChange(query);
  }, [query, handleQueryChange]);

  // Local selection cursor — keyboard nav could come later; for now just
  // support click-through.
  const [selectedIndex, setSelectedIndex] = React.useState<number>(0);

  React.useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Filter to document results defensively — backend scope may vary.
  const docResults = React.useMemo(() => {
    return results.filter((r) => {
      const t = String(r.type || '').toLowerCase();
      return (
        t === 'document' ||
        t === 'doc_metadata' ||
        t.includes('document') ||
        t === 'search_document_chunks'
      );
    });
  }, [results]);

  if (!query.trim()) return null;

  if (isLoading && docResults.length === 0) {
    return (
      <div
        style={{
          padding: '24px 16px',
          color: 'var(--txt2)',
          fontFamily: 'var(--font-sans)',
          fontSize: 13,
        }}
        data-testid="documents-search-loading"
      >
        Searching…
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: '24px 16px',
          color: 'var(--red)',
          fontFamily: 'var(--font-sans)',
          fontSize: 13,
        }}
        data-testid="documents-search-error"
      >
        {error}
      </div>
    );
  }

  if (docResults.length === 0) {
    return (
      <div
        style={{
          padding: '24px 16px',
          color: 'var(--txt2)',
          fontFamily: 'var(--font-sans)',
          fontSize: 13,
        }}
        data-testid="documents-search-empty"
      >
        No documents match &lsquo;{query}&rsquo;
      </div>
    );
  }

  return (
    <div
      data-testid="documents-search-results"
      style={{
        flex: 1,
        minHeight: 0,
        overflowY: 'auto',
        paddingTop: 8,
      }}
    >
      {docResults.map((result, index) => (
        <SpotlightResultRow
          key={result.id || `r-${index}`}
          result={{
            id: result.id,
            type: String(result.type || 'document'),
            title: result.title || 'Untitled',
            subtitle: result.subtitle || '',
            snippet: result.snippet,
            metadata: result.metadata as Record<string, unknown> | undefined,
          }}
          isSelected={index === selectedIndex}
          index={index}
          onClick={() => {
            setSelectedIndex(index);
            if (result.id) onSelect(result.id);
          }}
          onDoubleClick={() => {
            if (result.id) onSelect(result.id);
          }}
        />
      ))}
    </div>
  );
}
