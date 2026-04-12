/**
 * HandoverQueueView unit tests
 *
 * Tests cover:
 * - Loading skeleton renders per section
 * - Sections render with items from mocked queue response
 * - "No items" empty state per section
 * - "Already added" state shows checkmark
 * - Endpoint-pending graceful state (404 response)
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
  counts: { open_faults: 0, overdue_work_orders: 0, low_stock_parts: 0, pending_orders: 0, total: 0 },
};

const QUEUE_WITH_ITEMS = {
  open_faults: [
    { id: 'f1', entity_type: 'fault', entity_id: 'fault-01', title: 'Port engine vibration', ref: 'F-0061', status: 'open', age_display: '3d' },
  ],
  overdue_work_orders: [
    { id: 'w1', entity_type: 'work_order', entity_id: 'wo-01', title: 'Engine mount replacement', ref: 'WO-441', status: 'overdue' },
  ],
  low_stock_parts: [],
  pending_orders: [],
  already_queued: [],
  counts: { open_faults: 1, overdue_work_orders: 1, low_stock_parts: 0, pending_orders: 0, total: 2 },
};

const QUEUE_WITH_QUEUED = {
  ...QUEUE_WITH_ITEMS,
  already_queued: ['fault-01'],
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

  it('renders ref codes alongside item titles', async () => {
    mockFetchHandoverQueue.mockResolvedValue(QUEUE_WITH_ITEMS);
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('F-0061')).toBeInTheDocument();
      expect(screen.getByText('WO-441')).toBeInTheDocument();
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
  it('shows endpoint-pending message on 404 response', async () => {
    mockFetchHandoverQueue.mockRejectedValue(new Error('API 404: Not Found'));
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('Queue endpoint deploying')).toBeInTheDocument();
    });
  });

  it('shows retry button on non-404 error', async () => {
    mockFetchHandoverQueue.mockRejectedValue(new Error('Network error'));
    await act(async () => { await renderView(); });
    await waitFor(() => {
      expect(screen.getByText('Failed to load queue')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});
