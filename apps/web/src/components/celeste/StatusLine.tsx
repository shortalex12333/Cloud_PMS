'use client';

/**
 * StatusLine
 * System transparency - shows what's happening.
 *
 * Rules (from UX spec):
 * - Appear inline
 * - Are factual
 * - Use present tense
 * - Auto-dismiss when complete
 * - No personality
 * - No reassurance language
 *
 * Brand tokens: semantic.textMuted (#86868B), duration.fast (150ms)
 */

import { cn } from '@/lib/utils';

interface StatusLineProps {
  message: string;
  visible?: boolean;
  className?: string;
}

export default function StatusLine({
  message,
  visible = true,
  className,
}: StatusLineProps) {
  if (!visible || !message) return null;

  return (
    <div
      className={cn(
        'typo-meta text-celeste-text-muted',
        'font-body',
        'transition-opacity duration-celeste-fast',
        className
      )}
    >
      {message}
    </div>
  );
}
