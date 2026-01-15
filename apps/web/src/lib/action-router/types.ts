/**
 * Action Router Types
 *
 * Type definitions for the action routing system.
 */

// ============================================================================
// HANDLER TYPES
// ============================================================================

export type HandlerType = 'internal' | 'n8n';

// ============================================================================
// ACTION DEFINITION
// ============================================================================

export interface ActionDefinition {
  actionId: string;
  label: string;
  endpoint: string;
  handlerType: HandlerType;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  allowedRoles: string[];
  requiredFields: string[];
  schemaFile: string | null;
}

// ============================================================================
// REQUEST/RESPONSE TYPES
// ============================================================================

export interface ActionContext {
  yacht_id: string;
  equipment_id?: string;
  work_order_id?: string;
  fault_id?: string;
  document_id?: string;
  part_id?: string;
  handover_id?: string;
  [key: string]: string | undefined;
}

export interface ActionPayload {
  [key: string]: unknown;
}

export interface ActionRequest {
  action: string;
  context: ActionContext;
  payload: ActionPayload;
}

export type ActionStatus = 'success' | 'error';

export interface ActionResult {
  [key: string]: unknown;
}

export interface ActionResponse {
  status: ActionStatus;
  action: string;
  result?: ActionResult;
  error_code?: string;
  message?: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// VALIDATION TYPES
// ============================================================================

export interface ValidationError {
  error_code: string;
  message: string;
  field?: string;
  details?: Record<string, unknown>;
}

export interface ValidationResult {
  valid: boolean;
  error?: ValidationError;
  context?: Record<string, unknown>;
}

export interface UserContext {
  user_id: string;
  yacht_id: string;
  role: string;
  email?: string;
}

// ============================================================================
// VALIDATION ERROR CODES
// ============================================================================

export type ValidationErrorCode =
  | 'invalid_token'
  | 'token_expired'
  | 'missing_token'
  | 'action_not_found'
  | 'yacht_mismatch'
  | 'yacht_not_found'
  | 'permission_denied'
  | 'missing_field'
  | 'invalid_field'
  | 'schema_validation_error'
  | 'handler_validation_error'
  | 'handler_execution_error'
  | 'internal_server_error';

// ============================================================================
// DISPATCHER TYPES
// ============================================================================

export interface DispatchParams {
  yacht_id: string;
  user_id: string;
  role: string;
  [key: string]: unknown;
}

export interface DispatchResult {
  [key: string]: unknown;
}

// ============================================================================
// LOGGER TYPES
// ============================================================================

export interface ActionLogEntry {
  id?: string;
  yacht_id: string;
  user_id: string;
  action_id: string;
  action_label: string;
  payload: Record<string, unknown>;
  status: ActionStatus;
  result?: Record<string, unknown>;
  error_message?: string;
  duration_ms?: number;
  created_at?: string;
}

// ============================================================================
// ROUTING TYPES
// ============================================================================

export interface RouteContext {
  yachtId: string;
  userId: string;
  userRole: string;
}

export interface RouteOptions {
  skipValidation?: boolean;
  skipLogging?: boolean;
  timeout?: number;
}

// ============================================================================
// HOOK TYPES
// ============================================================================

export interface ActionState {
  isLoading: boolean;
  isSuccess: boolean;
  isError: boolean;
  error: ActionResponse | null;
  result: ActionResult | null;
}

export interface UseActionOptions {
  onSuccess?: (result: ActionResult) => void;
  onError?: (error: ActionResponse) => void;
  skipConfirmation?: boolean;
}
