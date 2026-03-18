'use client';

/**
 * ChecklistSection — Checklist with progress bar matching prototype pattern.
 * Round check boxes (green filled / pending border), step numbers, completion dimming.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface ChecklistItem {
  id: string;
  step?: number;
  description: string;
  completed: boolean;
  completedBy?: string;
  completedAt?: string;
}

export interface ChecklistSectionProps {
  items: ChecklistItem[];
  onToggle?: (itemId: string) => void;
}

export function ChecklistSection({ items, onToggle }: ChecklistSectionProps) {
  const completedCount = items.filter((i) => i.completed).length;
  const progress = items.length > 0 ? (completedCount / items.length) * 100 : 0;

  return (
    <CollapsibleSection
      id="sec-checklist"
      title="Checklist"
      count={items.length}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.3" />
          <path d="M5.5 8l2 2 3.5-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      }
    >
      {/* Progress bar */}
      {items.length > 0 && (
        <div className={styles.progressBar}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>
      )}

      {items.length === 0 ? (
        <div className={styles.emptyState}>No checklist items.</div>
      ) : (
        items.map((item) => (
          <div
            key={item.id}
            className={`${styles.checkItem} ${item.completed ? styles.done : ''}`}
          >
            {item.step !== undefined && (
              <span className={styles.checkStep}>{item.step}</span>
            )}
            <span
              className={`${styles.checkBox} ${item.completed ? styles.checkBoxChecked : styles.checkBoxPending}`}
              onClick={!item.completed && onToggle ? () => onToggle(item.id) : undefined}
              role={!item.completed && onToggle ? 'button' : undefined}
              tabIndex={!item.completed && onToggle ? 0 : undefined}
            >
              {item.completed && (
                <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8.5l3.5 3.5 6.5-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </span>
            <div className={styles.checkText}>
              <div className={styles.checkDesc}>{item.description}</div>
              {item.completed && (item.completedBy || item.completedAt) && (
                <div className={styles.checkMeta}>
                  {item.completedBy && <span>{item.completedBy}</span>}
                  {item.completedAt && <span className={styles.checkTs}>{item.completedAt}</span>}
                </div>
              )}
            </div>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
