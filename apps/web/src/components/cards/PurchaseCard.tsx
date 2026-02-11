/**
 * PurchaseCard Component
 *
 * Displays purchase order/request with approval status and actions
 */

'use client';

import { ShoppingCart, DollarSign, Truck, CheckCircle2, Clock } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface PurchaseCardProps {
  purchase: {
    id: string;
    title: string;
    description?: string;
    status: 'pending' | 'approved' | 'ordered' | 'in_transit' | 'received' | 'cancelled';
    total_amount?: number;
    invoice_amount?: number;
    currency?: string;
    supplier?: string;
    created_at: string;
    approved_at?: string;
    received_at?: string;
    tracking_number?: string;
    items_count?: number;
  };
  actions?: MicroAction[];
}

export function PurchaseCard({ purchase, actions = [] }: PurchaseCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'received':
        return 'text-restricted-green bg-restricted-green/10 border-restricted-green/30';
      case 'approved':
      case 'ordered':
        return 'text-celeste-accent bg-celeste-accent/10 border-celeste-accent/30';
      case 'in_transit':
        return 'text-celeste-accent bg-celeste-accent/10 border-celeste-accent/30';
      case 'cancelled':
        return 'text-celeste-text-muted bg-celeste-bg-secondary border-celeste-border';
      default:
        return 'text-restricted-yellow bg-restricted-yellow/10 border-restricted-yellow/30';
    }
  };

  const getStatusIcon = () => {
    switch (purchase.status) {
      case 'received':
        return <CheckCircle2 className="h-5 w-5 text-restricted-green" />;
      case 'in_transit':
        return <Truck className="h-5 w-5 text-celeste-accent" />;
      case 'approved':
      case 'ordered':
        return <ShoppingCart className="h-5 w-5 text-celeste-accent" />;
      default:
        return <Clock className="h-5 w-5 text-restricted-yellow" />;
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        {/* Purchase Icon */}
        <div className="mt-1">{getStatusIcon()}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title & Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{purchase.title}</h3>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                getStatusColor(purchase.status)
              )}
            >
              {purchase.status}
            </span>
          </div>

          {/* Description */}
          {purchase.description && (
            <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
              {purchase.description}
            </p>
          )}

          {/* Supplier */}
          {purchase.supplier && (
            <p className="text-sm text-muted-foreground mb-2">
              <span className="font-medium">Supplier:</span> {purchase.supplier}
            </p>
          )}

          {/* Amount */}
          {(purchase.total_amount || purchase.invoice_amount) && (
            <div className="flex items-center gap-1.5 text-sm font-medium mb-2">
              <DollarSign className="h-4 w-4 text-restricted-green" />
              <span>
                {purchase.currency || '$'}
                {(purchase.invoice_amount || purchase.total_amount)?.toFixed(2)}
              </span>
              {purchase.items_count && (
                <span className="text-xs text-muted-foreground font-normal">
                  ({purchase.items_count} items)
                </span>
              )}
            </div>
          )}

          {/* Tracking */}
          {purchase.tracking_number && (
            <p className="text-xs text-muted-foreground mb-2">
              <span className="font-medium">Tracking:</span> {purchase.tracking_number}
            </p>
          )}

          {/* Dates */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            <span>Created: {formatDate(purchase.created_at)}</span>
            {purchase.approved_at && (
              <span>Approved: {formatDate(purchase.approved_at)}</span>
            )}
            {purchase.received_at && (
              <span className="text-restricted-green">
                Received: {formatDate(purchase.received_at)}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ purchase_id: purchase.id }}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
