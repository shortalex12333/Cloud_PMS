/**
 * normalizeWarrantyEntity — maps raw /v1/entity/warranty/{id} response
 * to the shape WarrantyContent.tsx expects.
 *
 * Field deviations from the API:
 *  - API: claim_number     → component: claim_number (no change)
 *  - API: vendor_name      → component: vendor_name (no change — component was wrong, now fixed)
 *  - API: expiry_date      → component: expiry_date (matches ✓)
 *  - API: claimed_amount   → component: claimed_amount (no change — component was wrong, now fixed)
 *  - API: equipment_name   → component: equipment_name ✓
 *  - API: days_until_expiry → component: days_until_expiry ✓
 *  - MISSING in old component: status_label, workflow_stage, drafted_at, rejection_reason, email_draft
 */
export function normalizeWarrantyEntity(data: Record<string, unknown>): Record<string, unknown> {
  // No-op if already normalized
  if (!data) return data;
  return {
    ...data,
    // Ensure consistent field names (defensive aliases)
    claim_number:      data.claim_number ?? data.warranty_number,
    vendor_name:       data.vendor_name ?? data.provider ?? data.supplier,
    expiry_date:       data.expiry_date ?? data.end_date ?? data.warranty_expiry,
    claimed_amount:    data.claimed_amount ?? data.total_claimed,
    equipment_name:    data.equipment_name ?? (data.equipment as Record<string, unknown> | undefined)?.name,
    equipment_code:    data.equipment_code ?? (data.equipment as Record<string, unknown> | undefined)?.code,
    days_until_expiry: data.days_until_expiry ?? null,
    status_label:      data.status_label ?? (data.status as string ?? '').replace(/_/g, ' '),
    workflow_stage:    data.workflow_stage ?? 0,
    drafted_at:        data.drafted_at ?? data.created_at,
    rejection_reason:  data.rejection_reason ?? null,
    email_draft:       data.email_draft ?? null,
    // Ensure arrays are never undefined
    notes:             Array.isArray(data.notes) ? data.notes : [],
    attachments:       Array.isArray(data.attachments) ? data.attachments : [],
    related_entities:  Array.isArray(data.related_entities) ? data.related_entities : [],
  };
}
