/**
 * CelesteOS Dashboard Data Hook
 *
 * Fetches and manages data for all Control Center modules.
 * Provides real-time updates and caching for dashboard widgets.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { getYachtId, getYachtSignature } from '@/lib/authHelpers';
import { ensureFreshToken } from '@/lib/tokenRefresh';

// ============================================================================
// TYPES
// ============================================================================

export interface WorkOrderSummary {
  id: string;
  title: string;
  equipment: string;
  dueDate: string;
  priority: 'routine' | 'important' | 'critical';
  status: 'scheduled' | 'in_progress' | 'overdue' | 'completed';
}

export interface WorkOrderStats {
  total: number;
  completed: number;
  inProgress: number;
  overdue: number;
}

export interface FaultSummary {
  id: string;
  code: string;
  title: string;
  equipment: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'investigating' | 'resolved';
  timestamp: string;
}

export interface FaultStats {
  total: number;
  open: number;
  investigating: number;
  resolved: number;
  critical: number;
}

export interface EquipmentStatus {
  id: string;
  name: string;
  system: string;
  status: 'operational' | 'degraded' | 'offline' | 'maintenance';
  lastChecked: string;
  runningHours?: number;
}

export interface EquipmentStats {
  total: number;
  operational: number;
  degraded: number;
  offline: number;
  maintenance: number;
}

export interface InventoryItem {
  id: string;
  partNumber: string;
  name: string;
  quantity: number;
  minStock: number;
  location: string;
  status: 'healthy' | 'low' | 'critical' | 'out_of_stock';
}

export interface InventoryStats {
  totalParts: number;
  lowStock: number;
  outOfStock: number;
  pendingOrders: number;
}

export interface CrewNote {
  id: string;
  author: string;
  content: string;
  timestamp: string;
  type: 'observation' | 'concern' | 'recommendation';
  status: 'new' | 'reviewed' | 'actioned';
}

export interface PredictiveRisk {
  id: string;
  equipment: string;
  riskType: string;
  probability: number;
  impact: 'low' | 'medium' | 'high' | 'critical';
  recommendation: string;
  timeframe: string;
}

export interface ExpiringDocument {
  id: string;
  name: string;
  type: 'certificate' | 'survey' | 'license' | 'permit';
  expiryDate: string;
  daysUntil: number;
  status: 'valid' | 'expiring' | 'critical' | 'expired';
}

export interface DocumentStats {
  total: number;
  valid: number;
  expiringSoon: number;
  expired: number;
}

export interface HandoverSection {
  name: string;
  items: number;
  complete: boolean;
}

export interface HandoverStatus {
  status: 'draft' | 'ready' | 'submitted';
  lastUpdated: string;
  sections: HandoverSection[];
  nextHandover: string;
  assignedTo: string;
}

export interface DashboardData {
  workOrders: {
    items: WorkOrderSummary[];
    stats: WorkOrderStats;
  };
  faults: {
    items: FaultSummary[];
    stats: FaultStats;
  };
  equipment: {
    items: EquipmentStatus[];
    stats: EquipmentStats;
  };
  inventory: {
    items: InventoryItem[];
    stats: InventoryStats;
  };
  crewNotes: CrewNote[];
  predictiveRisks: PredictiveRisk[];
  documents: {
    items: ExpiringDocument[];
    stats: DocumentStats;
  };
  handover: HandoverStatus;
}

interface DashboardState {
  data: DashboardData | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

// ============================================================================
// API HELPERS
// ============================================================================

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

async function fetchDashboardEndpoint<T>(endpoint: string): Promise<T> {
  const jwt = await ensureFreshToken();
  const yachtId = await getYachtId();
  const yachtSignature = await getYachtSignature(yachtId);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${endpoint}: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// MOCK DATA GENERATORS (Used when API is unavailable)
// ============================================================================

function generateMockWorkOrders(): { items: WorkOrderSummary[]; stats: WorkOrderStats } {
  return {
    items: [
      {
        id: 'WO-2024-0847',
        title: 'Generator Coolant Flush',
        equipment: 'Main Generator #1',
        dueDate: '3 days',
        priority: 'routine',
        status: 'scheduled',
      },
      {
        id: 'WO-2024-0852',
        title: 'Stabiliser Hydraulic Check',
        equipment: 'Port Stabiliser',
        dueDate: 'Today',
        priority: 'important',
        status: 'in_progress',
      },
      {
        id: 'WO-2024-0849',
        title: 'AC Filter Replacement',
        equipment: 'HVAC System',
        dueDate: 'Overdue 2d',
        priority: 'critical',
        status: 'overdue',
      },
    ],
    stats: {
      total: 24,
      completed: 18,
      inProgress: 4,
      overdue: 2,
    },
  };
}

function generateMockFaults(): { items: FaultSummary[]; stats: FaultStats } {
  return {
    items: [
      {
        id: 'F-2847',
        code: 'E-2847',
        title: 'Generator Overheating Alert',
        equipment: 'Main Generator #1',
        severity: 'critical',
        status: 'investigating',
        timestamp: '2h ago',
      },
      {
        id: 'F-2843',
        code: 'H-1234',
        title: 'Low Hydraulic Pressure',
        equipment: 'Port Stabiliser',
        severity: 'high',
        status: 'open',
        timestamp: '5h ago',
      },
    ],
    stats: {
      total: 12,
      open: 5,
      investigating: 2,
      resolved: 5,
      critical: 1,
    },
  };
}

function generateMockEquipment(): { items: EquipmentStatus[]; stats: EquipmentStats } {
  return {
    items: [
      {
        id: 'EQ-001',
        name: 'Main Generator #1',
        system: 'Power',
        status: 'degraded',
        lastChecked: '2h ago',
        runningHours: 12450,
      },
      {
        id: 'EQ-002',
        name: 'Port Stabiliser',
        system: 'Stabilisation',
        status: 'operational',
        lastChecked: '1h ago',
        runningHours: 8230,
      },
      {
        id: 'EQ-003',
        name: 'HVAC Unit #1',
        system: 'Climate',
        status: 'maintenance',
        lastChecked: '30m ago',
      },
    ],
    stats: {
      total: 156,
      operational: 142,
      degraded: 8,
      offline: 2,
      maintenance: 4,
    },
  };
}

function generateMockInventory(): { items: InventoryItem[]; stats: InventoryStats } {
  return {
    items: [
      {
        id: 'P-3512-B',
        partNumber: '3512-B',
        name: 'Coolant Temperature Sensor',
        quantity: 2,
        minStock: 3,
        location: 'A4-12',
        status: 'low',
      },
      {
        id: 'P-7892-A',
        partNumber: '7892-A',
        name: 'Hydraulic Filter Element',
        quantity: 0,
        minStock: 2,
        location: 'B2-08',
        status: 'out_of_stock',
      },
      {
        id: 'P-1234-C',
        partNumber: '1234-C',
        name: 'Air Filter - HVAC',
        quantity: 6,
        minStock: 4,
        location: 'C1-15',
        status: 'healthy',
      },
    ],
    stats: {
      totalParts: 1247,
      lowStock: 23,
      outOfStock: 4,
      pendingOrders: 8,
    },
  };
}

function generateMockCrewNotes(): CrewNote[] {
  return [
    {
      id: 'N-001',
      author: '2nd Engineer',
      content: 'Unusual vibration from generator #1 during startup. Recommend inspection.',
      timestamp: '3h ago',
      type: 'concern',
      status: 'new',
    },
    {
      id: 'N-002',
      author: 'Chief Engineer',
      content: 'Scheduled maintenance for stabilisers moved to next port stay.',
      timestamp: '5h ago',
      type: 'observation',
      status: 'reviewed',
    },
    {
      id: 'N-003',
      author: 'ETO',
      content: 'Network switch replaced in engine control room. All systems nominal.',
      timestamp: '1d ago',
      type: 'observation',
      status: 'actioned',
    },
  ];
}

function generateMockPredictiveRisks(): PredictiveRisk[] {
  return [
    {
      id: 'PR-001',
      equipment: 'Main Generator #1',
      riskType: 'Coolant System Failure',
      probability: 78,
      impact: 'high',
      recommendation: 'Schedule coolant system inspection within 72 hours',
      timeframe: '7-14 days',
    },
    {
      id: 'PR-002',
      equipment: 'Bow Thruster',
      riskType: 'Seal Wear',
      probability: 45,
      impact: 'medium',
      recommendation: 'Monitor for leaks; plan seal replacement at next drydock',
      timeframe: '30-60 days',
    },
  ];
}

function generateMockDocuments(): { items: ExpiringDocument[]; stats: DocumentStats } {
  return {
    items: [
      {
        id: 'DOC-001',
        name: 'Safety Equipment Certificate',
        type: 'certificate',
        expiryDate: '2025-02-15',
        daysUntil: 18,
        status: 'expiring',
      },
      {
        id: 'DOC-002',
        name: 'Class Survey - Hull',
        type: 'survey',
        expiryDate: '2025-03-01',
        daysUntil: 32,
        status: 'valid',
      },
      {
        id: 'DOC-003',
        name: 'Radio License',
        type: 'license',
        expiryDate: '2025-01-30',
        daysUntil: 2,
        status: 'critical',
      },
    ],
    stats: {
      total: 45,
      valid: 42,
      expiringSoon: 3,
      expired: 0,
    },
  };
}

function generateMockHandover(): HandoverStatus {
  return {
    status: 'draft',
    lastUpdated: '2h ago',
    sections: [
      { name: 'Critical Items', items: 3, complete: true },
      { name: 'Work Orders', items: 5, complete: true },
      { name: 'Equipment Status', items: 2, complete: false },
      { name: 'Pending Deliveries', items: 4, complete: true },
      { name: 'Crew Notes', items: 6, complete: false },
    ],
    nextHandover: 'Tomorrow 08:00',
    assignedTo: 'Chief Engineer → 2nd Engineer',
  };
}

function generateMockDashboardData(): DashboardData {
  return {
    workOrders: generateMockWorkOrders(),
    faults: generateMockFaults(),
    equipment: generateMockEquipment(),
    inventory: generateMockInventory(),
    crewNotes: generateMockCrewNotes(),
    predictiveRisks: generateMockPredictiveRisks(),
    documents: generateMockDocuments(),
    handover: generateMockHandover(),
  };
}

// ============================================================================
// HOOK
// ============================================================================

export function useDashboardData(refreshInterval: number = 60000) {
  const [state, setState] = useState<DashboardState>({
    data: null,
    isLoading: true,
    error: null,
    lastUpdated: null,
  });

  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  const fetchData = useCallback(async (silent: boolean = false) => {
    if (!silent) {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
    }

    try {
      // Try to fetch real data from API
      // For now, use mock data until API endpoints are available
      // TODO: Replace with actual API calls when backend is ready
      //
      // const data = await fetchDashboardEndpoint<DashboardData>('/dashboard/summary');

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Use mock data
      const data = generateMockDashboardData();

      if (isMountedRef.current) {
        setState({
          data,
          isLoading: false,
          error: null,
          lastUpdated: new Date(),
        });
      }
    } catch (error) {
      console.error('[useDashboardData] Fetch error:', error);

      if (isMountedRef.current) {
        // Fall back to mock data on error
        const mockData = generateMockDashboardData();
        setState({
          data: mockData,
          isLoading: false,
          error: 'Using cached data - live sync unavailable',
          lastUpdated: new Date(),
        });
      }
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchData();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (refreshInterval > 0) {
      refreshTimerRef.current = setInterval(() => {
        fetchData(true); // Silent refresh
      }, refreshInterval);

      return () => {
        if (refreshTimerRef.current) {
          clearInterval(refreshTimerRef.current);
        }
      };
    }
  }, [refreshInterval, fetchData]);

  // Manual refresh
  const refresh = useCallback(() => {
    fetchData(false);
  }, [fetchData]);

  return {
    ...state,
    refresh,
  };
}

// ============================================================================
// INDIVIDUAL MODULE HOOKS
// ============================================================================

export function useWorkOrderData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    workOrders: data?.workOrders.items ?? [],
    stats: data?.workOrders.stats ?? { total: 0, completed: 0, inProgress: 0, overdue: 0 },
    isLoading,
    error,
    refresh,
  };
}

export function useFaultData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    faults: data?.faults.items ?? [],
    stats: data?.faults.stats ?? { total: 0, open: 0, investigating: 0, resolved: 0, critical: 0 },
    isLoading,
    error,
    refresh,
  };
}

export function useEquipmentData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    equipment: data?.equipment.items ?? [],
    stats: data?.equipment.stats ?? { total: 0, operational: 0, degraded: 0, offline: 0, maintenance: 0 },
    isLoading,
    error,
    refresh,
  };
}

export function useInventoryData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    items: data?.inventory.items ?? [],
    stats: data?.inventory.stats ?? { totalParts: 0, lowStock: 0, outOfStock: 0, pendingOrders: 0 },
    isLoading,
    error,
    refresh,
  };
}

export function useCrewNotesData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    notes: data?.crewNotes ?? [],
    isLoading,
    error,
    refresh,
  };
}

export function usePredictiveRiskData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    risks: data?.predictiveRisks ?? [],
    isLoading,
    error,
    refresh,
  };
}

export function useDocumentExpiryData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    documents: data?.documents.items ?? [],
    stats: data?.documents.stats ?? { total: 0, valid: 0, expiringSoon: 0, expired: 0 },
    isLoading,
    error,
    refresh,
  };
}

export function useHandoverData() {
  const { data, isLoading, error, refresh } = useDashboardData();

  return {
    handover: data?.handover ?? null,
    isLoading,
    error,
    refresh,
  };
}
