/**
 * Lens Data Types
 *
 * Shared type definitions for lens components and their sections.
 * These types define the data structures returned from the backend API
 * for each entity type.
 *
 * Per 1-URL philosophy: All lenses render inside ContextPanel at app.celeste7.ai
 */

// Import and re-export ShoppingListItemData
import type { ShoppingListItemData as _ShoppingListItemData } from '@/components/cards/ShoppingListCard';
export type ShoppingListItemData = _ShoppingListItemData;

// ===========================================================================
// Equipment Lens Types
// ===========================================================================

export interface EquipmentLensData {
  id: string;
  name: string;
  /** Status enum: active | inactive | maintenance */
  status: string;
  /** Physical location on the yacht, e.g. "Engine Room / Station 2" */
  location?: string;
  /** Manufacturer name */
  manufacturer?: string;
  /** Model number/name */
  model?: string;
  serial_number?: string;
  installation_date?: string;
  warranty_expiry?: string;
  running_hours?: number;
  risk_score?: number;
  created_at?: string;
  /** Linked faults (fetched separately for count + list display) */
  faults?: LinkedFault[];
  /** Count of open faults (may be denormalized for performance) */
  open_faults_count?: number;
  /** Linked work orders */
  work_orders?: LinkedWorkOrder[];
  /** Count of active work orders */
  active_wo_count?: number;
  /** Specification details */
  specifications?: EquipmentSpecification;
  /** Maintenance history entries */
  maintenance_history?: MaintenanceHistoryEntry[];
  /** Linked documents (manuals, certificates) */
  documents?: EquipmentDocument[];
  /** Running hours log entries (pms_equipment_hours_log) */
  hours_log?: HoursLogEntry[];
  /** Status change history (pms_equipment_status_log) */
  status_history?: StatusHistoryEntry[];
}

export interface LinkedFault {
  id: string;
  title?: string;
  fault_code?: string;
  severity: string;
  status: string;
  detected_at?: string;
}

export interface LinkedWorkOrder {
  id: string;
  title?: string;
  wo_number?: string;
  status: string;
  priority?: string;
  due_date?: string;
}

export interface EquipmentSpecification {
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  installation_date?: string;
  warranty_expiry?: string;
  running_hours?: number;
  equipment_type?: string;
  category?: string;
}

export interface MaintenanceHistoryEntry {
  id: string;
  action: string;
  performed_at: string;
  performed_by?: string;
  work_order_id?: string;
  notes?: string;
}

export interface EquipmentDocument {
  id: string;
  title: string;
  document_type?: string;
  file_url?: string;
  uploaded_at?: string;
}

export interface HoursLogEntry {
  id: string;
  recorded_at: string;
  hours: number;
  recorded_by?: string;
}

export interface StatusHistoryEntry {
  id: string;
  old_status?: string;
  new_status: string;
  changed_at: string;
  changed_by?: string;
  reason?: string;
  work_order_id?: string;
  fault_id?: string;
}

// ===========================================================================
// Fault Lens Types
// ===========================================================================

export interface FaultLensData {
  id: string;
  /** System fault code e.g. "FLT-2026-000001" — NEVER show raw id UUID */
  fault_code?: string;
  /** Short fault title */
  title?: string;
  /** Detailed fault description */
  description?: string;
  /** Severity: cosmetic | minor | major | critical | safety */
  severity: string;
  /** Status: open | work_ordered | resolved | closed */
  status?: string;
  /** acknowledged_at: non-null when fault has been acknowledged */
  acknowledged_at?: string;
  /** FK to pms_equipment */
  equipment_id?: string;
  /** Denormalized equipment name for display */
  equipment_name?: string;
  /** ISO timestamp when fault was detected */
  detected_at?: string;
  /** ISO timestamp of record creation */
  created_at: string;
  /** ISO timestamp when fault was resolved (null = still open) */
  resolved_at?: string;
  /** User who reported (name string from metadata or denormalized join) */
  reporter_name?: string;
  /** Computed: days since detected_at */
  days_open?: number;
  /** Whether a work order has been raised from this fault */
  has_work_order?: boolean;
  /** Notes attached to the fault */
  notes?: WorkOrderNote[];
  /** Audit log entries */
  history?: AuditLogEntry[];
  /** Photo attachments */
  photos?: FaultPhoto[];
}

export interface FaultPhoto {
  id: string;
  storage_path: string;
  caption?: string;
  created_at: string;
  mime_type?: string;
  file_name?: string;
  file_size?: number;
}

// ===========================================================================
// Handover Lens Types
// ===========================================================================

export type HandoverStatus =
  | 'draft'
  | 'pending_signatures'
  | 'complete';

export type HandoverItemEntityType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'document'
  | 'note';

export interface HandoverItem {
  id: string;
  summary: string;
  section?: string;
  is_critical?: boolean;
  requires_action?: boolean;
  category?: 'fyi' | 'action_required' | 'critical' | 'resolved';
  entity_type: HandoverItemEntityType;
  entity_id: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  created_at: string;
  added_by?: string;
  risk_tags?: string[];
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  status?: 'pending' | 'acknowledged' | 'actioned' | 'closed';
}

export interface HandoverExport {
  id: string;
  export_date: string;
  department?: string;
  file_url?: string;
  outgoing_user_id?: string;
  outgoing_user_name?: string;
  outgoing_signed_at?: string;
  incoming_user_id?: string;
  incoming_user_name?: string;
  incoming_signed_at?: string;
  signoff_complete?: boolean;
}

export interface HandoverSignature {
  user_id: string;
  user_name: string;
  signed_at: string;
  role: 'outgoing' | 'incoming';
}

export interface HandoverLensData {
  id: string;
  /** Handover title for display — never show raw UUID */
  title: string;
  /** Status enum: draft | pending_signatures | complete */
  status: HandoverStatus;
  /** Outgoing crew member name */
  outgoing_crew_name?: string;
  /** Outgoing crew member user ID */
  outgoing_crew_id?: string;
  /** Incoming crew member name */
  incoming_crew_name?: string;
  /** Incoming crew member user ID */
  incoming_crew_id?: string;
  /** Handover items */
  items?: HandoverItem[];
  /** Exports with signature tracking */
  exports?: HandoverExport[];
  /** Outgoing signature record */
  outgoing_signature?: HandoverSignature;
  /** Incoming signature record */
  incoming_signature?: HandoverSignature;
  /** ISO timestamp of creation */
  created_at?: string;
  /** ISO timestamp of finalization */
  finalized_at?: string;
  /** ISO timestamp of completion */
  completed_at?: string;
}

// ===========================================================================
// Hours of Rest Lens Types
// ===========================================================================

export interface RestPeriod {
  /** Start time as "HH:MM" (24-hour) */
  start: string;
  /** End time as "HH:MM" (24-hour) */
  end: string;
  /** Duration in hours */
  hours: number;
}

export interface DailyLogEntry {
  id: string;
  /** ISO date: "2026-02-01" */
  record_date: string;
  /** Array of rest periods logged for this day */
  rest_periods: RestPeriod[];
  /** Total rest hours for the day */
  total_rest_hours: number;
  /**
   * Compliance status for this day.
   * compliant = meets minimum, warning = close to threshold, violation = STCW breach
   */
  compliance_status: 'compliant' | 'warning' | 'violation';
}

export interface HorWarning {
  id: string;
  /** ISO date when the warning was raised */
  warning_date: string;
  /** Human-readable violation description */
  description: string;
  /** Severity of the STCW violation */
  severity: 'warning' | 'violation';
  /** Whether the crew member has acknowledged this warning */
  acknowledged_at?: string;
  /** Who acknowledged it */
  acknowledged_by?: string;
}

export interface MonthlySignOff {
  id: string;
  /** "YYYY-MM" — e.g., "2026-02" */
  month: string;
  /** Department: "deck" | "engine" | "interior" */
  department: string;
  /** Whether the crew member has signed */
  crew_signed_at?: string;
  /** Whether the HOD has signed */
  hod_signed_at?: string;
  /** Whether the captain has countersigned */
  captain_signed_at?: string;
  /** Overall sign-off status */
  status: 'pending' | 'crew_signed' | 'hod_signed' | 'captain_signed' | 'complete';
}

export interface HoursOfRestLensData {
  id: string;
  /** Crew member UUID */
  user_id: string;
  /** Display name of the crew member */
  crew_name: string;
  /** Department: "deck" | "engine" | "interior" */
  department?: string;
  /**
   * Compliance status for the displayed period.
   * compliant = all days OK, warning = close to threshold, violation = STCW breach
   */
  compliance_status: 'compliant' | 'warning' | 'violation';
  /** Period start — ISO date "2026-02-01" */
  period_start: string;
  /** Period end — ISO date "2026-02-28" */
  period_end: string;
  /** Number of STCW violation days in the period */
  violations_count: number;
  /** Whether the current month has been signed off */
  monthly_signoff_complete?: boolean;
  /** Daily log entries for the period */
  daily_logs?: DailyLogEntry[];
  /** Warnings/violations raised during this period */
  warnings?: HorWarning[];
  /** Monthly sign-off records */
  signoffs?: MonthlySignOff[];
}

// ===========================================================================
// Shopping List Lens Types
// ===========================================================================

export interface ShoppingListAuditEntry {
  id: string;
  action: string;
  actor_name?: string;
  actor_id?: string;
  timestamp: string;
  details?: string;
  /** Item name affected (for per-item actions) */
  item_name?: string;
}

export interface ShoppingListLensData {
  id: string;
  /** Human-readable title e.g. "Monthly Engine Room Restock" */
  title?: string;
  /** Status: pending | approved | rejected | ordered */
  status: string;
  /** Crew member who created the shopping list */
  requester_name?: string;
  requester_id?: string;
  /** HOD who approved/rejected the list, or null if pending */
  approver_name?: string;
  approver_id?: string;
  /** ISO timestamp of record creation */
  created_at: string;
  /** ISO timestamp of most recent approval action */
  approved_at?: string;
  /** List items (per-item approval workflow) */
  items?: ShoppingListItemData[];
  /** Audit log entries for the shopping list */
  history?: ShoppingListAuditEntry[];
}


// ===========================================================================
// Shared Types (used across multiple lenses)
// ===========================================================================

export interface WorkOrderNote {
  id: string;
  text: string;
  created_at: string;
  author_name?: string;
  author_id?: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  timestamp: string;
  actor_name?: string;
  actor_id?: string;
  old_value?: string;
  new_value?: string;
  details?: string;
}
