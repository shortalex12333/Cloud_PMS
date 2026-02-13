'use client';

/**
 * EquipmentStateModule
 * Equipment operational status for Control Center
 * Connected to real dashboard data via useDashboardData hook
 */

import React, { useMemo } from 'react';
import { Cog, CheckCircle, AlertCircle, XCircle, Pause, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, ProgressBar } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { useEquipmentData, EquipmentStatus, EquipmentStats } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface SystemGroup {
  id: string;
  name: string;
  operational: number;
  total: number;
  status: 'healthy' | 'warning' | 'critical';
}

interface EquipmentStateModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  equipment?: EquipmentStatus[];
  stats?: EquipmentStats;
}

// ============================================================================
// HELPERS
// ============================================================================

function groupEquipmentBySystems(equipment: EquipmentStatus[]): SystemGroup[] {
  // Group equipment by system
  const systemMap = new Map<string, { operational: number; total: number }>();

  for (const item of equipment) {
    const system = item.system || 'Other';
    const existing = systemMap.get(system) || { operational: 0, total: 0 };
    existing.total++;
    if (item.status === 'operational') {
      existing.operational++;
    }
    systemMap.set(system, existing);
  }

  return Array.from(systemMap.entries()).map(([name, data]) => {
    const percent = data.total > 0 ? Math.round((data.operational / data.total) * 100) : 0;
    const status: 'healthy' | 'warning' | 'critical' =
      percent === 100 ? 'healthy' : percent >= 50 ? 'warning' : 'critical';

    return {
      id: name.toLowerCase().replace(/\s+/g, '-'),
      name,
      operational: data.operational,
      total: data.total,
      status,
    };
  });
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function EquipmentStateModule({
  isExpanded,
  onToggle,
  className,
  equipment: propEquipment,
  stats: propStats,
}: EquipmentStateModuleProps) {
  // Use hook data unless props are provided
  const hookData = useEquipmentData();

  const equipment = propEquipment ?? hookData.equipment;
  const stats = propStats ?? hookData.stats;
  const isLoading = !propEquipment && hookData.isLoading;

  // Group equipment by system for display
  const systems = useMemo(() => groupEquipmentBySystems(equipment), [equipment]);

  const hasIssues = stats.offline > 0 || stats.maintenance > 0;
  const overallStatus = stats.offline > 0 ? 'critical' : stats.maintenance > 0 ? 'warning' : 'healthy';
  const operationalPercent = stats.total > 0 ? Math.round((stats.operational / stats.total) * 100) : 0;

  return (
    <ModuleContainer
      title="Equipment Status"
      icon={<Cog className="h-4.5 w-4.5 text-violet-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={`${operationalPercent}% operational`}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={operationalPercent} status={overallStatus} />
          <span className="text-celeste-xs text-zinc-500">{stats.operational}/{stats.total}</span>
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
          {/* Status summary */}
          <div className="flex items-center gap-4 mb-4 pb-3 border-b border-zinc-200/60 dark:border-zinc-700/60">
            <div className="flex items-center gap-1.5">
              <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-celeste-xs text-zinc-600 dark:text-zinc-300">
                <strong>{stats.operational}</strong> operational
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Pause className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-celeste-xs text-zinc-600 dark:text-zinc-300">
                <strong>{stats.maintenance}</strong> maintenance
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <XCircle className="h-3.5 w-3.5 text-red-500" />
              <span className="text-celeste-xs text-zinc-600 dark:text-zinc-300">
                <strong>{stats.offline}</strong> offline
              </span>
            </div>
          </div>

          {/* Systems list */}
          <div className="space-y-1">
            {systems.map((system) => {
              const percent = system.total > 0 ? Math.round((system.operational / system.total) * 100) : 0;

              return (
                <ModuleItem
                  key={system.id}
                  icon={
                    percent === 100 ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : percent >= 50 ? (
                      <AlertCircle className="h-4 w-4 text-amber-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )
                  }
                  title={system.name}
                  subtitle={`${system.operational}/${system.total} units operational`}
                  status={system.status}
                  onClick={() => console.log('View system:', system.id)}
                  actions={
                    <ActionButton
                      action="view_equipment_details"
                      context={{ equipment_id: system.id }}
                      size="sm"
                      iconOnly
                    />
                  }
                />
              );
            })}
          </div>

          {/* Module actions */}
          <div className="flex items-center gap-2 mt-4">
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'text-celeste-xs font-medium',
              'text-celeste-accent hover:text-celeste-accent-hover',
              'hover:bg-celeste-accent-subtle dark:hover:bg-celeste-accent-subtle',
              'transition-colors'
            )}>
              View all equipment →
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
