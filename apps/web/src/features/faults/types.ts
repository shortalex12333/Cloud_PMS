export interface Fault {
  id: string;
  fault_number?: string;
  title: string;
  description?: string;
  status: string;
  severity: string;
  equipment_id?: string;
  equipment_name?: string;
  reported_by_id?: string;
  reported_by_name?: string;
  acknowledged_at?: string;
  resolved_at?: string;
  created_at: string;
  updated_at?: string;
}
