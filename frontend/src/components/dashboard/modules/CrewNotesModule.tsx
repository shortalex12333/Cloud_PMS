'use client';

/**
 * CrewNotesModule
 * Recent crew observations and notes
 */

import React from 'react';
import { MessageSquare, User, Clock, Pin } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const RECENT_NOTES = [
  {
    id: 'N-001',
    author: 'Chief Engineer',
    content: 'Generator 1 coolant temp running slightly high during morning checks. Monitoring.',
    timeAgo: '2h ago',
    pinned: true,
    linkedTo: 'Main Generator #1',
  },
  {
    id: 'N-002',
    author: 'ETO',
    content: 'Port nav light replaced. Tested OK.',
    timeAgo: '5h ago',
    pinned: false,
    linkedTo: 'Navigation Lights',
  },
  {
    id: 'N-003',
    author: '2nd Engineer',
    content: 'Bilge pump cycling more frequently in engine room. May need inspection.',
    timeAgo: '1d ago',
    pinned: false,
    linkedTo: 'Bilge System',
  },
];

// ============================================================================
// COMPONENT
// ============================================================================

interface CrewNotesModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export default function CrewNotesModule({
  isExpanded,
  onToggle,
  className,
}: CrewNotesModuleProps) {
  const pinnedCount = RECENT_NOTES.filter(n => n.pinned).length;

  return (
    <ModuleContainer
      title="Crew Notes"
      icon={<MessageSquare className="h-4.5 w-4.5 text-sky-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status="neutral"
      statusLabel={`${RECENT_NOTES.length} recent notes`}
      badge={pinnedCount > 0 ? pinnedCount : undefined}
      collapsedContent={
        <p className="text-[12px] text-zinc-500 truncate">
          Latest: {RECENT_NOTES[0]?.content}
        </p>
      }
      className={className}
    >
      {/* Notes list */}
      <div className="space-y-3">
        {RECENT_NOTES.map((note) => (
          <div
            key={note.id}
            className={cn(
              'p-3 rounded-xl',
              'bg-zinc-50 dark:bg-zinc-800/50',
              note.pinned && 'ring-1 ring-amber-300 dark:ring-amber-700'
            )}
          >
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-200 dark:bg-zinc-700">
                <User className="h-3 w-3 text-zinc-500" />
              </div>
              <span className="text-[12px] font-medium text-zinc-700 dark:text-zinc-300">
                {note.author}
              </span>
              {note.pinned && (
                <Pin className="h-3 w-3 text-amber-500" />
              )}
              <span className="ml-auto flex items-center gap-1 text-[11px] text-zinc-400">
                <Clock className="h-3 w-3" />
                {note.timeAgo}
              </span>
            </div>

            {/* Content */}
            <p className="text-[13px] text-zinc-600 dark:text-zinc-300 mb-2">
              {note.content}
            </p>

            {/* Linked entity */}
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-zinc-400">
                Re: {note.linkedTo}
              </span>
              <MicroactionButton
                action="add_to_handover"
                size="sm"
                onClick={() => console.log('Add to handover:', note.id)}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4">
        <MicroactionButton
          action="add_work_order_note"
          size="md"
          showLabel
          onClick={() => console.log('Add note')}
        />
        <button className={cn(
          'px-3 py-1.5 rounded-lg',
          'text-[12px] font-medium',
          'text-blue-500 hover:text-blue-600',
          'hover:bg-blue-50 dark:hover:bg-blue-900/20',
          'transition-colors'
        )}>
          View all notes →
        </button>
      </div>
    </ModuleContainer>
  );
}
