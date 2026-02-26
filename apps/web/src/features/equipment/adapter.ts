import type { EntityListResult } from '@/features/entity-list/types';
import type { Equipment } from './types';

export function equipmentToListResult(equipment: Equipment): EntityListResult {
  const statusDisplay = equipment.status?.replace(/_/g, ' ') || 'Active';

  return {
    id: equipment.id,
    type: 'pms_equipment',
    title: equipment.name || `Equipment ${equipment.equipment_number || equipment.id.slice(0, 8)}`,
    subtitle: `${statusDisplay}${equipment.category ? ` · ${equipment.category}` : ''}${equipment.location ? ` · ${equipment.location}` : ''}`,
    snippet: equipment.description,
    metadata: {
      status: equipment.status,
      category: equipment.category,
      location: equipment.location,
      manufacturer: equipment.manufacturer,
      model: equipment.model,
      created_at: equipment.created_at,
    },
  };
}
