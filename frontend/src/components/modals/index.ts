/**
 * Modal Components Index
 *
 * Central export point for all modal components
 * Phase 4 - Modal Components & Action Completion
 */

// Phase 1 - Example Modal
export { CreateWorkOrderModal } from './CreateWorkOrderModal';

// Phase 4 - High-Priority CREATE Modals
export { ReportFaultModal } from './ReportFaultModal';
export { AddPartModal } from './AddPartModal';
export { OrderPartModal } from './OrderPartModal';
export { LogPartUsageModal } from './LogPartUsageModal';
export { CreatePurchaseRequestModal } from './CreatePurchaseRequestModal';

// Phase 4 - Audit-Sensitive EDIT Modals
export { EditInvoiceAmountModal } from './EditInvoiceAmountModal';
export { EditWorkOrderDetailsModal } from './EditWorkOrderDetailsModal';
export { EditPartQuantityModal } from './EditPartQuantityModal';
export { EditEquipmentDetailsModal } from './EditEquipmentDetailsModal';
export { EditFaultDetailsModal } from './EditFaultDetailsModal';

// Phase 4 - LINKING Selection Modals
export { AddToHandoverModal } from './AddToHandoverModal';
export { LinkEquipmentToFaultModal } from './LinkEquipmentToFaultModal';
export { LinkPartsToWorkOrderModal } from './LinkPartsToWorkOrderModal';

// Phase 4 - Advanced/RAG Modal
export { DiagnoseFaultModal } from './DiagnoseFaultModal';

// Phase 4 - Special Utility Modal
export { CompleteWorkOrderModal } from './CompleteWorkOrderModal';

/**
 * Usage example:
 *
 * import { ReportFaultModal, OrderPartModal } from '@/components/modals';
 *
 * <ReportFaultModal
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   context={{ equipment_id: '123', equipment_name: 'Engine' }}
 *   onSuccess={(fault_id) => console.log('Fault reported:', fault_id)}
 * />
 */
