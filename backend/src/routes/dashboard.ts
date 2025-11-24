// CelesteOS Dashboard Routes
// GET /v1/dashboard/briefing
// GET /v1/dashboard/legacy

import { Hono } from 'hono';
import type { Context } from 'hono';
import type {
  DashboardBriefingResponse,
  DashboardLegacyResponse,
  HighRiskEquipmentItem,
  RiskMovement,
  UnstableSystem,
  Pattern,
  OverdueWorkOrder,
  InventoryGap,
  InspectionDue,
  CrewFrustration,
  SummaryStats,
} from '../types/index.js';
import { authMiddleware, yachtIsolationMiddleware, createError } from '../middleware/auth.js';

const dashboard = new Hono();

// Apply middleware to all routes
dashboard.use('*', authMiddleware);
dashboard.use('*', yachtIsolationMiddleware);

// ============================================================================
// GET /v1/dashboard/briefing - Intelligence Snapshot
// ============================================================================

dashboard.get('/briefing', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const yachtId = auth.yacht_id;

  try {
    // Check for cached snapshot first
    const { data: cachedSnapshot } = await supabase
      .from('dashboard_snapshot')
      .select('*')
      .eq('yacht_id', yachtId)
      .eq('snapshot_type', 'briefing')
      .gte('valid_until', new Date().toISOString())
      .order('generated_at', { ascending: false })
      .limit(1)
      .single();

    if (cachedSnapshot) {
      return c.json({
        risk_movements: cachedSnapshot.risk_movements,
        high_risk_equipment: cachedSnapshot.high_risk_equipment,
        patterns_7d: cachedSnapshot.patterns_7d,
        unstable_systems: cachedSnapshot.unstable_systems,
        inventory_gaps: cachedSnapshot.inventory_gaps,
        overdue_critical: cachedSnapshot.overdue_critical,
        inspections_due: cachedSnapshot.inspections_due,
        crew_frustration: cachedSnapshot.crew_frustration,
        summary: cachedSnapshot.summary_stats,
        generated_at: cachedSnapshot.generated_at,
        cache_valid_until: cachedSnapshot.valid_until,
      } as DashboardBriefingResponse);
    }

    // Generate fresh snapshot
    const startTime = Date.now();

    // Parallel queries for all dashboard data
    const [
      highRiskResult,
      riskMovementsResult,
      unstableResult,
      overdueResult,
      inventoryGapsResult,
      inspectionsResult,
      crewFrustrationResult,
      summaryResult,
    ] = await Promise.all([
      getHighRiskEquipment(supabase, yachtId),
      getRiskMovements(supabase, yachtId),
      getUnstableSystems(supabase, yachtId),
      getOverdueCritical(supabase, yachtId),
      getInventoryGaps(supabase, yachtId),
      getInspectionsDue(supabase, yachtId),
      getCrewFrustration(supabase, yachtId),
      getSummaryStats(supabase, yachtId),
    ]);

    // Detect 7-day patterns
    const patterns7d = await detect7DayPatterns(supabase, yachtId);

    const response: DashboardBriefingResponse = {
      risk_movements: riskMovementsResult,
      high_risk_equipment: highRiskResult,
      patterns_7d: patterns7d,
      unstable_systems: unstableResult,
      inventory_gaps: inventoryGapsResult,
      overdue_critical: overdueResult,
      inspections_due: inspectionsResult,
      crew_frustration: crewFrustrationResult,
      summary: summaryResult,
      generated_at: new Date().toISOString(),
    };

    // Cache the snapshot (valid for 30 minutes)
    const validUntil = new Date(Date.now() + 30 * 60 * 1000).toISOString();
    await supabase.from('dashboard_snapshot').insert({
      yacht_id: yachtId,
      snapshot_type: 'briefing',
      high_risk_equipment: highRiskResult,
      risk_movements: riskMovementsResult,
      unstable_systems: unstableResult,
      patterns_7d: patterns7d,
      overdue_critical: overdueResult,
      inventory_gaps: inventoryGapsResult,
      inspections_due: inspectionsResult,
      crew_frustration: crewFrustrationResult,
      summary_stats: summaryResult,
      generated_at: new Date().toISOString(),
      generation_duration_ms: Date.now() - startTime,
      valid_until: validUntil,
    });

    response.cache_valid_until = validUntil;

    return c.json(response);

  } catch (error) {
    console.error('Dashboard briefing error:', error);
    return createError('internal_error', 'Failed to generate dashboard briefing', 500);
  }
});

// ============================================================================
// GET /v1/dashboard/legacy - Legacy Compatibility View
// ============================================================================

dashboard.get('/legacy', async (c: Context) => {
  const auth = c.get('auth');
  const supabase = c.get('supabase');
  const yachtId = auth.yacht_id;

  try {
    // Check for cached legacy view
    const { data: cachedView } = await supabase
      .from('dashboard_legacy_view')
      .select('*')
      .eq('yacht_id', yachtId)
      .gte('valid_until', new Date().toISOString())
      .single();

    if (cachedView) {
      return c.json({
        equipment: cachedView.equipment_overview,
        work_orders: cachedView.work_orders_overview,
        inventory: cachedView.inventory_overview,
        certificates: cachedView.certificates_overview,
        faults: cachedView.fault_history,
        scheduled_maintenance: cachedView.scheduled_maintenance,
        parts: cachedView.parts_usage,
        documents: cachedView.documents_summary,
        counts: {
          equipment: cachedView.equipment_count,
          work_orders: cachedView.work_orders_count,
          inventory: cachedView.inventory_count,
          certificates: cachedView.certificates_count,
          faults_active: cachedView.faults_active_count,
          maintenance_overdue: cachedView.maintenance_overdue,
        },
        generated_at: cachedView.generated_at,
      } as DashboardLegacyResponse);
    }

    // Generate fresh legacy view
    const [
      equipmentResult,
      workOrdersResult,
      inventoryResult,
      certificatesResult,
      faultsResult,
      maintenanceResult,
      partsResult,
      documentsResult,
    ] = await Promise.all([
      getEquipmentOverview(supabase, yachtId),
      getWorkOrdersOverview(supabase, yachtId),
      getInventoryOverview(supabase, yachtId),
      getCertificatesOverview(supabase, yachtId),
      getFaultHistory(supabase, yachtId),
      getScheduledMaintenance(supabase, yachtId),
      getPartsUsage(supabase, yachtId),
      getDocumentsSummary(supabase, yachtId),
    ]);

    const response: DashboardLegacyResponse = {
      equipment: equipmentResult.items,
      work_orders: workOrdersResult.items,
      inventory: inventoryResult.items,
      certificates: certificatesResult.items,
      faults: faultsResult.items,
      scheduled_maintenance: maintenanceResult.items,
      parts: partsResult,
      documents: documentsResult,
      counts: {
        equipment: equipmentResult.total,
        work_orders: workOrdersResult.total,
        inventory: inventoryResult.total,
        certificates: certificatesResult.total,
        faults_active: faultsResult.activeCount,
        maintenance_overdue: maintenanceResult.overdueCount,
      },
      generated_at: new Date().toISOString(),
    };

    // Cache legacy view (valid for 1 hour)
    const validUntil = new Date(Date.now() + 60 * 60 * 1000).toISOString();
    await supabase.from('dashboard_legacy_view').upsert({
      yacht_id: yachtId,
      equipment_overview: equipmentResult.items,
      equipment_count: equipmentResult.total,
      equipment_by_status: equipmentResult.byStatus,
      work_orders_overview: workOrdersResult.items,
      work_orders_count: workOrdersResult.total,
      work_orders_by_status: workOrdersResult.byStatus,
      work_orders_overdue_count: workOrdersResult.overdueCount,
      inventory_overview: inventoryResult.items,
      inventory_count: inventoryResult.total,
      inventory_low_stock_count: inventoryResult.lowStockCount,
      certificates_overview: certificatesResult.items,
      certificates_count: certificatesResult.total,
      certificates_expiring_soon: certificatesResult.expiringSoon,
      fault_history: faultsResult.items,
      faults_active_count: faultsResult.activeCount,
      faults_resolved_30d: faultsResult.resolved30d,
      scheduled_maintenance: maintenanceResult.items,
      maintenance_upcoming_7d: maintenanceResult.upcoming7d,
      maintenance_overdue: maintenanceResult.overdueCount,
      parts_usage: partsResult,
      documents_summary: documentsResult,
      documents_total: documentsResult.total,
      generated_at: new Date().toISOString(),
      valid_until: validUntil,
    });

    return c.json(response);

  } catch (error) {
    console.error('Dashboard legacy error:', error);
    return createError('internal_error', 'Failed to generate legacy dashboard', 500);
  }
});

// ============================================================================
// HELPER FUNCTIONS - Briefing Data
// ============================================================================

async function getHighRiskEquipment(supabase: any, yachtId: string): Promise<HighRiskEquipmentItem[]> {
  const { data } = await supabase
    .from('predictive_state')
    .select(`
      equipment_id,
      risk_score,
      risk_level,
      trend,
      contributing_factors,
      equipment:equipment_id (name, system_type)
    `)
    .eq('yacht_id', yachtId)
    .gte('risk_score', 0.6)
    .order('risk_score', { ascending: false })
    .limit(10);

  return (data || []).map((item: any) => ({
    equipment_id: item.equipment_id,
    equipment_name: item.equipment?.name || 'Unknown',
    risk_score: item.risk_score,
    risk_level: item.risk_level,
    trend: item.trend || 'stable',
    system_type: item.equipment?.system_type,
    contributing_factors: item.contributing_factors,
  }));
}

async function getRiskMovements(supabase: any, yachtId: string): Promise<RiskMovement[]> {
  const { data } = await supabase
    .from('predictive_state')
    .select(`
      equipment_id,
      risk_score,
      previous_risk_score,
      equipment:equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .gte('updated_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
    .order('updated_at', { ascending: false });

  return (data || [])
    .filter((item: any) => {
      const delta = Math.abs(item.risk_score - (item.previous_risk_score || 0));
      return delta > 0.05;
    })
    .map((item: any) => ({
      equipment_id: item.equipment_id,
      equipment_name: item.equipment?.name || 'Unknown',
      current_score: item.risk_score,
      previous_score: item.previous_risk_score || 0,
      delta: item.risk_score - (item.previous_risk_score || 0),
      direction: item.risk_score > (item.previous_risk_score || 0) ? 'up' : 'down',
    }));
}

async function getUnstableSystems(supabase: any, yachtId: string): Promise<UnstableSystem[]> {
  const cutoff = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();

  // Get equipment with multiple faults in 48h
  const { data: faultData } = await supabase
    .rpc('get_unstable_systems', { p_yacht_id: yachtId, p_hours: 48 });

  if (faultData) return faultData;

  // Fallback query
  const { data } = await supabase
    .from('faults')
    .select('equipment_id, equipment:equipment_id (name)')
    .eq('yacht_id', yachtId)
    .gte('detected_at', cutoff);

  const counts: Record<string, { name: string; faults: number }> = {};
  (data || []).forEach((f: any) => {
    if (!counts[f.equipment_id]) {
      counts[f.equipment_id] = { name: f.equipment?.name || 'Unknown', faults: 0 };
    }
    counts[f.equipment_id].faults++;
  });

  return Object.entries(counts)
    .filter(([_, v]) => v.faults >= 2)
    .map(([id, v]) => ({
      equipment_id: id,
      equipment_name: v.name,
      fault_count_48h: v.faults,
      note_count_48h: 0,
      risk_score: 0,
    }));
}

async function getOverdueCritical(supabase: any, yachtId: string): Promise<OverdueWorkOrder[]> {
  const { data } = await supabase
    .from('work_orders')
    .select(`
      id,
      title,
      equipment_id,
      due_date,
      priority,
      equipment:equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .in('status', ['planned', 'in_progress'])
    .lt('due_date', new Date().toISOString().split('T')[0])
    .order('due_date', { ascending: true })
    .limit(20);

  return (data || []).map((wo: any) => {
    const dueDate = new Date(wo.due_date);
    const daysOverdue = Math.floor((Date.now() - dueDate.getTime()) / (1000 * 60 * 60 * 24));
    return {
      work_order_id: wo.id,
      title: wo.title,
      equipment_id: wo.equipment_id,
      equipment_name: wo.equipment?.name,
      due_date: wo.due_date,
      days_overdue: daysOverdue,
      priority: wo.priority,
    };
  });
}

async function getInventoryGaps(supabase: any, yachtId: string): Promise<InventoryGap[]> {
  const { data } = await supabase
    .from('stock_levels')
    .select(`
      part_id,
      quantity,
      min_quantity,
      parts:part_id (name)
    `)
    .eq('yacht_id', yachtId)
    .lt('quantity', supabase.raw('min_quantity'));

  return (data || []).map((item: any) => ({
    part_id: item.part_id,
    part_name: item.parts?.name || 'Unknown Part',
    current_qty: item.quantity,
    min_qty: item.min_quantity,
    shortage: item.min_quantity - item.quantity,
  }));
}

async function getInspectionsDue(supabase: any, yachtId: string): Promise<InspectionDue[]> {
  const in7Days = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const { data } = await supabase
    .from('work_orders')
    .select(`
      id,
      title,
      equipment_id,
      due_date,
      equipment:equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .eq('type', 'scheduled')
    .eq('status', 'planned')
    .lte('due_date', in7Days)
    .order('due_date', { ascending: true })
    .limit(10);

  return (data || []).map((wo: any) => {
    const dueDate = new Date(wo.due_date);
    const daysUntil = Math.floor((dueDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return {
      inspection_id: wo.id,
      title: wo.title,
      equipment_id: wo.equipment_id,
      equipment_name: wo.equipment?.name,
      due_date: wo.due_date,
      days_until: daysUntil,
    };
  });
}

async function getCrewFrustration(supabase: any, yachtId: string): Promise<CrewFrustration[]> {
  // Get search query clusters from last 7 days
  const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const { data } = await supabase
    .from('search_queries')
    .select('query_text, entities')
    .eq('yacht_id', yachtId)
    .gte('created_at', cutoff);

  // Simple clustering by keywords
  const clusters: Record<string, { count: number; queries: string[] }> = {};

  (data || []).forEach((q: any) => {
    const text = q.query_text.toLowerCase();
    const words = text.split(/\s+/).filter((w: string) => w.length > 3);

    words.forEach((word: string) => {
      if (!clusters[word]) {
        clusters[word] = { count: 0, queries: [] };
      }
      clusters[word].count++;
      if (clusters[word].queries.length < 5) {
        clusters[word].queries.push(q.query_text);
      }
    });
  });

  return Object.entries(clusters)
    .filter(([_, v]) => v.count >= 3)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 5)
    .map(([cluster, v]) => ({
      search_cluster: cluster,
      query_count: v.count,
      recent_queries: v.queries,
      potential_issue: `Crew searching "${cluster}" frequently`,
    }));
}

async function getSummaryStats(supabase: any, yachtId: string): Promise<SummaryStats> {
  const [
    { count: totalEquipment },
    { count: highRiskCount },
    { count: overdueWoCount },
    { count: lowStockCount },
    { count: activeFaults },
    { count: inspectionsDue7d },
  ] = await Promise.all([
    supabase.from('equipment').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId),
    supabase.from('predictive_state').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId).gte('risk_score', 0.6),
    supabase.from('work_orders').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId).in('status', ['planned', 'in_progress']).lt('due_date', new Date().toISOString().split('T')[0]),
    supabase.from('stock_levels').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId).lt('quantity', supabase.raw('min_quantity')),
    supabase.from('faults').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId).is('resolved_at', null),
    supabase.from('work_orders').select('*', { count: 'exact', head: true }).eq('yacht_id', yachtId).eq('type', 'scheduled').eq('status', 'planned').lte('due_date', new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]),
  ]);

  return {
    total_equipment: totalEquipment || 0,
    high_risk_count: highRiskCount || 0,
    overdue_wo_count: overdueWoCount || 0,
    low_stock_count: lowStockCount || 0,
    active_faults: activeFaults || 0,
    inspections_due_7d: inspectionsDue7d || 0,
  };
}

async function detect7DayPatterns(supabase: any, yachtId: string): Promise<Pattern[]> {
  // Simplified pattern detection
  const patterns: Pattern[] = [];

  // Check for repeated faults on same equipment
  const { data: faultPatterns } = await supabase
    .from('faults')
    .select('equipment_id, fault_code, equipment:equipment_id (name)')
    .eq('yacht_id', yachtId)
    .gte('detected_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString());

  const faultCounts: Record<string, { code: string; name: string; count: number }> = {};
  (faultPatterns || []).forEach((f: any) => {
    const key = `${f.equipment_id}-${f.fault_code}`;
    if (!faultCounts[key]) {
      faultCounts[key] = { code: f.fault_code, name: f.equipment?.name || 'Unknown', count: 0 };
    }
    faultCounts[key].count++;
  });

  Object.values(faultCounts)
    .filter(v => v.count >= 2)
    .forEach(v => {
      patterns.push({
        pattern_type: 'recurring_fault',
        description: `Fault ${v.code} occurred ${v.count} times on ${v.name} in 7 days`,
        affected_equipment: [v.name],
        confidence: Math.min(v.count / 5, 1),
      });
    });

  return patterns;
}

// ============================================================================
// HELPER FUNCTIONS - Legacy Data
// ============================================================================

async function getEquipmentOverview(supabase: any, yachtId: string) {
  const { data, count } = await supabase
    .from('equipment')
    .select(`
      id,
      name,
      system_type,
      criticality,
      predictive_state (risk_score)
    `, { count: 'exact' })
    .eq('yacht_id', yachtId)
    .order('name')
    .limit(100);

  const items = (data || []).map((e: any) => ({
    id: e.id,
    name: e.name,
    system_type: e.system_type,
    status: e.criticality || 'normal',
    risk_score: e.predictive_state?.[0]?.risk_score,
  }));

  const byStatus: Record<string, number> = {};
  items.forEach((i: any) => {
    byStatus[i.status] = (byStatus[i.status] || 0) + 1;
  });

  return { items, total: count || 0, byStatus };
}

async function getWorkOrdersOverview(supabase: any, yachtId: string) {
  const { data, count } = await supabase
    .from('work_orders')
    .select(`
      id,
      title,
      status,
      priority,
      due_date,
      equipment:equipment_id (name)
    `, { count: 'exact' })
    .eq('yacht_id', yachtId)
    .order('due_date', { ascending: true })
    .limit(100);

  const items = (data || []).map((wo: any) => ({
    id: wo.id,
    title: wo.title,
    status: wo.status,
    priority: wo.priority,
    due_date: wo.due_date,
    equipment_name: wo.equipment?.name,
  }));

  const byStatus: Record<string, number> = {};
  let overdueCount = 0;
  items.forEach((i: any) => {
    byStatus[i.status] = (byStatus[i.status] || 0) + 1;
    if (i.due_date && new Date(i.due_date) < new Date() && !['completed', 'cancelled'].includes(i.status)) {
      overdueCount++;
    }
  });

  return { items, total: count || 0, byStatus, overdueCount };
}

async function getInventoryOverview(supabase: any, yachtId: string) {
  const { data, count } = await supabase
    .from('stock_levels')
    .select(`
      id,
      quantity,
      min_quantity,
      parts:part_id (name, part_number)
    `, { count: 'exact' })
    .eq('yacht_id', yachtId)
    .order('quantity', { ascending: true })
    .limit(100);

  let lowStockCount = 0;
  const items = (data || []).map((s: any) => {
    const status = s.quantity < s.min_quantity ? 'critical' : s.quantity < s.min_quantity * 1.5 ? 'low' : 'ok';
    if (status !== 'ok') lowStockCount++;
    return {
      id: s.id,
      name: s.parts?.name || 'Unknown',
      part_number: s.parts?.part_number,
      quantity: s.quantity,
      min_quantity: s.min_quantity,
      status,
    };
  });

  return { items, total: count || 0, lowStockCount };
}

async function getCertificatesOverview(supabase: any, yachtId: string) {
  // Assuming certificates are stored in documents with a type
  const { data, count } = await supabase
    .from('documents')
    .select('id, filename, metadata', { count: 'exact' })
    .eq('yacht_id', yachtId)
    .contains('tags', ['certificate'])
    .limit(50);

  let expiringSoon = 0;
  const items = (data || []).map((d: any) => {
    const expiryDate = d.metadata?.expiry_date;
    let daysUntilExpiry = 999;
    let status: 'valid' | 'expiring' | 'expired' = 'valid';

    if (expiryDate) {
      daysUntilExpiry = Math.floor((new Date(expiryDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
      if (daysUntilExpiry < 0) status = 'expired';
      else if (daysUntilExpiry < 30) {
        status = 'expiring';
        expiringSoon++;
      }
    }

    return {
      id: d.id,
      name: d.filename,
      expiry_date: expiryDate,
      days_until_expiry: daysUntilExpiry,
      status,
    };
  });

  return { items, total: count || 0, expiringSoon };
}

async function getFaultHistory(supabase: any, yachtId: string) {
  const { data } = await supabase
    .from('faults')
    .select(`
      id,
      fault_code,
      title,
      severity,
      detected_at,
      resolved_at,
      equipment:equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .order('detected_at', { ascending: false })
    .limit(50);

  let activeCount = 0;
  let resolved30d = 0;
  const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;

  const items = (data || []).map((f: any) => {
    if (!f.resolved_at) activeCount++;
    if (f.resolved_at && new Date(f.resolved_at).getTime() > thirtyDaysAgo) resolved30d++;

    return {
      id: f.id,
      fault_code: f.fault_code,
      title: f.title,
      equipment_name: f.equipment?.name,
      severity: f.severity,
      detected_at: f.detected_at,
      resolved_at: f.resolved_at,
    };
  });

  return { items, activeCount, resolved30d };
}

async function getScheduledMaintenance(supabase: any, yachtId: string) {
  const { data } = await supabase
    .from('work_orders')
    .select(`
      id,
      title,
      due_date,
      status,
      frequency,
      equipment:equipment_id (name)
    `)
    .eq('yacht_id', yachtId)
    .eq('type', 'scheduled')
    .order('due_date', { ascending: true })
    .limit(50);

  let upcoming7d = 0;
  let overdueCount = 0;
  const sevenDaysFromNow = Date.now() + 7 * 24 * 60 * 60 * 1000;

  const items = (data || []).map((wo: any) => {
    const dueDate = new Date(wo.due_date).getTime();
    if (dueDate < Date.now() && !['completed', 'cancelled'].includes(wo.status)) overdueCount++;
    if (dueDate <= sevenDaysFromNow && dueDate > Date.now()) upcoming7d++;

    return {
      id: wo.id,
      title: wo.title,
      equipment_name: wo.equipment?.name,
      due_date: wo.due_date,
      frequency: wo.frequency?.type,
      status: wo.status,
    };
  });

  return { items, upcoming7d, overdueCount };
}

async function getPartsUsage(supabase: any, yachtId: string) {
  // Aggregate part usage from work_order_history
  const { data } = await supabase
    .from('work_order_history')
    .select('parts_used')
    .eq('yacht_id', yachtId)
    .gte('completed_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString());

  const usage: Record<string, number> = {};
  (data || []).forEach((h: any) => {
    const parts = h.parts_used || [];
    parts.forEach((p: any) => {
      usage[p.part_id] = (usage[p.part_id] || 0) + (p.quantity || 1);
    });
  });

  // Get part names
  const partIds = Object.keys(usage);
  if (partIds.length === 0) return [];

  const { data: partData } = await supabase
    .from('parts')
    .select('id, name')
    .in('id', partIds);

  const partNames: Record<string, string> = {};
  (partData || []).forEach((p: any) => {
    partNames[p.id] = p.name;
  });

  return Object.entries(usage).map(([id, count]) => ({
    part_id: id,
    part_name: partNames[id] || 'Unknown',
    usage_30d: count,
    avg_monthly: count,
  }));
}

async function getDocumentsSummary(supabase: any, yachtId: string) {
  const { count: total } = await supabase
    .from('documents')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', yachtId);

  const { count: indexed } = await supabase
    .from('documents')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', yachtId)
    .eq('indexed', true);

  return {
    total: total || 0,
    indexed: indexed || 0,
    by_type: {},
  };
}

export default dashboard;
