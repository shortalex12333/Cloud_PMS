/**
 * Action Router - Logger
 *
 * Log all action executions to the database for audit trail.
 */

import { supabase } from '@/lib/supabaseClient';
import type { ActionLogEntry, ActionStatus } from './types';

// ============================================================================
// SENSITIVE FIELD PATTERNS
// ============================================================================

const SENSITIVE_PATTERNS = [
  /password/i,
  /secret/i,
  /token/i,
  /api_key/i,
  /apikey/i,
  /credential/i,
  /private_key/i,
  /auth/i,
];

// ============================================================================
// SANITIZATION
// ============================================================================

/**
 * Sanitize payload by redacting sensitive fields
 *
 * @param payload - Payload to sanitize
 * @returns Sanitized payload
 */
export function sanitizePayload(
  payload: Record<string, unknown>
): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(payload)) {
    // Check if key matches sensitive pattern
    const isSensitive = SENSITIVE_PATTERNS.some((pattern) => pattern.test(key));

    if (isSensitive) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizePayload(value as Record<string, unknown>);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

// ============================================================================
// ACTION LOGGING
// ============================================================================

/**
 * Log an action execution to the database
 *
 * @param entry - Log entry data
 * @returns Log entry ID or null on error
 */
export async function logAction(entry: {
  actionId: string;
  actionLabel: string;
  yachtId: string;
  userId: string;
  payload: Record<string, unknown>;
  status: ActionStatus;
  result?: Record<string, unknown>;
  errorMessage?: string;
  durationMs?: number;
}): Promise<string | null> {
  try {
    // Sanitize payload and result
    const sanitizedPayload = sanitizePayload(entry.payload);
    const sanitizedResult = entry.result
      ? sanitizePayload(entry.result)
      : undefined;

    const logEntry: ActionLogEntry = {
      yacht_id: entry.yachtId,
      user_id: entry.userId,
      action_id: entry.actionId,
      action_label: entry.actionLabel,
      payload: sanitizedPayload,
      status: entry.status,
      result: sanitizedResult,
      error_message: entry.errorMessage,
      duration_ms: entry.durationMs,
    };

    const { data, error } = await supabase
      .from('action_executions')
      .insert(logEntry)
      .select('id')
      .single();

    if (error) {
      console.error('Failed to log action:', error);
      return null;
    }

    return data.id;
  } catch (error) {
    console.error('Failed to log action:', error);
    return null;
  }
}

// ============================================================================
// ACTION STATISTICS
// ============================================================================

/**
 * Get action execution statistics for a yacht
 *
 * @param yachtId - Yacht ID
 * @param hours - Time period in hours (default 24)
 * @returns Action statistics
 */
export async function getActionStats(
  yachtId: string,
  hours: number = 24
): Promise<{
  total: number;
  success: number;
  error: number;
  byAction: Record<string, { total: number; success: number }>;
  avgDurationMs: number;
}> {
  try {
    const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

    const { data, error } = await supabase
      .from('action_executions')
      .select('action_id, status, duration_ms')
      .eq('yacht_id', yachtId)
      .gte('created_at', since);

    if (error) {
      throw error;
    }

    const stats = {
      total: 0,
      success: 0,
      error: 0,
      byAction: {} as Record<string, { total: number; success: number }>,
      avgDurationMs: 0,
    };

    let totalDuration = 0;
    let durationCount = 0;

    for (const row of data || []) {
      stats.total++;

      if (row.status === 'success') {
        stats.success++;
      } else {
        stats.error++;
      }

      // Track by action
      if (!stats.byAction[row.action_id]) {
        stats.byAction[row.action_id] = { total: 0, success: 0 };
      }
      stats.byAction[row.action_id].total++;
      if (row.status === 'success') {
        stats.byAction[row.action_id].success++;
      }

      // Track duration
      if (row.duration_ms) {
        totalDuration += row.duration_ms;
        durationCount++;
      }
    }

    stats.avgDurationMs =
      durationCount > 0 ? Math.round(totalDuration / durationCount) : 0;

    return stats;
  } catch (error) {
    console.error('Failed to get action stats:', error);
    return {
      total: 0,
      success: 0,
      error: 0,
      byAction: {},
      avgDurationMs: 0,
    };
  }
}

// ============================================================================
// RECENT ACTIONS
// ============================================================================

/**
 * Get recent action executions for a yacht
 *
 * @param yachtId - Yacht ID
 * @param limit - Maximum number of results (default 50)
 * @returns Recent action log entries
 */
export async function getRecentActions(
  yachtId: string,
  limit: number = 50
): Promise<ActionLogEntry[]> {
  try {
    const { data, error } = await supabase
      .from('action_executions')
      .select('*')
      .eq('yacht_id', yachtId)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      throw error;
    }

    return (data || []) as ActionLogEntry[];
  } catch (error) {
    console.error('Failed to get recent actions:', error);
    return [];
  }
}

// ============================================================================
// ACTION HISTORY FOR ENTITY
// ============================================================================

/**
 * Get action history for a specific entity
 *
 * @param yachtId - Yacht ID
 * @param entityType - Type of entity (equipment_id, work_order_id, etc.)
 * @param entityId - Entity ID
 * @param limit - Maximum number of results (default 20)
 * @returns Action log entries for entity
 */
export async function getEntityActionHistory(
  yachtId: string,
  entityType: string,
  entityId: string,
  limit: number = 20
): Promise<ActionLogEntry[]> {
  try {
    // Query for actions where payload contains the entity
    const { data, error } = await supabase
      .from('action_executions')
      .select('*')
      .eq('yacht_id', yachtId)
      .contains('payload', { [entityType]: entityId })
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) {
      throw error;
    }

    return (data || []) as ActionLogEntry[];
  } catch (error) {
    console.error('Failed to get entity action history:', error);
    return [];
  }
}
