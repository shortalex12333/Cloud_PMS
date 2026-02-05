/**
 * Handover Export API Client
 *
 * Resolves link tokens from handover export PDFs/HTMLs.
 * Single-surface architecture: /open?t=<token> -> resolve -> focus entity
 */

import { supabase } from './supabaseClient';

// API base URL - handover export service on Render
const HANDOVER_EXPORT_API_BASE = process.env.NEXT_PUBLIC_HANDOVER_EXPORT_API_BASE || 'https://handover-export.onrender.com';

/**
 * Focus descriptor returned from token resolution
 */
export interface FocusDescriptor {
  type: string;  // work_order, fault, equipment, part, warranty, document, email
  id: string;
  title?: string;
}

/**
 * Response from POST /api/v1/open/resolve
 */
export interface ResolveResponse {
  focus: FocusDescriptor;
  yacht_id: string;
  scope: string;
  version: number;
}

/**
 * Error class for resolve failures
 */
export class ResolveError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ResolveError';
  }
}

/**
 * Get the current user's JWT token
 */
async function getUserJwt(): Promise<string> {
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    throw new ResolveError('Authentication required', 401, 'Please log in to access this link');
  }

  return session.access_token;
}

/**
 * Resolve a link token to a focus descriptor
 *
 * @param token - The link token from /open?t=<token>
 * @returns ResolveResponse with focus descriptor
 * @throws ResolveError on failure
 */
export async function resolveOpenToken(token: string): Promise<ResolveResponse> {
  const jwt = await getUserJwt();

  const response = await fetch(`${HANDOVER_EXPORT_API_BASE}/api/v1/open/resolve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwt}`,
    },
    body: JSON.stringify({ t: token }),
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
    } catch {
      // Ignore JSON parse errors
    }

    // Map status codes to user-friendly messages
    const messages: Record<number, string> = {
      401: 'This link has expired or requires authentication',
      403: 'You do not have access to this item',
      404: 'The linked item could not be found',
      429: 'Too many requests. Please try again later',
    };

    throw new ResolveError(
      messages[response.status] || 'Unable to open this link',
      response.status,
      detail
    );
  }

  return response.json();
}

/**
 * Check if handover export service is available
 */
export async function checkServiceHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${HANDOVER_EXPORT_API_BASE}/health`, {
      method: 'GET',
    });
    return response.ok;
  } catch {
    return false;
  }
}
