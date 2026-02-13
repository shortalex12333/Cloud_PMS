'use client';

/**
 * WorkOrderModule
 * Work order health overview for Control Center
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { Wrench, Clock, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard, ProgressBar } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { useWorkOrderData, WorkOrderSummary, WorkOrderStats } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface WorkOrderModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  // Optional: allow passing data directly for testing
  workOrders?: WorkOrderSummary[];
  stats?: WorkOrderStats;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function WorkOrderModule({
  isExpanded,
  onToggle,
  className,
  workOrders: propWorkOrders,
  stats: propStats,
}: WorkOrderModuleProps) {
  // Use hook data unless props are provided
  const hookData = useWorkOrderData();

  const workOrders = propWorkOrders ?? hookData.workOrders;
  const stats = propStats ?? hookData.stats;
  const isLoading = !propWorkOrders && hookData.isLoading;

  const overallStatus = stats.overdue > 0 ? 'critical' : stats.inProgress > 0 ? 'warning' : 'healthy';
  const completionRate = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <ModuleContainer
      title="Work Orders"
      icon={<Wrench className="h-4.5 w-4.5 text-celeste-text-muted" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={stats.overdue > 0 ? `${stats.overdue} overdue` : `${stats.inProgress} in progress`}
      badge={stats.total}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={completionRate} status="healthy" />
          <span className="text-celeste-xs text-zinc-500">{completionRate}% done</span>
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
            <StatCard label="Completed" value={stats.completed} status="healthy" />
            <StatCard label="In Progress" value={stats.inProgress} status="warning" />
            <StatCard label="Overdue" value={stats.overdue} status={stats.overdue > 0 ? 'critical' : 'neutral'} />
          </div>

          {/* Work order list */}
          <div className="space-y-1">
            {workOrders.map((wo) => {
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
                  // NO execution buttons in list view (per situation UX spec)
                  // Execution buttons only appear in detail/expanded view
                />
              );
            })}
          </div>

          {/* Module actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="create_work_order"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'text-celeste-xs font-medium',
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
