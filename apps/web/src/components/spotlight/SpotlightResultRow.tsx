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
}

// ============================================================================
// TYPE CONFIG - CelesteOS role colors (from branding/Brand/colour-system.md)
// ============================================================================

const TYPE_CONFIG: Record<string, { icon: React.ElementType; bg: string }> = {
  // Safety-critical: restricted red
  fault: { icon: AlertTriangle, bg: '#FF3B30' },
  hor_table: { icon: Clock, bg: '#FF3B30' },

  // Primary: celeste blue
  work_order: { icon: Wrench, bg: '#0070FF' },

  // Secondary: celeste blue-secondary
  equipment: { icon: Cog, bg: '#00A4FF' },
  document: { icon: FileText, bg: '#00A4FF' },
  document_chunk: { icon: FileText, bg: '#00A4FF' },
  checklist: { icon: ClipboardList, bg: '#00A4FF' },

  // Committed state: restricted green
  part: { icon: Package, bg: '#34C759' },

  // Time-sensitive: restricted orange/yellow
  handover: { icon: Users, bg: '#FF9500' },
  purchase: { icon: DollarSign, bg: '#FF9500' },

  // Email: purple (evidence/communication)
  email_thread: { icon: Mail, bg: '#AF52DE' },

  // Predictive/AI: celeste blue-soft
  worklist: { icon: ClipboardList, bg: '#BADDE9' },
  fleet_summary: { icon: Ship, bg: '#BADDE9' },
  smart_summary: { icon: Sparkles, bg: '#BADDE9' },
  predictive: { icon: Sparkles, bg: '#BADDE9' },
};

const DEFAULT_CONFIG = { icon: FileText, bg: '#86868B' };

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightResultRow({
  result,
  isSelected,
  index,
  onClick,
  onDoubleClick,
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
        'flex items-center gap-3 font-body',
        'mx-1.5 px-2.5 py-1.5',
        'cursor-pointer select-none',
        'rounded-celeste-sm',
        'transition-colors duration-celeste-fast',
        isSelected ? 'bg-celeste-blue' : 'bg-transparent'
      )}
    >
      {/* Icon - App icon style */}
      <div
        className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-celeste-md"
        style={{ backgroundColor: config.bg }}
      >
        <Icon className="w-4 h-4 text-celeste-white" strokeWidth={1.75} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-celeste-base font-normal truncate leading-tight',
            isSelected ? 'text-celeste-white' : 'text-celeste-text-primary'
          )}
        >
          {result.title}
        </p>
        {result.subtitle && (
          <p
            className={cn(
              'text-celeste-xs truncate leading-tight mt-px',
              isSelected ? 'text-celeste-white/70' : 'text-celeste-text-secondary'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
