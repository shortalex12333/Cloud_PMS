/**
 * CelesteOS Search API - Payload Validators
 *
 * Validates incoming requests against Option A (Minimal) contract
 */

import type {
  CelesteHeaders,
  SearchFilters,
  SearchMode,
  DocumentType,
} from './types';

// ============================================
// VALIDATION RESULT TYPES
// ============================================

export interface ValidationError {
  field: string;
  message: string;
  code: 'MISSING' | 'INVALID' | 'FORBIDDEN' | 'SECURITY_VIOLATION';
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

// ============================================
// CONSTANTS
// ============================================

const VALID_SEARCH_MODES: SearchMode[] = ['auto', 'standard', 'deep'];

const VALID_DOCUMENT_TYPES: DocumentType[] = [
  'manual',
  'drawing',
  'handover',
  'invoice',
  'email',
  'note',
  'work_order',
];

/**
 * Fields that MUST NOT appear in request body
 */
const FORBIDDEN_BODY_FIELDS = [
  'user_id',
  'yacht_id',
  'jwt',
  'token',
  'authorization',
  'access_token',
  'refresh_token',
] as const;

/**
 * Patterns that indicate env var leakage
 */
const FORBIDDEN_PATTERNS = [
  /^NEXT_PUBLIC_/,
  /^SUPABASE_/,
  /^API_KEY/,
  /^SECRET/,
] as const;

// ============================================
// HEADER VALIDATORS
// ============================================

/**
 * Validates the Authorization header
 */
export function validateAuthorizationHeader(
  header: string | undefined
): ValidationError | null {
  if (!header) {
    return {
      field: 'Authorization',
      message: 'Authorization header is required',
      code: 'MISSING',
    };
  }

  if (!header.startsWith('Bearer ')) {
    return {
      field: 'Authorization',
      message: 'Authorization header must start with "Bearer "',
      code: 'INVALID',
    };
  }

  const token = header.slice(7);
  if (!token || token.length < 10) {
    return {
      field: 'Authorization',
      message: 'Invalid JWT token format',
      code: 'INVALID',
    };
  }

  // Basic JWT structure check (3 parts separated by dots)
  const parts = token.split('.');
  if (parts.length !== 3) {
    return {
      field: 'Authorization',
      message: 'JWT must have 3 parts (header.payload.signature)',
      code: 'INVALID',
    };
  }

  return null;
}

/**
 * Validates the X-Yacht-Signature header
 */
export function validateYachtSignatureHeader(
  header: string | undefined
): ValidationError | null {
  if (!header) {
    return {
      field: 'X-Yacht-Signature',
      message: 'X-Yacht-Signature header is required for tenant isolation',
      code: 'MISSING',
    };
  }

  // SHA256 hash should be 64 hex characters
  if (!/^[a-f0-9]{64}$/i.test(header)) {
    return {
      field: 'X-Yacht-Signature',
      message: 'X-Yacht-Signature must be a valid SHA256 hash (64 hex chars)',
      code: 'INVALID',
    };
  }

  return null;
}

/**
 * Validates Content-Type header
 */
export function validateContentTypeHeader(
  header: string | undefined
): ValidationError | null {
  if (!header) {
    return {
      field: 'Content-Type',
      message: 'Content-Type header is required',
      code: 'MISSING',
    };
  }

  if (!header.includes('application/json')) {
    return {
      field: 'Content-Type',
      message: 'Content-Type must be application/json',
      code: 'INVALID',
    };
  }

  return null;
}

/**
 * Validates all required headers
 */
export function validateHeaders(headers: Partial<CelesteHeaders>): ValidationResult {
  const errors: ValidationError[] = [];

  const authError = validateAuthorizationHeader(headers.authorization);
  if (authError) errors.push(authError);

  const sigError = validateYachtSignatureHeader(headers['x-yacht-signature']);
  if (sigError) errors.push(sigError);

  const ctError = validateContentTypeHeader(headers['content-type']);
  if (ctError) errors.push(ctError);

  return {
    valid: errors.length === 0,
    errors,
  };
}

// ============================================
// BODY VALIDATORS
// ============================================

/**
 * Checks for forbidden fields in request body
 */
export function checkForbiddenFields(body: Record<string, unknown>): ValidationError[] {
  const errors: ValidationError[] = [];

  // Check explicit forbidden fields
  for (const field of FORBIDDEN_BODY_FIELDS) {
    if (field in body) {
      errors.push({
        field,
        message: `"${field}" must NOT be in request body. Backend extracts from JWT.`,
        code: 'FORBIDDEN',
      });
    }
  }

  // Check for env var patterns
  for (const key of Object.keys(body)) {
    for (const pattern of FORBIDDEN_PATTERNS) {
      if (pattern.test(key)) {
        errors.push({
          field: key,
          message: `Environment variable "${key}" must NOT be sent to backend`,
          code: 'SECURITY_VIOLATION',
        });
      }
    }
  }

  return errors;
}

/**
 * Validates the query field
 */
export function validateQuery(query: unknown): ValidationError | null {
  if (query === undefined || query === null) {
    return {
      field: 'query',
      message: 'query field is required',
      code: 'MISSING',
    };
  }

  if (typeof query !== 'string') {
    return {
      field: 'query',
      message: 'query must be a string',
      code: 'INVALID',
    };
  }

  if (query.trim().length === 0) {
    return {
      field: 'query',
      message: 'query cannot be empty',
      code: 'INVALID',
    };
  }

  if (query.length > 2000) {
    return {
      field: 'query',
      message: 'query must not exceed 2000 characters',
      code: 'INVALID',
    };
  }

  return null;
}

/**
 * Validates the mode field (optional)
 */
export function validateMode(mode: unknown): ValidationError | null {
  if (mode === undefined) {
    return null; // Optional field
  }

  if (typeof mode !== 'string') {
    return {
      field: 'mode',
      message: 'mode must be a string',
      code: 'INVALID',
    };
  }

  if (!VALID_SEARCH_MODES.includes(mode as SearchMode)) {
    return {
      field: 'mode',
      message: `mode must be one of: ${VALID_SEARCH_MODES.join(', ')}`,
      code: 'INVALID',
    };
  }

  return null;
}

/**
 * Validates the filters object (optional)
 */
export function validateFilters(filters: unknown): ValidationError[] {
  const errors: ValidationError[] = [];

  if (filters === undefined) {
    return errors; // Optional field
  }

  if (typeof filters !== 'object' || filters === null) {
    errors.push({
      field: 'filters',
      message: 'filters must be an object',
      code: 'INVALID',
    });
    return errors;
  }

  const f = filters as Partial<SearchFilters>;

  // Validate equipment_id if present
  if (f.equipment_id !== undefined) {
    if (typeof f.equipment_id !== 'string') {
      errors.push({
        field: 'filters.equipment_id',
        message: 'equipment_id must be a string (UUID)',
        code: 'INVALID',
      });
    } else if (!/^[0-9a-f-]{36}$/i.test(f.equipment_id)) {
      errors.push({
        field: 'filters.equipment_id',
        message: 'equipment_id must be a valid UUID',
        code: 'INVALID',
      });
    }
  }

  // Validate document_type if present
  if (f.document_type !== undefined) {
    if (!VALID_DOCUMENT_TYPES.includes(f.document_type as DocumentType)) {
      errors.push({
        field: 'filters.document_type',
        message: `document_type must be one of: ${VALID_DOCUMENT_TYPES.join(', ')}`,
        code: 'INVALID',
      });
    }
  }

  return errors;
}

/**
 * Validates the complete search request body
 */
export function validateSearchRequestBody(
  body: unknown
): ValidationResult {
  const errors: ValidationError[] = [];

  if (typeof body !== 'object' || body === null) {
    return {
      valid: false,
      errors: [
        {
          field: 'body',
          message: 'Request body must be a JSON object',
          code: 'INVALID',
        },
      ],
    };
  }

  const b = body as Record<string, unknown>;

  // Check for forbidden fields first (security)
  errors.push(...checkForbiddenFields(b));

  // Validate required fields
  const queryError = validateQuery(b.query);
  if (queryError) errors.push(queryError);

  // Validate optional fields
  const modeError = validateMode(b.mode);
  if (modeError) errors.push(modeError);

  errors.push(...validateFilters(b.filters));

  return {
    valid: errors.length === 0,
    errors,
  };
}

// ============================================
// FULL REQUEST VALIDATOR
// ============================================

export interface FullRequestValidationResult extends ValidationResult {
  headerErrors: ValidationError[];
  bodyErrors: ValidationError[];
}

/**
 * Validates a complete search request (headers + body)
 */
export function validateSearchRequest(
  headers: Partial<CelesteHeaders>,
  body: unknown
): FullRequestValidationResult {
  const headerResult = validateHeaders(headers);
  const bodyResult = validateSearchRequestBody(body);

  return {
    valid: headerResult.valid && bodyResult.valid,
    errors: [...headerResult.errors, ...bodyResult.errors],
    headerErrors: headerResult.errors,
    bodyErrors: bodyResult.errors,
  };
}
