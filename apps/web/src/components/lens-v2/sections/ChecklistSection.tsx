'use client';

/**
 * ChecklistSection — Checklist with progress bar.
 *
 * Two item types:
 *   'tick'        — binary done/not-done. Tap the checkbox to complete.
 *   'measurement' — requires a numeric/text value to be logged before the item
 *                   is considered complete. A text input + unit label replace
 *                   the checkbox. Submitting the value marks it complete.
 *
 * Completed measurement items show the logged value + unit inline.
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
  /** 'tick' = done/not-done; 'measurement' = log a value */
  item_type?: 'tick' | 'measurement';
  /** Unit label displayed next to the measurement input/value (e.g. "Ω", "°C") */
  unit?: string;
  /** Logged value for measurement items (set when completed) */
  actual_value?: string | null;
}

export interface ChecklistSectionProps {
  items: ChecklistItem[];
  /** Called when user ticks a tick-type item */
  onToggle?: (itemId: string) => void;
  /** Called when user submits a value for a measurement item */
  onMeasurement?: (itemId: string, value: string) => void;
}

// ── Measurement row ────────────────────────────────────────────────────────

function MeasurementRow({
  item,
  onMeasurement,
}: {
  item: ChecklistItem;
  onMeasurement?: (itemId: string, value: string) => void;
}) {
  const [draft, setDraft] = React.useState('');
  const [saving, setSaving] = React.useState(false);

  if (item.completed) {
    return (
      <div className={`${styles.checkItem} ${styles.done}`}>
        {item.step !== undefined && <span className={styles.checkStep}>{item.step}</span>}
        <span className={`${styles.checkBox} ${styles.checkBoxChecked}`}>
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
            <path d="M3 8.5l3.5 3.5 6.5-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <div className={styles.checkText}>
          <div className={styles.checkDesc} style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
            {item.description}
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 12,
              color: 'var(--mark)', fontWeight: 600,
              background: 'var(--teal-bg)', borderRadius: 4,
              padding: '1px 6px',
            }}>
              {item.actual_value}
              {item.unit && <span style={{ marginLeft: 3, color: 'var(--txt3)', fontWeight: 400 }}>{item.unit}</span>}
            </span>
          </div>
          {(item.completedBy || item.completedAt) && (
            <div className={styles.checkMeta}>
              {item.completedBy && <span>{item.completedBy}</span>}
              {item.completedAt && <span className={styles.checkTs}>{item.completedAt}</span>}
            </div>
          )}
        </div>
      </div>
    );
  }

  const handleLog = async () => {
    if (!draft.trim() || saving || !onMeasurement) return;
    setSaving(true);
    try {
      await onMeasurement(item.id, draft.trim());
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.checkItem}>
      {item.step !== undefined && <span className={styles.checkStep}>{item.step}</span>}
      {/* Measurement icon instead of checkbox */}
      <span style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: 20, height: 20, borderRadius: 4, flexShrink: 0,
        border: '1.5px solid var(--mark-hover)',
        background: 'var(--teal-bg)',
        color: 'var(--mark)',
        fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
      }}>
        #
      </span>
      <div className={styles.checkText} style={{ gap: 6 }}>
        <div className={styles.checkDesc}>{item.description}</div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <input
            type="text"
            inputMode="decimal"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleLog(); }}
            placeholder="Enter reading…"
            style={{
              width: 110, padding: '4px 8px',
              border: '1px solid var(--border-sub)', borderRadius: 5,
              background: 'var(--bg)', color: 'var(--txt)',
              fontSize: 12, fontFamily: 'var(--font-mono)',
            }}
          />
          {item.unit && (
            <span style={{ fontSize: 12, color: 'var(--txt3)', fontFamily: 'var(--font-mono)' }}>
              {item.unit}
            </span>
          )}
          <button
            type="button"
            onClick={handleLog}
            disabled={!draft.trim() || saving || !onMeasurement}
            style={{
              padding: '4px 10px', borderRadius: 5, border: 'none',
              background: draft.trim() ? 'var(--mark)' : 'var(--border-faint)',
              color: draft.trim() ? 'var(--surface)' : 'var(--txt3)',
              fontSize: 11, fontWeight: 600,
              cursor: draft.trim() ? 'pointer' : 'not-allowed',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {saving ? '…' : 'Log'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function ChecklistSection({ items, onToggle, onMeasurement }: ChecklistSectionProps) {
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
      {items.length > 0 && (
        <>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
          }}>
            <div className={styles.progressBar} style={{ flex: 1 }}>
              <div className={styles.progressFill} style={{ width: `${progress}%` }} />
            </div>
            <span style={{ fontSize: 11, color: 'var(--txt3)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
              {completedCount}/{items.length}
            </span>
          </div>
        </>
      )}

      {items.length === 0 ? (
        <div className={styles.emptyState}>No checklist steps yet.</div>
      ) : (
        items.map((item) => {
          if (item.item_type === 'measurement') {
            return (
              <MeasurementRow key={item.id} item={item} onMeasurement={onMeasurement} />
            );
          }
          // Default: tick item
          return (
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
                onKeyDown={!item.completed && onToggle ? (e) => { if (e.key === 'Enter' || e.key === ' ') onToggle(item.id); } : undefined}
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
          );
        })
      )}
    </CollapsibleSection>
  );
}
