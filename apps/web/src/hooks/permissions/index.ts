/**
 * Centralized Permission Hooks Exports
 *
 * Type-safe permission hooks for all 12 lenses.
 * All hooks derive from lens_matrix.json via PermissionService.
 *
 * Usage:
 *   import { useFaultPermissions } from '@/hooks/permissions';
 *   const { canUpdateFault, canCloseFault } = useFaultPermissions();
 */

// Universal permission hook
export { usePermissions, useMultiLensPermissions, type PermissionResult } from '../usePermissions';

// Fault lens
export {
  useFaultPermissions,
  type FaultPermissions,
  type FaultAction,
} from './useFaultPermissions';

// Equipment lens
export {
  useEquipmentPermissions,
  type EquipmentPermissions,
  type EquipmentAction,
} from './useEquipmentPermissions';

// Work Order lens
export {
  useWorkOrderPermissions,
  type WorkOrderPermissions,
  type WorkOrderAction,
} from './useWorkOrderPermissions';

// Certificate lens
export {
  useCertificatePermissions,
  type CertificatePermissions,
  type CertificateAction,
} from './useCertificatePermissions';

// Part lens
export {
  usePartPermissions,
  type PartPermissions,
  type PartAction,
} from './usePartPermissions';

// Inventory lens
export {
  useInventoryPermissions,
  type InventoryPermissions,
  type InventoryAction,
} from './useInventoryPermissions';

// Warranty lens
export {
  useWarrantyPermissions,
  type WarrantyPermissions,
  type WarrantyAction,
} from './useWarrantyPermissions';

// Shopping List lens
export {
  useShoppingListPermissions,
  type ShoppingListPermissions,
  type ShoppingListAction,
} from './useShoppingListPermissions';

// Receiving lens
export {
  useReceivingPermissions,
  type ReceivingPermissions,
  type ReceivingAction,
} from './useReceivingPermissions';

// Handover lens
export {
  useHandoverPermissions,
  type HandoverPermissions,
  type HandoverAction,
} from './useHandoverPermissions';

// Hours of Rest lens
export {
  useHoursOfRestPermissions,
  type HoursOfRestPermissions,
  type HoursOfRestAction,
} from './useHoursOfRestPermissions';

// Email lens
export {
  useEmailPermissions,
  type EmailPermissions,
  type EmailAction,
} from './useEmailPermissions';
