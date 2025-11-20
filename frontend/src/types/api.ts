// API Request/Response Types for CelesteOS

export interface APIResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginationParams {
  page?: number
  limit?: number
  offset?: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  hasMore: boolean
}

// Search API Types
export interface SearchRequest {
  query: string
  partial?: boolean
  filters?: SearchFilters
}

export interface SearchFilters {
  equipment_id?: string
  document_type?: string
  fault_code?: string
  date_from?: string
  date_to?: string
}

export interface SearchResponse {
  intent: string
  entities: Record<string, any>
  cards: SearchResultCard[]
  actions: MicroAction[]
  confidence: number
}

export interface SearchResultCard {
  type: 'document' | 'fault' | 'work_order' | 'part' | 'predictive' | 'equipment'
  id: string
  title: string
  preview?: string
  metadata?: Record<string, any>
  actions?: string[]
}

export interface MicroAction {
  id: string
  label: string
  action: string
  icon?: string
  primary?: boolean
}

// Dashboard API Types
export interface DashboardSummary {
  risk_overview: RiskOverview
  work_orders: WorkOrderSummary
  inventory: InventorySummary
  faults: FaultsSummary
  upcoming_tasks: UpcomingTask[]
}

export interface RiskOverview {
  high_risk_equipment: HighRiskEquipment[]
  overall_risk_level: 'low' | 'medium' | 'high' | 'critical'
  trending: 'improving' | 'stable' | 'worsening'
}

export interface HighRiskEquipment {
  equipment_id: string
  equipment_name: string
  system_type: string
  risk_score: number
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  trend: 'up' | 'down' | 'stable'
  contributing_factors: string[]
  last_issue?: string
  last_issue_date?: string
}

export interface WorkOrderSummary {
  overdue: number
  due_this_week: number
  high_priority: number
  recent_overdue: WorkOrderPreview[]
}

export interface WorkOrderPreview {
  id: string
  title: string
  equipment_name?: string
  days_overdue?: number
  priority: string
  due_date?: string
}

export interface InventorySummary {
  low_stock_count: number
  critical_parts: PartPreview[]
}

export interface PartPreview {
  id: string
  name: string
  part_number: string
  system: string
  current_qty: number
  min_qty: number
  location?: string
}

export interface FaultsSummary {
  last_7_days: number
  last_30_days: number
  critical_count: number
  recent_faults: FaultPreview[]
}

export interface FaultPreview {
  id: string
  fault_code?: string
  equipment_name: string
  title: string
  severity: string
  detected_at: string
  resolved: boolean
}

export interface UpcomingTask {
  id: string
  title: string
  equipment_name?: string
  due_date: string
  days_until_due: number
  type: string
}

// Predictive API Types
export interface PredictiveState {
  equipment_id: string
  equipment_name: string
  risk_score: number
  risk_level: string
  trend: string
  last_updated: string
  insights: string[]
}

export interface PredictiveInsightsRequest {
  equipment_id?: string
  limit?: number
}

export interface PredictiveInsightsResponse {
  insights: PredictiveState[]
  summary: string
}
