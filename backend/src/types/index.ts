// CelesteOS Backend Types
// Version: 1.0

// ============================================================================
// ENUMS
// ============================================================================

export type RiskLevel = 'normal' | 'monitor' | 'emerging' | 'high' | 'critical';
export type ActionStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
export type InsightType = 'threshold_alert' | 'pattern_detected' | 'trend_warning' | 'crew_frustration' | 'inventory_gap' | 'compliance_due';
export type SnapshotType = 'briefing' | 'legacy' | 'predictive';
export type Priority = 'low' | 'medium' | 'high' | 'critical';
export type WorkOrderType = 'scheduled' | 'corrective' | 'unplanned';
export type WorkOrderStatus = 'planned' | 'in_progress' | 'completed' | 'deferred' | 'cancelled';

// ============================================================================
// DATABASE ENTITIES
// ============================================================================

export interface Yacht {
  id: string;
  name: string;
  imo?: string;
  mmsi?: string;
  flag_state?: string;
  signature: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  yacht_id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Equipment {
  id: string;
  yacht_id: string;
  parent_id?: string;
  name: string;
  code?: string;
  description?: string;
  location?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  criticality?: string;
  system_type?: string;
  attention_flag?: boolean;
  attention_reason?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkOrder {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  title: string;
  description?: string;
  type: WorkOrderType;
  priority: Priority;
  status: WorkOrderStatus;
  due_date?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Fault {
  id: string;
  yacht_id: string;
  equipment_id: string;
  fault_code?: string;
  title: string;
  description?: string;
  severity: string;
  detected_at: string;
  resolved_at?: string;
  created_at: string;
}

export interface Part {
  id: string;
  yacht_id: string;
  name: string;
  part_number: string;
  manufacturer?: string;
  description?: string;
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface StockLevel {
  id: string;
  yacht_id: string;
  part_id: string;
  quantity: number;
  min_quantity: number;
  max_quantity?: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  yacht_id: string;
  source: string;
  filename: string;
  content_type?: string;
  size_bytes?: number;
  sha256: string;
  storage_path: string;
  indexed: boolean;
  created_at: string;
}

export interface Note {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  user_id?: string;
  note_text: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// PREDICTIVE TYPES
// ============================================================================

export interface PredictiveState {
  id: string;
  yacht_id: string;
  equipment_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  trend?: 'improving' | 'stable' | 'worsening';
  trend_delta?: number;
  contributing_factors: ContributingFactors;
  last_calculated_at: string;
  previous_risk_score?: number;
  created_at: string;
  updated_at: string;
}

export interface ContributingFactors {
  fault_signal: number;
  work_order_signal: number;
  notes_signal: number;
  corrective_signal: number;
  criticality_signal: number;
  fault_count: number;
  overdue_count: number;
  note_count: number;
  corrective_count: number;
}

export interface PredictiveInsight {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  insight_type: InsightType;
  title: string;
  description: string;
  recommendation?: string;
  severity?: string;
  metadata?: Record<string, unknown>;
  acknowledged: boolean;
  dismissed: boolean;
  created_at: string;
}

// ============================================================================
// DASHBOARD TYPES
// ============================================================================

export interface DashboardSnapshot {
  id: string;
  yacht_id: string;
  snapshot_type: SnapshotType;
  high_risk_equipment: HighRiskEquipmentItem[];
  risk_movements: RiskMovement[];
  unstable_systems: UnstableSystem[];
  patterns_7d: Pattern[];
  overdue_critical: OverdueWorkOrder[];
  inventory_gaps: InventoryGap[];
  inspections_due: InspectionDue[];
  crew_frustration: CrewFrustration[];
  summary_stats: SummaryStats;
  generated_at: string;
  valid_until?: string;
}

export interface HighRiskEquipmentItem {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  risk_level: RiskLevel;
  trend: string;
  system_type?: string;
  contributing_factors?: ContributingFactors;
}

export interface RiskMovement {
  equipment_id: string;
  equipment_name: string;
  current_score: number;
  previous_score: number;
  delta: number;
  direction: 'up' | 'down' | 'stable';
}

export interface UnstableSystem {
  equipment_id: string;
  equipment_name: string;
  fault_count_48h: number;
  note_count_48h: number;
  risk_score: number;
}

export interface Pattern {
  pattern_type: string;
  description: string;
  affected_equipment: string[];
  confidence: number;
}

export interface OverdueWorkOrder {
  work_order_id: string;
  title: string;
  equipment_id?: string;
  equipment_name?: string;
  due_date: string;
  days_overdue: number;
  priority: Priority;
}

export interface InventoryGap {
  part_id: string;
  part_name: string;
  current_qty: number;
  min_qty: number;
  shortage: number;
}

export interface InspectionDue {
  inspection_id: string;
  title: string;
  equipment_id?: string;
  equipment_name?: string;
  due_date: string;
  days_until: number;
}

export interface CrewFrustration {
  search_cluster: string;
  query_count: number;
  recent_queries: string[];
  potential_issue: string;
}

export interface SummaryStats {
  total_equipment: number;
  high_risk_count: number;
  overdue_wo_count: number;
  low_stock_count: number;
  active_faults: number;
  inspections_due_7d: number;
}

// ============================================================================
// LEGACY VIEW TYPES
// ============================================================================

export interface DashboardLegacyView {
  id: string;
  yacht_id: string;
  equipment_overview: EquipmentOverviewItem[];
  equipment_count: number;
  equipment_by_status: Record<string, number>;
  work_orders_overview: WorkOrderOverviewItem[];
  work_orders_count: number;
  work_orders_by_status: Record<string, number>;
  work_orders_overdue_count: number;
  inventory_overview: InventoryOverviewItem[];
  inventory_count: number;
  inventory_low_stock_count: number;
  certificates_overview: CertificateOverviewItem[];
  certificates_count: number;
  certificates_expiring_soon: number;
  fault_history: FaultHistoryItem[];
  faults_active_count: number;
  faults_resolved_30d: number;
  scheduled_maintenance: ScheduledMaintenanceItem[];
  maintenance_upcoming_7d: number;
  maintenance_overdue: number;
  parts_usage: PartUsageItem[];
  documents_summary: DocumentsSummary;
  documents_total: number;
  generated_at: string;
}

export interface EquipmentOverviewItem {
  id: string;
  name: string;
  system_type?: string;
  status: string;
  last_service?: string;
  risk_score?: number;
}

export interface WorkOrderOverviewItem {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_date?: string;
  equipment_name?: string;
}

export interface InventoryOverviewItem {
  id: string;
  name: string;
  part_number: string;
  quantity: number;
  min_quantity: number;
  status: 'ok' | 'low' | 'critical';
}

export interface CertificateOverviewItem {
  id: string;
  name: string;
  expiry_date: string;
  days_until_expiry: number;
  status: 'valid' | 'expiring' | 'expired';
}

export interface FaultHistoryItem {
  id: string;
  fault_code?: string;
  title: string;
  equipment_name?: string;
  severity: string;
  detected_at: string;
  resolved_at?: string;
}

export interface ScheduledMaintenanceItem {
  id: string;
  title: string;
  equipment_name?: string;
  due_date: string;
  frequency?: string;
  status: string;
}

export interface PartUsageItem {
  part_id: string;
  part_name: string;
  usage_30d: number;
  avg_monthly: number;
}

export interface DocumentsSummary {
  total: number;
  indexed: number;
  by_type: Record<string, number>;
}

// ============================================================================
// ACTION TYPES
// ============================================================================

export interface ActionExecuteRequest {
  action: string;
  context: {
    yacht_id: string;
    equipment_id?: string;
    work_order_id?: string;
    document_id?: string;
    [key: string]: unknown;
  };
  payload: Record<string, unknown>;
}

export interface ActionExecuteResponse {
  status: 'success' | 'error';
  action: string;
  result?: Record<string, unknown>;
  error?: string;
  error_code?: string;
}

export interface ActionLogEntry {
  id: string;
  yacht_id: string;
  user_id?: string;
  action_name: string;
  action_status: ActionStatus;
  request_payload: Record<string, unknown>;
  response_payload?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

// ============================================================================
// API RESPONSE TYPES
// ============================================================================

export interface DashboardBriefingResponse {
  risk_movements: RiskMovement[];
  high_risk_equipment: HighRiskEquipmentItem[];
  patterns_7d: Pattern[];
  unstable_systems: UnstableSystem[];
  inventory_gaps: InventoryGap[];
  overdue_critical: OverdueWorkOrder[];
  inspections_due: InspectionDue[];
  crew_frustration: CrewFrustration[];
  summary: SummaryStats;
  generated_at: string;
  cache_valid_until?: string;
}

export interface DashboardLegacyResponse {
  equipment: EquipmentOverviewItem[];
  work_orders: WorkOrderOverviewItem[];
  inventory: InventoryOverviewItem[];
  certificates: CertificateOverviewItem[];
  faults: FaultHistoryItem[];
  scheduled_maintenance: ScheduledMaintenanceItem[];
  parts: PartUsageItem[];
  documents: DocumentsSummary;
  counts: {
    equipment: number;
    work_orders: number;
    inventory: number;
    certificates: number;
    faults_active: number;
    maintenance_overdue: number;
  };
  generated_at: string;
}

export interface PredictiveStateResponse {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  risk_level: RiskLevel;
  trend: string;
  confidence: number;
  contributing_factors: ContributingFactors;
  last_calculated_at: string;
}

export interface PredictiveInsightResponse {
  id: string;
  insight_type: InsightType;
  title: string;
  description: string;
  recommendation?: string;
  severity?: string;
  equipment_id?: string;
  equipment_name?: string;
  acknowledged: boolean;
  created_at: string;
}

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface APIError {
  status: 'error';
  error_code: string;
  message: string;
}

export type ErrorCode =
  | 'missing_field'
  | 'invalid_field'
  | 'invalid_role'
  | 'yacht_mismatch'
  | 'schema_invalid'
  | 'workflow_failed'
  | 'not_found'
  | 'unauthorized'
  | 'forbidden'
  | 'internal_error';
