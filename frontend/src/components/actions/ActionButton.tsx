/**
 * ActionButton Component
 *
 * Renders a single micro-action button with:
 * - Proper icon
 * - Label
 * - Loading state
 * - Confirmation dialog (if required)
 * - Execution logic
 */

'use client';

import { useState } from 'react';
import * as LucideIcons from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  MicroAction,
  getActionMetadata,
  requiresConfirmation,
  requiresReason,
} from '@/types/actions';
import { useActionHandler } from '@/hooks/useActionHandler';
import { ConfirmationDialog } from './ConfirmationDialog';
import { cn } from '@/lib/utils';

interface ActionButtonProps {
  action: MicroAction;
  context?: Record<string, any>;
  variant?: 'default' | 'outline' | 'ghost' | 'secondary';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  className?: string;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  /** Custom label (overrides default) */
  label?: string;
  /** Show icon */
  showIcon?: boolean;
  /** Icon only (no label) */
  iconOnly?: boolean;
  /** Disabled */
  disabled?: boolean;
}

export function ActionButton({
  action,
  context = {},
  variant = 'secondary',
  size = 'sm',
  className,
  onSuccess,
  onError,
  label,
  showIcon = true,
  iconOnly = false,
  disabled = false,
}: ActionButtonProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [showConfirm, setShowConfirm] = useState(false);
  const metadata = getActionMetadata(action);

  // Get icon component
  const IconComponent = showIcon
    ? LucideIcons[metadata.icon as keyof typeof LucideIcons] || LucideIcons.Circle
    : null;

  const needsConfirmation = requiresConfirmation(action);
  const needsReason = requiresReason(action);

  const handleClick = async () => {
    // If action requires reason (like edit_invoice_amount),
    // this should open a modal instead - handled by parent
    if (needsReason) {
      // This will be handled by specific modals (EditInvoiceModal, etc.)
      // The button should not execute directly
      console.warn(`Action ${action} requires a modal with reason input`);
      return;
    }

    // If confirmation required, show dialog first
    if (needsConfirmation) {
      setShowConfirm(true);
      return;
    }

    // Otherwise, execute immediately
    await executeDirectly();
  };

  const executeDirectly = async () => {
    const response = await executeAction(action, context, {
      skipConfirmation: true,
      onSuccess: () => {
        if (onSuccess) onSuccess();
      },
      onError: (error) => {
        if (onError) onError(error);
      },
    });

    // Close confirmation dialog if it was open
    if (showConfirm) {
      setShowConfirm(false);
    }

    return response;
  };

  const displayLabel = label || metadata.label;

  return (
    <>
      <Button
        variant={variant}
        size={size}
        onClick={handleClick}
        disabled={disabled || isLoading}
        className={cn('inline-flex items-center gap-1.5', className)}
      >
        {showIcon && IconComponent && (
          <IconComponent className={cn(
            'h-3.5 w-3.5',
            size === 'icon' && 'h-4 w-4'
          )} />
        )}
        {!iconOnly && (
          <span>{isLoading ? 'Processing...' : displayLabel}</span>
        )}
      </Button>

      {/* Confirmation Dialog */}
      {needsConfirmation && (
        <ConfirmationDialog
          open={showConfirm}
          onOpenChange={setShowConfirm}
          title={`Confirm: ${metadata.label}`}
          description={`Are you sure you want to ${metadata.description.toLowerCase()}?`}
          confirmLabel={metadata.label}
          onConfirm={executeDirectly}
          isLoading={isLoading}
          destructive={action === 'delete_item'}
        />
      )}
    </>
  );
}

/**
 * ActionButtons Component
 *
 * Renders a list of action buttons for a card/result
 */
interface ActionButtonsProps {
  actions: MicroAction[];
  context?: Record<string, any>;
  className?: string;
}

export function ActionButtons({
  actions,
  context = {},
  className,
}: ActionButtonsProps) {
  if (!actions || actions.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {actions.map((action) => (
        <ActionButton
          key={action}
          action={action}
          context={context}
          variant="secondary"
          size="sm"
          showIcon={true}
        />
      ))}
    </div>
  );
}
