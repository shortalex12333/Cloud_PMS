import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export interface RelatedEntity {
  entity_type: string;
  entity_id: string;
  label: string;
}

export interface RelatedEntitiesSectionProps {
  entities: RelatedEntity[];
  onNavigate: (entityType: string, entityId: string) => void;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/** Format snake_case entity type to display label: work_order -> "Work Order" */
function formatEntityType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ============================================================================
// ENTITY ROW
// ============================================================================

interface EntityRowProps {
  entity: RelatedEntity;
  onNavigate: (entityType: string, entityId: string) => void;
}

function EntityRow({ entity, onNavigate }: EntityRowProps) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(entity.entity_type, entity.entity_id)}
      className={cn(
        'flex items-center justify-between w-full text-left',
        'px-5 py-3 min-h-11',
        'border-b border-surface-border-subtle last:border-b-0',
        'transition-colors duration-fast hover:bg-surface-hover'
      )}
    >
      <span className="text-body-strong text-celeste-blue truncate">
        {entity.label}
      </span>
      <span className="text-label text-txt-secondary flex-shrink-0 ml-3 px-2 py-0.5 bg-surface-secondary rounded">
        {formatEntityType(entity.entity_type)}
      </span>
    </button>
  );
}

// ============================================================================
// RELATED ENTITIES SECTION
// ============================================================================

export function RelatedEntitiesSection({
  entities,
  onNavigate,
  stickyTop,
}: RelatedEntitiesSectionProps) {
  return (
    <SectionContainer
      title="Related"
      count={entities.length}
      stickyTop={stickyTop}
    >
      <div className="-mx-4">
        {entities.map((entity) => (
          <EntityRow
            key={`${entity.entity_type}-${entity.entity_id}`}
            entity={entity}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </SectionContainer>
  );
}
