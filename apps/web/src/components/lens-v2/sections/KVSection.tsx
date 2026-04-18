'use client';

/**
 * KVSection — Key-value detail rows matching prototype kv-row pattern.
 * Uppercase labels (11px), values (13px), optional mono formatting.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface KVItem {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}

export interface KVSectionProps {
  title: string;
  items: KVItem[];
  defaultCollapsed?: boolean;
  icon?: React.ReactNode;
  /** Rendered after the KV rows, inside the same collapsible body. Used e.g.
   *  for multi-line preformatted blocks that do not fit the label/value grid. */
  children?: React.ReactNode;
}

export function KVSection({ title, items, defaultCollapsed = false, icon, children }: KVSectionProps) {
  return (
    <CollapsibleSection
      id={`sec-${title.toLowerCase().replace(/\s+/g, '-')}`}
      title={title}
      defaultCollapsed={defaultCollapsed}
      icon={icon}
    >
      {items.length === 0 && !children ? (
        <div className={styles.emptyState}>No details.</div>
      ) : (
        items.map((item, i) => (
          <div key={i} className={styles.kvRow}>
            <span className={styles.kvLabel}>{item.label}</span>
            <span className={item.mono ? styles.monoVal : styles.kvValue}>
              {item.value}
            </span>
          </div>
        ))
      )}
      {children}
    </CollapsibleSection>
  );
}
