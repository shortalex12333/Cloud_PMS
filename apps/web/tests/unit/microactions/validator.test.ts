/**
 * Validator Unit Tests
 *
 * Tests for the microaction validation system including context validation,
 * parameter validation, and full request validation.
 */

import { describe, it, expect } from 'vitest';
import {
  validateContext,
  validateParams,
  validateActionName,
  validateActionRequest,
  getParamSchema,
  requiresEntityId,
} from '@/lib/microactions/validator';
import type { ActionContext } from '@/lib/microactions/types';

describe('Validator Module', () => {
  // Valid UUIDs for testing
  const validUUID = '123e4567-e89b-12d3-a456-426614174000';
  const validUUID2 = '123e4567-e89b-12d3-a456-426614174001';

  // Valid context for testing
  const validContext: ActionContext = {
    yacht_id: validUUID,
    user_id: validUUID2,
    user_role: 'captain',
    source_card: 'fault',
  };

  // ============================================================================
  // Context Validation Tests
  // ============================================================================

  describe('Context Validation', () => {
    it('should validate a complete valid context', () => {
      const result = validateContext(validContext);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject invalid yacht_id UUID', () => {
      const context = { ...validContext, yacht_id: 'not-a-uuid' };
      const result = validateContext(context);
      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.field === 'yacht_id')).toBe(true);
    });

    it('should reject invalid user_id UUID', () => {
      const context = { ...validContext, user_id: 'invalid' };
      const result = validateContext(context);
      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.field === 'user_id')).toBe(true);
    });

    it('should reject empty user_role', () => {
      const context = { ...validContext, user_role: '' };
      const result = validateContext(context);
      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.field === 'user_role')).toBe(true);
    });

    it('should accept optional entity_id when valid', () => {
      const context = { ...validContext, entity_id: validUUID };
      const result = validateContext(context);
      expect(result.valid).toBe(true);
    });

    it('should reject invalid entity_id UUID', () => {
      const context = { ...validContext, entity_id: 'bad-uuid' };
      const result = validateContext(context);
      expect(result.valid).toBe(false);
    });

    it('should validate source_card enum values', () => {
      const context = { ...validContext, source_card: 'invalid_card' as any };
      const result = validateContext(context);
      expect(result.valid).toBe(false);
    });
  });

  // ============================================================================
  // Action Name Validation Tests
  // ============================================================================

  describe('Action Name Validation', () => {
    it('should validate existing action name', () => {
      const result = validateActionName('diagnose_fault');
      expect(result.valid).toBe(true);
    });

    it('should reject unknown action name', () => {
      const result = validateActionName('nonexistent_action');
      expect(result.valid).toBe(false);
      expect(result.errors[0].code).toBe('invalid_enum_value');
    });

    it('should reject empty action name', () => {
      const result = validateActionName('');
      expect(result.valid).toBe(false);
      expect(result.errors[0].code).toBe('required');
    });

    it('should reject null/undefined action name', () => {
      const result = validateActionName(null as any);
      expect(result.valid).toBe(false);
    });
  });

  // ============================================================================
  // Parameter Validation Tests
  // ============================================================================

  describe('Parameter Validation', () => {
    it('should validate diagnose_fault params', () => {
      const params = { fault_id: validUUID };
      const result = validateParams('diagnose_fault', params);
      expect(result.valid).toBe(true);
    });

    it('should reject invalid fault_id in diagnose_fault', () => {
      const params = { fault_id: 'not-a-uuid' };
      const result = validateParams('diagnose_fault', params);
      expect(result.valid).toBe(false);
    });

    it('should validate add_fault_note params', () => {
      const params = {
        fault_id: validUUID,
        note_text: 'Engine inspection completed',
      };
      const result = validateParams('add_fault_note', params);
      expect(result.valid).toBe(true);
    });

    it('should reject empty note_text in add_fault_note', () => {
      const params = {
        fault_id: validUUID,
        note_text: '',
      };
      const result = validateParams('add_fault_note', params);
      expect(result.valid).toBe(false);
    });

    it('should validate create_work_order params', () => {
      const params = {
        title: 'Fix engine coolant leak',
        description: 'Detected during routine inspection',
        priority: 'high',
        equipment_id: validUUID,
      };
      const result = validateParams('create_work_order', params);
      expect(result.valid).toBe(true);
    });

    it('should reject invalid priority in create_work_order', () => {
      const params = {
        title: 'Test',
        priority: 'invalid_priority',
      };
      const result = validateParams('create_work_order', params);
      expect(result.valid).toBe(false);
    });

    it('should validate order_part params', () => {
      const params = {
        part_id: validUUID,
        quantity: 5,
        urgency: 'urgent',
      };
      const result = validateParams('order_part', params);
      expect(result.valid).toBe(true);
    });

    it('should reject non-positive quantity in order_part', () => {
      const params = {
        part_id: validUUID,
        quantity: 0,
      };
      const result = validateParams('order_part', params);
      expect(result.valid).toBe(false);
    });

    it('should allow undefined params for read-only actions', () => {
      const result = validateParams('view_fault_history', undefined);
      expect(result.valid).toBe(true);
    });
  });

  // ============================================================================
  // Full Request Validation Tests
  // ============================================================================

  describe('Full Request Validation', () => {
    it('should validate complete valid request', () => {
      const params = { fault_id: validUUID };
      const result = validateActionRequest('diagnose_fault', validContext, params);
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should collect all errors from action, context, and params', () => {
      const invalidContext = {
        yacht_id: 'bad-uuid',
        user_id: 'bad-uuid',
        user_role: '',
      };
      const invalidParams = { fault_id: 'bad' };
      const result = validateActionRequest('diagnose_fault', invalidContext, invalidParams);
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
    });

    it('should fail fast on invalid action name', () => {
      const result = validateActionRequest('nonexistent', validContext, {});
      expect(result.valid).toBe(false);
      expect(result.errors[0].field).toBe('action_name');
    });
  });

  // ============================================================================
  // Schema & Utility Tests
  // ============================================================================

  describe('Schema Utilities', () => {
    it('should return schema for known action', () => {
      const schema = getParamSchema('create_work_order');
      expect(schema).not.toBeNull();
    });

    it('should return null for action without schema', () => {
      const schema = getParamSchema('view_fault_history');
      expect(schema).toBeNull();
    });

    it('should identify actions requiring entity_id', () => {
      expect(requiresEntityId('diagnose_fault')).toBe(true);
      expect(requiresEntityId('add_fault_note')).toBe(true);
      expect(requiresEntityId('view_equipment_details')).toBe(true);
    });

    it('should identify actions not requiring entity_id', () => {
      expect(requiresEntityId('create_work_order')).toBe(false);
      expect(requiresEntityId('export_handover')).toBe(false);
    });
  });
});
