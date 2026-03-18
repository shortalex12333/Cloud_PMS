'use client';

/**
 * NotesSection — Note timeline matching prototype pattern.
 * Author + mono timestamp, body text, "Show more" for clamped notes.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface NoteItem {
  id: string;
  author: string;
  timestamp: string;
  body: string;
}

export interface NotesSectionProps {
  notes: NoteItem[];
  onAddNote?: () => void;
  canAddNote?: boolean;
}

export function NotesSection({ notes, onAddNote, canAddNote }: NotesSectionProps) {
  return (
    <CollapsibleSection
      id="sec-notes"
      title="Notes"
      count={notes.length}
      action={canAddNote && onAddNote ? { label: '+ Add Note', onClick: onAddNote } : undefined}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M13 1H3a1 1 0 00-1 1v12l3-2h8a1 1 0 001-1V2a1 1 0 00-1-1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
      }
    >
      {notes.length === 0 ? (
        <div className={styles.emptyState}>No notes yet.</div>
      ) : (
        notes.map((note) => <NoteRow key={note.id} note={note} />)
      )}
    </CollapsibleSection>
  );
}

function NoteRow({ note }: { note: NoteItem }) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className={styles.note}>
      <div className={styles.noteMeta}>
        <span className={styles.noteAuthor}>{note.author}</span>
        <span className={styles.noteTime}>{note.timestamp}</span>
      </div>
      <div className={`${styles.noteBody} ${!expanded ? styles.noteBodyClamped : ''}`}>
        {note.body}
      </div>
      {!expanded && note.body.length > 200 && (
        <button className={styles.noteMore} onClick={() => setExpanded(true)}>
          Show more
        </button>
      )}
    </div>
  );
}
