'use client';

/**
 * ResultCard
 * The atomic unit of CelesteOS.
 *
 * Structure (from UX spec):
 * [Header — what this thing is]
 * [Body — the minimum useful truth]
 * [Primary Action]    [▼]
 *
 * Nothing else is allowed.
 *
 * Brand tokens: semantic colors, fontSize scale, font-body
 */

import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import ActionDropdown from './ActionDropdown';
import type { Action } from './ActionDropdown';

interface ResultCardProps {
  /** What this thing is */
  header: string;
  /** The minimum useful truth */
  body: string;
  /** Optional secondary info */
  meta?: string;
  /** Primary action - should be safest READ action */
  primaryAction?: Action;
  /** Additional actions for dropdown */
  actions?: Action[];
  /** Is this card selected/focused */
  isSelected?: boolean;
  className?: string;
}

export default function ResultCard({
  header,
  body,
  meta,
  primaryAction,
  actions = [],
  isSelected = false,
  className,
}: ResultCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const hasDropdown = actions.length > 0;

  return (
    <div
      className={cn(
        'px-4 py-3 font-body',
        'border-b border-celeste-border-subtle',
        'transition-colors duration-celeste-fast',
        isSelected && 'bg-celeste-blue/10',
        className
      )}
    >
      {/* Header — what this thing is */}
      <div className="typo-label font-medium text-celeste-text-primary">
        {header}
      </div>

      {/* Body — the minimum useful truth */}
      <div className="mt-1 typo-body text-celeste-text-secondary leading-relaxed">
        {body}
      </div>

      {/* Meta — optional secondary info */}
      {meta && (
        <div className="mt-1 typo-meta text-celeste-text-disabled">
          {meta}
        </div>
      )}

      {/* Actions row */}
      {(primaryAction || hasDropdown) && (
        <div className="mt-3 flex items-center justify-between">
          {/* Primary Action - READ style (plain text, no decoration) */}
          {primaryAction && (
            <button
              onClick={primaryAction.onAction}
              className="btn-ghost"
            >
              {primaryAction.label}
            </button>
          )}

          {/* Dropdown trigger */}
          {hasDropdown && (
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="btn-icon"
                aria-label="More actions"
              >
                <ChevronDown className="w-4 h-4" />
              </button>

              <ActionDropdown
                actions={actions}
                isOpen={dropdownOpen}
                onClose={() => setDropdownOpen(false)}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
