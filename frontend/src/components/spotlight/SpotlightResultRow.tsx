'use client';

/**
 * SpotlightResultRow
 * Apple Spotlight-identical result row
 *
 * Anatomy (Apple style):
 * [40px Icon] [Title + Subtitle stacked]
 *
 * NO: badges, confidence bars, chevrons, microactions
 * YES: clean, minimal, focused
 */

import React from 'react';
import {
  AlertTriangle, Wrench, Cog, Package, FileText,
  ClipboardList, Ship, Sparkles, Users, Clock, DollarSign
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
// TYPE ICON MAPPING - App icon style
// ============================================================================

const TYPE_CONFIG: Record<string, { icon: React.ElementType; bg: string }> = {
  fault: { icon: AlertTriangle, bg: 'bg-[#FF3B30]' },
  work_order: { icon: Wrench, bg: 'bg-[#007AFF]' },
  equipment: { icon: Cog, bg: 'bg-[#5856D6]' },
  part: { icon: Package, bg: 'bg-[#34C759]' },
  handover: { icon: Users, bg: 'bg-[#FF9500]' },
  document: { icon: FileText, bg: 'bg-[#5AC8FA]' },
  document_chunk: { icon: FileText, bg: 'bg-[#5AC8FA]' },
  hor_table: { icon: Clock, bg: 'bg-[#FF2D55]' },
  purchase: { icon: DollarSign, bg: 'bg-[#30B0C7]' },
  checklist: { icon: ClipboardList, bg: 'bg-[#64D2FF]' },
  worklist: { icon: ClipboardList, bg: 'bg-[#BF5AF2]' },
  fleet_summary: { icon: Ship, bg: 'bg-[#32ADE6]' },
  smart_summary: { icon: Sparkles, bg: 'bg-[#AF52DE]' },
  predictive: { icon: Sparkles, bg: 'bg-[#AF52DE]' },
};

const DEFAULT_CONFIG = { icon: FileText, bg: 'bg-[#8E8E93]' };

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
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      className={cn(
        'flex items-center gap-3',
        'px-4 py-2 mx-1',
        'cursor-default select-none',
        'rounded-lg',
        'transition-colors duration-75',
        isSelected
          ? 'bg-[#0066CC] text-white'
          : 'hover:bg-black/[0.04] dark:hover:bg-white/[0.06]'
      )}
    >
      {/* Icon - App icon style (40px rounded square) */}
      <div
        className={cn(
          'flex-shrink-0 flex items-center justify-center',
          'w-10 h-10 rounded-[10px]',
          config.bg,
          'shadow-sm'
        )}
      >
        <Icon
          className={cn(
            'w-5 h-5',
            'text-white'
          )}
          strokeWidth={1.75}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 py-0.5">
        {/* Title */}
        <p
          className={cn(
            'text-[15px] font-medium truncate leading-tight',
            isSelected
              ? 'text-white'
              : 'text-[#1d1d1f] dark:text-[#f5f5f7]'
          )}
        >
          {result.title}
        </p>

        {/* Subtitle */}
        {result.subtitle && (
          <p
            className={cn(
              'text-[13px] truncate leading-tight mt-0.5',
              isSelected
                ? 'text-white/80'
                : 'text-[#86868b] dark:text-[#98989d]'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
