'use client';

/**
 * FaultActivityModule
 * Recent fault activity for Control Center
 */

import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const MOCK_FAULTS = [
  {
    id: 'F-2024-0127',
    title: 'Generator 1 Overheating',
    equipment: 'Main Generator #1',
    severity: 'critical' as const,
    timeAgo: '2h ago',
    status: 'open' as const,
  },
  {
    id: 'F-2024-0126',
    title: 'Low Fuel Pressure Warning',
    equipment: 'Fuel System',
    severity: 'warning' as const,
    timeAgo: '6h ago',
    status: 'investigating' as const,
  },
  {
    id: 'F-2024-0125',
    title: 'Bilge Pump Cycle Alert',
    equipment: 'Bilge System',
    severity: 'low' as const,
    timeAgo: '1d ago',
    status: 'resolved' as const,
  },
];

const STATS = {
  active: 2,
  resolved24h: 3,
  avgResolution: '4.2h',
};

// ============================================================================
// COMPONENT
// ============================================================================

interface FaultActivityModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export default function FaultActivityModule({
  isExpanded,
  onToggle,
  className,
}: FaultActivityModuleProps) {
  const hasActiveCritical = MOCK_FAULTS.some(f => f.status === 'open' && f.severity === 'critical');
  const overallStatus = hasActiveCritical ? 'critical' : STATS.active > 0 ? 'warning' : 'healthy';

  return (
    <ModuleContainer
      title="Fault Activity"
      icon={<AlertTriangle className="h-4.5 w-4.5 text-red-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={hasActiveCritical ? 'Critical fault active' : `${STATS.active} active faults`}
      badge={STATS.active}
      collapsedContent={
        <div className="flex items-center gap-2">
          <span className={cn(
            'px-2 py-0.5 rounded-full',
            'text-[11px] font-medium',
            hasActiveCritical ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                               'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400'
          )}>
            {STATS.active} active
          </span>
          <span className="text-[11px] text-zinc-400">·</span>
          <span className="text-[11px] text-zinc-500">{STATS.resolved24h} resolved today</span>
        </div>
      }
      className={className}
    >
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatCard
          label="Active"
          value={STATS.active}
          status={STATS.active > 0 ? 'warning' : 'healthy'}
        />
        <StatCard
          label="Resolved 24h"
          value={STATS.resolved24h}
          status="healthy"
        />
        <StatCard
          label="Avg Resolution"
          value={STATS.avgResolution}
          status="neutral"
        />
      </div>

      {/* Fault list */}
      <div className="space-y-1">
        {MOCK_FAULTS.map((fault) => {
          const severityIcon = fault.severity === 'critical' ? AlertCircle :
                              fault.severity === 'warning' ? AlertTriangle : Clock;
          const SeverityIcon = severityIcon;
          const itemStatus = fault.severity === 'critical' ? 'critical' :
                            fault.severity === 'warning' ? 'warning' : 'neutral';

          return (
            <ModuleItem
              key={fault.id}
              icon={<SeverityIcon className={cn(
                'h-4 w-4',
                fault.severity === 'critical' && 'text-red-500',
                fault.severity === 'warning' && 'text-amber-500',
                fault.severity === 'low' && 'text-zinc-400'
              )} />}
              title={fault.title}
              subtitle={`${fault.id} · ${fault.equipment}`}
              status={fault.status === 'resolved' ? 'healthy' : itemStatus}
              value={fault.timeAgo}
              onClick={() => console.log('Open fault:', fault.id)}
              actions={
                fault.status !== 'resolved' && (
                  <MicroactionButton
                    action="diagnose_fault"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      console.log('Diagnose:', fault.id);
                    }}
                  />
                )
              }
            />
          );
        })}
      </div>

      {/* Module actions */}
      <div className="flex items-center gap-2 mt-4">
        <MicroactionButton
          action="report_fault"
          size="md"
          showLabel
          onClick={() => console.log('Report fault')}
        />
        <button className={cn(
          'px-3 py-1.5 rounded-lg',
          'text-[12px] font-medium',
          'text-blue-500 hover:text-blue-600',
          'hover:bg-blue-50 dark:hover:bg-blue-900/20',
          'transition-colors'
        )}>
          View all →
        </button>
      </div>
    </ModuleContainer>
  );
}
