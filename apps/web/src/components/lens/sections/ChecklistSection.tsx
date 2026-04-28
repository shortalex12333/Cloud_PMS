'use client';

/**
 * ChecklistSection — Batch-mode checklist.
 * Items tick/text are captured locally; a single "Submit Checklist" call
 * commits them all. No per-item API calls. Already-completed items are
 * shown as read-only.
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
  itemType?: 'tick' | 'text' | 'measurement';
  actualValue?: string;
  isRequired?: boolean;
}

export interface ChecklistSectionProps {
  items: ChecklistItem[];
  onSubmit?: (items: { checklist_item_id: string; actual_value?: string }[]) => Promise<void>;
}

export function ChecklistSection({ items, onSubmit }: ChecklistSectionProps) {
  const [localState, setLocalState] = React.useState<Record<string, { ticked: boolean; value: string }>>({});
  const [submitting, setSubmitting] = React.useState(false);

  // Reset local state when items change (e.g. after entity refresh)
  React.useEffect(() => {
    setLocalState({});
  }, [items.map((i) => i.id).join(',')]);

  const pendingItems = items.filter((i) => !i.completed);
  const alreadyDone = items.filter((i) => i.completed);

  const completedCount = alreadyDone.length +
    pendingItems.filter((item) => {
      const s = localState[item.id];
      if (!s) return false;
      return item.itemType === 'text' || item.itemType === 'measurement'
        ? s.value.trim().length > 0
        : s.ticked;
    }).length;

  const total = items.length;
  const progress = total > 0 ? (completedCount / total) * 100 : 0;

  // All required pending items are satisfied in local state
  const requiredPending = pendingItems.filter((i) => i.isRequired !== false);
  const allRequiredDone = requiredPending.every((item) => {
    const s = localState[item.id];
    if (!s) return false;
    return item.itemType === 'text' || item.itemType === 'measurement'
      ? s.value.trim().length > 0
      : s.ticked;
  });

  const handleTick = (id: string) => {
    setLocalState((prev) => ({
      ...prev,
      [id]: { ticked: !prev[id]?.ticked, value: prev[id]?.value ?? '' },
    }));
  };

  const handleText = (id: string, value: string) => {
    setLocalState((prev) => ({
      ...prev,
      [id]: { ticked: value.trim().length > 0, value },
    }));
  };

  const handleSubmit = async () => {
    if (!onSubmit || submitting) return;
    const payload = pendingItems
      .filter((item) => {
        const s = localState[item.id];
        if (!s) return false;
        return item.itemType === 'text' || item.itemType === 'measurement'
          ? s.value.trim().length > 0
          : s.ticked;
      })
      .map((item) => {
        const s = localState[item.id];
        return {
          checklist_item_id: item.id,
          ...(s?.value?.trim() ? { actual_value: s.value.trim() } : {}),
        };
      });
    if (payload.length === 0) return;
    setSubmitting(true);
    try {
      await onSubmit(payload);
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = pendingItems.length > 0 && allRequiredDone && !submitting;

  return (
    <CollapsibleSection
      id="sec-checklist"
      title="Checklist"
      count={total}
      icon={
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.3" />
          <path d="M5.5 8l2 2 3.5-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      }
    >
      {total > 0 && (
        <div className={styles.progressBar}>
          <div className={styles.progressFill} style={{ width: `${progress}%` }} />
        </div>
      )}

      {total === 0 ? (
        <div className={styles.emptyState}>No checklist items.</div>
      ) : (
        <>
          {/* Already-completed items */}
          {alreadyDone.map((item) => (
            <div key={item.id} className={`${styles.checkItem} ${styles.done}`}>
              {item.step !== undefined && <span className={styles.checkStep}>{item.step}</span>}
              <span className={`${styles.checkBox} ${styles.checkBoxChecked}`}>
                <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8.5l3.5 3.5 6.5-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <div className={styles.checkText}>
                <div className={styles.checkDesc}>{item.description}</div>
                {item.actualValue && (
                  <div className={styles.checkMeta}><span>{item.actualValue}</span></div>
                )}
                {(item.completedBy || item.completedAt) && (
                  <div className={styles.checkMeta}>
                    {item.completedBy && <span>{item.completedBy}</span>}
                    {item.completedAt && <span className={styles.checkTs}>{item.completedAt}</span>}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Pending items — local interaction only, no API calls */}
          {pendingItems.map((item) => {
            const s = localState[item.id];
            const isTextType = item.itemType === 'text' || item.itemType === 'measurement';
            const isSatisfied = isTextType
              ? (s?.value?.trim().length ?? 0) > 0
              : s?.ticked ?? false;

            return (
              <div
                key={item.id}
                className={`${styles.checkItem} ${isSatisfied ? styles.done : ''}`}
              >
                {item.step !== undefined && <span className={styles.checkStep}>{item.step}</span>}
                {!isTextType && (
                  <span
                    className={`${styles.checkBox} ${isSatisfied ? styles.checkBoxChecked : styles.checkBoxPending}`}
                    onClick={() => handleTick(item.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === ' ' || e.key === 'Enter' ? handleTick(item.id) : undefined}
                  >
                    {isSatisfied && (
                      <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8.5l3.5 3.5 6.5-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </span>
                )}
                {isTextType && (
                  <span className={`${styles.checkBox} ${isSatisfied ? styles.checkBoxChecked : styles.checkBoxPending}`}>
                    {isSatisfied && (
                      <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8.5l3.5 3.5 6.5-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </span>
                )}
                <div className={styles.checkText}>
                  <div className={styles.checkDesc}>
                    {item.description}
                    {item.isRequired !== false && !isSatisfied && (
                      <span style={{ color: 'var(--color-error, #e53e3e)', marginLeft: 4, fontSize: '0.7em' }}>*</span>
                    )}
                  </div>
                  {isTextType && (
                    <input
                      type="text"
                      className={styles.checkInput}
                      placeholder={item.itemType === 'measurement' ? `Enter value${item.actualValue ? ` (${item.actualValue})` : ''}` : 'Enter value…'}
                      value={s?.value ?? ''}
                      onChange={(e) => handleText(item.id, e.target.value)}
                    />
                  )}
                </div>
              </div>
            );
          })}

          {/* Submit button — only shown when there are pending items */}
          {pendingItems.length > 0 && onSubmit && (
            <div className={styles.checklistSubmitRow}>
              <button
                className={styles.checklistSubmitBtn}
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                {submitting ? 'Submitting…' : `Submit Checklist (${completedCount - alreadyDone.length} new)`}
              </button>
              {!allRequiredDone && (
                <span className={styles.checklistHint}>Complete all required items (*) to submit</span>
              )}
            </div>
          )}
        </>
      )}
    </CollapsibleSection>
  );
}
