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
        return 'border-green-200 bg-green-50 text-green-700 hover:bg-green-100';
      case 'yellow':
        return 'border-yellow-200 bg-yellow-50 text-yellow-700 hover:bg-yellow-100';
      case 'orange':
        return 'border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100';
      case 'red':
        return 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100';
      case 'blue':
        return 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100';
      case 'gray':
        return 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100';
      default:
        return 'border-muted bg-muted text-foreground hover:bg-accent';
    }
  };

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">
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
                    : 'border-border bg-background text-muted-foreground hover:bg-accent'
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
