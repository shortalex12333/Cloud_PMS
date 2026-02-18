'use client';

/**
 * PredictiveRiskModule
 * AI-driven predictive maintenance insights
 * Spans 2 columns for visual prominence
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { TrendingUp, AlertTriangle, Clock, Zap, ArrowRight, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ProgressBar } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { usePredictiveRiskData, PredictiveRisk } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface PredictiveRiskModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  risks?: PredictiveRisk[];
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function PredictiveRiskModule({
  isExpanded,
  onToggle,
  className,
  risks: propRisks,
}: PredictiveRiskModuleProps) {
  // Use hook data unless props are provided
  const hookData = usePredictiveRiskData();

  const risks = propRisks ?? hookData.risks;
  const isLoading = !propRisks && hookData.isLoading;

  const hasHighRisk = risks.some(p => p.impact === 'high' && p.probability > 80);
  const overallStatus = hasHighRisk ? 'warning' : 'healthy';

  // Calculate stats from risks data
  const activeAlerts = risks.length;
  const highRiskCount = risks.filter(r => r.probability >= 70).length;

  return (
    <ModuleContainer
      title="Predictive Insights"
      icon={<TrendingUp className="h-4.5 w-4.5 text-purple-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={`${activeAlerts} predictive alerts`}
      badge={activeAlerts}
      collapsedContent={
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Zap className="h-3 w-3 text-purple-500" />
            <span className="text-xs text-zinc-500">AI-Powered Analysis</span>
          </div>
          <span className="text-xs text-amber-500">
            {highRiskCount} high probability
          </span>
        </div>
      }
      className={className}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 text-zinc-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Stats header */}
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-200/60 dark:border-zinc-700/60">
            <div className="flex items-center gap-6">
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">Active Alerts</p>
                <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{activeAlerts}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">High Priority</p>
                <p className="text-lg font-semibold text-amber-600 dark:text-amber-400">{highRiskCount}</p>
              </div>
            </div>
            <div className={cn(
              'px-3 py-1.5 rounded-lg',
              'bg-purple-100 dark:bg-purple-900/30',
              'text-xs font-medium text-purple-600 dark:text-purple-400'
            )}>
              AI-Powered
            </div>
          </div>

          {/* Predictions grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {risks.map((risk) => (
              <div
                key={risk.id}
                className={cn(
                  'p-3 rounded-xl',
                  'bg-zinc-50 dark:bg-zinc-800/50',
                  'border border-zinc-200/60 dark:border-zinc-700/60',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'cursor-pointer transition-colors'
                )}
                onClick={() => console.log('View prediction:', risk.id)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className={cn(
                    'p-1.5 rounded-lg',
                    risk.impact === 'critical' || risk.impact === 'high' ? 'bg-red-100 dark:bg-red-900/30' :
                    risk.impact === 'medium' ? 'bg-amber-100 dark:bg-amber-900/30' :
                    'bg-zinc-100 dark:bg-zinc-800'
                  )}>
                    <AlertTriangle className={cn(
                      'h-4 w-4',
                      risk.impact === 'critical' || risk.impact === 'high' ? 'text-red-500' :
                      risk.impact === 'medium' ? 'text-amber-500' :
                      'text-txt-tertiary'
                    )} />
                  </div>
                  <span className={cn(
                    'text-xl font-bold tabular-nums',
                    risk.probability >= 80 ? 'text-red-500' :
                    risk.probability >= 60 ? 'text-amber-500' :
                    'text-txt-tertiary'
                  )}>
                    {risk.probability}%
                  </span>
                </div>

                {/* Content */}
                <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                  {risk.equipment}
                </h4>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 mb-2">
                  {risk.riskType}
                </p>

                {/* Timeframe */}
                <div className="flex items-center gap-1.5 mb-3">
                  <Clock className="h-3 w-3 text-zinc-400" />
                  <span className="text-xs text-zinc-500">
                    Expected: {risk.timeframe}
                  </span>
                </div>

                {/* Progress bar */}
                <ProgressBar
                  value={risk.probability}
                  status={risk.probability >= 80 ? 'critical' : risk.probability >= 60 ? 'warning' : 'neutral'}
                  size="sm"
                />

                {/* Action */}
                <div className="mt-3 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/60">
                  <p className="text-xs text-zinc-500 mb-1.5">Suggested:</p>
                  <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
                    {risk.recommendation}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Module actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="request_predictive_insight"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <ActionButton
              action="add_to_handover"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <button className={cn(
              'ml-auto px-3 py-1.5 rounded-lg',
              'text-xs font-medium',
              'text-brand-interactive hover:text-brand-hover',
              'hover:bg-brand-interactive/10 dark:hover:bg-brand-interactive/10',
              'transition-colors',
              'flex items-center gap-1'
            )}>
              View all insights
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
