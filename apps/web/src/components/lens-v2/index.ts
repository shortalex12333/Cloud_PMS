/**
 * Lens V2 — Production-paired component library
 *
 * Visual layer matches approved prototypes (2026-03-17).
 * Data layer reuses production hooks (useEntityLens, EntityLensContext).
 *
 * Phase 1: Built in parallel — zero production files touched.
 * Phase 3: Atomic swap — git mv lens lens-deprecated, git mv lens-v2 lens.
 */

// Shell
export { LensShell, type LensShellProps } from './LensShell';

// Core components
export { LensGlassHeader, type LensGlassHeaderProps } from './LensGlassHeader';
export { IdentityStrip, type IdentityStripProps, type DetailLine, type PillDef } from './IdentityStrip';
export { SplitButton, type SplitButtonProps, type DropdownItem } from './SplitButton';
export { CollapsibleSection, type CollapsibleSectionProps } from './CollapsibleSection';
export { LensPill, type LensPillProps, type PillVariant } from './LensPill';
export { ScrollReveal, type ScrollRevealProps } from './ScrollReveal';

// Popup
export { ActionPopup, type ActionPopupProps, type ActionPopupField, type ActionPopupGate } from './ActionPopup';

// Sections
export {
  NotesSection,
  AuditTrailSection,
  AttachmentsSection,
  PartsSection,
  ChecklistSection,
  DocRowsSection,
  KVSection,
} from './sections';

// Entity content components
export {
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
} from './entity';
