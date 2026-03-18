'use client';

/**
 * AuditTrailSection — Dot timeline matching prototype audit trail.
 * Teal-bordered dots, vertical connector line, crew emphasis, mono timestamps.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface AuditEvent {
  id: string;
  action: string;
  actor?: string;
  timestamp: string;
}

export interface AuditTrailSectionProps {
  events: AuditEvent[];
  defaultCollapsed?: boolean;
  title?: string;
}

export function AuditTrailSection({ events, defaultCollapsed = true, title = 'History' }: AuditTrailSectionProps) {
  return (
    <CollapsibleSection
      id={`sec-${title.toLowerCase().replace(/\s+/g, '-')}`}
      title={title}
      count={events.length}
      defaultCollapsed={defaultCollapsed}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" />
          <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      }
    >
      {events.length === 0 ? (
        <div className={styles.emptyState}>No history.</div>
      ) : (
        events.map((event) => (
          <div key={event.id} className={styles.auditEvent}>
            <div className={styles.auditDot} />
            <div className={styles.auditInfo}>
              <div className={styles.auditAction}>
                {event.actor && <span className={styles.auditCrew}>{event.actor}</span>}{' '}
                {event.action}
              </div>
              <div className={styles.auditTime}>{event.timestamp}</div>
            </div>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
