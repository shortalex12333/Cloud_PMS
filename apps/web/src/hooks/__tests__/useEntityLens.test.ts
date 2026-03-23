import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useEntityLens } from '../useEntityLens';

// Mock useAuth
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ session: { access_token: 'test-token' }, user: { id: 'u1' } }),
}));

// Mock React Query
const mockInvalidateQueries = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: mockInvalidateQueries }),
}));

// Mock useNeedsAttention export
vi.mock('@/hooks/useNeedsAttention', () => ({
  ATTENTION_QUERY_KEY: ['attention'],
}));

const mockAction = {
  action_id: 'close_work_order',
  label: 'Close',
  variant: 'MUTATE' as const,
  disabled: false,
  disabled_reason: null,
  requires_signature: false,
  prefill: { work_order_id: 'wo-1' },
  required_fields: ['work_order_id'],
  optional_fields: [],
};

const mockEntity = {
  id: 'wo-1',
  title: 'Test WO',
  status: 'open',
  available_actions: [mockAction],
};

describe('useEntityLens', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('fetches entity and populates entity + availableActions', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.entity).toEqual({ id: 'wo-1', title: 'Test WO', status: 'open' });
    expect(result.current.availableActions).toHaveLength(1);
    expect(result.current.availableActions[0].action_id).toBe('close_work_order');
  });

  it('sets error when fetch fails', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({}),
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'bad-id'));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe('404');
    expect(result.current.entity).toBeNull();
  });

  it('executeAction merges prefill into payload before POSTing', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', { completion_notes: 'done' });
    });

    const executeCalls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const executeCall = executeCalls[1];
    const body = JSON.parse(executeCall[1].body);
    expect(body.payload.work_order_id).toBe('wo-1');
    expect(body.payload.completion_notes).toBe('done');
  });

  it('executeAction triggers refetch on success', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...mockEntity, status: 'closed', available_actions: [] }) });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', {});
    });

    expect(result.current.availableActions).toHaveLength(0);
  });

  it('executeAction does NOT refetch when the execute POST fails', async () => {
    (fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ ok: true, json: async () => mockEntity })
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => ({ success: false, error: 'Validation failed' }) });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.executeAction('close_work_order', {});
    });

    expect((fetch as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(2);
    expect(result.current.availableActions).toHaveLength(1);
  });

  it('getAction returns null for an action_id not in availableActions', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.getAction('nonexistent')).toBeNull();
  });

  it('getAction returns the action when it exists', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEntity,
    });

    const { result } = renderHook(() => useEntityLens('work_order', 'wo-1'));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.getAction('close_work_order')).toEqual(mockAction);
  });
});
