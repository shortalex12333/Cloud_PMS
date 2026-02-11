'use client';

/**
 * SituationCard Component
 *
 * Displays a detected situation with severity indicator and recommendations.
 * Used within SituationPanel to show contextual AI-detected situations.
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, AlertCircle, Info, Clock, ChevronRight, Sparkles } from 'lucide-react';
import type { Situation, Recommendation } from '@/lib/situations/types';
import { ActionButton } from '@/components/actions/ActionButton';
import { MicroAction } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

interface SituationCardProps {
  /** The detected situation */
  situation: Situation;
  /** Recommended actions for this situation */
  recommendations: Recommendation[];
  /** Context for action execution */
  context?: Record<string, any>;
  /** Callback when action is executed */
  onActionExecuted?: (action: string) => void;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Additional class names */
  className?: string;
}

// ============================================================================
// HELPERS
// ============================================================================

function getSeverityConfig(severity: Situation['severity']) {
  switch (severity) {
    case 'high':
      return {
        icon: AlertCircle,
        bgColor: 'bg-red-50 dark:bg-red-900/20',
        borderColor: 'border-red-200 dark:border-red-800',
        textColor: 'text-red-700 dark:text-red-300',
        iconColor: 'text-red-500',
        badge: 'High Priority',
        badgeBg: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
      };
    case 'medium':
      return {
        icon: AlertTriangle,
        bgColor: 'bg-amber-50 dark:bg-amber-900/20',
        borderColor: 'border-amber-200 dark:border-amber-800',
        textColor: 'text-amber-700 dark:text-amber-300',
        iconColor: 'text-amber-500',
        badge: 'Attention Needed',
        badgeBg: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
      };
    case 'low':
    default:
      return {
        icon: Info,
        bgColor: 'bg-celeste-accent-subtle dark:bg-celeste-accent/10',
        borderColor: 'border-celeste-accent-muted dark:border-celeste-accent/30',
        textColor: 'text-celeste-accent dark:text-celeste-accent',
        iconColor: 'text-celeste-accent',
        badge: 'Info',
        badgeBg: 'bg-celeste-accent-subtle text-celeste-accent dark:bg-celeste-accent/20 dark:text-celeste-accent',
      };
  }
}

function getUrgencyColor(urgency: Recommendation['urgency']) {
  switch (urgency) {
    case 'urgent':
      return 'text-red-600 dark:text-red-400';
    case 'high':
      return 'text-orange-600 dark:text-orange-400';
    case 'elevated':
      return 'text-amber-600 dark:text-amber-400';
    default:
      return 'text-zinc-600 dark:text-zinc-400';
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

export function SituationCard({
  situation,
  recommendations,
  context = {},
  onActionExecuted,
  compact = false,
  className,
}: SituationCardProps) {
  const config = getSeverityConfig(situation.severity);
  const SeverityIcon = config.icon;

  return (
    <div
      className={cn(
        'rounded-xl border overflow-hidden',
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      {/* Header */}
      <div className={cn(
        'px-4 py-3',
        'flex items-start gap-3'
      )}>
        <div className={cn(
          'flex items-center justify-center',
          'w-8 h-8 rounded-lg shrink-0',
          'bg-white/80 dark:bg-zinc-800/80'
        )}>
          <SeverityIcon className={cn('h-4 w-4', config.iconColor)} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className={cn('text-[13px] font-semibold', config.textColor)}>
              {situation.label}
            </h4>
            <span className={cn(
              'px-1.5 py-0.5 rounded text-[10px] font-medium uppercase',
              config.badgeBg
            )}>
              {config.badge}
            </span>
          </div>

          {situation.context && (
            <div className="flex items-center gap-1 mt-1">
              <Clock className="h-3 w-3 text-zinc-400" />
              <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                {situation.context}
              </span>
            </div>
          )}
        </div>

        <Sparkles className="h-4 w-4 text-purple-400 shrink-0" />
      </div>

      {/* Evidence */}
      {!compact && situation.evidence.length > 0 && (
        <div className="px-4 pb-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 mb-1.5">
            Evidence
          </p>
          <ul className="space-y-1">
            {situation.evidence.map((item, i) => (
              <li key={i} className="flex items-start gap-2">
                <ChevronRight className="h-3 w-3 text-zinc-400 mt-0.5 shrink-0" />
                <span className="text-[12px] text-zinc-600 dark:text-zinc-300">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className={cn(
          'px-4 py-3',
          'bg-white/60 dark:bg-zinc-800/40',
          'border-t border-zinc-200/60 dark:border-zinc-700/40'
        )}>
          <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 mb-2">
            Recommended Actions
          </p>
          <div className="space-y-2">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex items-center gap-3">
                <ActionButton
                  action={rec.action as MicroAction}
                  context={{ ...context, template: rec.template }}
                  size="sm"
                  onSuccess={() => onActionExecuted?.(rec.action)}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] text-zinc-700 dark:text-zinc-300 truncate">
                    {rec.reason}
                  </p>
                  {rec.urgency !== 'normal' && (
                    <span className={cn(
                      'text-[10px] font-medium uppercase',
                      getUrgencyColor(rec.urgency)
                    )}>
                      {rec.urgency}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SituationCard;
