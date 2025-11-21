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

// Phase 4 - Audit-Sensitive EDIT Modals
export { EditInvoiceAmountModal } from './EditInvoiceAmountModal';

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
