'use client';

/**
 * CollapsibleSection — Section wrapper matching prototype section system.
 * Separator line, icon + title + count + action + chevron, collapsible body.
 */

import * as React from 'react';
import styles from './lens.module.css';

export interface CollapsibleSectionProps {
  id: string;
  title: string;
  icon?: React.ReactNode;
  count?: number;
  action?: { label: string; onClick: () => void };
  defaultCollapsed?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function CollapsibleSection({
  id,
  title,
  icon,
  count,
  action,
  defaultCollapsed = false,
  children,
  className,
}: CollapsibleSectionProps) {
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);
  const bodyRef = React.useRef<HTMLDivElement>(null);

  const toggle = React.useCallback(() => setCollapsed((c) => !c), []);

  const handleActionClick = React.useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      action?.onClick();
    },
    [action]
  );

  return (
    <div
      id={id}
      className={`${styles.section} ${collapsed ? styles.collapsed : ''} ${className ?? ''}`}
    >
      <div className={styles.secHdr} onClick={toggle} role="button" tabIndex={0}>
        {icon && <span className={styles.secIcon}>{icon}</span>}
        <span className={styles.secTitle}>{title}</span>
        {typeof count === 'number' && (
          <span className={styles.secCount}>{count}</span>
        )}
        {action && (
          <button className={styles.secAction} onClick={handleActionClick}>
            {action.label}
          </button>
        )}
        <svg className={styles.secChevron} viewBox="0 0 16 16" fill="none">
          <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div
        ref={bodyRef}
        className={styles.secBody}
        style={collapsed ? undefined : { maxHeight: '4000px', opacity: 1 }}
      >
        {children}
      </div>
    </div>
  );
}
