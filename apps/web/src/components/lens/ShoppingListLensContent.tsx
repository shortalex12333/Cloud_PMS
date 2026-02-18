'use client';

/**
 * ShoppingListLensContent - Inner content for Shopping List lens (no LensContainer).
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

export interface ShoppingListLensContentProps {
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
    case 'pending': return 'warning';
    case 'approved':
    case 'ordered': return 'success';
    default: return 'neutral';
  }
}

export function ShoppingListLensContent({
  id,
  data,
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: ShoppingListLensContentProps) {
  // Map data
  const title = (data.title as string) || 'Shopping List';
  const status = (data.status as string) || 'pending';
  const requester_name = data.requester_name as string | undefined;
  const approver_name = data.approver_name as string | undefined;
  const created_at = data.created_at as string | undefined;
  const approved_at = data.approved_at as string | undefined;

  // Items from child table
  const items = (data.items as Array<{
    id: string;
    part_name: string;
    quantity_requested: number;
    unit?: string;
    status: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
  }>) || [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  // Calculate item counts
  const pendingItems = items.filter(i => i.status === 'candidate' || i.status === 'under_review').length;
  const approvedItems = items.filter(i => i.status === 'approved').length;

  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Requester', value: requester_name ?? 'Unknown' },
    { label: 'Approver', value: approver_name ?? 'Pending' },
    { label: 'Created', value: created_at ? formatRelativeTime(created_at) : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Shopping List" title={title} onBack={onBack} onClose={onClose} />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <PrimaryButton onClick={() => console.log('[ShoppingListLens] Add item:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Add Item</PrimaryButton>
          {approvedItems > 0 && (
            <GhostButton onClick={() => console.log('[ShoppingListLens] Mark ordered:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Mark {approvedItems} as Ordered</GhostButton>
          )}
        </div>

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="text-sm text-txt-tertiary">No items added yet.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => {
                  const urgencyColor = item.urgency === 'critical' ? 'text-status-critical' :
                                       item.urgency === 'high' ? 'text-status-warning' : 'text-txt-tertiary';
                  const itemStatusColor = item.status === 'approved' ? 'text-status-success' :
                                          item.status === 'rejected' ? 'text-status-critical' : 'text-txt-tertiary';
                  return (
                    <li key={item.id || index} className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg">
                      <div>
                        <span className="text-sm text-txt-primary">{item.part_name}</span>
                        <span className="ml-2 text-sm text-txt-tertiary">
                          × {item.quantity_requested}{item.unit ? ` ${item.unit}` : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        {item.urgency && item.urgency !== 'normal' && (
                          <span className={cn('text-xs uppercase', urgencyColor)}>{item.urgency}</span>
                        )}
                        <span className={cn('text-xs uppercase', itemStatusColor)}>
                          {item.status.replace(/_/g, ' ')}
                        </span>
                        {(item.status === 'candidate' || item.status === 'under_review') && (
                          <div className="flex gap-1">
                            <button
                              onClick={() => console.log('[ShoppingListLens] Approve item:', item.id)}
                              className="text-xs px-2 py-1 bg-status-success/20 text-status-success rounded hover:bg-status-success/30"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => console.log('[ShoppingListLens] Reject item:', item.id)}
                              className="text-xs px-2 py-1 bg-status-critical/20 text-status-critical rounded hover:bg-status-critical/30"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionContainer>
        </div>

        {approved_at && (
          <div className="mt-6">
            <SectionContainer title="Approval" stickyTop={56}>
              <p className="text-sm text-txt-tertiary">
                Approved {formatRelativeTime(approved_at)}
                {approver_name && ` by ${approver_name}`}
              </p>
            </SectionContainer>
          </div>
        )}
      </main>
    </div>
  );
}

export default ShoppingListLensContent;
