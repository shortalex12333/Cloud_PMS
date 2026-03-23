import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Part } from './types';

export async function fetchParts(params: FetchParams): Promise<FetchResponse<Part>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_parts')
    .select(
      'id, name, part_number, description, category, manufacturer, quantity_on_hand, minimum_quantity, unit, location, is_critical, created_at, updated_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch parts: ${error.message}`);
  }

  return { data: (data ?? []) as Part[], total: count ?? 0 };
}

export async function fetchPart(id: string, _token: string): Promise<Part> {
  const { data, error } = await supabase
    .from('pms_parts')
    .select(
      'id, name, part_number, description, category, manufacturer, quantity_on_hand, minimum_quantity, unit, location, is_critical, created_at, updated_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Part ${id} not found`);
  }

  return data as Part;
}
