/**
 * ReceivingCard Component
 *
 * Displays receiving record information with status, items count, and actions
 *
 * Architecture:
 * - Renders ONLY backend-provided actions (no UI authority)
 * - data-entity-type="receiving" for E2E testing
 * - data-entity-id for entity identification
 */

'use client';

import { Package, Calendar, FileText, CheckCircle, XCircle, Clock } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface ReceivingCardProps {
  receiving: {
    id: string;
    vendor_reference: string;
    received_date: string;
    status: 'draft' | 'accepted' | 'rejected';
    items_count?: number;
    documents_count?: number;
    received_by?: string;
    notes?: string;
  };
  actions?: MicroAction[];
}

export function ReceivingCard({ receiving, actions = [] }: ReceivingCardProps) {
  const getStatusConfig = () => {
    switch (receiving.status) {
      case 'accepted':
        return {
          icon: CheckCircle,
          label: 'Accepted',
          color: 'text-green-700 bg-green-50 border-green-200',
        };
      case 'rejected':
        return {
          icon: XCircle,
          label: 'Rejected',
          color: 'text-red-700 bg-red-50 border-red-200',
        };
      case 'draft':
      default:
        return {
          icon: Clock,
          label: 'Draft',
          color: 'text-orange-700 bg-orange-50 border-orange-200',
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div
      className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors"
      data-entity-type="receiving"
      data-entity-id={receiving.id}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="mt-1 text-primary">
          <Package className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Vendor Reference & Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{receiving.vendor_reference}</h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase inline-flex items-center gap-1',
                statusConfig.color
              )}
            >
              <StatusIcon className="h-3 w-3" />
              {statusConfig.label}
            </span>
          </div>

          {/* Received Date */}
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-2">
            <Calendar className="h-4 w-4" />
            <span>Received: {new Date(receiving.received_date).toLocaleDateString()}</span>
          </div>

          {/* Items & Documents Count */}
          <div className="flex items-center gap-4 mb-2">
            {receiving.items_count !== undefined && (
              <div className="text-sm">
                <span className="font-medium">Items:</span>{' '}
                <span className={cn(receiving.items_count === 0 && 'text-muted-foreground')}>
                  {receiving.items_count}
                </span>
              </div>
            )}
            {receiving.documents_count !== undefined && (
              <div className="text-sm flex items-center gap-1">
                <FileText className="h-4 w-4" />
                <span className="font-medium">Docs:</span>{' '}
                <span className={cn(receiving.documents_count === 0 && 'text-muted-foreground')}>
                  {receiving.documents_count}
                </span>
              </div>
            )}
          </div>

          {/* Notes (if present) */}
          {receiving.notes && (
            <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
              {receiving.notes}
            </p>
          )}

          {/* Actions - Rendered ONLY if backend provides them */}
          {actions.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-border">
              {actions.map((action) => (
                <ActionButton
                  key={action}
                  action={action}
                  context={{ receiving_id: receiving.id }}
                  variant="secondary"
                  size="sm"
                  showIcon={true}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
