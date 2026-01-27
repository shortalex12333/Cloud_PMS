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
export class ActionExecutionError extends Error {
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
export const ACTION_CONFIGS = {
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
export function useAction() {
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
