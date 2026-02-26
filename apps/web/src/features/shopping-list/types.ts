export interface ShoppingListItem {
  id: string;
  yacht_id?: string;
  part_id?: string;
  part_name?: string;
  part_number?: string;
  manufacturer?: string;
  description?: string;
  quantity_requested: number;
  quantity_approved?: number;
  unit_of_measure?: string;
  status: string;
  priority?: string;
  urgency?: string;
  is_candidate_part?: boolean;
  source_type?: string;
  source_work_order_id?: string;
  source_receiving_id?: string;
  source_notes?: string;
  requested_by_id?: string;
  requested_by_name?: string;
  approved_by_id?: string;
  approved_by_name?: string;
  notes?: string;
  required_by_date?: string;
  created_at: string;
  updated_at?: string;
}

export interface ShoppingListStateHistory {
  id: string;
  shopping_list_item_id: string;
  previous_state?: string;
  new_state: string;
  transition_reason?: string;
  transition_notes?: string;
  changed_by: string;
  changed_by_name?: string;
  changed_at: string;
  related_order_id?: string;
  related_receiving_event_id?: string;
}

export interface CreateShoppingListItemPayload {
  part_name: string;
  quantity_requested: number;
  source_type?: string;
  part_id?: string;
  part_number?: string;
  manufacturer?: string;
  urgency?: string;
  required_by_date?: string;
  source_work_order_id?: string;
  source_notes?: string;
}
