export interface ShoppingListItem {
  id: string;
  part_id?: string;
  part_name?: string;
  part_number?: string;
  description?: string;
  quantity_requested: number;
  quantity_approved?: number;
  unit_of_measure?: string;
  status: string;
  priority?: string;
  requested_by_id?: string;
  requested_by_name?: string;
  approved_by_id?: string;
  approved_by_name?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}
