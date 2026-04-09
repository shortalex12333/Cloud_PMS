'use client';

/**
 * SuggestedActions Component
 *
 * Renders backend-provided action suggestions as buttons from spotlight search.
 * Uses the prototype-matched ActionPopup (lens-v2) for all action execution —
 * schema-driven fields, signature levels, data gates, proper styling.
 *
 * After successful action execution, navigates to the entity's fragment route.
 */

import React, { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { PenLine } from 'lucide-react';
import { executeAction, type ActionSuggestion } from '@/lib/actionClient';
import { ActionPopup, type ActionPopupField } from '@/components/lens-v2/ActionPopup';
import { getEntityRoute } from '@/lib/entityRoutes';
import { toast } from 'sonner';

// Fields handled automatically — never shown in the form
const BACKEND_AUTO = new Set(['yacht_id', 'signature', 'idempotency_key']);

// Priority options (reused across domains)
const PRIORITY_OPTIONS = [
  { value: 'routine', label: 'Routine' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'critical', label: 'Critical' },
];

// Certificate type options
const CERTIFICATE_TYPE_OPTIONS = [
  { value: 'FLAG', label: 'Flag State Certificate' },
  { value: 'CLASS', label: 'Classification Certificate' },
  { value: 'SAFETY', label: 'Safety Certificate' },
  { value: 'CREW', label: 'Crew Certificate' },
  { value: 'OTHER', label: 'Other' },
];

// Shopping list source type options
const SOURCE_TYPE_OPTIONS = [
  { value: 'manual_add', label: 'Manual Add' },
  { value: 'inventory_low', label: 'Inventory Low' },
  { value: 'inventory_oos', label: 'Inventory Out of Stock' },
  { value: 'work_order_usage', label: 'Work Order Usage' },
  { value: 'receiving_missing', label: 'Receiving Missing' },
  { value: 'receiving_damaged', label: 'Receiving Damaged' },
];

/**
 * Infer ActionPopup field type from field name
 */
function inferFieldType(name: string): ActionPopupField['type'] {
  if (name.includes('date') || name.includes('expiry') || name.includes('issue')) {
    return 'date-pick';
  }
  if (name.includes('reason') || name.includes('note') || name.includes('description') || name.includes('comment') || name.includes('justification')) {
    return 'text-area';
  }
  if (name.includes('type') || name.includes('priority') || name === 'source_type') {
    return 'select';
  }
  if (name.includes('assigned') || name.includes('assignee')) {
    return 'person-assign';
  }
  return 'kv-edit';
}

/**
 * Get select options for known select fields
 */
function getSelectOptions(name: string): { value: string; label: string }[] | undefined {
  if (name.includes('priority')) return PRIORITY_OPTIONS;
  if (name === 'certificate_type') return CERTIFICATE_TYPE_OPTIONS;
  if (name === 'source_type') return SOURCE_TYPE_OPTIONS;
  return undefined;
}

/**
 * Returns true if a field is a narrative/text field that should receive query prefill
 */
function isNarrativeField(name: string): boolean {
  const type = inferFieldType(name);
  return (
    type === 'text-area' ||
    name === 'title' ||
    name === 'content' ||
    name === 'summary' ||
    name === 'text' ||
    name === 'comment' ||
    name === 'hod_justification'
  );
}

/**
 * Convert ActionSuggestion → ActionPopupField[]
 */
function mapActionToPopupFields(
  action: ActionSuggestion,
  query?: string
): ActionPopupField[] {
  const trimmedQuery = query?.trim() ?? '';

  return action.required_fields
    .filter((f) => !BACKEND_AUTO.has(f))
    .map((fieldName) => {
      const type = inferFieldType(fieldName);
      const options = getSelectOptions(fieldName);

      // Resolve initial value: backend prefill > query seed > empty
      let value = '';
      if (action.prefill?.[fieldName] != null && action.prefill[fieldName] !== '') {
        value = String(action.prefill[fieldName]);
      } else if (trimmedQuery && isNarrativeField(fieldName)) {
        value = trimmedQuery;
      }

      return {
        name: fieldName,
        label: fieldName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        type,
        value: value || undefined,
        placeholder: `Enter ${fieldName.replace(/_/g, ' ')}...`,
        required: true,
        options,
      };
    });
}

/**
 * Map action_id prefix → entity type for post-action navigation
 */
function deriveEntityType(action: ActionSuggestion): string | null {
  const id = action.action_id;

  // Direct prefix matching
  if (id.includes('work_order') || id.includes('wo')) return 'work_order';
  if (id.includes('fault')) return 'fault';
  if (id.includes('equipment')) return 'equipment';
  if (id.includes('certificate') || id.includes('cert')) return 'certificate';
  if (id.includes('part') || id.includes('inventory') || id.includes('stock')) return 'part';
  if (id.includes('purchase_order') || id.includes('po')) return 'purchase_order';
  if (id.includes('receiving')) return 'receiving';
  if (id.includes('shopping') || id.includes('list')) return 'shopping_list';
  if (id.includes('document') || id.includes('manual')) return 'document';
  if (id.includes('warranty')) return 'warranty';
  if (id.includes('hours_of_rest') || id.includes('hor')) return 'hours_of_rest';
  if (id.includes('handover')) return 'handover_export';
  if (id.includes('email')) return 'email';

  // Fallback: try domain field
  if (action.domain) {
    const domainMap: Record<string, string> = {
      maintenance: 'work_order',
      certificates: 'certificate',
      inventory: 'part',
      email: 'email',
      purchasing: 'purchase_order',
      receiving: 'receiving',
      documents: 'document',
      manuals: 'document',
    };
    return domainMap[action.domain] ?? null;
  }

  return null;
}

/**
 * Map variant to signature level
 */
function variantToSignatureLevel(variant: ActionSuggestion['variant']): 0 | 1 | 2 {
  switch (variant) {
    case 'READ': return 0;
    case 'MUTATE': return 1;
    case 'SIGNED': return 2;
    default: return 1;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  query?: string;
  onActionComplete?: () => void;
  className?: string;
}

export default function SuggestedActions({
  actions,
  yachtId,
  query,
  onActionComplete,
  className,
}: SuggestedActionsProps) {
  const router = useRouter();
  const [selectedAction, setSelectedAction] = useState<ActionSuggestion | null>(null);

  if (!actions || actions.length === 0) {
    return null;
  }

  const handleActionClick = (action: ActionSuggestion) => {
    setSelectedAction(action);
  };

  const handleClose = () => {
    setSelectedAction(null);
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (!selectedAction || !yachtId) return;

    const context: Record<string, string> = { yacht_id: yachtId };
    const payload: Record<string, unknown> = { ...values };

    // Add idempotency key if required
    if (selectedAction.required_fields.includes('idempotency_key')) {
      payload.idempotency_key = crypto.randomUUID();
    }

    // For SIGNED actions, add signature data
    if (selectedAction.variant === 'SIGNED') {
      payload.signature = {
        signed_by: 'current_user',
        signed_at: new Date().toISOString(),
        reason: (values.reason as string) || 'User initiated action',
        ...(values.signature_name ? { typed_name: values.signature_name } : {}),
        ...(values.pin ? { pin: values.pin } : {}),
      };
    }

    try {
      const result = await executeAction(selectedAction.action_id, context, payload);

      if (result.status === 'success') {
        toast.success('Action completed', { description: selectedAction.label });
        setSelectedAction(null);
        onActionComplete?.();

        // Navigate to entity fragment route if we got back an entity_id
        const entityId = result.result?.entity_id ?? result.result?.id;
        const entityType = deriveEntityType(selectedAction);
        if (entityId && entityType) {
          const route = getEntityRoute(
            entityType as Parameters<typeof getEntityRoute>[0],
            String(entityId)
          );
          router.push(route);
        }
      } else {
        throw new Error(result.message || 'Action failed');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Action failed';
      toast.error('Action failed', { description: message });
    }
  };

  // Build popup props for the selected action
  const popupMode = selectedAction?.variant === 'READ' ? 'read' : 'mutate';
  const popupFields = selectedAction
    ? mapActionToPopupFields(selectedAction, query)
    : [];
  const sigLevel = selectedAction
    ? variantToSignatureLevel(selectedAction.variant)
    : 1;

  return (
    <>
      <div
        className={cn(
          'flex flex-wrap gap-2 px-4 py-2 border-b border-surface-border/30',
          className
        )}
        data-testid="suggested-actions"
      >
        <span className="typo-meta text-txt-secondary self-center mr-1">
          Actions:
        </span>
        {actions.map((action) => (
          <button
            key={action.action_id}
            onClick={() => handleActionClick(action)}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg',
              'typo-meta font-medium',
              'bg-brand-muted text-brand-interactive',
              'hover:bg-brand-hover/30 transition-colors',
              'border border-brand-interactive/30',
              action.variant === 'SIGNED' && 'border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
            )}
            data-testid={`action-btn-${action.action_id}`}
          >
            {action.label}
            {action.variant === 'SIGNED' && (
              <PenLine className="w-3.5 h-3.5" aria-label="Requires signature" />
            )}
          </button>
        ))}
      </div>

      {/* Action Popup — prototype-matched, schema-driven */}
      {selectedAction && (
        <ActionPopup
          mode={popupMode as 'read' | 'mutate'}
          title={selectedAction.label}
          subtitle={query ? `From search: "${query}"` : undefined}
          fields={popupFields}
          signatureLevel={sigLevel}
          onSubmit={handleSubmit}
          onClose={handleClose}
        />
      )}
    </>
  );
}
