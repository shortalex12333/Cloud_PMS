/**
 * Action Client for CelesteOS Action Router
 *
 * Connects UI action buttons to backend Action Router service.
 * All user-initiated mutations go through POST /v1/actions/execute
 */

import { useState } from 'react';
import { supabase } from './supabaseClient';

// Action Router endpoints
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const ACTION_ROUTER_URL = `${API_BASE_URL}/v1/actions/execute`;
const ACTION_LIST_URL = `${API_BASE_URL}/v1/actions/list`;

/**
 * Action execution result
 */
export interface ActionResult {
  status: 'success' | 'error';
  action: string;
  result?: Record<string, any>;
  error_code?: string;
  message?: string;
}

/**
 * Action suggestion from backend
 */
export interface ActionSuggestion {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'SIGNED';
  allowed_roles: string[];
  required_fields: string[];
  domain: string | null;
  match_score: number;
  storage_options?: {
    bucket: string;
    path_preview: string;
    writable_prefixes: string[];
    confirmation_required: boolean;
  };
}

/**
 * Action suggestions response from backend
 */
export interface ActionSuggestionsResponse {
  query: string | null;
  actions: ActionSuggestion[];
  total_count: number;
  role: string;
}

/**
 * Action execution error
 */
class ActionExecutionError extends Error {
  constructor(
    public action: string,
    public error_code: string,
    message: string,
    public status_code?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ActionExecutionError';
  }
}

/**
 * Execute an action through the Action Router
 *
 * @param action - Action ID (e.g., 'add_note', 'create_work_order')
 * @param context - Action context (yacht_id, equipment_id, etc.)
 * @param payload - Action payload (user inputs)
 * @returns Action result
 *
 * @example
 * ```typescript
 * const result = await executeAction('add_note', {
 *   yacht_id: 'uuid',
 *   equipment_id: 'uuid'
 * }, {
 *   note_text: 'Found leak in coolant system'
 * });
 * ```
 */
export async function executeAction(
  action: string,
  context: Record<string, any>,
  payload: Record<string, any> = {}
): Promise<ActionResult> {
  // Get current Supabase session for JWT
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new ActionExecutionError(
      action,
      'unauthenticated',
      'Authentication required to perform actions',
      401
    );
  }

  // Prepare request
  const request_body = {
    action,
    context,
    payload,
  };

  console.log('[actionClient] Executing action:', {
    action,
    context,
    payload,
    user_id: session.user.id,
  });

  try {
    const response = await fetch(ACTION_ROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(request_body),
    });

    // Parse response
    const result: ActionResult = await response.json();

    console.log('[actionClient] Action response:', {
      status: response.status,
      action,
      result_status: result.status,
    });

    // Handle errors
    if (!response.ok || result.status === 'error') {
      throw new ActionExecutionError(
        action,
        result.error_code || 'unknown_error',
        result.message || `Action '${action}' failed`,
        response.status,
        result
      );
    }

    return result;
  } catch (error) {
    // Re-throw ActionExecutionError as-is
    if (error instanceof ActionExecutionError) {
      throw error;
    }

    // Network or parsing errors
    console.error('[actionClient] Action execution failed:', error);
    throw new ActionExecutionError(
      action,
      'network_error',
      error instanceof Error ? error.message : 'Network error',
      undefined,
      error
    );
  }
}

/**
 * Action handlers by action ID
 * Maps action IDs to their parameter requirements
 */
const ACTION_CONFIGS = {
  // Notes
  add_note: {
    required_context: ['yacht_id', 'equipment_id'],
    required_payload: ['note_text'],
  },
  add_note_to_work_order: {
    required_context: ['yacht_id', 'work_order_id'],
    required_payload: ['note_text'],
  },

  // Work Orders
  create_work_order: {
    required_context: ['yacht_id', 'equipment_id'],
    required_payload: ['title', 'priority'],
  },
  create_work_order_fault: {
    required_context: ['yacht_id', 'fault_id'],
    required_payload: ['title', 'priority'],
  },
  close_work_order: {
    required_context: ['yacht_id', 'work_order_id'],
    required_payload: [],
  },

  // Handovers
  add_to_handover: {
    required_context: ['yacht_id', 'handover_id', 'equipment_id'],
    required_payload: [],
  },
  add_document_to_handover: {
    required_context: ['yacht_id', 'handover_id', 'document_id'],
    required_payload: [],
  },
  add_part_to_handover: {
    required_context: ['yacht_id', 'handover_id', 'part_id'],
    required_payload: [],
  },
  add_predictive_to_handover: {
    required_context: ['yacht_id', 'handover_id', 'predictive_id'],
    required_payload: [],
  },
  edit_handover_section: {
    required_context: ['yacht_id', 'handover_id'],
    required_payload: ['section_name', 'new_text'],
  },
  export_handover: {
    required_context: ['yacht_id', 'handover_id'],
    required_payload: ['format'],
  },

  // Documents
  open_document: {
    required_context: [],
    required_payload: ['storage_path'],
  },

  // Inventory
  order_part: {
    required_context: ['yacht_id', 'part_id'],
    required_payload: ['quantity'],
  },
} as const;

/**
 * Get action suggestions from backend
 *
 * @param query - Search query (e.g., 'add certificate')
 * @param domain - Domain filter (e.g., 'certificates')
 * @returns Promise with action suggestions
 *
 * @example
 * ```typescript
 * const { actions } = await getActionSuggestions('add certificate', 'certificates');
 * // actions: [{ action_id: 'create_vessel_certificate', label: 'Add Vessel Certificate', ... }]
 * ```
 */
export async function getActionSuggestions(
  query: string,
  domain: string = 'certificates'
): Promise<ActionSuggestionsResponse> {
  // Get current Supabase session for JWT
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new ActionExecutionError(
      'list_actions',
      'unauthenticated',
      'Authentication required to fetch action suggestions',
      401
    );
  }

  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (domain) params.set('domain', domain);

  const url = `${ACTION_LIST_URL}?${params.toString()}`;

  console.log('[actionClient] Fetching action suggestions:', { query, domain, url });

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${session.access_token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ActionExecutionError(
        'list_actions',
        errorData.error_code || 'fetch_error',
        errorData.message || `Failed to fetch suggestions: ${response.status}`,
        response.status
      );
    }

    const data: ActionSuggestionsResponse = await response.json();

    console.log('[actionClient] Action suggestions received:', {
      query,
      count: data.total_count,
      role: data.role,
    });

    return data;
  } catch (error) {
    if (error instanceof ActionExecutionError) {
      throw error;
    }

    console.error('[actionClient] Failed to fetch action suggestions:', error);
    throw new ActionExecutionError(
      'list_actions',
      'network_error',
      error instanceof Error ? error.message : 'Network error',
      undefined,
      error
    );
  }
}

/**
 * React hook for executing actions with loading/error states
 *
 * @example
 * ```typescript
 * const { execute, loading, error, result } = useAction();
 *
 * const handleAddNote = async () => {
 *   await execute('add_note', {
 *     yacht_id: yacht.id,
 *     equipment_id: equipment.id
 *   }, {
 *     note_text: inputValue
 *   });
 * };
 * ```
 */
function useAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ActionExecutionError | null>(null);
  const [result, setResult] = useState<ActionResult | null>(null);

  const execute = async (
    action: string,
    context: Record<string, any>,
    payload: Record<string, any> = {}
  ) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await executeAction(action, context, payload);
      setResult(res);
      return res;
    } catch (err) {
      const actionError = err instanceof ActionExecutionError
        ? err
        : new ActionExecutionError(action, 'unknown_error', 'Unknown error occurred');
      setError(actionError);
      throw actionError;
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setLoading(false);
    setError(null);
    setResult(null);
  };

  return {
    execute,
    loading,
    error,
    result,
    reset,
  };
}

// ============================================================================
// Generic Prefill Types
// ============================================================================

/**
 * Dropdown option for disambiguation
 */
export interface DropdownOption {
  value: string;
  label: string;
}

/**
 * Field warning from prefill engine
 */
export interface PrefillWarning {
  field: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

/**
 * Generic prefill response from /v1/actions/prefill/{action_id}
 *
 * Includes field-level confidence scoring for low-confidence highlighting.
 * When backend returns field_confidence, the UI will show visual indicators:
 * - confidence >= 0.8: Normal field (no indicator)
 * - confidence 0.5-0.8: Yellow border + "Low confidence" badge
 * - confidence < 0.5: Red border + "Review required" badge
 */
export interface PrefillResponse {
  status: 'success' | 'error';
  mutation_preview: Record<string, any>;
  dropdown_options: Record<string, DropdownOption[]>;
  warnings: PrefillWarning[];
  ready_to_commit: boolean;
  error?: string;
  message?: string;
  /**
   * Field-level confidence scores (0-1) from NLP/prefill engine.
   * Used by ConfidenceField component to highlight low-confidence fields.
   * @example { "equipment_id": 0.65, "priority": 0.95 }
   */
  field_confidence?: Record<string, number>;
  /**
   * Alternative suggestions for fields with low confidence.
   * Rendered as clickable correction chips by ConfidenceField.
   * @example { "equipment_id": ["Main Engine Port", "Main Engine Starboard"] }
   */
  field_alternatives?: Record<string, string[]>;
}

/**
 * Fetch prefill data for an action modal
 *
 * Calls /v1/actions/prefill/{actionId} to get pre-filled form values
 * based on NLP entity extraction from the query text.
 *
 * @param actionId - Action ID (e.g., 'create_work_order')
 * @param queryText - Original search query text (for NLP prefill)
 * @param extractedEntities - Already extracted entities from search results
 * @returns Prefill response with mutation preview and dropdown options
 *
 * @example
 * ```typescript
 * const prefill = await fetchPrefill(
 *   'create_work_order',
 *   'fix the main engine cooling pump',
 *   { equipment_name: 'Main Engine' }
 * );
 * // prefill.mutation_preview: { title: 'Fix cooling pump', equipment_id: 'uuid', ... }
 * // prefill.dropdown_options: { equipment_id: [{ value: 'uuid', label: 'Main Engine' }] }
 * ```
 */
export async function fetchPrefill(
  actionId: string,
  queryText: string,
  extractedEntities?: Record<string, string>
): Promise<PrefillResponse> {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new ActionExecutionError(
      'prefill',
      'unauthenticated',
      'Authentication required to fetch prefill data',
      401
    );
  }

  const request_body = {
    context: {},
    payload: {
      query_text: queryText,
      extracted_entities: extractedEntities || {},
    },
  };

  console.log('[actionClient] Fetching prefill:', {
    actionId,
    queryText,
    extractedEntities,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/v1/actions/prefill/${actionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(request_body),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new ActionExecutionError(
        'prefill',
        result.code || 'prefill_error',
        result.error || result.detail || 'Failed to fetch prefill data',
        response.status,
        result
      );
    }

    console.log('[actionClient] Prefill response:', {
      actionId,
      ready_to_commit: result.ready_to_commit,
      warnings_count: result.warnings?.length || 0,
      dropdown_fields: Object.keys(result.dropdown_options || {}),
    });

    return result;
  } catch (error) {
    if (error instanceof ActionExecutionError) {
      throw error;
    }
    console.error('[actionClient] Prefill failed:', error);
    throw new ActionExecutionError(
      'prefill',
      'network_error',
      error instanceof Error ? error.message : 'Network error',
      undefined,
      error
    );
  }
}

// ============================================================================
// Prefill Integration Types (v1.3)
// ============================================================================

/**
 * Prefill field with confidence and source attribution
 */
export interface PrefillField {
  value: any;
  confidence: number;
  source: 'entity_resolver' | 'keyword_map' | 'temporal' | 'template';
}

/**
 * Ambiguity candidate for disambiguation UI
 */
export interface AmbiguityCandidate {
  id: string;
  label: string;
  confidence: number;
}

/**
 * Ambiguity requiring user selection
 */
export interface Ambiguity {
  field: string;
  candidates: AmbiguityCandidate[];
}

/**
 * Response from /v1/actions/prepare endpoint
 */
export interface PrepareResponse {
  action_id: string;
  match_score: number;
  ready_to_commit: boolean;
  prefill: Record<string, PrefillField>;
  missing_required_fields: string[];
  ambiguities: Ambiguity[];
  errors: Array<{ error_code: string; message: string; field?: string }>;
}

/**
 * Request to /v1/actions/prepare endpoint
 */
export interface PrepareRequest {
  q: string;
  domain: string;
  candidate_action_ids: string[];
  context: { yacht_id: string; user_role: string };
  hint_entities?: Record<string, any>;
  client: { timezone: string; now_iso: string };
}

/**
 * Get JWT token helper (reuse existing auth)
 */
async function getJwtToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

/**
 * Call /v1/actions/prepare endpoint to get prefill preview
 *
 * @param request - Prepare request with query, domain, candidates
 * @param signal - Optional abort signal for cancellation
 * @returns PrepareResponse with prefilled values
 */
export async function prepareAction(
  request: PrepareRequest,
  signal?: AbortSignal
): Promise<PrepareResponse> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const jwt = await getJwtToken();

  const response = await fetch(`${API_URL}/v1/actions/prepare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': jwt ? `Bearer ${jwt}` : '',
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `Prepare failed: ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Two-Phase Mutation Types
// ============================================================================

/**
 * Field metadata from generic prefill engine
 */
export interface FieldMetadata {
  source: 'user_input' | 'nlp_entity' | 'derived' | 'database';
  confidence: number;
  editable: boolean;
  required: boolean;
  label?: string;
  options?: { value: string; label: string }[];
}

/**
 * Mutation preview response from /prepare endpoint
 */
export interface MutationPreview {
  title: string;
  description?: string;
  equipment_id?: string;
  equipment_id_options?: { value: string; label: string }[];
  priority: string;
  assigned_to?: string;
  assigned_to_options?: { value: string; label: string }[];
  scheduled_date?: string;
  field_metadata: Record<string, FieldMetadata>;
}

/**
 * PrepareResponse from two-phase mutation
 */
export interface PrepareResponse {
  success: boolean;
  mutation_preview?: MutationPreview;
  error?: string;
}

/**
 * CommitResponse from two-phase mutation
 */
export interface CommitResponse {
  success: boolean;
  work_order_id?: string;
  wo_number?: string;
  error?: string;
  message?: string;
}

// ============================================================================
// Two-Phase Mutation API Client
// ============================================================================

/**
 * Phase 1: Prepare work order creation
 *
 * Calls /v1/actions/work_order/create/prepare to get mutation preview
 * with pre-filled fields based on NLP entity extraction.
 *
 * @param context - yacht_id, query_text, extracted_entities
 * @returns Mutation preview with pre-filled form fields
 */
export async function prepareWorkOrderCreate(
  context: {
    yacht_id: string;
    query_text?: string;
    extracted_entities?: string[];
  }
): Promise<PrepareResponse> {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new ActionExecutionError(
      'prepare_work_order',
      'unauthenticated',
      'Authentication required to prepare work order',
      401
    );
  }

  const request_body = {
    context,
    payload: {},
  };

  console.log('[actionClient] Preparing work order create:', {
    yacht_id: context.yacht_id,
    query_text: context.query_text,
    entities_count: context.extracted_entities?.length,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/v1/actions/work_order/create/prepare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(request_body),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new ActionExecutionError(
        'prepare_work_order',
        result.code || 'prepare_error',
        result.error || result.detail || 'Failed to prepare work order',
        response.status,
        result
      );
    }

    return result;
  } catch (error) {
    if (error instanceof ActionExecutionError) {
      throw error;
    }
    console.error('[actionClient] Prepare work order failed:', error);
    throw new ActionExecutionError(
      'prepare_work_order',
      'network_error',
      error instanceof Error ? error.message : 'Network error',
      undefined,
      error
    );
  }
}

/**
 * Phase 2: Commit work order creation
 *
 * Calls /v1/actions/work_order/create/commit with user-reviewed payload.
 *
 * @param context - yacht_id
 * @param payload - User-reviewed form values
 * @returns Created work order data
 */
export async function commitWorkOrderCreate(
  context: { yacht_id: string },
  payload: {
    title: string;
    equipment_id?: string;
    priority: string;
    assigned_to?: string;
    description?: string;
    scheduled_date?: string;
  }
): Promise<CommitResponse> {
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError || !session) {
    throw new ActionExecutionError(
      'commit_work_order',
      'unauthenticated',
      'Authentication required to create work order',
      401
    );
  }

  const request_body = {
    context,
    payload,
  };

  console.log('[actionClient] Committing work order create:', {
    yacht_id: context.yacht_id,
    title: payload.title,
    priority: payload.priority,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/v1/actions/work_order/create/commit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify(request_body),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new ActionExecutionError(
        'commit_work_order',
        result.code || 'commit_error',
        result.error || result.detail || 'Failed to create work order',
        response.status,
        result
      );
    }

    return result;
  } catch (error) {
    if (error instanceof ActionExecutionError) {
      throw error;
    }
    console.error('[actionClient] Commit work order failed:', error);
    throw new ActionExecutionError(
      'commit_work_order',
      'network_error',
      error instanceof Error ? error.message : 'Network error',
      undefined,
      error
    );
  }
}
