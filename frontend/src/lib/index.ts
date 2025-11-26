/**
 * CelesteOS Frontend Library
 *
 * Centralized exports for all library modules.
 */

// Supabase client
export { supabase } from './supabase-client'

// Auth helpers
export {
  ensureFreshToken,
  getCurrentSession,
  getAuthContext,
  calculateYachtSignature,
  isAuthenticated,
  hasYachtAssigned,
  signOut,
  setUserYachtId
} from './auth-helpers'
export type { SessionInfo, AuthContext } from './auth-helpers'

// API client
export { api, default as apiClient } from './api-client'
export type {
  // Search
  SearchFilters,
  SearchPayload,
  SearchContext,
  SearchAction,
  SearchResult,
  SearchResponse,

  // Notes
  CreateNotePayload,
  CreateNoteResponse,

  // Work Orders
  WorkOrderPriority,
  CreateWorkOrderPayload,
  CreateWorkOrderResponse,
  AddNoteToWorkOrderPayload,
  AddNoteToWorkOrderResponse,
  CloseWorkOrderPayload,
  CloseWorkOrderResponse,
  WorkOrderHistoryResponse,

  // Handover
  AddItemToHandoverPayload,
  AddItemToHandoverResponse,
  AddDocumentToHandoverPayload,
  AddDocumentToHandoverResponse,
  AddPredictiveToHandoverPayload,
  AddPredictiveToHandoverResponse,
  EditHandoverSectionPayload,
  EditHandoverSectionResponse,
  ExportHandoverResponse,

  // Documents
  OpenDocumentPayload,
  OpenDocumentResponse,
  FullDocumentResponse,

  // Faults
  DiagnoseFaultResponse,

  // Inventory
  StockResponse,
  OrderPartPayload,
  OrderPartResponse,

  // Predictive
  PredictiveStateResponse,
  PredictiveInsightResponse,

  // Actions
  ExecuteActionPayload,
  ExecuteActionResponse,

  // Health
  HealthResponse,

  // Errors
  ApiError
} from './api-client'
