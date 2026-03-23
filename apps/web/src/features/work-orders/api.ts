import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { WorkOrder } from './types';

export async function fetchWorkOrders(params: FetchParams): Promise<FetchResponse<WorkOrder>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_work_orders')
    .select(
      'id, wo_number, title, description, status, priority, equipment_id, assigned_to, due_date, created_at, updated_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch work orders: ${error.message}`);
  }

  return { data: (data ?? []) as WorkOrder[], total: count ?? 0 };
}

export async function fetchWorkOrder(id: string, _token: string): Promise<WorkOrder> {
  const { data, error } = await supabase
    .from('pms_work_orders')
    .select(
      'id, wo_number, title, description, status, priority, equipment_id, assigned_to, due_date, created_at, updated_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Work order ${id} not found`);
  }

  return data as WorkOrder;
}
