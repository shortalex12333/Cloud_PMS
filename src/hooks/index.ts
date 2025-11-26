/**
 * CelesteOS Frontend Hooks
 *
 * All hooks use the centralized API client with:
 * - Base URL: https://api.celeste7.ai/webhook/
 * - Automatic JWT token refresh via ensureFreshToken()
 * - No double slashes in URLs
 */

export { useSearch } from './useSearch'
export type {
  SearchFilters,
  SearchResponse,
  SearchResult,
  SearchAction,
  SearchResultType,
  SearchState
} from './useSearch'

export { useActions } from './useActions'
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
} from './useActions'
