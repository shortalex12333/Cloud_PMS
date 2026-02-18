'use client';

/**
 * LensRenderer - Renders entity lenses inside ContextPanel
 *
 * Per rules.md 1-URL philosophy:
 * - All lenses render within ContextPanel, not at separate page routes
 * - Back button uses NavigationContext stack (if available), or closes panel
 * - Close button returns to search-dominant state
 *
 * This component acts as an adapter between ContextPanel and lens components,
 * providing them with the navigation callbacks they need.
 */

import React from 'react';
import { useSurface } from '@/contexts/SurfaceContext';
import { useNavigationContextSafe } from '@/contexts/NavigationContext';

// Lens content components
import { WorkOrderLensContent } from './WorkOrderLensContent';
import { FaultLensContent } from './FaultLensContent';
import { EquipmentLensContent } from './EquipmentLensContent';
import { PartsLensContent } from './PartsLensContent';
import { ReceivingLensContent } from './ReceivingLensContent';
import { CertificateLensContent } from './CertificateLensContent';
import { HandoverLensContent } from './HandoverLensContent';
import { HoursOfRestLensContent } from './HoursOfRestLensContent';
import { WarrantyLensContent } from './WarrantyLensContent';
import { ShoppingListLensContent } from './ShoppingListLensContent';
import { DocumentLensContent } from './DocumentLensContent';

export interface LensRendererProps {
  /** Entity type to render */
  entityType: string;
  /** Entity ID */
  entityId: string;
  /** Entity data from backend */
  entityData: Record<string, unknown>;
  /** Loading state */
  loading?: boolean;
  /** Callback to refresh entity data */
  onRefresh?: () => void;
}

/**
 * LensRenderer - Maps entity types to their lens content components.
 *
 * Handles navigation callbacks:
 * - onBack: Uses NavigationContext.back() if available, otherwise closes panel
 * - onClose: Returns to search-dominant state via SurfaceContext.hideContext()
 * - onNavigate: Cross-lens navigation via showContext (pushes to nav stack)
 */
export function LensRenderer({
  entityType,
  entityId,
  entityData,
  loading,
  onRefresh,
}: LensRendererProps) {
  const { hideContext, showContext } = useSurface();
  // Use safe version that doesn't throw if NavigationProvider is missing
  const navigation = useNavigationContextSafe();

  // Back handler: go back in stack or close
  const handleBack = React.useCallback(() => {
    if (navigation?.canGoBack) {
      navigation.back();
    } else {
      hideContext();
    }
  }, [navigation, hideContext]);

  // Close handler: always return to search
  const handleClose = React.useCallback(() => {
    navigation?.endContext();
    hideContext();
  }, [navigation, hideContext]);

  // Navigate to another entity (cross-lens navigation)
  const handleNavigate = React.useCallback(
    (targetType: string, targetId: string) => {
      // Update navigation context stack if available
      navigation?.pushViewer(targetType, targetId);
      // Also update surface context to render new entity
      showContext(targetType, targetId);
    },
    [navigation, showContext]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-celeste-text-muted">
          Loading {entityType}...
        </div>
      </div>
    );
  }

  // Common props passed to all lens content components
  const commonProps = {
    id: entityId,
    data: entityData,
    onBack: handleBack,
    onClose: handleClose,
    onNavigate: handleNavigate,
    onRefresh,
  };

  // Render the appropriate lens content based on entity type
  switch (entityType) {
    case 'work_order':
      return <WorkOrderLensContent {...commonProps} />;
    case 'fault':
      return <FaultLensContent {...commonProps} />;
    case 'equipment':
      return <EquipmentLensContent {...commonProps} />;
    case 'part':
    case 'inventory':
      return <PartsLensContent {...commonProps} entityType={entityType} />;
    case 'receiving':
      return <ReceivingLensContent {...commonProps} />;
    case 'certificate':
      return <CertificateLensContent {...commonProps} />;
    case 'handover':
      return <HandoverLensContent {...commonProps} />;
    case 'hours_of_rest':
      return <HoursOfRestLensContent {...commonProps} />;
    case 'warranty':
      return <WarrantyLensContent {...commonProps} />;
    case 'shopping_list':
      return <ShoppingListLensContent {...commonProps} />;
    case 'document':
      return <DocumentLensContent {...commonProps} />;
    default:
      return (
        <div className="p-6 text-celeste-text-muted">
          <p>Unknown entity type: {entityType}</p>
          <p className="text-xs mt-2 text-celeste-text-disabled">
            Supported types: work_order, fault, equipment, part, inventory, receiving,
            certificate, handover, hours_of_rest, warranty, shopping_list, document
          </p>
        </div>
      );
  }
}

export default LensRenderer;
