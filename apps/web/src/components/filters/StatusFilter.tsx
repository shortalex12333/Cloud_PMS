/**
 * StatusFilter Component
 *
 * Generic multi-select status filter
 * Entity-agnostic - receives status options from parent
 */

'use client';

import { useState } from 'react';
import { Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface StatusOption {
  value: string;
  label: string;
  color?: string;
}

interface StatusFilterProps {
  options: StatusOption[];
  value: string[];
  multiSelect?: boolean;
  onApply: (statuses: string[]) => void;
  onClear: () => void;
}

export function StatusFilter({
  options,
  value,
  multiSelect = true,
  onApply,
  onClear,
}: StatusFilterProps) {
  const [localValue, setLocalValue] = useState<string[]>(value || []);

  const toggleStatus = (status: string) => {
    if (multiSelect) {
      setLocalValue((prev) =>
        prev.includes(status)
          ? prev.filter((s) => s !== status)
          : [...prev, status]
      );
    } else {
      setLocalValue([status]);
    }
  };

  const handleApply = () => {
    if (localValue.length > 0) {
      onApply(localValue);
    }
  };

  const handleClear = () => {
    setLocalValue([]);
    onClear();
  };

  const hasValue = value && value.length > 0;

  const getColorClasses = (color?: string) => {
    switch (color) {
      case 'green':
        return 'border-status-success/30 bg-status-success/10 text-status-success hover:bg-status-success/20';
      case 'yellow':
        return 'border-status-warning/30 bg-status-warning/10 text-status-warning hover:bg-status-warning/20';
      case 'orange':
        return 'border-status-warning/30 bg-status-warning/10 text-status-warning hover:bg-status-warning/20';
      case 'red':
        return 'border-status-critical/30 bg-status-critical/10 text-status-critical hover:bg-status-critical/20';
      case 'blue':
        return 'border-brand-interactive/30 bg-brand-interactive/10 text-brand-interactive hover:bg-brand-interactive/20';
      case 'gray':
        return 'border-surface-border bg-surface-primary text-txt-secondary hover:bg-surface-hover';
      default:
        return 'border-surface-border bg-surface-hover text-txt-primary hover:bg-surface-elevated';
    }
  };

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-2">
        <Label className="text-xs text-txt-tertiary">
          <Filter className="h-3 w-3 inline mr-1" />
          Status
        </Label>

        <div className="flex gap-1.5 flex-wrap max-w-md">
          {options.map((option) => {
            const isSelected = localValue.includes(option.value);
            return (
              <button
                key={option.value}
                onClick={() => toggleStatus(option.value)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-md border transition-colors',
                  isSelected
                    ? getColorClasses(option.color)
                    : 'border-surface-border bg-surface-primary text-txt-tertiary hover:bg-surface-hover'
                )}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-1">
        <Button
          size="sm"
          onClick={handleApply}
          disabled={localValue.length === 0}
        >
          Apply
        </Button>
        {hasValue && (
          <Button size="sm" variant="ghost" onClick={handleClear}>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
