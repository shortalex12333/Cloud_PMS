/**
 * AlertDialog Component Stub
 *
 * Minimal implementation for Phase 3 pages.
 * TODO: Replace with proper shadcn/ui alert-dialog component
 */

import React from 'react';

export function AlertDialog({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}

export function AlertDialogTrigger({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

export function AlertDialogContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" />
      <div className="relative bg-background p-6 rounded-lg shadow-lg max-w-md w-full">
        {children}
      </div>
    </div>
  );
}

export function AlertDialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="mb-4">{children}</div>;
}

export function AlertDialogTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-semibold">{children}</h2>;
}

export function AlertDialogDescription({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function AlertDialogFooter({ children }: { children: React.ReactNode }) {
  return <div className="flex justify-end gap-2 mt-4">{children}</div>;
}

export function AlertDialogAction({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className="px-4 py-2 bg-primary text-primary-foreground rounded-md"
      {...props}
    >
      {children}
    </button>
  );
}

export function AlertDialogCancel({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className="px-4 py-2 border border-input bg-background rounded-md"
      {...props}
    >
      {children}
    </button>
  );
}
