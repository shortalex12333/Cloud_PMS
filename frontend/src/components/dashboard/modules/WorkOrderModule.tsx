'use client';

/**
 * WorkOrderModule
 * Work order health overview for Control Center
 */

import React from 'react';
import { Wrench, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard, ProgressBar } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const MOCK_WORK_ORDERS = [
  {
    id: 'WO-2024-0847',
    title: 'Generator Coolant Flush',
    equipment: 'Main Generator #1',
    dueDate: '3 days',
    priority: 'routine' as const,
    status: 'scheduled' as const,
  },
  {
    id: 'WO-2024-0852',
    title: 'Stabiliser Hydraulic Check',
    equipment: 'Port Stabiliser',
    dueDate: 'Today',
    priority: 'important' as const,
    status: 'in_progress' as const,
  },
  {
    id: 'WO-2024-0849',
    title: 'AC Filter Replacement',
    equipment: 'HVAC System',
    dueDate: 'Overdue 2d',
    priority: 'critical' as const,
    status: 'overdue' as const,
  },
];

const STATS = {
  total: 24,
  completed: 18,
  inProgress: 4,
  overdue: 2,
};

// ============================================================================
// TYPES
// ============================================================================

interface WorkOrderModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function WorkOrderModule({
  isExpanded,
  onToggle,
  className,
}: WorkOrderModuleProps) {
  const overallStatus = STATS.overdue > 0 ? 'critical' : STATS.inProgress > 0 ? 'warning' : 'healthy';
  const completionRate = Math.round((STATS.completed / STATS.total) * 100);

  return (
    <ModuleContainer
      title="Work Orders"
      icon={<Wrench className="h-4.5 w-4.5 text-blue-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={STATS.overdue > 0 ? `${STATS.overdue} overdue` : `${STATS.inProgress} in progress`}
      badge={STATS.total}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={completionRate} status="healthy" />
          <span className="text-[11px] text-zinc-500">{completionRate}% complete</span>
        </div>
      }
      className={className}
    >
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatCard label="Completed" value={STATS.completed} status="healthy" />
        <StatCard label="In Progress" value={STATS.inProgress} status="warning" />
        <StatCard label="Overdue" value={STATS.overdue} status={STATS.overdue > 0 ? 'critical' : 'neutral'} />
      </div>

      {/* Work order list */}
      <div className="space-y-1">
        {MOCK_WORK_ORDERS.map((wo) => {
          const statusIcon = wo.status === 'overdue' ? AlertCircle :
                            wo.status === 'in_progress' ? Clock : CheckCircle;
          const StatusIcon = statusIcon;
          const itemStatus = wo.status === 'overdue' ? 'critical' :
                            wo.status === 'in_progress' ? 'warning' : 'neutral';

          return (
            <ModuleItem
              key={wo.id}
              icon={<StatusIcon className={cn(
                'h-4 w-4',
                wo.status === 'overdue' && 'text-red-500',
                wo.status === 'in_progress' && 'text-amber-500',
                wo.status === 'scheduled' && 'text-zinc-400'
              )} />}
              title={wo.title}
              subtitle={`${wo.id} · ${wo.equipment}`}
              status={itemStatus}
              value={wo.dueDate}
              onClick={() => console.log('Open WO:', wo.id)}
              actions={
                <MicroactionButton
                  action="complete_work_order"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    console.log('Complete:', wo.id);
                  }}
                />
              }
            />
          );
        })}
      </div>

      {/* Module actions */}
      <div className="flex items-center gap-2 mt-4">
        <MicroactionButton
          action="create_work_order"
          size="md"
          showLabel
          onClick={() => console.log('Create work order')}
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
