/**
 * HandoverQueueView unit tests
 *
 * Tests cover:
 * - Sections render with items from mocked queue response
 * - "No items" empty state per section
 * - "Already added" state shows checkmark
 * - Error + retry state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as React from 'react';

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('@/contexts/VesselContext', () => ({
  useActiveVessel: () => ({ vesselId: 'vessel-abc-123' }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'user-xyz', role: 'chief_engineer' } }),
}));

vi.mock('@/lib/supabaseClient', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'tok' } } }) },
  },
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// fetchHandoverQueue is the API call we control in tests
const mockFetchHandoverQueue = vi.fn();
vi.mock('@/components/shell/api', () => ({
  fetchHandoverQueue: (...args: unknown[]) => mockFetchHandoverQueue(...args),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const EMPTY_QUEUE = {
  open_faults: [],
  overdue_work_orders: [],
  low_stock_parts: [],
  pending_orders: [],
  already_queued: [],
  counts: { faults: 0, work_orders: 0, parts: 0, orders: 0, already_queued: 0 },
};

const QUEUE_WITH_ITEMS = {
  open_faults: [
    { id: 'fault-01', title: 'Port engine vibration', severity: 'high', equipment_name: 'Port Engine', created_at: '2026-04-01T00:00:00Z' },
  ],
  overdue_work_orders: [
    { id: 'wo-01', title: 'Engine mount replacement', priority: 'urgent', due_at: '2026-03-28T00:00:00Z', assigned_to: 'John' },
  ],
  low_stock_parts: [],
  pending_orders: [],
  already_queued: [],
  counts: { faults: 1, work_orders: 1, parts: 0, orders: 0, already_queued: 0 },
};

const QUEUE_WITH_QUEUED = {
  ...QUEUE_WITH_ITEMS,
  already_queued: [{ id: 'qi-01', entity_type: 'fault', entity_id: 'fault-01', summary: 'Port engine vibration' }],
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function renderView() {
  const { HandoverQueueView } = await import('../HandoverQueueView');
  return render(<HandoverQueueView />);
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('HandoverQueueView — sections render', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders all four section labels', async () => {
    mockFetchHandoverQueue.mockResolvedValue(EMPTY_QUEUE);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('Open Faults')).toBeInTheDocument();
      expect(screen.getByText('Overdue Work Orders')).toBeInTheDocument();
      expect(screen.getByText('Low Stock Parts')).toBeInTheDocument();
      expect(screen.getByText('Pending Purchase Orders')).toBeInTheDocument();
    });
  });

  it('renders item titles when queue has items', async () => {
    mockFetchHandoverQueue.mockResolvedValue(QUEUE_WITH_ITEMS);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('Port engine vibration')).toBeInTheDocument();
      expect(screen.getByText('Engine mount replacement')).toBeInTheDocument();
    });
  });

  it('renders meta text alongside item titles', async () => {
    mockFetchHandoverQueue.mockResolvedValue(QUEUE_WITH_ITEMS);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      // Fault meta: severity · equipment_name
      expect(screen.getByText(/high.*Port Engine/i)).toBeInTheDocument();
    });
  });
});

describe('HandoverQueueView — empty state', () => {
  it('shows "No items in this category" for empty sections', async () => {
    mockFetchHandoverQueue.mockResolvedValue(EMPTY_QUEUE);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      const empties = screen.getAllByText('No items in this category');
      expect(empties.length).toBe(4);
    });
  });
});

describe('HandoverQueueView — already queued', () => {
  it('shows "Added" button for already-queued entity_ids', async () => {
    mockFetchHandoverQueue.mockResolvedValue(QUEUE_WITH_QUEUED);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      // fault-01 is in already_queued — should show "Added" not "Add"
      const addedBtns = screen.getAllByText('Added');
      expect(addedBtns.length).toBeGreaterThan(0);
    });
  });
});

describe('HandoverQueueView — error states', () => {
  it('shows retry button on error', async () => {
    mockFetchHandoverQueue.mockRejectedValue(new Error('Network error'));
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('Failed to load queue')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});
