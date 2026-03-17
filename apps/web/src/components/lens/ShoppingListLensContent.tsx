'use client';

/**
 * ShoppingListLensContent - Shopping List detail view (lens entity view).
 *
 * Renders inside EntityLensPage at /shopping-list/{id}.
 * Reads all data and actions from useEntityLensContext() — zero props.
 *
 * This component contains:
 * - LensTitleBlock with status pill
 * - VitalSignsRow (5 indicators: Status, Items, Requester, Approver, Created)
 * - Add Item button / Mark as Ordered button (gated by action consts)
 * - Items list with per-item approve / reject / promote buttons
 * - Approval section (if approved_at exists)
 * - RelatedEntitiesSection
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';
import { RelatedEntitiesSection, type RelatedEntity } from './sections';
import { useEntityLensContext } from '@/contexts/EntityLensContext';
import { getEntityRoute } from '@/lib/featureFlags';

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected': return 'critical';
    case 'pending':  return 'warning';
    case 'approved':
    case 'ordered':  return 'success';
    default:         return 'neutral';
  }
}

// ---------------------------------------------------------------------------
// ShoppingListLensContent — zero props
// ---------------------------------------------------------------------------

export function ShoppingListLensContent() {
  const router = useRouter();
  const { entity, executeAction, getAction, isLoading } = useEntityLensContext();

  // Named action consts — null = no permission = don't render the button
  const createItemAction     = getAction('create_shopping_list_item');
  const approveItemAction    = getAction('approve_shopping_list_item');
  const rejectItemAction     = getAction('reject_shopping_list_item');
  const promoteToPartAction  = getAction('promote_candidate_to_part');
  const markOrderedAction    = getAction('mark_shopping_list_ordered');

  // Entity field access — handle both flat and nested payload structures
  const payload = (entity?.payload as Record<string, unknown>) ?? {};
  const title           = ((entity?.title          ?? payload.title)          as string | undefined) ?? 'Shopping List';
  const status          = ((entity?.status         ?? payload.status)         as string | undefined) ?? 'pending';
  const requester_name  = (entity?.requester_name  ?? payload.requester_name) as string | undefined;
  const approver_name   = (entity?.approver_name   ?? payload.approver_name)  as string | undefined;
  const created_at      = (entity?.created_at      ?? payload.created_at)     as string | undefined;
  const approved_at     = (entity?.approved_at     ?? payload.approved_at)    as string | undefined;

  const items = ((entity?.items ?? payload.items) as Array<{
    id?: string;
    part_name: string;
    quantity_requested: number;
    unit?: string;
    status?: string;
    urgency?: 'low' | 'normal' | 'high' | 'critical';
    part_id?: string;
  }> | undefined) ?? [];

  const related_entities = ((entity?.related_entities ?? payload.related_entities) as RelatedEntity[] | undefined) ?? [];

  // Derived display values
  const statusColor = mapStatusToColor(status);
  const statusLabel = status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  // VitalSigns
  const vitalSigns: VitalSign[] = [
    { label: 'Status',    value: statusLabel,                                                    color: statusColor },
    { label: 'Items',     value: `${items.length} item${items.length === 1 ? '' : 's'}` },
    { label: 'Requester', value: requester_name ?? 'Unknown' },
    { label: 'Approver',  value: approver_name  ?? 'Pending' },
    { label: 'Created',   value: created_at ? formatRelativeTime(created_at) : '—' },
  ];

  // Action handlers
  const handleAddItem = React.useCallback(async () => {
    const partName = window.prompt('Part name to add:');
    if (!partName) return;
    const qtyStr   = window.prompt('Quantity requested:', '1');
    const quantity = Math.max(1, parseInt(qtyStr || '1') || 1);
    await executeAction('create_shopping_list_item', {
      part_name:          partName,
      quantity_requested: quantity,
      source_type:        'manual_add',
    });
  }, [executeAction]);

  const handleMarkOrdered = React.useCallback(async () => {
    if (!confirm('Mark this shopping list as ordered?')) return;
    await executeAction('mark_shopping_list_ordered', {});
  }, [executeAction]);

  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) =>
      router.push(getEntityRoute(entityType as Parameters<typeof getEntityRoute>[0], entityId)),
    [router]
  );

  return (
    <div className="flex flex-col h-full">
      {/* Main content — scrollable */}
      <main className="flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12">
        {/* Title block */}
        <div className="mt-6">
          <LensTitleBlock
            title={title}
            status={{ label: statusLabel, color: statusColor }}
          />
        </div>

        {/* Vital Signs */}
        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        {/* Action buttons */}
        <div className="mt-4 flex items-center gap-2 flex-wrap">
          {createItemAction !== null && (
            <PrimaryButton
              onClick={handleAddItem}
              disabled={createItemAction?.disabled ?? isLoading}
              title={createItemAction?.disabled_reason ?? undefined}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              Add Item
            </PrimaryButton>
          )}
          {markOrderedAction !== null && (
            <GhostButton
              onClick={handleMarkOrdered}
              disabled={markOrderedAction?.disabled ?? isLoading}
              title={markOrderedAction?.disabled_reason ?? undefined}
              className="text-[13px] min-h-9 px-4 py-2"
            >
              Mark as Ordered
            </GhostButton>
          )}
        </div>

        {/* Section divider */}
        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        {/* Items list */}
        <div className="mt-6">
          <SectionContainer title={`Items (${items.length})`} stickyTop={56}>
            {items.length === 0 ? (
              <p className="typo-body text-celeste-text-muted">No items added yet.</p>
            ) : (
              <ul className="space-y-3">
                {items.map((item, index) => {
                  const urgencyColor =
                    item.urgency === 'critical' ? 'text-status-critical' :
                    item.urgency === 'high'     ? 'text-status-warning'  : 'text-celeste-text-muted';
                  const itemStatusColor =
                    item.status === 'approved' ? 'text-status-success' :
                    item.status === 'rejected' ? 'text-status-critical' : 'text-celeste-text-muted';

                  return (
                    <li
                      key={item.id ?? index}
                      className="flex justify-between items-center p-3 bg-surface-secondary rounded-lg"
                    >
                      <div>
                        {item.part_id ? (
                          <button
                            onClick={() => handleNavigate('part', item.part_id!)}
                            className="typo-body text-action-primary hover:text-action-primary-hover transition-colors"
                          >
                            {item.part_name}
                          </button>
                        ) : (
                          <span className="typo-body text-celeste-text-primary">{item.part_name}</span>
                        )}
                        <span className="ml-2 typo-body text-celeste-text-muted">
                          × {item.quantity_requested}{item.unit ? ` ${item.unit}` : ''}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        {item.urgency && item.urgency !== 'normal' && (
                          <span className={cn('typo-meta uppercase', urgencyColor)}>{item.urgency}</span>
                        )}
                        {item.status && (
                          <span className={cn('typo-meta uppercase', itemStatusColor)}>
                            {item.status.replace(/_/g, ' ')}
                          </span>
                        )}

                        {/* Per-item action buttons — gated by list-level action consts */}
                        <div className="flex gap-1">
                          {approveItemAction !== null && !!item.id && item.status !== 'approved' && (
                            <button
                              onClick={() => executeAction('approve_shopping_list_item', { item_id: item.id })}
                              disabled={approveItemAction?.disabled ?? isLoading}
                              title={approveItemAction?.disabled_reason ?? undefined}
                              className="typo-meta px-2 py-1 bg-status-success/20 text-status-success rounded hover:bg-status-success/30 disabled:opacity-50"
                            >
                              Approve
                            </button>
                          )}
                          {rejectItemAction !== null && !!item.id && item.status !== 'rejected' && (
                            <button
                              onClick={async () => {
                                const reason = window.prompt('Rejection reason:');
                                if (reason === null) return;
                                await executeAction('reject_shopping_list_item', { item_id: item.id, reason: reason || 'Rejected' });
                              }}
                              disabled={rejectItemAction?.disabled ?? isLoading}
                              title={rejectItemAction?.disabled_reason ?? undefined}
                              className="typo-meta px-2 py-1 bg-status-critical/20 text-status-critical rounded hover:bg-status-critical/30 disabled:opacity-50"
                            >
                              Reject
                            </button>
                          )}
                          {promoteToPartAction !== null && !!item.id && item.status === 'approved' && (
                            <button
                              onClick={() => executeAction('promote_candidate_to_part', { item_id: item.id })}
                              disabled={promoteToPartAction?.disabled ?? isLoading}
                              title={promoteToPartAction?.disabled_reason ?? undefined}
                              className="typo-meta px-2 py-1 bg-surface-secondary text-celeste-text-muted rounded hover:bg-surface-secondary/80 disabled:opacity-50"
                            >
                              Promote to Part
                            </button>
                          )}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionContainer>
        </div>

        {/* Approval section */}
        {approved_at && (
          <div className="mt-6">
            <SectionContainer title="Approval" stickyTop={56}>
              <p className="typo-body text-celeste-text-muted">
                Approved {formatRelativeTime(approved_at)}
                {approver_name && ` by ${approver_name}`}
              </p>
            </SectionContainer>
          </div>
        )}

        {/* Related entities */}
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
