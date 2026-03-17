'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { CheckCircle2, Circle, ListChecks } from 'lucide-react';

interface ChecklistItem {
  id: string;
  description: string;
  is_completed: boolean;
  completed_at?: string;
  completed_by?: string;
  notes?: string;
  sequence: number;
}

interface ChecklistProgress {
  completed: number;
  total: number;
  percent: number;
}

/**
 * ActionResult-compatible response shape.
 * The execute() helper in useWorkOrderActions spreads the JSON response,
 * so checklist/progress may appear as top-level keys or nested under `data`.
 */
interface ChecklistResponse {
  success: boolean;
  checklist?: ChecklistItem[];
  progress?: ChecklistProgress;
  data?: {
    checklist?: ChecklistItem[];
    progress?: ChecklistProgress;
  };
}

export interface ChecklistSectionProps {
  workOrderId: string;
  viewChecklist: () => Promise<ChecklistResponse>;
  markComplete?: (itemId: string) => Promise<unknown>;
  stickyTop?: number;
}

export function ChecklistSection({
  workOrderId,
  viewChecklist,
  markComplete,
  stickyTop = 56,
}: ChecklistSectionProps) {
  const [items, setItems] = React.useState<ChecklistItem[]>([]);
  const [progress, setProgress] = React.useState<ChecklistProgress>({ completed: 0, total: 0, percent: 0 });
  const [isOpen, setIsOpen] = React.useState(true);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    viewChecklist().then((result) => {
      if (cancelled) return;
      if (result.success) {
        // Handle both flat and nested response shapes
        const checklist = result.checklist ?? result.data?.checklist;
        const prog = result.progress ?? result.data?.progress;
        if (checklist) setItems(checklist);
        if (prog) setProgress(prog);
      }
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [viewChecklist, workOrderId]);

  if (loading) return null;
  if (items.length === 0) return null;

  return (
    <section>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full text-left group"
        style={{ position: 'sticky', top: stickyTop, zIndex: 1, background: 'var(--surface-primary)' }}
      >
        <ListChecks className="w-4 h-4 text-txt-tertiary" />
        <span className="text-overline text-txt-tertiary uppercase tracking-wider">
          Checklist
        </span>
        <span className="text-caption text-txt-tertiary ml-auto">
          {progress.completed}/{progress.total} ({progress.percent}%)
        </span>
        <span className="text-txt-tertiary text-caption">{isOpen ? '−' : '+'}</span>
      </button>

      {/* Progress bar */}
      <div className="mt-2 h-1 w-full rounded-full bg-surface-border overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-interactive transition-all duration-300"
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      {isOpen && (
        <div className="mt-3 space-y-1">
          {items.map((item) => (
            <div
              key={item.id}
              className={cn(
                'flex items-start gap-2 py-2 px-2 rounded-md min-h-[44px]',
                item.is_completed && 'opacity-60'
              )}
            >
              <button
                onClick={() => !item.is_completed && markComplete?.(item.id)}
                disabled={item.is_completed}
                className="mt-0.5 flex-shrink-0"
                aria-label={item.is_completed ? 'Completed' : 'Mark complete'}
              >
                {item.is_completed ? (
                  <CheckCircle2 className="w-4 h-4 text-status-success" />
                ) : (
                  <Circle className="w-4 h-4 text-txt-tertiary hover:text-brand-interactive" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <p className={cn(
                  'text-body leading-snug',
                  item.is_completed && 'line-through text-txt-tertiary'
                )}>
                  {item.description}
                </p>
                {item.notes && (
                  <p className="text-caption text-txt-tertiary mt-0.5">{item.notes}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
