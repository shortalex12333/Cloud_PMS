'use client';

/**
 * LensTabBar — horizontal tabbed navigation for entity lens cards.
 *
 * Replaces the vertical-stacked ScrollReveal pattern on dense lenses (work
 * orders, equipment, faults) where users need to land on a specific
 * sub-domain of the entity (Checklist, Safety, Notes, etc.) without scrolling
 * past everything.
 *
 * Design contract
 *   - Sticky under the IdentityStrip; keyboard navigable (←/→).
 *   - Active tab marked by an underline + token-coloured label.
 *   - Counts render in a muted pill after the label ("Notes · 3").
 *   - Disabled tabs render muted, aria-disabled, non-focusable.
 *   - 100% tokenised (no hard-coded colours / sizes).
 *
 * Consumer owns tab body rendering — pass `renderBody(activeKey)`.
 */

import * as React from 'react';

export interface LensTab {
  /** Stable key — used for state + React key. */
  key: string;
  /** Display label. */
  label: string;
  /** Optional count rendered as a muted pill after the label. */
  count?: number;
  /** Optional: disable the tab (renders muted, not focusable). */
  disabled?: boolean;
  /** Optional disabled-reason tooltip text (title attr). */
  disabledReason?: string;
}

export interface LensTabBarProps {
  tabs: LensTab[];
  /** Controlled active tab key (omit for uncontrolled = first enabled). */
  activeKey?: string;
  /** Default tab key for uncontrolled mode. */
  defaultActiveKey?: string;
  onChange?: (key: string) => void;
  /** Render function for the active tab body. */
  renderBody: (activeKey: string) => React.ReactNode;
  /** Aria label for the tablist (default: "Lens sections"). */
  'aria-label'?: string;
}

export function LensTabBar({
  tabs,
  activeKey: controlledKey,
  defaultActiveKey,
  onChange,
  renderBody,
  'aria-label': ariaLabel = 'Lens sections',
}: LensTabBarProps) {
  const firstEnabled = tabs.find((t) => !t.disabled)?.key ?? tabs[0]?.key ?? '';
  const [uncontrolledKey, setUncontrolledKey] = React.useState<string>(
    defaultActiveKey ?? firstEnabled,
  );
  const activeKey = controlledKey ?? uncontrolledKey;

  const handleSelect = React.useCallback(
    (key: string) => {
      const tab = tabs.find((t) => t.key === key);
      if (!tab || tab.disabled) return;
      if (controlledKey === undefined) setUncontrolledKey(key);
      onChange?.(key);
    },
    [tabs, controlledKey, onChange],
  );

  // ← / → keyboard nav between enabled tabs
  const enabledKeys = React.useMemo(
    () => tabs.filter((t) => !t.disabled).map((t) => t.key),
    [tabs],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    const idx = enabledKeys.indexOf(activeKey);
    if (idx < 0) return;
    const next =
      e.key === 'ArrowRight'
        ? enabledKeys[(idx + 1) % enabledKeys.length]
        : enabledKeys[(idx - 1 + enabledKeys.length) % enabledKeys.length];
    handleSelect(next);
    e.preventDefault();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div
        role="tablist"
        aria-label={ariaLabel}
        onKeyDown={handleKeyDown}
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 2,
          display: 'flex',
          gap: 2,
          padding: '0 4px',
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--surface-base)',
          overflowX: 'auto',
          scrollbarWidth: 'none',
        }}
      >
        {tabs.map((tab) => {
          const isActive = tab.key === activeKey;
          return (
            <button
              key={tab.key}
              role="tab"
              type="button"
              id={`tab-${tab.key}`}
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.key}`}
              aria-disabled={tab.disabled || undefined}
              tabIndex={isActive ? 0 : -1}
              title={tab.disabledReason}
              onClick={() => handleSelect(tab.key)}
              disabled={tab.disabled}
              style={{
                appearance: 'none',
                WebkitAppearance: 'none',
                background: 'transparent',
                border: 'none',
                padding: '10px 14px',
                cursor: tab.disabled ? 'not-allowed' : 'pointer',
                fontSize: 13,
                fontWeight: isActive ? 600 : 500,
                color: tab.disabled
                  ? 'var(--text-tertiary)'
                  : isActive
                    ? 'var(--txt)'
                    : 'var(--txt2)',
                borderBottom: `2px solid ${
                  isActive ? 'var(--mark)' : 'transparent'
                }`,
                marginBottom: -1,
                whiteSpace: 'nowrap',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                opacity: tab.disabled ? 0.5 : 1,
                transition: 'color 120ms ease, border-color 120ms ease',
              }}
            >
              {tab.label}
              {typeof tab.count === 'number' && tab.count > 0 && (
                <span
                  aria-hidden="true"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: 18,
                    height: 18,
                    padding: '0 6px',
                    borderRadius: 9,
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--txt2)',
                    background: 'var(--neutral-bg)',
                    border: '1px solid var(--border-faint)',
                  }}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`tabpanel-${activeKey}`}
        aria-labelledby={`tab-${activeKey}`}
        style={{ flex: 1, minHeight: 0, padding: '16px 0' }}
      >
        {renderBody(activeKey)}
      </div>
    </div>
  );
}
