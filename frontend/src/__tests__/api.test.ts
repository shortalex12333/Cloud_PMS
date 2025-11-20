/**
 * CelesteOS API Client Tests
 *
 * Tests for typed API wrappers using mocked fetch.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  api,
  APIError,
  searchAPI,
  workOrderAPI,
  predictiveAPI,
} from '../lib/api';
import * as supabase from '../lib/supabase';

// Mock Supabase getAccessToken
vi.mock('../lib/supabase', () => ({
  getAccessToken: vi.fn().mockResolvedValue('mock-jwt-token'),
}));

// Mock global fetch
global.fetch = vi.fn();

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Search API', () => {
    it('should perform search query', async () => {
      const mockResponse = {
        data: {
          query_id: 'test-query-id',
          intent: 'diagnose_fault',
          entities: {
            equipment_name: 'main engine',
            fault_code: 'E047',
          },
          results: [],
          actions: [],
          processing_time_ms: 123,
        },
        timestamp: new Date().toISOString(),
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await searchAPI.search({
        query: 'fault code E047 main engine',
        mode: 'auto',
      });

      expect(result.intent).toBe('diagnose_fault');
      expect(result.entities.equipment_name).toBe('main engine');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/search'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
      );
    });

    it('should handle search errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({
          error: {
            code: 'SEARCH_FAILED',
            message: 'Search engine unavailable',
          },
          timestamp: new Date().toISOString(),
        }),
      });

      await expect(searchAPI.search({ query: 'test' }))
        .rejects.toThrow(APIError);
    });
  });

  describe('Work Order API', () => {
    it('should create work order', async () => {
      const mockWorkOrder = {
        id: 'wo-123',
        yacht_id: 'yacht-456',
        title: 'Fix stabiliser leak',
        status: 'pending',
        priority: 'high',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockWorkOrder }),
      });

      const result = await workOrderAPI.create({
        title: 'Fix stabiliser leak',
        priority: 'high',
      });

      expect(result.id).toBe('wo-123');
      expect(result.status).toBe('pending');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/work-orders'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('Fix stabiliser leak'),
        })
      );
    });

    it('should list work orders with pagination', async () => {
      const mockResponse = {
        data: [
          { id: 'wo-1', title: 'Work Order 1' },
          { id: 'wo-2', title: 'Work Order 2' },
        ],
        pagination: {
          page: 1,
          page_size: 50,
          total_count: 2,
          total_pages: 1,
        },
        timestamp: new Date().toISOString(),
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await workOrderAPI.list({
        status: 'pending',
        page: 1,
        page_size: 50,
      });

      expect(result.data).toHaveLength(2);
      expect(result.pagination.total_count).toBe(2);
    });
  });

  describe('Predictive API', () => {
    it('should get predictive state', async () => {
      const mockState = [
        {
          id: 'ps-1',
          yacht_id: 'yacht-123',
          equipment_id: 'eq-456',
          risk_score: 0.75,
          risk_level: 'high',
          summary: 'High pressure faults detected',
          contributing_factors: ['Repeated E047 faults', 'Part consumption spike'],
          recommended_actions: ['Inspect compressor', 'Order replacement parts'],
          last_calculated: new Date().toISOString(),
        },
      ];

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockState }),
      });

      const result = await predictiveAPI.getState();

      expect(result).toHaveLength(1);
      expect(result[0].risk_level).toBe('high');
      expect(result[0].risk_score).toBe(0.75);
    });

    it('should trigger predictive calculation', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { status: 'calculating' } }),
      });

      const result = await predictiveAPI.triggerCalculation();

      expect(result.status).toBe('calculating');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/v1/predictive/calculate'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('should throw APIError with details', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: async () => ({
          error: {
            code: 'ACCESS_DENIED',
            message: 'Insufficient permissions',
            details: { required_role: 'manager' },
          },
          timestamp: new Date().toISOString(),
        }),
      });

      try {
        await searchAPI.search({ query: 'test' });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        expect((error as APIError).statusCode).toBe(403);
        expect((error as APIError).code).toBe('ACCESS_DENIED');
        expect((error as APIError).details).toEqual({ required_role: 'manager' });
      }
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      await expect(searchAPI.search({ query: 'test' }))
        .rejects.toThrow('Network error');
    });
  });

  describe('Authentication', () => {
    it('should include JWT in all requests', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      });

      await workOrderAPI.list();

      expect(supabase.getAccessToken).toHaveBeenCalled();
      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-jwt-token',
          }),
        })
      );
    });

    it('should handle missing token gracefully', async () => {
      vi.mocked(supabase.getAccessToken).mockResolvedValueOnce(null);

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: [] }),
      });

      await workOrderAPI.list();

      // Should still make request, but without Authorization header
      expect(global.fetch).toHaveBeenCalled();
    });
  });
});
