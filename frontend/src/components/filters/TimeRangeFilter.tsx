// @ts-nocheck - Phase 3: Requires shadcn/ui components and action type updates
/**
 * TimeRangeFilter Component
 *
 * Generic time range filter with presets and custom range
 * Entity-agnostic - works for any date-based filtering
 */

'use client';

import { useState } from 'react';
import { Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface TimeRangeValue {
  start: string;
  end: string;
}

interface TimeRangePreset {
  label: string;
  getValue: () => TimeRangeValue;
}

interface TimeRangeFilterProps {
  value: TimeRangeValue | null;
  presets?: TimeRangePreset[];
  onApply: (range: TimeRangeValue) => void;
  onClear: () => void;
}

// Default presets
const DEFAULT_PRESETS: TimeRangePreset[] = [
  {
    label: 'Today',
    getValue: () => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const end = new Date(today);
      end.setHours(23, 59, 59, 999);
      return {
        start: today.toISOString(),
        end: end.toISOString(),
      };
    },
  },
  {
    label: 'This Week',
    getValue: () => {
      const now = new Date();
      const dayOfWeek = now.getDay();
      const start = new Date(now);
      start.setDate(now.getDate() - dayOfWeek);
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      end.setHours(23, 59, 59, 999);
      return {
        start: start.toISOString(),
        end: end.toISOString(),
      };
    },
  },
  {
    label: 'Last 7 Days',
    getValue: () => {
      const end = new Date();
      end.setHours(23, 59, 59, 999);
      const start = new Date(end);
      start.setDate(end.getDate() - 7);
      start.setHours(0, 0, 0, 0);
      return {
        start: start.toISOString(),
        end: end.toISOString(),
      };
    },
  },
  {
    label: 'Last 30 Days',
    getValue: () => {
      const end = new Date();
      end.setHours(23, 59, 59, 999);
      const start = new Date(end);
      start.setDate(end.getDate() - 30);
      start.setHours(0, 0, 0, 0);
      return {
        start: start.toISOString(),
        end: end.toISOString(),
      };
    },
  },
];

export function TimeRangeFilter({
  value,
  presets = DEFAULT_PRESETS,
  onApply,
  onClear,
}: TimeRangeFilterProps) {
  const [localValue, setLocalValue] = useState<TimeRangeValue | null>(value);
  const [customMode, setCustomMode] = useState(false);

  const handlePreset = (preset: TimeRangePreset) => {
    const range = preset.getValue();
    setLocalValue(range);
    setCustomMode(false);
    onApply(range);
  };

  const handleCustomApply = () => {
    if (localValue?.start && localValue?.end) {
      onApply(localValue);
      setCustomMode(false);
    }
  };

  const handleClear = () => {
    setLocalValue(null);
    setCustomMode(false);
    onClear();
  };

  const formatDateForInput = (isoString: string) => {
    return isoString.split('T')[0];
  };

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">
          <Calendar className="h-3 w-3 inline mr-1" />
          Date Range
        </Label>

        {!customMode ? (
          /* Preset Buttons */
          <div className="flex gap-1.5 flex-wrap">
            {presets.map((preset) => (
              <Button
                key={preset.label}
                size="sm"
                variant="outline"
                onClick={() => handlePreset(preset)}
                className="text-xs"
              >
                {preset.label}
              </Button>
            ))}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCustomMode(true)}
              className="text-xs"
            >
              Custom
            </Button>
          </div>
        ) : (
          /* Custom Date Inputs */
          <div className="flex gap-2 items-center">
            <div>
              <Input
                type="date"
                value={localValue?.start ? formatDateForInput(localValue.start) : ''}
                onChange={(e) =>
                  setLocalValue((prev) => ({
                    start: new Date(e.target.value).toISOString(),
                    end: prev?.end || new Date().toISOString(),
                  }))
                }
                className="w-[140px] text-xs"
              />
            </div>
            <span className="text-muted-foreground text-xs">to</span>
            <div>
              <Input
                type="date"
                value={localValue?.end ? formatDateForInput(localValue.end) : ''}
                onChange={(e) =>
                  setLocalValue((prev) => ({
                    start: prev?.start || new Date().toISOString(),
                    end: new Date(e.target.value).toISOString(),
                  }))
                }
                className="w-[140px] text-xs"
              />
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {customMode && (
        <div className="flex gap-1">
          <Button
            size="sm"
            onClick={handleCustomApply}
            disabled={!localValue?.start || !localValue?.end}
          >
            Apply
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setCustomMode(false)}
          >
            Cancel
          </Button>
        </div>
      )}

      {value && !customMode && (
        <Button size="sm" variant="ghost" onClick={handleClear}>
          Clear
        </Button>
      )}
    </div>
  );
}
