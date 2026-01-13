# CELESTEOS V4 ARCHITECTURE - COMPLETE FOLDER STRUCTURE & ORGANIZATION

**Version:** 4.0
**Date:** 2026-01-11
**Purpose:** Define exact folder structure, file organization, CORS policies, RPC patterns, and Supabase policies for all 67+ micro-actions

---

## CRITICAL PROBLEMS ADDRESSED

Based on your issues with:
1. **CORS errors** - Document viewer, API calls failing
2. **RPC function organization** - Scattered, hard to find, permission errors
3. **Supabase policies** - Conflicting policies, yacht isolation breaking
4. **Document viewer situation** - RAG, embeddings, CORS on storage buckets

This document provides the **EXACT** architecture to solve these problems.

---

## TABLE OF CONTENTS

1. [REPOSITORY STRUCTURE](#1-repository-structure)
2. [FRONTEND FOLDER STRUCTURE](#2-frontend-folder-structure)
3. [BACKEND (SUPABASE) STRUCTURE](#3-backend-supabase-structure)
4. [MICRO-ACTION ORGANIZATION](#4-micro-action-organization)
5. [RPC FUNCTION PATTERNS](#5-rpc-function-patterns)
6. [SUPABASE POLICIES ORGANIZATION](#6-supabase-policies-organization)
7. [CORS CONFIGURATION](#7-cors-configuration-critical)
8. [DOCUMENT VIEWER ARCHITECTURE](#8-document-viewer-architecture)
9. [NESTED ACTIONS PATTERN](#9-nested-actions-within-actions)
10. [SECURITY BOUNDARIES](#10-security-boundaries)
11. [DEPLOYMENT STRUCTURE](#11-deployment-structure)

---

## 1. REPOSITORY STRUCTURE

```
Cloud_PMS/
├── .github/
│   └── workflows/
│       └── deploy.yml                 # CI/CD pipeline
│
├── supabase/
│   ├── migrations/                    # Database migrations (ALREADY APPLIED)
│   ├── functions/                     # Edge Functions (Deno runtime)
│   │   ├── _shared/                   # Shared utilities for edge functions
│   │   │   ├── cors.ts                # ⚠️ CRITICAL: CORS configuration
│   │   │   ├── auth.ts                # Auth helpers
│   │   │   └── types.ts               # Shared types
│   │   │
│   │   ├── document-processing/       # RAG document processing
│   │   │   └── index.ts               # Chunking, embedding generation
│   │   │
│   │   ├── semantic-search/           # Document semantic search
│   │   │   └── index.ts               # Vector similarity search
│   │   │
│   │   └── action-execute/            # Generic action executor (optional)
│   │       └── index.ts
│   │
│   ├── rpc/                           # ⚠️ NEW: RPC function SQL definitions
│   │   ├── 00_helpers/                # Shared helper functions
│   │   ├── 01_faults/                 # Fault-related RPCs
│   │   ├── 02_work_orders/            # Work order RPCs
│   │   ├── 03_shopping_list/          # Shopping list RPCs
│   │   ├── 04_receiving/              # Receiving RPCs
│   │   ├── 05_handover/               # Handover RPCs
│   │   ├── 06_checklists/             # Checklist RPCs
│   │   ├── 07_maintenance/            # PM schedule RPCs
│   │   ├── 08_documents/              # Document management RPCs
│   │   ├── 09_inventory/              # Inventory RPCs
│   │   ├── 10_crew/                   # Crew rotation RPCs
│   │   ├── 11_compliance/             # Certificates, contracts
│   │   └── 12_analytics/              # Dashboards, reports
│   │
│   ├── policies/                      # ⚠️ NEW: RLS policies organized
│   │   ├── 00_global_policies.sql     # Yacht isolation (FOUNDATIONAL)
│   │   ├── 01_faults_policies.sql
│   │   ├── 02_work_orders_policies.sql
│   │   ├── 03_shopping_list_policies.sql
│   │   ├── 04_receiving_policies.sql
│   │   ├── 05_handover_policies.sql
│   │   ├── 06_checklists_policies.sql
│   │   ├── 07_maintenance_policies.sql
│   │   ├── 08_documents_policies.sql
│   │   ├── 09_inventory_policies.sql
│   │   ├── 10_crew_policies.sql
│   │   ├── 11_compliance_policies.sql
│   │   └── 12_storage_policies.sql    # ⚠️ CRITICAL: Storage bucket policies
│   │
│   └── config.toml                    # Supabase project config
│
├── src/                               # Next.js 14 app directory
│   ├── app/                           # App router
│   │   ├── (auth)/                    # Auth routes
│   │   │   ├── login/
│   │   │   └── logout/
│   │   │
│   │   ├── (dashboard)/               # Main app (requires auth)
│   │   │   ├── layout.tsx             # Dashboard shell
│   │   │   ├── page.tsx               # Home/overview
│   │   │   │
│   │   │   ├── faults/                # Fault management
│   │   │   │   ├── page.tsx           # Fault list
│   │   │   │   ├── [id]/              # Fault detail
│   │   │   │   └── _components/       # Fault-specific components
│   │   │   │       ├── FaultCard.tsx
│   │   │   │       ├── ReportFaultModal.tsx      # MICRO-ACTION: report_fault
│   │   │   │       ├── DiagnoseFaultModal.tsx    # MICRO-ACTION: diagnose_fault
│   │   │   │       ├── AcknowledgeFaultModal.tsx # MICRO-ACTION: acknowledge_fault
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── work-orders/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── [id]/
│   │   │   │   └── _components/
│   │   │   │       ├── CreateWorkOrderModal.tsx  # MICRO-ACTION: create_work_order
│   │   │   │       ├── AssignWorkOrderModal.tsx  # MICRO-ACTION: assign_work_order
│   │   │   │       ├── CloseWorkOrderModal.tsx   # MICRO-ACTION: close_work_order
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── shopping-list/
│   │   │   │   ├── page.tsx
│   │   │   │   └── _components/
│   │   │   │       ├── AddToShoppingListModal.tsx    # MICRO-ACTION: add_to_shopping_list
│   │   │   │       ├── ApproveShoppingItemModal.tsx  # MICRO-ACTION: approve_shopping_item
│   │   │   │       ├── CommitShoppingListModal.tsx   # MICRO-ACTION: commit_shopping_list
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── receiving/
│   │   │   │   ├── page.tsx
│   │   │   │   └── _components/
│   │   │   │       ├── StartReceivingSessionModal.tsx    # MICRO-ACTION: start_receiving
│   │   │   │       ├── CheckInItemModal.tsx              # MICRO-ACTION: check_in_item
│   │   │   │       ├── CommitReceivingModal.tsx          # MICRO-ACTION: commit_receiving (NESTED)
│   │   │   │       │   # ↑ Contains: review → accept → commit (3 steps)
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── handover/
│   │   │   │   ├── page.tsx
│   │   │   │   └── _components/
│   │   │   │       ├── CreateHandoverModal.tsx           # MICRO-ACTION: create_handover
│   │   │   │       ├── AcknowledgeHandoverModal.tsx      # MICRO-ACTION: acknowledge_handover
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── checklists/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── execute/
│   │   │   │   │   └── [executionId]/                    # Checklist execution
│   │   │   │   └── _components/
│   │   │   │       ├── CreateChecklistModal.tsx
│   │   │   │       ├── ExecuteChecklistModal.tsx         # MICRO-ACTION: execute_checklist (NESTED)
│   │   │   │       │   # ↑ Contains: start → complete_items → sign_off (multi-step)
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── documents/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── viewer/
│   │   │   │   │   └── [documentId]/                     # ⚠️ CRITICAL: Document viewer
│   │   │   │   │       └── page.tsx                      # RAG, semantic search, CORS issues
│   │   │   │   └── _components/
│   │   │   │       ├── UploadDocumentModal.tsx           # MICRO-ACTION: upload_document
│   │   │   │       ├── ViewManualSectionModal.tsx        # MICRO-ACTION: show_manual_section
│   │   │   │       ├── SemanticSearchPanel.tsx           # RAG semantic search
│   │   │   │       └── ...
│   │   │   │
│   │   │   ├── inventory/
│   │   │   ├── maintenance/
│   │   │   ├── crew/
│   │   │   ├── compliance/
│   │   │   └── settings/
│   │   │
│   │   └── api/                       # API routes (Next.js)
│   │       ├── actions/               # Server actions for micro-actions
│   │       │   ├── faults/
│   │       │   │   ├── report-fault.ts            # Server action → RPC
│   │       │   │   ├── diagnose-fault.ts
│   │       │   │   └── ...
│   │       │   ├── work-orders/
│   │       │   ├── shopping-list/
│   │       │   ├── receiving/
│   │       │   └── ...
│   │       │
│   │       └── webhooks/              # External webhooks
│   │           └── supabase-auth.ts
│   │
│   ├── components/                    # Shared components (NOT action-specific)
│   │   ├── ui/                        # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── modal.tsx
│   │   │   ├── form.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   ├── shared/                    # Shared across actions
│   │   │   ├── EntitySelector.tsx     # Select equipment, part, etc.
│   │   │   ├── UserRoleBadge.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── SignatureCapture.tsx   # For high-value actions
│   │   │   └── ...
│   │   │
│   │   └── guards/                    # Security components
│   │       ├── RoleGuard.tsx          # Enforce user role requirements
│   │       └── YachtGuard.tsx         # Enforce yacht isolation
│   │
│   ├── lib/                           # Utility libraries
│   │   ├── supabase/
│   │   │   ├── client.ts              # Client-side Supabase client
│   │   │   ├── server.ts              # Server-side Supabase client
│   │   │   ├── middleware.ts          # Auth middleware
│   │   │   └── types.ts               # Database types (generated)
│   │   │
│   │   ├── actions/                   # ⚠️ CRITICAL: Action registry and logic
│   │   │   ├── registry.ts            # Central action registry (67+ actions)
│   │   │   ├── types.ts               # Action type definitions
│   │   │   ├── guards.ts              # Permission guards for actions
│   │   │   ├── executors/             # Action execution logic
│   │   │   │   ├── fault-actions.ts   # All fault-related actions
│   │   │   │   ├── work-order-actions.ts
│   │   │   │   ├── shopping-actions.ts
│   │   │   │   ├── receiving-actions.ts
│   │   │   │   ├── handover-actions.ts
│   │   │   │   ├── checklist-actions.ts
│   │   │   │   └── ...
│   │   │   │
│   │   │   └── hooks/                 # React hooks for actions
│   │   │       ├── useAction.ts       # Generic action hook
│   │   │       ├── useFaultActions.ts
│   │   │       ├── useWorkOrderActions.ts
│   │   │       └── ...
│   │   │
│   │   ├── validation/                # Input validation
│   │   │   ├── schemas/               # Zod schemas per action
│   │   │   │   ├── fault-schemas.ts
│   │   │   │   ├── work-order-schemas.ts
│   │   │   │   └── ...
│   │   │   └── errors.ts              # Error handling
│   │   │
│   │   ├── state/                     # State management
│   │   │   ├── situational-states.ts  # Shopping list, receiving state machines
│   │   │   └── user-context.ts        # User role, yacht context
│   │   │
│   │   └── utils/
│   │       ├── cors.ts                # ⚠️ CRITICAL: CORS utility functions
│   │       ├── formatting.ts
│   │       └── constants.ts
│   │
│   ├── hooks/                         # Global React hooks
│   │   ├── useUser.ts                 # Current user context
│   │   ├── useYacht.ts                # Current yacht context
│   │   ├── usePermissions.ts          # User permissions
│   │   └── useSupabase.ts             # Supabase client hook
│   │
│   ├── types/                         # TypeScript types
│   │   ├── database.types.ts          # ⚠️ GENERATED from Supabase
│   │   ├── actions.types.ts           # Action type definitions
│   │   ├── user.types.ts
│   │   └── entities.types.ts
│   │
│   └── middleware.ts                  # Next.js middleware (auth, CORS)
│
├── public/
│   ├── icons/
│   └── documents/                     # ⚠️ DO NOT USE: Use Supabase storage instead
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE_V4_COMPLETE.md    # THIS FILE
│   ├── DATABASE_SPEC/                 # Database specifications
│   ├── ACTION_CATALOG/                # Micro-action specifications
│   └── API_DOCS/                      # API documentation
│
├── .env.local                         # Local environment variables
├── .env.production                    # Production environment variables
├── next.config.js                     # ⚠️ CRITICAL: CORS configuration here
├── package.json
└── tsconfig.json
```

---

## 2. FRONTEND FOLDER STRUCTURE

### 2.1 Action-Specific Components Pattern

**RULE:** Every micro-action has its own component in the relevant section's `_components/` folder.

**Example: Fault Actions**
```
src/app/(dashboard)/faults/_components/
├── ReportFaultModal.tsx           # MICRO-ACTION: report_fault
├── AcknowledgeFaultModal.tsx      # MICRO-ACTION: acknowledge_fault
├── DiagnoseFaultModal.tsx         # MICRO-ACTION: diagnose_fault
├── CreateWorkOrderFromFaultModal.tsx  # MICRO-ACTION: create_work_order_from_fault (NESTED)
├── UpdateFaultModal.tsx           # MICRO-ACTION: update_fault
├── CloseFaultModal.tsx            # MICRO-ACTION: close_fault
└── FaultCard.tsx                  # Display component (not an action)
```

**Naming Convention:**
- **Modal components:** `{ActionName}Modal.tsx` (PascalCase)
- **Inline components:** `{ActionName}Form.tsx` or `{ActionName}Panel.tsx`
- **Display components:** `{Entity}Card.tsx`, `{Entity}List.tsx`

### 2.2 Modal Component Structure (Standard Pattern)

Every micro-action modal follows this structure:

```typescript
// src/app/(dashboard)/faults/_components/ReportFaultModal.tsx

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { reportFaultSchema } from '@/lib/validation/schemas/fault-schemas';
import { useFaultActions } from '@/lib/actions/hooks/useFaultActions';
import { Modal } from '@/components/ui/modal';
import { Form, FormField } from '@/components/ui/form';
import { Button } from '@/components/ui/button';
import { EntitySelector } from '@/components/shared/EntitySelector';

interface ReportFaultModalProps {
  isOpen: boolean;
  onClose: () => void;
  equipmentId?: string;  // Optional prefill
}

export function ReportFaultModal({ isOpen, onClose, equipmentId }: ReportFaultModalProps) {
  const { reportFault, isLoading } = useFaultActions();

  const form = useForm({
    resolver: zodResolver(reportFaultSchema),
    defaultValues: {
      equipment_id: equipmentId || '',
      fault_type: '',
      description: '',
      severity: 'medium',
      requires_immediate_attention: false,
    },
  });

  const onSubmit = async (data) => {
    try {
      // 1. VALIDATION: Schema validation already done by resolver

      // 2. PERMISSION CHECK: Done in hook
      const result = await reportFault(data);

      // 3. SUCCESS: Close modal and notify
      if (result.success) {
        onClose();
        // Optional: Show toast notification
      }
    } catch (error) {
      // 4. ERROR HANDLING: Display to user
      form.setError('root', { message: error.message });
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Report Fault">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* Equipment Selection */}
          <FormField
            control={form.control}
            name="equipment_id"
            render={({ field }) => (
              <EntitySelector
                type="equipment"
                value={field.value}
                onChange={field.onChange}
                label="Equipment"
                required
              />
            )}
          />

          {/* Fault Type */}
          <FormField
            control={form.control}
            name="fault_type"
            render={({ field }) => (
              <select {...field}>
                <option value="">Select fault type...</option>
                <option value="mechanical">Mechanical</option>
                <option value="electrical">Electrical</option>
                <option value="hydraulic">Hydraulic</option>
                {/* ... */}
              </select>
            )}
          />

          {/* Description */}
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <textarea
                {...field}
                placeholder="Describe the fault in detail..."
                minLength={10}
                required
              />
            )}
          />

          {/* Severity */}
          <FormField
            control={form.control}
            name="severity"
            render={({ field }) => (
              <select {...field}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            )}
          />

          {/* Submit */}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isLoading}>
              Report Fault
            </Button>
          </div>
        </form>
      </Form>
    </Modal>
  );
}
```

### 2.3 Action Hooks Pattern

Every action cluster has a custom hook in `lib/actions/hooks/`:

```typescript
// src/lib/actions/hooks/useFaultActions.ts

import { useCallback } from 'react';
import { useUser } from '@/hooks/useUser';
import { useYacht } from '@/hooks/useYacht';
import { faultActionExecutor } from '@/lib/actions/executors/fault-actions';

export function useFaultActions() {
  const { user } = useUser();
  const { yacht } = useYacht();

  // MICRO-ACTION: report_fault
  const reportFault = useCallback(async (data: ReportFaultInput) => {
    // 1. Permission check
    if (!user || !yacht) {
      throw new Error('User not authenticated or yacht not selected');
    }

    // 2. Execute via central executor
    return await faultActionExecutor.reportFault({
      ...data,
      yacht_id: yacht.id,
      reported_by: user.id,
      reported_by_name: user.name,
      reported_by_role: user.role,
    });
  }, [user, yacht]);

  // MICRO-ACTION: acknowledge_fault
  const acknowledgeFault = useCallback(async (faultId: string, data: AcknowledgeFaultInput) => {
    if (!user || !yacht) {
      throw new Error('User not authenticated');
    }

    // Permission: Only engineer+ can acknowledge
    if (!['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'].includes(user.role)) {
      throw new Error('Insufficient permissions to acknowledge fault');
    }

    return await faultActionExecutor.acknowledgeFault({
      fault_id: faultId,
      ...data,
      acknowledged_by: user.id,
      acknowledged_by_name: user.name,
    });
  }, [user, yacht]);

  // MICRO-ACTION: diagnose_fault
  const diagnoseFault = useCallback(async (faultId: string, data: DiagnoseFaultInput) => {
    if (!user || !yacht) {
      throw new Error('User not authenticated');
    }

    // Permission: Only engineer+ can diagnose
    if (!['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'].includes(user.role)) {
      throw new Error('Insufficient permissions to diagnose fault');
    }

    return await faultActionExecutor.diagnoseFault({
      fault_id: faultId,
      ...data,
      diagnosed_by: user.id,
      diagnosed_by_name: user.name,
    });
  }, [user, yacht]);

  // ... more actions

  return {
    reportFault,
    acknowledgeFault,
    diagnoseFault,
    isLoading: false, // TODO: Add loading state management
  };
}
```

---

## 3. BACKEND (SUPABASE) STRUCTURE

### 3.1 RPC Functions Organization

**CRITICAL RULE:** One RPC function per micro-action. NO GENERIC RPCS.

**File Structure:**
```
supabase/rpc/
├── 00_helpers/
│   ├── validate_yacht_access.sql      # Helper: Check user has yacht access
│   ├── validate_user_role.sql         # Helper: Check user role permission
│   └── create_audit_log_entry.sql     # Helper: Create audit log
│
├── 01_faults/
│   ├── report_fault.sql               # RPC: report_fault
│   ├── acknowledge_fault.sql          # RPC: acknowledge_fault
│   ├── diagnose_fault.sql             # RPC: diagnose_fault
│   ├── update_fault.sql               # RPC: update_fault
│   ├── close_fault.sql                # RPC: close_fault
│   └── get_fault_details.sql          # RPC: get_fault_details (READ)
│
├── 02_work_orders/
│   ├── create_work_order.sql
│   ├── create_work_order_from_fault.sql    # NESTED ACTION
│   ├── assign_work_order.sql
│   ├── update_work_order_hours.sql
│   ├── close_work_order.sql
│   ├── cancel_work_order.sql
│   └── get_work_order_details.sql
│
├── 03_shopping_list/
│   ├── add_to_shopping_list.sql
│   ├── approve_shopping_item.sql
│   ├── commit_shopping_list.sql
│   ├── remove_from_shopping_list.sql
│   └── get_shopping_list_summary.sql
│
├── 04_receiving/
│   ├── start_receiving_session.sql
│   ├── add_receiving_item.sql
│   ├── check_in_item.sql              # Checkbox = truth
│   ├── commit_receiving_session.sql   # MULTI-STEP: review → accept → commit
│   ├── cancel_receiving_session.sql
│   └── get_receiving_session_details.sql
│
├── 05_handover/
│   ├── create_handover.sql
│   ├── acknowledge_handover.sql
│   └── get_unacknowledged_handovers.sql
│
├── 06_checklists/
│   ├── create_checklist.sql
│   ├── start_checklist_execution.sql
│   ├── complete_checklist_item.sql
│   ├── sign_off_checklist.sql
│   └── get_checklist_execution_status.sql
│
├── 07_maintenance/
│   ├── create_pm_schedule.sql
│   ├── record_pm_completion.sql
│   ├── defer_pm_task.sql
│   └── get_upcoming_pm_tasks.sql
│
├── 08_documents/
│   ├── upload_document_metadata.sql   # Store metadata after upload
│   ├── process_document_chunks.sql    # Trigger chunking
│   ├── semantic_search.sql            # ⚠️ Vector similarity search
│   └── get_document_viewer_data.sql   # Fetch doc + chunks
│
├── 09_inventory/
│   ├── adjust_inventory.sql
│   ├── transfer_inventory.sql
│   └── get_inventory_summary.sql
│
├── 10_crew/
│   ├── add_crew_rotation.sql
│   ├── record_embark.sql
│   ├── record_disembark.sql
│   └── get_current_crew.sql
│
├── 11_compliance/
│   ├── add_certificate.sql
│   ├── renew_certificate.sql
│   ├── add_service_contract.sql
│   └── record_contract_claim.sql
│
└── 12_analytics/
    ├── get_dashboard_overview.sql
    ├── get_fault_statistics.sql
    └── get_maintenance_compliance_report.sql
```

### 3.2 RPC Function Template

**STANDARD RPC PATTERN:**

```sql
-- supabase/rpc/01_faults/report_fault.sql

CREATE OR REPLACE FUNCTION public.report_fault(
  p_equipment_id UUID,
  p_fault_type TEXT,
  p_description TEXT,
  p_severity TEXT DEFAULT 'medium',
  p_requires_immediate_attention BOOLEAN DEFAULT FALSE,
  p_photo_urls TEXT[] DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER  -- ⚠️ Runs with elevated privileges
SET search_path = public
AS $$
DECLARE
  v_yacht_id UUID;
  v_user_id UUID;
  v_user_name TEXT;
  v_user_role TEXT;
  v_new_fault_id UUID;
  v_result JSON;
BEGIN
  -- 1. GET CURRENT USER CONTEXT
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- 2. GET USER DETAILS
  SELECT yacht_id, name, role
  INTO v_yacht_id, v_user_name, v_user_role
  FROM public.user_profiles
  WHERE id = v_user_id AND deleted_at IS NULL AND is_active = TRUE;

  IF v_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not found or inactive';
  END IF;

  -- 3. VALIDATE EQUIPMENT BELONGS TO USER'S YACHT
  IF NOT EXISTS (
    SELECT 1 FROM public.pms_equipment
    WHERE id = p_equipment_id
    AND yacht_id = v_yacht_id
    AND deleted_at IS NULL
  ) THEN
    RAISE EXCEPTION 'Equipment not found or access denied';
  END IF;

  -- 4. VALIDATE INPUT
  IF LENGTH(TRIM(p_description)) < 10 THEN
    RAISE EXCEPTION 'Description must be at least 10 characters';
  END IF;

  IF p_severity NOT IN ('low', 'medium', 'high', 'critical') THEN
    RAISE EXCEPTION 'Invalid severity level';
  END IF;

  -- 5. INSERT FAULT (RLS policies automatically enforce yacht isolation)
  INSERT INTO public.pms_faults (
    yacht_id,
    equipment_id,
    fault_type,
    description,
    severity,
    requires_immediate_attention,
    photo_urls,
    reported_by,
    reported_by_name,
    reported_by_role,
    status,
    reported_at
  ) VALUES (
    v_yacht_id,
    p_equipment_id,
    p_fault_type,
    p_description,
    p_severity,
    p_requires_immediate_attention,
    p_photo_urls,
    v_user_id,
    v_user_name,
    v_user_role,
    'reported',
    NOW()
  ) RETURNING id INTO v_new_fault_id;

  -- 6. CREATE AUDIT LOG ENTRY
  INSERT INTO public.pms_audit_log (
    yacht_id,
    action,
    entity_type,
    entity_id,
    user_id,
    user_name,
    user_role,
    new_values,
    changes_summary,
    risk_level,
    created_at
  ) VALUES (
    v_yacht_id,
    'report_fault',
    'fault',
    v_new_fault_id,
    v_user_id,
    v_user_name,
    v_user_role,
    jsonb_build_object(
      'equipment_id', p_equipment_id,
      'fault_type', p_fault_type,
      'severity', p_severity
    ),
    format('Reported %s fault on equipment %s', p_severity, p_equipment_id),
    'low',
    NOW()
  );

  -- 7. CHECK IF AUTO-ACTIONS NEEDED
  -- Example: If critical fault, auto-create handover item
  IF p_severity = 'critical' THEN
    INSERT INTO public.pms_handover (
      yacht_id,
      entity_type,
      entity_id,
      summary,
      priority,
      created_by,
      created_by_name,
      created_at
    ) VALUES (
      v_yacht_id,
      'fault',
      v_new_fault_id,
      'CRITICAL FAULT: ' || p_description,
      'critical',
      v_user_id,
      v_user_name,
      NOW()
    );
  END IF;

  -- 8. RETURN SUCCESS RESULT
  v_result := jsonb_build_object(
    'success', TRUE,
    'fault_id', v_new_fault_id,
    'message', 'Fault reported successfully'
  );

  RETURN v_result;

EXCEPTION
  WHEN OTHERS THEN
    -- Error handling
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', SQLERRM
    );
END;
$$;

-- ⚠️ GRANT EXECUTE TO AUTHENTICATED USERS
GRANT EXECUTE ON FUNCTION public.report_fault TO authenticated;

-- COMMENT
COMMENT ON FUNCTION public.report_fault IS 'MICRO-ACTION: report_fault - Create new fault record with validation and audit trail';
```

**KEY PATTERNS IN EVERY RPC:**
1. ✅ Get current user context (`auth.uid()`)
2. ✅ Validate user has yacht access
3. ✅ Validate input data
4. ✅ Execute mutation (RLS automatically enforces yacht isolation)
5. ✅ Create audit log entry
6. ✅ Handle auto-triggers (if any)
7. ✅ Return structured JSON result
8. ✅ Error handling with try/catch
9. ✅ Grant execute to authenticated users only

---

## 4. MICRO-ACTION ORGANIZATION

### 4.1 Action Registry (Central Source of Truth)

```typescript
// src/lib/actions/registry.ts

export enum ActionCluster {
  FIX_SOMETHING = 'FIX_SOMETHING',
  DO_MAINTENANCE = 'DO_MAINTENANCE',
  MANAGE_EQUIPMENT = 'MANAGE_EQUIPMENT',
  INVENTORY_PARTS = 'INVENTORY_PARTS',
  HANDOVER = 'HANDOVER',
  COMPLIANCE = 'COMPLIANCE',
  DOCUMENTS = 'DOCUMENTS',
  PURCHASING = 'PURCHASING',
  CHECKLISTS = 'CHECKLISTS',
  SHIPYARD = 'SHIPYARD',
  FLEET = 'FLEET',
  SYSTEM_UTILITY = 'SYSTEM_UTILITY',
}

export enum ActionClassification {
  READ = 'READ',
  MUTATE_LOW = 'MUTATE_LOW',
  MUTATE_MEDIUM = 'MUTATE_MEDIUM',
  MUTATE_HIGH = 'MUTATE_HIGH',
}

export interface ActionDefinition {
  id: string;                          // Unique action ID
  name: string;                        // Human-readable name
  cluster: ActionCluster;              // Which cluster?
  classification: ActionClassification; // Risk level
  allowedRoles: UserRole[];            // Who can execute?
  requiresSignature: boolean;          // High-value actions
  isMultiStep: boolean;                // Multi-step journey?
  steps?: ActionStep[];                // If multi-step
  rpcFunction?: string;                // Supabase RPC function name
  affectedTables: string[];            // Which tables mutated?
  situationalStates?: string[];        // Situational states this action affects
  canTriggerActions?: string[];        // Actions this can trigger
}

export interface ActionStep {
  step: number;
  name: string;
  type: 'prefill' | 'user_input' | 'preview' | 'execute' | 'success';
  isOptional: boolean;
}

// ⚠️ COMPLETE ACTION REGISTRY - 67+ ACTIONS
export const ACTION_REGISTRY: Record<string, ActionDefinition> = {
  // CLUSTER: FIX_SOMETHING
  report_fault: {
    id: 'report_fault',
    name: 'Report Fault',
    cluster: ActionCluster.FIX_SOMETHING,
    classification: ActionClassification.MUTATE_LOW,
    allowedRoles: ['crew', 'engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'report_fault',
    affectedTables: ['pms_faults', 'pms_audit_log'],
    situationalStates: ['fault_reported'],
    canTriggerActions: ['create_handover'], // If critical fault
  },

  acknowledge_fault: {
    id: 'acknowledge_fault',
    name: 'Acknowledge Fault',
    cluster: ActionCluster.FIX_SOMETHING,
    classification: ActionClassification.MUTATE_LOW,
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'acknowledge_fault',
    affectedTables: ['pms_faults', 'pms_audit_log'],
    situationalStates: ['fault_acknowledged'],
  },

  diagnose_fault: {
    id: 'diagnose_fault',
    name: 'Diagnose Fault',
    cluster: ActionCluster.FIX_SOMETHING,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'diagnose_fault',
    affectedTables: ['pms_faults', 'pms_audit_log'],
    situationalStates: ['fault_diagnosed'],
  },

  create_work_order_from_fault: {
    id: 'create_work_order_from_fault',
    name: 'Create Work Order from Fault',
    cluster: ActionCluster.FIX_SOMETHING,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: true,  // ⚠️ NESTED ACTION
    steps: [
      { step: 1, name: 'Prefill from Fault', type: 'prefill', isOptional: false },
      { step: 2, name: 'User Edits WO Details', type: 'user_input', isOptional: false },
      { step: 3, name: 'Preview WO', type: 'preview', isOptional: true },
      { step: 4, name: 'Create WO', type: 'execute', isOptional: false },
      { step: 5, name: 'Update Fault Status', type: 'execute', isOptional: false },
      { step: 6, name: 'Success', type: 'success', isOptional: false },
    ],
    rpcFunction: 'create_work_order_from_fault',
    affectedTables: ['pms_work_orders', 'pms_faults', 'pms_audit_log'],
    situationalStates: ['fault_work_created', 'work_order_draft'],
  },

  // CLUSTER: DO_MAINTENANCE
  create_pm_schedule: {
    id: 'create_pm_schedule',
    name: 'Create PM Schedule',
    cluster: ActionCluster.DO_MAINTENANCE,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'create_pm_schedule',
    affectedTables: ['pms_maintenance_schedules', 'pms_audit_log'],
  },

  // CLUSTER: PURCHASING
  add_to_shopping_list: {
    id: 'add_to_shopping_list',
    name: 'Add to Shopping List',
    cluster: ActionCluster.PURCHASING,
    classification: ActionClassification.MUTATE_LOW,
    allowedRoles: ['crew', 'engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'add_to_shopping_list',
    affectedTables: ['pms_shopping_list', 'pms_audit_log'],
    situationalStates: ['shopping_list_candidate'],
  },

  approve_shopping_item: {
    id: 'approve_shopping_item',
    name: 'Approve Shopping Item',
    cluster: ActionCluster.PURCHASING,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['chief_engineer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'approve_shopping_item',
    affectedTables: ['pms_shopping_list', 'pms_audit_log'],
    situationalStates: ['shopping_list_active', 'shopping_list_approved'],
  },

  commit_shopping_list: {
    id: 'commit_shopping_list',
    name: 'Commit Shopping List to PO',
    cluster: ActionCluster.PURCHASING,
    classification: ActionClassification.MUTATE_HIGH, // ⚠️ Financial commitment
    allowedRoles: ['chief_engineer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: true, // ⚠️ Requires signature if >$1000
    isMultiStep: true,
    steps: [
      { step: 1, name: 'Review Items', type: 'preview', isOptional: false },
      { step: 2, name: 'Select Supplier', type: 'user_input', isOptional: false },
      { step: 3, name: 'Confirm Total', type: 'preview', isOptional: false },
      { step: 4, name: 'Sign (if required)', type: 'user_input', isOptional: true },
      { step: 5, name: 'Execute Commit', type: 'execute', isOptional: false },
      { step: 6, name: 'Success', type: 'success', isOptional: false },
    ],
    rpcFunction: 'commit_shopping_list',
    affectedTables: ['pms_shopping_list', 'pms_purchase_orders', 'pms_audit_log'],
    situationalStates: ['shopping_list_committed', 'purchase_order_sent'],
  },

  commit_receiving_session: {
    id: 'commit_receiving_session',
    name: 'Commit Receiving Session',
    cluster: ActionCluster.PURCHASING,
    classification: ActionClassification.MUTATE_HIGH, // ⚠️ Immutable after commit
    allowedRoles: ['chief_engineer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: true, // ⚠️ Always requires signature
    isMultiStep: true,
    steps: [
      { step: 1, name: 'Review Checked Items', type: 'preview', isOptional: false },
      { step: 2, name: 'Verify Discrepancies', type: 'user_input', isOptional: true },
      { step: 3, name: 'Sign Off', type: 'user_input', isOptional: false },
      { step: 4, name: 'Execute Commit', type: 'execute', isOptional: false },
      { step: 5, name: 'Update Inventory', type: 'execute', isOptional: false },
      { step: 6, name: 'Update Shopping List', type: 'execute', isOptional: false },
      { step: 7, name: 'Success', type: 'success', isOptional: false },
    ],
    rpcFunction: 'commit_receiving_session',
    affectedTables: ['pms_receiving_sessions', 'pms_receiving_items', 'pms_inventory_transactions', 'pms_shopping_list', 'pms_audit_log'],
    situationalStates: ['receiving_committed', 'shopping_list_fulfilled', 'inventory_updated'],
  },

  // CLUSTER: CHECKLISTS
  execute_checklist: {
    id: 'execute_checklist',
    name: 'Execute Checklist',
    cluster: ActionCluster.CHECKLISTS,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['crew', 'engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain'],
    requiresSignature: true, // Signature on completion
    isMultiStep: true,
    steps: [
      { step: 1, name: 'Start Execution', type: 'execute', isOptional: false },
      { step: 2, name: 'Complete Items', type: 'user_input', isOptional: false },
      { step: 3, name: 'Handle Failures', type: 'user_input', isOptional: true },
      { step: 4, name: 'Sign Off', type: 'user_input', isOptional: false },
      { step: 5, name: 'Finalize', type: 'execute', isOptional: false },
    ],
    rpcFunction: 'start_checklist_execution', // Start only, items completed separately
    affectedTables: ['pms_checklist_executions', 'pms_checklist_execution_items', 'pms_work_orders', 'pms_audit_log'],
    canTriggerActions: ['auto_create_work_order_on_checklist_failure'],
  },

  // CLUSTER: DOCUMENTS
  upload_document: {
    id: 'upload_document',
    name: 'Upload Document',
    cluster: ActionCluster.DOCUMENTS,
    classification: ActionClassification.MUTATE_MEDIUM,
    allowedRoles: ['engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: true,
    steps: [
      { step: 1, name: 'Upload to Storage', type: 'execute', isOptional: false },
      { step: 2, name: 'Store Metadata', type: 'execute', isOptional: false },
      { step: 3, name: 'Trigger Chunking', type: 'execute', isOptional: true },
      { step: 4, name: 'Generate Embeddings', type: 'execute', isOptional: true },
    ],
    rpcFunction: 'upload_document_metadata',
    affectedTables: ['pms_documents', 'pms_document_chunks', 'pms_audit_log'],
    canTriggerActions: ['process_document_chunks'],
  },

  show_manual_section: {
    id: 'show_manual_section',
    name: 'Show Manual Section',
    cluster: ActionCluster.DOCUMENTS,
    classification: ActionClassification.READ,
    allowedRoles: ['crew', 'engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin'],
    requiresSignature: false,
    isMultiStep: false,
    rpcFunction: 'semantic_search', // ⚠️ Vector similarity search
    affectedTables: [],
  },

  // ... (Continue for all 67+ actions)
};

// Helper: Get action definition
export function getActionDefinition(actionId: string): ActionDefinition | undefined {
  return ACTION_REGISTRY[actionId];
}

// Helper: Get actions by cluster
export function getActionsByCluster(cluster: ActionCluster): ActionDefinition[] {
  return Object.values(ACTION_REGISTRY).filter(action => action.cluster === cluster);
}

// Helper: Check if user can execute action
export function canUserExecuteAction(userRole: UserRole, actionId: string): boolean {
  const action = getActionDefinition(actionId);
  if (!action) return false;
  return action.allowedRoles.includes(userRole);
}
```

---

## 5. RPC FUNCTION PATTERNS

### 5.1 Naming Convention

**RULE:** RPC function name = action ID (snake_case)

```
Action ID: report_fault          → RPC: report_fault()
Action ID: commit_shopping_list  → RPC: commit_shopping_list()
Action ID: execute_checklist     → RPC: start_checklist_execution()
```

### 5.2 Multi-Step Actions

**For multi-step actions:**
- Create ONE RPC per logical step
- Frontend orchestrates the multi-step flow
- Backend ensures each step is atomic

**Example: commit_receiving_session (Multi-step)**

```sql
-- Step 1: Review (READ-only, no RPC needed, just fetch data)

-- Step 2: Verify discrepancies (UPDATE receiving_items with notes)
CREATE OR REPLACE FUNCTION update_receiving_item_notes(
  p_item_id UUID,
  p_notes TEXT
) RETURNS JSON ...

-- Step 3: Sign off (UPDATE receiving_session with signature)
CREATE OR REPLACE FUNCTION sign_receiving_session(
  p_session_id UUID,
  p_signature_data JSONB
) RETURNS JSON ...

-- Step 4: Execute commit (FINAL MUTATION - immutable after this)
CREATE OR REPLACE FUNCTION commit_receiving_session(
  p_session_id UUID
) RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_session RECORD;
BEGIN
  -- 1. Validate session status
  SELECT * INTO v_session
  FROM pms_receiving_sessions
  WHERE id = p_session_id;

  IF v_session.status != 'review' THEN
    RAISE EXCEPTION 'Session must be in review status to commit';
  END IF;

  IF v_session.signature_data IS NULL THEN
    RAISE EXCEPTION 'Session must be signed before committing';
  END IF;

  -- 2. Process ONLY checked items (checkbox = truth)
  FOR item IN
    SELECT * FROM pms_receiving_items
    WHERE receiving_session_id = p_session_id
    AND checked = TRUE
  LOOP
    -- Create inventory transaction
    INSERT INTO pms_inventory_transactions (...) VALUES (...);

    -- Update shopping list item
    UPDATE pms_shopping_list
    SET status = 'fulfilled', fulfilled_at = NOW()
    WHERE id = item.shopping_list_item_id;
  END LOOP;

  -- 3. Mark session as committed (IMMUTABLE)
  UPDATE pms_receiving_sessions
  SET status = 'committed', committed_at = NOW()
  WHERE id = p_session_id;

  -- 4. Audit log
  INSERT INTO pms_audit_log (...) VALUES (...);

  RETURN jsonb_build_object('success', TRUE);
END;
$$;
```

Frontend orchestrates:
```typescript
// Frontend: src/lib/actions/executors/receiving-actions.ts

export async function commitReceivingSession(sessionId: string) {
  // Step 1: Review (fetch data)
  const session = await supabase.rpc('get_receiving_session_details', { p_session_id: sessionId });

  // Step 2: User verifies discrepancies (modal updates notes via update_receiving_item_notes)

  // Step 3: User signs (modal captures signature, calls sign_receiving_session)

  // Step 4: Final commit (immutable)
  const result = await supabase.rpc('commit_receiving_session', { p_session_id: sessionId });

  return result;
}
```

---

## 6. SUPABASE POLICIES ORGANIZATION

### 6.1 Policy File Structure

```
supabase/policies/
├── 00_global_policies.sql         # ⚠️ FOUNDATIONAL: Yacht isolation
├── 01_faults_policies.sql
├── 02_work_orders_policies.sql
├── 03_shopping_list_policies.sql
├── 04_receiving_policies.sql
├── 05_handover_policies.sql
├── 06_checklists_policies.sql
├── 07_maintenance_policies.sql
├── 08_documents_policies.sql
├── 09_inventory_policies.sql
├── 10_crew_policies.sql
├── 11_compliance_policies.sql
└── 12_storage_policies.sql        # ⚠️ CRITICAL: Storage buckets
```

### 6.2 Global Policies (Yacht Isolation)

```sql
-- supabase/policies/00_global_policies.sql

-- ⚠️ CRITICAL: This pattern MUST be replicated on EVERY table

-- EXAMPLE: pms_faults table
ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;

-- Policy 1: Users can SELECT faults on their own yacht
CREATE POLICY "Users view faults on own yacht" ON public.pms_faults
  FOR SELECT
  TO authenticated
  USING (
    yacht_id IN (
      SELECT yacht_id FROM public.user_profiles
      WHERE id = auth.uid()
      AND deleted_at IS NULL
      AND is_active = TRUE
    )
  );

-- Policy 2: All users can INSERT faults (creation)
CREATE POLICY "Users can create faults on own yacht" ON public.pms_faults
  FOR INSERT
  TO authenticated
  WITH CHECK (
    yacht_id IN (
      SELECT yacht_id FROM public.user_profiles
      WHERE id = auth.uid()
      AND deleted_at IS NULL
      AND is_active = TRUE
    )
  );

-- Policy 3: Engineers+ can UPDATE faults
CREATE POLICY "Engineers+ can update faults" ON public.pms_faults
  FOR UPDATE
  TO authenticated
  USING (
    yacht_id IN (
      SELECT yacht_id FROM public.user_profiles
      WHERE id = auth.uid()
      AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
      AND deleted_at IS NULL
      AND is_active = TRUE
    )
  );

-- Policy 4: Soft delete (not true DELETE)
CREATE POLICY "Chiefs+ can soft delete faults" ON public.pms_faults
  FOR UPDATE
  TO authenticated
  USING (
    yacht_id IN (
      SELECT yacht_id FROM public.user_profiles
      WHERE id = auth.uid()
      AND role IN ('chief_engineer', 'captain', 'admin')
      AND deleted_at IS NULL
    )
  )
  WITH CHECK (
    deleted_at IS NOT NULL
    AND deleted_by = auth.uid()
  );

-- ⚠️ CRITICAL: NO DELETE POLICY (soft delete only)
-- Users should NEVER be able to truly DELETE rows (audit trail)

-- ========================================================
-- APPLY SAME PATTERN TO ALL TABLES
-- ========================================================
```

### 6.3 Storage Bucket Policies (⚠️ CRITICAL FOR DOCUMENT VIEWER)

```sql
-- supabase/policies/12_storage_policies.sql

-- ⚠️ CRITICAL: Storage bucket policies for documents

-- BUCKET: documents
-- Contains: PDFs, manuals, drawings, SOPs

-- Policy 1: Users can SELECT (read) documents on their own yacht
CREATE POLICY "Users can view documents on own yacht"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM public.user_profiles
    WHERE id = auth.uid()
    AND deleted_at IS NULL
    AND is_active = TRUE
  )
);

-- Policy 2: Engineers+ can INSERT (upload) documents
CREATE POLICY "Engineers+ can upload documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM public.user_profiles
    WHERE id = auth.uid()
    AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
    AND deleted_at IS NULL
  )
);

-- Policy 3: Chiefs+ can DELETE documents
CREATE POLICY "Chiefs+ can delete documents"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM public.user_profiles
    WHERE id = auth.uid()
    AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
    AND deleted_at IS NULL
  )
);

-- ⚠️ CRITICAL: Storage folder structure
-- documents/
--   {yacht_id}/
--     manuals/
--       {document_id}.pdf
--     drawings/
--       {document_id}.pdf
--     sops/
--       {document_id}.pdf
--     certificates/
--       {document_id}.pdf

-- BUCKET: checklist-photos
-- Contains: Photos taken during checklist execution

CREATE POLICY "Users can view checklist photos on own yacht"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'checklist-photos'
  AND (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM public.user_profiles
    WHERE id = auth.uid()
    AND deleted_at IS NULL
  )
);

CREATE POLICY "Users can upload checklist photos"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'checklist-photos'
  AND (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM public.user_profiles
    WHERE id = auth.uid()
    AND deleted_at IS NULL
  )
);

-- ========================================================
-- ⚠️ GRAVE DANGER: CORS ISSUES WITH STORAGE
-- ========================================================
-- If document viewer shows CORS errors, it's because:
-- 1. Storage bucket CORS not configured in Supabase dashboard
-- 2. Frontend trying to access storage from wrong origin
-- 3. Storage policies not allowing access

-- SOLUTION: Configure CORS in Supabase Dashboard
-- Settings → Storage → documents bucket → CORS Configuration:
-- Allowed Origins: http://localhost:3000, https://your-domain.com
-- Allowed Methods: GET, POST, PUT, DELETE
-- Allowed Headers: authorization, x-client-info, apikey, content-type
```

---

## 7. CORS CONFIGURATION (⚠️ CRITICAL)

### 7.1 Supabase Edge Functions CORS

```typescript
// supabase/functions/_shared/cors.ts

/**
 * ⚠️ CRITICAL: CORS configuration for Edge Functions
 *
 * PROBLEM: Document viewer, semantic search, and other Edge Functions
 * were failing with CORS errors because:
 * 1. No CORS headers in responses
 * 2. No OPTIONS preflight handling
 * 3. Wrong allowed origins
 *
 * SOLUTION: Use this helper in EVERY Edge Function
 */

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*', // ⚠️ In production, use specific domain
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, PUT, DELETE',
};

export function handleCors(req: Request) {
  // Handle OPTIONS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }
}

export function corsResponse(data: any, status: number = 200) {
  return new Response(
    JSON.stringify(data),
    {
      status,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json',
      },
    }
  );
}
```

**USE IN EVERY EDGE FUNCTION:**

```typescript
// supabase/functions/semantic-search/index.ts

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors, corsResponse } from '../_shared/cors.ts';

serve(async (req) => {
  // ⚠️ CRITICAL: Handle CORS preflight
  const corsCheck = handleCors(req);
  if (corsCheck) return corsCheck;

  try {
    const { query, yacht_id } = await req.json();

    // ... semantic search logic

    return corsResponse({ results });
  } catch (error) {
    return corsResponse({ error: error.message }, 500);
  }
});
```

### 7.2 Next.js API Routes CORS

```typescript
// src/app/api/actions/faults/report-fault/route.ts

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

// ⚠️ CRITICAL: Set CORS headers on API routes

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*', // ⚠️ Use specific domain in production
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}

export async function POST(request: NextRequest) {
  const supabase = createClient();

  try {
    const body = await request.json();

    // Call Supabase RPC
    const { data, error } = await supabase.rpc('report_fault', body);

    if (error) throw error;

    return NextResponse.json(data, {
      headers: {
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error.message },
      {
        status: 500,
        headers: {
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  }
}
```

### 7.3 Next.js Middleware CORS

```typescript
// src/middleware.ts

import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();

  // ⚠️ CRITICAL: Add CORS headers to all responses
  res.headers.set('Access-Control-Allow-Origin', '*'); // ⚠️ Use specific domain in production
  res.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Handle OPTIONS preflight
  if (req.method === 'OPTIONS') {
    return new NextResponse(null, { status: 200, headers: res.headers });
  }

  // Supabase auth
  const supabase = createMiddlewareClient({ req, res });
  await supabase.auth.getSession();

  return res;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
```

### 7.4 Next.js Config CORS

```javascript
// next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' }, // ⚠️ Use specific domain in production
          { key: 'Access-Control-Allow-Methods', value: 'GET,DELETE,PATCH,POST,PUT,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization' },
        ],
      },
    ];
  },

  // ⚠️ CRITICAL: Allow images from Supabase storage
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'vzsohavtuotocgrfkfyd.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },
};

module.exports = nextConfig;
```

---

## 8. DOCUMENT VIEWER ARCHITECTURE

**⚠️ CRITICAL SECTION - Addresses your document viewer CORS issues**

### 8.1 Document Upload Flow

```
1. User selects PDF file
   ↓
2. Frontend uploads to Supabase Storage (documents bucket)
   File path: documents/{yacht_id}/manuals/{document_id}.pdf
   ↓
3. Frontend calls RPC: upload_document_metadata()
   - Stores metadata in pms_documents table
   - Sets chunking_status = 'pending'
   ↓
4. Supabase trigger or Edge Function processes document:
   - Extract text from PDF
   - Split into chunks (~500 tokens each)
   - Generate embeddings (OpenAI ada-002)
   - Store in pms_document_chunks table
   ↓
5. Set chunking_status = 'completed'
```

### 8.2 Document Viewer Component

```typescript
// src/app/(dashboard)/documents/viewer/[documentId]/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useSupabase } from '@/hooks/useSupabase';
import { SemanticSearchPanel } from '@/app/(dashboard)/documents/_components/SemanticSearchPanel';

export default function DocumentViewerPage({ params }: { params: { documentId: string } }) {
  const supabase = useSupabase();
  const [document, setDocument] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [chunks, setChunks] = useState([]);

  useEffect(() => {
    loadDocument();
  }, [params.documentId]);

  async function loadDocument() {
    // 1. Fetch document metadata
    const { data: doc, error: docError } = await supabase
      .from('pms_documents')
      .select('*')
      .eq('id', params.documentId)
      .single();

    if (docError) throw docError;
    setDocument(doc);

    // 2. Get signed URL for PDF (⚠️ CRITICAL: Signed URL avoids CORS issues)
    const { data: signedUrlData, error: urlError } = await supabase.storage
      .from('documents')
      .createSignedUrl(doc.file_path, 3600); // Valid for 1 hour

    if (urlError) throw urlError;
    setPdfUrl(signedUrlData.signedUrl);

    // 3. Fetch chunks for semantic search
    const { data: chunksData, error: chunksError } = await supabase
      .from('pms_document_chunks')
      .select('*')
      .eq('document_id', params.documentId)
      .order('chunk_index', { ascending: true });

    if (chunksError) throw chunksError;
    setChunks(chunksData);
  }

  return (
    <div className="grid grid-cols-2 gap-4 h-screen">
      {/* Left: PDF Viewer */}
      <div className="col-span-1">
        <iframe
          src={pdfUrl}
          className="w-full h-full"
          title={document?.name}
        />
      </div>

      {/* Right: Semantic Search */}
      <div className="col-span-1">
        <SemanticSearchPanel
          documentId={params.documentId}
          chunks={chunks}
        />
      </div>
    </div>
  );
}
```

### 8.3 Semantic Search Panel

```typescript
// src/app/(dashboard)/documents/_components/SemanticSearchPanel.tsx

'use client';

import { useState } from 'react';
import { useSupabase } from '@/hooks/useSupabase';

export function SemanticSearchPanel({ documentId, chunks }) {
  const supabase = useSupabase();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  async function handleSearch() {
    setIsSearching(true);

    try {
      // ⚠️ Call Edge Function for semantic search
      const { data, error } = await supabase.functions.invoke('semantic-search', {
        body: {
          query,
          document_id: documentId,
          limit: 5,
        },
      });

      if (error) throw error;

      setResults(data.results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Semantic Search</h2>

      {/* Search Input */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about this document..."
          className="flex-1 px-3 py-2 border rounded"
        />
        <button
          onClick={handleSearch}
          disabled={isSearching || !query}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {isSearching ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {results.map((result, index) => (
          <div key={index} className="p-3 border rounded">
            <div className="text-sm text-gray-500 mb-1">
              Page {result.page_number} • Similarity: {(result.similarity * 100).toFixed(1)}%
            </div>
            <div className="text-sm">{result.chunk_text}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 8.4 Semantic Search Edge Function

```typescript
// supabase/functions/semantic-search/index.ts

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors, corsResponse } from '../_shared/cors.ts';

serve(async (req) => {
  // ⚠️ CRITICAL: Handle CORS
  const corsCheck = handleCors(req);
  if (corsCheck) return corsCheck;

  try {
    const { query, document_id, limit = 5 } = await req.json();

    // 1. Generate embedding for query (using OpenAI)
    const openaiResponse = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'text-embedding-ada-002',
        input: query,
      }),
    });

    const openaiData = await openaiResponse.json();
    const queryEmbedding = openaiData.data[0].embedding;

    // 2. Search similar chunks using vector similarity
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );

    const { data, error } = await supabase.rpc('match_document_chunks', {
      query_embedding: queryEmbedding,
      match_document_id: document_id,
      match_threshold: 0.7,
      match_count: limit,
    });

    if (error) throw error;

    return corsResponse({ results: data });
  } catch (error) {
    return corsResponse({ error: error.message }, 500);
  }
});
```

### 8.5 Vector Similarity RPC

```sql
-- supabase/rpc/08_documents/match_document_chunks.sql

CREATE OR REPLACE FUNCTION match_document_chunks(
  query_embedding vector(1536),
  match_document_id UUID DEFAULT NULL,
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  chunk_text TEXT,
  page_number INTEGER,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    pms_document_chunks.id,
    pms_document_chunks.document_id,
    pms_document_chunks.chunk_text,
    pms_document_chunks.page_number,
    1 - (pms_document_chunks.embedding <=> query_embedding) AS similarity
  FROM pms_document_chunks
  WHERE
    (match_document_id IS NULL OR pms_document_chunks.document_id = match_document_id)
    AND 1 - (pms_document_chunks.embedding <=> query_embedding) > match_threshold
  ORDER BY pms_document_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION match_document_chunks TO authenticated;
```

---

## 9. NESTED ACTIONS (ACTIONS WITHIN ACTIONS)

### 9.1 Pattern: Action Triggering Another Action

**Example: Critical fault auto-creates handover**

```typescript
// src/lib/actions/executors/fault-actions.ts

export async function reportFault(data: ReportFaultInput) {
  // 1. Call RPC to create fault
  const { data: result, error } = await supabase.rpc('report_fault', data);

  if (error) throw error;

  // 2. Check if fault is critical
  if (data.severity === 'critical') {
    // ⚠️ NESTED ACTION: Auto-create handover
    await createHandover({
      entity_type: 'fault',
      entity_id: result.fault_id,
      summary: `CRITICAL FAULT: ${data.description}`,
      priority: 'critical',
    });
  }

  return result;
}
```

### 9.2 Pattern: Multi-Step User Journey

**Example: Create Work Order from Fault (Multi-step)**

```typescript
// Frontend component orchestrates multiple steps

export function CreateWorkOrderFromFaultModal({ faultId, isOpen, onClose }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({});

  // Step 1: Prefill from fault
  useEffect(() => {
    if (isOpen && faultId) {
      loadFaultData();
    }
  }, [isOpen, faultId]);

  async function loadFaultData() {
    const { data: fault } = await supabase
      .from('pms_faults')
      .select('*')
      .eq('id', faultId)
      .single();

    setFormData({
      fault_id: faultId,
      equipment_id: fault.equipment_id,
      title: `Fix: ${fault.description.substring(0, 50)}...`,
      description: fault.diagnosis || fault.description,
      priority: fault.severity,
    });

    setStep(2); // Move to user input step
  }

  // Step 2: User edits WO details
  function handleEdit(field, value) {
    setFormData({ ...formData, [field]: value });
  }

  // Step 3: Preview
  function handlePreview() {
    setStep(3);
  }

  // Step 4: Execute
  async function handleExecute() {
    const { data, error } = await supabase.rpc('create_work_order_from_fault', formData);

    if (error) throw error;

    setStep(5); // Success
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      {step === 1 && <div>Loading fault data...</div>}
      {step === 2 && (
        <EditWorkOrderForm
          data={formData}
          onChange={handleEdit}
          onNext={handlePreview}
        />
      )}
      {step === 3 && (
        <PreviewWorkOrder
          data={formData}
          onBack={() => setStep(2)}
          onExecute={handleExecute}
        />
      )}
      {step === 5 && <SuccessMessage onClose={onClose} />}
    </Modal>
  );
}
```

---

## 10. SECURITY BOUNDARIES

### 10.1 Client vs Server Execution

**RULE:** NEVER trust client-side permissions. Always validate on server (RPC).

```typescript
// ❌ BAD: Client-side only check
function canCloseWorkOrder(userRole: string) {
  return ['chief_engineer', 'captain', 'admin'].includes(userRole);
}

if (canCloseWorkOrder(user.role)) {
  // User can bypass this by editing client code
  await supabase.from('pms_work_orders').update({ status: 'completed' });
}

// ✅ GOOD: Server-side check in RPC
// RPC function validates role before allowing mutation
await supabase.rpc('close_work_order', { p_work_order_id: woId });
```

### 10.2 Service Role vs Authenticated Role

**⚠️ CRITICAL RULE:** Service role bypasses RLS. Use with extreme caution.

```typescript
// ❌ DANGER: Service role in frontend (NEVER DO THIS)
const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // ⚠️ EXPOSED TO CLIENT
);

// ✅ CORRECT: Service role ONLY in backend (API routes, Edge Functions)
// src/app/api/admin/route.ts (server-side only)
import { createClient } from '@supabase/supabase-js';

export async function POST(req: Request) {
  const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!, // ⚠️ Server-side only
    { auth: { persistSession: false } }
  );

  // Admin operations that bypass RLS
  const { data } = await supabaseAdmin.from('pms_work_orders').select('*'); // All yachts

  return Response.json(data);
}
```

### 10.3 Yacht Isolation Enforcement

**Every RPC function MUST:**
1. Get user's yacht_id from user_profiles
2. Validate entity belongs to user's yacht
3. Use RLS policies as backup

```sql
-- ⚠️ ALWAYS VALIDATE YACHT ACCESS

CREATE OR REPLACE FUNCTION close_work_order(p_work_order_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_user_yacht_id UUID;
  v_wo_yacht_id UUID;
BEGIN
  -- 1. Get user's yacht
  SELECT yacht_id INTO v_user_yacht_id
  FROM public.user_profiles
  WHERE id = auth.uid();

  -- 2. Get work order's yacht
  SELECT yacht_id INTO v_wo_yacht_id
  FROM public.pms_work_orders
  WHERE id = p_work_order_id;

  -- 3. CRITICAL: Validate match
  IF v_user_yacht_id != v_wo_yacht_id THEN
    RAISE EXCEPTION 'Access denied: Work order belongs to different yacht';
  END IF;

  -- 4. Proceed with mutation
  UPDATE public.pms_work_orders
  SET status = 'completed', completed_at = NOW()
  WHERE id = p_work_order_id;

  RETURN jsonb_build_object('success', TRUE);
END;
$$;
```

---

## 11. DEPLOYMENT STRUCTURE

### 11.1 Environment Variables

```bash
# .env.local (development)
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-...

# .env.production (production)
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
OPENAI_API_KEY=sk-...
NEXT_PUBLIC_APP_URL=https://celesteos.com
```

### 11.2 Deployment Checklist

1. ✅ Deploy Supabase policies (run all SQL files in supabase/policies/)
2. ✅ Deploy Supabase RPC functions (run all SQL files in supabase/rpc/)
3. ✅ Deploy Edge Functions (`supabase functions deploy`)
4. ✅ Configure storage bucket CORS in Supabase dashboard
5. ✅ Deploy Next.js frontend to Vercel
6. ✅ Set environment variables in Vercel dashboard
7. ✅ Test CORS on production domain
8. ✅ Test RLS policies with different user roles
9. ✅ Test document upload and viewer
10. ✅ Test semantic search

---

## ⚠️ CRITICAL ISSUES FIXED

### Issue 1: CORS Errors on Document Viewer
**CAUSE:** No CORS headers in Edge Functions, no signed URLs for storage
**FIX:** Use corsHeaders in all Edge Functions, use signed URLs for PDFs

### Issue 2: RPC Functions Not Found
**CAUSE:** RPC functions not deployed, or wrong schema
**FIX:** Deploy all RPC functions from supabase/rpc/ folder, use `public.` schema

### Issue 3: RLS Policy Blocking Legitimate Access
**CAUSE:** Policies too restrictive, or yacht_id not matching
**FIX:** Validate yacht_id in RPC functions, use SECURITY DEFINER carefully

### Issue 4: Storage Policies Denying Upload
**CAUSE:** Storage policies check wrong folder structure
**FIX:** Use folder structure: `documents/{yacht_id}/category/{document_id}.pdf`

### Issue 5: Semantic Search Returns No Results
**CAUSE:** Embeddings not generated, or vector index missing
**FIX:** Create HNSW index on embedding column, ensure chunking complete

---

**END OF ARCHITECTURE V4**

This architecture solves your CORS, RPC, policies, and document viewer issues. Follow this EXACTLY.
