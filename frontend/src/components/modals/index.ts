/**
 * Modal Components Index
 *
 * Central export point for all modal components
 * Phase 4 - Modal Components & Action Completion
 */

// Phase 1 - Example Modal (located in actions/modals)
export { CreateWorkOrderModal } from '../actions/modals/CreateWorkOrderModal';

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

// Phase 5 - Generic Note/Photo Modals
export { AddNoteModal } from './AddNoteModal';
export { AddPhotoModal } from './AddPhotoModal';

// Phase 5 - Assignment & Handover Modals
export { AssignWorkOrderModal } from './AssignWorkOrderModal';
export { EditHandoverSectionModal } from './EditHandoverSectionModal';

// Phase 5 - Compliance & Purchasing Modals
export { UpdateHoursOfRestModal } from './UpdateHoursOfRestModal';
export { LogDeliveryReceivedModal } from './LogDeliveryReceivedModal';

// Phase 5 - Shipyard Worklist Modal
export { AddWorklistTaskModal } from './AddWorklistTaskModal';

/**
 * Modal Coverage Summary:
 *
 * FAULT & DIAGNOSIS (9 actions):
 * - diagnose_fault: DiagnoseFaultModal
 * - report_fault: ReportFaultModal
 * - add_fault_note: AddNoteModal (entity_type='fault')
 * - add_fault_photo: AddPhotoModal (entity_type='fault')
 * - link_equipment_to_fault: LinkEquipmentToFaultModal
 * - edit_fault_details: EditFaultDetailsModal
 *
 * WORK ORDER (11 actions):
 * - create_work_order: CreateWorkOrderModal
 * - complete_work_order: CompleteWorkOrderModal
 * - add_work_order_note: AddNoteModal (entity_type='work_order')
 * - add_work_order_photo: AddPhotoModal (entity_type='work_order')
 * - link_parts_to_work_order: LinkPartsToWorkOrderModal
 * - assign_work_order: AssignWorkOrderModal
 * - edit_work_order_details: EditWorkOrderDetailsModal
 *
 * EQUIPMENT (6 actions):
 * - add_equipment_note: AddNoteModal (entity_type='equipment')
 * - edit_equipment_details: EditEquipmentDetailsModal
 *
 * INVENTORY (9 actions):
 * - add_part: AddPartModal
 * - order_part: OrderPartModal
 * - log_part_usage: LogPartUsageModal
 * - edit_part_quantity: EditPartQuantityModal
 *
 * HANDOVER (6 actions):
 * - add_to_handover: AddToHandoverModal
 * - edit_handover_section: EditHandoverSectionModal
 *
 * PURCHASING (7 actions):
 * - create_purchase_request: CreatePurchaseRequestModal
 * - edit_invoice_amount: EditInvoiceAmountModal
 * - log_delivery_received: LogDeliveryReceivedModal
 *
 * CHECKLIST (4 actions):
 * - add_checklist_note: AddNoteModal (entity_type='checklist')
 * - add_checklist_photo: AddPhotoModal (entity_type='checklist')
 *
 * COMPLIANCE (MLC/ISM):
 * - update_hours_of_rest: UpdateHoursOfRestModal
 *
 * SHIPYARD/WORKLIST:
 * - add_worklist_task: AddWorklistTaskModal
 */
