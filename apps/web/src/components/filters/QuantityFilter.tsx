/**
 * QuantityFilter Component
 *
 * Generic number/quantity filter with comparison operators
 * Entity-agnostic - works for stock, price, hours, any numeric field
 */

'use client';

import { useState } from 'react';
import { Hash } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

export interface QuantityFilterValue {
  operator: 'lt' | 'lte' | 'gt' | 'gte' | 'eq' | 'between';
  value: number | [number, number];
}

interface QuantityFilterProps {
  label: string;
  value: QuantityFilterValue | null;
  min?: number;
  max?: number;
  step?: number;
  onApply: (filter: QuantityFilterValue) => void;
  onClear: () => void;
}

const OPERATORS = [
  { value: 'lt', label: 'Less than (<)' },
  { value: 'lte', label: 'Less than or equal (≤)' },
  { value: 'gt', label: 'Greater than (>)' },
  { value: 'gte', label: 'Greater than or equal (≥)' },
  { value: 'eq', label: 'Equal to (=)' },
  { value: 'between', label: 'Between' },
] as const;

export function QuantityFilter({
  label,
  value,
  min,
  max,
  step = 1,
  onApply,
  onClear,
}: QuantityFilterProps) {
  const [localOperator, setLocalOperator] = useState<QuantityFilterValue['operator']>(
    value?.operator || 'lt'
  );
  const [localValue, setLocalValue] = useState<number | [number, number]>(
    value?.value || 0
  );

  const isBetween = localOperator === 'between';

  const handleApply = () => {
    if (isBetween && Array.isArray(localValue)) {
      if (localValue[0] !== undefined && localValue[1] !== undefined) {
        onApply({ operator: localOperator, value: localValue });
      }
    } else if (!isBetween && typeof localValue === 'number') {
      onApply({ operator: localOperator, value: localValue });
    }
  };

  const handleClear = () => {
    setLocalOperator('lt');
    setLocalValue(0);
    onClear();
  };

  const hasValue = value !== null;

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-2">
        <Label className="typo-meta text-muted-foreground">
          <Hash className="h-3 w-3 inline mr-1" />
          {label}
        </Label>

        <div className="flex gap-2 items-center">
          {/* Operator Selector */}
          <Select
            value={localOperator}
            onValueChange={(val) => setLocalOperator(val as QuantityFilterValue['operator'])}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OPERATORS.map((op) => (
                <SelectItem key={op.value} value={op.value}>
                  {op.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Value Input(s) */}
          {isBetween ? (
            <div className="flex gap-1.5 items-center">
              <Input
                type="number"
                min={min}
                max={max}
                step={step}
                value={Array.isArray(localValue) ? localValue[0] : 0}
                onChange={(e) =>
                  setLocalValue([
                    Number(e.target.value),
                    Array.isArray(localValue) ? localValue[1] : 0,
                  ])
                }
                className="w-[80px]"
                placeholder="Min"
              />
              <span className="typo-meta text-muted-foreground">and</span>
              <Input
                type="number"
                min={min}
                max={max}
                step={step}
                value={Array.isArray(localValue) ? localValue[1] : 0}
                onChange={(e) =>
                  setLocalValue([
                    Array.isArray(localValue) ? localValue[0] : 0,
                    Number(e.target.value),
                  ])
                }
                className="w-[80px]"
                placeholder="Max"
              />
            </div>
          ) : (
            <Input
              type="number"
              min={min}
              max={max}
              step={step}
              value={typeof localValue === 'number' ? localValue : 0}
              onChange={(e) => setLocalValue(Number(e.target.value))}
              className="w-[100px]"
              placeholder="Value"
            />
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-1">
        <Button size="sm" onClick={handleApply}>
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
