'use client';

/**
 * LensPill — Status pill matching prototype brand.
 * Colours: green (good), amber (warning), red (critical), neutral, blue (info).
 */

import * as React from 'react';
import styles from './lens.module.css';

export type PillVariant = 'green' | 'amber' | 'red' | 'neutral' | 'blue';

export interface LensPillProps {
  variant: PillVariant;
  label: string;
  showDot?: boolean;
}

const variantMap: Record<PillVariant, string> = {
  green: styles.pillGreen,
  amber: styles.pillAmber,
  red: styles.pillRed,
  neutral: styles.pillNeutral,
  blue: styles.pillBlue,
};

export function LensPill({ variant, label, showDot = true }: LensPillProps) {
  return (
    <span className={`${styles.pill} ${variantMap[variant]}`}>
      {showDot && <span className={styles.dot} />}
      {label}
    </span>
  );
}
