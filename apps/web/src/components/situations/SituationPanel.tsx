'use client';

/**
 * SituationPanel Component
 *
 * Displays AI-detected situations with contextual recommendations.
 * Integrates with the situation engine to provide intelligent suggestions.
 *
 * Features:
 * - Auto-detects situations based on entity context
 * - Shows severity-aware cards with evidence
 * - Provides actionable recommendations
 * - Supports multiple situation types
 */

import React, { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Sparkles, RefreshCw, X } from 'lucide-react';
import { useSituation } from '@/lib/situations/hooks/useSituation';
import { SituationCard } from './SituationCard';
import type { ResolvedEntity, UserRole } from '@/lib/situations/types';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface SituationPanelProps {
  /** Yacht ID for situation detection */
  yachtId: string;
  /** Entity type being viewed */
  entityType: 'fault' | 'work_order' | 'equipment' | 'part' | 'document';
  /** Entity ID being viewed */
  entityId: string;
  /** Entity name/label for display */
  entityName?: string;
  /** Additional context for action execution */
  actionContext?: Record<string, any>;
  /** Whether to auto-analyze on mount */
  autoAnalyze?: boolean;
  /** Callback when situation changes */
  onSituationChange?: (hasSituation: boolean) => void;
  /** Additional class names */
  className?: string;
}

// ============================================================================
// HELPERS
// ============================================================================

function mapEntityTypeToSituationType(entityType: SituationPanelProps['entityType']): ResolvedEntity['type'] {
  switch (entityType) {
    case 'fault':
      return 'fault';
    case 'work_order':
      return 'work_order';
    case 'equipment':
      return 'equipment';
    case 'part':
      return 'part';
    case 'document':
      return 'document';
    default:
      return 'equipment';
  }
}

function mapUserRole(role?: string): UserRole {
  switch (role) {
    case 'captain':
      return 'captain';
    case 'chief_engineer':
      return 'chief_engineer';
    case 'engineer':
    case 'eto':
      return 'engineer';
    case 'manager':
    case 'admin':
    case 'owner':
      return 'management';
    default:
      return 'crew';
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

export function SituationPanel({
  yachtId,
  entityType,
  entityId,
  entityName,
  actionContext,
  autoAnalyze = true,
  onSituationChange,
  className,
}: SituationPanelProps) {
  const { user } = useAuth();
  const userRole = mapUserRole(user?.role);

  const {
    situation,
    recommendations,
    isDetecting,
    error,
    analyzeEntities,
    clearSituation,
  } = useSituation({
    yachtId,
    userRole,
    onSituationDetected: () => onSituationChange?.(true),
  });

  // Auto-analyze on mount or when entity changes
  useEffect(() => {
    if (!autoAnalyze) return;

    const entities: ResolvedEntity[] = [
      {
        type: mapEntityTypeToSituationType(entityType),
        entity_id: entityId,
        canonical: entityName || entityId,
        confidence: 1.0,
      },
    ];

    analyzeEntities(entities);
  }, [entityType, entityId, entityName, autoAnalyze, analyzeEntities]);

  // Notify parent when situation changes
  useEffect(() => {
    onSituationChange?.(situation !== null);
  }, [situation, onSituationChange]);

  // No situation detected
  if (!situation && !isDetecting && !error) {
    return null;
  }

  // Context for action execution
  const context = {
    ...actionContext,
    [`${entityType}_id`]: entityId,
    entity_id: entityId,
    entity_type: entityType,
  };

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-500" />
          <span className="text-celeste-xs font-semibold text-zinc-700 dark:text-zinc-300">
            AI Insights
          </span>
        </div>

        <div className="flex items-center gap-1">
          {isDetecting && (
            <RefreshCw className="h-3.5 w-3.5 text-zinc-400 animate-spin" />
          )}
          {situation && (
            <button
              onClick={clearSituation}
              className={cn(
                'p-1 rounded-md',
                'text-zinc-400 hover:text-zinc-600',
                'dark:hover:text-zinc-300',
                'hover:bg-zinc-100 dark:hover:bg-zinc-700',
                'transition-colors'
              )}
              aria-label="Dismiss"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Loading state */}
      {isDetecting && !situation && (
        <div className={cn(
          'px-4 py-6 rounded-xl',
          'bg-zinc-50 dark:bg-zinc-800/50',
          'border border-zinc-200/60 dark:border-zinc-700/60',
          'flex items-center justify-center'
        )}>
          <RefreshCw className="h-5 w-5 text-zinc-400 animate-spin mr-2" />
          <span className="text-celeste-sm text-zinc-500">Analyzing...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className={cn(
          'px-4 py-3 rounded-xl',
          'bg-red-50 dark:bg-red-900/20',
          'border border-red-200 dark:border-red-800',
          'text-celeste-xs text-red-600 dark:text-red-400'
        )}>
          Failed to analyze: {error}
        </div>
      )}

      {/* Situation card */}
      {situation && (
        <SituationCard
          situation={situation}
          recommendations={recommendations}
          context={context}
          onActionExecuted={(action) => {
            console.log('Action executed:', action);
          }}
        />
      )}

      {/* No situation state (only if auto-analyze completed) */}
      {!isDetecting && !situation && !error && autoAnalyze && (
        <div className={cn(
          'px-4 py-4 rounded-xl',
          'bg-emerald-50 dark:bg-emerald-900/20',
          'border border-emerald-200 dark:border-emerald-800',
          'text-center'
        )}>
          <span className="text-celeste-xs text-emerald-600 dark:text-emerald-400">
            No issues detected
          </span>
        </div>
      )}
    </div>
  );
}

export default SituationPanel;
