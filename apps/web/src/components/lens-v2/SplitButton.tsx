'use client';

/**
 * SplitButton — Primary action + dropdown matching prototype split button.
 * Active state (teal bg), disabled state (grey bg + tooltip), danger items.
 */

import * as React from 'react';
import styles from './lens.module.css';

export interface DropdownItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
  disabledReason?: string;
  /** Optional data-testid applied to the rendered button */
  testid?: string;
}

export interface SplitButtonProps {
  /** Primary action label */
  label: string;
  /** Primary action icon (14px SVG) */
  icon?: React.ReactNode;
  /** Primary action handler */
  onClick: () => void;
  /** Whether primary action is disabled */
  disabled?: boolean;
  /** Tooltip shown when disabled */
  disabledReason?: string;
  /** Dropdown items */
  items?: DropdownItem[];
  /** Optional data-testid applied to the primary (main) button */
  primaryTestId?: string;
  /** Optional data-testid applied to the dropdown chevron toggle button */
  toggleTestId?: string;
}

export function SplitButton({
  label,
  icon,
  onClick,
  disabled = false,
  disabledReason,
  items = [],
  primaryTestId,
  toggleTestId,
}: SplitButtonProps) {
  const [open, setOpen] = React.useState(false);
  const wrapRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  React.useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [open]);

  const toggleDropdown = React.useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setOpen((o) => !o);
    },
    []
  );

  const handleItemClick = React.useCallback(
    (item: DropdownItem) => {
      setOpen(false);
      item.onClick();
    },
    []
  );

  // Find separator position (before first danger item)
  const dangerIndex = items.findIndex((i) => i.danger);
  const hasSeparator = dangerIndex > 0;

  return (
    <div className={styles.splitWrap} ref={wrapRef}>
      <div className={styles.splitBtn}>
        <button
          className={`${styles.splitMain} ${disabled ? styles.disabled : ''}`}
          onClick={disabled ? undefined : onClick}
          disabled={disabled}
          data-testid={primaryTestId}
        >
          {icon}
          {label}
        </button>
        {items.length > 0 && (
          <button
            className={`${styles.splitToggle} ${disabled ? styles.disabled : ''}`}
            onClick={toggleDropdown}
            aria-label="More actions"
            data-testid={toggleTestId}
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>

      {/* Disabled tooltip */}
      {disabled && disabledReason && (
        <div className={styles.splitTooltip}>{disabledReason}</div>
      )}

      {/* Dropdown */}
      {open && items.length > 0 && (
        <div className={`${styles.dropdown} ${styles.open}`}>
          {items.map((item, i) => (
            <React.Fragment key={i}>
              {hasSeparator && i === dangerIndex && <div className={styles.ddSep} />}
              <button
                className={`${styles.ddItem} ${item.danger ? styles.danger : ''}`}
                onClick={item.disabled ? undefined : () => handleItemClick(item)}
                disabled={item.disabled}
                title={item.disabledReason ?? undefined}
                style={item.disabled ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
                data-testid={item.testid}
              >
                {item.icon}
                {item.label}
              </button>
            </React.Fragment>
          ))}
        </div>
      )}
    </div>
  );
}
