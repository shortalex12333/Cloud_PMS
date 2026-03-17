import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import * as React from 'react';
import { EntityLensProvider, useEntityLensContext } from '../EntityLensContext';
import type { EntityLensContextValue } from '../EntityLensContext';

const makeValue = (overrides: Partial<EntityLensContextValue> = {}): EntityLensContextValue => ({
  entityType: 'work_order',
  entityId: 'test-id',
  entity: null,
  availableActions: [],
  isLoading: false,
  error: null,
  executeAction: async () => ({ success: true }),
  refetch: () => {},
  getAction: () => null,
  ...overrides,
});

describe('useEntityLensContext', () => {
  it('throws when used outside EntityLensProvider', () => {
    expect(() => {
      renderHook(() => useEntityLensContext());
    }).toThrow('useEntityLensContext must be used inside EntityLensProvider');
  });

  it('returns the provided value when inside EntityLensProvider', () => {
    const value = makeValue({ entityId: 'abc-123' });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.entityId).toBe('abc-123');
  });

  it('getAction returns null for an action_id not in availableActions', () => {
    const value = makeValue({
      availableActions: [
        { action_id: 'close_work_order', label: 'Close', variant: 'MUTATE', disabled: false, disabled_reason: null, requires_signature: false, prefill: {}, required_fields: [], optional_fields: [] },
      ],
    });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.getAction('nonexistent_action')).toBeNull();
  });

  it('getAction returns the action when it exists in availableActions', () => {
    const action = {
      action_id: 'close_work_order',
      label: 'Close',
      variant: 'MUTATE' as const,
      disabled: false,
      disabled_reason: null,
      requires_signature: false,
      prefill: {},
      required_fields: [],
      optional_fields: [],
    };
    const value = makeValue({ availableActions: [action] });
    const { result } = renderHook(() => useEntityLensContext(), {
      wrapper: ({ children }) => (
        <EntityLensProvider value={value}>{children}</EntityLensProvider>
      ),
    });
    expect(result.current.getAction('close_work_order')).toEqual(action);
  });
});
