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
import { ActionButton } from '@/components/actions/ActionButton';
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
      statusLabel={isComplete ? 'Ready for handover' : `${progress}% done`}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={progress} status={isComplete ? 'healthy' : 'warning'} />
          <span className="typo-meta text-zinc-500">{completeSections}/{totalSections} sections</span>
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
              <p className="typo-meta text-zinc-500 dark:text-zinc-400">Next Handover</p>
              <p className="typo-meta font-medium text-zinc-700 dark:text-zinc-200">
                {handover.nextHandover}
              </p>
            </div>
            <div className="text-right">
              <p className="typo-meta text-zinc-500 dark:text-zinc-400">Assignment</p>
              <p className="typo-meta font-medium text-zinc-700 dark:text-zinc-200">
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
                  <ActionButton
                    action="edit_handover_section"
                    context={{ section_name: section.name }}
                    size="sm"
                    iconOnly
                    onSuccess={() => hookData.refresh?.()}
                  />
                }
              />
            ))}
          </div>

          {/* Overall progress */}
          <div className="mt-4 p-3 rounded-[10px] bg-zinc-100 dark:bg-zinc-800">
            <div className="flex items-center justify-between mb-2">
              <span className="typo-meta font-medium text-zinc-700 dark:text-zinc-300">
                Overall Progress
              </span>
              <span className={cn(
                'typo-meta font-semibold',
                isComplete ? 'text-emerald-600' : 'text-amber-600'
              )}>
                {progress}%
              </span>
            </div>
            <ProgressBar value={progress} status={isComplete ? 'healthy' : 'warning'} size="md" />
          </div>

          {/* Last updated */}
          <p className="mt-3 typo-meta text-zinc-400 text-center">
            Last updated {handover.lastUpdated}
          </p>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="add_to_handover"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <ActionButton
              action="regenerate_handover_summary"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <ActionButton
              action="export_handover"
              size="sm"
            />
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
