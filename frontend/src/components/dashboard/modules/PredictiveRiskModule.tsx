'use client';

/**
 * PredictiveRiskModule
 * AI-driven predictive maintenance insights
 * Spans 2 columns for visual prominence
 */

import React from 'react';
import { TrendingUp, AlertTriangle, Clock, Zap, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ProgressBar } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const PREDICTIONS = [
  {
    id: 'pred-1',
    equipment: 'Main Generator #1',
    issue: 'Coolant pump bearing wear detected',
    probability: 87,
    timeframe: '7-14 days',
    impact: 'high' as const,
    suggestedAction: 'Schedule preventive replacement',
  },
  {
    id: 'pred-2',
    equipment: 'Port Stabiliser',
    issue: 'Hydraulic pressure trending low',
    probability: 72,
    timeframe: '21-30 days',
    impact: 'medium' as const,
    suggestedAction: 'Check for seal degradation',
  },
  {
    id: 'pred-3',
    equipment: 'HVAC Compressor #2',
    issue: 'Refrigerant levels declining',
    probability: 65,
    timeframe: '30+ days',
    impact: 'low' as const,
    suggestedAction: 'Schedule leak inspection',
  },
];

const STATS = {
  activeAlerts: 3,
  preventedFailures: 12,
  accuracy: 94,
};

// ============================================================================
// COMPONENT
// ============================================================================

interface PredictiveRiskModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export default function PredictiveRiskModule({
  isExpanded,
  onToggle,
  className,
}: PredictiveRiskModuleProps) {
  const hasHighRisk = PREDICTIONS.some(p => p.impact === 'high' && p.probability > 80);
  const overallStatus = hasHighRisk ? 'warning' : 'healthy';

  return (
    <ModuleContainer
      title="Predictive Insights"
      icon={<TrendingUp className="h-4.5 w-4.5 text-purple-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={`${STATS.activeAlerts} predictive alerts`}
      badge={STATS.activeAlerts}
      collapsedContent={
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Zap className="h-3 w-3 text-purple-500" />
            <span className="text-[11px] text-zinc-500">{STATS.accuracy}% accuracy</span>
          </div>
          <span className="text-[11px] text-emerald-500">
            {STATS.preventedFailures} failures prevented
          </span>
        </div>
      }
      className={className}
    >
      {/* Stats header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-200/60 dark:border-zinc-700/60">
        <div className="flex items-center gap-6">
          <div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Model Accuracy</p>
            <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{STATS.accuracy}%</p>
          </div>
          <div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Failures Prevented</p>
            <p className="text-lg font-semibold text-emerald-600 dark:text-emerald-400">{STATS.preventedFailures}</p>
          </div>
        </div>
        <div className={cn(
          'px-3 py-1.5 rounded-lg',
          'bg-purple-100 dark:bg-purple-900/30',
          'text-[12px] font-medium text-purple-600 dark:text-purple-400'
        )}>
          AI-Powered
        </div>
      </div>

      {/* Predictions grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PREDICTIONS.map((pred) => (
          <div
            key={pred.id}
            className={cn(
              'p-3 rounded-xl',
              'bg-zinc-50 dark:bg-zinc-800/50',
              'border border-zinc-200/60 dark:border-zinc-700/60',
              'hover:bg-zinc-100 dark:hover:bg-zinc-800',
              'cursor-pointer transition-colors'
            )}
            onClick={() => console.log('View prediction:', pred.id)}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div className={cn(
                'p-1.5 rounded-lg',
                pred.impact === 'high' ? 'bg-red-100 dark:bg-red-900/30' :
                pred.impact === 'medium' ? 'bg-amber-100 dark:bg-amber-900/30' :
                'bg-blue-100 dark:bg-blue-900/30'
              )}>
                <AlertTriangle className={cn(
                  'h-4 w-4',
                  pred.impact === 'high' ? 'text-red-500' :
                  pred.impact === 'medium' ? 'text-amber-500' :
                  'text-blue-500'
                )} />
              </div>
              <span className={cn(
                'text-xl font-bold tabular-nums',
                pred.probability >= 80 ? 'text-red-500' :
                pred.probability >= 60 ? 'text-amber-500' :
                'text-blue-500'
              )}>
                {pred.probability}%
              </span>
            </div>

            {/* Content */}
            <h4 className="text-[13px] font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
              {pred.equipment}
            </h4>
            <p className="text-[12px] text-zinc-600 dark:text-zinc-400 mb-2">
              {pred.issue}
            </p>

            {/* Timeframe */}
            <div className="flex items-center gap-1.5 mb-3">
              <Clock className="h-3 w-3 text-zinc-400" />
              <span className="text-[11px] text-zinc-500">
                Expected: {pred.timeframe}
              </span>
            </div>

            {/* Progress bar */}
            <ProgressBar
              value={pred.probability}
              status={pred.probability >= 80 ? 'critical' : pred.probability >= 60 ? 'warning' : 'neutral'}
              size="sm"
            />

            {/* Action */}
            <div className="mt-3 pt-2 border-t border-zinc-200/60 dark:border-zinc-700/60">
              <p className="text-[11px] text-zinc-500 mb-1.5">Suggested:</p>
              <p className="text-[12px] font-medium text-zinc-700 dark:text-zinc-300">
                {pred.suggestedAction}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Module actions */}
      <div className="flex items-center gap-2 mt-4">
        <MicroactionButton
          action="request_predictive_insight"
          size="md"
          showLabel
          onClick={() => console.log('Request insight')}
        />
        <MicroactionButton
          action="add_to_handover"
          size="md"
          showLabel
          onClick={() => console.log('Add to handover')}
        />
        <button className={cn(
          'ml-auto px-3 py-1.5 rounded-lg',
          'text-[12px] font-medium',
          'text-blue-500 hover:text-blue-600',
          'hover:bg-blue-50 dark:hover:bg-blue-900/20',
          'transition-colors',
          'flex items-center gap-1'
        )}>
          View all insights
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </ModuleContainer>
  );
}
