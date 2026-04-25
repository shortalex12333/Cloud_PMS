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

  it('9. skips FK UUID rows when a paired human-readable name exists', () => {
    // Per FAULT05 PR #704 review: equipment_id / part_id / work_order_id / etc.
    // are routing plumbing; only the human-readable name surfaces to the user.
    renderPopup({
      prefill: {
        fault_code: 'F-0102',
        severity: 'high',
        equipment_id: '11111111-2222-3333-4444-555555555555',
        equipment_name: 'Main Engine',
      },
    });
    expect(screen.getByTestId('action-popup-source-row-fault_code')).toBeTruthy();
    expect(screen.getByTestId('action-popup-source-row-severity')).toBeTruthy();
    expect(screen.getByTestId('action-popup-source-row-equipment_name')).toBeTruthy();
    expect(
      screen.queryByTestId('action-popup-source-row-equipment_id'),
    ).toBeNull();
  });

  it('10a. applies acronym label overrides (po_number, wo_number, sku)', () => {
    // Per PURCHASE05 PR #704 review: humanizeKey defaults read weakly when an
    // embedded acronym is present ("Po number"). Override map fixes the
    // common ones without burning a general acronym inflector.
    renderPopup({
      prefill: {
        po_number: 'PO-2026-0042',
        wonumber: 'WO-0074',
        sku: 'XY-123',
      },
    });
    // Each row's textContent contains both label + value; assert label token.
    expect(
      screen.getByTestId('action-popup-source-row-po_number'),
    ).toHaveTextContent('PO number');
    expect(
      screen.getByTestId('action-popup-source-row-wonumber'),
    ).toHaveTextContent('WO number');
    expect(
      screen.getByTestId('action-popup-source-row-sku'),
    ).toHaveTextContent('SKU');
    // Negative check: the raw humanised form must NOT leak through.
    expect(
      screen.getByTestId('action-popup-source-row-po_number'),
    ).not.toHaveTextContent('Po number');
  });

  it('10. skips every FK UUID key in the hidden list', () => {
    // Regression guard for the never-render list. If a FK UUID ever surfaces
    // visually, this test should catch it.
    renderPopup({
      prefill: {
        code: 'EQ-001',
        equipment_id: 'x',
        part_id: 'x',
        work_order_id: 'x',
        fault_id: 'x',
        certificate_id: 'x',
        purchase_order_id: 'x',
        previous_export_id: 'x',
        added_by: 'x',
        outgoing_user_id: 'x',
      },
    });
    expect(screen.getByTestId('action-popup-source-row-code')).toBeTruthy();
    [
      'equipment_id',
      'part_id',
      'work_order_id',
      'fault_id',
      'certificate_id',
      'purchase_order_id',
      'previous_export_id',
      'added_by',
      'outgoing_user_id',
    ].forEach((key) => {
      expect(
        screen.queryByTestId(`action-popup-source-row-${key}`),
      ).toBeNull();
    });
  });
});
