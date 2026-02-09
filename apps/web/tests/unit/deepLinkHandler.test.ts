/**
 * Unit tests for DeepLinkHandler prefetch logic
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the microaction handlers
vi.mock('@/lib/microactions/handlers/workOrders', () => ({
  viewWorkOrder: vi.fn(),
}));

vi.mock('@/lib/microactions/handlers/faults', () => ({
  viewFault: vi.fn(),
}));

vi.mock('@/lib/microactions/handlers/equipment', () => ({
  viewEquipmentDetails: vi.fn(),
}));

vi.mock('@/lib/microactions/handlers/inventory', () => ({
  viewPartStock: vi.fn(),
}));

import { viewWorkOrder } from '@/lib/microactions/handlers/workOrders';
import { viewFault } from '@/lib/microactions/handlers/faults';
import { viewEquipmentDetails } from '@/lib/microactions/handlers/equipment';
import { viewPartStock } from '@/lib/microactions/handlers/inventory';

// Import the types
import type { ActionContext, ActionResult } from '@/lib/microactions/types';

describe('DeepLinkHandler prefetch logic', () => {
  const mockContext: ActionContext = {
    yacht_id: 'test-yacht-id',
    user_id: 'test-user-id',
    user_role: 'member',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Work Order prefetch', () => {
    it('should call viewWorkOrder with correct params', async () => {
      const mockResult: ActionResult = {
        success: true,
        action_name: 'view_work_order',
        data: {
          work_order: {
            id: 'wo-123',
            title: 'Test Work Order',
            description: 'Test description',
            status: 'in_progress',
            priority: 'high',
            created_at: '2026-01-01T00:00:00Z',
          },
          checklist_progress: { completed: 2, total: 5, percent: 40 },
          parts_count: 3,
        },
        error: null,
        confirmation_required: false,
      };

      (viewWorkOrder as any).mockResolvedValue(mockResult);

      // Call the handler
      const result = await viewWorkOrder(mockContext, { work_order_id: 'wo-123' });

      expect(viewWorkOrder).toHaveBeenCalledWith(mockContext, { work_order_id: 'wo-123' });
      expect(result.success).toBe(true);
      expect((result.data as any).work_order.title).toBe('Test Work Order');
    });

    it('should return error when work order not found', async () => {
      const mockResult: ActionResult = {
        success: false,
        action_name: 'view_work_order',
        data: null,
        error: { code: 'NOT_FOUND', message: 'Work order not found' },
        confirmation_required: false,
      };

      (viewWorkOrder as any).mockResolvedValue(mockResult);

      const result = await viewWorkOrder(mockContext, { work_order_id: 'invalid-id' });

      expect(result.success).toBe(false);
      expect(result.error?.message).toBe('Work order not found');
    });
  });

  describe('Fault prefetch', () => {
    it('should call viewFault with correct params', async () => {
      const mockResult: ActionResult = {
        success: true,
        action_name: 'view_fault',
        data: {
          fault: {
            id: 'fault-123',
            title: 'Engine Overheating',
            severity: 'high',
            created_at: '2026-01-01T00:00:00Z',
          },
        },
        error: null,
        confirmation_required: false,
      };

      (viewFault as any).mockResolvedValue(mockResult);

      const result = await viewFault(mockContext, { fault_id: 'fault-123' });

      expect(viewFault).toHaveBeenCalledWith(mockContext, { fault_id: 'fault-123' });
      expect(result.success).toBe(true);
    });
  });

  describe('Equipment prefetch', () => {
    it('should call viewEquipmentDetails with correct params', async () => {
      const mockResult: ActionResult = {
        success: true,
        action_name: 'view_equipment_details',
        data: {
          equipment: {
            id: 'eq-123',
            name: 'Main Engine',
            status: 'operational',
          },
        },
        error: null,
        confirmation_required: false,
      };

      (viewEquipmentDetails as any).mockResolvedValue(mockResult);

      const result = await viewEquipmentDetails(mockContext, { equipment_id: 'eq-123' });

      expect(viewEquipmentDetails).toHaveBeenCalledWith(mockContext, { equipment_id: 'eq-123' });
      expect(result.success).toBe(true);
    });
  });

  describe('Part prefetch', () => {
    it('should call viewPartStock with correct params', async () => {
      const mockResult: ActionResult = {
        success: true,
        action_name: 'view_part_stock',
        data: {
          part: {
            id: 'part-123',
            name: 'Oil Filter',
            quantity: 5,
            stock_status: 'IN_STOCK',
          },
        },
        error: null,
        confirmation_required: false,
      };

      (viewPartStock as any).mockResolvedValue(mockResult);

      const result = await viewPartStock(mockContext, { part_id: 'part-123' });

      expect(viewPartStock).toHaveBeenCalledWith(mockContext, { part_id: 'part-123' });
      expect(result.success).toBe(true);
    });
  });
});
