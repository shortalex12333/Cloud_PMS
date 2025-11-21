'use client';

import {
  Plus,
  FileText,
  Wrench,
  Package,
  Clock,
  TrendingUp,
  StickyNote,
  Camera,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types';

interface MicroActionsProps {
  actions: MicroAction[];
  resultId: string;
}

export default function MicroActions({ actions, resultId }: MicroActionsProps) {
  const handleAction = (action: MicroAction) => {
    // TODO: Implement actual action handlers
    console.log('Action triggered:', action, 'for result:', resultId);

    // Placeholder action routing
    switch (action) {
      case 'create_work_order':
        console.log('Creating work order...');
        break;
      case 'add_to_handover':
        console.log('Adding to handover...');
        break;
      case 'open_document':
        console.log('Opening document...');
        break;
      case 'order_part':
        console.log('Ordering part...');
        break;
      case 'view_history':
        console.log('Viewing history...');
        break;
      case 'show_predictive':
        console.log('Showing predictive insights...');
        break;
      case 'add_note':
        console.log('Adding note...');
        break;
      case 'attach_photo':
        console.log('Attaching photo...');
        break;
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
    };

    return configs[action];
  };

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const config = getActionConfig(action);
        const Icon = config.icon;

        return (
          <button
            key={action}
            onClick={(e) => {
              e.stopPropagation();
              handleAction(action);
            }}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
              config.variant === 'primary'
                ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {config.label}
          </button>
        );
      })}
    </div>
  );
}
