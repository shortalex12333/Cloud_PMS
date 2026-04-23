/**
 * Shopping List types — field names mirror pms_shopping_list_items columns
 * (TENANT DB). Name fields (requested_by_name, approved_by_name) are NOT
 * columns — they are resolved by the backend from auth_users_profiles and
 * attached to the record before it hits the adapter.
 */

export interface ShoppingListItem {
  id: string;
  yacht_id?: string;
  part_id?: string;
  part_name?: string;
  part_number?: string;
  manufacturer?: string;
  is_candidate_part?: boolean;
  quantity_requested?: number;
  quantity_approved?: number;
  quantity_ordered?: number;
  quantity_received?: number;
  quantity_installed?: number;
  unit?: string;
  preferred_supplier?: string;
  estimated_unit_price?: number;
  status: string;
  source_type?: string;
  source_work_order_id?: string;
  source_receiving_id?: string;
  source_notes?: string;
  urgency?: string;
  required_by_date?: string;
  // FK UUIDs — never rendered directly
  requested_by?: string;
  approved_by?: string;
  rejected_by?: string;
  // Resolved names — attached by backend (not DB columns)
  requested_by_name?: string;
  approved_by_name?: string;
  approved_at?: string;
  approval_notes?: string;
  rejected_at?: string;
  rejection_reason?: string;
  rejection_notes?: string;
  fulfilled_at?: string;
  installed_at?: string;
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
