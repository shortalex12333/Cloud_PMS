'use client';

/**
 * CrewNotesModule
 * Recent crew observations and notes
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { MessageSquare, User, Clock, Pin, AlertCircle, Lightbulb, Eye, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { useCrewNotesData, CrewNote } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface CrewNotesModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  notes?: CrewNote[];
}

// ============================================================================
// HELPERS
// ============================================================================

function getNoteIcon(type: CrewNote['type']) {
  switch (type) {
    case 'concern':
      return AlertCircle;
    case 'recommendation':
      return Lightbulb;
    default:
      return Eye;
  }
}

function getNoteIconColor(type: CrewNote['type']) {
  switch (type) {
    case 'concern':
      return 'text-amber-500';
    case 'recommendation':
      return 'text-celeste-accent';
    default:
      return 'text-zinc-400';
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function CrewNotesModule({
  isExpanded,
  onToggle,
  className,
  notes: propNotes,
}: CrewNotesModuleProps) {
  // Use hook data unless props are provided
  const hookData = useCrewNotesData();

  const notes = propNotes ?? hookData.notes;
  const isLoading = !propNotes && hookData.isLoading;

  const newNotes = notes.filter(n => n.status === 'new');

  return (
    <ModuleContainer
      title="Crew Notes"
      icon={<MessageSquare className="h-4.5 w-4.5 text-sky-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status="neutral"
      statusLabel={`${notes.length} recent notes`}
      badge={newNotes.length > 0 ? newNotes.length : undefined}
      collapsedContent={
        <p className="typo-meta text-zinc-500 truncate">
          Latest: {notes[0]?.content}
        </p>
      }
      className={className}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 text-zinc-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Notes list */}
          <div className="space-y-3">
            {notes.map((note) => {
              const NoteIcon = getNoteIcon(note.type);
              const iconColor = getNoteIconColor(note.type);

              return (
                <div
                  key={note.id}
                  className={cn(
                    'p-3 rounded-xl',
                    'bg-zinc-50 dark:bg-zinc-800/50',
                    note.status === 'new' && 'ring-1 ring-celeste-accent-muted dark:ring-celeste-accent-muted'
                  )}
                >
                  {/* Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-200 dark:bg-zinc-700">
                      <User className="h-3 w-3 text-zinc-500" />
                    </div>
                    <span className="typo-meta font-medium text-zinc-700 dark:text-zinc-300">
                      {note.author}
                    </span>
                    <NoteIcon className={cn('h-3 w-3', iconColor)} />
                    <span className="ml-auto flex items-center gap-1 typo-meta text-zinc-400">
                      <Clock className="h-3 w-3" />
                      {note.timestamp}
                    </span>
                  </div>

                  {/* Content */}
                  <p className="typo-meta text-zinc-600 dark:text-zinc-300 mb-2">
                    {note.content}
                  </p>

                  {/* Footer */}
                  <div className="flex items-center justify-between">
                    <span className={cn(
                      'typo-meta px-1.5 py-0.5 rounded',
                      note.status === 'new' && 'bg-celeste-accent-subtle text-celeste-accent dark:bg-celeste-accent-subtle dark:text-celeste-accent',
                      note.status === 'reviewed' && 'bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400',
                      note.status === 'actioned' && 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
                    )}>
                      {note.status}
                    </span>
                    <ActionButton
                      action="add_to_handover"
                      context={{ note_id: note.id, source_type: 'note' }}
                      size="sm"
                      iconOnly
                      onSuccess={() => hookData.refresh?.()}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="add_work_order_note"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'typo-meta font-medium',
              'text-celeste-accent hover:text-celeste-accent-hover',
              'hover:bg-celeste-accent-subtle dark:hover:bg-celeste-accent-subtle',
              'transition-colors'
            )}>
              View all notes →
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
