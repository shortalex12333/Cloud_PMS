'use client';

/**
 * SplitButton — Primary action + dropdown matching prototype split button.
 * Active state (teal bg), disabled state (grey bg + tooltip), danger items.
 *
 * PR-D2 (2026-04-17): Migrated to Radix Dropdown Menu for viewport-aware
 * collision detection — the dropdown auto-flips when the button sits near
 * the viewport edge. Public API is unchanged. All visual tokens preserved.
 */

import * as React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
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
  // Find separator position (before first danger item)
  const dangerIndex = items.findIndex((i) => i.danger);
  const hasSeparator = dangerIndex > 0;

  const handlePrimary = React.useCallback(() => {
    if (!disabled) onClick();
  }, [disabled, onClick]);

  return (
    <div className={styles.splitWrap}>
      <div className={styles.splitBtn}>
        <button
          type="button"
          className={`${styles.splitMain} ${disabled ? styles.disabled : ''}`}
          onClick={handlePrimary}
          disabled={disabled}
          data-testid={primaryTestId}
        >
          {icon}
          {label}
        </button>
        {items.length > 0 && (
          <DropdownMenu.Root modal={false}>
            <DropdownMenu.Trigger asChild>
              <button
                type="button"
                className={`${styles.splitToggle} ${disabled ? styles.disabled : ''}`}
                disabled={disabled}
                aria-label="More actions"
                data-testid={toggleTestId}
              >
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path
                    d="M4 6l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                side="bottom"
                align="end"
                sideOffset={4}
                collisionPadding={8}
                className={styles.dropdown}
                // Close on Escape is built in; onCloseAutoFocus prevents
                // focus jumping back to trigger when item handler opens a modal.
                onCloseAutoFocus={(e) => e.preventDefault()}
              >
                {items.map((item, i) => (
                  <React.Fragment key={i}>
                    {hasSeparator && i === dangerIndex && (
                      <DropdownMenu.Separator className={styles.ddSep} />
                    )}
                    <DropdownMenu.Item
                      className={`${styles.ddItem} ${item.danger ? styles.danger : ''}`}
                      disabled={item.disabled}
                      onSelect={(e) => {
                        if (item.disabled) {
                          e.preventDefault();
                          return;
                        }
                        item.onClick();
                      }}
                      data-testid={item.testid}
                      title={item.disabledReason ?? undefined}
                      style={item.disabled ? { opacity: 0.4, cursor: 'not-allowed' } : undefined}
                    >
                      {item.icon}
                      {item.label}
                    </DropdownMenu.Item>
                  </React.Fragment>
                ))}
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        )}
      </div>

      {/* Disabled tooltip */}
      {disabled && disabledReason && (
        <div className={styles.splitTooltip} role="tooltip">
          {disabledReason}
        </div>
      )}
    </div>
  );
}
