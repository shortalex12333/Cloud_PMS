'use client';

/**
 * SpotlightResultRow
 * Apple Spotlight-identical result row
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
// TYPE CONFIG - Apple system colors
// ============================================================================

const TYPE_CONFIG: Record<string, { icon: React.ElementType; bg: string }> = {
  fault: { icon: AlertTriangle, bg: '#FF453A' },
  work_order: { icon: Wrench, bg: '#0A84FF' },
  equipment: { icon: Cog, bg: '#5E5CE6' },
  part: { icon: Package, bg: '#30D158' },
  handover: { icon: Users, bg: '#FF9F0A' },
  document: { icon: FileText, bg: '#64D2FF' },
  document_chunk: { icon: FileText, bg: '#64D2FF' },
  hor_table: { icon: Clock, bg: '#FF375F' },
  purchase: { icon: DollarSign, bg: '#40C8E0' },
  checklist: { icon: ClipboardList, bg: '#64D2FF' },
  worklist: { icon: ClipboardList, bg: '#BF5AF2' },
  fleet_summary: { icon: Ship, bg: '#32ADE6' },
  smart_summary: { icon: Sparkles, bg: '#BF5AF2' },
  predictive: { icon: Sparkles, bg: '#BF5AF2' },
};

const DEFAULT_CONFIG = { icon: FileText, bg: '#8E8E93' };

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
        'mx-1.5 px-2.5 py-1.5',
        'cursor-default select-none',
        'rounded-md',
        'transition-colors duration-[50ms]'
      )}
      style={{
        backgroundColor: isSelected ? '#0A84FF' : 'transparent',
      }}
    >
      {/* Icon - App icon style */}
      <div
        className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg"
        style={{ backgroundColor: config.bg }}
      >
        <Icon className="w-4 h-4 text-white" strokeWidth={1.75} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-[13px] font-normal truncate leading-tight',
            isSelected ? 'text-white' : 'text-[#f5f5f7]'
          )}
        >
          {result.title}
        </p>
        {result.subtitle && (
          <p
            className={cn(
              'text-[11px] truncate leading-tight mt-px',
              isSelected ? 'text-white/70' : 'text-[#98989f]'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
