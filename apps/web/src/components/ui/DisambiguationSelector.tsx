'use client';

/**
 * DisambiguationSelector Component
 *
 * Blocking UI component for disambiguation when multiple matches are found.
 * Used in modals to require user selection before action execution.
 *
 * Features:
 * - Radio button group for clear single selection
 * - Displays option metadata (location, category, etc.)
 * - Required field indication with warning styling
 * - Full keyboard accessibility with aria labels
 * - Visual distinction from regular form fields
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DisambiguationOption {
  id: string;
  name: string;
  /** Additional metadata for display (location, category, type, etc.) */
  [key: string]: any;
}

export interface DisambiguationSelectorProps {
  /** Field name for form binding (e.g., "equipment_id") */
  fieldName: string;
  /** Human-readable field label (e.g., "Equipment") */
  fieldLabel: string;
  /** Array of options to choose from */
  options: DisambiguationOption[];
  /** Callback when user selects an option */
  onSelect: (selectedId: string) => void;
  /** Whether selection is required before proceeding */
  required?: boolean;
  /** Currently selected option ID (for controlled mode) */
  selectedId?: string;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Extract display metadata from option object.
 * Returns array of [label, value] pairs for secondary info display.
 */
function extractMetadata(option: DisambiguationOption): [string, string][] {
  const metadata: [string, string][] = [];
  const skipKeys = new Set(['id', 'name', 'value', 'label']);

  for (const [key, value] of Object.entries(option)) {
    if (skipKeys.has(key) || value == null || value === '') continue;
    if (typeof value === 'object') continue;

    // Convert snake_case to Title Case
    const label = key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

    metadata.push([label, String(value)]);
  }

  return metadata;
}

/**
 * Get a concise metadata string for inline display.
 * Prioritizes location and category fields.
 */
function getInlineMetadata(option: DisambiguationOption): string {
  const parts: string[] = [];

  // Priority fields for inline display
  const priorityFields = ['location', 'category', 'type', 'department', 'system'];

  for (const field of priorityFields) {
    if (option[field] && typeof option[field] === 'string') {
      parts.push(option[field]);
    }
  }

  return parts.slice(0, 2).join(' - ');
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DisambiguationSelector({
  fieldName,
  fieldLabel,
  options,
  onSelect,
  required = true,
  selectedId,
  className,
}: DisambiguationSelectorProps) {
  const [internalSelected, setInternalSelected] = React.useState<string | null>(
    selectedId || null
  );

  // Sync with controlled value
  React.useEffect(() => {
    if (selectedId !== undefined) {
      setInternalSelected(selectedId);
    }
  }, [selectedId]);

  const handleSelect = React.useCallback(
    (id: string) => {
      setInternalSelected(id);
      onSelect(id);
    },
    [onSelect]
  );

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent, optionId: string) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleSelect(optionId);
      }
    },
    [handleSelect]
  );

  if (!options || options.length === 0) {
    return null;
  }

  const hasSelection = internalSelected !== null;

  return (
    <div
      className={cn(
        // Container styling with warning border
        'rounded-lg border-2',
        hasSelection
          ? 'border-status-success/50 bg-status-success/5'
          : 'border-status-warning/50 bg-status-warning/5',
        'p-4',
        'transition-colors duration-fast',
        className
      )}
      role="group"
      aria-labelledby={`${fieldName}-disambiguation-label`}
    >
      {/* Header with warning icon */}
      <div className="flex items-start gap-2 mb-3">
        <AlertTriangle
          className={cn(
            'w-5 h-5 flex-shrink-0 mt-0.5',
            hasSelection ? 'text-status-success' : 'text-status-warning'
          )}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <h4
            id={`${fieldName}-disambiguation-label`}
            className="text-label font-semibold text-txt-primary"
          >
            Multiple matches found for "{fieldLabel}"
          </h4>
          <p className="text-meta text-txt-secondary mt-0.5">
            {required && !hasSelection
              ? 'Please select one to continue'
              : hasSelection
              ? 'Selection made'
              : 'Select an option below'}
          </p>
        </div>
      </div>

      {/* Radio button options */}
      <div
        role="radiogroup"
        aria-required={required}
        aria-label={`Select ${fieldLabel}`}
        className="space-y-2"
      >
        {options.map((option) => {
          const isSelected = internalSelected === option.id;
          const inlineMetadata = getInlineMetadata(option);

          return (
            <label
              key={option.id}
              className={cn(
                'flex items-start gap-3 p-3 rounded-md cursor-pointer',
                'border transition-all duration-fast',
                isSelected
                  ? 'border-brand-interactive bg-brand-interactive/10 ring-2 ring-brand-interactive/30'
                  : 'border-surface-border bg-surface-primary hover:border-brand-interactive/50 hover:bg-surface-primary/80'
              )}
              onKeyDown={(e) => handleKeyDown(e, option.id)}
            >
              {/* Custom radio button */}
              <span
                className={cn(
                  'flex-shrink-0 w-5 h-5 rounded-full border-2 mt-0.5',
                  'flex items-center justify-center',
                  'transition-colors duration-fast',
                  isSelected
                    ? 'border-brand-interactive bg-brand-interactive'
                    : 'border-surface-border bg-surface-base'
                )}
                aria-hidden="true"
              >
                {isSelected && (
                  <span className="w-2 h-2 rounded-full bg-white" />
                )}
              </span>

              {/* Hidden actual radio input for accessibility */}
              <input
                type="radio"
                name={fieldName}
                value={option.id}
                checked={isSelected}
                onChange={() => handleSelect(option.id)}
                className="sr-only"
                aria-describedby={`${fieldName}-option-${option.id}-desc`}
              />

              {/* Option content */}
              <div className="flex-1 min-w-0">
                <span
                  className={cn(
                    'block text-body font-medium',
                    isSelected ? 'text-brand-interactive' : 'text-txt-primary'
                  )}
                >
                  {option.name || option.label || option.id}
                </span>
                {inlineMetadata && (
                  <span
                    id={`${fieldName}-option-${option.id}-desc`}
                    className="block text-meta text-txt-secondary mt-0.5"
                  >
                    {inlineMetadata}
                  </span>
                )}
              </div>
            </label>
          );
        })}
      </div>

      {/* Required indicator */}
      {required && !hasSelection && (
        <div
          className="mt-3 flex items-center gap-2 text-meta font-medium text-status-warning"
          role="alert"
          aria-live="polite"
        >
          <span aria-hidden="true">*</span>
          <span>Selection required to continue</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compact Variant (for tight spaces)
// ---------------------------------------------------------------------------

export interface DisambiguationDropdownProps
  extends Omit<DisambiguationSelectorProps, 'className'> {
  className?: string;
}

/**
 * Compact dropdown variant for disambiguation.
 * Use when space is limited or options list is long.
 */
export function DisambiguationDropdown({
  fieldName,
  fieldLabel,
  options,
  onSelect,
  required = true,
  selectedId,
  className,
}: DisambiguationDropdownProps) {
  const [internalSelected, setInternalSelected] = React.useState<string>(
    selectedId || ''
  );

  // Sync with controlled value
  React.useEffect(() => {
    if (selectedId !== undefined) {
      setInternalSelected(selectedId);
    }
  }, [selectedId]);

  const handleChange = React.useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value;
      setInternalSelected(value);
      if (value) {
        onSelect(value);
      }
    },
    [onSelect]
  );

  if (!options || options.length === 0) {
    return null;
  }

  const hasSelection = internalSelected !== '';

  return (
    <div
      className={cn(
        'rounded-lg border-2 p-4',
        hasSelection
          ? 'border-status-success/50 bg-status-success/5'
          : 'border-status-warning/50 bg-status-warning/5',
        'transition-colors duration-fast',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle
          className={cn(
            'w-5 h-5 flex-shrink-0',
            hasSelection ? 'text-status-success' : 'text-status-warning'
          )}
          aria-hidden="true"
        />
        <label
          htmlFor={`${fieldName}-dropdown`}
          className="text-label font-semibold text-txt-primary"
        >
          Multiple matches for "{fieldLabel}"
          {required && <span className="text-status-critical ml-1">*</span>}
        </label>
      </div>

      {/* Dropdown select */}
      <select
        id={`${fieldName}-dropdown`}
        name={fieldName}
        value={internalSelected}
        onChange={handleChange}
        required={required}
        aria-required={required}
        className={cn(
          'w-full px-3 py-2.5 rounded-md',
          'bg-surface-primary border border-surface-border',
          'text-body text-txt-primary',
          'focus:outline-none focus:ring-2 focus:ring-brand-interactive focus:border-transparent',
          'transition-colors duration-fast',
          !hasSelection && 'text-txt-tertiary'
        )}
      >
        <option value="" disabled>
          Select {fieldLabel.toLowerCase()}...
        </option>
        {options.map((option) => {
          const inlineMetadata = getInlineMetadata(option);
          const displayName = option.name || option.label || option.id;

          return (
            <option key={option.id} value={option.id}>
              {displayName}
              {inlineMetadata && ` - ${inlineMetadata}`}
            </option>
          );
        })}
      </select>

      {/* Required indicator */}
      {required && !hasSelection && (
        <p
          className="mt-2 text-meta text-status-warning"
          role="alert"
          aria-live="polite"
        >
          Please select an option to continue
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

export default DisambiguationSelector;
