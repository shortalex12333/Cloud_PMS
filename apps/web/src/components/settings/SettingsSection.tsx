'use client';

/**
 * SettingsSection - Section wrapper for Settings modal
 *
 * Provides consistent section header styling per Celeste design system.
 * No hardcoded values - tokens only.
 */

import { ReactNode } from 'react';

interface SettingsSectionProps {
  title: string;
  children: ReactNode;
}

export function SettingsSection({ title, children }: SettingsSectionProps) {
  return (
    <div className="space-y-[var(--celeste-spacing-3)]">
      <h3 className="text-celeste-xs font-semibold text-celeste-text-muted uppercase tracking-widest">
        {title}
      </h3>
      <div className="bg-celeste-bg-primary border border-celeste-border rounded-celeste-md">
        {children}
      </div>
    </div>
  );
}
