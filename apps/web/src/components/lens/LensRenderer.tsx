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

// Lens content components (lens-v2)
import { EntityLensPage } from './EntityLensPage';
import {
  WorkOrderContent,
  EquipmentContent,
  FaultContent,
  CertificateContent,
  PartsInventoryContent,
  PurchaseOrderContent,
  DocumentContent,
  WarrantyContent,
  HoursOfRestContent,
  ShoppingListContent,
  ReceivingContent,
  HandoverContent,
} from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';

// Wrapped content components with prototype token scoping
function WOContent() { return <div className={lensStyles.root}><WorkOrderContent /></div>; }
function EqContent() { return <div className={lensStyles.root}><EquipmentContent /></div>; }
function FtContent() { return <div className={lensStyles.root}><FaultContent /></div>; }
function CtContent() { return <div className={lensStyles.root}><CertificateContent /></div>; }
function PtContent() { return <div className={lensStyles.root}><PartsInventoryContent /></div>; }
function RcContent() { return <div className={lensStyles.root}><ReceivingContent /></div>; }
function HdContent() { return <div className={lensStyles.root}><HandoverContent /></div>; }
function HrContent() { return <div className={lensStyles.root}><HoursOfRestContent /></div>; }
function WrContent() { return <div className={lensStyles.root}><WarrantyContent /></div>; }
function SlContent() { return <div className={lensStyles.root}><ShoppingListContent /></div>; }
function DcContent() { return <div className={lensStyles.root}><DocumentContent /></div>; }
function PoContent() { return <div className={lensStyles.root}><PurchaseOrderContent /></div>; }

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
      return <EntityLensPage entityType="work_order" entityId={entityId} content={WOContent} />;
    case 'fault':
      return <EntityLensPage entityType="fault" entityId={entityId} content={FtContent} />;
    case 'equipment':
      return <EntityLensPage entityType="equipment" entityId={entityId} content={EqContent} />;
    case 'part':
    case 'inventory':
      return <EntityLensPage entityType="part" entityId={entityId} content={PtContent} />;
    case 'receiving':
      return <EntityLensPage entityType="receiving" entityId={entityId} content={RcContent} />;
    case 'certificate':
      return <EntityLensPage entityType="certificate" entityId={entityId} content={CtContent} />;
    case 'handover':
      return <EntityLensPage entityType="handover_export" entityId={entityId} content={HdContent} />;
    case 'handover_export':
      return <EntityLensPage entityType="handover_export" entityId={entityId} content={HdContent} />;
    case 'hours_of_rest':
      return <EntityLensPage entityType="hours_of_rest" entityId={entityId} content={HrContent} />;
    case 'warranty':
      return <EntityLensPage entityType="warranty" entityId={entityId} content={WrContent} />;
    case 'shopping_list':
      return <EntityLensPage entityType="shopping_list" entityId={entityId} content={SlContent} />;
    case 'document':
      return <EntityLensPage entityType="document" entityId={entityId} content={DcContent} />;
    case 'purchase_order':
      return <EntityLensPage entityType="purchase_order" entityId={entityId} content={PoContent} />;
    default:
      return (
        <div className="p-6 text-celeste-text-muted">
          <p>Unknown entity type: {entityType}</p>
          <p className="typo-meta mt-2 text-celeste-text-disabled">
            Supported types: work_order, fault, equipment, part, inventory, receiving,
            certificate, handover, handover_export, hours_of_rest, warranty, shopping_list, document, purchase_order
          </p>
        </div>
      );
  }
}

