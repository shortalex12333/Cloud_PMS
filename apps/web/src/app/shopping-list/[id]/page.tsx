'use client';

/**
 * Shopping List Detail Page - /shopping-list/[id]
 *
 * Thin shell: delegates all data fetching, action execution, and layout to
 * EntityLensPage. Entity-specific UI lives in ShoppingListLensContent.
 *
 * @see REQUIREMENTS_TABLE.md - T1-SL-02
 */

import { useParams } from 'next/navigation';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { ShoppingListContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

function LensContent() {
  return <div className={lensStyles.root}><ShoppingListContent /></div>;
}

export default function ShoppingListDetailPage() {
  const params = useParams();
  return (
    <EntityLensPage
      entityType="shopping_list"
      entityId={params.id as string}
      content={LensContent}
    />
  );
}
