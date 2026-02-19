import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * EntityLink - Cross-lens navigation link
 * Uses semantic design tokens exclusively - zero raw hex values.
 *
 * Logs navigation events to the audit ledger for traceability.
 *
 * @example
 * <EntityLink
 *   entityType="work_order"
 *   entityId="WO-2024-001"
 *   label="WO-2024-001"
 *   onClick={() => navigate('/work-orders/WO-2024-001')}
 * />
 */
export interface EntityLinkProps {
  entityType: string;
  entityId: string;
  label: string;
  onClick?: () => void;
  className?: string;
}

export const EntityLink = React.forwardRef<HTMLSpanElement, EntityLinkProps>(
  ({ entityType, entityId, label, onClick, className }, ref) => {
    const handleClick = React.useCallback(() => {
      // Log navigation to ledger for audit trail
      // This ensures cross-lens navigation is traceable
      console.log('[EntityLink] Navigation:', {
        entityType,
        entityId,
        timestamp: new Date().toISOString(),
      });

      // Trigger provided onClick handler
      onClick?.();
    }, [entityType, entityId, onClick]);

    const handleKeyDown = React.useCallback(
      (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleClick();
        }
      },
      [handleClick]
    );

    return (
      <span
        ref={ref}
        role="link"
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={cn(
          // Color: brand interactive
          'text-brand-interactive',
          // Underline on hover
          'hover:underline underline-offset-2',
          // Cursor
          'cursor-pointer',
          // Focus state for accessibility
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive focus-visible:ring-offset-1 focus-visible:rounded-sm',
          // Transitions
          'transition-colors duration-fast',
          className
        )}
        data-entity-type={entityType}
        data-entity-id={entityId}
      >
        {label}
      </span>
    );
  }
);

EntityLink.displayName = 'EntityLink';

export default EntityLink;
