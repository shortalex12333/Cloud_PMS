/**
 * ConfirmationDialog Component
 *
 * Generic confirmation dialog for mutation_heavy actions
 * Used before executing destructive or important actions
 */

'use client';

import { ReactNode, useState, useCallback } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { AlertTriangle } from 'lucide-react';

interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string | ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void | Promise<void>;
  isLoading?: boolean;
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  isLoading = false,
}: ConfirmationDialogProps) {
  const handleConfirm = async () => {
    await onConfirm();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            {destructive && (
              <AlertTriangle className="h-5 w-5 text-destructive" />
            )}
            <AlertDialogTitle>{title}</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-left">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isLoading}
            className={destructive ? 'bg-destructive hover:bg-destructive/90' : ''}
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/**
 * Hook to manage confirmation dialog state
 */
export function useConfirmation() {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<Omit<ConfirmationDialogProps, 'open' | 'onOpenChange'> | null>(null);

  const confirm = useCallback((config: Omit<ConfirmationDialogProps, 'open' | 'onOpenChange'>) => {
    return new Promise<boolean>((resolve) => {
      setConfig({
        ...config,
        onConfirm: async () => {
          await config.onConfirm();
          resolve(true);
        },
      });
      setIsOpen(true);
    });
  }, []);

  const ConfirmDialog = config ? (
    <ConfirmationDialog
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open);
        if (!open) setConfig(null);
      }}
      {...config}
    />
  ) : null;

  return {
    confirm,
    ConfirmDialog,
  };
}
