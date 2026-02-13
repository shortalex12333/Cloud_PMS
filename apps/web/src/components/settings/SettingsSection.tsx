'use client';

/**
 * SettingsSection - Section wrapper for Settings modal
 *
 * NO BOXES. Just a header and content.
 * Content flows flat with subtle dividers.
 */

import { ReactNode } from 'react';

interface SettingsSectionProps {
  title: string;
  children: ReactNode;
}

export function SettingsSection({ title, children }: SettingsSectionProps) {
  return (
    <div>
      <h3 className="text-celeste-xs font-semibold text-celeste-text-muted uppercase tracking-widest mb-[var(--celeste-spacing-3)]">
        {title}
      </h3>
      {children}
    </div>
  );
}
