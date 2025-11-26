import { ensureFreshToken, getCurrentSession } from './auth-helpers'

/**
 * CelesteOS API Client
 *
 * Base URL: https://api.celeste7.ai/webhook
 * All endpoints use fresh JWT tokens via ensureFreshToken()
 */

// Base URL - no trailing slash to prevent double slashes
const API_BASE_URL = 'https://api.celeste7.ai/webhook'

/**
 * Build full URL from endpoint path
 * Ensures no double slashes
 */
function buildUrl(endpoint: string): string {
  // Remove leading slash if present to prevent double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  return `${API_BASE_URL}/${cleanEndpoint}`
}

/**
 * Standard error response from API
 */
export interface ApiError {
  status: 'error'
  error_code: string
  message: string
}

/**
 * Make authenticated GET request
 */
async function apiGet<T>(endpoint: string, params?: Record<string, string>): Promise<T> {
  const token = await ensureFreshToken()

  let url = buildUrl(endpoint)
  if (params) {
    const searchParams = new URLSearchParams(params)
    url = `${url}?${searchParams.toString()}`
  }

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    const error = await response.json() as ApiError
    throw new Error(error.message || `API error: ${response.status}`)
  }

  return response.json()
}

/**
 * Make authenticated POST request
 */
async function apiPost<T>(endpoint: string, payload: Record<string, unknown>): Promise<T> {
  const token = await ensureFreshToken()
  const session = await getCurrentSession()

  // Auto-inject yacht_id if not present
  const body = {
    yacht_id: session.yachtId,
    ...payload
  }

  const response = await fetch(buildUrl(endpoint), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })

  if (!response.ok) {
    const error = await response.json() as ApiError
    throw new Error(error.message || `API error: ${response.status}`)
  }

  return response.json()
}

// ============================================================
// SEARCH API
// ============================================================

export interface SearchFilters {
  equipment_id?: string | null
  document_type?: string | null
}

export interface SearchContext {
  client_ts: number
  stream_id: string
  session_id: string
  source: 'web'
  client_version: string
  locale: string
  timezone: string
  platform: 'browser'
}

export interface SearchPayload {
  query: string
  query_type: 'free-text'
  auth: {
    user_id: string
    yacht_id: string | null
    yacht_signature: null
  }
  context: SearchContext
  filters?: SearchFilters
  stream: boolean
}

export interface SearchAction {
  label: string
  action: string
  equipment_id?: string
  context?: Record<string, unknown>
}

export interface SearchResult {
  type: 'document_chunk' | 'fault' | 'work_order' | 'part' | 'predictive' | 'history_event'
  document_id?: string
  work_order_id?: string
  chunk_index?: number
  score: number
  text_preview?: string
  summary?: string
  title?: string
  actions?: string[]
}

export interface SearchResponse {
  query_id: string
  intent: string
  entities: {
    equipment_id?: string
    fault_code?: string
    part_number?: string
  }
  results: SearchResult[]
  actions: SearchAction[]
}

/**
 * POST /v1/search
 * Universal search endpoint
 */
export async function search(query: string, filters?: SearchFilters): Promise<SearchResponse> {
  const token = await ensureFreshToken()
  const session = await getCurrentSession()

  const payload: SearchPayload = {
    query,
    query_type: 'free-text',
    auth: {
      user_id: session.userId,
      yacht_id: session.yachtId,
      yacht_signature: null
    },
    context: {
      client_ts: Math.floor(Date.now() / 1000),
      stream_id: crypto.randomUUID(),
      session_id: crypto.randomUUID(),
      source: 'web',
      client_version: '1.0.0',
      locale: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      platform: 'browser'
    },
    filters: filters || undefined,
    stream: true
  }

  const response = await fetch(buildUrl('v1/search'), {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Search failed: ${response.status} - ${errorText}`)
  }

  return response.json()
}

// ============================================================
// NOTES API
// ============================================================

export interface CreateNotePayload {
  equipment_id: string
  note_text: string
}

export interface CreateNoteResponse {
  note_id: string
}

/**
 * POST /v1/notes/create
 * Create a note linked to equipment
 */
export async function createNote(payload: CreateNotePayload): Promise<CreateNoteResponse> {
  return apiPost<CreateNoteResponse>('v1/notes/create', payload)
}

// ============================================================
// WORK ORDERS API
// ============================================================

export type WorkOrderPriority = 'low' | 'medium' | 'high' | 'critical'

export interface CreateWorkOrderPayload {
  equipment_id: string
  title: string
  description: string
  priority: WorkOrderPriority
}

export interface CreateWorkOrderResponse {
  work_order_id: string
}

/**
 * POST /v1/work-orders/create
 * Create a new work order
 */
export async function createWorkOrder(payload: CreateWorkOrderPayload): Promise<CreateWorkOrderResponse> {
  return apiPost<CreateWorkOrderResponse>('v1/work-orders/create', payload)
}

export interface AddNoteToWorkOrderPayload {
  work_order_id: string
  note_text: string
}

export interface AddNoteToWorkOrderResponse {
  note_id: string
}

/**
 * POST /v1/work-orders/add-note
 * Add a note to an existing work order
 */
export async function addNoteToWorkOrder(payload: AddNoteToWorkOrderPayload): Promise<AddNoteToWorkOrderResponse> {
  return apiPost<AddNoteToWorkOrderResponse>('v1/work-orders/add-note', payload)
}

export interface CloseWorkOrderPayload {
  work_order_id: string
}

export interface CloseWorkOrderResponse {
  status: 'closed'
}

/**
 * POST /v1/work-orders/close
 * Close a work order
 */
export async function closeWorkOrder(payload: CloseWorkOrderPayload): Promise<CloseWorkOrderResponse> {
  return apiPost<CloseWorkOrderResponse>('v1/work-orders/close', payload)
}

export interface WorkOrderHistoryResponse {
  work_order_id: string
  history: unknown[]
}

/**
 * GET /v1/work-orders/history
 * Get work order history
 */
export async function getWorkOrderHistory(workOrderId: string): Promise<WorkOrderHistoryResponse> {
  return apiGet<WorkOrderHistoryResponse>('v1/work-orders/history', { work_order_id: workOrderId })
}

// ============================================================
// HANDOVER API
// ============================================================

export interface AddItemToHandoverPayload {
  equipment_id: string
  summary_text: string
}

export interface AddItemToHandoverResponse {
  handover_item_id: string
}

/**
 * POST /v1/handover/add-item
 * Add equipment item to handover
 */
export async function addItemToHandover(payload: AddItemToHandoverPayload): Promise<AddItemToHandoverResponse> {
  return apiPost<AddItemToHandoverResponse>('v1/handover/add-item', payload)
}

export interface AddDocumentToHandoverPayload {
  document_id: string
  context?: string
}

export interface AddDocumentToHandoverResponse {
  handover_item_id: string
}

/**
 * POST /v1/handover/add-document
 * Add document to handover
 */
export async function addDocumentToHandover(payload: AddDocumentToHandoverPayload): Promise<AddDocumentToHandoverResponse> {
  return apiPost<AddDocumentToHandoverResponse>('v1/handover/add-document', payload)
}

export interface AddPredictiveToHandoverPayload {
  equipment_id: string
  insight_id: string
  summary: string
}

export interface AddPredictiveToHandoverResponse {
  handover_item_id: string
}

/**
 * POST /v1/handover/add-predictive
 * Add predictive insight to handover
 */
export async function addPredictiveToHandover(payload: AddPredictiveToHandoverPayload): Promise<AddPredictiveToHandoverResponse> {
  return apiPost<AddPredictiveToHandoverResponse>('v1/handover/add-predictive', payload)
}

export interface EditHandoverSectionPayload {
  handover_id: string
  section_name: string
  new_text: string
}

export interface EditHandoverSectionResponse {
  status: 'updated'
}

/**
 * POST /v1/handover/edit-section
 * Edit a section of the handover
 */
export async function editHandoverSection(payload: EditHandoverSectionPayload): Promise<EditHandoverSectionResponse> {
  return apiPost<EditHandoverSectionResponse>('v1/handover/edit-section', payload)
}

export interface ExportHandoverResponse {
  download_url: string
}

/**
 * POST /v1/handover/export
 * Export handover as PDF
 */
export async function exportHandover(): Promise<ExportHandoverResponse> {
  return apiPost<ExportHandoverResponse>('v1/handover/export', {})
}

// ============================================================
// DOCUMENTS API
// ============================================================

export interface OpenDocumentPayload {
  storage_path: string
}

export interface OpenDocumentResponse {
  url: string
}

/**
 * POST /v1/documents/open
 * Get signed URL to open a document
 */
export async function openDocument(payload: OpenDocumentPayload): Promise<OpenDocumentResponse> {
  return apiPost<OpenDocumentResponse>('v1/documents/open', payload)
}

export interface FullDocumentResponse {
  document_id: string
  url: string
}

/**
 * GET /v1/documents/full
 * Get full document with signed URL
 */
export async function getFullDocument(documentId: string): Promise<FullDocumentResponse> {
  return apiGet<FullDocumentResponse>('v1/documents/full', { document_id: documentId })
}

// ============================================================
// FAULTS API
// ============================================================

export interface DiagnoseFaultResponse {
  code: string
  equipment_id: string
  likely_causes: string[]
  related_parts: string[]
  documents: string[]
}

/**
 * GET /v1/faults/diagnose
 * Diagnose a fault code
 */
export async function diagnoseFault(code: string, equipmentId: string): Promise<DiagnoseFaultResponse> {
  return apiGet<DiagnoseFaultResponse>('v1/faults/diagnose', {
    code,
    equipment_id: equipmentId
  })
}

// ============================================================
// INVENTORY API
// ============================================================

export interface StockResponse {
  part_id: string
  current_qty: number
  min_qty: number
}

/**
 * GET /v1/inventory/stock
 * Get stock level for a part
 */
export async function getStock(partId: string): Promise<StockResponse> {
  return apiGet<StockResponse>('v1/inventory/stock', { part_id: partId })
}

export interface OrderPartPayload {
  part_id: string
  qty: number
}

export interface OrderPartResponse {
  purchase_order_id: string
}

/**
 * POST /v1/inventory/order-part
 * Order a part
 */
export async function orderPart(payload: OrderPartPayload): Promise<OrderPartResponse> {
  return apiPost<OrderPartResponse>('v1/inventory/order-part', payload)
}

// ============================================================
// PREDICTIVE API
// ============================================================

export interface PredictiveStateResponse {
  risk_score: number
  trend: 'up' | 'down' | 'stable'
  signals: Record<string, unknown>
}

/**
 * GET /v1/predictive/state
 * Get predictive state for equipment
 */
export async function getPredictiveState(equipmentId: string): Promise<PredictiveStateResponse> {
  return apiGet<PredictiveStateResponse>('v1/predictive/state', { equipment_id: equipmentId })
}

export interface PredictiveInsightResponse {
  id: string
  equipment_id: string
  risk_score: number
  summary: string
}

/**
 * GET /v1/predictive/insight
 * Get predictive insight details
 */
export async function getPredictiveInsight(insightId: string): Promise<PredictiveInsightResponse> {
  return apiGet<PredictiveInsightResponse>('v1/predictive/insight', { id: insightId })
}

// ============================================================
// ACTION ROUTER API
// ============================================================

export interface ExecuteActionPayload {
  action: string
  context: Record<string, unknown>
  payload: Record<string, unknown>
}

export interface ExecuteActionResponse {
  status: 'success' | 'error'
  result?: unknown
  error_code?: string
  message?: string
}

/**
 * POST /v1/actions/execute
 * Execute a micro-action through the action router
 * This is the ONLY endpoint the frontend calls for mutations
 */
export async function executeAction(payload: ExecuteActionPayload): Promise<ExecuteActionResponse> {
  return apiPost<ExecuteActionResponse>('v1/actions/execute', payload)
}

// ============================================================
// HEALTH API
// ============================================================

export interface HealthResponse {
  status: 'ok'
  uptime: number
  load: Record<string, unknown>
}

/**
 * GET /v1/health
 * Check API health
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(buildUrl('v1/health'), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }

  return response.json()
}

// ============================================================
// EXPORT ALL ENDPOINTS AS OBJECT
// ============================================================

export const api = {
  // Search
  search,

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

  // Actions
  executeAction,

  // Health
  getHealth
}

export default api
