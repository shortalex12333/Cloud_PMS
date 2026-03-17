/**
 * RelatedDrawer unit tests
 *
 * TDD NOTE: The tests in the "signal section with empty FK groups" describe block
 * would have FAILED against the original RelatedDrawer. The original code had:
 *
 *   if (totalItems === 0) { return <empty state>; }          ← BUG: fires before signal eval
 *
 * Writing these tests FIRST (before integrating signal props) would have immediately
 * produced:
 *
 *   Expected: element with testid "signal-also-related" to be in the document
 *   Received: element "No related items found" text is in the document
 *
 * That failure would have forced the fix: move signal evaluation before the guard.
 * No E2E debugging needed — caught in <50ms by this unit test.
 *
 * Correct guard after fix:
 *   if (totalItems === 0 && !signalLoading && novelSignalItems.length === 0) {
 *     return <empty state>;
 *   }
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as React from 'react';
import { RelatedDrawer } from '../RelatedDrawer';
import type { SignalRelatedItem } from '@/hooks/useSignalRelated';
import type { RelatedGroup } from '@/hooks/useRelated';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const NO_FK_GROUPS: RelatedGroup[] = [];

const FK_GROUP_WITH_FAULT: RelatedGroup[] = [
  {
    group_key: 'faults',
    items: [
      {
        entity_type: 'fault',
        entity_id: 'fk-fault-id',
        title: 'FK Fault',
        weight: 90,
        match_reasons: ['FK:equipment_id'],
      },
    ],
  },
];

const SIGNAL_FAULT: SignalRelatedItem = {
  entity_id: 'signal-fault-id',
  entity_type: 'fault',
  title: 'Engine Overheating — Signal Match',
  subtitle: 'fault',
  match_reasons: ['signal:entity_embedding'],
  weight: 50,
};

const SIGNAL_MANUAL: SignalRelatedItem = {
  entity_id: 'signal-manual-id',
  entity_type: 'manual',
  title: 'C18 Engine Service Manual',
  subtitle: 'manual',
  match_reasons: ['signal:entity_embedding'],
  weight: 50,
};

// Used specifically to test entity_type label rendering — entity_type 'work_order'
// renders as 'work order' (after replace), which is distinct from its subtitle.
const SIGNAL_WORK_ORDER: SignalRelatedItem = {
  entity_id: 'signal-wo-id',
  entity_type: 'work_order',
  title: 'Main Engine Service',
  subtitle: 'Active',
  match_reasons: ['signal:entity_embedding'],
  weight: 50,
};

const noop = vi.fn();

// ─── Helpers ──────────────────────────────────────────────────────────────────

function renderDrawer(props: {
  groups?: RelatedGroup[];
  isLoading?: boolean;
  error?: Error | null;
  signalItems?: SignalRelatedItem[];
  signalLoading?: boolean;
}) {
  return render(
    <RelatedDrawer
      groups={props.groups ?? NO_FK_GROUPS}
      isLoading={props.isLoading ?? false}
      error={props.error ?? null}
      onNavigate={noop}
      signalItems={props.signalItems}
      signalLoading={props.signalLoading}
    />
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('RelatedDrawer — signal section with empty FK groups', () => {
  /**
   * THE critical test.
   *
   * TDD failure with old code:
   *   "No related items found." was rendered instead — early return fired
   *   before signal items were evaluated.
   *
   * This test is the regression guard. If the early return is ever
   * accidentally moved back above the signal evaluation, this test
   * immediately catches it.
   */
  it('renders "Also Related" section when FK groups empty but signal has items', () => {
    renderDrawer({ signalItems: [SIGNAL_FAULT, SIGNAL_MANUAL] });

    expect(screen.getByTestId('signal-also-related')).toBeInTheDocument();
    expect(screen.getByTestId('signal-item-fault-signal-fault-id')).toBeInTheDocument();
    expect(screen.getByTestId('signal-item-manual-signal-manual-id')).toBeInTheDocument();
  });

  it('does NOT show "No related items found" when signal has items', () => {
    renderDrawer({ signalItems: [SIGNAL_FAULT] });

    expect(screen.queryByText('No related items found.')).not.toBeInTheDocument();
  });

  it('shows spinner when FK groups empty and signal is loading', () => {
    renderDrawer({ signalLoading: true });

    const section = screen.getByTestId('signal-also-related');
    expect(section).toBeInTheDocument();
    expect(within(section).getByText('Discovering related…')).toBeInTheDocument();
  });

  it('shows empty state when FK empty AND signal returns no items AND not loading', () => {
    renderDrawer({ signalItems: [], signalLoading: false });

    expect(screen.getByText('No related items found.')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });

  it('shows empty state when signalItems prop is absent (backward compat)', () => {
    renderDrawer({});

    expect(screen.getByText('No related items found.')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });
});

describe('RelatedDrawer — deduplication', () => {
  it('excludes signal items already shown via FK from "Also Related"', () => {
    // FK has fault with fk-fault-id; signal also has fk-fault-id plus a new manual
    const signalItems: SignalRelatedItem[] = [
      { ...SIGNAL_FAULT, entity_id: 'fk-fault-id' }, // duplicate of FK item
      SIGNAL_MANUAL,                                    // novel
    ];

    renderDrawer({ groups: FK_GROUP_WITH_FAULT, signalItems });

    // Novel manual should appear in signal section
    expect(screen.getByTestId('signal-item-manual-signal-manual-id')).toBeInTheDocument();

    // FK fault should NOT appear in signal section (only via FK group)
    expect(screen.queryByTestId('signal-item-fault-fk-fault-id')).not.toBeInTheDocument();
  });

  it('hides "Also Related" section when all signal items are already in FK groups', () => {
    const signalItems: SignalRelatedItem[] = [
      { ...SIGNAL_FAULT, entity_id: 'fk-fault-id' }, // same id as FK item
    ];

    renderDrawer({ groups: FK_GROUP_WITH_FAULT, signalItems });

    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
    // FK section IS rendered (not an empty state)
    expect(screen.getByText('FK Fault')).toBeInTheDocument();
  });
});

describe('RelatedDrawer — FK and signal together', () => {
  it('renders FK groups above signal section when both have items', () => {
    renderDrawer({ groups: FK_GROUP_WITH_FAULT, signalItems: [SIGNAL_MANUAL] });

    // Both sections present
    expect(screen.getByText('FK Fault')).toBeInTheDocument();
    expect(screen.getByTestId('signal-also-related')).toBeInTheDocument();
    expect(screen.getByTestId('signal-item-manual-signal-manual-id')).toBeInTheDocument();
  });

  it('signal section header shows correct novel item count', () => {
    renderDrawer({ groups: FK_GROUP_WITH_FAULT, signalItems: [SIGNAL_MANUAL, SIGNAL_FAULT] });

    const section = screen.getByTestId('signal-also-related');
    // Both signal items are novel (neither matches the FK fault id)
    expect(within(section).getByText('2')).toBeInTheDocument();
  });

  it('entity_type label renders entity_type with underscores replaced by spaces', () => {
    renderDrawer({ signalItems: [SIGNAL_WORK_ORDER] });

    // entity_type 'work_order' → 'work order' (underscores replaced)
    // subtitle is 'Active' so 'work order' is unambiguous
    expect(screen.getByText('work order')).toBeInTheDocument();
  });
});

describe('RelatedDrawer — loading and error states', () => {
  it('shows FK loading spinner when isLoading=true (signal state irrelevant)', () => {
    renderDrawer({ isLoading: true, signalItems: [SIGNAL_FAULT] });

    expect(screen.getByText('Loading related...')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });

  it('shows FK error message when error prop is set', () => {
    renderDrawer({ error: new Error('Connection refused'), signalItems: [SIGNAL_FAULT] });

    expect(screen.getByText('Failed to load related items')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });

  it('signal error (signalItems absent) does not crash the drawer', () => {
    // When signal hook errors, EntityLensPage passes signalItems=undefined
    renderDrawer({ groups: FK_GROUP_WITH_FAULT, signalItems: undefined, signalLoading: false });

    expect(screen.getByText('FK Fault')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });
});
