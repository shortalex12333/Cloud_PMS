export interface WorkOrder {
  id: string;
  wo_number: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  /** Logical sub-type — preventive / corrective / scheduled / unplanned. */
  type?: string;
  /** Deprecated alias for `type` on older rows; keep both until DB is cleaned. */
  work_order_type?: string;
  /** Crit assessment — distinct from priority. UX sheet line 340. */
  severity?: string;
  /** Recurrence cadence (daily / weekly / monthly / annual). UX line 316. */
  frequency?: string;
  equipment_id?: string;
  equipment_name?: string;
  assigned_to?: string;
  assigned_to_id?: string;
  assigned_to_name?: string;
  due_date?: string;
  /** Exact datetime the WO was marked complete. UX line 334. */
  completed_at?: string;
  // ── PR-WO-7 schema additions (UX sheet lines 354-356) ──────────────────
  /** Parent system UUID. FK → pms_equipment.id (top-level). */
  system_id?: string;
  /** Denormalised parent system name for frontend ergonomics. */
  system_name?: string;
  /** Whether this WO tracks running hours (rotating machinery). */
  running_hours_required?: boolean;
  /** Current running-hours reading at WO creation. */
  running_hours_current?: number;
  /** Running-hours checkpoint at which service is due. */
  running_hours_checkpoint?: number;
  created_at: string;
  updated_at?: string;
}
