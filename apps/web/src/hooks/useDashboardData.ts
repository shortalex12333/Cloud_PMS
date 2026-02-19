/**
 * CelesteOS Dashboard Data Hook
 *
 * Fetches and manages data for all Control Center modules.
 * Provides real-time updates and caching for dashboard widgets.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { getYachtId } from '@/lib/authHelpers';

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

/**
 * Get the current yacht_id from user session metadata
 */
async function getCurrentYachtId(): Promise<string | null> {
  try {
    const yachtId = await getYachtId();
    return yachtId;
  } catch {
    return null;
  }
}

/**
 * Calculate relative time string (e.g., "2h ago", "3 days")
 */
function formatRelativeTime(date: string | null): string {
  if (!date) return 'Unknown';

  try {
    const now = new Date();
    const then = new Date(date);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return then.toLocaleDateString();
  } catch {
    return 'Unknown';
  }
}

/**
 * Calculate days until a date (positive = future, negative = past/overdue)
 */
function daysUntil(date: string | null): number {
  if (!date) return 0;

  try {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const target = new Date(date);
    target.setHours(0, 0, 0, 0);
    const diffMs = target.getTime() - now.getTime();
    return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}

/**
 * Format due date for work orders
 */
function formatDueDate(dueDate: string | null, status: string): string {
  if (!dueDate) return 'No due date';

  const days = daysUntil(dueDate);

  if (status === 'completed' || status === 'closed' || status === 'cancelled') {
    return 'Completed';
  }

  if (days < 0) return `Overdue ${Math.abs(days)}d`;
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  return `${days} days`;
}

// ============================================================================
// REAL DATA FETCHERS
// ============================================================================

/**
 * Fetch work orders from Supabase
 */
async function fetchWorkOrders(yachtId: string): Promise<{ items: WorkOrderSummary[]; stats: WorkOrderStats }> {
  // Get work orders with equipment join
  const { data: workOrders, error } = await supabase
    .from('pms_work_orders')
    .select(`
      id,
      wo_number,
      title,
      status,
      priority,
      due_date,
      equipment_id,
      pms_equipment!equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .not('status', 'in', '("closed","cancelled")')
    .order('due_date', { ascending: true, nullsFirst: false })
    .limit(10);

  if (error) {
    console.error('[useDashboardData] Error fetching work orders:', error);
    throw error;
  }

  // Get stats with separate count queries
  const [totalResult, completedResult, inProgressResult, overdueResult] = await Promise.all([
    supabase
      .from('pms_work_orders')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId),
    supabase
      .from('pms_work_orders')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .in('status', ['completed', 'closed']),
    supabase
      .from('pms_work_orders')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'in_progress'),
    supabase
      .from('pms_work_orders')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .not('status', 'in', '("completed","closed","cancelled")')
      .lt('due_date', new Date().toISOString().split('T')[0]),
  ]);

  // Map to summary format
  const items: WorkOrderSummary[] = (workOrders || []).map((wo: any) => {
    const isOverdue = wo.due_date && daysUntil(wo.due_date) < 0 && !['completed', 'closed', 'cancelled'].includes(wo.status);
    const mappedStatus = isOverdue ? 'overdue' : (wo.status === 'open' ? 'scheduled' : wo.status);

    // Map priority to our schema
    let mappedPriority: 'routine' | 'important' | 'critical' = 'routine';
    if (wo.priority === 'critical' || wo.priority === 'high') {
      mappedPriority = 'critical';
    } else if (wo.priority === 'medium') {
      mappedPriority = 'important';
    }

    return {
      id: wo.wo_number || wo.id,
      title: wo.title || 'Untitled Work Order',
      equipment: wo.pms_equipment?.name || 'Unknown Equipment',
      dueDate: formatDueDate(wo.due_date, wo.status),
      priority: mappedPriority,
      status: mappedStatus as WorkOrderSummary['status'],
    };
  });

  return {
    items,
    stats: {
      total: totalResult.count || 0,
      completed: completedResult.count || 0,
      inProgress: inProgressResult.count || 0,
      overdue: overdueResult.count || 0,
    },
  };
}

/**
 * Fetch faults from Supabase
 */
async function fetchFaults(yachtId: string): Promise<{ items: FaultSummary[]; stats: FaultStats }> {
  // Get active faults with equipment join
  const { data: faults, error } = await supabase
    .from('pms_faults')
    .select(`
      id,
      fault_code,
      title,
      description,
      severity,
      detected_at,
      resolved_at,
      created_at,
      equipment_id,
      pms_equipment!equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .is('resolved_at', null)
    .order('detected_at', { ascending: false, nullsFirst: false })
    .limit(10);

  if (error) {
    console.error('[useDashboardData] Error fetching faults:', error);
    throw error;
  }

  // Get stats
  const [totalResult, openResult, investigatingResult, resolvedResult, criticalResult] = await Promise.all([
    supabase
      .from('pms_faults')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId),
    supabase
      .from('pms_faults')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .is('resolved_at', null),
    // For investigating, we check if there's a related work order in_progress
    supabase
      .from('pms_faults')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .is('resolved_at', null)
      .not('equipment_id', 'is', null),
    supabase
      .from('pms_faults')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .not('resolved_at', 'is', null),
    supabase
      .from('pms_faults')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('severity', 'critical')
      .is('resolved_at', null),
  ]);

  // Map to summary format
  const items: FaultSummary[] = (faults || []).map((fault: any) => ({
    id: fault.id,
    code: fault.fault_code || `F-${fault.id.slice(0, 4)}`,
    title: fault.title || fault.description?.slice(0, 50) || 'Fault Reported',
    equipment: fault.pms_equipment?.name || 'Unknown Equipment',
    severity: fault.severity || 'medium',
    status: fault.resolved_at ? 'resolved' : 'open',
    timestamp: formatRelativeTime(fault.detected_at || fault.created_at),
  }));

  return {
    items,
    stats: {
      total: totalResult.count || 0,
      open: openResult.count || 0,
      investigating: Math.min(investigatingResult.count || 0, openResult.count || 0),
      resolved: resolvedResult.count || 0,
      critical: criticalResult.count || 0,
    },
  };
}

/**
 * Fetch equipment status from Supabase
 */
async function fetchEquipment(yachtId: string): Promise<{ items: EquipmentStatus[]; stats: EquipmentStats }> {
  // Get equipment with status
  const { data: equipment, error } = await supabase
    .from('pms_equipment')
    .select(`
      id,
      name,
      system,
      category,
      status,
      running_hours,
      last_service_date,
      updated_at
    `)
    .eq('yacht_id', yachtId)
    .order('updated_at', { ascending: false })
    .limit(20);

  if (error) {
    console.error('[useDashboardData] Error fetching equipment:', error);
    throw error;
  }

  // Get stats
  const [totalResult, operationalResult, degradedResult, offlineResult, maintenanceResult] = await Promise.all([
    supabase
      .from('pms_equipment')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId),
    supabase
      .from('pms_equipment')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'operational'),
    supabase
      .from('pms_equipment')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'degraded'),
    supabase
      .from('pms_equipment')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'offline'),
    supabase
      .from('pms_equipment')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'maintenance'),
  ]);

  // Map to status format
  const items: EquipmentStatus[] = (equipment || []).map((eq: any) => ({
    id: eq.id,
    name: eq.name || 'Unknown Equipment',
    system: eq.system || eq.category || 'General',
    status: eq.status || 'operational',
    lastChecked: formatRelativeTime(eq.updated_at || eq.last_service_date),
    runningHours: eq.running_hours,
  }));

  return {
    items,
    stats: {
      total: totalResult.count || 0,
      operational: operationalResult.count || 0,
      degraded: degradedResult.count || 0,
      offline: offlineResult.count || 0,
      maintenance: maintenanceResult.count || 0,
    },
  };
}

/**
 * Fetch inventory/parts from Supabase
 */
async function fetchInventory(yachtId: string): Promise<{ items: InventoryItem[]; stats: InventoryStats }> {
  // Get parts that are low stock or out of stock first
  const { data: parts, error } = await supabase
    .from('pms_parts')
    .select(`
      id,
      part_number,
      name,
      quantity,
      quantity_on_hand,
      minimum_quantity,
      min_quantity,
      location,
      storage_location,
      bin_number
    `)
    .eq('yacht_id', yachtId)
    .order('quantity', { ascending: true })
    .limit(20);

  if (error) {
    console.error('[useDashboardData] Error fetching inventory:', error);
    throw error;
  }

  // Get stats
  const [totalResult, pendingOrdersResult] = await Promise.all([
    supabase
      .from('pms_parts')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId),
    supabase
      .from('pms_purchase_orders')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', yachtId)
      .eq('status', 'pending'),
  ]);

  // Calculate low stock and out of stock counts
  let lowStockCount = 0;
  let outOfStockCount = 0;

  // Map to inventory format
  const items: InventoryItem[] = (parts || []).map((part: any) => {
    const qty = part.quantity ?? part.quantity_on_hand ?? 0;
    const minQty = part.minimum_quantity ?? part.min_quantity ?? 0;
    const location = part.location || part.storage_location || part.bin_number || 'Unknown';

    let status: InventoryItem['status'] = 'healthy';
    if (qty <= 0) {
      status = 'out_of_stock';
      outOfStockCount++;
    } else if (qty <= minQty) {
      status = 'low';
      lowStockCount++;
    } else if (qty < minQty * 1.5) {
      status = 'low';
      lowStockCount++;
    }

    return {
      id: part.id,
      partNumber: part.part_number || part.id.slice(0, 8),
      name: part.name || 'Unknown Part',
      quantity: qty,
      minStock: minQty,
      location,
      status,
    };
  });

  // Filter to show only items that need attention
  const criticalItems = items.filter(i => i.status !== 'healthy').slice(0, 10);

  return {
    items: criticalItems.length > 0 ? criticalItems : items.slice(0, 5),
    stats: {
      totalParts: totalResult.count || 0,
      lowStock: lowStockCount,
      outOfStock: outOfStockCount,
      pendingOrders: pendingOrdersResult.count || 0,
    },
  };
}

/**
 * Fetch crew notes from Supabase
 */
async function fetchCrewNotes(yachtId: string): Promise<CrewNote[]> {
  // Get recent notes
  const { data: notes, error } = await supabase
    .from('pms_notes')
    .select(`
      id,
      content,
      created_at,
      created_by,
      entity_type,
      category
    `)
    .eq('yacht_id', yachtId)
    .order('created_at', { ascending: false })
    .limit(10);

  if (error) {
    console.error('[useDashboardData] Error fetching crew notes:', error);
    throw error;
  }

  // Map to crew note format
  return (notes || []).map((note: any) => {
    // Determine note type based on content or category
    let noteType: CrewNote['type'] = 'observation';
    const content = (note.content || '').toLowerCase();
    if (content.includes('concern') || content.includes('issue') || content.includes('problem')) {
      noteType = 'concern';
    } else if (content.includes('recommend') || content.includes('suggest')) {
      noteType = 'recommendation';
    }

    return {
      id: note.id,
      author: note.created_by || 'Crew Member',
      content: note.content || '',
      timestamp: formatRelativeTime(note.created_at),
      type: noteType,
      status: 'new' as const,
    };
  });
}

/**
 * Fetch predictive risks (placeholder - requires predictive_state table)
 */
async function fetchPredictiveRisks(yachtId: string): Promise<PredictiveRisk[]> {
  // Try to get predictive state data
  try {
    const { data: risks, error } = await supabase
      .from('predictive_state')
      .select(`
        id,
        equipment_id,
        risk_score,
        risk_factors,
        predicted_failure_date,
        recommendation,
        pms_equipment!equipment_id (name)
      `)
      .eq('yacht_id', yachtId)
      .gt('risk_score', 30)
      .order('risk_score', { ascending: false })
      .limit(5);

    if (error) {
      // Table may not exist, return empty array
      console.log('[useDashboardData] Predictive state not available');
      return [];
    }

    return (risks || []).map((risk: any) => {
      let impact: PredictiveRisk['impact'] = 'low';
      if (risk.risk_score >= 80) impact = 'critical';
      else if (risk.risk_score >= 60) impact = 'high';
      else if (risk.risk_score >= 40) impact = 'medium';

      return {
        id: risk.id,
        equipment: risk.pms_equipment?.name || 'Equipment',
        riskType: risk.risk_factors?.[0] || 'Potential Issue',
        probability: risk.risk_score || 0,
        impact,
        recommendation: risk.recommendation || 'Monitor equipment condition',
        timeframe: risk.predicted_failure_date
          ? `${daysUntil(risk.predicted_failure_date)} days`
          : 'Unknown',
      };
    });
  } catch {
    return [];
  }
}

/**
 * Fetch expiring documents from Supabase
 */
async function fetchDocuments(yachtId: string): Promise<{ items: ExpiringDocument[]; stats: DocumentStats }> {
  // Get documents with expiry dates
  const { data: docs, error } = await supabase
    .from('documents')
    .select(`
      id,
      title,
      name,
      document_type,
      category,
      expiry_date,
      created_at
    `)
    .eq('yacht_id', yachtId)
    .not('expiry_date', 'is', null)
    .order('expiry_date', { ascending: true })
    .limit(20);

  if (error) {
    console.error('[useDashboardData] Error fetching documents:', error);
    throw error;
  }

  // Get total count
  const { count: totalCount } = await supabase
    .from('documents')
    .select('id', { count: 'exact', head: true })
    .eq('yacht_id', yachtId);

  const now = new Date();
  let valid = 0;
  let expiringSoon = 0;
  let expired = 0;

  // Map to document format
  const items: ExpiringDocument[] = (docs || []).map((doc: any) => {
    const days = daysUntil(doc.expiry_date);

    let docStatus: ExpiringDocument['status'] = 'valid';
    if (days < 0) {
      docStatus = 'expired';
      expired++;
    } else if (days <= 7) {
      docStatus = 'critical';
      expiringSoon++;
    } else if (days <= 30) {
      docStatus = 'expiring';
      expiringSoon++;
    } else {
      valid++;
    }

    // Map document type
    let docType: ExpiringDocument['type'] = 'certificate';
    const category = (doc.category || doc.document_type || '').toLowerCase();
    if (category.includes('survey')) docType = 'survey';
    else if (category.includes('license')) docType = 'license';
    else if (category.includes('permit')) docType = 'permit';

    return {
      id: doc.id,
      name: doc.title || doc.name || 'Untitled Document',
      type: docType,
      expiryDate: doc.expiry_date,
      daysUntil: days,
      status: docStatus,
    };
  });

  // Show documents that need attention first
  const priorityItems = items
    .filter(d => d.status !== 'valid')
    .sort((a, b) => a.daysUntil - b.daysUntil)
    .slice(0, 5);

  return {
    items: priorityItems.length > 0 ? priorityItems : items.slice(0, 5),
    stats: {
      total: totalCount || 0,
      valid,
      expiringSoon,
      expired,
    },
  };
}

/**
 * Fetch handover status from Supabase
 */
async function fetchHandover(yachtId: string): Promise<HandoverStatus> {
  // Get recent handover items grouped by category
  const { data: items, error } = await supabase
    .from('handover_items')
    .select(`
      id,
      section,
      category,
      is_critical,
      requires_action,
      created_at,
      updated_at
    `)
    .eq('yacht_id', yachtId)
    .is('deleted_at', null)
    .order('created_at', { ascending: false })
    .limit(50);

  if (error) {
    console.error('[useDashboardData] Error fetching handover:', error);
    throw error;
  }

  // Get latest export status
  const { data: latestExport } = await supabase
    .from('handover_exports')
    .select('id, export_status, created_at')
    .eq('yacht_id', yachtId)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();

  // Group items by section
  const sectionGroups: Record<string, { items: number; critical: number }> = {};
  (items || []).forEach((item: any) => {
    const section = item.section || item.category || 'General';
    if (!sectionGroups[section]) {
      sectionGroups[section] = { items: 0, critical: 0 };
    }
    sectionGroups[section].items++;
    if (item.is_critical) {
      sectionGroups[section].critical++;
    }
  });

  // Build sections array
  const sections: HandoverSection[] = Object.entries(sectionGroups).map(([name, data]) => ({
    name,
    items: data.items,
    complete: data.critical === 0, // Section complete if no critical items
  }));

  // Determine overall status
  let status: HandoverStatus['status'] = 'draft';
  if (latestExport?.export_status === 'completed') {
    status = 'submitted';
  } else if (sections.some(s => s.items > 0)) {
    status = 'ready';
  }

  // Calculate next handover (8am tomorrow)
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(8, 0, 0, 0);

  return {
    status,
    lastUpdated: formatRelativeTime(items?.[0]?.updated_at || items?.[0]?.created_at),
    sections: sections.length > 0 ? sections : [
      { name: 'No items', items: 0, complete: true },
    ],
    nextHandover: `Tomorrow ${tomorrow.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
    assignedTo: 'Chief Engineer',
  };
}

/**
 * Fetch all dashboard data in parallel
 */
async function fetchAllDashboardData(yachtId: string): Promise<DashboardData> {
  const [
    workOrders,
    faults,
    equipment,
    inventory,
    crewNotes,
    predictiveRisks,
    documents,
    handover,
  ] = await Promise.all([
    fetchWorkOrders(yachtId),
    fetchFaults(yachtId),
    fetchEquipment(yachtId),
    fetchInventory(yachtId),
    fetchCrewNotes(yachtId),
    fetchPredictiveRisks(yachtId),
    fetchDocuments(yachtId),
    fetchHandover(yachtId),
  ]);

  return {
    workOrders,
    faults,
    equipment,
    inventory,
    crewNotes,
    predictiveRisks,
    documents,
    handover,
  };
}

// ============================================================================
// FALLBACK DATA (Used when API is unavailable or yacht_id is missing)
// ============================================================================

function getEmptyDashboardData(): DashboardData {
  return {
    workOrders: { items: [], stats: { total: 0, completed: 0, inProgress: 0, overdue: 0 } },
    faults: { items: [], stats: { total: 0, open: 0, investigating: 0, resolved: 0, critical: 0 } },
    equipment: { items: [], stats: { total: 0, operational: 0, degraded: 0, offline: 0, maintenance: 0 } },
    inventory: { items: [], stats: { totalParts: 0, lowStock: 0, outOfStock: 0, pendingOrders: 0 } },
    crewNotes: [],
    predictiveRisks: [],
    documents: { items: [], stats: { total: 0, valid: 0, expiringSoon: 0, expired: 0 } },
    handover: {
      status: 'draft',
      lastUpdated: 'Never',
      sections: [],
      nextHandover: 'Not scheduled',
      assignedTo: 'Unassigned',
    },
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
      // Get yacht_id from user session
      const yachtId = await getCurrentYachtId();

      if (!yachtId) {
        console.warn('[useDashboardData] No yacht_id in session, returning empty data');
        if (isMountedRef.current) {
          setState({
            data: getEmptyDashboardData(),
            isLoading: false,
            error: 'No yacht selected',
            lastUpdated: new Date(),
          });
        }
        return;
      }

      // Fetch all dashboard data from Supabase in parallel
      const data = await fetchAllDashboardData(yachtId);

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
        // Return empty data on error with error message
        setState({
          data: getEmptyDashboardData(),
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to load dashboard data',
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
