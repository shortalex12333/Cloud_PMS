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
  /** Human name (resolved from user_id). Never a raw UUID. */
  actor?: string;
  /** Resolved role (e.g. "chief_engineer") — rendered as small suffix after the actor name. */
  actor_role?: string;
  /** ISO timestamp or pre-formatted string. */
  timestamp: string;
  /**
   * When true, the row is rendered struck-through with a "(deleted)" suffix.
   * Per spec: we NEVER hard-delete audit rows — soft-delete keeps them visible
   * with visual emphasis for the audit trail.
   */
  deleted?: boolean;
}

export interface AuditTrailSectionProps {
  events: AuditEvent[];
  defaultCollapsed?: boolean;
  title?: string;
}

/**
 * Audit trail dot-timeline. Each event = `<actor> <action> · <role>` + timestamp.
 * Deleted rows kept visible with line-through (soft-delete per spec).
 */
export function AuditTrailSection({ events, defaultCollapsed = true, title = 'Audit Trail' }: AuditTrailSectionProps) {
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
          <div
            key={event.id}
            className={styles.auditEvent}
            style={event.deleted ? { opacity: 0.6 } : undefined}
          >
            <div className={styles.auditDot} />
            <div className={styles.auditInfo}>
              <div
                className={styles.auditAction}
                style={event.deleted ? { textDecoration: 'line-through' } : undefined}
              >
                {event.actor && <span className={styles.auditCrew}>{event.actor}</span>}
                {event.actor_role && (
                  <span
                    style={{
                      fontSize: 'var(--font-size-caption)',
                      color: 'var(--text-tertiary)',
                      marginLeft: '6px',
                    }}
                  >
                    · {event.actor_role.replace(/_/g, ' ')}
                  </span>
                )}{' '}
                {event.action}
                {event.deleted && (
                  <span
                    style={{
                      fontSize: 'var(--font-size-caption)',
                      color: 'var(--status-critical)',
                      marginLeft: '8px',
                      textDecoration: 'none',
                    }}
                  >
                    (deleted)
                  </span>
                )}
              </div>
              <div className={styles.auditTime}>{event.timestamp}</div>
            </div>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
