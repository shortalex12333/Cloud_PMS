import type { EntityListResult } from '@/features/entity-list/types';
import type { Equipment } from './types';

export function equipmentToListResult(equipment: Equipment): EntityListResult {
  const statusDisplay = equipment.status?.replace(/_/g, ' ') || 'Active';

  return {
    id: equipment.id,
    type: 'pms_equipment',
    title: equipment.name || `Equipment ${equipment.equipment_number || 'Equipment'}`,
    subtitle: `${statusDisplay}${equipment.category ? ` \u00b7 ${equipment.category}` : ''}${equipment.location ? ` \u00b7 ${equipment.location}` : ''}`,
    snippet: equipment.description,
    metadata: {
      status: equipment.status,
      category: equipment.category,
      code: equipment.code ?? null,
      system_type: equipment.system_type ?? null,
      criticality: equipment.criticality ?? null,
      running_hours: equipment.running_hours ?? null,
      serial_number: equipment.serial_number ?? null,
      location: equipment.location,
      manufacturer: equipment.manufacturer,
      model: equipment.model,
      deleted_at: equipment.deleted_at ?? null,
      created_at: equipment.created_at,
      updated_at: equipment.updated_at ?? null,
    },

    // Extended fields for EntityRecordRow
    entityRef: equipment.equipment_number || '',
    equipmentName: equipment.manufacturer && equipment.model
      ? `${equipment.manufacturer} ${equipment.model}`
      : undefined,
    assignedTo: undefined,
    status: statusDisplay,
    statusVariant: 'open',
    severity: null,
    age: '\u2014',
  };
}
