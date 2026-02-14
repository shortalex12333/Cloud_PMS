'use client';

/**
 * SettingsComponents - CelesteOS Settings UI Components
 *
 * Fully tokenized components for settings interface.
 * All styles use CSS custom properties from globals.css.
 */

import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// SECTION HEADER
// ============================================================================

interface SectionHeaderProps {
  title: string;
  isMobile?: boolean;
}

export function SectionHeader({ title, isMobile = false }: SectionHeaderProps) {
  return (
    <div
      className="mb-[var(--celeste-spacing-6)]"
      style={{ paddingLeft: 'var(--celeste-settings-card-padding)' }}
    >
      <h2
        className={cn(
          'font-display m-0',
          'text-celeste-text-title'
        )}
        style={{
          fontSize: 'var(--celeste-settings-title-size)',
          fontWeight: 'var(--celeste-settings-title-weight)',
          lineHeight: isMobile ? '26px' : '28px',
        }}
      >
        {title}
      </h2>
    </div>
  );
}

// ============================================================================
// FORM GROUP
// ============================================================================

interface FormGroupProps {
  label: string;
  children: React.ReactNode;
  description?: string;
}

export function FormGroup({ label, children, description }: FormGroupProps) {
  return (
    <div className="mb-[var(--celeste-spacing-6)]">
      <label
        className={cn(
          'block font-body mb-[var(--celeste-spacing-2)]',
          'text-celeste-text-primary'
        )}
        style={{
          fontSize: 'var(--celeste-settings-label-size)',
          fontWeight: 'var(--celeste-settings-label-weight)',
        }}
      >
        {label}
      </label>
      {children}
      {description && (
        <p
          className="font-body mt-[var(--celeste-spacing-1)] m-0 text-celeste-text-muted"
          style={{ fontSize: 'var(--celeste-settings-helper-size)' }}
        >
          {description}
        </p>
      )}
    </div>
  );
}

// ============================================================================
// SETTINGS ROW (Apple-inspired)
// ============================================================================

interface SelectOption {
  value: string;
  label: string;
}

interface SettingsRowProps {
  label: string;
  value: string;
  isEditable?: boolean;
  onChange?: (value: string) => void;
  type?: 'text' | 'select';
  options?: SelectOption[];
  placeholder?: string;
  isMobile?: boolean;
}

export function SettingsRow({
  label,
  value,
  isEditable = false,
  onChange,
  type = 'text',
  options,
  placeholder,
  isMobile = false,
}: SettingsRowProps) {
  return (
    <div className="settings-row">
      <div
        className={cn(
          'font-body flex-shrink-0 flex items-center',
          'text-celeste-text-title'
        )}
        style={{
          fontSize: isMobile ? '14px' : '16px',
          fontWeight: 'var(--celeste-settings-label-weight)',
          minWidth: isMobile ? '120px' : '140px',
          marginRight: 'var(--celeste-spacing-3)',
        }}
      >
        {label}
      </div>

      <div
        className="flex-shrink-0 text-right flex items-center justify-end"
        style={{ width: isMobile ? '140px' : '200px' }}
      >
        {isEditable ? (
          type === 'select' && options ? (
            <div className="relative flex items-center w-full">
              <select
                value={value}
                onChange={(e) => onChange?.(e.target.value)}
                className={cn(
                  'settings-input w-full text-right cursor-pointer appearance-none',
                  'pr-8'
                )}
                style={{
                  fontSize: isMobile ? '13px' : '16px',
                  padding: isMobile ? '8px 28px 8px 12px' : '10px 32px 10px 16px',
                }}
              >
                {options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <ChevronDown
                className="absolute top-1/2 -translate-y-1/2 pointer-events-none text-celeste-text-muted"
                style={{
                  right: isMobile ? '8px' : '12px',
                  width: '16px',
                  height: '16px',
                }}
              />
            </div>
          ) : (
            <input
              type="text"
              value={value}
              onChange={(e) => onChange?.(e.target.value)}
              placeholder={placeholder}
              className="settings-input w-full text-right"
              style={{
                fontSize: isMobile ? '13px' : '16px',
                padding: isMobile ? '8px 12px' : '10px 16px',
              }}
            />
          )
        ) : (
          <div
            className="font-body text-celeste-text-muted truncate"
            style={{ fontSize: isMobile ? '13px' : '16px' }}
          >
            {value}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// SWITCH ROW
// ============================================================================

interface SwitchRowProps {
  label: string;
  description?: string;
  checked: boolean;
  onCheckedChange?: (checked: boolean) => void;
  isMobile?: boolean;
}

export function SwitchRow({
  label,
  description,
  checked,
  onCheckedChange,
  isMobile = false,
}: SwitchRowProps) {
  return (
    <div className="settings-row items-start">
      <div className="flex-1 mr-[var(--celeste-spacing-3)]">
        <div
          className="font-body text-celeste-text-title"
          style={{
            fontSize: isMobile ? '15px' : '16px',
            fontWeight: 'var(--celeste-settings-label-weight)',
            marginBottom: description ? 'var(--celeste-spacing-1)' : '0',
          }}
        >
          {label}
        </div>
        {description && (
          <div
            className="font-body text-celeste-text-muted"
            style={{ fontSize: isMobile ? '13px' : '14px' }}
          >
            {description}
          </div>
        )}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onCheckedChange?.(!checked)}
        className={cn(
          'relative inline-flex flex-shrink-0 h-6 w-11 items-center rounded-full',
          'transition-colors duration-celeste-fast',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent',
          checked ? 'bg-celeste-accent' : 'bg-celeste-bg-tertiary'
        )}
      >
        <span
          className={cn(
            'inline-block h-5 w-5 rounded-full bg-white shadow-sm',
            'transition-transform duration-celeste-fast',
            checked ? 'translate-x-[22px]' : 'translate-x-[2px]'
          )}
        />
      </button>
    </div>
  );
}

// ============================================================================
// UNIFIED TEXTAREA
// ============================================================================

interface UnifiedTextareaProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  rows?: number;
}

export function UnifiedTextarea({
  value,
  onChange,
  placeholder,
  rows = 4,
}: UnifiedTextareaProps) {
  return (
    <textarea
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows={rows}
      className={cn(
        'settings-input w-full resize-y',
        'max-w-[400px] min-h-[100px]'
      )}
      style={{
        fontSize: '16px',
        lineHeight: '24px',
        padding: 'var(--celeste-spacing-3)',
      }}
    />
  );
}

// ============================================================================
// MOBILE SECTION HEADER
// ============================================================================

interface MobileSectionHeaderProps {
  section: {
    id: string;
    label: string;
    icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  };
  isExpanded: boolean;
  onToggle: () => void;
}

export function MobileSectionHeader({
  section,
  isExpanded,
  onToggle,
}: MobileSectionHeaderProps) {
  const Icon = section.icon;
  return (
    <button
      onClick={onToggle}
      className={cn(
        'w-full flex items-center justify-between text-left',
        'transition-colors duration-celeste-fast',
        'settings-sidebar-item'
      )}
      style={{
        marginBottom: isExpanded ? '0' : 'var(--celeste-spacing-3)',
        borderRadius: isExpanded ? 'var(--celeste-settings-card-radius) var(--celeste-settings-card-radius) 0 0' : 'var(--celeste-settings-card-radius)',
      }}
    >
      <div className="flex items-center gap-[var(--celeste-spacing-3)]">
        <Icon
          className="text-celeste-text-muted"
          style={{ width: '18px', height: '18px' }}
        />
        <span
          className="font-body text-celeste-text-primary"
          style={{ fontSize: '16px', fontWeight: '500' }}
        >
          {section.label}
        </span>
      </div>
      <ChevronDown
        className={cn(
          'text-celeste-text-muted transition-transform duration-celeste-fast',
          isExpanded && 'rotate-180'
        )}
        style={{ width: '16px', height: '16px' }}
      />
    </button>
  );
}

// ============================================================================
// SETTINGS BUTTON - PRIMARY
// ============================================================================

interface SettingsButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

export function SettingsButton({
  variant = 'primary',
  children,
  className,
  ...props
}: SettingsButtonProps) {
  return (
    <button
      className={cn(
        variant === 'primary' ? 'settings-button-primary' : 'settings-button-secondary',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

// ============================================================================
// DATE RANGE BUTTON GROUP
// ============================================================================

interface DateRangeButtonGroupProps {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}

export function DateRangeButtonGroup({
  options,
  value,
  onChange,
}: DateRangeButtonGroupProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            'font-body cursor-pointer outline-none',
            'transition-all duration-celeste-fast'
          )}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            border: value === option.value ? 'none' : '1px solid var(--celeste-settings-card-border)',
            background: value === option.value
              ? 'var(--celeste-settings-button-primary-bg)'
              : 'var(--celeste-settings-input-bg)',
            color: value === option.value
              ? 'var(--celeste-settings-button-primary-text)'
              : 'var(--celeste-settings-input-text-muted)',
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
