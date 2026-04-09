/**
 * RelatedDrawer unit tests
 *
 * Signal-only drawer — FK groups removed. Tests cover:
 * - Signal items rendering
 * - Staged progress UI during loading
 * - Empty state when no signal items
 * - Entity type label rendering
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as React from 'react';
import { RelatedDrawer } from '../RelatedDrawer';
import type { SignalRelatedItem } from '@/hooks/useSignalRelated';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

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
  signalItems?: SignalRelatedItem[];
  signalLoading?: boolean;
}) {
  return render(
    <RelatedDrawer
      onNavigate={noop}
      signalItems={props.signalItems}
      signalLoading={props.signalLoading}
    />
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('RelatedDrawer — signal items', () => {
  it('renders "Related" section when signal has items', () => {
    renderDrawer({ signalItems: [SIGNAL_FAULT, SIGNAL_MANUAL] });

    expect(screen.getByTestId('signal-also-related')).toBeInTheDocument();
    expect(screen.getByTestId('signal-item-fault-signal-fault-id')).toBeInTheDocument();
    expect(screen.getByTestId('signal-item-manual-signal-manual-id')).toBeInTheDocument();
  });

  it('does NOT show "No related items found" when signal has items', () => {
    renderDrawer({ signalItems: [SIGNAL_FAULT] });

    expect(screen.queryByText('No related items found.')).not.toBeInTheDocument();
  });

  it('signal section header shows correct item count', () => {
    renderDrawer({ signalItems: [SIGNAL_MANUAL, SIGNAL_FAULT] });

    const section = screen.getByTestId('signal-also-related');
    expect(within(section).getByText('2')).toBeInTheDocument();
  });

  it('entity_type label renders entity_type with underscores replaced by spaces', () => {
    renderDrawer({ signalItems: [SIGNAL_WORK_ORDER] });

    expect(screen.getByText('work order')).toBeInTheDocument();
  });
});

describe('RelatedDrawer — staged progress', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows initial stage label when signal is loading', () => {
    renderDrawer({ signalLoading: true });

    const section = screen.getByTestId('signal-also-related');
    expect(section).toBeInTheDocument();
    expect(within(section).getByTestId('signal-stage-label')).toHaveTextContent('Extracting entity…');
  });

  it('advances to "Generating embedding…" after 800ms', () => {
    renderDrawer({ signalLoading: true });

    act(() => { vi.advanceTimersByTime(800); });

    expect(screen.getByTestId('signal-stage-label')).toHaveTextContent('Generating embedding…');
  });

  it('advances to "Searching entities…" after 3500ms', () => {
    renderDrawer({ signalLoading: true });

    act(() => { vi.advanceTimersByTime(3500); });

    expect(screen.getByTestId('signal-stage-label')).toHaveTextContent('Searching entities…');
  });

  it('advances to "Ranking results…" after 8000ms', () => {
    renderDrawer({ signalLoading: true });

    act(() => { vi.advanceTimersByTime(8000); });

    expect(screen.getByTestId('signal-stage-label')).toHaveTextContent('Ranking results…');
  });
});

describe('RelatedDrawer — empty and edge states', () => {
  it('shows empty state when signal returns no items and not loading', () => {
    renderDrawer({ signalItems: [], signalLoading: false });

    expect(screen.getByText('No related items found.')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });

  it('shows empty state when signalItems prop is absent', () => {
    renderDrawer({});

    expect(screen.getByText('No related items found.')).toBeInTheDocument();
    expect(screen.queryByTestId('signal-also-related')).not.toBeInTheDocument();
  });

  it('signal error (signalItems undefined) does not crash the drawer', () => {
    renderDrawer({ signalItems: undefined, signalLoading: false });

    expect(screen.getByText('No related items found.')).toBeInTheDocument();
  });
});
