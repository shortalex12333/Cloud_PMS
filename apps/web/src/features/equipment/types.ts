export interface Equipment {
  id: string;
  equipment_number?: string;
  name: string;
  description?: string;
  category?: string;
  location?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  status: string;
  last_service_date?: string;
  next_service_date?: string;
  created_at: string;
  updated_at?: string;
}
