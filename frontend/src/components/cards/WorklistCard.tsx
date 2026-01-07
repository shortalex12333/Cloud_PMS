/**
 * WorklistCard Component
 *
 * Displays shipyard worklist/snag list with task status
 */

'use client';

import { ListTodo, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface WorklistCardProps {
  worklist: {
    project_name: string;
    location: string;
    tasks: {
      id: string;
      title: string;
      category: 'electrical' | 'mechanical' | 'structural' | 'paintwork' | 'other';
      priority: 'low' | 'medium' | 'high' | 'urgent';
      status: 'pending' | 'in_progress' | 'completed' | 'blocked';
      progress?: number;
    }[];
    summary: {
      total_tasks: number;
      completed_tasks: number;
      pending_tasks: number;
      blocked_tasks: number;
    };
  };
  actions?: MicroAction[];
}

export function WorklistCard({ worklist, actions = [] }: WorklistCardProps) {
  const completionRate =
    worklist.summary.total_tasks > 0
      ? (worklist.summary.completed_tasks / worklist.summary.total_tasks) * 100
      : 0;

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-600" />;
      case 'blocked':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <ListTodo className="h-4 w-4 text-gray-600" />;
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Worklist Icon */}
        <div className="mt-1 text-primary">
          <ListTodo className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Project Name & Location */}
          <div className="mb-2">
            <h3 className="font-medium text-foreground">{worklist.project_name}</h3>
            <p className="text-sm text-muted-foreground">{worklist.location}</p>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-xs text-muted-foreground">Completion Rate</p>
              <p className="text-lg font-bold text-foreground">
                {completionRate.toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Tasks</p>
              <p className="text-sm">
                <span className="font-medium text-green-600">
                  {worklist.summary.completed_tasks}
                </span>
                {' / '}
                <span className="text-muted-foreground">
                  {worklist.summary.total_tasks}
                </span>
              </p>
            </div>
          </div>

          {/* Blocked Tasks Warning */}
          {worklist.summary.blocked_tasks > 0 && (
            <div className="flex items-center gap-1.5 text-sm text-red-600 mb-3 bg-red-50 border border-red-200 rounded p-2">
              <AlertCircle className="h-4 w-4" />
              <span>{worklist.summary.blocked_tasks} blocked task(s)</span>
            </div>
          )}

          {/* Task List Preview */}
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-foreground uppercase mb-2">
              Tasks
            </p>
            <ul className="space-y-2">
              {worklist.tasks.slice(0, 5).map((task) => (
                <li
                  key={task.id}
                  className="flex items-start justify-between gap-2 text-sm"
                >
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    {getStatusIcon(task.status)}
                    <span className="truncate">{task.title}</span>
                  </div>
                  <span
                    className={cn(
                      'text-xs px-1.5 py-0.5 rounded border flex-shrink-0',
                      getPriorityColor(task.priority)
                    )}
                  >
                    {task.priority}
                  </span>
                </li>
              ))}
              {worklist.tasks.length > 5 && (
                <li className="text-xs text-muted-foreground">
                  +{worklist.tasks.length - 5} more tasks
                </li>
              )}
            </ul>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ project_name: worklist.project_name }}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
