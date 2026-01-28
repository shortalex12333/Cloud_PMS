# Phase 4 Implementation Plan - Modal Components & Action Completion

**Date:** 2025-11-21
**Branch:** `claude/read-repo-files-01TwqiaKXUk14frUXUPkVKTj`
**Goal:** Complete the WRITE dimension by building all remaining modals for 67 micro-actions

---

## Overview

Phase 3 completed the **READ dimension** (filtering/viewing). Phase 4 completes the **WRITE dimension** by building modal components that enable users to CREATE, UPDATE, and LINK entities through proper UIs.

---

## Current State

### ✅ What Exists (Phase 1/2)
- **1 Modal:** `CreateWorkOrderModal.tsx` (example implementation)
- **Action Handler:** Complete infrastructure with confirmation/reason handling
- **Card Components:** All 12 cards with action buttons
- **6 n8n Workflows:** Scaffolded but only ~20% populated with SQL

### ❌ What's Missing
- **15-20 Modal Components:** Most CREATE/EDIT/LINKING actions have no UI
- **n8n Workflow Logic:** ~80% of action cases not implemented
- **Specialized Hooks:** Need domain-specific action hooks

---

## Phase 4 Priorities

### **Priority 1: High-Impact CREATE Modals (5 modals)**

These enable core functionality users need immediately:

1. **ReportFaultModal** - Report equipment faults
   - Fields: equipment_id, title, description, severity, deck, room
   - Validation: Required title/description, severity enum
   - Photo upload support
   - Auto-create work order option

2. **AddPartModal** - Add new inventory item
   - Fields: part_name, part_number, stock_quantity, min_stock_level, location (deck/room/storage), unit_cost, supplier
   - Validation: Unique part_number, positive quantities
   - Barcode generation

3. **OrderPartModal** - Order parts from supplier
   - Fields: part_id (pre-filled), quantity, supplier (dropdown), expected_delivery, notes
   - Shows current stock level + min level
   - Calculates estimated cost

4. **LogPartUsageModal** - Track part consumption
   - Fields: part_id (pre-filled), work_order_id (dropdown), quantity_used, notes
   - Validation: quantity <= available stock
   - Updates stock in real-time

5. **CreatePurchaseRequestModal** - Initiate purchasing
   - Fields: items (multi-select), justification, urgency, budget_code
   - Line items with quantities
   - Approval workflow trigger

---

### **Priority 2: Audit-Sensitive EDIT Modals (5 modals)**

These require **reason field** and create **audit logs** per user's requirement:

1. **EditInvoiceAmountModal** ⚠️ AUDIT-SENSITIVE
   - Fields: invoice_id (pre-filled), old_amount (read-only), new_amount, reason (REQUIRED)
   - Validation: Reason must be >10 chars
   - Triggers: Email notification if change >$500 or >10%
   - Audit: HIGH severity log

2. **EditWorkOrderDetailsModal**
   - Fields: work_order_id (pre-filled), title, description, priority, due_date, assigned_to
   - Shows change diff before save
   - Audit: MEDIUM severity log

3. **EditPartQuantityModal**
   - Fields: part_id (pre-filled), old_quantity (read-only), new_quantity, adjustment_reason
   - Shows stock level impact
   - Audit: MEDIUM severity log

4. **EditEquipmentDetailsModal**
   - Fields: equipment_id (pre-filled), name, model, serial_number, location, manufacturer
   - Change tracking for critical fields (serial_number)
   - Audit: LOW severity log

5. **EditFaultDetailsModal**
   - Fields: fault_id (pre-filled), title, description, severity, status
   - Status change validation (can't reopen closed faults without reason)
   - Audit: MEDIUM severity log

---

### **Priority 3: LINKING Selection Modals (3 modals)**

These enable associations between entities:

1. **AddToHandoverModal**
   - Select entity type: fault/work_order/equipment/part/document
   - Search/filter entities
   - Add summary/notes
   - Multi-select support

2. **LinkEquipmentToFaultModal**
   - Search equipment by name/location
   - Shows equipment details preview
   - Optional: Create work order for linked fault

3. **LinkPartsToWorkOrderModal**
   - Multi-select parts from inventory
   - Shows stock levels
   - Optional: Reserve parts for work order

---

### **Priority 4: Specialized Hooks (4 hooks)**

Domain-specific wrappers around useActionHandler:

1. **useFaultActions.ts**
```typescript
export function useFaultActions() {
  const { executeAction, isLoading } = useActionHandler();

  const reportFault = async (data: FaultData) => {
    return executeAction('report_fault', data, {
      successMessage: 'Fault reported successfully',
      refreshData: true,
    });
  };

  const resolveFault = async (fault_id: string, resolution_notes: string) => {
    return executeAction('resolve_fault', { fault_id, resolution_notes }, {
      successMessage: 'Fault marked as resolved',
      refreshData: true,
    });
  };

  return { reportFault, resolveFault, isLoading };
}
```

2. **useInventoryActions.ts** - Part/inventory operations
3. **usePurchaseActions.ts** - Purchasing workflow
4. **useEquipmentActions.ts** - Equipment management

---

## n8n Workflow Expansion

### **Master CREATE Workflow**

Currently has scaffold, needs SQL logic for:

**Faults:**
```sql
INSERT INTO faults (
  yacht_id, equipment_id, title, description,
  severity, status, deck, room, created_by, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.equipment_id}}',
  '{{$json.context.title}}',
  '{{$json.context.description}}',
  '{{$json.context.severity}}',
  'open',
  '{{$json.context.deck}}',
  '{{$json.context.room}}',
  '{{$json.user_id}}',
  NOW()
) RETURNING id;
```

**Parts:**
```sql
INSERT INTO parts (
  yacht_id, part_name, part_number, stock_quantity,
  min_stock_level, location, deck, room, storage,
  unit_cost, supplier, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.context.part_name}}',
  '{{$json.context.part_number}}',
  {{$json.context.stock_quantity}},
  {{$json.context.min_stock_level}},
  '{{$json.context.location}}',
  '{{$json.context.deck}}',
  '{{$json.context.room}}',
  '{{$json.context.storage}}',
  {{$json.context.unit_cost}},
  '{{$json.context.supplier}}',
  NOW()
) RETURNING id;
```

**Work Orders:** (already exists)

**Purchase Requests:**
```sql
INSERT INTO purchase_requests (
  yacht_id, requested_by, justification,
  urgency, status, created_at
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.user_id}}',
  '{{$json.context.justification}}',
  '{{$json.context.urgency}}',
  'pending_approval',
  NOW()
) RETURNING id;
```

---

### **Master UPDATE Workflow**

Needs audit logging implementation:

**Template for audit-sensitive edits:**
```sql
-- Update the entity
UPDATE invoices
SET amount = {{$json.context.new_amount}},
    updated_at = NOW()
WHERE id = '{{$json.context.invoice_id}}'
  AND yacht_id = '{{$json.yacht_id}}'
RETURNING *;

-- Create audit log
INSERT INTO audit_logs (
  yacht_id, user_id, action, entity_type, entity_id,
  old_value, new_value, reason, severity, timestamp
) VALUES (
  '{{$json.yacht_id}}',
  '{{$json.user_id}}',
  'edit_invoice_amount',
  'invoice',
  '{{$json.context.invoice_id}}',
  '{{$json.context.old_amount}}',
  '{{$json.context.new_amount}}',
  '{{$json.context.reason}}',
  'HIGH',
  NOW()
);

-- Check if notification needed
IF ({{$json.context.new_amount}} - {{$json.context.old_amount}}) > 500
   OR ({{$json.context.new_amount}} / {{$json.context.old_amount}}) > 1.1 THEN
  -- Send notification (next node)
  SELECT 'notification_required' as alert;
END IF;
```

---

## Implementation Timeline

### **Day 1: High-Impact CREATE Modals**
- [ ] ReportFaultModal
- [ ] AddPartModal
- [ ] OrderPartModal
- [ ] Update master-create-workflow.json with SQL logic

### **Day 2: Part Actions + Audit Modals**
- [ ] LogPartUsageModal
- [ ] CreatePurchaseRequestModal
- [ ] EditInvoiceAmountModal (audit-sensitive)
- [ ] EditWorkOrderDetailsModal

### **Day 3: Equipment/Fault EDIT Modals**
- [ ] EditPartQuantityModal
- [ ] EditEquipmentDetailsModal
- [ ] EditFaultDetailsModal
- [ ] Update master-update-workflow.json with audit logging

### **Day 4: LINKING Modals + Specialized Hooks**
- [ ] AddToHandoverModal
- [ ] LinkEquipmentToFaultModal
- [ ] LinkPartsToWorkOrderModal
- [ ] Build 4 specialized hooks

### **Day 5: Testing + Polish**
- [ ] End-to-end testing all modals
- [ ] Verify audit logs work correctly
- [ ] Test email notifications for high-severity edits
- [ ] Mobile responsive testing
- [ ] Performance testing

---

## Modal Component Pattern

All modals follow this structure (from CreateWorkOrderModal):

```typescript
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useActionHandler } from '@/hooks/useActionHandler';

const schema = z.object({
  // Fields with validation
});

export function ExampleModal({ open, onOpenChange, context, onSuccess }) {
  const { executeAction, isLoading } = useActionHandler();
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      // Pre-fill from context
    }
  });

  const onSubmit = async (data) => {
    const response = await executeAction('action_name', data, {
      successMessage: '...',
      refreshData: true,
    });

    if (response?.success) {
      onOpenChange(false);
      if (onSuccess) onSuccess(response);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Modal Title</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Form fields */}
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Processing...' : 'Submit'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Success Criteria

Phase 4 is complete when:

- [ ] All 15 high-priority modals are built
- [ ] All modals integrate with useActionHandler
- [ ] Audit logging works for sensitive edits
- [ ] Email notifications trigger for threshold edits
- [ ] n8n workflows handle all CREATE/UPDATE actions
- [ ] Specialized hooks provide clean APIs
- [ ] End-to-end flow: Card → Modal → Workflow → Response → Refresh
- [ ] All modals are mobile responsive
- [ ] Form validation prevents invalid submissions

---

## Phase 5 Preview

After Phase 4, remaining work includes:

- **RAG Modals:** DiagnoseFaultModal with AI streaming
- **Export Functionality:** PDF/Excel generation
- **Advanced Workflows:** Multi-step approval processes
- **Predictive Insights:** Smart summary generation
- **Mobile-Specific Actions:** Barcode scanning, photo capture

---

## Notes

- **Guard Rails:** Follow Phase 3's principle - only create NEW files, don't modify existing unless necessary
- **Naming:** Modal files go in `frontend/src/components/modals/`
- **Testing:** Each modal should be testable independently
- **Accessibility:** All forms need proper labels and error messages
- **Performance:** Forms with large dropdowns need search/filter
