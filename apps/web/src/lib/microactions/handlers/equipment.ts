/**
 * Equipment Domain Handlers
 *
 * TypeScript handlers for equipment-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

interface EquipmentData {
  id: string;
  yacht_id: string;
  name: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  status: string;
  location?: string;
  running_hours?: number;
  risk_score?: number;
  created_at: string;
}

/**
 * View equipment details
 */
export async function viewEquipmentDetails(
  context: ActionContext,
  params?: { equipment_id?: string }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'view_equipment_details',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: equipment, error } = await supabase
      .from('pms_equipment')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('id', equipmentId)
      .single();

    if (error || !equipment) {
      return {
        success: false,
        action_name: 'view_equipment_details',
        data: null,
        error: { code: 'NOT_FOUND', message: `Equipment not found: ${equipmentId}` },
        confirmation_required: false,
      };
    }

    // Get risk score from predictive state
    let riskScore = 0;
    try {
      const { data: predState } = await supabase
        .from('predictive_state')
        .select('risk_score')
        .eq('equipment_id', equipmentId)
        .single();
      riskScore = predState?.risk_score || 0;
    } catch {
      // Predictive state may not exist
    }

    const enrichedEquipment: EquipmentData = {
      ...equipment,
      risk_score: riskScore,
    };

    return {
      success: true,
      action_name: 'view_equipment_details',
      data: { equipment: enrichedEquipment },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_equipment_details',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * View equipment maintenance/work order history
 */
export async function viewEquipmentHistory(
  context: ActionContext,
  params?: { equipment_id?: string; offset?: number; limit?: number }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;
  const offset = params?.offset || 0;
  const limit = params?.limit || 20;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'view_equipment_history',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: workOrders, count, error } = await supabase
      .from('pms_work_orders')
      .select('*', { count: 'exact' })
      .eq('yacht_id', context.yacht_id)
      .eq('equipment_id', equipmentId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      return {
        success: false,
        action_name: 'view_equipment_history',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    const summary = {
      total: count || 0,
      open: (workOrders || []).filter((wo) =>
        ['open', 'in_progress', 'pending'].includes(wo.status)
      ).length,
      completed: (workOrders || []).filter((wo) =>
        ['completed', 'closed'].includes(wo.status)
      ).length,
    };

    return {
      success: true,
      action_name: 'view_equipment_history',
      data: {
        equipment_id: equipmentId,
        work_orders: workOrders || [],
        summary,
        pagination: { offset, limit, total: count || 0 },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_equipment_history',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * View parts associated with equipment
 */
export async function viewEquipmentParts(
  context: ActionContext,
  params?: { equipment_id?: string }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'view_equipment_parts',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get parts for this yacht (parts table doesn't have equipment_id FK)
    const { data: parts, error } = await supabase
      .from('pms_parts')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .limit(50);

    if (error) {
      return {
        success: false,
        action_name: 'view_equipment_parts',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Add stock status to each part
    const enrichedParts = (parts || []).map((part) => ({
      ...part,
      stock_status: computeStockStatus(part),
      is_low_stock: ['LOW_STOCK', 'OUT_OF_STOCK'].includes(computeStockStatus(part)),
    }));

    const summary = {
      total: enrichedParts.length,
      low_stock: enrichedParts.filter((p) => p.is_low_stock).length,
      in_stock: enrichedParts.filter((p) => p.stock_status === 'IN_STOCK').length,
    };

    return {
      success: true,
      action_name: 'view_equipment_parts',
      data: {
        equipment_id: equipmentId,
        parts: enrichedParts,
        summary,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_equipment_parts',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Compute stock status for a part
 */
function computeStockStatus(part: { quantity?: number; min_quantity?: number }): string {
  const qty = part.quantity || 0;
  const minQty = part.min_quantity || 0;

  if (qty <= 0) return 'OUT_OF_STOCK';
  if (qty <= minQty) return 'LOW_STOCK';
  return 'IN_STOCK';
}

/**
 * View faults linked to equipment
 */
export async function viewLinkedFaults(
  context: ActionContext,
  params?: { equipment_id?: string; offset?: number; limit?: number }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;
  const offset = params?.offset || 0;
  const limit = params?.limit || 20;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'view_linked_faults',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: faults, count, error } = await supabase
      .from('pms_faults')
      .select('*', { count: 'exact' })
      .eq('yacht_id', context.yacht_id)
      .eq('equipment_id', equipmentId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      return {
        success: false,
        action_name: 'view_linked_faults',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Add computed fields
    const enrichedFaults = (faults || []).map((fault) => {
      const isActive = !fault.resolved_at;
      let daysOpen = 0;

      if (isActive && fault.created_at) {
        try {
          const reported = new Date(fault.created_at);
          daysOpen = Math.floor((new Date().getTime() - reported.getTime()) / (1000 * 60 * 60 * 24));
        } catch {
          daysOpen = 0;
        }
      }

      return { ...fault, is_active: isActive, days_open: daysOpen };
    });

    const summary = {
      total: count || 0,
      active: enrichedFaults.filter((f) => f.is_active).length,
      critical: enrichedFaults.filter((f) => f.severity === 'critical').length,
      high: enrichedFaults.filter((f) => f.severity === 'high').length,
    };

    return {
      success: true,
      action_name: 'view_linked_faults',
      data: {
        equipment_id: equipmentId,
        faults: enrichedFaults,
        summary,
        pagination: { offset, limit, total: count || 0 },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_linked_faults',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * View equipment manual sections
 */
export async function viewEquipmentManual(
  context: ActionContext,
  params?: { equipment_id?: string }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'view_equipment_manual',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get equipment name for search
    const { data: equipment, error: eqError } = await supabase
      .from('pms_equipment')
      .select('name')
      .eq('id', equipmentId)
      .single();

    if (eqError || !equipment) {
      return {
        success: false,
        action_name: 'view_equipment_manual',
        data: null,
        error: { code: 'NOT_FOUND', message: `Equipment not found: ${equipmentId}` },
        confirmation_required: false,
      };
    }

    // Search document chunks for this equipment
    const { data: chunks } = await supabase
      .from('document_chunks')
      .select('id, document_id, section_title, page_number, content')
      .eq('yacht_id', context.yacht_id)
      .ilike('content', `%${equipment.name}%`)
      .limit(10);

    const manualSections = (chunks || []).map((c) => ({
      chunk_id: c.id,
      document_id: c.document_id,
      section_title: c.section_title,
      page_number: c.page_number,
      content_preview: c.content ? c.content.substring(0, 200) + '...' : '',
    }));

    const uniqueDocIds = [...new Set((chunks || []).map((c) => c.document_id).filter(Boolean))];

    return {
      success: true,
      action_name: 'view_equipment_manual',
      data: {
        equipment_id: equipmentId,
        equipment_label: equipment.name,
        manual_sections: manualSections,
        document_count: uniqueDocIds.length,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_equipment_manual',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Run diagnostic on equipment
 */
export async function runDiagnostic(
  context: ActionContext,
  params?: { equipment_id?: string }
): Promise<ActionResult> {
  
  const equipmentId = params?.equipment_id || context.entity_id;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'run_diagnostic',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get equipment info
    const { data: equipment, error: eqError } = await supabase
      .from('pms_equipment')
      .select('*')
      .eq('id', equipmentId)
      .single();

    if (eqError || !equipment) {
      return {
        success: false,
        action_name: 'run_diagnostic',
        data: null,
        error: { code: 'NOT_FOUND', message: `Equipment not found: ${equipmentId}` },
        confirmation_required: false,
      };
    }

    // Get latest sensor readings
    let sensors: Array<{
      sensor_type: string;
      value: number;
      unit: string;
      timestamp: string;
      is_anomaly?: boolean;
    }> = [];
    try {
      const { data: sensorData } = await supabase
        .from('sensor_readings')
        .select('sensor_type, value, unit, timestamp, is_anomaly')
        .eq('equipment_id', equipmentId)
        .order('timestamp', { ascending: false })
        .limit(10);
      sensors = sensorData || [];
    } catch {
      // Sensor readings may not exist
    }

    // Get predictive state
    let predictive: {
      risk_score: number;
      confidence: number;
      failure_probability: number;
      trend: string;
      anomalies: string[];
      next_maintenance_due?: string;
    } = {
      risk_score: 0,
      confidence: 0,
      failure_probability: 0,
      trend: 'stable',
      anomalies: [],
    };

    try {
      const { data: predData } = await supabase
        .from('predictive_state')
        .select('risk_score, confidence, anomalies, next_maintenance_due, failure_probability, trend')
        .eq('equipment_id', equipmentId)
        .single();
      if (predData) {
        predictive = {
          risk_score: predData.risk_score || 0,
          confidence: predData.confidence || 0,
          failure_probability: predData.failure_probability || 0,
          trend: predData.trend || 'stable',
          anomalies: predData.anomalies || [],
          next_maintenance_due: predData.next_maintenance_due,
        };
      }
    } catch {
      // Predictive state may not exist
    }

    // Get active faults
    const { data: activeFaults } = await supabase
      .from('pms_faults')
      .select('id, fault_code, severity, detected_at')
      .eq('equipment_id', equipmentId)
      .is('resolved_at', null);

    // Compute health status
    const healthStatus = computeHealthStatus(predictive, activeFaults || []);

    return {
      success: true,
      action_name: 'run_diagnostic',
      data: {
        equipment,
        sensor_readings: sensors,
        predictive_state: predictive,
        active_faults: activeFaults || [],
        health_status: healthStatus,
        ran_at: new Date().toISOString(),
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'run_diagnostic',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Compute overall equipment health status
 */
function computeHealthStatus(
  predictive: { risk_score: number },
  activeFaults: Array<{ severity?: string }>
): string {
  const riskScore = predictive.risk_score || 0;
  const criticalFaults = activeFaults.filter((f) => f.severity === 'critical').length;
  const highFaults = activeFaults.filter((f) => f.severity === 'high').length;

  if (criticalFaults > 0 || riskScore > 0.8) return 'CRITICAL';
  if (highFaults > 0 || riskScore > 0.6) return 'WARNING';
  if (activeFaults.length > 0 || riskScore > 0.4) return 'ATTENTION';
  return 'HEALTHY';
}

/**
 * Get all equipment handlers for registration
 */
export const equipmentHandlers = {
  view_equipment_details: viewEquipmentDetails,
  view_equipment_history: viewEquipmentHistory,
  view_equipment_parts: viewEquipmentParts,
  view_linked_faults: viewLinkedFaults,
  view_equipment_manual: viewEquipmentManual,
  run_diagnostic: runDiagnostic,
};
