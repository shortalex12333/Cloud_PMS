// @ts-nocheck - Phase 3: Requires shadcn/ui components and action type updates
/**
 * FilterBadge Component
 *
 * Displays active filter as a removable badge
 * Generic - used by FilterBar to show any active filter
 */

'use client';

import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FilterBadgeProps {
  label: string;
  value: string;
  onRemove: () => void;
  className?: string;
}

export function FilterBadge({ label, value, onRemove, className }: FilterBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-primary/20 bg-primary/10 text-sm',
        className
      )}
    >
      <span className="font-medium text-primary">{label}:</span>
      <span className="text-foreground">{value}</span>
      <button
        onClick={onRemove}
        className="ml-1 hover:bg-primary/20 rounded-full p-0.5 transition-colors"
        aria-label={`Remove ${label} filter`}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}
