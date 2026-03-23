import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Fault } from './types';

export async function fetchFaults(params: FetchParams): Promise<FetchResponse<Fault>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_faults')
    .select(
      'id, fault_code, title, description, status, severity, equipment_id, detected_at, resolved_at, created_at, updated_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch faults: ${error.message}`);
  }

  return { data: (data ?? []) as Fault[], total: count ?? 0 };
}

export async function fetchFault(id: string, _token: string): Promise<Fault> {
  const { data, error } = await supabase
    .from('pms_faults')
    .select(
      'id, fault_code, title, description, status, severity, equipment_id, detected_at, resolved_at, created_at, updated_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Fault ${id} not found`);
  }

  return data as Fault;
}
