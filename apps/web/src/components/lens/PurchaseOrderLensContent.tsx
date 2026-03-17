'use client';

/**
 * PurchaseOrderLensContent - Purchase Order detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /purchasing/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * No p0 actions are registered for purchase_order yet — available_actions
 * returns []. The shell action bar will be empty. The addAttachmentAction
 * const is a forward-compatibility placeholder that makes canAddFile reactive
 * the moment the backend adds the action.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
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
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// PurchaseOrderLensContent — zero props
// ---------------------------------------------------------------------------

export function PurchaseOrderLensContent() {
  const router = useRouter();
  const { entity, getAction } = useEntityLensContext();

  // Forward-compatibility placeholder — will be non-null once the backend
  // registers the action for this entity type.
  const addAttachmentAction = getAction('add_purchase_order_attachment');

  // Map entity fields — access via entity?.field ?? payload fallback ?? default
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const po_number = ((entity?.po_number ?? payload.po_number) as string | undefined) ?? `PO-${(entity?.id as string | undefined)?.slice(0, 8) ?? 'unknown'}`;
  const status = ((entity?.status ?? payload.status) as string | undefined) ?? 'draft';
  const supplier_name = ((entity?.supplier_name ?? entity?.vendor_name ?? payload.supplier_name ?? payload.vendor_name) as string | undefined) ?? 'Unknown Supplier';
  const order_date = (entity?.order_date ?? payload.order_date) as string | undefined;
  const expected_delivery = (entity?.expected_delivery ?? payload.expected_delivery) as string | undefined;
  const total_amount = (entity?.total_amount ?? payload.total_amount) as number | null | undefined;
  const currency = ((entity?.currency ?? payload.currency) as string | undefined) ?? 'USD';

  const items = ((entity?.items ?? payload.items) as Array<{
    id?: string;
    description?: string;
    part_name?: string;
    quantity: number;
    unit_price?: number | null;
  }> | undefined) ?? [];

  const attachments = ((entity?.attachments ?? payload.attachments) as Attachment[] | undefined) ?? [];
  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  // ---------------------------------------------------------------------------
  // Vital signs
  // ---------------------------------------------------------------------------
  const vitalSigns: VitalSign[] = [
    { label: 'Status', value: statusLabel, color: statusColor },
    { label: 'Supplier', value: supplier_name },
    { label: 'Items', value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Total', value: total_amount != null ? `${currency} ${total_amount.toFixed(2)}` : '—' },
    { label: 'Ordered', value: order_date ? formatRelativeTime(order_date) : '—' },
  ];

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => router.push('/purchasing'), [router]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      <LensHeader entityType="Purchase Order" title={po_number} onBack={handleBack} onClose={handleClose} />

      <main className="flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12">
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
                  <li
                    key={item.id ?? index}
                    className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg"
                  >
                    <span className="typo-body text-celeste-text-primary">
                      {item.description ?? item.part_name ?? `Item ${index + 1}`}
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
            <AttachmentsSection
              attachments={attachments}
              onAddFile={() => {}}
              canAddFile={addAttachmentAction !== null}
              stickyTop={56}
            />
          </div>
        )}

        {related_entities.length > 0 && (
          <div className="mt-6">
            <RelatedEntitiesSection
              entities={related_entities}
              onNavigate={handleNavigate}
              stickyTop={56}
            />
          </div>
        )}
      </main>
    </div>
  );
}
