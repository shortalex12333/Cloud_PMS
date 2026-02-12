'use client';

/**
 * SettingsRow - Flat row for Settings modal
 *
 * Simple left-right layout. Subtle bottom divider.
 * NO box, NO form styling.
 */

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SettingsRowProps {
  label: string;
  value?: string | ReactNode;
  children?: ReactNode;
  /** Show subtle bottom divider */
  divider?: boolean;
}

export function SettingsRow({ label, value, children, divider = true }: SettingsRowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between py-[var(--celeste-spacing-3)]',
        divider && 'border-b border-celeste-border-subtle'
      )}
    >
      <span className="text-celeste-sm text-celeste-text-secondary">{label}</span>
      {value !== undefined ? (
        <span className="text-celeste-sm font-medium text-celeste-text-primary truncate max-w-[60%] text-right">
          {value}
        </span>
      ) : (
        children
      )}
    </div>
  );
}
