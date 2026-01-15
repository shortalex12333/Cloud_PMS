/**
 * Action Router - Validators
 *
 * Validation functions for action execution:
 * - JWT validation
 * - Yacht isolation
 * - Role permissions
 * - Required fields
 * - Schema validation
 */

import type {
  ValidationResult,
  UserContext,
  ActionContext,
  ActionPayload,
} from './types';

// ============================================================================
// VALIDATION RESULT HELPERS
// ============================================================================

/**
 * Create a successful validation result
 */
export function validationSuccess(context?: Record<string, unknown>): ValidationResult {
  return {
    valid: true,
    context: context || {},
  };
}

/**
 * Create a failed validation result
 */
export function validationFailure(
  errorCode: string,
  message: string,
  field?: string,
  details?: Record<string, unknown>
): ValidationResult {
  return {
    valid: false,
    error: {
      error_code: errorCode,
      message,
      field,
      details,
    },
  };
}

// ============================================================================
// JWT VALIDATION
// ============================================================================

/**
 * Validate JWT token and extract user context
 *
 * In the browser, this uses the Supabase client session.
 * The actual JWT validation happens on the Supabase server.
 *
 * @param authorization - Authorization header value
 * @returns ValidationResult with user context if valid
 */
export function validateJWT(authorization: string | null): ValidationResult {
  // Check for missing token
  if (!authorization) {
    return validationFailure(
      'missing_token',
      'Authorization header is required'
    );
  }

  // Check for Bearer prefix
  if (!authorization.startsWith('Bearer ')) {
    return validationFailure(
      'invalid_token',
      'Authorization header must start with Bearer'
    );
  }

  const token = authorization.slice(7);

  // Check for empty token
  if (!token || token.trim() === '') {
    return validationFailure('invalid_token', 'Token is empty');
  }

  // In client-side context, we trust the Supabase session
  // Server-side validation would decode and verify the JWT here
  // For now, we return success and let Supabase RLS handle final validation

  return validationSuccess();
}

/**
 * Validate user context from Supabase session
 *
 * @param userContext - User context object
 * @returns ValidationResult
 */
export function validateUserContext(
  userContext: UserContext | null
): ValidationResult {
  if (!userContext) {
    return validationFailure(
      'invalid_token',
      'User context is required'
    );
  }

  if (!userContext.user_id) {
    return validationFailure(
      'invalid_token',
      'User ID is required in context'
    );
  }

  if (!userContext.yacht_id) {
    return validationFailure(
      'yacht_not_found',
      'Yacht ID is required in context'
    );
  }

  if (!userContext.role) {
    return validationFailure(
      'permission_denied',
      'User role is required in context'
    );
  }

  return validationSuccess({ user: userContext });
}

// ============================================================================
// YACHT ISOLATION VALIDATION
// ============================================================================

/**
 * Validate yacht isolation - ensure request yacht matches user's yacht
 *
 * @param actionContext - Context from action request
 * @param userContext - User context from JWT
 * @returns ValidationResult
 */
export function validateYachtIsolation(
  actionContext: ActionContext,
  userContext: UserContext
): ValidationResult {
  // Check yacht_id is present in request
  if (!actionContext.yacht_id) {
    return validationFailure(
      'yacht_not_found',
      'yacht_id is required in action context',
      'yacht_id'
    );
  }

  // Check yacht_id matches user's yacht
  if (actionContext.yacht_id !== userContext.yacht_id) {
    return validationFailure(
      'yacht_mismatch',
      `Access denied: Request yacht (${actionContext.yacht_id}) does not match user yacht (${userContext.yacht_id})`,
      'yacht_id'
    );
  }

  return validationSuccess();
}

// ============================================================================
// ROLE PERMISSION VALIDATION
// ============================================================================

/**
 * Validate user has permission to execute action
 *
 * @param userContext - User context from JWT
 * @param allowedRoles - List of roles allowed for this action
 * @param actionId - Action being executed (for error message)
 * @returns ValidationResult
 */
export function validateRolePermission(
  userContext: UserContext,
  allowedRoles: string[],
  actionId: string
): ValidationResult {
  const userRole = userContext.role;

  // Check if user's role is in allowed roles
  if (!allowedRoles.includes(userRole)) {
    return validationFailure(
      'permission_denied',
      `Role '${userRole}' is not allowed to execute action '${actionId}'. Required: ${allowedRoles.join(', ')}`,
      undefined,
      {
        user_role: userRole,
        allowed_roles: allowedRoles,
        action_id: actionId,
      }
    );
  }

  return validationSuccess();
}

// ============================================================================
// REQUIRED FIELDS VALIDATION
// ============================================================================

/**
 * Validate all required fields are present
 *
 * @param params - Merged context + payload
 * @param requiredFields - List of required field names
 * @param actionId - Action being executed (for error message)
 * @returns ValidationResult
 */
export function validateRequiredFields(
  params: Record<string, unknown>,
  requiredFields: string[],
  actionId: string
): ValidationResult {
  const missingFields: string[] = [];

  for (const field of requiredFields) {
    const value = params[field];

    // Check if field is missing or null/undefined
    if (value === undefined || value === null) {
      missingFields.push(field);
      continue;
    }

    // Check if string field is empty
    if (typeof value === 'string' && value.trim() === '') {
      missingFields.push(field);
    }
  }

  if (missingFields.length > 0) {
    return validationFailure(
      'missing_field',
      `Missing required field(s): ${missingFields.join(', ')}`,
      missingFields[0],
      {
        missing_fields: missingFields,
        action_id: actionId,
      }
    );
  }

  return validationSuccess();
}

// ============================================================================
// FIELD VALUE VALIDATION
// ============================================================================

/**
 * Validate field value against expected type
 *
 * @param value - Value to validate
 * @param fieldName - Name of field
 * @param expectedType - Expected type ('string', 'number', 'uuid', 'boolean')
 * @returns ValidationResult
 */
export function validateFieldType(
  value: unknown,
  fieldName: string,
  expectedType: 'string' | 'number' | 'uuid' | 'boolean' | 'array' | 'object'
): ValidationResult {
  if (value === null || value === undefined) {
    return validationSuccess(); // Null/undefined handled by required field check
  }

  switch (expectedType) {
    case 'string':
      if (typeof value !== 'string') {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be a string`,
          fieldName
        );
      }
      break;

    case 'number':
      if (typeof value !== 'number' || isNaN(value)) {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be a number`,
          fieldName
        );
      }
      break;

    case 'uuid':
      if (typeof value !== 'string') {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be a UUID string`,
          fieldName
        );
      }
      // UUID v4 regex pattern
      const uuidPattern =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
      if (!uuidPattern.test(value)) {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be a valid UUID`,
          fieldName
        );
      }
      break;

    case 'boolean':
      if (typeof value !== 'boolean') {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be a boolean`,
          fieldName
        );
      }
      break;

    case 'array':
      if (!Array.isArray(value)) {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be an array`,
          fieldName
        );
      }
      break;

    case 'object':
      if (typeof value !== 'object' || Array.isArray(value)) {
        return validationFailure(
          'invalid_field',
          `Field '${fieldName}' must be an object`,
          fieldName
        );
      }
      break;
  }

  return validationSuccess();
}

// ============================================================================
// SCHEMA VALIDATION
// ============================================================================

/**
 * Validate payload against JSON schema
 *
 * Note: Full JSON schema validation would use a library like ajv.
 * This is a simplified validator for common patterns.
 *
 * @param payload - Payload to validate
 * @param schemaFile - Schema file name (unused in simplified version)
 * @param actionId - Action being executed
 * @returns ValidationResult
 */
export function validateSchema(
  payload: ActionPayload,
  schemaFile: string | null,
  actionId: string
): ValidationResult {
  // If no schema file, skip validation
  if (!schemaFile) {
    return validationSuccess();
  }

  // Simplified schema validation
  // In production, load and validate against JSON schema file

  // Check payload is an object
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
    return validationFailure(
      'schema_validation_error',
      'Payload must be a JSON object',
      undefined,
      { action_id: actionId, schema_file: schemaFile }
    );
  }

  // Action-specific validations
  switch (actionId) {
    case 'add_note':
    case 'add_note_to_work_order':
      // Validate note_text is not too long
      if (
        typeof payload.note_text === 'string' &&
        payload.note_text.length > 10000
      ) {
        return validationFailure(
          'schema_validation_error',
          'note_text exceeds maximum length of 10000 characters',
          'note_text'
        );
      }
      break;

    case 'create_work_order':
      // Validate priority is valid
      if (
        payload.priority &&
        !['low', 'medium', 'high', 'critical'].includes(
          payload.priority as string
        )
      ) {
        return validationFailure(
          'schema_validation_error',
          'priority must be one of: low, medium, high, critical',
          'priority'
        );
      }
      break;

    case 'order_part':
      // Validate qty is positive
      if (typeof payload.qty === 'number' && payload.qty <= 0) {
        return validationFailure(
          'schema_validation_error',
          'qty must be a positive number',
          'qty'
        );
      }
      break;
  }

  return validationSuccess();
}

// ============================================================================
// COMPOSITE VALIDATION
// ============================================================================

/**
 * Run all validations for an action request
 *
 * @param actionId - Action being executed
 * @param context - Action context
 * @param payload - Action payload
 * @param userContext - User context
 * @param actionDef - Action definition
 * @returns ValidationResult
 */
export function validateActionRequest(
  actionId: string,
  context: ActionContext,
  payload: ActionPayload,
  userContext: UserContext,
  actionDef: {
    allowedRoles: string[];
    requiredFields: string[];
    schemaFile: string | null;
  }
): ValidationResult {
  // 1. Validate user context
  const userResult = validateUserContext(userContext);
  if (!userResult.valid) return userResult;

  // 2. Validate yacht isolation
  const yachtResult = validateYachtIsolation(context, userContext);
  if (!yachtResult.valid) return yachtResult;

  // 3. Validate role permissions
  const roleResult = validateRolePermission(
    userContext,
    actionDef.allowedRoles,
    actionId
  );
  if (!roleResult.valid) return roleResult;

  // 4. Merge params
  const params = { ...context, ...payload, user_id: userContext.user_id, role: userContext.role };

  // 5. Validate required fields
  const fieldResult = validateRequiredFields(
    params,
    actionDef.requiredFields,
    actionId
  );
  if (!fieldResult.valid) return fieldResult;

  // 6. Validate schema
  const schemaResult = validateSchema(payload, actionDef.schemaFile, actionId);
  if (!schemaResult.valid) return schemaResult;

  return validationSuccess({ params });
}
