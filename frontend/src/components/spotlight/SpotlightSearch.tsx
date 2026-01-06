'use client';

/**
 * CelesteOS Spotlight Search
 * Apple Spotlight-identical implementation
 */

import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { Search, X, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import type { SearchResult as APISearchResult } from '@/types/search';
import SpotlightResultRow from './SpotlightResultRow';
import SettingsModal from '@/components/SettingsModal';
import { EntityLine, StatusLine } from '@/components/celeste';

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
  return {
    id: result.id,
    type: result.type,
    title: result.title,
    subtitle: result.subtitle || result.preview || '',
    metadata: result.metadata,
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
          console.log('Open:', results[selectedIndex]);
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
  }, [results, selectedIndex, query, clear, onClose]);

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
        'w-full max-w-[680px] mx-auto',
        isModal && 'fixed inset-0 z-[9999] flex items-start justify-center pt-[18vh]',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif' }}
    >
      {/* Backdrop */}
      {isModal && (
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-md"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Main Spotlight Container */}
      <div
        className={cn(
          'spotlight-panel relative w-full',
          'animate-spotlight-in',
          isModal && 'z-10'
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
                    onClick={() => setSelectedIndex(index)}
                    onDoubleClick={() => console.log('Open:', result)}
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

      {/* Settings Button - bottom of interface */}
      <div className="flex justify-center mt-6">
        <button
          onClick={() => setShowSettings(true)}
          className="p-2.5 rounded-full text-[#98989f] hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Settings"
        >
          <Settings className="w-5 h-5" strokeWidth={1.5} />
        </button>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </div>
  );
}
