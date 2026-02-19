'use client';

/**
 * ReceivingLensContent - Inner content for Receiving lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';

export interface ReceivingLensContentProps {
  id: string;
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected': return 'critical';
    case 'draft':
    case 'in_review': return 'warning';
    case 'accepted': return 'success';
    default: return 'neutral';
  }
}

export function ReceivingLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: ReceivingLensContentProps) {
  // Map data
  const vendor_name = (data.vendor_name as string) || 'Unknown Vendor';
  const vendor_reference = data.vendor_reference as string | undefined;
  const po_number = data.po_number as string | undefined;
  const status = (data.status as string) || 'draft';
  const received_date = data.received_date as string | undefined;
  const total = data.total as number | undefined;
  const currency = (data.currency as string) || 'USD';
  const received_by = data.received_by as string | undefined;
  const notes = data.notes as string | undefined;

  // Items from child table
  const items = (data.items as Array<{
    id: string;
    description?: string;
    quantity_received: number;
    unit_price?: number | null;
  }>) || [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Vendor', value: vendor_name },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Total', value: total !== undefined ? `${currency} ${total.toFixed(2)}` : '—' },
    { label: 'Received', value: received_date ? formatRelativeTime(received_date) : '—' },
  ];

  const canModify = status === 'draft';

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Receiving" title={po_number || vendor_name} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={po_number || vendor_name}
            subtitle={vendor_reference ? `Ref: ${vendor_reference}` : undefined}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {canModify && (
          <div className="mt-4 flex items-center gap-2">
            <PrimaryButton onClick={() => console.log('[ReceivingLens] Add item:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Add Item</PrimaryButton>
            <GhostButton onClick={() => console.log('[ReceivingLens] Accept:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Accept</GhostButton>
            <GhostButton onClick={() => console.log('[ReceivingLens] Reject:', id)} className="text-[13px] min-h-[36px] px-4 py-2 text-status-critical">Reject</GhostButton>
          </div>
        )}

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No items added yet.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => (
                  <li key={item.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                    <span className="typo-body text-celeste-text-primary">{item.description || `Item ${index + 1}`}</span>
                    <span className="typo-body text-celeste-text-muted">
                      Qty: {item.quantity_received}
                      {item.unit_price !== null && item.unit_price !== undefined && ` @ ${currency} ${item.unit_price.toFixed(2)}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </SectionContainer>
        </div>

        {notes && (
          <div className="mt-6">
            <SectionContainer title="Notes" stickyTop={56}>
              <p className="typo-body text-celeste-text-primary">{notes}</p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}

export default ReceivingLensContent;
