/**
 * Audit Log Test Helper
 * =====================
 *
 * Helper functions to verify audit log entries in mutation tests.
 * Part of Pattern H1 fix: Missing Audit Logs
 *
 * Created: 2026-01-22
 * Agent: Agent 4 (Bulk Fixer)
 */

import { createClient } from '@supabase/supabase-js';
import { expect } from '@playwright/test';

const supabase = createClient(
    process.env.TENANT_SUPABASE_URL!,
    process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY!
);

/**
 * Verify that an audit log entry exists for an action
 *
 * @param action - The action name (e.g., 'create_work_order')
 * @param entity_id - The entity ID that was created/modified
 * @param yacht_id - Optional yacht ID to verify (defaults to TEST_YACHT_ID)
 * @returns The audit log entry
 *
 * @example
 * ```typescript
 * const response = await executeAction('create_work_order', context, payload);
 * await verifyAuditLog('create_work_order', response.work_order_id);
 * ```
 */
export async function verifyAuditLog(
    action: string,
    entity_id: string,
    yacht_id?: string
) {
    const { data: audit, error } = await supabase
        .from('pms_audit_log')
        .select('*')
        .eq('action', action)
        .eq('entity_id', entity_id)
        .maybeSingle();

    // Verify audit log exists
    expect(error).toBeNull();
    expect(audit).toBeTruthy();

    if (!audit) {
        throw new Error(`Audit log not found for action=${action}, entity_id=${entity_id}`);
    }

    // Verify required fields
    expect(audit.action).toBe(action);
    expect(audit.entity_id).toBe(entity_id);
    expect(audit.yacht_id).toBeTruthy();
    expect(audit.user_id).toBeTruthy();

    // Verify yacht_id if provided
    if (yacht_id) {
        expect(audit.yacht_id).toBe(yacht_id);
    }

    // Verify signature structure
    expect(audit.signature).toBeTruthy();
    expect(audit.signature.user_id).toBeTruthy();
    expect(audit.signature.execution_id).toBeTruthy();
    expect(audit.signature.timestamp).toBeTruthy();

    console.log(`✅ Audit log verified for ${action}: ${entity_id}`);

    return audit;
}

/**
 * Verify audit log with expected values
 *
 * @param action - The action name
 * @param entity_id - The entity ID
 * @param expected_new_values - Expected values in new_values field
 * @param yacht_id - Optional yacht ID
 *
 * @example
 * ```typescript
 * await verifyAuditLogWithValues('create_work_order', id, {
 *   title: 'Test WO',
 *   priority: 'routine'
 * });
 * ```
 */
export async function verifyAuditLogWithValues(
    action: string,
    entity_id: string,
    expected_new_values: Record<string, any>,
    yacht_id?: string
) {
    const audit = await verifyAuditLog(action, entity_id, yacht_id);

    // Verify new_values contains expected fields
    expect(audit.new_values).toBeTruthy();

    for (const [key, value] of Object.entries(expected_new_values)) {
        if (audit.new_values[key] !== undefined) {
            expect(audit.new_values[key]).toBe(value);
        }
    }

    console.log(`✅ Audit log values verified for ${action}`);

    return audit;
}

/**
 * Verify audit log count for an action
 * Useful for checking that multiple operations created audit entries
 *
 * @param action - The action name
 * @param expected_count - Expected number of audit entries
 * @param yacht_id - Optional yacht ID filter
 *
 * @example
 * ```typescript
 * // After creating 3 work orders
 * await verifyAuditLogCount('create_work_order', 3);
 * ```
 */
export async function verifyAuditLogCount(
    action: string,
    expected_count: number,
    yacht_id?: string
) {
    let query = supabase
        .from('pms_audit_log')
        .select('*', { count: 'exact', head: true })
        .eq('action', action);

    if (yacht_id) {
        query = query.eq('yacht_id', yacht_id);
    }

    const { count, error } = await query;

    expect(error).toBeNull();
    expect(count).toBe(expected_count);

    console.log(`✅ Audit log count verified for ${action}: ${count}/${expected_count}`);

    return count;
}

/**
 * Clean up audit log entries (for test cleanup)
 *
 * @param entity_id - The entity ID to clean up audit logs for
 *
 * @example
 * ```typescript
 * // In test cleanup
 * await cleanupAuditLog(work_order_id);
 * ```
 */
export async function cleanupAuditLog(entity_id: string) {
    const { error } = await supabase
        .from('pms_audit_log')
        .delete()
        .eq('entity_id', entity_id);

    if (error) {
        console.warn(`⚠️ Failed to cleanup audit log for entity_id=${entity_id}: ${error.message}`);
    } else {
        console.log(`🧹 Cleaned up audit log for entity_id=${entity_id}`);
    }
}
