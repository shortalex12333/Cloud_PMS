// Dashboard-specific types for CelesteOS HOD Interface

export interface DashboardData {
  riskOverview: RiskOverviewData
  workOrders: WorkOrdersData
  inventory: InventoryData
  faults: FaultsData
  upcomingTasks: UpcomingTasksData
  fleet?: FleetData
}

// Risk Overview Widget Types
export interface RiskOverviewData {
  topRisks: RiskItem[]
  overallTrend: 'improving' | 'stable' | 'worsening'
  lastUpdated: string
}

export interface RiskItem {
  equipment_id: string
  equipment_name: string
  system_type: string
  risk_score: number // 0.0 - 1.0
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  trend: 'up' | 'down' | 'stable'
  contributing_factors: string[]
  last_issue?: string
  last_issue_date?: string
}

// Work Orders Widget Types
export interface WorkOrdersData {
  overdue_count: number
  due_this_week: number
  high_priority: number
  recent_overdue: WorkOrderItem[]
}

export interface WorkOrderItem {
  id: string
  title: string
  equipment_name?: string
  equipment_id?: string
  days_overdue?: number
  priority: 'routine' | 'important' | 'critical'
  due_date?: string
  status: string
}

// Inventory Widget Types
export interface InventoryData {
  low_stock_count: number
  critical_items: InventoryItem[]
}

export interface InventoryItem {
  id: string
  part_name: string
  part_number: string
  system: string
  current_qty: number
  min_qty: number
  location?: string
  criticality: 'low' | 'medium' | 'high'
}

// Faults Widget Types
export interface FaultsData {
  last_7_days: number
  last_30_days: number
  critical_count: number
  recent_critical: FaultItem[]
  repeating_faults: FaultItem[]
}

export interface FaultItem {
  id: string
  fault_code?: string
  equipment_name: string
  equipment_id: string
  title: string
  severity: 'low' | 'medium' | 'high'
  detected_at: string
  resolved: boolean
  occurrences?: number
}

// Upcoming Tasks Widget Types
export interface UpcomingTasksData {
  tasks: UpcomingTaskItem[]
  total_count: number
}

export interface UpcomingTaskItem {
  id: string
  title: string
  equipment_name?: string
  equipment_id?: string
  due_date: string
  days_until_due: number
  type: 'scheduled' | 'corrective' | 'inspection'
  priority: string
}

// Fleet Widget Types (Optional - for multi-yacht)
export interface FleetData {
  yacht_count: number
  comparisons: FleetComparison[]
  alerts: FleetAlert[]
}

export interface FleetComparison {
  metric: string
  this_yacht: number
  fleet_average: number
  ranking?: number
}

export interface FleetAlert {
  id: string
  message: string
  severity: 'info' | 'warning' | 'critical'
  date: string
}

// Widget Props Types
export interface WidgetProps {
  className?: string
  onNavigateToSearch?: (query: string) => void
}

export interface RiskOverviewWidgetProps extends WidgetProps {
  data: RiskOverviewData | null
  loading?: boolean
}

export interface WorkOrdersWidgetProps extends WidgetProps {
  data: WorkOrdersData | null
  loading?: boolean
}

export interface InventoryWidgetProps extends WidgetProps {
  data: InventoryData | null
  loading?: boolean
}

export interface FaultsWidgetProps extends WidgetProps {
  data: FaultsData | null
  loading?: boolean
}

export interface UpcomingTasksWidgetProps extends WidgetProps {
  data: UpcomingTasksData | null
  loading?: boolean
}

export interface FleetWidgetProps extends WidgetProps {
  data: FleetData | null
  loading?: boolean
}
