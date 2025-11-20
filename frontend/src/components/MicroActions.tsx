'use client';

import { useState } from 'react';
import {
  Plus,
  FileText,
  Wrench,
  Package,
  Clock,
  TrendingUp,
  StickyNote,
  Camera,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { executeAction, ActionExecutionError } from '@/lib/actionClient';
import type { MicroAction, SearchResult } from '@/types';

interface MicroActionsProps {
  actions: MicroAction[];
  result: SearchResult;
}

export default function MicroActions({ actions, result }: MicroActionsProps) {
  const [loadingAction, setLoadingAction] = useState<MicroAction | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * Extract context from result metadata
   * This builds the action context required by the Action Router
   */
  const buildActionContext = (action: MicroAction): Record<string, any> => {
    const metadata = result.metadata || {};
    const context: Record<string, any> = {};

    // Always include yacht_id if available
    if (metadata.yacht_id) {
      context.yacht_id = metadata.yacht_id;
    }

    // Add context based on result type and action
    switch (result.type) {
      case 'equipment':
        context.equipment_id = result.id;
        break;
      case 'fault':
        context.fault_id = result.id;
        if (metadata.equipment_id) {
          context.equipment_id = metadata.equipment_id;
        }
        break;
      case 'work_order':
        context.work_order_id = result.id;
        break;
      case 'part':
        context.part_id = result.id;
        break;
      case 'document_chunk':
        if (metadata.document_id) {
          context.document_id = metadata.document_id;
        }
        if (metadata.storage_path) {
          context.storage_path = metadata.storage_path;
        }
        break;
      case 'predictive':
        context.predictive_id = result.id;
        break;
    }

    // Add any additional metadata fields
    if (metadata.handover_id) {
      context.handover_id = metadata.handover_id;
    }

    return context;
  };

  /**
   * Handle action execution
   */
  const handleAction = async (action: MicroAction) => {
    setLoadingAction(action);
    setError(null);

    try {
      const context = buildActionContext(action);

      // Action-specific handling
      switch (action) {
        case 'create_work_order':
          // For now, show prompt for user input (TODO: replace with modal)
          const title = prompt('Work order title:', result.title || '');
          const priority = prompt('Priority (low/medium/high/critical):', 'medium');

          if (!title) {
            setError('Work order title is required');
            return;
          }

          await executeAction('create_work_order', context, { title, priority });
          alert('Work order created successfully!');
          break;

        case 'add_note':
          const noteText = prompt('Add note:', '');
          if (!noteText) {
            setError('Note text is required');
            return;
          }

          await executeAction('add_note', context, { note_text: noteText });
          alert('Note added successfully!');
          break;

        case 'add_to_handover':
          // Assume handover_id is in metadata or prompt for it
          if (!context.handover_id) {
            setError('No handover selected. Please select a handover first.');
            return;
          }

          await executeAction('add_to_handover', context, {});
          alert('Added to handover successfully!');
          break;

        case 'open_document':
          if (!context.storage_path) {
            setError('Document path not available');
            return;
          }

          const docResult = await executeAction('open_document', {}, {
            storage_path: context.storage_path,
          });

          if (docResult.result?.signed_url) {
            window.open(docResult.result.signed_url, '_blank');
          }
          break;

        case 'order_part':
          const quantity = prompt('Quantity to order:', '1');
          if (!quantity) {
            setError('Quantity is required');
            return;
          }

          await executeAction('order_part', context, {
            quantity: parseInt(quantity, 10),
          });
          alert('Part order submitted successfully!');
          break;

        case 'view_history':
          // TODO: Navigate to history view
          console.log('View history for:', result.id);
          alert('History view coming soon...');
          break;

        case 'show_predictive':
          // TODO: Show predictive insights modal
          console.log('Show predictive for:', result.id);
          alert('Predictive insights coming soon...');
          break;

        case 'attach_photo':
          // TODO: Open camera/file picker
          console.log('Attach photo to:', result.id);
          alert('Photo attachment coming soon...');
          break;

        case 'resolve_fault':
          // TODO: Fault resolution flow
          console.log('Resolve fault:', result.id);
          alert('Fault resolution coming soon...');
          break;

        case 'assign_task':
          // TODO: Task assignment flow
          console.log('Assign task:', result.id);
          alert('Task assignment coming soon...');
          break;

        default:
          console.warn('Unhandled action:', action);
          setError(`Action "${action}" not implemented yet`);
      }
    } catch (err) {
      console.error('Action execution failed:', err);

      if (err instanceof ActionExecutionError) {
        setError(err.message);
      } else {
        setError('Action failed. Please try again.');
      }
    } finally {
      setLoadingAction(null);
    }
  };

  const getActionConfig = (action: MicroAction) => {
    const configs = {
      create_work_order: {
        label: 'Create WO',
        icon: Wrench,
        variant: 'primary' as const,
      },
      add_to_handover: {
        label: 'Add to Handover',
        icon: Plus,
        variant: 'secondary' as const,
      },
      open_document: {
        label: 'Open',
        icon: FileText,
        variant: 'secondary' as const,
      },
      order_part: {
        label: 'Order',
        icon: Package,
        variant: 'secondary' as const,
      },
      view_history: {
        label: 'History',
        icon: Clock,
        variant: 'secondary' as const,
      },
      show_predictive: {
        label: 'Insights',
        icon: TrendingUp,
        variant: 'secondary' as const,
      },
      add_note: {
        label: 'Add Note',
        icon: StickyNote,
        variant: 'secondary' as const,
      },
      attach_photo: {
        label: 'Photo',
        icon: Camera,
        variant: 'secondary' as const,
      },
      resolve_fault: {
        label: 'Resolve',
        icon: Wrench,
        variant: 'primary' as const,
      },
      assign_task: {
        label: 'Assign',
        icon: Plus,
        variant: 'secondary' as const,
      },
    };

    return configs[action] || { label: action, icon: FileText, variant: 'secondary' as const };
  };

  return (
    <div className="space-y-2">
      {error && (
        <div className="text-xs text-destructive bg-destructive/10 px-2 py-1 rounded">
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {actions.map((action) => {
          const config = getActionConfig(action);
          const Icon = loadingAction === action ? Loader2 : config.icon;
          const isLoading = loadingAction === action;

          return (
            <button
              key={action}
              onClick={(e) => {
                e.stopPropagation();
                handleAction(action);
              }}
              disabled={loadingAction !== null}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                config.variant === 'primary'
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
                isLoading && 'opacity-75 cursor-not-allowed',
                loadingAction && loadingAction !== action && 'opacity-50'
              )}
            >
              <Icon className={cn('h-3.5 w-3.5', isLoading && 'animate-spin')} />
              {config.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
