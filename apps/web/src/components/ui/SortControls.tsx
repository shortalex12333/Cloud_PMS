/**
 * SortControls Component
 *
 * Generic sort controls with field selector and direction toggle
 * Entity-agnostic - receives sort field options from parent
 */

'use client';

import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export interface SortField {
  value: string;
  label: string;
}

interface SortControlsProps {
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  sortFields: SortField[];
  onSortChange: (sortBy: string, sortOrder: 'asc' | 'desc') => void;
  className?: string;
}

export function SortControls({
  sortBy,
  sortOrder,
  sortFields,
  onSortChange,
  className,
}: SortControlsProps) {
  const toggleSortOrder = () => {
    const newOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    onSortChange(sortBy, newOrder);
  };

  const handleFieldChange = (newField: string) => {
    onSortChange(newField, sortOrder);
  };

  const getSortIcon = () => {
    if (sortOrder === 'asc') {
      return <ArrowUp className="h-4 w-4" />;
    }
    return <ArrowDown className="h-4 w-4" />;
  };

  const getSortLabel = () => {
    return sortOrder === 'asc' ? 'Ascending' : 'Descending';
  };

  return (
    <div className={cn('flex items-end gap-2', className)}>
      <div className="space-y-2">
        <Label className="text-xs text-txt-tertiary">
          <ArrowUpDown className="h-3 w-3 inline mr-1" />
          Sort by
        </Label>

        <div className="flex gap-2 items-center">
          {/* Sort field selector */}
          <Select value={sortBy} onValueChange={handleFieldChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sortFields.map((field) => (
                <SelectItem key={field.value} value={field.value}>
                  {field.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Sort direction toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleSortOrder}
            className="h-9 px-3"
            title={getSortLabel()}
          >
            {getSortIcon()}
            <span className="ml-2 text-xs">{getSortLabel()}</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
