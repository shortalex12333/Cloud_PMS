'use client';

/**
 * SpotlightResultRow
 * Apple Spotlight-identical result row
 *
 * Brand tokens: blue for selection, text colors, duration-fast
 */

import React from 'react';
import {
  AlertTriangle, Wrench, Cog, Package, FileText,
  ClipboardList, Ship, Sparkles, Users, Clock, DollarSign, Mail
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

interface SpotlightResultRowProps {
  result: SpotlightResult;
  isSelected: boolean;
  index: number;
  onClick?: () => void;
  onDoubleClick?: () => void;
  /** Top Match gets slightly larger styling */
  isTopMatch?: boolean;
}

// ============================================================================
// TYPE CONFIG - CelesteOS role colors (from branding/Brand/colour-system.md)
// ============================================================================

// Celeste Brand Colors (from tailwind.config.ts)
const CELESTE_COLORS = {
  accent: '#3A7C9D',      // Maritime teal - primary action
  red: '#9D3A3A',         // Dignified warning
  orange: '#9D6B3A',      // Time-sensitive
  green: '#3A9D5C',       // Committed state
  muted: '#6A6E72',       // Default/neutral
} as const;

const TYPE_CONFIG: Record<string, { icon: React.ElementType; bg: string }> = {
  // Safety-critical: restricted red
  fault: { icon: AlertTriangle, bg: CELESTE_COLORS.red },
  hor_table: { icon: Clock, bg: CELESTE_COLORS.red },

  // Primary: celeste accent (maritime teal)
  work_order: { icon: Wrench, bg: CELESTE_COLORS.accent },

  // Secondary: celeste accent
  equipment: { icon: Cog, bg: CELESTE_COLORS.accent },
  document: { icon: FileText, bg: CELESTE_COLORS.accent },
  document_chunk: { icon: FileText, bg: CELESTE_COLORS.accent },
  checklist: { icon: ClipboardList, bg: CELESTE_COLORS.accent },

  // Committed state: restricted green
  part: { icon: Package, bg: CELESTE_COLORS.green },

  // Time-sensitive: restricted orange
  handover: { icon: Users, bg: CELESTE_COLORS.orange },
  purchase: { icon: DollarSign, bg: CELESTE_COLORS.orange },

  // Email: celeste accent (unified brand)
  email_thread: { icon: Mail, bg: CELESTE_COLORS.accent },

  // Predictive/AI: celeste accent (muted)
  worklist: { icon: ClipboardList, bg: CELESTE_COLORS.accent },
  fleet_summary: { icon: Ship, bg: CELESTE_COLORS.accent },
  smart_summary: { icon: Sparkles, bg: CELESTE_COLORS.accent },
  predictive: { icon: Sparkles, bg: CELESTE_COLORS.accent },
};

const DEFAULT_CONFIG = { icon: FileText, bg: CELESTE_COLORS.muted };

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightResultRow({
  result,
  isSelected,
  index,
  onClick,
  onDoubleClick,
  isTopMatch = false,
}: SpotlightResultRowProps) {
  const config = TYPE_CONFIG[result.type] || DEFAULT_CONFIG;
  const Icon = config.icon;

  return (
    <div
      data-index={index}
      data-testid="search-result-item"
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      className={cn(
        'sr-row',
        'cursor-pointer select-none',
        'rounded-celeste-sm',
        'transition-colors duration-celeste-fast',
        isSelected && 'sr-row-selected',
        isSelected ? 'bg-celeste-accent' : 'bg-transparent',
        isTopMatch && !isSelected && 'bg-celeste-bg-tertiary'
      )}
    >
      {/* Icon - App icon style (larger for Top Match) */}
      <div
        className={cn(
          'flex-shrink-0 flex items-center justify-center rounded-celeste-md',
          isTopMatch ? 'w-10 h-10' : 'w-8 h-8'
        )}
        style={{ backgroundColor: config.bg }}
      >
        <Icon
          className={cn(
            'text-celeste-white',
            isTopMatch ? 'w-5 h-5' : 'w-4 h-4'
          )}
          strokeWidth={1.75}
        />
      </div>

      {/* Content - using sr-* typography classes */}
      <div className="sr-content">
        <p
          className={cn(
            'sr-title',
            isSelected && 'text-celeste-white'
          )}
        >
          {result.title}
        </p>
        {result.subtitle && (
          <p
            className={cn(
              'sr-sub',
              isSelected && 'text-celeste-white/70'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
