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
  created_at: string;
  updated_at?: string;
}
