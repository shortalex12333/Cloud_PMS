'use client';

/**
 * PartsSection — Parts list matching prototype pattern.
 * Teal-linked part names, mono IDs/quantities, stock levels.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface PartItem {
  id: string;
  name: string;
  partNumber?: string;
  quantity?: string;
  stock?: string;
  onNavigate?: () => void;
}

export interface PartsSectionProps {
  parts: PartItem[];
  onAddPart?: () => void;
  canAddPart?: boolean;
  defaultCollapsed?: boolean;
}

export function PartsSection({ parts, onAddPart, canAddPart, defaultCollapsed = false }: PartsSectionProps) {
  return (
    <CollapsibleSection
      id="sec-parts"
      title="Parts"
      count={parts.length}
      defaultCollapsed={defaultCollapsed}
      action={canAddPart && onAddPart ? { label: '+ Add Part', onClick: onAddPart } : undefined}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M2 4l6-3 6 3v8l-6 3-6-3V4z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M2 4l6 3 6-3M8 7v8" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
      }
    >
      {parts.length === 0 ? (
        <div className={styles.emptyState}>No parts linked.</div>
      ) : (
        parts.map((part) => (
          <div key={part.id} className={styles.partRow}>
            <span
              className={styles.partName}
              onClick={part.onNavigate}
              role={part.onNavigate ? 'link' : undefined}
              tabIndex={part.onNavigate ? 0 : undefined}
            >
              {part.name}
              {part.partNumber && (
                <> <span className={styles.partId}>{part.partNumber}</span></>
              )}
            </span>
            {part.quantity && <span className={styles.partQty}>{part.quantity}</span>}
            {part.stock && <span className={styles.partStock}>{part.stock}</span>}
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
