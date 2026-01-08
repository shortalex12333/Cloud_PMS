/**
 * ChecklistCard Component
 *
 * Displays operational checklist with completion status
 */

'use client';

import { CheckSquare, Square, Clock, CheckCircle2 } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface ChecklistCardProps {
  checklist: {
    id: string;
    title: string;
    checklist_type: 'daily' | 'weekly' | 'monthly' | 'pre-departure' | 'arrival' | 'other';
    due_date?: string;
    completed_at?: string;
    items: {
      id: string;
      description: string;
      is_completed: boolean;
      completed_by?: string;
      notes?: string;
    }[];
  };
  actions?: MicroAction[];
}

export function ChecklistCard({ checklist, actions = [] }: ChecklistCardProps) {
  const completedCount = checklist.items.filter((item) => item.is_completed).length;
  const totalCount = checklist.items.length;
  const completionPercentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const isFullyCompleted = completedCount === totalCount;

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Checklist Icon */}
        <div className={cn('mt-1', isFullyCompleted ? 'text-green-600' : 'text-blue-600')}>
          {isFullyCompleted ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : (
            <CheckSquare className="h-5 w-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Type */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{checklist.title}</h3>
            <span className="text-xs px-2 py-0.5 rounded-full border border-muted bg-muted text-muted-foreground uppercase">
              {checklist.checklist_type}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground">
                {completedCount} of {totalCount} completed
              </span>
              <span className="font-medium">{completionPercentage.toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all',
                  isFullyCompleted ? 'bg-green-600' : 'bg-blue-600'
                )}
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
          </div>

          {/* Dates */}
          {checklist.due_date && !checklist.completed_at && (
            <div className="flex items-center gap-1.5 text-sm text-orange-600 mb-2">
              <Clock className="h-4 w-4" />
              <span>Due: {formatDate(checklist.due_date)}</span>
            </div>
          )}
          {checklist.completed_at && (
            <p className="text-sm text-green-600 mb-2">
              ✓ Completed: {formatDate(checklist.completed_at)}
            </p>
          )}

          {/* Items Preview */}
          <div className="mb-3">
            <ul className="space-y-1.5">
              {checklist.items.slice(0, 5).map((item) => (
                <li
                  key={item.id}
                  className="flex items-start gap-2 text-sm"
                >
                  {item.is_completed ? (
                    <CheckSquare className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  ) : (
                    <Square className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  )}
                  <span
                    className={cn(
                      item.is_completed && 'line-through text-muted-foreground'
                    )}
                  >
                    {item.description}
                  </span>
                </li>
              ))}
              {checklist.items.length > 5 && (
                <li className="text-xs text-muted-foreground pl-6">
                  +{checklist.items.length - 5} more items
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
                context={{ checklist_id: checklist.id }}
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
