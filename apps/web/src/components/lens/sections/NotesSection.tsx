import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export interface WorkOrderNote {
  id: string;
  author: string;
  author_id?: string;
  content: string;
  created_at: string;
}

export interface NotesSectionProps {
  notes: WorkOrderNote[];
  onAddNote: () => void;
  canAddNote: boolean;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format timestamp per UI_SPEC.md:
 * - Today: "Today at 14:32"
 * - Within 7 days: "3 hours ago", "Yesterday", "2 days ago"
 * - Older: "Jan 23, 2026"
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  // Today
  if (diffDays === 0) {
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `Today at ${hh}:${mm}`;
  }

  // Within 7 days: relative
  if (diffDays < 7) {
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays} days ago`;
  }

  // Older: absolute
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

// ============================================================================
// NOTE ROW
// ============================================================================

interface NoteRowProps {
  note: WorkOrderNote;
}

function NoteRow({ note }: NoteRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  // Determine if content needs truncation (more than 3 lines approximated by char count)
  // We use a CSS-based approach with line-clamp for accuracy
  const needsTruncation = note.content.length > 200 || note.content.split('\n').length > 3;

  return (
    <div
      className={cn(
        // Row layout: 20px horizontal, 12px vertical per UI_SPEC.md
        'px-5 py-3',
        // Minimum touch target: 44px
        'min-h-[44px]',
        // Subtle border between rows (not full width — indented per Apple pattern)
        'border-b border-surface-border-subtle last:border-b-0'
      )}
    >
      {/* Author + timestamp row */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[13px] font-medium text-txt-primary leading-[1.4]">
          {note.author}
        </span>
        <span
          className="text-[12px] text-txt-tertiary leading-[1.4]"
          title={new Date(note.created_at).toLocaleString()}
        >
          {formatTimestamp(note.created_at)}
        </span>
      </div>

      {/* Note content: 3-line clamp with expand */}
      <div>
        <p
          className={cn(
            'text-[14px] font-normal text-txt-primary leading-[1.6]',
            // Max line length from UI_SPEC.md: 680px, achieved via parent max-width
            !isExpanded && needsTruncation && 'line-clamp-3'
          )}
        >
          {note.content}
        </p>

        {needsTruncation && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'mt-1 text-[13px] font-medium text-brand-interactive',
              'hover:text-brand-hover transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-sm'
            )}
          >
            {isExpanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// NOTES SECTION
// ============================================================================

/**
 * NotesSection - Displays work order notes with sticky header and add note action.
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 * Each note shows author, timestamp, and content (truncated to 3 lines with expand).
 *
 * Empty state: contextual, not generic.
 */
export function NotesSection({ notes, onAddNote, canAddNote }: NotesSectionProps) {
  return (
    <SectionContainer
      title="Notes"
      count={notes.length}
      action={
        canAddNote
          ? { label: '+ Add Note', onClick: onAddNote }
          : undefined
      }
    >
      {notes.length === 0 ? (
        // Contextual empty state per UI_SPEC.md language rules
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No notes yet. Add the first note to document progress.
          </p>
          {canAddNote && (
            <GhostButton
              onClick={onAddNote}
              className="mt-3"
            >
              + Add Note
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="-mx-4">
          {notes.map((note) => (
            <NoteRow key={note.id} note={note} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default NotesSection;
