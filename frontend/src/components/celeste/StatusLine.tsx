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
        'text-[12px] text-[#86868b]',
        'transition-opacity duration-200',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      {message}
    </div>
  );
}
