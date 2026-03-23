import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Equipment } from './types';

export async function fetchEquipment(params: FetchParams): Promise<FetchResponse<Equipment>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_equipment')
    .select(
      'id, name, description, status, criticality, location, manufacturer, model, serial_number, attention_flag, attention_reason, created_at, updated_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch equipment: ${error.message}`);
  }

  return { data: (data ?? []) as Equipment[], total: count ?? 0 };
}

export async function fetchEquipmentItem(id: string, _token: string): Promise<Equipment> {
  const { data, error } = await supabase
    .from('pms_equipment')
    .select(
      'id, name, description, status, criticality, location, manufacturer, model, serial_number, attention_flag, attention_reason, created_at, updated_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Equipment ${id} not found`);
  }

  return data as Equipment;
}
