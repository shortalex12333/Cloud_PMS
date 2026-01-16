'use client';

/**
 * SpotlightPreviewPane
 * Right-side preview panel showing detailed result information
 */

import React from 'react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';
import { MicroAction, ACTION_REGISTRY, CardType } from '@/types/actions';
import { ActionButton } from '@/components/actions/ActionButton';

// ============================================================================
// TYPES
// ============================================================================

interface SearchResult {
  id: string;
  type: CardType;
  title: string;
  subtitle: string;
  confidence: number;
  actions: MicroAction[];
  metadata?: Record<string, any>;
}

interface SpotlightPreviewPaneProps {
  result: SearchResult;
  onClose?: () => void;
}

// ============================================================================
// CARD TYPE CONFIG
// ============================================================================

const CARD_TYPE_CONFIG: Record<CardType, { icon: keyof typeof LucideIcons; color: string; bgColor: string }> = {
  fault: { icon: 'AlertTriangle', color: 'text-red-500', bgColor: 'bg-red-500/10' },
  work_order: { icon: 'Wrench', color: 'text-blue-500', bgColor: 'bg-blue-500/10' },
  equipment: { icon: 'Cog', color: 'text-violet-500', bgColor: 'bg-violet-500/10' },
  part: { icon: 'Package', color: 'text-emerald-500', bgColor: 'bg-emerald-500/10' },
  handover: { icon: 'Users', color: 'text-amber-500', bgColor: 'bg-amber-500/10' },
  document: { icon: 'FileText', color: 'text-indigo-500', bgColor: 'bg-indigo-500/10' },
  hor_table: { icon: 'Clock', color: 'text-pink-500', bgColor: 'bg-pink-500/10' },
  purchase: { icon: 'DollarSign', color: 'text-teal-500', bgColor: 'bg-teal-500/10' },
  checklist: { icon: 'ClipboardList', color: 'text-lime-500', bgColor: 'bg-lime-500/10' },
  worklist: { icon: 'ClipboardList', color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
  fleet_summary: { icon: 'Ship', color: 'text-cyan-500', bgColor: 'bg-cyan-500/10' },
  smart_summary: { icon: 'Sparkles', color: 'text-purple-500', bgColor: 'bg-purple-500/10' },
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightPreviewPane({
  result,
  onClose,
}: SpotlightPreviewPaneProps) {
  const config = CARD_TYPE_CONFIG[result.type];
  const IconComponent = (LucideIcons as any)[config.icon] || LucideIcons.Circle;

  // Group actions by cluster
  const actionsByCluster = result.actions.reduce((acc, action) => {
    const meta = ACTION_REGISTRY[action];
    const cluster = meta?.cluster || 'other';
    if (!acc[cluster]) acc[cluster] = [];
    acc[cluster].push(action);
    return acc;
  }, {} as Record<string, MicroAction[]>);

  return (
    <div
      className={cn(
        'w-[320px] flex-shrink-0',
        'bg-white/98 dark:bg-zinc-900/98',
        'backdrop-blur-[20px]',
        'border border-zinc-200/60 dark:border-zinc-700/60',
        'rounded-[14px]',
        'shadow-[0_8px_32px_rgba(0,0,0,0.12),0_2px_8px_rgba(0,0,0,0.08)]',
        'dark:shadow-[0_8px_32px_rgba(0,0,0,0.4),0_2px_8px_rgba(0,0,0,0.2)]',
        'overflow-hidden',
        'animate-in slide-in-from-right-2 duration-200'
      )}
    >
      {/* Header */}
      <div className={cn(
        'px-4 py-3',
        'border-b border-zinc-200/60 dark:border-zinc-700/60',
        config.bgColor
      )}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex items-center justify-center',
            'w-10 h-10 rounded-xl',
            'bg-white/80 dark:bg-zinc-800/80',
            'shadow-sm'
          )}>
            <IconComponent className={cn('h-5 w-5', config.color)} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100 truncate">
              {result.title}
            </h3>
            <p className="text-[12px] text-zinc-500 dark:text-zinc-400 truncate">
              {result.subtitle}
            </p>
          </div>
          <button
            onClick={onClose}
            className={cn(
              'p-1.5 rounded-md',
              'text-zinc-400 hover:text-zinc-600',
              'dark:text-zinc-500 dark:hover:text-zinc-300',
              'hover:bg-zinc-200/50 dark:hover:bg-zinc-700/50',
              'transition-colors'
            )}
          >
            <LucideIcons.X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Confidence */}
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Match Confidence
          </label>
          <div className="mt-1.5 flex items-center gap-2">
            <div className="flex-1 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  result.confidence >= 80 ? 'bg-emerald-500' :
                  result.confidence >= 50 ? 'bg-amber-500' : 'bg-red-500'
                )}
                style={{ width: `${result.confidence}%` }}
              />
            </div>
            <span className="text-[13px] font-medium text-zinc-700 dark:text-zinc-300 tabular-nums">
              {result.confidence}%
            </span>
          </div>
        </div>

        {/* Metadata */}
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <div>
            <label className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              Details
            </label>
            <div className="mt-1.5 space-y-1.5">
              {Object.entries(result.metadata).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-[13px] text-zinc-500 dark:text-zinc-400 capitalize">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span className="text-[13px] font-medium text-zinc-700 dark:text-zinc-300">
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions by cluster */}
        <div>
          <label className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            Available Actions
          </label>
          <div className="mt-2 space-y-3">
            {Object.entries(actionsByCluster).map(([cluster, actions]) => (
              <div key={cluster}>
                <span className="text-[11px] text-zinc-400 dark:text-zinc-500 capitalize">
                  {cluster.replace(/_/g, ' ')}
                </span>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {actions.map((action) => (
                    <ActionButton
                      key={action}
                      action={action}
                      context={{ entity_id: result.id, entity_type: result.type }}
                      size="sm"
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className={cn(
        'px-4 py-3',
        'border-t border-zinc-200/60 dark:border-zinc-700/60',
        'bg-zinc-50/80 dark:bg-zinc-800/80',
        'flex items-center justify-between'
      )}>
        <span className="text-[11px] text-zinc-400 dark:text-zinc-500">
          Press <kbd className="px-1 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-[10px] font-medium">Tab</kbd> to cycle actions
        </span>
        <button
          className={cn(
            'px-3 py-1.5 rounded-md',
            'bg-blue-500 hover:bg-blue-600',
            'text-[12px] font-medium text-white',
            'transition-colors'
          )}
        >
          Open
        </button>
      </div>
    </div>
  );
}
