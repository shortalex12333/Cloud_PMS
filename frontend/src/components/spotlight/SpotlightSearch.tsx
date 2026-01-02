'use client';

/**
 * CelesteOS Spotlight Search
 * Apple Spotlight-identical implementation
 *
 * Design principles:
 * - Single unified container (input + results seamlessly connected)
 * - Large radius (~20px), dramatic shadow
 * - Clean rows: icon + title + subtitle only
 * - No clutter: no badges, confidence bars, chevrons, keyboard hints
 * - Smooth animations, subtle interactions
 */

import React, { useEffect, useRef, useCallback, useMemo, useState } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCelesteSearch } from '@/hooks/useCelesteSearch';
import type { SearchResult as APISearchResult } from '@/types/search';
import SpotlightResultRow from './SpotlightResultRow';

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
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Map results
  const results = useMemo(() => apiResults.map(mapAPIResult), [apiResults]);

  // Focus input on mount
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results.length]);

  // Scroll selected into view
  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const el = resultsRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex, results.length]);

  // Keyboard navigation
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

  // Clear handler
  const handleClear = useCallback(() => {
    clear();
    setSelectedIndex(0);
    inputRef.current?.focus();
  }, [clear]);

  const hasResults = results.length > 0;
  const showResults = query.trim().length > 0;
  const showNoResults = showResults && !hasResults && !isLoading && !isStreaming;

  return (
    <div
      className={cn(
        'w-full max-w-[680px] mx-auto',
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

      {/* Main Spotlight Container - SINGLE UNIFIED PANEL */}
      <div
        className={cn(
          'spotlight-panel relative w-full',
          'animate-spotlight-in',
          isModal && 'z-10'
        )}
      >
        {/* Search Input Area */}
        <div className="flex items-center px-5 h-[52px] border-b border-black/[0.06] dark:border-white/[0.06]">
          {/* Search Icon */}
          <Search
            className="flex-shrink-0 w-[22px] h-[22px] text-[#86868b] dark:text-[#98989d]"
            strokeWidth={2}
          />

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Spotlight Search"
            className={cn(
              'flex-1 h-full ml-3',
              'bg-transparent border-none outline-none',
              'text-[18px] text-[#1d1d1f] dark:text-[#f5f5f7]',
              'placeholder:text-[#86868b] dark:placeholder:text-[#98989d]',
              'font-normal'
            )}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
          />

          {/* Loading / Clear */}
          <div className="flex items-center gap-2">
            {(isLoading || isStreaming) && (
              <Loader2 className="w-4 h-4 text-[#86868b] animate-spin" />
            )}
            {query && (
              <button
                onClick={handleClear}
                className={cn(
                  'flex items-center justify-center',
                  'w-[18px] h-[18px] rounded-full',
                  'bg-[#86868b]/80 hover:bg-[#86868b]',
                  'transition-colors duration-100'
                )}
                aria-label="Clear search"
              >
                <X className="w-3 h-3 text-white" strokeWidth={2.5} />
              </button>
            )}
          </div>
        </div>

        {/* Results Area - Seamlessly Connected */}
        {showResults && (
          <div
            ref={resultsRef}
            className="max-h-[400px] overflow-y-auto overflow-x-hidden spotlight-scrollbar"
          >
            {hasResults && (
              <div className="py-1">
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

            {/* No Results */}
            {showNoResults && (
              <div className="px-5 py-8 text-center">
                <p className="text-[15px] text-[#86868b] dark:text-[#98989d]">
                  No Results
                </p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="px-5 py-8 text-center">
                <p className="text-[15px] text-[#86868b] dark:text-[#98989d]">
                  {error}
                </p>
                <button
                  onClick={() => search(query)}
                  className="mt-2 text-[14px] text-[#0066CC] hover:underline"
                >
                  Try again
                </button>
              </div>
            )}
          </div>
        )}

        {/* Idle State - Siri Suggestions Style */}
        {!showResults && (
          <div className="px-5 py-4">
            <p className="text-[11px] font-medium uppercase tracking-[0.02em] text-[#86868b] dark:text-[#98989d] mb-3">
              Siri Suggestions
            </p>
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Faults', icon: '⚠️' },
                { label: 'Work Orders', icon: '🔧' },
                { label: 'Parts', icon: '📦' },
                { label: 'Documents', icon: '📄' },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => {
                    handleQueryChange(item.label.toLowerCase());
                    search(item.label.toLowerCase());
                  }}
                  className={cn(
                    'flex flex-col items-center gap-2 p-3',
                    'rounded-xl',
                    'hover:bg-black/[0.04] dark:hover:bg-white/[0.06]',
                    'transition-colors duration-100'
                  )}
                >
                  <span className="text-2xl">{item.icon}</span>
                  <span className="text-[11px] text-[#1d1d1f] dark:text-[#f5f5f7]">
                    {item.label}
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
