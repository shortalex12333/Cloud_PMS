'use client';

/**
 * DocRowsSection — Document rows matching prototype pattern.
 * Teal icon boxes, entity name + code, meta line, chevron.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface DocRowItem {
  id: string;
  name: string;
  code?: string;
  meta?: string;
  date?: string;
  size?: string;
  icon?: React.ReactNode;
  onClick?: () => void;
}

export interface DocRowsSectionProps {
  title: string;
  docs: DocRowItem[];
  defaultCollapsed?: boolean;
  icon?: React.ReactNode;
}

export function DocRowsSection({ title, docs, defaultCollapsed = false, icon }: DocRowsSectionProps) {
  return (
    <CollapsibleSection
      id={`sec-${title.toLowerCase().replace(/\s+/g, '-')}`}
      title={title}
      count={docs.length}
      defaultCollapsed={defaultCollapsed}
      icon={icon ?? (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
        </svg>
      )}
    >
      {docs.length === 0 ? (
        <div className={styles.emptyState}>None.</div>
      ) : (
        docs.map((doc) => (
          <div key={doc.id} className={styles.docRow} onClick={doc.onClick}>
            <div className={styles.docIcon}>
              {doc.icon ?? (
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                </svg>
              )}
            </div>
            <div className={styles.docInfo}>
              <div className={styles.docName}>
                {doc.name}
                {doc.code && <> <span className={styles.docCode}>{doc.code}</span></>}
              </div>
              {(doc.meta || doc.date || doc.size) && (
                <div className={styles.docMeta}>
                  {doc.meta}
                  {doc.date && <> · <span className={styles.docDate}>{doc.date}</span></>}
                  {doc.size && <> · <span className={styles.docSize}>{doc.size}</span></>}
                </div>
              )}
            </div>
            <svg className={styles.docChevron} width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
