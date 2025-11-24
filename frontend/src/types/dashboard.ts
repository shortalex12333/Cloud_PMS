// Dashboard briefing data types

export interface RiskMovement {
  id: string;
  equipment_name: string;
  risk_delta: number;
  current_risk: number;
  reason: string;
}

export interface HighRiskEquipment {
  id: string;
  name: string;
  risk_score: number;
  category: string;
  last_service: string;
  reason: string;
}

export interface Pattern {
  id: string;
  pattern_type: string;
  description: string;
  occurrences: number;
  affected_items: string[];
  trend: "increasing" | "stable" | "decreasing";
}

export interface UnstableSystem {
  id: string;
  name: string;
  stability_score: number;
  fault_count_48h: number;
  reason: string;
}

export interface InventoryGap {
  id: string;
  part_name: string;
  current_stock: number;
  minimum_required: number;
  deficit: number;
  criticality: "low" | "medium" | "high" | "critical";
}

export interface OverdueCritical {
  id: string;
  work_order_id: string;
  title: string;
  equipment_name: string;
  days_overdue: number;
  priority: "low" | "medium" | "high" | "critical";
}

export interface InspectionDue {
  id: string;
  name: string;
  equipment_name: string;
  due_date: string;
  days_until_due: number;
  type: string;
}

export interface CrewSignal {
  id: string;
  signal_type: string;
  description: string;
  frequency: number;
  department: string;
}

// Legacy panel data types
export interface LegacyEquipment {
  id: string;
  name: string;
  category: string;
  status: "operational" | "maintenance" | "offline";
  last_service: string;
}

export interface LegacyWorkOrder {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "completed";
  priority: "low" | "medium" | "high" | "critical";
  equipment_name: string;
  due_date: string;
}

export interface LegacyInventoryItem {
  id: string;
  name: string;
  quantity: number;
  location: string;
  category: string;
}

export interface LegacyCertificate {
  id: string;
  name: string;
  expiry_date: string;
  status: "valid" | "expiring" | "expired";
  authority: string;
}

export interface LegacyFault {
  id: string;
  code: string;
  equipment_name: string;
  description: string;
  date: string;
  severity: "low" | "medium" | "high" | "critical";
}

export interface LegacyNote {
  id: string;
  title: string;
  author: string;
  date: string;
  category: string;
}

export interface LegacyMaintenance {
  id: string;
  name: string;
  equipment_name: string;
  schedule: string;
  next_due: string;
}

export interface LegacySparePart {
  id: string;
  name: string;
  part_number: string;
  quantity: number;
  equipment_compatible: string[];
}

export interface LegacyDocument {
  id: string;
  name: string;
  type: string;
  last_updated: string;
  category: string;
}

export interface LegacyData {
  equipment: LegacyEquipment[];
  work_orders: LegacyWorkOrder[];
  inventory: LegacyInventoryItem[];
  certificates: LegacyCertificate[];
  faults: LegacyFault[];
  notes: LegacyNote[];
  scheduled_maintenance: LegacyMaintenance[];
  spare_parts: LegacySparePart[];
  documents: LegacyDocument[];
}

export interface DashboardBriefing {
  risk_movements: RiskMovement[];
  high_risk_equipment: HighRiskEquipment[];
  patterns_7d: Pattern[];
  unstable_systems: UnstableSystem[];
  inventory_gaps: InventoryGap[];
  overdue_critical: OverdueCritical[];
  inspections_due: InspectionDue[];
  crew_signals: CrewSignal[];
  legacy: LegacyData;
}

// Card configuration for intelligence cards
export interface IntelligenceCardConfig {
  id: string;
  title: string;
  icon: string;
  dataKey: keyof Omit<DashboardBriefing, "legacy">;
  searchQuery: string;
  countExtractor: (data: DashboardBriefing) => number;
  trendExtractor?: (data: DashboardBriefing) => string;
  topItemsExtractor: (data: DashboardBriefing) => { name: string; metric: string; reason: string }[];
}
