'use client';

/**
 * FaultActivityModule
 * Recent fault activity for Control Center
 * Connected to real dashboard data via useDashboardData hook
 */

import React, { useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { DiagnoseFaultModal, ReportFaultModal } from '@/components/modals';
import { useFaultData, FaultSummary, FaultStats } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface FaultActivityModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  // Optional: allow passing data directly for testing
  faults?: FaultSummary[];
  stats?: FaultStats;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function FaultActivityModule({
  isExpanded,
  onToggle,
  className,
  faults: propFaults,
  stats: propStats,
}: FaultActivityModuleProps) {
  // Modal state
  const [diagnoseFaultId, setDiagnoseFaultId] = useState<string | null>(null);
  const [showReportFault, setShowReportFault] = useState(false);

  // Use hook data unless props are provided
  const hookData = useFaultData();

  const faults = propFaults ?? hookData.faults;
  const stats = propStats ?? hookData.stats;
  const isLoading = !propFaults && hookData.isLoading;

  const hasActiveCritical = faults.some(f => f.status === 'open' && f.severity === 'critical');
  const overallStatus = hasActiveCritical ? 'critical' : stats.open > 0 ? 'warning' : 'healthy';

  return (
    <ModuleContainer
      title="Fault Activity"
      icon={<AlertTriangle className="h-4.5 w-4.5 text-red-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={hasActiveCritical ? 'Critical fault active' : `${stats.open} active faults`}
      badge={stats.open}
      collapsedContent={
        <div className="flex items-center gap-2">
          <span className={cn(
            'px-2 py-0.5 rounded-full',
            'text-[11px] font-medium',
            hasActiveCritical ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                               'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
          )}>
            {stats.open} active
          </span>
          <span className="text-[11px] text-zinc-400">·</span>
          <span className="text-[11px] text-zinc-500">{stats.resolved} resolved</span>
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
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <StatCard
              label="Active"
              value={stats.open}
              status={stats.open > 0 ? 'warning' : 'healthy'}
            />
            <StatCard
              label="Investigating"
              value={stats.investigating}
              status="warning"
            />
            <StatCard
              label="Resolved"
              value={stats.resolved}
              status="healthy"
            />
          </div>

          {/* Fault list */}
          <div className="space-y-1">
            {faults.map((fault) => {
              const severityIcon = fault.severity === 'critical' ? AlertCircle :
                                  fault.severity === 'high' ? AlertTriangle : Clock;
              const SeverityIcon = severityIcon;
              const itemStatus = fault.severity === 'critical' ? 'critical' :
                                fault.severity === 'high' ? 'warning' : 'neutral';

              return (
                <ModuleItem
                  key={fault.id}
                  icon={<SeverityIcon className={cn(
                    'h-4 w-4',
                    fault.severity === 'critical' && 'text-red-500',
                    fault.severity === 'high' && 'text-amber-500',
                    (fault.severity === 'medium' || fault.severity === 'low') && 'text-zinc-400'
                  )} />}
                  title={fault.title}
                  subtitle={`${fault.code} · ${fault.equipment}`}
                  status={fault.status === 'resolved' ? 'healthy' : itemStatus}
                  value={fault.timestamp}
                  onClick={() => console.log('Open fault:', fault.id)}
                  actions={
                    fault.status !== 'resolved' && (
                      <ActionButton
                        action="diagnose_fault"
                        context={{ fault_id: fault.id }}
                        size="sm"
                        iconOnly
                        onSuccess={() => hookData.refresh?.()}
                      />
                    )
                  }
                />
              );
            })}
          </div>

          {/* Module actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="report_fault"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'text-[12px] font-medium',
              'text-celeste-accent hover:text-celeste-accent-hover',
              'hover:bg-celeste-accent-subtle dark:hover:bg-celeste-accent-subtle',
              'transition-colors'
            )}>
              View all →
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
