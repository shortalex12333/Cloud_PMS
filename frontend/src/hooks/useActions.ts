import { useState, useCallback } from 'react'
import {
  api,
  CreateNotePayload,
  CreateNoteResponse,
  CreateWorkOrderPayload,
  CreateWorkOrderResponse,
  AddNoteToWorkOrderPayload,
  AddNoteToWorkOrderResponse,
  CloseWorkOrderPayload,
  CloseWorkOrderResponse,
  AddItemToHandoverPayload,
  AddItemToHandoverResponse,
  AddDocumentToHandoverPayload,
  AddDocumentToHandoverResponse,
  AddPredictiveToHandoverPayload,
  AddPredictiveToHandoverResponse,
  EditHandoverSectionPayload,
  EditHandoverSectionResponse,
  ExportHandoverResponse,
  OpenDocumentPayload,
  OpenDocumentResponse,
  OrderPartPayload,
  OrderPartResponse,
  ExecuteActionPayload,
  ExecuteActionResponse
} from '@/lib/api-client'

// Re-export types
export type {
  CreateNotePayload,
  CreateWorkOrderPayload,
  AddNoteToWorkOrderPayload,
  CloseWorkOrderPayload,
  AddItemToHandoverPayload,
  AddDocumentToHandoverPayload,
  AddPredictiveToHandoverPayload,
  EditHandoverSectionPayload,
  OpenDocumentPayload,
  OrderPartPayload,
  ExecuteActionPayload
}

interface ActionState {
  isLoading: boolean
  error: string | null
}

/**
 * Hook for executing micro-actions in CelesteOS.
 *
 * All actions use:
 * - Base URL: https://api.celeste7.ai/webhook/
 * - Automatic JWT token refresh
 * - Auto-injected yacht_id from session
 *
 * @example
 * ```tsx
 * const { createWorkOrder, isLoading, error } = useActions()
 *
 * const handleCreate = async () => {
 *   const result = await createWorkOrder({
 *     equipment_id: 'uuid',
 *     title: 'Fix pump',
 *     description: 'Pump is leaking',
 *     priority: 'high'
 *   })
 * }
 * ```
 */
export function useActions() {
  const [state, setState] = useState<ActionState>({
    isLoading: false,
    error: null
  })

  const wrapAction = useCallback(<T, R>(
    action: (payload: T) => Promise<R>
  ) => {
    return async (payload: T): Promise<R | null> => {
      setState({ isLoading: true, error: null })
      try {
        const result = await action(payload)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })

        // Re-throw auth errors
        if (errorMessage === 'Not authenticated' || errorMessage === 'Failed to refresh token') {
          throw err
        }
        return null
      }
    }
  }, [])

  // ============================================================
  // NOTES
  // ============================================================

  const createNote = useCallback(
    (payload: CreateNotePayload) => wrapAction(api.createNote)(payload),
    [wrapAction]
  )

  // ============================================================
  // WORK ORDERS
  // ============================================================

  const createWorkOrder = useCallback(
    (payload: CreateWorkOrderPayload) => wrapAction(api.createWorkOrder)(payload),
    [wrapAction]
  )

  const addNoteToWorkOrder = useCallback(
    (payload: AddNoteToWorkOrderPayload) => wrapAction(api.addNoteToWorkOrder)(payload),
    [wrapAction]
  )

  const closeWorkOrder = useCallback(
    (payload: CloseWorkOrderPayload) => wrapAction(api.closeWorkOrder)(payload),
    [wrapAction]
  )

  const getWorkOrderHistory = useCallback(
    async (workOrderId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.getWorkOrderHistory(workOrderId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  // ============================================================
  // HANDOVER
  // ============================================================

  const addItemToHandover = useCallback(
    (payload: AddItemToHandoverPayload) => wrapAction(api.addItemToHandover)(payload),
    [wrapAction]
  )

  const addDocumentToHandover = useCallback(
    (payload: AddDocumentToHandoverPayload) => wrapAction(api.addDocumentToHandover)(payload),
    [wrapAction]
  )

  const addPredictiveToHandover = useCallback(
    (payload: AddPredictiveToHandoverPayload) => wrapAction(api.addPredictiveToHandover)(payload),
    [wrapAction]
  )

  const editHandoverSection = useCallback(
    (payload: EditHandoverSectionPayload) => wrapAction(api.editHandoverSection)(payload),
    [wrapAction]
  )

  const exportHandover = useCallback(
    async () => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.exportHandover()
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  // ============================================================
  // DOCUMENTS
  // ============================================================

  const openDocument = useCallback(
    (payload: OpenDocumentPayload) => wrapAction(api.openDocument)(payload),
    [wrapAction]
  )

  const getFullDocument = useCallback(
    async (documentId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.getFullDocument(documentId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  // ============================================================
  // FAULTS
  // ============================================================

  const diagnoseFault = useCallback(
    async (code: string, equipmentId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.diagnoseFault(code, equipmentId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  // ============================================================
  // INVENTORY
  // ============================================================

  const getStock = useCallback(
    async (partId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.getStock(partId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  const orderPart = useCallback(
    (payload: OrderPartPayload) => wrapAction(api.orderPart)(payload),
    [wrapAction]
  )

  // ============================================================
  // PREDICTIVE
  // ============================================================

  const getPredictiveState = useCallback(
    async (equipmentId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.getPredictiveState(equipmentId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  const getPredictiveInsight = useCallback(
    async (insightId: string) => {
      setState({ isLoading: true, error: null })
      try {
        const result = await api.getPredictiveInsight(insightId)
        setState({ isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Action failed'
        setState({ isLoading: false, error: errorMessage })
        return null
      }
    },
    []
  )

  // ============================================================
  // GENERIC ACTION EXECUTOR
  // ============================================================

  /**
   * Execute any micro-action through the action router.
   * This is the primary way frontend executes actions from search results.
   */
  const executeAction = useCallback(
    (payload: ExecuteActionPayload) => wrapAction(api.executeAction)(payload),
    [wrapAction]
  )

  return {
    // State
    isLoading: state.isLoading,
    error: state.error,

    // Notes
    createNote,

    // Work Orders
    createWorkOrder,
    addNoteToWorkOrder,
    closeWorkOrder,
    getWorkOrderHistory,

    // Handover
    addItemToHandover,
    addDocumentToHandover,
    addPredictiveToHandover,
    editHandoverSection,
    exportHandover,

    // Documents
    openDocument,
    getFullDocument,

    // Faults
    diagnoseFault,

    // Inventory
    getStock,
    orderPart,

    // Predictive
    getPredictiveState,
    getPredictiveInsight,

    // Generic
    executeAction
  }
}
