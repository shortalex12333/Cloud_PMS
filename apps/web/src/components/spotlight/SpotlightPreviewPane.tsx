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

// Celeste brand colors for card types (dignified, not loud)
const CARD_TYPE_CONFIG: Record<CardType, { icon: keyof typeof LucideIcons; color: string; bgColor: string }> = {
  fault: { icon: 'AlertTriangle', color: 'text-restricted-red', bgColor: 'bg-restricted-red/10' },
  work_order: { icon: 'Wrench', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  equipment: { icon: 'Cog', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  part: { icon: 'Package', color: 'text-restricted-green', bgColor: 'bg-restricted-green/10' },
  handover: { icon: 'Users', color: 'text-restricted-orange', bgColor: 'bg-restricted-orange/10' },
  document: { icon: 'FileText', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  hor_table: { icon: 'Clock', color: 'text-restricted-red', bgColor: 'bg-restricted-red/10' },
  purchase: { icon: 'DollarSign', color: 'text-restricted-orange', bgColor: 'bg-restricted-orange/10' },
  checklist: { icon: 'ClipboardList', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  worklist: { icon: 'ClipboardList', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  fleet_summary: { icon: 'Ship', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
  smart_summary: { icon: 'Sparkles', color: 'text-celeste-accent', bgColor: 'bg-celeste-accent-subtle' },
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
        'w-celeste-panel-medium flex-shrink-0',
        'bg-celeste-surface-light/98 dark:bg-celeste-surface/98',
        'backdrop-blur-celeste-md',
        'border border-celeste-border-subtle-light dark:border-celeste-border-subtle',
        'rounded-celeste-xl',
        'shadow-celeste-lg',
        'overflow-hidden',
        'animate-in slide-in-from-right-2 duration-normal'
      )}
    >
      {/* Header */}
      <div className={cn(
        'px-4 py-3',
        'border-b border-celeste-divider-light dark:border-celeste-divider',
        config.bgColor
      )}>
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex items-center justify-center',
            'w-10 h-10 rounded-celeste-lg',
            'bg-celeste-surface-light/80 dark:bg-celeste-bg-tertiary/80',
            'shadow-sm'
          )}>
            <IconComponent className={cn('h-5 w-5', config.color)} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-celeste-lg font-semibold text-celeste-text-title-light dark:text-celeste-text-title truncate">
              {result.title}
            </h3>
            <p className="text-celeste-sm text-celeste-text-secondary truncate">
              {result.subtitle}
            </p>
          </div>
          <button
            onClick={onClose}
            className={cn(
              'p-1.5 rounded-md',
              'text-celeste-text-muted hover:text-celeste-text-primary-light',
              'dark:text-celeste-text-muted dark:hover:text-celeste-text-primary',
              'hover:bg-celeste-bg-secondary-light/50 dark:hover:bg-celeste-bg-tertiary/50',
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
          <label className="sr-section-header">
            Match Confidence
          </label>
          <div className="mt-1.5 flex items-center gap-2">
            <div className="flex-1 h-2 bg-celeste-bg-secondary-light dark:bg-celeste-bg-tertiary rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  result.confidence >= 80 ? 'bg-restricted-green' :
                  result.confidence >= 50 ? 'bg-restricted-orange' : 'bg-restricted-red'
                )}
                style={{ width: `${result.confidence}%` }}
              />
            </div>
            <span className="sr-meta tabular-nums">
              {result.confidence}%
            </span>
          </div>
        </div>

        {/* Metadata */}
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <div>
            <label className="sr-section-header">
              Details
            </label>
            <div className="mt-1.5 space-y-1.5">
              {Object.entries(result.metadata).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="sr-sub capitalize">
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span className="sr-meta">
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions by cluster */}
        <div>
          <label className="sr-section-header">
            Available Actions
          </label>
          <div className="mt-2 space-y-3">
            {Object.entries(actionsByCluster).map(([cluster, actions]) => (
              <div key={cluster}>
                <span className="text-celeste-xs text-celeste-text-muted capitalize">
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
        'border-t border-celeste-divider-light dark:border-celeste-divider',
        'bg-celeste-panel-light/80 dark:bg-celeste-panel/80',
        'flex items-center justify-between'
      )}>
        <span className="text-celeste-xs text-celeste-text-muted">
          Press <kbd className="px-1 py-0.5 rounded bg-celeste-bg-secondary-light dark:bg-celeste-bg-tertiary text-celeste-xs font-medium">Tab</kbd> to cycle actions
        </span>
        <button
          className={cn(
            'px-3 py-1.5 rounded-md',
            'bg-celeste-accent hover:bg-celeste-accent-hover',
            'text-celeste-sm font-medium text-white',
            'transition-colors'
          )}
        >
          Open
        </button>
      </div>
    </div>
  );
}
