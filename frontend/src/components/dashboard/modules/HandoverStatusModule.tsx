'use client';

/**
 * HandoverStatusModule
 * Current handover draft and status
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { Users, FileText, CheckCircle, Clock, Edit, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, ProgressBar } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';
import { useHandoverData, HandoverStatus } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface HandoverStatusModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  handover?: HandoverStatus | null;
}

// ============================================================================
// DEFAULT DATA
// ============================================================================

const DEFAULT_HANDOVER: HandoverStatus = {
  status: 'draft',
  lastUpdated: 'Unknown',
  sections: [],
  nextHandover: 'Not scheduled',
  assignedTo: 'Unassigned',
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function HandoverStatusModule({
  isExpanded,
  onToggle,
  className,
  handover: propHandover,
}: HandoverStatusModuleProps) {
  // Use hook data unless props are provided
  const hookData = useHandoverData();

  const handover = propHandover ?? hookData.handover ?? DEFAULT_HANDOVER;
  const isLoading = !propHandover && hookData.isLoading;

  const completeSections = handover.sections.filter(s => s.complete).length;
  const totalSections = handover.sections.length;
  const progress = totalSections > 0 ? Math.round((completeSections / totalSections) * 100) : 0;
  const isComplete = progress === 100;

  return (
    <ModuleContainer
      title="Handover Status"
      icon={<Users className="h-4.5 w-4.5 text-amber-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={isComplete ? 'healthy' : 'warning'}
      statusLabel={isComplete ? 'Ready for handover' : `${progress}% complete`}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={progress} status={isComplete ? 'healthy' : 'warning'} />
          <span className="text-[11px] text-zinc-500">{completeSections}/{totalSections} sections</span>
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
          {/* Header info */}
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-200/60 dark:border-zinc-700/60">
            <div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Next Handover</p>
              <p className="text-[13px] font-medium text-zinc-700 dark:text-zinc-200">
                {handover.nextHandover}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Assignment</p>
              <p className="text-[13px] font-medium text-zinc-700 dark:text-zinc-200">
                {handover.assignedTo}
              </p>
            </div>
          </div>

          {/* Section checklist */}
          <div className="space-y-1">
            {handover.sections.map((section, index) => (
              <ModuleItem
                key={index}
                icon={
                  section.complete ? (
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <Clock className="h-4 w-4 text-amber-500" />
                  )
                }
                title={section.name}
                subtitle={`${section.items} items`}
                status={section.complete ? 'healthy' : 'warning'}
                onClick={() => console.log('Edit section:', section.name)}
                actions={
                  <MicroactionButton
                    action="edit_handover_section"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      console.log('Edit:', section.name);
                    }}
                  />
                }
              />
            ))}
          </div>

          {/* Overall progress */}
          <div className="mt-4 p-3 rounded-xl bg-zinc-100 dark:bg-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[12px] font-medium text-zinc-700 dark:text-zinc-300">
                Overall Progress
              </span>
              <span className={cn(
                'text-[12px] font-semibold',
                isComplete ? 'text-emerald-600' : 'text-amber-600'
              )}>
                {progress}%
              </span>
            </div>
            <ProgressBar value={progress} status={isComplete ? 'healthy' : 'warning'} size="md" />
          </div>

          {/* Last updated */}
          <p className="mt-3 text-[11px] text-zinc-400 text-center">
            Last updated {handover.lastUpdated}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4">
            <MicroactionButton
              action="add_to_handover"
              size="md"
              showLabel
              onClick={() => console.log('Add to handover')}
            />
            <MicroactionButton
              action="regenerate_handover_summary"
              size="md"
              showLabel
              onClick={() => console.log('Regenerate')}
            />
            <MicroactionButton
              action="export_handover"
              size="md"
              showLabel
              onClick={() => console.log('Export')}
            />
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
