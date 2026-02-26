export interface WorkOrder {
  id: string;
  wo_number: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  equipment_id?: string;
  equipment_name?: string;
  assigned_to_id?: string;
  assigned_to_name?: string;
  due_date?: string;
  created_at: string;
  updated_at?: string;
}
