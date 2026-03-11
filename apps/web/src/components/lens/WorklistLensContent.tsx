'use client';

/**
 * WorklistLensContent - Inner content for Worklist lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 *
 * Created 2026-03-02 to close GAP-007 (Worklist lens missing component).
 *
 * @see FAILED_BUTTONS_REPORT_2026-03-02.md
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { toast } from 'sonner';
import { useWorklistActions, useWorklistPermissions } from '@/hooks/useWorklistActions';

export interface WorklistLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

interface WorklistTask {
  id: string;
  task_description: string;
  description?: string;
  priority?: 'low' | 'normal' | 'high' | 'critical';
  status: string;
  due_date?: string;
  assigned_to?: string;
  created_at?: string;
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'overdue':
    case 'blocked':
      return 'critical';
    case 'in_progress':
    case 'pending':
      return 'warning';
    case 'completed':
    case 'done':
      return 'success';
    default:
      return 'neutral';
  }
}

function mapPriorityToColor(priority?: string): string {
  switch (priority) {
    case 'critical':
      return 'text-status-critical';
    case 'high':
      return 'text-status-warning';
    case 'low':
      return 'text-celeste-text-disabled';
    default:
      return 'text-celeste-text-muted';
  }
}

export function WorklistLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: WorklistLensContentProps) {
  // Hook for worklist actions and permissions
  const { addTask, exportWorklist, isLoading } = useWorklistActions(id);
  const { canAddTask, canExport } = useWorklistPermissions();

  // Track action in progress
  const [actionInProgress, setActionInProgress] = React.useState<string | null>(null);

  // Modal state for add task
  const [showAddTaskForm, setShowAddTaskForm] = React.useState(false);
  const [newTaskTitle, setNewTaskTitle] = React.useState('');
  const [newTaskPriority, setNewTaskPriority] = React.useState<string>('normal');

  // Map data
  const title = (data.title as string) || (data.name as string) || 'Worklist';
  const status = (data.status as string) || 'active';
  const owner_name = data.owner_name as string | undefined;
  const created_at = data.created_at as string | undefined;
  const updated_at = data.updated_at as string | undefined;

  // Tasks from child table
  const tasks = (data.tasks as WorklistTask[]) || [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // Calculate task counts
  const pendingTasks = tasks.filter(t => t.status === 'pending' || t.status === 'in_progress').length;
  const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'done').length;

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Tasks', value: `${tasks.length} total` },
    { label: 'Pending', value: `${pendingTasks}`, color: pendingTasks > 0 ? 'warning' : 'neutral' },
    { label: 'Completed', value: `${completedTasks}`, color: completedTasks > 0 ? 'success' : 'neutral' },
    { label: 'Owner', value: owner_name ?? 'Unassigned' },
  ];

  // Action handlers
  const handleAddTask = async () => {
    if (!newTaskTitle.trim()) {
      toast.error('Task title is required');
      return;
    }

    setActionInProgress('add');
    const result = await addTask({
      title: newTaskTitle.trim(),
      priority: newTaskPriority,
    });

    if (result.success) {
      toast.success('Task added to worklist');
      setNewTaskTitle('');
      setShowAddTaskForm(false);
      onRefresh?.();
    } else {
      toast.error(result.error || 'Failed to add task');
    }
    setActionInProgress(null);
  };

  const handleExport = async (format: 'pdf' | 'csv') => {
    setActionInProgress('export');
    const result = await exportWorklist(format);

    if (result.success) {
      toast.success(`Worklist exported as ${format.toUpperCase()}`);
      // If result contains a download URL, open it
      if (result.data?.url) {
        window.open(result.data.url as string, '_blank');
      }
    } else {
      toast.error(result.error || 'Failed to export worklist');
    }
    setActionInProgress(null);
  };

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Worklist" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            subtitle={owner_name ? `Managed by ${owner_name}` : undefined}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Action Buttons */}
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          {canAddTask && (
            <PrimaryButton
              onClick={() => setShowAddTaskForm(true)}
              disabled={isLoading || actionInProgress !== null}
              className="text-[13px] min-h-9 px-4 py-2"
              data-testid="add-task-btn"
            >
              Add Task
            </PrimaryButton>
          )}
          {canExport && (
            <>
              <GhostButton
                onClick={() => handleExport('pdf')}
                disabled={isLoading || actionInProgress === 'export'}
                className="text-[13px] min-h-9 px-4 py-2"
                data-testid="export-pdf-btn"
              >
                {actionInProgress === 'export' ? 'Exporting...' : 'Export PDF'}
              </GhostButton>
              <GhostButton
                onClick={() => handleExport('csv')}
                disabled={isLoading || actionInProgress === 'export'}
                className="text-[13px] min-h-9 px-4 py-2"
                data-testid="export-csv-btn"
              >
                Export CSV
              </GhostButton>
            </>
          )}
        </div>

        {/* Add Task Form (inline) */}
        {showAddTaskForm && (
          <div className="mt-4 p-4 bg-surface-secondary rounded-lg border border-surface-border">
            <h3 className="typo-label text-celeste-text-primary mb-3">New Task</h3>
            <div className="space-y-3">
              <div>
                <label className="typo-meta text-celeste-text-muted block mb-1">Title</label>
                <input
                  type="text"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  placeholder="Task description..."
                  className="w-full px-3 py-2 bg-surface-base border border-surface-border rounded-lg text-celeste-text-primary placeholder:text-celeste-text-disabled focus:outline-none focus:ring-2 focus:ring-accent-blue"
                  data-testid="new-task-title-input"
                />
              </div>
              <div>
                <label className="typo-meta text-celeste-text-muted block mb-1">Priority</label>
                <select
                  value={newTaskPriority}
                  onChange={(e) => setNewTaskPriority(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-base border border-surface-border rounded-lg text-celeste-text-primary focus:outline-none focus:ring-2 focus:ring-accent-blue"
                  data-testid="new-task-priority-select"
                >
                  <option value="low">Low</option>
                  <option value="normal">Normal</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="flex gap-2">
                <PrimaryButton
                  onClick={handleAddTask}
                  disabled={isLoading || actionInProgress === 'add'}
                  className="text-[13px] min-h-9 px-4 py-2"
                  data-testid="submit-task-btn"
                >
                  {actionInProgress === 'add' ? 'Adding...' : 'Add Task'}
                </PrimaryButton>
                <GhostButton
                  onClick={() => {
                    setShowAddTaskForm(false);
                    setNewTaskTitle('');
                  }}
                  className="text-[13px] min-h-9 px-4 py-2"
                >
                  Cancel
                </GhostButton>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Tasks List */}
        <div className="mt-6">
          <SectionContainer title={`Tasks (${tasks.length})`} stickyTop={56}>
            {tasks.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No tasks in this worklist.</p>
            ) : (
              <ul className="space-y-3">
                {tasks.map((task, index) => {
                  const taskStatusColor = mapStatusToColor(task.status);
                  const priorityColor = mapPriorityToColor(task.priority);

                  return (
                    <li
                      key={task.id || index}
                      className="flex justify-between items-start p-3 bg-surface-secondary rounded-lg"
                    >
                      <div className="flex-1">
                        <span className="typo-body text-celeste-text-primary">
                          {task.task_description}
                        </span>
                        {task.description && (
                          <p className="typo-meta text-celeste-text-muted mt-1">{task.description}</p>
                        )}
                        {task.due_date && (
                          <p className="typo-meta text-celeste-text-muted mt-1">
                            Due: {new Date(task.due_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 ml-4">
                        {task.priority && task.priority !== 'normal' && (
                          <span className={cn('typo-meta uppercase', priorityColor)}>
                            {task.priority}
                          </span>
                        )}
                        <span
                          className={cn(
                            'typo-meta uppercase px-2 py-0.5 rounded',
                            taskStatusColor === 'success' && 'bg-status-success/20 text-status-success',
                            taskStatusColor === 'warning' && 'bg-status-warning/20 text-status-warning',
                            taskStatusColor === 'critical' && 'bg-status-critical/20 text-status-critical',
                            taskStatusColor === 'neutral' && 'bg-surface-tertiary text-celeste-text-muted'
                          )}
                        >
                          {task.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionContainer>
        </div>

        {/* Metadata */}
        {(created_at || updated_at) && (
          <div className="mt-6">
            <SectionContainer title="Details" stickyTop={56}>
              <dl className="grid grid-cols-2 gap-4 typo-body">
                {created_at && (
                  <>
                    <dt className="text-celeste-text-muted">Created</dt>
                    <dd className="text-celeste-text-primary">{formatRelativeTime(created_at)}</dd>
                  </>
                )}
                {updated_at && (
                  <>
                    <dt className="text-celeste-text-muted">Last Updated</dt>
                    <dd className="text-celeste-text-primary">{formatRelativeTime(updated_at)}</dd>
                  </>
                )}
              </dl>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}
