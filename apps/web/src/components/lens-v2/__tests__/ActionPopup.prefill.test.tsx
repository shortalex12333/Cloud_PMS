/**
 * ActionPopup — Source-context (prefill) rendering tests (HANDOVER08 task B12).
 *
 * Contract:
 *   Prefill keys NOT mapped to a user-editable field render as a read-only
 *   "Source" block at the top of the popup. Back-end-only keys
 *   (entity_id, yacht_id, …) are never rendered. Null/undefined rows are
 *   skipped. Codes/identifiers render in monospace; numbers render in
 *   monospace; booleans render as Yes/No; the block is invisible when no
 *   rows survive filtering.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as React from 'react';
import { ActionPopup, type ActionPopupField } from '../ActionPopup';

// useAuth is only consumed by FieldEntitySearch; none of these tests render
// that field, but the import chain still evaluates the hook module. Stub to
// keep tests hermetic.
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: null, session: null }),
}));

// ─── Helpers ────────────────────────────────────────────────────────────────

function renderPopup(
  over: Partial<React.ComponentProps<typeof ActionPopup>> = {},
) {
  const props: React.ComponentProps<typeof ActionPopup> = {
    mode: 'mutate',
    title: 'Test action',
    fields: [],
    signatureLevel: 1,
    onSubmit: vi.fn(),
    onClose: vi.fn(),
    ...over,
  };
  return render(<ActionPopup {...props} />);
}

function getSourceBlock() {
  return screen.queryByTestId('action-popup-source');
}

// ─── Tests ──────────────────────────────────────────────────────────────────

describe('ActionPopup — Source context (prefill rendering)', () => {
  it('1. renders NO source block when prefill prop is absent', () => {
    renderPopup();
    expect(getSourceBlock()).toBeNull();
  });

  it('2. renders NO source block when prefill is {} (no keys)', () => {
    renderPopup({ prefill: {} });
    expect(getSourceBlock()).toBeNull();
  });

  it('3. renders code in monospace and name in sans when both are non-editable', () => {
    renderPopup({
      prefill: { code: 'EQ-001', name: 'Main Engine' },
      fields: [],
    });
    expect(getSourceBlock()).not.toBeNull();

    const codeRow = screen.getByTestId('action-popup-source-row-code');
    const nameRow = screen.getByTestId('action-popup-source-row-name');
    expect(codeRow).toHaveTextContent('Code');
    expect(codeRow).toHaveTextContent('EQ-001');
    expect(nameRow).toHaveTextContent('Name');
    expect(nameRow).toHaveTextContent('Main Engine');

    // monospace vs sans is driven by inline font-family on the value span.
    const codeVal = screen.getByTestId('action-popup-source-val-code');
    const nameVal = screen.getByTestId('action-popup-source-val-name');
    expect(codeVal.getAttribute('style')).toContain('var(--font-mono)');
    expect(nameVal.getAttribute('style')).toContain('var(--font-sans)');
  });

  it('4. excludes prefill keys that collide with a user-editable field', () => {
    const fields: ActionPopupField[] = [
      { name: 'summary', label: 'Summary', type: 'text-area' },
    ];
    renderPopup({
      prefill: { code: 'EQ-001', summary: 'hi' },
      fields,
    });
    expect(screen.getByTestId('action-popup-source-row-code')).toBeTruthy();
    expect(screen.queryByTestId('action-popup-source-row-summary')).toBeNull();
  });

  it('5. omits backend-only keys (entity_id) from the Source block', () => {
    renderPopup({
      prefill: { entity_id: '00000000-0000-0000-0000-000000000000', code: 'X' },
    });
    expect(screen.getByTestId('action-popup-source-row-code')).toBeTruthy();
    expect(screen.queryByTestId('action-popup-source-row-entity_id')).toBeNull();
  });

  it('6. renders numbers in monospace', () => {
    renderPopup({ prefill: { running_hours: 1234 } });
    const row = screen.getByTestId('action-popup-source-row-running_hours');
    expect(row).toHaveTextContent('Running hours');
    expect(row).toHaveTextContent('1234');
    const val = screen.getByTestId('action-popup-source-val-running_hours');
    expect(val.getAttribute('style')).toContain('var(--font-mono)');
  });

  it('7. renders booleans as Yes / No', () => {
    renderPopup({ prefill: { is_critical: true, is_archived: false } });
    expect(
      screen.getByTestId('action-popup-source-row-is_critical'),
    ).toHaveTextContent('Yes');
    expect(
      screen.getByTestId('action-popup-source-row-is_archived'),
    ).toHaveTextContent('No');
  });

  it('8. skips rows whose value is null', () => {
    renderPopup({ prefill: { some_null_field: null, code: 'X' } });
    expect(screen.getByTestId('action-popup-source-row-code')).toBeTruthy();
    expect(
      screen.queryByTestId('action-popup-source-row-some_null_field'),
    ).toBeNull();
  });
});
