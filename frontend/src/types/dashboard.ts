// Dashboard-specific TypeScript types

export interface DashboardMetrics {
  total_equipment: number;
  active_work_orders: number;
  overdue_tasks: number;
  high_risk_systems: number;
  parts_low_stock: number;
  completed_this_week: number;
}

export interface EquipmentStatus {
  id: string;
  name: string;
  status: 'operational' | 'needs_attention' | 'critical' | 'offline';
  last_maintenance: string;
  next_maintenance: string;
  risk_score?: number;
}

export interface WorkOrderSummary {
  id: string;
  title: string;
  equipment_name?: string;
  priority: 'routine' | 'important' | 'critical';
  status: 'planned' | 'in_progress' | 'completed' | 'deferred' | 'cancelled';
  due_date?: string;
  assigned_to?: string;
}

export interface InventoryAlert {
  part_id: string;
  part_name: string;
  current_quantity: number;
  min_quantity: number;
  location: string;
  urgency: 'low' | 'medium' | 'high';
}

export interface PredictiveInsight {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  summary: string;
  contributing_factors: string[];
  recommended_actions: string[];
  trend: 'improving' | 'stable' | 'degrading';
}

export interface DashboardWidget {
  id: string;
  type: 'predictive' | 'work_orders' | 'equipment' | 'inventory' | 'custom';
  title: string;
  position: { x: number; y: number; w: number; h: number };
  config?: Record<string, any>;
}

export interface FleetComparison {
  yacht_id: string;
  yacht_name: string;
  metric_value: number;
  benchmark_value: number;
  variance_percent: number;
}

// Widget configurations
export interface WidgetConfig {
  refresh_interval?: number; // seconds
  show_trend?: boolean;
  max_items?: number;
  filters?: Record<string, any>;
}
