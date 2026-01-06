'use client';

/**
 * AuditRecord
 * Proof of change - immutable record shown after commit.
 *
 * Rules (from UX spec):
 * - Append-only
 * - Never editable
 * - Never hidden
 */

import React from 'react';
import { cn } from '@/lib/utils';

interface AuditRecordProps {
  userName: string;
  timestamp: Date;
  className?: string;
}

function formatDate(date: Date): string {
  const day = date.getDate();
  const month = date.toLocaleDateString('en-US', { month: 'short' });
  const year = date.getFullYear();
  const time = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  return `${day} ${month} ${year} · ${time}`;
}

export default function AuditRecord({
  userName,
  timestamp,
  className,
}: AuditRecordProps) {
  return (
    <div
      className={cn(
        'text-[11px] text-[#636366]',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      Updated by {userName}
      <br />
      {formatDate(timestamp)}
    </div>
  );
}
