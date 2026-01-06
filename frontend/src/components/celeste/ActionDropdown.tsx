'use client';

/**
 * ActionDropdown
 * Shows additional actions with READ/MUTATE separation.
 *
 * Rules (from UX spec):
 * - Only appears if more than one action exists
 * - Always right-aligned to primary action
 * - Opens downward
 * - No animation flair
 * - No icons inside
 *
 * Ordering:
 * 1. Remaining READ actions
 * 2. MUTATE actions (visually separated)
 *
 * The divider is semantic, not decorative.
 */

import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

export type ActionType = 'read' | 'mutate';

export interface Action {
  label: string;
  type: ActionType;
  onAction: () => void;
}

interface ActionDropdownProps {
  actions: Action[];
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

export default function ActionDropdown({
  actions,
  isOpen,
  onClose,
  className,
}: ActionDropdownProps) {
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Separate READ and MUTATE actions
  const readActions = actions.filter((a) => a.type === 'read');
  const mutateActions = actions.filter((a) => a.type === 'mutate');
  const hasBothTypes = readActions.length > 0 && mutateActions.length > 0;

  return (
    <div
      ref={ref}
      className={cn(
        'absolute right-0 top-full mt-1',
        'min-w-[160px]',
        'bg-[#2c2c2e] border border-[#3d3d3f]',
        'rounded-lg shadow-lg',
        'py-1',
        'z-50',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      {/* READ actions */}
      {readActions.map((action, i) => (
        <button
          key={`read-${i}`}
          onClick={() => {
            action.onAction();
            onClose();
          }}
          className={cn(
            'w-full px-3 py-1.5 text-left',
            'text-[13px] text-[#f5f5f7]',
            'hover:bg-[#3d3d3f]',
            'transition-colors'
          )}
        >
          {action.label}
        </button>
      ))}

      {/* Semantic divider between READ and MUTATE */}
      {hasBothTypes && (
        <div className="my-1 border-t border-[#3d3d3f]" />
      )}

      {/* MUTATE actions - visually separated, lower priority */}
      {mutateActions.map((action, i) => (
        <button
          key={`mutate-${i}`}
          onClick={() => {
            action.onAction();
            onClose();
          }}
          className={cn(
            'w-full px-3 py-1.5 text-left',
            'text-[13px] text-[#86868b]', // Lower visual priority
            'hover:bg-[#3d3d3f] hover:text-[#f5f5f7]',
            'transition-colors'
          )}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
