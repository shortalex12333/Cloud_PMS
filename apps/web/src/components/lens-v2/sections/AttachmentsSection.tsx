'use client';

/**
 * AttachmentsSection — File rows with thumbnails matching prototype pattern.
 * Image thumbnails get gradient+teal overlay, doc thumbnails get icon.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface AttachmentItem {
  id: string;
  name: string;
  caption?: string;
  size?: string;
  kind: 'image' | 'document';
  url?: string;
}

export interface AttachmentsSectionProps {
  attachments: AttachmentItem[];
  onAddFile?: () => void;
  canAddFile?: boolean;
  /** Optional data-testid applied to the "+ Upload" section action button */
  addFileTestId?: string;
}

export function AttachmentsSection({ attachments, onAddFile, canAddFile, addFileTestId }: AttachmentsSectionProps) {
  return (
    <CollapsibleSection
      id="sec-attachments"
      title="Attachments"
      count={attachments.length}
      action={canAddFile && onAddFile ? { label: '+ Upload', onClick: onAddFile, testid: addFileTestId } : undefined}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M14 10v3a1 1 0 01-1 1H3a1 1 0 01-1-1v-3M11 5l-3-3-3 3M8 2v9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      }
    >
      {attachments.length === 0 ? (
        <div className={styles.emptyState}>No attachments.</div>
      ) : (
        attachments.map((att) => {
          const inner = (
            <>
              <div className={`${styles.attachThumb} ${att.kind === 'image' ? styles.attachThumbImg : styles.attachThumbDoc}`}>
                {att.kind === 'document' && (
                  <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                    <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5L9 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                    <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                  </svg>
                )}
              </div>
              <div className={styles.attachInfo}>
                <div className={styles.attachName}>{att.name}</div>
                {att.caption && <div className={styles.attachCaption}>{att.caption}</div>}
              </div>
              {att.size && <span className={styles.attachSize}>{att.size}</span>}
            </>
          );
          return att.url ? (
            <a
              key={att.id}
              href={att.url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.attachRow}
              style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              {inner}
            </a>
          ) : (
            <div key={att.id} className={styles.attachRow}>
              {inner}
            </div>
          );
        })
      )}
    </CollapsibleSection>
  );
}
