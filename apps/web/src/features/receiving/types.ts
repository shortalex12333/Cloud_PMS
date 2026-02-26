export interface ReceivingItem {
  id: string;
  receiving_number?: string;
  supplier_name?: string;
  description?: string;
  status: string;
  received_date?: string;
  expected_date?: string;
  items_count?: number;
  total_value?: number;
  currency?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}
