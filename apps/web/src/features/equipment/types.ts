export interface Equipment {
  id: string;
  equipment_number?: string;
  code?: string | null;
  name: string;
  description?: string;
  category?: string;
  system_type?: string | null;
  location?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  status: string;
  criticality?: string | null;
  running_hours?: number | null;
  last_service_date?: string;
  next_service_date?: string;
  deleted_at?: string | null;
  created_at: string;
  updated_at?: string;
}
