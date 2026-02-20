/**
 * CelesteOS Microaction Type Definitions
 *
 * These types define the structure of microactions, their side effects,
 * purpose clusters, and execution context.
 */

// Side effect classification for actions
export type SideEffectType = 'read_only' | 'mutation_light' | 'mutation_heavy';

// The 7 purpose clusters
export type PurposeCluster =
  | 'fix_something'      // 7 actions - Diagnose and resolve faults
  | 'do_maintenance'     // 16 actions - Execute planned maintenance
  | 'manage_equipment'   // 6 actions - Understand equipment state
  | 'control_inventory'  // 7 actions - Track and manage parts
  | 'communicate_status' // 9 actions - Transfer knowledge
  | 'comply_audit'       // 5 actions - Maintain compliance
  | 'procure_suppliers'; // 7 actions - Acquire parts

// Card types that can display actions
export type CardType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'handover'
  | 'document'
  | 'hor_table'
  | 'purchase'
  | 'checklist'
  | 'worklist'
  | 'fleet_summary'
  | 'smart_summary';

// Individual microaction definition
export interface MicroAction {
  action_name: string;
  label: string;
  cluster: PurposeCluster;
  card_types: CardType[];
  side_effect: SideEffectType;
  description: string;
  handler: string;
  requires_confirmation: boolean;
}

// Action execution context
export interface ActionContext {
  yacht_id: string;
  user_id: string;
  user_role: string;
  entity_id?: string;
  entity_type?: CardType;
  source_card?: CardType;
}

// Action execution result
export interface ActionResult<T = unknown> {
  success: boolean;
  action_name: string;
  data: T | null;
  error: ActionError | null;
  confirmation_required: boolean;
  confirmation_message?: string;
}

// Action error structure
export interface ActionError {
  code: 'NOT_FOUND' | 'FORBIDDEN' | 'VALIDATION_ERROR' | 'INTERNAL_ERROR' | 'CONFIRMATION_REQUIRED';
  message: string;
  details?: Record<string, unknown>;
}

// Action availability based on context
export interface AvailableAction {
  action_name: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'NAVIGATE';
  icon?: string;
  is_primary?: boolean;
  requires_signature?: boolean;
  disabled?: boolean;
  disabled_reason?: string;
}

// Action validation result
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

// Confirmation dialog configuration
export interface ConfirmationConfig {
  title: string;
  message: string;
  confirm_label: string;
  cancel_label: string;
  variant: 'default' | 'destructive' | 'warning';
}

// Action execution state (for hooks)
export interface ActionState {
  loading: boolean;
  error: ActionError | null;
  result: ActionResult | null;
  confirmation_pending: boolean;
}

// Trigger context for conditional action visibility
export interface TriggerContext {
  // Fault-specific context
  fault?: {
    id: string;
    code?: string;
    status?: 'open' | 'investigating' | 'resolved' | 'closed';
    acknowledged?: boolean;
    ai_diagnosis?: {
      is_known: boolean;
      diagnosis?: string;
      confidence?: number;
    };
    equipment_id?: string;
    has_work_order?: boolean;
  };

  // Equipment-specific context
  equipment?: {
    id: string;
    name?: string;
    has_manual?: boolean;
    predictive_maintenance_enabled?: boolean;
  };

  // Part-specific context
  part?: {
    id: string;
    name?: string;
    stock_level?: number;
    reorder_threshold?: number;
    is_out_of_stock?: boolean;
  };

  // Work order-specific context
  work_order?: {
    id: string;
    status?: 'open' | 'in_progress' | 'completed' | 'cancelled';
    has_checklist?: boolean;
    equipment_id?: string;
  };

  // Purchase-specific context
  purchase?: {
    id: string;
    status?: 'draft' | 'pending_approval' | 'approved' | 'ordered' | 'in_transit' | 'received';
  };

  // Handover-specific context
  handover?: {
    id?: string;
    exists?: boolean;
  };

  // User role for permission checks
  user_role?: string;

  // Environmental context
  environment?: 'at_sea' | 'port' | 'shipyard' | 'guest_trip';
}

