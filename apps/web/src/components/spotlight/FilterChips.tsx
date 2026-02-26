'use client';

/**
 * FilterChips - Quick Filter Suggestions
 *
 * Renders deterministic filter suggestions as clickable chips.
 * Clicking a chip navigates to the filtered list route.
 *
 * Design principles:
 * - Deterministic: same input → same chips
 * - Fast: pattern matching, no LLM
 * - Minimal: max 5 chips, no clutter
 */

import React, { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { inferFilters, hasExplicitFilterMatch, type InferredFilter } from '@/lib/filters/infer';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import {
  AlertTriangle,
  ClipboardList,
  Settings,
  Package,
  FileText,
  Mail,
  Award,
  ShoppingCart,
  ArrowRightLeft,
  type LucideIcon,
} from 'lucide-react';

interface FilterChipsProps {
  query: string;
  className?: string;
  onFilterClick?: (filterId: string, route: string) => void;
}

/**
 * Domain → Icon mapping
 */
const DOMAIN_ICONS: Record<string, LucideIcon> = {
  'work-orders': ClipboardList,
  faults: AlertTriangle,
  equipment: Settings,
  inventory: Package,
  certificates: Award,
  documents: FileText,
  email: Mail,
  'shopping-list': ShoppingCart,
  receiving: ArrowRightLeft,
};

/**
 * Build full URL with query params
 */
function buildFilterUrl(route: string, queryParams: Record<string, string>): string {
  const params = new URLSearchParams(queryParams);
  return `${route}?${params.toString()}`;
}

export default function FilterChips({ query, className, onFilterClick }: FilterChipsProps) {
  const router = useRouter();

  // Only show chips if fragmented routes are enabled
  const fragmentedEnabled = isFragmentedRoutesEnabled();

  // Infer filters from query
  const inferredFilters = useMemo(() => {
    if (!fragmentedEnabled || !query || query.length < 3) {
      return [];
    }
    return inferFilters(query, 5);
  }, [query, fragmentedEnabled]);

  // Only show if we have explicit matches or high-confidence suggestions
  const hasExplicit = useMemo(() => hasExplicitFilterMatch(query), [query]);
  const shouldShow = inferredFilters.length > 0 && (hasExplicit || inferredFilters[0]?.score >= 0.7);

  if (!shouldShow) {
    return null;
  }

  const handleChipClick = (inferred: InferredFilter) => {
    const { filter } = inferred;
    const url = buildFilterUrl(filter.route, filter.query_params);

    // Callback for tracking/logging
    onFilterClick?.(filter.filter_id, url);

    // Navigate to filtered list
    router.push(url);
  };

  return (
    <div
      className={cn(
        'flex flex-wrap gap-2 px-4 py-2',
        'border-t border-surface-border/50',
        className
      )}
      data-testid="filter-chips"
    >
      <span className="text-txt-tertiary typo-meta self-center mr-1">Quick filters:</span>
      {inferredFilters.map((inferred) => {
        const { filter, score, matchType } = inferred;
        const Icon = DOMAIN_ICONS[filter.domain] || ClipboardList;

        return (
          <button
            key={filter.filter_id}
            onClick={() => handleChipClick(inferred)}
            className={cn(
              'inline-flex items-center gap-1.5',
              'px-3 py-1.5 rounded-full',
              'typo-meta font-medium',
              'transition-all duration-celeste-snappy',
              // High confidence = more prominent
              matchType === 'pattern'
                ? 'bg-brand-interactive/20 text-brand-interactive hover:bg-brand-interactive/30 ring-1 ring-brand-interactive/30'
                : 'bg-surface-secondary text-txt-secondary hover:bg-surface-tertiary hover:text-txt-primary',
              'cursor-pointer'
            )}
            data-testid={`filter-chip-${filter.filter_id}`}
            data-filter-id={filter.filter_id}
            data-match-type={matchType}
            data-score={score.toFixed(2)}
          >
            <Icon className="w-3.5 h-3.5" strokeWidth={2} />
            <span>{filter.label}</span>
          </button>
        );
      })}
    </div>
  );
}
