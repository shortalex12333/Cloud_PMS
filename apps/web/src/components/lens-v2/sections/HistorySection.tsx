'use client';

/**
 * HistorySection — Prior service periods for the same entity.
 * Shows year-grouped periods (e.g. 2022, 2023, 2024 of the same work order).
 * NOT audit trail (user actions) — that's AuditTrailSection.
 * Matches prototype period layout: year, label, tag (Active/Closed), summary.
 */

import * as React from 'react';
import styles from '../lens.module.css';
import { CollapsibleSection } from '../CollapsibleSection';

export interface HistoryPeriod {
  id: string;
  year: string;
  label: string;
  status: 'active' | 'closed';
  summary: string;
}

export interface HistorySectionProps {
  periods: HistoryPeriod[];
  defaultCollapsed?: boolean;
}

export function HistorySection({ periods, defaultCollapsed = true }: HistorySectionProps) {
  return (
    <CollapsibleSection
      id="sec-history"
      title="History"
      defaultCollapsed={defaultCollapsed}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.3" />
          <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      }
    >
      {periods.length === 0 ? (
        <div className={styles.emptyState}>No prior periods.</div>
      ) : (
        periods.map((period) => (
          <div key={period.id} className={styles.period}>
            <div className={styles.periodHdr}>
              <span className={styles.periodYear}>{period.year}</span>
              <span className={styles.periodLabel}>{period.label}</span>
              <span className={period.status === 'active' ? styles.periodTagActive : styles.periodTagClosed}>
                {period.status === 'active' ? 'Active' : 'Closed'}
              </span>
            </div>
            <div className={styles.periodSummary}>{period.summary}</div>
          </div>
        ))
      )}
    </CollapsibleSection>
  );
}
