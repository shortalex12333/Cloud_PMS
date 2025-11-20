// Mock data for dashboard - TODO: Replace with real API calls

import {
  RiskOverviewData,
  WorkOrdersData,
  InventoryData,
  FaultsData,
  UpcomingTasksData,
  FleetData,
} from '@/types/dashboard'

// Mock Risk Overview Data
export const mockRiskOverviewData: RiskOverviewData = {
  topRisks: [
    {
      equipment_id: '1',
      equipment_name: 'HVAC Compressor #2',
      system_type: 'HVAC',
      risk_score: 0.82,
      risk_level: 'high',
      trend: 'up',
      contributing_factors: ['Repeated high-pressure faults', 'Overdue maintenance'],
      last_issue: 'High pressure alarm',
      last_issue_date: '2025-11-18',
    },
    {
      equipment_id: '2',
      equipment_name: 'Port Generator',
      system_type: 'Power Generation',
      risk_score: 0.74,
      risk_level: 'high',
      trend: 'stable',
      contributing_factors: ['Coolant temperature rising', 'Increased crew searches'],
      last_issue: 'Temperature spike',
      last_issue_date: '2025-11-17',
    },
    {
      equipment_id: '3',
      equipment_name: 'Stabilizer Pump',
      system_type: 'Stabilization',
      risk_score: 0.68,
      risk_level: 'medium',
      trend: 'down',
      contributing_factors: ['Recent seal replacement', 'Vibration detected'],
      last_issue: 'Leak detected',
      last_issue_date: '2025-11-15',
    },
    {
      equipment_id: '4',
      equipment_name: 'Main Engine Starboard',
      system_type: 'Propulsion',
      risk_score: 0.56,
      risk_level: 'medium',
      trend: 'stable',
      contributing_factors: ['Hours approaching service interval'],
      last_issue: undefined,
      last_issue_date: undefined,
    },
  ],
  overallTrend: 'worsening',
  lastUpdated: new Date().toISOString(),
}

// Mock Work Orders Data
export const mockWorkOrdersData: WorkOrdersData = {
  overdue_count: 8,
  due_this_week: 12,
  high_priority: 5,
  recent_overdue: [
    {
      id: 'wo-1',
      title: 'Replace HVAC air filters',
      equipment_name: 'HVAC System',
      days_overdue: 5,
      priority: 'important',
      status: 'planned',
    },
    {
      id: 'wo-2',
      title: 'Generator coolant flush',
      equipment_name: 'Port Generator',
      days_overdue: 3,
      priority: 'critical',
      status: 'planned',
    },
    {
      id: 'wo-3',
      title: 'Stabilizer hydraulic inspection',
      equipment_name: 'Stabilizer System',
      days_overdue: 2,
      priority: 'important',
      status: 'in_progress',
    },
    {
      id: 'wo-4',
      title: 'Fire suppression system test',
      equipment_name: 'Safety Systems',
      days_overdue: 1,
      priority: 'critical',
      status: 'planned',
    },
  ],
}

// Mock Inventory Data
export const mockInventoryData: InventoryData = {
  low_stock_count: 12,
  critical_items: [
    {
      id: 'part-1',
      part_name: 'Racor 2040 Fuel Filter',
      part_number: '2040N2',
      system: 'Fuel System',
      current_qty: 2,
      min_qty: 4,
      location: 'Engine Room Locker A',
      criticality: 'high',
    },
    {
      id: 'part-2',
      part_name: 'Generator Coolant',
      part_number: 'MTU-COOL-5L',
      system: 'Cooling System',
      current_qty: 3,
      min_qty: 8,
      location: 'Engine Room Storage',
      criticality: 'high',
    },
    {
      id: 'part-3',
      part_name: 'HVAC Compressor Seal Kit',
      part_number: 'HVAC-SEAL-01',
      system: 'HVAC',
      current_qty: 0,
      min_qty: 2,
      location: 'Not Stocked',
      criticality: 'medium',
    },
    {
      id: 'part-4',
      part_name: 'Hydraulic Oil (20L)',
      part_number: 'HYD-OIL-20',
      system: 'Hydraulic System',
      current_qty: 1,
      min_qty: 3,
      location: 'Aft Deck Storage',
      criticality: 'medium',
    },
  ],
}

// Mock Faults Data
export const mockFaultsData: FaultsData = {
  last_7_days: 14,
  last_30_days: 47,
  critical_count: 3,
  recent_critical: [
    {
      id: 'fault-1',
      fault_code: 'E047',
      equipment_name: 'Port Generator',
      equipment_id: '2',
      title: 'Coolant temperature high',
      severity: 'high',
      detected_at: '2025-11-19T08:30:00Z',
      resolved: false,
    },
    {
      id: 'fault-2',
      fault_code: 'P0128',
      equipment_name: 'HVAC Compressor #2',
      equipment_id: '1',
      title: 'High pressure alarm',
      severity: 'high',
      detected_at: '2025-11-18T14:15:00Z',
      resolved: true,
    },
    {
      id: 'fault-3',
      equipment_name: 'Stabilizer System',
      equipment_id: '3',
      title: 'Hydraulic pressure low',
      severity: 'medium',
      detected_at: '2025-11-17T10:45:00Z',
      resolved: false,
    },
  ],
  repeating_faults: [
    {
      id: 'fault-4',
      fault_code: 'E047',
      equipment_name: 'Port Generator',
      equipment_id: '2',
      title: 'Coolant temperature high',
      severity: 'high',
      detected_at: '2025-11-19T08:30:00Z',
      resolved: false,
      occurrences: 4,
    },
    {
      id: 'fault-5',
      equipment_name: 'Black Water Tank',
      equipment_id: '5',
      title: 'Level sensor fault',
      severity: 'medium',
      detected_at: '2025-11-16T09:00:00Z',
      resolved: false,
      occurrences: 3,
    },
  ],
}

// Mock Upcoming Tasks Data
export const mockUpcomingTasksData: UpcomingTasksData = {
  tasks: [
    {
      id: 'task-1',
      title: 'Fire suppression system test',
      equipment_name: 'Safety Systems',
      due_date: '2025-11-21',
      days_until_due: 1,
      type: 'scheduled',
      priority: 'critical',
    },
    {
      id: 'task-2',
      title: 'Generator coolant flush',
      equipment_name: 'Port Generator',
      due_date: '2025-11-22',
      days_until_due: 2,
      type: 'corrective',
      priority: 'important',
    },
    {
      id: 'task-3',
      title: 'HVAC filter replacement',
      equipment_name: 'HVAC System',
      due_date: '2025-11-24',
      days_until_due: 4,
      type: 'scheduled',
      priority: 'routine',
    },
    {
      id: 'task-4',
      title: 'Stabilizer annual inspection',
      equipment_name: 'Stabilizer System',
      due_date: '2025-11-26',
      days_until_due: 6,
      type: 'inspection',
      priority: 'important',
    },
    {
      id: 'task-5',
      title: 'Main engine oil analysis',
      equipment_name: 'Main Engine Starboard',
      due_date: '2025-12-01',
      days_until_due: 11,
      type: 'scheduled',
      priority: 'routine',
    },
  ],
  total_count: 18,
}

// Mock Fleet Data (Optional)
export const mockFleetData: FleetData = {
  yacht_count: 24,
  comparisons: [
    {
      metric: 'HVAC Faults',
      this_yacht: 12,
      fleet_average: 7,
      ranking: 18,
    },
    {
      metric: 'Generator Runtime Hours',
      this_yacht: 850,
      fleet_average: 920,
      ranking: 10,
    },
    {
      metric: 'Work Order Completion Rate',
      this_yacht: 94,
      fleet_average: 88,
      ranking: 5,
    },
  ],
  alerts: [
    {
      id: 'alert-1',
      message: 'Your yacht shows 2.1x more HVAC pressure faults than fleet average',
      severity: 'warning',
      date: '2025-11-18',
    },
  ],
}
