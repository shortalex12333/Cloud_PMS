export interface Part {
  id: string;
  part_number: string;
  name: string;
  description?: string;
  category?: string;
  manufacturer?: string;
  quantity_on_hand: number;
  minimum_quantity?: number;
  unit_of_measure?: string;
  location?: string;
  price?: number;
  currency?: string;
  created_at: string;
  updated_at?: string;
}
