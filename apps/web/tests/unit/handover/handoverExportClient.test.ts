/**
 * Handover Export Client Unit Tests
 *
 * Tests for the handover export client functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  resolveOpenToken,
  ResolveError,
  isSupportedEntityType,
  isUnsupportedEntityType,
  SUPPORTED_ENTITY_TYPES,
  UNSUPPORTED_ENTITY_TYPES,
} from '@/lib/handoverExportClient';

// Mock authHelpers
vi.mock('@/lib/authHelpers', () => ({
  getValidJWT: vi.fn().mockResolvedValue('mock-jwt-token'),
  AuthError: class AuthError extends Error {
    constructor(message: string, public code: string) {
      super(message);
      this.name = 'AuthError';
    }
  },
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('handoverExportClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ============================================================================
  // resolveOpenToken Tests
  // ============================================================================

  describe('resolveOpenToken', () => {
    it('should throw ResolveError for empty token', async () => {
      await expect(resolveOpenToken('')).rejects.toThrow(ResolveError);
      await expect(resolveOpenToken('')).rejects.toMatchObject({
        code: 'TOKEN_INVALID',
        status: 400,
      });
    });

    it('should call API with correct headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            focus: { type: 'work_order', id: 'test-id' },
            yacht_id: 'yacht-123',
            scope: 'view',
            version: 1,
          }),
      });

      await resolveOpenToken('test-token');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/open/resolve'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-jwt-token',
          }),
          body: JSON.stringify({ t: 'test-token' }),
        })
      );
    });

    it('should return focus descriptor on success', async () => {
      const mockResponse = {
        focus: { type: 'fault', id: 'fault-123' },
        yacht_id: 'yacht-456',
        scope: 'view',
        version: 1,
        entity_title: 'Test Fault',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await resolveOpenToken('valid-token');

      expect(result).toEqual(mockResponse);
      expect(result.focus.type).toBe('fault');
      expect(result.focus.id).toBe('fault-123');
    });

    it('should throw TOKEN_EXPIRED for 401 with expired message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Token has expired' }),
      });

      await expect(resolveOpenToken('expired-token')).rejects.toMatchObject({
        code: 'TOKEN_EXPIRED',
        status: 401,
      });
    });

    it('should throw AUTH_REQUIRED for 401 without expired message', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid token' }),
      });

      await expect(resolveOpenToken('bad-token')).rejects.toMatchObject({
        code: 'AUTH_REQUIRED',
        status: 401,
      });
    });

    it('should throw YACHT_MISMATCH for 403', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () =>
          Promise.resolve({ detail: 'Token belongs to different yacht' }),
      });

      await expect(resolveOpenToken('wrong-yacht-token')).rejects.toMatchObject({
        code: 'YACHT_MISMATCH',
        status: 403,
      });
    });

    it('should throw ENTITY_NOT_FOUND for 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Entity not found' }),
      });

      await expect(resolveOpenToken('missing-entity-token')).rejects.toMatchObject(
        {
          code: 'ENTITY_NOT_FOUND',
          status: 404,
        }
      );
    });

    it('should throw UNSUPPORTED_TYPE for 400 with "not yet supported"', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () =>
          Promise.resolve({ detail: 'Entity type inventory not yet supported' }),
      });

      await expect(
        resolveOpenToken('unsupported-type-token')
      ).rejects.toMatchObject({
        code: 'UNSUPPORTED_TYPE',
        status: 400,
      });
    });

    it('should throw UNKNOWN_TYPE for 400 with "unknown entity type"', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: 'Unknown entity type: xyz' }),
      });

      await expect(
        resolveOpenToken('unknown-type-token')
      ).rejects.toMatchObject({
        code: 'UNKNOWN_TYPE',
        status: 400,
      });
    });

    it('should throw TOKEN_INVALID for other 400 errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: 'Malformed token' }),
      });

      await expect(resolveOpenToken('malformed-token')).rejects.toMatchObject({
        code: 'TOKEN_INVALID',
        status: 400,
      });
    });

    it('should throw UNKNOWN_ERROR for other status codes', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal server error' }),
      });

      await expect(resolveOpenToken('server-error-token')).rejects.toMatchObject(
        {
          code: 'UNKNOWN_ERROR',
          status: 500,
        }
      );
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(resolveOpenToken('network-error')).rejects.toMatchObject({
        code: 'UNKNOWN_ERROR',
        status: 500,
      });
    });

    it('should handle JSON parse errors in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(resolveOpenToken('invalid-json')).rejects.toMatchObject({
        code: 'TOKEN_INVALID',
        status: 400,
      });
    });
  });

  // ============================================================================
  // isSupportedEntityType Tests
  // ============================================================================

  describe('isSupportedEntityType', () => {
    it('should return true for all supported types', () => {
      for (const type of SUPPORTED_ENTITY_TYPES) {
        expect(isSupportedEntityType(type)).toBe(true);
      }
    });

    it('should return false for unsupported types', () => {
      for (const type of UNSUPPORTED_ENTITY_TYPES) {
        expect(isSupportedEntityType(type)).toBe(false);
      }
    });

    it('should return false for unknown types', () => {
      expect(isSupportedEntityType('unknown_type')).toBe(false);
      expect(isSupportedEntityType('')).toBe(false);
      expect(isSupportedEntityType('WORK_ORDER')).toBe(false); // Case sensitive
    });
  });

  // ============================================================================
  // isUnsupportedEntityType Tests
  // ============================================================================

  describe('isUnsupportedEntityType', () => {
    it('should return true for all unsupported types', () => {
      for (const type of UNSUPPORTED_ENTITY_TYPES) {
        expect(isUnsupportedEntityType(type)).toBe(true);
      }
    });

    it('should return false for supported types', () => {
      for (const type of SUPPORTED_ENTITY_TYPES) {
        expect(isUnsupportedEntityType(type)).toBe(false);
      }
    });

    it('should return false for unknown types', () => {
      expect(isUnsupportedEntityType('unknown_type')).toBe(false);
    });
  });

  // ============================================================================
  // ResolveError Tests
  // ============================================================================

  describe('ResolveError', () => {
    it('should have correct properties', () => {
      const error = new ResolveError('TOKEN_EXPIRED', 'Token has expired', 401);

      expect(error.code).toBe('TOKEN_EXPIRED');
      expect(error.message).toBe('Token has expired');
      expect(error.status).toBe(401);
      expect(error.name).toBe('ResolveError');
    });

    it('should be instanceof Error', () => {
      const error = new ResolveError('UNKNOWN_ERROR', 'Test', 500);
      expect(error).toBeInstanceOf(Error);
    });
  });

  // ============================================================================
  // Entity Type Constants Tests
  // ============================================================================

  describe('Entity Type Constants', () => {
    it('should have expected supported types', () => {
      expect(SUPPORTED_ENTITY_TYPES).toContain('work_order');
      expect(SUPPORTED_ENTITY_TYPES).toContain('fault');
      expect(SUPPORTED_ENTITY_TYPES).toContain('equipment');
      expect(SUPPORTED_ENTITY_TYPES).toContain('part');
      expect(SUPPORTED_ENTITY_TYPES).toContain('warranty');
      expect(SUPPORTED_ENTITY_TYPES).toContain('document');
      expect(SUPPORTED_ENTITY_TYPES).toContain('email');
    });

    it('should have expected unsupported types', () => {
      expect(UNSUPPORTED_ENTITY_TYPES).toContain('inventory');
      expect(UNSUPPORTED_ENTITY_TYPES).toContain('purchase_order');
      expect(UNSUPPORTED_ENTITY_TYPES).toContain('voyage');
      expect(UNSUPPORTED_ENTITY_TYPES).toContain('guest');
      expect(UNSUPPORTED_ENTITY_TYPES).toContain('crew');
    });

    it('should have no overlap between supported and unsupported', () => {
      const supported = new Set(SUPPORTED_ENTITY_TYPES);
      const unsupported = new Set(UNSUPPORTED_ENTITY_TYPES);

      for (const type of supported) {
        expect(unsupported.has(type)).toBe(false);
      }
    });
  });
});
