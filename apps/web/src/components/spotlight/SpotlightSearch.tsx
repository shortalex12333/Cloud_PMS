'use client';

/**
 * CelesteOS Spotlight Search
 * Apple Spotlight-identical implementation
 */

import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { Search, X, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import { useSituationState } from '@/hooks/useSituationState';
import type { SearchResult as APISearchResult } from '@/types/search';
import type { EntityType, SituationDomain } from '@/types/situation';
import SpotlightResultRow from './SpotlightResultRow';
import SettingsModal from '@/components/SettingsModal';
import { EntityLine, StatusLine } from '@/components/celeste';
import SituationRouter from '@/components/situations/SituationRouter';
import { toast } from 'sonner';
import { executeAction } from '@/lib/actionClient';
import { supabase } from '@/lib/supabaseClient';

// ============================================================================
// ROLLING PLACEHOLDER SUGGESTIONS
// ============================================================================

const PLACEHOLDER_SUGGESTIONS = [
  'Find fault 1234',
  'Generator maintenance history',
  'Create work order for...',
  "What's overdue this week?",
  'Parts low in stock',
  'Show recent handovers',
  'Equipment status summary',
  'Search documents...',
];

// ============================================================================
// TYPES
// ============================================================================

export interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

interface SpotlightSearchProps {
  onClose?: () => void;
  isModal?: boolean;
  className?: string;
}

// ============================================================================
// RESULT MAPPING
// ============================================================================

function mapAPIResult(result: APISearchResult): SpotlightResult {
  // Backend returns different field names than frontend expects
  // Map backend schema → frontend schema
  const anyResult = result as any;

  // Try to extract title from various possible fields
  let title =
    result.title ||
    anyResult.name ||
    anyResult.equipment_name ||
    anyResult.part_name ||
    anyResult.section_title ||
    anyResult.document_name ||
    anyResult.filename ||
    anyResult.code ||
    '';

  // If title is generic or missing, try to extract from content fields
  if (!title || title === 'Untitled' || title === 'Untitled Result') {
    // Try subtitle/snippet/preview for better title
    const contentText = result.subtitle || result.snippet || result.preview || anyResult.content || anyResult.text || '';
    if (contentText) {
      // Extract first meaningful sentence (up to 80 chars)
      const firstSentence = contentText.split(/[.!?]|  /)[0].trim();
      if (firstSentence.length > 0 && firstSentence.length < 120) {
        title = firstSentence;
      } else if (contentText.length > 0) {
        // Use first 80 characters
        title = contentText.substring(0, 80).trim();
      }
    }
  }

  // Final fallback
  if (!title) {
    title = result.id ? `Document ${result.id.substring(0, 8)}` : 'Untitled Document';
  }

  // Try to construct subtitle from available fields
  const subtitleParts: string[] = [];

  if (anyResult.manufacturer) subtitleParts.push(`Manufacturer: ${anyResult.manufacturer}`);
  if (anyResult.category) subtitleParts.push(`Category: ${anyResult.category}`);
  if (anyResult.part_number) subtitleParts.push(`P/N: ${anyResult.part_number}`);
  if (anyResult.location) subtitleParts.push(`Location: ${anyResult.location}`);
  if (anyResult.equipment_type) subtitleParts.push(`Type: ${anyResult.equipment_type}`);
  if (anyResult.page_number) subtitleParts.push(`Page: ${anyResult.page_number}`);
  if (anyResult.section_title && anyResult.section_title !== title) subtitleParts.push(`Section: ${anyResult.section_title}`);

  const subtitle =
    result.subtitle ||
    result.snippet ||
    result.preview ||
    subtitleParts.join(' | ') ||
    (anyResult.description || '').substring(0, 100) ||
    (anyResult.content || '').substring(0, 100) ||
    '';

  return {
    id: result.id || result.primary_id || crypto.randomUUID(),
    type: result.type || result.source_table || 'document',
    title: title.trim(),
    subtitle: subtitle.trim(),
    metadata: result.metadata || result.raw_data || (result as Record<string, any>),
  };
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightSearch({
  onClose,
  isModal = false,
  className
}: SpotlightSearchProps) {
  const {
    query,
    results: apiResults,
    isLoading,
    isStreaming,
    error,
    handleQueryChange,
    search,
    clear,
  } = useCelesteSearch();

  const {
    situation,
    createSituation,
    updateSituation,
    transitionTo,
    resetToIdle,
  } = useSituationState();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const results = useMemo(() => apiResults.map(mapAPIResult), [apiResults]);

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  // Rolling placeholder animation - cycle every 3 seconds
  useEffect(() => {
    if (query) return; // Don't animate when user is typing

    const interval = setInterval(() => {
      setIsAnimating(true);

      // After animation starts, change the text
      setTimeout(() => {
        setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_SUGGESTIONS.length);
        setIsAnimating(false);
      }, 200); // Half of transition duration
    }, 3000);

    return () => clearInterval(interval);
  }, [query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [results.length]);

  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const el = resultsRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex, results.length]);

  /**
   * Map result type to entity type for situation creation
   */
  const mapResultTypeToEntityType = useCallback((type: string): EntityType => {
    if (type.includes('document') || type === 'search_document_chunks') return 'document';
    if (type.includes('equipment') || type === 'pms_equipment') return 'equipment';
    if (type.includes('part') || type === 'pms_parts') return 'part';
    if (type.includes('work_order')) return 'work_order';
    if (type.includes('fault')) return 'fault';
    if (type.includes('inventory') || type === 'v_inventory') return 'inventory';
    return 'document'; // Default fallback
  }, []);

  /**
   * Map entity type to domain
   */
  const mapEntityTypeToDomain = useCallback((entityType: EntityType): SituationDomain => {
    if (entityType === 'document') return 'manuals';
    if (entityType === 'equipment' || entityType === 'work_order' || entityType === 'fault') return 'maintenance';
    if (entityType === 'part' || entityType === 'inventory') return 'inventory';
    return 'manuals'; // Default fallback
  }, []);

  /**
   * Handle result selection (single click) - Creates CANDIDATE situation
   */
  const handleResultSelect = useCallback((result: SpotlightResult, index: number) => {
    setSelectedIndex(index);

    // Create CANDIDATE situation
    const entityType = mapResultTypeToEntityType(result.type);
    const domain = mapEntityTypeToDomain(entityType);

    // Store full result in metadata for later access
    const situationMetadata = {
      ...result.metadata,
      title: result.title,
      subtitle: result.subtitle,
      type: result.type,
      storage_path: result.metadata?.storage_path || result.metadata?.path,
      name: result.title,
    };

    createSituation({
      entity_type: entityType,
      entity_id: result.id,
      domain,
      initial_state: 'CANDIDATE',
      metadata: situationMetadata,
    });
  }, [createSituation, mapResultTypeToEntityType, mapEntityTypeToDomain]);

  /**
   * Handle result open (double-click or Enter) - Creates ACTIVE situation
   */
  const handleResultOpen = useCallback(async (result: SpotlightResult) => {
    const entityType = mapResultTypeToEntityType(result.type);
    const domain = mapEntityTypeToDomain(entityType);

    // Store full result in metadata for viewer access
    const situationMetadata = {
      ...result.metadata,
      title: result.title,
      subtitle: result.subtitle,
      type: result.type,
      storage_path: result.metadata?.storage_path || result.metadata?.path,
      name: result.title,
    };

    // Create or transition to ACTIVE situation
    if (situation && situation.state === 'CANDIDATE') {
      // Update evidence with metadata before transitioning
      await updateSituation({
        evidence: situationMetadata as any,
      });
      await transitionTo('ACTIVE', 'User opened entity from CANDIDATE state');
    } else {
      await createSituation({
        entity_type: entityType,
        entity_id: result.id,
        domain,
        initial_state: 'ACTIVE',
        metadata: situationMetadata,
      });
    }
  }, [situation, createSituation, transitionTo, updateSituation, mapResultTypeToEntityType, mapEntityTypeToDomain]);

  /**
   * Handle situation close (any viewer)
   */
  const handleSituationClose = useCallback(() => {
    resetToIdle();
    inputRef.current?.focus();
  }, [resetToIdle]);

  /**
   * Handle situation actions (add to handover, etc.)
   */
  const handleSituationAction = useCallback(async (action: string, payload: any) => {
    console.log('[SpotlightSearch] Situation action:', action, payload);

    try {
      // Get current user session
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user) {
        toast.error('Authentication required');
        return;
      }

      // Get yacht_id from user profile
      const { data: profile } = await supabase
        .from('auth_users_profiles')
        .select('yacht_id')
        .eq('id', session.user.id)
        .single();

      if (!profile?.yacht_id) {
        toast.error('No yacht associated with user');
        return;
      }

      // Handle different actions
      switch (action) {
        case 'add_to_handover':
          await handleAddToHandover(session.user.id, profile.yacht_id, payload);
          break;

        default:
          console.warn(`[SpotlightSearch] Unknown action: ${action}`);
          toast.error(`Action "${action}" not yet implemented`);
      }
    } catch (error) {
      console.error('[SpotlightSearch] Action failed:', error);
      toast.error(error instanceof Error ? error.message : 'Action failed');
    }
  }, []);

  /**
   * Handle add_to_handover action
   */
  const handleAddToHandover = async (
    userId: string,
    yachtId: string,
    payload: any
  ) => {
    // Map entity type for documents
    const entityType = payload.type === 'document' || payload.document_id
      ? 'document_chunk'
      : payload.type || 'document_chunk';

    // Generate summary from available data
    const summaryText = payload.document_title || payload.title || payload.name || 'Document reference';

    // Map entity type to category
    const categoryMap: Record<string, string> = {
      'fault': 'ongoing_fault',
      'work_order': 'work_in_progress',
      'equipment': 'equipment_status',
      'document': 'important_info',
      'document_chunk': 'important_info',
      'part': 'general',
    };
    const category = categoryMap[entityType] || 'important_info';

    // Build API request payload
    const requestPayload = {
      entity_type: entityType,
      entity_id: payload.document_id || payload.entity_id || payload.id,
      summary_text: summaryText,
      category: category,
      priority: payload.priority || 'normal',
    };

    console.log('[SpotlightSearch] Executing add_to_handover:', {
      action: 'add_to_handover',
      context: { yacht_id: yachtId, user_id: userId },
      payload: requestPayload,
    });

    // Call backend API via actionClient
    const result = await executeAction(
      'add_to_handover',
      {
        yacht_id: yachtId,
        user_id: userId,
      },
      requestPayload
    );

    if (result.status === 'error') {
      throw new Error(result.message || 'Failed to add to handover');
    }

    // Show success message
    toast.success('Added to handover', {
      description: summaryText.substring(0, 80),
    });

    console.log('[SpotlightSearch] Handover entry created:', result);
  };

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          handleResultOpen(results[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        if (query) {
          clear();
        } else {
          onClose?.();
        }
        break;
    }
  }, [results, selectedIndex, query, clear, onClose, handleResultOpen]);

  const handleClear = useCallback(() => {
    clear();
    setSelectedIndex(0);
    inputRef.current?.focus();
  }, [clear]);

  const hasResults = results.length > 0;
  const hasQuery = query.trim().length > 0;
  const showNoResults = hasQuery && !hasResults && !isLoading && !isStreaming;

  return (
    <div
      className={cn(
        isModal && 'fixed inset-0 z-[9999] flex items-start justify-center pt-[18vh]',
        className
      )}
    >
      {/* Backdrop */}
      {isModal && (
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-md"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Spotlight Container - constrained width */}
      <div
        className={cn(
          'w-full max-w-[680px] mx-auto px-4',
          isModal && 'relative z-10'
        )}
      >
        {/* Main Spotlight Panel */}
        <div
          className={cn(
            'spotlight-panel w-full font-body',
            'animate-spotlight-in'
          )}
        >
          {/* Search Input */}
          <div
            className={cn(
              'flex items-center gap-3 px-4 h-[50px]',
              (hasQuery || hasResults) && 'border-b border-[#3d3d3f]/30'
            )}
          >
            <Search
              className="flex-shrink-0 w-5 h-5 text-[#98989f]"
              strokeWidth={1.8}
            />

            <div className="flex-1 h-full relative">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => handleQueryChange(e.target.value)}
                onKeyDown={handleKeyDown}
                className={cn(
                  'w-full h-full',
                  'bg-transparent border-none outline-none',
                  'text-[17px] text-white',
                  'font-normal tracking-[-0.01em]',
                  'caret-white',
                  'relative z-10'
                )}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
              />
              {/* Animated rolling placeholder */}
              {!query && (
                <div
                  className="absolute inset-0 flex items-center pointer-events-none overflow-hidden"
                >
                  <span
                    className={cn(
                      'text-[17px] text-[#98989f] font-normal tracking-[-0.01em]',
                      'transition-all duration-[400ms] ease-out',
                      isAnimating
                        ? 'opacity-0 -translate-y-3'
                        : 'opacity-100 translate-y-0'
                    )}
                  >
                    {PLACEHOLDER_SUGGESTIONS[placeholderIndex]}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {query && (
                <button
                  onClick={handleClear}
                  className="flex items-center justify-center w-4 h-4 rounded-full bg-[#636366] hover:bg-[#8e8e93] transition-colors"
                  aria-label="Clear"
                >
                  <X className="w-2.5 h-2.5 text-[#1c1c1e]" strokeWidth={3} />
                </button>
              )}
            </div>
          </div>

          {/* Status Line - system transparency */}
          <StatusLine
            message={isLoading ? 'Searching…' : isStreaming ? 'Loading results…' : ''}
            visible={isLoading || isStreaming}
            className="px-4 py-2"
          />

          {/* Entity Line - what Celeste understood (placeholder for NLP extraction) */}
          {hasQuery && hasResults && (
            <EntityLine
              entities={[
                // These would come from NLP extraction in the search hook
                // For now, extract type from first result as demonstration
                ...(results[0]?.type ? [{ label: 'Type', value: results[0].type.replace('_', ' ') }] : []),
              ]}
            />
          )}

          {/* Results */}
          {hasQuery && (
            <div
              ref={resultsRef}
              className="max-h-[420px] overflow-y-auto overflow-x-hidden spotlight-scrollbar"
            >
              {hasResults && (
                <div className="py-1.5">
                  {results.map((result, index) => (
                    <SpotlightResultRow
                      key={result.id}
                      result={result}
                      isSelected={index === selectedIndex}
                      index={index}
                      onClick={() => handleResultOpen(result)}
                      onDoubleClick={() => handleResultOpen(result)}
                    />
                  ))}
                </div>
              )}

              {showNoResults && (
                <div className="py-10 text-center">
                  <p className="text-[15px] text-[#98989f]">No Results</p>
                </div>
              )}

              {error && (
                <div className="py-10 text-center">
                  <p className="text-[15px] text-[#98989f]">{error}</p>
                  <button
                    onClick={() => search(query)}
                    className="mt-2 text-[14px] text-[#0a84ff] hover:text-[#409cff]"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Settings Button - below panel, centered */}
        <div className="flex justify-center mt-4">
          <button
            onClick={() => setShowSettings(true)}
            className="p-2.5 rounded-full text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Settings"
          >
            <Settings className="w-5 h-5" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* Situation Router - Renders appropriate viewer based on situation type */}
      <SituationRouter
        situation={situation}
        onClose={handleSituationClose}
        onAction={handleSituationAction}
      />
    </div>
  );
}
