'use client';

/**
 * SettingsRow - Row component for Settings modal
 *
 * Displays label/value pairs or interactive controls.
 * No hardcoded values - tokens only.
 */

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface SettingsRowProps {
  label: string;
  value?: string | ReactNode;
  children?: ReactNode;
  /** Add bottom border (for all rows except last in section) */
  border?: boolean;
}

export function SettingsRow({ label, value, children, border = true }: SettingsRowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between px-[var(--celeste-spacing-4)] py-[var(--celeste-spacing-3)]',
        border && 'border-b border-celeste-border last:border-b-0'
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
