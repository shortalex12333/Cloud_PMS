'use client';

/**
 * =============================================================================
 * WORK ORDER LENS - Full Page View
 * =============================================================================
 *
 * CREATED: 2026-02-05
 * PURPOSE: Full-page lens for work order entities accessed via handover export links
 *
 * HANDOVER EXPORT FLOW:
 * ---------------------
 * 1. User clicks link in handover PDF/HTML: https://app.celeste7.ai/open?t=<JWS_TOKEN>
 * 2. /open page resolves token via POST /api/v1/open/resolve (handover-export service on Render)
 * 3. Token returns: { focus: { type: "work_order", id: "uuid" }, yacht_id, scope }
 * 4. /open page redirects to this lens: /work-orders/{id}
 * 5. This page fetches full work order data and renders it
 *
 * ALTERNATIVE FLOW (direct deep link):
 * ------------------------------------
 * 1. URL: /app?entity=work_order&id=uuid
 * 2. DeepLinkHandler.tsx intercepts and redirects to /work-orders/{id}
 *
 * DATA FETCHING:
 * --------------
 * - Uses microaction handler: viewWorkOrder() from @/lib/microactions/handlers/workOrders
 * - Requires ActionContext with yacht_id (from useAuth bootstrap)
 * - Queries Supabase table: pms_work_orders
 *
 * AUTHENTICATION:
 * ---------------
 * - Requires authenticated session with yachtId from bootstrap
 * - Shows error if not authenticated
 * - Real flow: user is already authenticated when arriving from /open token resolution
 *
 * =============================================================================
 * WHAT THIS SKELETON PROVIDES (for engineers to extend):
 * =============================================================================
 * - Route structure and Next.js dynamic routing pattern
 * - Auth check pattern (wait for authLoading + bootstrapping)
 * - Data fetching via microaction handler pattern
 * - Loading/error/success state management
 * - Basic responsive layout with header and content sections
 * - RelatedEmailsPanel integration
 *
 * =============================================================================
 * WHAT'S MISSING (for engineers to implement):
 * =============================================================================
 * - [ ] Action buttons (mark complete, assign, add note, add photo, etc.)
 * - [ ] Checklist display and interaction (pms_checklist_items)
 * - [ ] Parts list display (pms_work_order_parts)
 * - [ ] Edit modal for updating work order details
 * - [ ] Status transition buttons with confirmation
 * - [ ] Attachments/photos gallery
 * - [ ] Activity/audit log timeline
 * - [ ] Link to parent equipment
 * - [ ] Link to source fault (if created from fault)
 * - [ ] Print/export functionality
 * - [ ] Mobile-optimized touch interactions
 *
 * =============================================================================
 * RELATED FILES:
 * =============================================================================
 * - /src/lib/microactions/handlers/workOrders.ts - Data fetching logic
 * - /src/components/cards/WorkOrderCard.tsx - Card component (has action buttons)
 * - /src/app/open/page.tsx - Token resolution (redirects here)
 * - /src/app/app/DeepLinkHandler.tsx - Query param handling (redirects here)
 * - /apps/api/services/handover_export_service.py - Generates export HTML with links
 *
 * =============================================================================
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { viewWorkOrder } from '@/lib/microactions/handlers/workOrders';
import type { ActionContext } from '@/lib/microactions/types';
import {
  Loader2,
  ArrowLeft,
  Wrench,
  Clock,
  User,
  CheckCircle2,
  Calendar,
  AlertTriangle,
  Settings,
  FileText
} from 'lucide-react';
import { RelatedEmailsPanel } from '@/components/email/RelatedEmailsPanel';
import { cn } from '@/lib/utils';

/**
 * Work order data shape returned from viewWorkOrder handler
 * Maps to pms_work_orders table + computed fields
 */
interface WorkOrderData {
  id: string;
  title: string;
  description?: string;
  status: string;          // draft, open, in_progress, pending_parts, completed, closed, cancelled
  priority: string;        // low, medium, high, critical
  equipment_id?: string;   // FK to pms_equipment
  equipment_name?: string; // Denormalized for display
  assigned_to?: string;    // FK to user
  assigned_to_name?: string;
  created_at: string;
  completed_at?: string;
  due_date?: string;
  is_overdue?: boolean;    // Computed: due_date < now && not completed
  days_open?: number;      // Computed: days since created_at
}

export default function WorkOrderLensPage() {
  // ---------------------------------------------------------------------------
  // ROUTING & AUTH
  // ---------------------------------------------------------------------------
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading, bootstrapping } = useAuth();

  // ---------------------------------------------------------------------------
  // STATE
  // ---------------------------------------------------------------------------
  const [workOrder, setWorkOrder] = useState<WorkOrderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Extract work order ID from URL: /work-orders/[id]
  const workOrderId = params.id as string;

  // ---------------------------------------------------------------------------
  // DATA FETCHING
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // IMPORTANT: Wait for BOTH authLoading AND bootstrapping to complete
    // - authLoading: Supabase session check
    // - bootstrapping: Render API call to get yacht_id from MASTER DB
    // The yacht_id is required to query tenant-specific data
    if (authLoading || bootstrapping) return;

    // If no yacht context after bootstrap, user is not properly authenticated
    if (!user?.yachtId) {
      setError('Authentication required');
      setLoading(false);
      return;
    }

    const fetchWorkOrder = async () => {
      try {
        // Build ActionContext - required by all microaction handlers
        // This context ensures queries are scoped to the correct yacht/tenant
        const context: ActionContext = {
          yacht_id: user.yachtId!,
          user_id: user.id,
          user_role: user.role || 'member',
          entity_id: workOrderId,
          entity_type: 'work_order',
        };

        // Call microaction handler - this queries Supabase directly
        // See: /src/lib/microactions/handlers/workOrders.ts
        const result = await viewWorkOrder(context, { work_order_id: workOrderId });

        if (!result.success || !result.data) {
          setError(result.error?.message || 'Work order not found');
          setLoading(false);
          return;
        }

        // Extract work order from result
        const data = result.data as { work_order: WorkOrderData };
        setWorkOrder(data.work_order);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load work order');
        setLoading(false);
      }
    };

    fetchWorkOrder();
  }, [workOrderId, user, authLoading, bootstrapping]);

  // ---------------------------------------------------------------------------
  // STYLING HELPERS
  // ---------------------------------------------------------------------------

  /** Map status to visual style */
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed':
        return { bg: 'bg-green-500/10', text: 'text-green-400', label: 'Completed' };
      case 'in_progress':
        return { bg: 'bg-celeste-accent-subtle', text: 'text-celeste-accent', label: 'In Progress' };
      case 'cancelled':
        return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Cancelled' };
      case 'pending_parts':
        return { bg: 'bg-purple-500/10', text: 'text-purple-400', label: 'Pending Parts' };
      default:
        return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Pending' };
    }
  };

  /** Map priority to visual style */
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'critical':
      case 'urgent':
        return { bg: 'bg-red-500/10', text: 'text-red-400', label: priority.charAt(0).toUpperCase() + priority.slice(1) };
      case 'high':
        return { bg: 'bg-orange-500/10', text: 'text-orange-400', label: 'High' };
      case 'medium':
        return { bg: 'bg-amber-500/10', text: 'text-amber-400', label: 'Medium' };
      default:
        return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Low' };
    }
  };

  /** Format date for display */
  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // ---------------------------------------------------------------------------
  // LOADING STATE
  // ---------------------------------------------------------------------------
  if (loading || authLoading || bootstrapping) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-celeste-accent animate-spin mx-auto mb-4" />
          <p className="text-celeste-text-muted">Loading work order...</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center p-4">
        <div className="bg-celeste-bg-tertiary rounded-lg p-8 max-w-md w-full text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error</h2>
          <p className="text-celeste-text-muted mb-6">{error}</p>
          <button
            onClick={() => router.push('/app')}
            className="px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-white rounded-lg transition-colors"
          >
            Return to App
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // NULL CHECK
  // ---------------------------------------------------------------------------
  if (!workOrder) {
    return null;
  }

  const status = getStatusStyle(workOrder.status);
  const priority = getPriorityStyle(workOrder.priority);

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-celeste-black">
      {/* ===================================================================
          HEADER - Sticky with back navigation
          TODO: Add action buttons here (Edit, Mark Complete, etc.)
          =================================================================== */}
      <header className="bg-celeste-bg-tertiary/50 border-b border-celeste-text-secondary/50 sticky top-0 z-10 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-celeste-text-secondary/50 rounded-lg transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-celeste-text-muted" />
            </button>
            <div className="flex items-center gap-2">
              <Wrench className="w-5 h-5 text-celeste-accent" />
              <span className="text-sm text-celeste-text-muted uppercase tracking-wider">Work Order</span>
            </div>
            {/* TODO: Add action buttons here
            <div className="ml-auto flex gap-2">
              <ActionButton action="mark_work_order_complete" ... />
              <ActionButton action="assign_work_order" ... />
            </div>
            */}
          </div>
        </div>
      </header>

      {/* ===================================================================
          MAIN CONTENT
          =================================================================== */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* -----------------------------------------------------------------
            TITLE SECTION
            ----------------------------------------------------------------- */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-4">
            {workOrder.title}
          </h1>

          {/* Status & Priority Badges */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={cn('px-3 py-1 rounded-full text-sm font-medium', status.bg, status.text)}>
              {status.label}
            </span>
            <span className={cn('px-3 py-1 rounded-full text-sm font-medium', priority.bg, priority.text)}>
              {priority.label} Priority
            </span>
            {workOrder.is_overdue && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-500/10 text-red-400">
                Overdue
              </span>
            )}
          </div>

          {/* Equipment Link - TODO: Make clickable to navigate to equipment lens */}
          {workOrder.equipment_name && (
            <div className="flex items-center gap-2 text-celeste-text-muted mb-2">
              <Settings className="w-4 h-4" />
              <span>{workOrder.equipment_name}</span>
              {/* TODO: Add link: onClick={() => router.push(`/equipment/${workOrder.equipment_id}`)} */}
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            DESCRIPTION
            ----------------------------------------------------------------- */}
        {workOrder.description && (
          <div className="bg-celeste-bg-tertiary/50 rounded-lg p-6 mb-6 border border-celeste-text-secondary/50">
            <h2 className="text-sm font-semibold text-celeste-text-muted uppercase tracking-wider mb-3">
              Description
            </h2>
            <p className="text-celeste-border whitespace-pre-wrap">
              {workOrder.description}
            </p>
          </div>
        )}

        {/* -----------------------------------------------------------------
            DETAILS GRID
            TODO: Add more fields as needed (checklist progress, parts count)
            ----------------------------------------------------------------- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Assigned To */}
          {workOrder.assigned_to_name && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <User className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Assigned To</p>
                  <p className="text-celeste-border">{workOrder.assigned_to_name}</p>
                </div>
              </div>
            </div>
          )}

          {/* Created Date */}
          <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-celeste-text-disabled" />
              <div>
                <p className="text-xs text-celeste-text-disabled uppercase">Created</p>
                <p className="text-celeste-border">{formatDate(workOrder.created_at)}</p>
              </div>
            </div>
          </div>

          {/* Due Date */}
          {workOrder.due_date && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <Clock className={cn('w-5 h-5', workOrder.is_overdue ? 'text-red-500' : 'text-celeste-text-disabled')} />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Due Date</p>
                  <p className={cn(workOrder.is_overdue ? 'text-red-400' : 'text-celeste-border')}>
                    {formatDate(workOrder.due_date)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Completed Date */}
          {workOrder.completed_at && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Completed</p>
                  <p className="text-green-400">{formatDate(workOrder.completed_at)}</p>
                </div>
              </div>
            </div>
          )}

          {/* Days Open */}
          {workOrder.days_open !== undefined && workOrder.days_open > 0 && (
            <div className="bg-celeste-bg-tertiary/50 rounded-lg p-4 border border-celeste-text-secondary/50">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-celeste-text-disabled" />
                <div>
                  <p className="text-xs text-celeste-text-disabled uppercase">Days Open</p>
                  <p className="text-celeste-border">{workOrder.days_open} days</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* -----------------------------------------------------------------
            TODO: CHECKLIST SECTION
            Fetch from pms_checklist_items where work_order_id = this.id
            Display progress bar and interactive checklist items
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            TODO: PARTS SECTION
            Fetch from pms_work_order_parts where work_order_id = this.id
            Display parts list with quantities
            ----------------------------------------------------------------- */}

        {/* -----------------------------------------------------------------
            RELATED EMAILS
            Uses existing RelatedEmailsPanel component
            Fetches emails linked to this work order via object_type/object_id
            ----------------------------------------------------------------- */}
        <div className="bg-celeste-bg-tertiary/50 rounded-lg p-6 border border-celeste-text-secondary/50">
          <h2 className="text-sm font-semibold text-celeste-text-muted uppercase tracking-wider mb-4">
            Related Emails
          </h2>
          <RelatedEmailsPanel
            objectType="work_order"
            objectId={workOrder.id}
          />
        </div>
      </main>
    </div>
  );
}
