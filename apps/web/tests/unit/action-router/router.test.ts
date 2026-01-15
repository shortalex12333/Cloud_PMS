/**
 * Action Router Unit Tests
 *
 * Tests for main router functions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  executeAction,
  executeActionById,
  canExecuteAction,
  getExecutableActions,
} from '@/lib/action-router/router';
import type { ActionRequest, UserContext } from '@/lib/action-router/types';

// Mock Supabase client
vi.mock('@/lib/supabaseClient', () => ({
  supabase: {
    from: vi.fn().mockReturnValue({
      insert: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 'new-id', created_at: '2025-01-01' },
            error: null,
          }),
        }),
      }),
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            single: vi.fn().mockResolvedValue({
              data: { id: 'wo-123' },
              error: null,
            }),
          }),
        }),
      }),
      update: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            select: vi.fn().mockReturnValue({
              single: vi.fn().mockResolvedValue({
                data: { id: 'wo-123', status: 'completed', completed_at: '2025-01-01' },
                error: null,
              }),
            }),
          }),
        }),
      }),
    }),
    storage: {
      from: vi.fn().mockReturnValue({
        createSignedUrl: vi.fn().mockResolvedValue({
          data: { signedUrl: 'https://example.com/signed-url' },
          error: null,
        }),
      }),
    },
  },
}));

describe('Action Router', () => {
  const validUserContext: UserContext = {
    user_id: '550e8400-e29b-41d4-a716-446655440000',
    yacht_id: '550e8400-e29b-41d4-a716-446655440001',
    role: 'Engineer',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // executeAction Tests
  // ============================================================================

  describe('executeAction', () => {
    it('should fail for unknown action', async () => {
      const request: ActionRequest = {
        action: 'unknown_action',
        context: { yacht_id: validUserContext.yacht_id },
        payload: {},
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('action_not_found');
    });

    it('should fail for yacht mismatch', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: { yacht_id: 'different-yacht' },
        payload: { equipment_id: 'eq-1', note_text: 'Test' },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('yacht_mismatch');
    });

    it('should fail for unauthorized role', async () => {
      const request: ActionRequest = {
        action: 'close_work_order',
        context: { yacht_id: validUserContext.yacht_id },
        payload: { work_order_id: 'wo-123' },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('permission_denied');
    });

    it('should fail for missing required fields', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: { yacht_id: validUserContext.yacht_id },
        payload: { note_text: 'Test' }, // Missing equipment_id
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('missing_field');
    });

    it('should execute valid internal action', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: {
          yacht_id: validUserContext.yacht_id,
          equipment_id: 'eq-123',
        },
        payload: { note_text: 'Test note' },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('success');
      expect(result.result).toBeDefined();
      expect(result.result?.note_id).toBeDefined();
    });

    it('should skip validation when option set', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: { yacht_id: 'wrong-yacht' },
        payload: { equipment_id: 'eq-1', note_text: 'Test' },
      };

      // This should succeed because validation is skipped
      // (In real use, the handler might still fail on database constraints)
      const result = await executeAction(request, validUserContext, {
        skipValidation: true,
        skipLogging: true,
      });

      // Action proceeds without validation error
      expect(result.error_code).not.toBe('yacht_mismatch');
    });
  });

  // ============================================================================
  // executeActionById Tests
  // ============================================================================

  describe('executeActionById', () => {
    it('should execute action with simplified parameters', async () => {
      const result = await executeActionById(
        'add_note',
        validUserContext.yacht_id,
        { equipment_id: 'eq-123', note_text: 'Test' },
        validUserContext
      );

      expect(result.action).toBe('add_note');
    });

    it('should fail for invalid action ID', async () => {
      const result = await executeActionById(
        'invalid',
        validUserContext.yacht_id,
        {},
        validUserContext
      );

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('action_not_found');
    });
  });

  // ============================================================================
  // canExecuteAction Tests
  // ============================================================================

  describe('canExecuteAction', () => {
    it('should return true for allowed action', () => {
      expect(canExecuteAction('add_note', 'Engineer')).toBe(true);
      expect(canExecuteAction('create_work_order', 'Engineer')).toBe(true);
    });

    it('should return false for disallowed action', () => {
      expect(canExecuteAction('close_work_order', 'Engineer')).toBe(false);
      expect(canExecuteAction('export_handover', 'Engineer')).toBe(false);
    });

    it('should return false for unknown action', () => {
      expect(canExecuteAction('fake_action', 'Engineer')).toBe(false);
    });

    it('should check HOD permissions correctly', () => {
      expect(canExecuteAction('close_work_order', 'HOD')).toBe(true);
      expect(canExecuteAction('export_handover', 'HOD')).toBe(true);
    });

    it('should check Manager permissions correctly', () => {
      expect(canExecuteAction('close_work_order', 'Manager')).toBe(true);
      expect(canExecuteAction('add_note', 'Manager')).toBe(true);
    });

    it('should check Crew permissions correctly', () => {
      expect(canExecuteAction('open_document', 'Crew')).toBe(true);
      expect(canExecuteAction('add_note', 'Crew')).toBe(false);
    });
  });

  // ============================================================================
  // getExecutableActions Tests
  // ============================================================================

  describe('getExecutableActions', () => {
    it('should return actions for Engineer', () => {
      const actions = getExecutableActions('Engineer');
      expect(actions).toContain('add_note');
      expect(actions).toContain('create_work_order');
      expect(actions).not.toContain('close_work_order');
    });

    it('should return actions for HOD', () => {
      const actions = getExecutableActions('HOD');
      expect(actions).toContain('close_work_order');
      expect(actions).toContain('export_handover');
    });

    it('should return limited actions for Crew', () => {
      const actions = getExecutableActions('Crew');
      expect(actions.length).toBeLessThan(5);
      expect(actions).toContain('open_document');
    });

    it('should return empty array for unknown role', () => {
      const actions = getExecutableActions('Unknown');
      expect(actions).toHaveLength(0);
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle empty payload', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: { yacht_id: validUserContext.yacht_id, equipment_id: 'eq-1' },
        payload: {},
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('missing_field');
    });

    it('should handle special characters in payload', async () => {
      const request: ActionRequest = {
        action: 'add_note',
        context: {
          yacht_id: validUserContext.yacht_id,
          equipment_id: 'eq-123',
        },
        payload: {
          note_text: 'Test <script>alert("xss")</script> \u00e9\u00e0\u00fc',
        },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      // Should execute (sanitization happens at display time)
      expect(result.status).toBe('success');
    });

    it('should handle very long note text within limit', async () => {
      const longText = 'a'.repeat(9999);
      const request: ActionRequest = {
        action: 'add_note',
        context: {
          yacht_id: validUserContext.yacht_id,
          equipment_id: 'eq-123',
        },
        payload: { note_text: longText },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('success');
    });

    it('should reject note text exceeding limit', async () => {
      const longText = 'a'.repeat(10001);
      const request: ActionRequest = {
        action: 'add_note',
        context: {
          yacht_id: validUserContext.yacht_id,
          equipment_id: 'eq-123',
        },
        payload: { note_text: longText },
      };

      const result = await executeAction(request, validUserContext, {
        skipLogging: true,
      });

      expect(result.status).toBe('error');
      expect(result.error_code).toBe('schema_validation_error');
    });
  });
});
