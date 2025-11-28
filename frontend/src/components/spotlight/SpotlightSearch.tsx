'use client';

/**
 * CelesteOS Spotlight Search
 * Apple Spotlight-quality search interface
 *
 * Features:
 * - Glassmorphic container with precise blur/shadow
 * - Tiered results (Top Hits → Direct Matches → Related → Recommendations)
 * - Keyboard navigation with visual feedback
 * - Inline microactions with overflow handling
 * - Confidence indicators
 * - Preview pane support
 * - Real streaming API integration via useCelesteSearch hook
 */

import React, { useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Search, X, Loader2, Command, ArrowUp, ArrowDown,
  CornerDownLeft, Clock, Sparkles,
  AlertTriangle, Wrench, Cog, Package, FileText,
  ClipboardList, Ship, TrendingUp, DollarSign, Users,
  Mail, MessageSquare
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MicroAction, CardType, ACTION_REGISTRY } from '@/types/actions';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import type { SearchResult as APISearchResult, ResultCardType, MicroAction as APIMicroAction } from '@/types/search';
import SpotlightResultRow from './SpotlightResultRow';
import SpotlightPreviewPane from './SpotlightPreviewPane';

// ============================================================================
// TYPES
// ============================================================================

export interface SpotlightResult {
  id: string;
  type: CardType;
  title: string;
  subtitle: string;
  confidence: number; // 0-100
  timestamp?: string;
  actions: MicroAction[];
  metadata?: Record<string, any>;
  highlight?: string; // Matched text highlight
}

interface ResultGroup {
  id: string;
  label: string;
  results: SpotlightResult[];
  priority: number;
}

interface SpotlightSearchProps {
  onClose?: () => void;
  isModal?: boolean;
  className?: string;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const CARD_TYPE_ICONS: Record<CardType, React.ElementType> = {
  fault: AlertTriangle,
  work_order: Wrench,
  equipment: Cog,
  part: Package,
  handover: Users,
  document: FileText,
  hor_table: Clock,
  purchase: DollarSign,
  checklist: ClipboardList,
  worklist: ClipboardList,
  fleet_summary: Ship,
  smart_summary: Sparkles,
};

const CARD_TYPE_LABELS: Record<CardType, string> = {
  fault: 'Fault',
  work_order: 'Work Order',
  equipment: 'Equipment',
  part: 'Part',
  handover: 'Handover',
  document: 'Document',
  hor_table: 'Hours of Rest',
  purchase: 'Purchase',
  checklist: 'Checklist',
  worklist: 'Worklist',
  fleet_summary: 'Fleet',
  smart_summary: 'Summary',
};

// Extended icons for API result types not in core CardType
const EXTENDED_ICONS: Record<string, React.ElementType> = {
  document_chunk: FileText,
  predictive: TrendingUp,
  handover_item: Users,
  email: Mail,
  note: MessageSquare,
};

// ============================================================================
// TYPE MAPPING UTILITIES
// ============================================================================

/**
 * Map API ResultCardType to UI CardType
 * Handles extended types that come from the search API
 */
function mapResultTypeToCardType(type: ResultCardType | string): CardType {
  const typeMap: Record<string, CardType> = {
    // Direct mappings
    fault: 'fault',
    work_order: 'work_order',
    part: 'part',
    equipment: 'equipment',

    // Extended type mappings
    document_chunk: 'document',
    predictive: 'smart_summary',
    handover_item: 'handover',
    email: 'document',
    note: 'document',
  };

  return typeMap[type] || 'document';
}

/**
 * Map API MicroAction to actions.ts MicroAction
 * Converts search API action names to the 67 canonical actions
 */
function mapAPIMicroAction(action: APIMicroAction | string): MicroAction {
  const actionMap: Record<string, MicroAction> = {
    // Search API action mappings
    create_work_order: 'create_work_order',
    add_to_handover: 'add_to_handover',
    open_document: 'view_document',
    order_part: 'order_part',
    view_history: 'view_fault_history',
    show_predictive: 'request_predictive_insight',
    add_note: 'add_fault_note',
    attach_photo: 'add_fault_photo',
    resolve_fault: 'diagnose_fault',
    assign_task: 'assign_work_order',
  };

  // First check if it's already a valid MicroAction in ACTION_REGISTRY
  if (action in ACTION_REGISTRY) {
    return action as MicroAction;
  }

  // Otherwise map it
  return actionMap[action] || 'view_document';
}

/**
 * Convert API SearchResult to SpotlightResult
 */
function mapAPIResultToSpotlight(result: APISearchResult): SpotlightResult {
  const cardType = mapResultTypeToCardType(result.type);

  // Map API actions to canonical MicroActions
  const mappedActions: MicroAction[] = result.actions
    .map(mapAPIMicroAction)
    .filter((action, index, self) => self.indexOf(action) === index); // Deduplicate

  return {
    id: result.id,
    type: cardType,
    title: result.title,
    subtitle: result.subtitle || result.preview || '',
    confidence: result.score, // API uses 'score', UI uses 'confidence'
    timestamp: result.timestamp,
    actions: mappedActions,
    metadata: result.metadata,
    highlight: result.preview,
  };
}

/**
 * Get icon for result type (handles extended types)
 */
function getResultIcon(type: CardType | ResultCardType | string): React.ElementType {
  // First check standard CardType icons
  if (type in CARD_TYPE_ICONS) {
    return CARD_TYPE_ICONS[type as CardType];
  }
  // Then check extended icons
  if (type in EXTENDED_ICONS) {
    return EXTENDED_ICONS[type];
  }
  // Default to document
  return FileText;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightSearch({
  onClose,
  isModal = false,
  className
}: SpotlightSearchProps) {
  // Use the real search hook
  const {
    query,
    results: apiResults,
    isLoading,
    isStreaming,
    error,
    suggestions,
    handleQueryChange,
    search,
    clear,
    recentQueries,
  } = useCelesteSearch();

  // Local UI state
  const [selectedIndex, setSelectedIndex] = React.useState(0);
  const [showPreview, setShowPreview] = React.useState(false);
  const [expandedGroups, setExpandedGroups] = React.useState<Set<string>>(new Set(['top_hits', 'direct']));

  // Refs
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Map API results to Spotlight format
  const results: SpotlightResult[] = useMemo(() => {
    return apiResults.map(mapAPIResultToSpotlight);
  }, [apiResults]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Global keyboard shortcut (Cmd+K)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Reset selected index when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results.length]);

  // Group results by tier
  const groupedResults = useMemo((): ResultGroup[] => {
    if (results.length === 0) return [];

    const topHits = results.filter(r => r.confidence >= 85);
    const directMatches = results.filter(r => r.confidence >= 60 && r.confidence < 85);
    const related = results.filter(r => r.confidence >= 40 && r.confidence < 60);
    const recommendations = results.filter(r => r.confidence < 40);

    const groups: ResultGroup[] = [];

    if (topHits.length > 0) {
      groups.push({ id: 'top_hits', label: 'Top Hits', results: topHits, priority: 1 });
    }
    if (directMatches.length > 0) {
      groups.push({ id: 'direct', label: 'Direct Matches', results: directMatches, priority: 2 });
    }
    if (related.length > 0) {
      groups.push({ id: 'related', label: 'Related', results: related, priority: 3 });
    }
    if (recommendations.length > 0) {
      groups.push({ id: 'recommendations', label: 'Recommendations', results: recommendations, priority: 4 });
    }

    return groups;
  }, [results]);

  // Flatten results for keyboard navigation
  const flatResults = useMemo(() => {
    return groupedResults.flatMap(g => g.results);
  }, [groupedResults]);

  // Get selected result
  const selectedResult = flatResults[selectedIndex];

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, flatResults.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedResult) {
          // Handle Enter on selected result
          console.log('Open:', selectedResult);
        }
        break;
      case 'Tab':
        e.preventDefault();
        // Tab to microactions
        setShowPreview(true);
        break;
      case 'Escape':
        if (query) {
          clear();
        } else {
          onClose?.();
        }
        break;
      case 'ArrowRight':
        if (e.metaKey || e.ctrlKey) {
          e.preventDefault();
          setShowPreview(true);
        }
        break;
      case 'ArrowLeft':
        if (e.metaKey || e.ctrlKey) {
          e.preventDefault();
          setShowPreview(false);
        }
        break;
    }
  }, [flatResults.length, selectedResult, query, onClose, clear]);

  // Scroll selected item into view
  useEffect(() => {
    if (resultsRef.current && flatResults.length > 0) {
      const selectedElement = resultsRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex, flatResults.length]);

  // Toggle group expansion
  const toggleGroup = useCallback((groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  }, []);

  // Handle recent query click
  const handleRecentClick = useCallback((recentQuery: string) => {
    handleQueryChange(recentQuery);
    search(recentQuery);
    inputRef.current?.focus();
  }, [handleQueryChange, search]);

  // Clear search - use hook's clear method
  const handleClear = useCallback(() => {
    clear();
    setSelectedIndex(0);
    inputRef.current?.focus();
  }, [clear]);

  const showResults = query.trim().length > 0;
  const showEmptyState = query.trim().length > 0 && results.length === 0 && !isLoading && !isStreaming;
  const showRecentQueries = !query.trim() && results.length === 0;

  return (
    <div
      ref={containerRef}
      className={cn(
        'spotlight-container w-full max-w-[680px]',
        isModal && 'fixed inset-0 z-[800] flex items-start justify-center pt-[15vh]',
        className
      )}
    >
      {/* Backdrop for modal mode */}
      {isModal && (
        <div
          className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Main search container */}
      <div className={cn(
        'relative w-full',
        isModal && 'z-10'
      )}>
        {/* Search Input */}
        <div className="relative">
          <div
            className={cn(
              'relative flex items-center',
              'bg-white/95 dark:bg-zinc-900/95',
              'backdrop-blur-[20px]',
              'border border-zinc-200/60 dark:border-zinc-700/60',
              'rounded-[14px]',
              'shadow-[0_8px_32px_rgba(0,0,0,0.12),0_2px_8px_rgba(0,0,0,0.08)]',
              'dark:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_2px_8px_rgba(0,0,0,0.2)]',
              'transition-shadow duration-200',
              'hover:shadow-[0_12px_40px_rgba(0,0,0,0.16),0_4px_12px_rgba(0,0,0,0.10)]',
              'focus-within:shadow-[0_12px_40px_rgba(0,0,0,0.16),0_4px_12px_rgba(0,0,0,0.10)]',
              'focus-within:ring-2 focus-within:ring-blue-500/30'
            )}
          >
            {/* Search icon */}
            <Search className="absolute left-[18px] h-5 w-5 text-zinc-400 dark:text-zinc-500" />

            {/* Input */}
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search anything..."
              className={cn(
                'w-full h-14 pl-[52px] pr-[100px]',
                'bg-transparent',
                'text-[17px] text-zinc-900 dark:text-zinc-100',
                'placeholder:text-zinc-400 dark:placeholder:text-zinc-500',
                'focus:outline-none',
                'font-normal tracking-[-0.01em]'
              )}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
            />

            {/* Right side controls */}
            <div className="absolute right-3 flex items-center gap-2">
              {/* Loading indicator */}
              {(isLoading || isStreaming) && (
                <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
              )}

              {/* Clear button */}
              {query && (
                <button
                  onClick={handleClear}
                  className={cn(
                    'p-1.5 rounded-md',
                    'text-zinc-400 hover:text-zinc-600',
                    'dark:text-zinc-500 dark:hover:text-zinc-300',
                    'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                    'transition-colors duration-150'
                  )}
                >
                  <X className="h-4 w-4" />
                </button>
              )}

              {/* Keyboard hint */}
              <kbd className={cn(
                'hidden sm:flex items-center gap-1',
                'px-1.5 py-0.5 rounded',
                'bg-zinc-100 dark:bg-zinc-800',
                'text-[11px] text-zinc-500 dark:text-zinc-400',
                'font-medium'
              )}>
                <Command className="h-3 w-3" />K
              </kbd>
            </div>
          </div>

          {/* Streaming progress bar */}
          {isStreaming && (
            <div className="absolute bottom-0 left-4 right-4 h-[2px] overflow-hidden rounded-full">
              <div className="h-full bg-blue-500 animate-[progress_1.5s_ease-in-out_infinite]"
                style={{
                  background: 'linear-gradient(90deg, transparent, #3B82F6, transparent)',
                  animation: 'shimmer 1.5s infinite',
                  backgroundSize: '200% 100%'
                }}
              />
            </div>
          )}
        </div>

        {/* Results Container */}
        {showResults && (
          <div className="flex gap-2 mt-2">
            {/* Results list */}
            <div
              ref={resultsRef}
              className={cn(
                'flex-1',
                'bg-white/98 dark:bg-zinc-900/98',
                'backdrop-blur-[20px]',
                'border border-zinc-200/60 dark:border-zinc-700/60',
                'rounded-[14px]',
                'shadow-[0_8px_32px_rgba(0,0,0,0.12),0_2px_8px_rgba(0,0,0,0.08)]',
                'dark:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_2px_8px_rgba(0,0,0,0.2)]',
                'overflow-hidden',
                'max-h-[480px] overflow-y-auto',
                'scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700'
              )}
            >
              {groupedResults.map((group, groupIndex) => {
                const isExpanded = expandedGroups.has(group.id);
                const visibleResults = isExpanded ? group.results : group.results.slice(0, 3);

                return (
                  <div key={group.id}>
                    {/* Group header */}
                    <div className={cn(
                      'sticky top-0 z-10',
                      'flex items-center justify-between',
                      'px-4 py-2',
                      'bg-zinc-50/95 dark:bg-zinc-800/95',
                      'backdrop-blur-sm',
                      groupIndex > 0 && 'border-t border-zinc-200/60 dark:border-zinc-700/60'
                    )}>
                      <span className={cn(
                        'text-[11px] font-semibold uppercase tracking-[0.04em]',
                        'text-zinc-500 dark:text-zinc-400'
                      )}>
                        {group.label}
                      </span>
                      {group.results.length > 3 && (
                        <button
                          onClick={() => toggleGroup(group.id)}
                          className={cn(
                            'text-[11px] font-medium',
                            'text-blue-500 hover:text-blue-600',
                            'dark:text-blue-400 dark:hover:text-blue-300',
                            'transition-colors'
                          )}
                        >
                          {isExpanded ? 'Show less' : `Show all ${group.results.length}`}
                        </button>
                      )}
                    </div>

                    {/* Results */}
                    {visibleResults.map((result, resultIndex) => {
                      const flatIndex = flatResults.findIndex(r => r.id === result.id);
                      const isSelected = flatIndex === selectedIndex;

                      return (
                        <SpotlightResultRow
                          key={result.id}
                          result={result}
                          isSelected={isSelected}
                          index={flatIndex}
                          icon={CARD_TYPE_ICONS[result.type]}
                          typeLabel={CARD_TYPE_LABELS[result.type]}
                          onClick={() => setSelectedIndex(flatIndex)}
                          onDoubleClick={() => console.log('Open:', result)}
                        />
                      );
                    })}
                  </div>
                );
              })}

              {/* Error state */}
              {error && (
                <div className="py-6 px-4 text-center">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                  </div>
                  <p className="text-[14px] font-medium text-zinc-600 dark:text-zinc-400">
                    {error}
                  </p>
                  <button
                    onClick={() => search(query)}
                    className="mt-2 text-[13px] text-blue-500 hover:text-blue-600 dark:text-blue-400"
                  >
                    Try again
                  </button>
                </div>
              )}

              {/* Empty state */}
              {showEmptyState && !error && (
                <div className="py-12 px-4 text-center">
                  <Search className="h-10 w-10 mx-auto mb-3 text-zinc-300 dark:text-zinc-600" />
                  <p className="text-[15px] font-medium text-zinc-600 dark:text-zinc-400">
                    No results for "{query}"
                  </p>
                  <p className="mt-1 text-[13px] text-zinc-500 dark:text-zinc-500">
                    Try searching for equipment, fault codes, or documents
                  </p>
                </div>
              )}

              {/* Keyboard navigation hints */}
              {results.length > 0 && (
                <div className={cn(
                  'flex items-center justify-center gap-4',
                  'px-4 py-2',
                  'border-t border-zinc-200/60 dark:border-zinc-700/60',
                  'bg-zinc-50/80 dark:bg-zinc-800/80'
                )}>
                  <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                    <ArrowUp className="h-3 w-3" />
                    <ArrowDown className="h-3 w-3" />
                    <span>Navigate</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                    <CornerDownLeft className="h-3 w-3" />
                    <span>Open</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                    <kbd className="px-1 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-[10px]">Tab</kbd>
                    <span>Actions</span>
                  </span>
                  <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                    <kbd className="px-1 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-[10px]">Esc</kbd>
                    <span>Clear</span>
                  </span>
                </div>
              )}
            </div>

            {/* Preview pane */}
            {showPreview && selectedResult && (
              <SpotlightPreviewPane
                result={selectedResult}
                onClose={() => setShowPreview(false)}
              />
            )}
          </div>
        )}

        {/* Recent queries (empty state) */}
        {showRecentQueries && (
          <div className="mt-6 px-2">
            {recentQueries.length > 0 && (
              <>
                <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-zinc-500 dark:text-zinc-400 mb-3">
                  Recent Searches
                </p>
                <div className="flex flex-wrap gap-2">
                  {recentQueries.map((recentQuery, index) => (
                    <button
                      key={index}
                      onClick={() => handleRecentClick(recentQuery)}
                      className={cn(
                        'flex items-center gap-1.5',
                        'px-3 py-1.5 rounded-lg',
                        'bg-zinc-100 dark:bg-zinc-800',
                        'hover:bg-zinc-200 dark:hover:bg-zinc-700',
                        'text-[13px] text-zinc-600 dark:text-zinc-300',
                        'transition-colors duration-150'
                      )}
                    >
                      <Clock className="h-3 w-3 text-zinc-400" />
                      {recentQuery}
                    </button>
                  ))}
                </div>
              </>
            )}

            {/* Example queries */}
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-zinc-500 dark:text-zinc-400 mt-6 mb-3">
              Try Searching For
            </p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { query: 'overheating generator', desc: 'Find related faults' },
                { query: 'manual stabiliser', desc: 'Search documents' },
                { query: 'fault 1234', desc: 'Lookup fault code' },
                { query: 'part 3512-B gasket', desc: 'Check inventory' },
              ].map((example, index) => (
                <button
                  key={index}
                  onClick={() => handleRecentClick(example.query)}
                  className={cn(
                    'flex flex-col items-start gap-0.5',
                    'p-3 rounded-xl',
                    'bg-zinc-50 dark:bg-zinc-800/50',
                    'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                    'border border-zinc-200/60 dark:border-zinc-700/60',
                    'transition-colors duration-150'
                  )}
                >
                  <span className="text-[13px] font-medium text-zinc-700 dark:text-zinc-200">
                    {example.query}
                  </span>
                  <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                    {example.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
