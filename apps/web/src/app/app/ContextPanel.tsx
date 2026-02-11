'use client';

/**
 * ContextPanel - Entity Detail View
 *
 * Slides from right when context-open state is active.
 * Renders actual entity cards (FaultCard, WorkOrderCard, etc.) that
 * call /v1/decisions for server-driven action visibility.
 *
 * Phase 12: Updated to render real card components for E2E testability.
 */

import { useSurface } from '@/contexts/SurfaceContext';
import { useAuth } from '@/hooks/useAuth';
import { X, ChevronRight, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FaultCard } from '@/components/cards/FaultCard';
import { WorkOrderCard } from '@/components/cards/WorkOrderCard';
import { EquipmentCard } from '@/components/cards/EquipmentCard';
import { PartCard } from '@/components/cards/PartCard';
import { ReceivingCard } from '@/components/cards/ReceivingCard';
import type { MicroAction } from '@/types/actions';

/**
 * Get available actions for parts based on user role
 * Mirrors backend domain_microactions.py logic
 */
function getPartActions(role: string): MicroAction[] {
  const actions: MicroAction[] = [];

  // READ actions - available to all roles
  const allRoles = ['crew', 'deckhand', 'steward', 'chef', 'bosun', 'engineer', 'eto',
                    'chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'];

  if (allRoles.includes(role)) {
    actions.push('view_part_location' as MicroAction); // Fixed: use action that exists in registry
    actions.push('view_part_stock' as MicroAction); // Fixed: use action that exists in registry
  }

  // Usage History - elevated roles only
  const elevatedRoles = ['engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager'];
  if (elevatedRoles.includes(role)) {
    actions.push('view_part_usage' as MicroAction);
  }

  // MUTATE actions - elevated roles only
  if (elevatedRoles.includes(role)) {
    actions.push('log_part_usage' as MicroAction);
  }

  return actions;
}

/**
 * Get available actions for receiving based on status and user role
 * Mirrors backend receiving_handlers.py permissions (HOD+)
 */
function getReceivingActions(status: string, role: string): MicroAction[] {
  const actions: MicroAction[] = [];

  // Only HOD+ roles can interact with receivings
  const hodPlusRoles = ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'];

  if (!hodPlusRoles.includes(role)) {
    return actions; // Empty for non-HOD roles
  }

  // All HOD+ can view history
  actions.push('view_receiving_history' as MicroAction);

  // Draft status: full edit capabilities
  if (status === 'draft') {
    actions.push('add_receiving_item' as MicroAction);
    actions.push('attach_receiving_image_with_comment' as MicroAction);
    actions.push('extract_receiving_candidates' as MicroAction);
    actions.push('update_receiving' as MicroAction);
    actions.push('accept_receiving' as MicroAction);
    actions.push('reject_receiving' as MicroAction);
  }

  // In review: can accept or reject
  if (status === 'in_review') {
    actions.push('accept_receiving' as MicroAction);
    actions.push('reject_receiving' as MicroAction);
  }

  // Accepted: can link to invoice, view history
  if (status === 'accepted') {
    actions.push('link_receiving_to_invoice' as MicroAction);
  }

  return actions;
}

export default function ContextPanel() {
  const { contextPanel, hideContext } = useSurface();
  const { user } = useAuth();
  const { visible, entityType, entityId, entityData } = contextPanel;

  // Entity type display names
  const entityTypeNames: Record<string, string> = {
    work_order: 'Work Order',
    equipment: 'Equipment',
    fault: 'Fault',
    part: 'Part',
    inventory: 'Inventory',
    purchase_order: 'Purchase Order',
    supplier: 'Supplier',
    document: 'Document',
    email_thread: 'Email Thread',
    receiving: 'Receiving',
  };

  const displayName = entityType ? entityTypeNames[entityType] || entityType : 'Details';

  /**
   * Render the appropriate entity card based on entityType
   * These cards call /v1/decisions for server-driven action visibility
   */
  const renderEntityCard = () => {
    if (!entityType || !entityId) return null;

    const data = entityData as Record<string, unknown> || {};

    switch (entityType) {
      case 'fault':
        // FaultCard expects specific props - map from entityData
        const faultData = {
          id: entityId,
          title: (data.title as string) || 'Fault',
          description: (data.description as string) || '',
          severity: (data.severity as 'low' | 'medium' | 'high' | 'critical') || 'medium',
          equipment_id: (data.equipment_id as string) || '',
          equipment_name: (data.equipment_name as string) || 'Unknown Equipment',
          reported_at: (data.reported_at as string) || (data.detected_at as string) || new Date().toISOString(),
          reporter: (data.reporter as string) || (data.reported_by as string) || 'System',
          ai_diagnosis: data.ai_diagnosis as { is_known: boolean } | undefined,
          has_work_order: (data.has_work_order as boolean) || false,
        };
        return (
          <div data-testid="context-panel-fault-card">
            <FaultCard
              fault={faultData}
              userRole={user?.role}
            />
          </div>
        );

      case 'work_order':
        const workOrderData = {
          id: entityId,
          title: (data.title as string) || 'Work Order',
          description: (data.description as string) || '',
          status: (data.status as 'pending' | 'in_progress' | 'completed' | 'cancelled') || 'pending',
          priority: (data.priority as 'low' | 'medium' | 'high' | 'urgent') || 'medium',
          equipment_id: data.equipment_id as string | undefined,
          equipment_name: data.equipment_name as string | undefined,
          assigned_to: data.assigned_to as string | undefined,
          assigned_to_name: data.assigned_to_name as string | undefined,
          created_at: (data.created_at as string) || new Date().toISOString(),
          completed_at: data.completed_at as string | undefined,
          due_date: data.due_date as string | undefined,
        };
        return (
          <div data-testid="context-panel-work-order-card">
            <WorkOrderCard workOrder={workOrderData} />
          </div>
        );

      case 'equipment':
        const equipmentData = {
          id: entityId,
          name: (data.name as string) || 'Equipment',
          equipment_type: (data.equipment_type as string) || (data.category as string) || 'General',
          manufacturer: data.manufacturer as string | undefined,
          model: data.model as string | undefined,
          serial_number: data.serial_number as string | undefined,
          location: (data.location as string) || 'Unknown',
          status: (data.status as 'operational' | 'faulty' | 'maintenance' | 'offline') || 'operational',
          installation_date: data.installation_date as string | undefined,
          last_maintenance: data.last_maintenance as string | undefined,
          next_maintenance: data.next_maintenance as string | undefined,
          fault_count: data.fault_count as number | undefined,
          work_order_count: data.work_order_count as number | undefined,
        };
        return (
          <div data-testid="context-panel-equipment-card">
            <EquipmentCard equipment={equipmentData} />
          </div>
        );

      case 'part':
      case 'inventory':
        const partData = {
          id: entityId,
          part_name: (data.name as string) || (data.part_name as string) || 'Part',
          part_number: (data.part_number as string) || '',
          stock_quantity: (data.quantity_on_hand as number) || (data.stock_quantity as number) || 0,
          min_stock_level: (data.minimum_quantity as number) || (data.min_stock_level as number) || 0,
          location: (data.location as string) || 'Unknown',
          unit_cost: data.unit_cost as number | undefined,
          supplier: data.supplier as string | undefined,
          category: data.category as string | undefined,
          last_counted_at: data.last_counted_at as string | undefined,
          last_counted_by: data.last_counted_by as string | undefined,
          unit: data.unit as string | undefined,
        };

        // Get available actions based on user role
        const partActions = getPartActions(user?.role || 'crew');

        return (
          <div data-testid={`context-panel-${entityType}-card`}>
            <PartCard
              part={partData}
              entityType={entityType as 'part' | 'inventory'}
              actions={partActions}
            />
          </div>
        );

      case 'receiving':
        const receivingData = {
          id: entityId,
          vendor_name: data.vendor_name as string | undefined,
          vendor_reference: data.vendor_reference as string | undefined,
          received_date: data.received_date as string | undefined,
          status: (data.status as 'draft' | 'in_review' | 'accepted' | 'rejected') || 'draft',
          total: data.total as number | undefined,
          currency: data.currency as string | undefined,
          notes: data.notes as string | undefined,
          received_by: data.received_by as string | undefined,
        };

        // Get available actions based on status and role
        const receivingActions = getReceivingActions(
          receivingData.status,
          user?.role || 'crew'
        );

        return (
          <div data-testid="context-panel-receiving-card">
            <ReceivingCard
              receiving={receivingData}
              actions={receivingActions}
            />
          </div>
        );

      default:
        // Generic display for unsupported entity types
        return (
          <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
            <h3 className="text-lg font-semibold text-white mb-2">
              {(data.title as string) || (data.name as string) || displayName}
            </h3>
            <p className="text-sm text-celeste-text-muted">
              {(data.subtitle as string) || (data.description as string) || 'Details unavailable'}
            </p>
            <p className="text-xs text-celeste-text-disabled mt-2">
              Entity type: {entityType} | ID: {entityId}
            </p>
          </div>
        );
    }
  };

  return (
    <div
      className={cn(
        'absolute inset-y-0 right-0 w-[520px] bg-celeste-black/95 border-l border-celeste-text-secondary/50',
        'flex flex-col',
        'transform transition-transform duration-300 ease-out z-[10001]',
        'backdrop-blur-sm shadow-2xl',
        visible ? 'translate-x-0' : 'translate-x-full'
      )}
      data-testid="context-panel"
      data-entity-type={entityType}
      data-entity-id={entityId}
    >
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between p-4 border-b border-celeste-text-secondary/50 relative z-50 bg-celeste-black/95">
        <div className="flex items-center gap-4">
          <button
            onClick={hideContext}
            className="relative z-50 p-2 hover:bg-celeste-bg-tertiary rounded-lg transition-colors pointer-events-auto cursor-pointer"
            aria-label="Close context panel"
            data-testid="close-context-panel"
            type="button"
          >
            <X className="w-5 h-5 text-celeste-text-muted pointer-events-none" />
          </button>
          <div>
            <span className="text-xs text-celeste-text-disabled uppercase tracking-wider">
              {displayName}
            </span>
            {entityId && (
              <p className="text-sm text-celeste-text-muted font-mono">
                {entityId.substring(0, 8)}...
              </p>
            )}
          </div>
        </div>
        <button
          onClick={hideContext}
          className="relative z-50 p-2 hover:bg-celeste-bg-tertiary rounded-lg transition-colors pointer-events-auto cursor-pointer"
          aria-label="Close panel"
          type="button"
        >
          <ChevronRight className="w-5 h-5 text-celeste-text-muted pointer-events-none" />
        </button>
      </div>

      {/* Content - Render actual entity cards */}
      <div className="flex-1 overflow-y-auto p-4" data-testid="context-panel-content">
        {visible && entityType && entityId ? (
          <div className="space-y-4">
            {/* Render the appropriate card component */}
            {renderEntityCard()}
          </div>
        ) : (
          <div className="text-center py-12" data-testid="context-panel-empty">
            <AlertCircle className="w-8 h-8 text-celeste-text-secondary mx-auto mb-3" />
            <p className="text-celeste-text-muted text-sm">
              Select an item to view details
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
