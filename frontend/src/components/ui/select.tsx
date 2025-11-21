/**
 * Select Component Stub
 *
 * Minimal implementation for Phase 3 pages.
 * TODO: Replace with proper shadcn/ui select component
 */

import React from 'react';

export function Select({
  value,
  onValueChange,
  children,
}: {
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
}) {
  return <div>{children}</div>;
}

export function SelectTrigger({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={`flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ${className}`}
    >
      {children}
    </button>
  );
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  return <span className="text-muted-foreground">{placeholder}</span>;
}

export function SelectContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md">
      {children}
    </div>
  );
}

export function SelectItem({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 px-2 text-sm outline-none hover:bg-accent">
      {children}
    </div>
  );
}
