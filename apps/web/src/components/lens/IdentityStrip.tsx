'use client';

/**
 * IdentityStrip — Entity identity block matching prototype pattern.
 * Top row (overline ID + split button), title, context line, pills, detail lines, description.
 */

import * as React from 'react';
import styles from './lens.module.css';
import { LensPill, type PillVariant } from './LensPill';

export interface DetailLine {
  label: string;
  value: string;
  mono?: boolean;
}

export interface PillDef {
  label: string;
  variant: PillVariant;
  /** Optional data-testid applied to the rendered pill */
  testid?: string;
}

export interface IdentityStripProps {
  /** Mono overline ID (e.g. "WO-2024-0847") */
  overline?: string;
  /** Main title */
  title: string;
  /** Context line (e.g. "Engine Room · Assigned to R. Chen") */
  context?: React.ReactNode;
  /** Status pills */
  pills?: PillDef[];
  /** Key-value detail lines */
  details?: DetailLine[];
  /** Description text */
  description?: string;
  /** Slot for the split button (top-right of identity) */
  actionSlot?: React.ReactNode;
}

export function IdentityStrip({
  overline,
  title,
  context,
  pills,
  details,
  description,
  actionSlot,
}: IdentityStripProps) {
  return (
    <div className={styles.identity}>
      {/* Top row: overline + action */}
      {(overline || actionSlot) && (
        <div className={styles.identityTopRow}>
          {overline ? <span className={styles.identityOverline}>{overline}</span> : <span />}
          {actionSlot}
        </div>
      )}

      {/* Title */}
      <h1 className={styles.identityTitle}>{title}</h1>

      {/* Context line */}
      {context && <div className={styles.identityContext}>{context}</div>}

      {/* Pills */}
      {pills && pills.length > 0 && (
        <div className={styles.pills}>
          {pills.map((p, i) => (
            <LensPill key={i} variant={p.variant} label={p.label} testid={p.testid} />
          ))}
        </div>
      )}

      {/* Detail lines */}
      {details && details.length > 0 && (
        <div className={styles.detailLines}>
          {details.map((d, i) => (
            <div key={i} className={styles.detailLine}>
              <span className={styles.detailLabel}>{d.label}</span>
              <span className={d.mono ? styles.monoVal : styles.detailVal}>
                {d.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Description */}
      {description && (
        <div className={styles.descBlock}>
          <div className={styles.descLabel}>Description</div>
          <div className={styles.descText}>{description}</div>
        </div>
      )}
    </div>
  );
}
