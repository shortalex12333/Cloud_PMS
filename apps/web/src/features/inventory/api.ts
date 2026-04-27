import { API_BASE } from '@/lib/apiBase';
import type { Part } from './types';

export async function fetchPart(id: string, token: string): Promise<Part> {
  const res = await fetch(`${API_BASE}/v1/entity/part/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Part ${id} not found`);
  const raw = await res.json();
  return {
    ...raw,
    quantity_on_hand: raw.stock_quantity ?? raw.quantity_on_hand ?? 0,
    minimum_quantity: raw.min_stock_level ?? raw.minimum_quantity ?? null,
    unit_of_measure: raw.unit_of_measure ?? raw.unit ?? null,
  } as Part;
}
