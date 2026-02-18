/**
 * Handover Export API Client
 *
 * Resolves link tokens from handover export PDFs/HTMLs.
 * Single-surface architecture: /open?t=<token> -> resolve -> focus entity
 */

import { getValidJWT } from './authHelpers';

// API base URL - handover export service on Render
const HANDOVER_EXPORT_API_BASE = process.env.NEXT_PUBLIC_HANDOVER_EXPORT_API_BASE || 'https://handover-export.onrender.com';

// Entity type constants for validation
export const SUPPORTED_ENTITY_TYPES = [
  'work_order',
  'fault',
  'equipment',
  'part',
  'warranty',
  'document',
  'email',
  'certificate',
  'handover',
] as const;

export const UNSUPPORTED_ENTITY_TYPES = [
  'inventory',
  'purchase_order',
  'voyage',
  'guest',
  'crew',
] as const;

export type SupportedEntityType = typeof SUPPORTED_ENTITY_TYPES[number];
export type UnsupportedEntityType = typeof UNSUPPORTED_ENTITY_TYPES[number];

export function isSupportedEntityType(type: string): type is SupportedEntityType {
  return SUPPORTED_ENTITY_TYPES.includes(type as SupportedEntityType);
}

export function isUnsupportedEntityType(type: string): type is UnsupportedEntityType {
  return UNSUPPORTED_ENTITY_TYPES.includes(type as UnsupportedEntityType);
}

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
 * Error codes for resolve failures
 */
export type ResolveErrorCode =
  | 'TOKEN_EXPIRED'
  | 'TOKEN_INVALID'
  | 'AUTH_REQUIRED'
  | 'YACHT_MISMATCH'
  | 'ENTITY_NOT_FOUND'
  | 'UNSUPPORTED_TYPE'
  | 'UNKNOWN_TYPE'
  | 'UNKNOWN_ERROR';

/**
 * Error class for resolve failures
 */
export class ResolveError extends Error {
  constructor(
    public code: ResolveErrorCode,
    message: string,
    public status: number
  ) {
    super(message);
    this.name = 'ResolveError';
  }
}

/**
 * Map HTTP status and detail to error code
 */
function mapToErrorCode(status: number, detail: string): ResolveErrorCode {
  const detailLower = detail.toLowerCase();

  if (status === 401) {
    if (detailLower.includes('expired')) {
      return 'TOKEN_EXPIRED';
    }
    return 'AUTH_REQUIRED';
  }

  if (status === 403) {
    return 'YACHT_MISMATCH';
  }

  if (status === 404) {
    return 'ENTITY_NOT_FOUND';
  }

  if (status === 400) {
    if (detailLower.includes('not yet supported')) {
      return 'UNSUPPORTED_TYPE';
    }
    if (detailLower.includes('unknown entity type')) {
      return 'UNKNOWN_TYPE';
    }
    return 'TOKEN_INVALID';
  }

  return 'UNKNOWN_ERROR';
}

/**
 * Resolve a link token to a focus descriptor
 *
 * @param token - The link token from /open?t=<token>
 * @returns ResolveResponse with focus descriptor
 * @throws ResolveError on failure
 */
export async function resolveOpenToken(token: string): Promise<ResolveResponse> {
  // Validate token is not empty
  if (!token || token.trim() === '') {
    throw new ResolveError('TOKEN_INVALID', 'Token is required', 400);
  }

  let jwt: string;
  try {
    jwt = await getValidJWT();
  } catch {
    throw new ResolveError('AUTH_REQUIRED', 'Authentication required', 401);
  }

  let response: Response;
  try {
    response = await fetch(`${HANDOVER_EXPORT_API_BASE}/api/v1/open/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${jwt}`,
      },
      body: JSON.stringify({ t: token }),
    });
  } catch {
    throw new ResolveError('UNKNOWN_ERROR', 'Network error', 500);
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        detail = errorData.detail;
      }
    } catch {
      // Ignore JSON parse errors
    }

    const code = mapToErrorCode(response.status, detail);

    // Map status codes to user-friendly messages
    const messages: Record<ResolveErrorCode, string> = {
      'TOKEN_EXPIRED': 'This link has expired',
      'TOKEN_INVALID': detail,
      'AUTH_REQUIRED': 'Authentication required',
      'YACHT_MISMATCH': 'You do not have access to this item',
      'ENTITY_NOT_FOUND': 'The linked item could not be found',
      'UNSUPPORTED_TYPE': detail,
      'UNKNOWN_TYPE': detail,
      'UNKNOWN_ERROR': 'Unable to open this link',
    };

    throw new ResolveError(code, messages[code], response.status);
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

// ============================================================================
// PIPELINE EXPORT FUNCTIONS
// ============================================================================

export interface PipelineRunResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'complete' | 'failed';
}

export interface PipelineJobResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'complete' | 'failed';
  result_url?: string;
  error?: string;
}

/**
 * Start an export pipeline job for a handover
 */
export async function startExportJob(handoverId: string, yachtId: string): Promise<PipelineRunResponse> {
  const response = await fetch(`${HANDOVER_EXPORT_API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handover_id: handoverId, yacht_id: yachtId }),
  });
  if (!response.ok) throw new Error('Failed to start export job');
  return response.json();
}

/**
 * Check the status of a pipeline export job
 */
export async function checkJobStatus(jobId: string): Promise<PipelineJobResponse> {
  const response = await fetch(`${HANDOVER_EXPORT_API_BASE}/api/pipeline/job/${jobId}`);
  if (!response.ok) throw new Error('Failed to check job status');
  return response.json();
}

/**
 * Retrieve the HTML report for a completed pipeline job
 */
export async function getReportHtml(jobId: string): Promise<string> {
  const response = await fetch(`${HANDOVER_EXPORT_API_BASE}/api/pipeline/report/${jobId}`);
  if (!response.ok) throw new Error('Failed to get report');
  return response.text();
}
