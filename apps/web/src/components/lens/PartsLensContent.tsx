'use client';

/**
 * PartsLensContent - Inner content for Parts/Inventory lens (no LensContainer).
 * Renders inside ContextPanel following the 1-URL philosophy.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { formatRelativeTime } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { GhostButton } from '@/components/ui/GhostButton';

export interface PartsLensContentProps {
  id: string;
  data: Record<string, unknown>;
  entityType?: 'part' | 'inventory';
  onBack: () => void;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
  onRefresh?: () => void;
}

function mapStockStatus(current: number, minimum: number): 'critical' | 'warning' | 'success' | 'neutral' {
  if (current <= 0) return 'critical';
  if (current < minimum) return 'warning';
  return 'success';
}

export function PartsLensContent({
  id,
  data,
  entityType = 'part',
  onBack,
  onClose,
  onNavigate,
  onRefresh,
}: PartsLensContentProps) {
  // Map data
  const part_name = (data.name as string) || (data.part_name as string) || 'Part';
  const part_number = data.part_number as string | undefined;
  const stock_quantity = (data.quantity_on_hand as number) || (data.stock_quantity as number) || 0;
  const min_stock_level = (data.minimum_quantity as number) || (data.min_stock_level as number) || 0;
  const location = (data.location as string) || 'Unknown';
  const unit = data.unit as string | undefined;
  const unit_cost = data.unit_cost as number | undefined;
  const supplier = data.supplier as string | undefined;
  const category = data.category as string | undefined;
  const last_counted_at = data.last_counted_at as string | undefined;

  const stockColor = mapStockStatus(stock_quantity, min_stock_level);
  const stockLabel = stock_quantity <= 0 ? 'Out of Stock' :
                     stock_quantity < min_stock_level ? 'Low Stock' : 'In Stock';

  const vitalSigns: VitalSign[] = [
    { label: 'Stock', value: stockLabel, color: stockColor },
    { label: 'Quantity', value: `${stock_quantity}${unit ? ` ${unit}` : ''}` },
    { label: 'Min Level', value: `${min_stock_level}${unit ? ` ${unit}` : ''}` },
    { label: 'Location', value: location },
    { label: 'Last Count', value: last_counted_at ? formatRelativeTime(last_counted_at) : '—' },
  ];

  return (
    <div className="flex flex-col h-full">
      <LensHeader
        entityType={entityType === 'inventory' ? 'Inventory' : 'Part'}
        title={part_name}
        onBack={onBack}
        onClose={onClose}
      />

      <main className={cn('flex-1 overflow-y-auto pt-14 px-10 md:px-6 sm:px-4 max-w-[800px] mx-auto w-full pb-12')}>
        <div className="mt-6">
          <LensTitleBlock
            title={part_name}
            subtitle={part_number ? `Part #${part_number}` : undefined}
            status={{ label: stockLabel, color: stockColor }}
          />
        </div>

        <div className="mt-3">
          <VitalSignsRow signs={vitalSigns} />
        </div>

        <div className="mt-4 flex items-center gap-2">
          <PrimaryButton onClick={() => console.log('[PartsLens] Log usage:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Log Usage</PrimaryButton>
          <GhostButton onClick={() => console.log('[PartsLens] Count stock:', id)} className="text-[13px] min-h-[36px] px-4 py-2">Count Stock</GhostButton>
        </div>

        <div className="mt-6 border-t border-surface-border" aria-hidden="true" />

        <div className="mt-6">
          <SectionContainer title="Details" stickyTop={56}>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              {part_number && (
                <>
                  <dt className="text-txt-tertiary">Part Number</dt>
                  <dd className="text-txt-primary">{part_number}</dd>
                </>
              )}
              {category && (
                <>
                  <dt className="text-txt-tertiary">Category</dt>
                  <dd className="text-txt-primary">{category}</dd>
                </>
              )}
              {supplier && (
                <>
                  <dt className="text-txt-tertiary">Supplier</dt>
                  <dd className="text-txt-primary">{supplier}</dd>
                </>
              )}
              {unit_cost !== undefined && (
                <>
                  <dt className="text-txt-tertiary">Unit Cost</dt>
                  <dd className="text-txt-primary">${unit_cost.toFixed(2)}</dd>
                </>
              )}
            </dl>
          </SectionContainer>
        </div>
      </main>
    </div>
  );
}

export default PartsLensContent;
