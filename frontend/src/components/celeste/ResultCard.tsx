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
        'px-4 py-3',
        'border-b border-[#3d3d3f]/30',
        'transition-colors duration-50',
        isSelected && 'bg-[#0A84FF]/10',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      {/* Header — what this thing is */}
      <div className="text-[14px] font-medium text-[#f5f5f7]">
        {header}
      </div>

      {/* Body — the minimum useful truth */}
      <div className="mt-1 text-[13px] text-[#98989f] leading-relaxed">
        {body}
      </div>

      {/* Meta — optional secondary info */}
      {meta && (
        <div className="mt-1 text-[11px] text-[#636366]">
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
              className="text-[13px] text-[#86868b] hover:text-[#f5f5f7] transition-colors"
            >
              {primaryAction.label}
            </button>
          )}

          {/* Dropdown trigger */}
          {hasDropdown && (
            <div className="relative">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="p-1 text-[#636366] hover:text-[#86868b] transition-colors"
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
