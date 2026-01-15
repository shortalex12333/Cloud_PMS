/**
 * Confirmation Dialog Logic
 *
 * Manages confirmation dialogs for mutation_heavy actions.
 */

import { getAction } from './registry';
import { getConfirmationConfig } from './executor';
import type { MicroAction, ConfirmationConfig } from './types';

/**
 * Check if an action requires confirmation
 */
export function requiresConfirmation(actionName: string): boolean {
  const action = getAction(actionName);
  return action?.requires_confirmation ?? false;
}

/**
 * Get confirmation dialog configuration for an action
 */
export function getConfirmation(actionName: string): ConfirmationConfig | null {
  const action = getAction(actionName);
  if (!action || !action.requires_confirmation) {
    return null;
  }
  return getConfirmationConfig(action);
}

/**
 * Generate confirmation message with context
 */
export function generateConfirmationMessage(
  action: MicroAction,
  context: {
    entityName?: string;
    entityType?: string;
    additionalInfo?: string;
  }
): string {
  const config = getConfirmationConfig(action);
  let message = config.message;

  // Replace placeholders with context values
  if (context.entityName) {
    message = message.replace('{entity_name}', context.entityName);
  }
  if (context.entityType) {
    message = message.replace('{entity_type}', context.entityType);
  }
  if (context.additionalInfo) {
    message += ` ${context.additionalInfo}`;
  }

  return message;
}

/**
 * Get all actions that require confirmation
 */
export function getConfirmationRequiredActions(): string[] {
  const { getConfirmationRequiredActions: getActions } = require('./registry');
  return getActions().map((a: MicroAction) => a.action_name);
}

/**
 * Confirmation state management helper
 */
export interface ConfirmationState {
  isOpen: boolean;
  actionName: string | null;
  config: ConfirmationConfig | null;
  onConfirm: (() => void) | null;
  onCancel: (() => void) | null;
}

export const initialConfirmationState: ConfirmationState = {
  isOpen: false,
  actionName: null,
  config: null,
  onConfirm: null,
  onCancel: null,
};

/**
 * Create a confirmation request
 */
export function createConfirmationRequest(
  actionName: string,
  onConfirm: () => void,
  onCancel: () => void
): ConfirmationState | null {
  const config = getConfirmation(actionName);
  if (!config) {
    return null;
  }

  return {
    isOpen: true,
    actionName,
    config,
    onConfirm,
    onCancel,
  };
}

/**
 * Variant styles for confirmation dialogs
 */
export const confirmationVariantStyles = {
  default: {
    confirmButtonClass: 'bg-primary text-primary-foreground hover:bg-primary/90',
    iconClass: 'text-primary',
  },
  warning: {
    confirmButtonClass: 'bg-yellow-600 text-white hover:bg-yellow-700',
    iconClass: 'text-yellow-600',
  },
  destructive: {
    confirmButtonClass: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    iconClass: 'text-destructive',
  },
};

/**
 * Get styles for a confirmation variant
 */
export function getVariantStyles(
  variant: ConfirmationConfig['variant']
): (typeof confirmationVariantStyles)[keyof typeof confirmationVariantStyles] {
  return confirmationVariantStyles[variant] || confirmationVariantStyles.default;
}
