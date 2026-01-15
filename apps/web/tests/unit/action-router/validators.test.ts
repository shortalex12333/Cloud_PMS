/**
 * Action Router Validators Unit Tests
 *
 * Tests for all validation functions.
 */

import { describe, it, expect } from 'vitest';
import {
  validationSuccess,
  validationFailure,
  validateJWT,
  validateUserContext,
  validateYachtIsolation,
  validateRolePermission,
  validateRequiredFields,
  validateFieldType,
  validateSchema,
  validateActionRequest,
} from '@/lib/action-router/validators';
import type { UserContext, ActionContext } from '@/lib/action-router/types';

describe('Action Router Validators', () => {
  // ============================================================================
  // Validation Result Helpers Tests
  // ============================================================================

  describe('validationSuccess', () => {
    it('should create valid result with no context', () => {
      const result = validationSuccess();
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
      expect(result.context).toEqual({});
    });

    it('should create valid result with context', () => {
      const result = validationSuccess({ key: 'value' });
      expect(result.valid).toBe(true);
      expect(result.context).toEqual({ key: 'value' });
    });
  });

  describe('validationFailure', () => {
    it('should create invalid result with error', () => {
      const result = validationFailure('error_code', 'Error message');
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('error_code');
      expect(result.error?.message).toBe('Error message');
    });

    it('should include field and details if provided', () => {
      const result = validationFailure('code', 'msg', 'field_name', { extra: 'info' });
      expect(result.error?.field).toBe('field_name');
      expect(result.error?.details).toEqual({ extra: 'info' });
    });
  });

  // ============================================================================
  // JWT Validation Tests
  // ============================================================================

  describe('validateJWT', () => {
    it('should fail for missing authorization', () => {
      const result = validateJWT(null);
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('missing_token');
    });

    it('should fail for empty authorization', () => {
      const result = validateJWT('');
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('missing_token');
    });

    it('should fail for missing Bearer prefix', () => {
      const result = validateJWT('token123');
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('invalid_token');
    });

    it('should fail for empty token after Bearer', () => {
      const result = validateJWT('Bearer ');
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('invalid_token');
    });

    it('should pass for valid Bearer token format', () => {
      const result = validateJWT('Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================================
  // User Context Validation Tests
  // ============================================================================

  describe('validateUserContext', () => {
    it('should fail for null context', () => {
      const result = validateUserContext(null);
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('invalid_token');
    });

    it('should fail for missing user_id', () => {
      const result = validateUserContext({
        yacht_id: 'yacht-123',
        role: 'Engineer',
      } as UserContext);
      expect(result.valid).toBe(false);
      expect(result.error?.message).toContain('User ID');
    });

    it('should fail for missing yacht_id', () => {
      const result = validateUserContext({
        user_id: 'user-123',
        role: 'Engineer',
      } as UserContext);
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('yacht_not_found');
    });

    it('should fail for missing role', () => {
      const result = validateUserContext({
        user_id: 'user-123',
        yacht_id: 'yacht-123',
      } as UserContext);
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('permission_denied');
    });

    it('should pass for complete context', () => {
      const result = validateUserContext({
        user_id: 'user-123',
        yacht_id: 'yacht-123',
        role: 'Engineer',
      });
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================================
  // Yacht Isolation Tests
  // ============================================================================

  describe('validateYachtIsolation', () => {
    const userContext: UserContext = {
      user_id: 'user-123',
      yacht_id: 'yacht-abc',
      role: 'Engineer',
    };

    it('should fail for missing yacht_id in action context', () => {
      const result = validateYachtIsolation({} as ActionContext, userContext);
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('yacht_not_found');
    });

    it('should fail for mismatched yacht_id', () => {
      const result = validateYachtIsolation(
        { yacht_id: 'yacht-xyz' },
        userContext
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('yacht_mismatch');
    });

    it('should pass for matching yacht_id', () => {
      const result = validateYachtIsolation(
        { yacht_id: 'yacht-abc' },
        userContext
      );
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================================
  // Role Permission Tests
  // ============================================================================

  describe('validateRolePermission', () => {
    it('should pass when role is in allowed list', () => {
      const result = validateRolePermission(
        { user_id: 'u', yacht_id: 'y', role: 'Engineer' },
        ['Engineer', 'HOD', 'Manager'],
        'test_action'
      );
      expect(result.valid).toBe(true);
    });

    it('should fail when role is not in allowed list', () => {
      const result = validateRolePermission(
        { user_id: 'u', yacht_id: 'y', role: 'Crew' },
        ['Engineer', 'HOD', 'Manager'],
        'test_action'
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('permission_denied');
    });

    it('should include role details in error', () => {
      const result = validateRolePermission(
        { user_id: 'u', yacht_id: 'y', role: 'Crew' },
        ['HOD', 'Manager'],
        'close_work_order'
      );
      expect(result.error?.details?.user_role).toBe('Crew');
      expect(result.error?.details?.allowed_roles).toEqual(['HOD', 'Manager']);
    });
  });

  // ============================================================================
  // Required Fields Tests
  // ============================================================================

  describe('validateRequiredFields', () => {
    it('should pass when all required fields present', () => {
      const result = validateRequiredFields(
        { yacht_id: 'y', equipment_id: 'e', note_text: 'text' },
        ['yacht_id', 'equipment_id', 'note_text'],
        'add_note'
      );
      expect(result.valid).toBe(true);
    });

    it('should fail for missing field', () => {
      const result = validateRequiredFields(
        { yacht_id: 'y', equipment_id: 'e' },
        ['yacht_id', 'equipment_id', 'note_text'],
        'add_note'
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('missing_field');
      expect(result.error?.details?.missing_fields).toContain('note_text');
    });

    it('should fail for null field', () => {
      const result = validateRequiredFields(
        { yacht_id: 'y', note_text: null },
        ['yacht_id', 'note_text'],
        'test'
      );
      expect(result.valid).toBe(false);
    });

    it('should fail for empty string field', () => {
      const result = validateRequiredFields(
        { yacht_id: 'y', note_text: '   ' },
        ['yacht_id', 'note_text'],
        'test'
      );
      expect(result.valid).toBe(false);
    });

    it('should report multiple missing fields', () => {
      const result = validateRequiredFields(
        { yacht_id: 'y' },
        ['yacht_id', 'equipment_id', 'note_text'],
        'test'
      );
      expect(result.error?.details?.missing_fields).toHaveLength(2);
    });
  });

  // ============================================================================
  // Field Type Tests
  // ============================================================================

  describe('validateFieldType', () => {
    it('should pass for null/undefined (handled by required check)', () => {
      expect(validateFieldType(null, 'field', 'string').valid).toBe(true);
      expect(validateFieldType(undefined, 'field', 'number').valid).toBe(true);
    });

    it('should validate string type', () => {
      expect(validateFieldType('hello', 'f', 'string').valid).toBe(true);
      expect(validateFieldType(123, 'f', 'string').valid).toBe(false);
    });

    it('should validate number type', () => {
      expect(validateFieldType(123, 'f', 'number').valid).toBe(true);
      expect(validateFieldType('123', 'f', 'number').valid).toBe(false);
      expect(validateFieldType(NaN, 'f', 'number').valid).toBe(false);
    });

    it('should validate uuid type', () => {
      expect(
        validateFieldType('550e8400-e29b-41d4-a716-446655440000', 'f', 'uuid').valid
      ).toBe(true);
      expect(validateFieldType('not-a-uuid', 'f', 'uuid').valid).toBe(false);
      expect(validateFieldType(123, 'f', 'uuid').valid).toBe(false);
    });

    it('should validate boolean type', () => {
      expect(validateFieldType(true, 'f', 'boolean').valid).toBe(true);
      expect(validateFieldType(false, 'f', 'boolean').valid).toBe(true);
      expect(validateFieldType('true', 'f', 'boolean').valid).toBe(false);
    });

    it('should validate array type', () => {
      expect(validateFieldType([], 'f', 'array').valid).toBe(true);
      expect(validateFieldType([1, 2], 'f', 'array').valid).toBe(true);
      expect(validateFieldType({}, 'f', 'array').valid).toBe(false);
    });

    it('should validate object type', () => {
      expect(validateFieldType({}, 'f', 'object').valid).toBe(true);
      expect(validateFieldType({ a: 1 }, 'f', 'object').valid).toBe(true);
      expect(validateFieldType([], 'f', 'object').valid).toBe(false);
    });
  });

  // ============================================================================
  // Schema Validation Tests
  // ============================================================================

  describe('validateSchema', () => {
    it('should pass when no schema file', () => {
      const result = validateSchema({ data: 'anything' }, null, 'action');
      expect(result.valid).toBe(true);
    });

    it('should fail for non-object payload', () => {
      const result = validateSchema([] as any, 'schema.json', 'action');
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('schema_validation_error');
    });

    it('should validate note_text length for add_note', () => {
      const longText = 'a'.repeat(10001);
      const result = validateSchema(
        { note_text: longText },
        'add_note.json',
        'add_note'
      );
      expect(result.valid).toBe(false);
      expect(result.error?.field).toBe('note_text');
    });

    it('should validate priority for create_work_order', () => {
      const result = validateSchema(
        { priority: 'invalid' },
        'create_work_order.json',
        'create_work_order'
      );
      expect(result.valid).toBe(false);
      expect(result.error?.field).toBe('priority');
    });

    it('should validate qty for order_part', () => {
      const result = validateSchema(
        { qty: -5 },
        'order_part.json',
        'order_part'
      );
      expect(result.valid).toBe(false);
      expect(result.error?.field).toBe('qty');
    });

    it('should pass valid create_work_order payload', () => {
      const result = validateSchema(
        { priority: 'high' },
        'create_work_order.json',
        'create_work_order'
      );
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================================
  // Composite Validation Tests
  // ============================================================================

  describe('validateActionRequest', () => {
    const userContext: UserContext = {
      user_id: 'user-123',
      yacht_id: 'yacht-abc',
      role: 'Engineer',
    };

    const actionDef = {
      allowedRoles: ['Engineer', 'HOD', 'Manager'],
      requiredFields: ['yacht_id', 'equipment_id', 'note_text'],
      schemaFile: 'add_note.json',
    };

    it('should pass for valid request', () => {
      const result = validateActionRequest(
        'add_note',
        { yacht_id: 'yacht-abc', equipment_id: 'eq-1' },
        { note_text: 'Test note' },
        userContext,
        actionDef
      );
      expect(result.valid).toBe(true);
    });

    it('should fail for yacht mismatch', () => {
      const result = validateActionRequest(
        'add_note',
        { yacht_id: 'wrong-yacht', equipment_id: 'eq-1' },
        { note_text: 'Test' },
        userContext,
        actionDef
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('yacht_mismatch');
    });

    it('should fail for unauthorized role', () => {
      const result = validateActionRequest(
        'add_note',
        { yacht_id: 'yacht-abc', equipment_id: 'eq-1' },
        { note_text: 'Test' },
        { ...userContext, role: 'Guest' },
        actionDef
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('permission_denied');
    });

    it('should fail for missing required field', () => {
      const result = validateActionRequest(
        'add_note',
        { yacht_id: 'yacht-abc' },
        { note_text: 'Test' },
        userContext,
        actionDef
      );
      expect(result.valid).toBe(false);
      expect(result.error?.error_code).toBe('missing_field');
    });
  });
});
