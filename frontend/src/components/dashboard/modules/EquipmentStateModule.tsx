'use client';

/**
 * EquipmentStateModule
 * Equipment operational status for Control Center
 */

import React from 'react';
import { Cog, CheckCircle, AlertCircle, XCircle, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, ProgressBar } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const EQUIPMENT_SYSTEMS = [
  { id: 'gen', name: 'Generators', operational: 2, total: 2, status: 'healthy' as const },
  { id: 'hvac', name: 'HVAC System', operational: 4, total: 5, status: 'warning' as const },
  { id: 'nav', name: 'Navigation', operational: 8, total: 8, status: 'healthy' as const },
  { id: 'stab', name: 'Stabilisers', operational: 2, total: 2, status: 'healthy' as const },
  { id: 'water', name: 'Water Makers', operational: 1, total: 2, status: 'critical' as const },
];

const STATS = {
  totalEquipment: 156,
  operational: 148,
  maintenance: 6,
  offline: 2,
};

// ============================================================================
// COMPONENT
// ============================================================================

interface EquipmentStateModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export default function EquipmentStateModule({
  isExpanded,
  onToggle,
  className,
}: EquipmentStateModuleProps) {
  const hasIssues = STATS.offline > 0 || STATS.maintenance > 0;
  const overallStatus = STATS.offline > 0 ? 'critical' : STATS.maintenance > 0 ? 'warning' : 'healthy';
  const operationalPercent = Math.round((STATS.operational / STATS.totalEquipment) * 100);

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
          <span className="text-[11px] text-zinc-500">{STATS.operational}/{STATS.totalEquipment}</span>
        </div>
      }
      className={className}
    >
      {/* Status summary */}
      <div className="flex items-center gap-4 mb-4 pb-3 border-b border-zinc-200/60 dark:border-zinc-700/60">
        <div className="flex items-center gap-1.5">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
          <span className="text-[12px] text-zinc-600 dark:text-zinc-300">
            <strong>{STATS.operational}</strong> operational
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Pause className="h-3.5 w-3.5 text-amber-500" />
          <span className="text-[12px] text-zinc-600 dark:text-zinc-300">
            <strong>{STATS.maintenance}</strong> maintenance
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle className="h-3.5 w-3.5 text-red-500" />
          <span className="text-[12px] text-zinc-600 dark:text-zinc-300">
            <strong>{STATS.offline}</strong> offline
          </span>
        </div>
      </div>

      {/* Systems list */}
      <div className="space-y-1">
        {EQUIPMENT_SYSTEMS.map((system) => {
          const percent = Math.round((system.operational / system.total) * 100);

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
                <MicroactionButton
                  action="view_equipment_details"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    console.log('View details:', system.id);
                  }}
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
          'text-[12px] font-medium',
          'text-blue-500 hover:text-blue-600',
          'hover:bg-blue-50 dark:hover:bg-blue-900/20',
          'transition-colors'
        )}>
          View all equipment →
        </button>
      </div>
    </ModuleContainer>
  );
}
