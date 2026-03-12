'use client';

/**
 * PurchaseOrderLensContent - Inner content for Purchase Order lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import {
  AttachmentsSection,
  RelatedEntitiesSection,
  type Attachment,
  type RelatedEntity,
} from './sections';

export interface PurchaseOrderLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'cancelled':
    case 'rejected': return 'critical';
    case 'draft':
    case 'pending_approval': return 'warning';
    case 'approved':
    case 'received':
    case 'completed': return 'success';
    case 'ordered':
    case 'partially_received': return 'neutral';
    default: return 'neutral';
  }
}

export function PurchaseOrderLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: PurchaseOrderLensContentProps) {
  // Map data
  const po_number = (data.po_number as string) || `PO-${id.slice(0, 8)}`;
  const status = (data.status as string) || 'draft';
  const supplier_name = (data.supplier_name as string) || (data.vendor_name as string) || 'Unknown Supplier';
  const order_date = data.order_date as string | undefined;
  const expected_delivery = data.expected_delivery as string | undefined;
  const total_amount = data.total_amount as number | null | undefined;
  const currency = (data.currency as string) || 'USD';

  // Items from child table
  const items = (data.items as Array<{
    id: string;
    description?: string;
    part_name?: string;
    quantity: number;
    unit_price?: number | null;
  }>) || [];

  // Attachments and related entities
  const attachments = (data.attachments as Attachment[]) || [];
  const related_entities = (data.related_entities as RelatedEntity[]) || [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Supplier', value: supplier_name },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Total', value: total_amount != null ? `${currency} ${total_amount.toFixed(2)}` : '—' },
    { label: 'Ordered', value: order_date ? formatRelativeTime(order_date) : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Purchase Order" title={po_number} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={po_number}
            subtitle={supplier_name}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {expected_delivery && (
          <div className="mt-3">
            <p className="typo-body text-celeste-text-muted">
              Expected delivery: {new Date(expected_delivery).toLocaleDateString()}
            </p>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No items on this order.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => (
                  <li key={item.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                    <span className="typo-body text-celeste-text-primary">
                      {item.description || item.part_name || `Item ${index + 1}`}
                    </span>
                    <span className="typo-body text-celeste-text-muted">
                      Qty: {item.quantity}
                      {item.unit_price != null && ` @ ${currency} ${item.unit_price.toFixed(2)}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </SectionContainer>
        </div>

        {attachments.length > 0 && (
          <div className="mt-6">
            <AttachmentsSection attachments={attachments} onAddFile={() => {}} canAddFile={false} stickyTop={56} />
          </div>
        )}

        {related_entities.length > 0 && onNavigate && (
          <div className="mt-6">
            <RelatedEntitiesSection entities={related_entities} onNavigate={onNavigate} stickyTop={56} />
          </div>
        )}
      </main>
    </div>
  );
}
