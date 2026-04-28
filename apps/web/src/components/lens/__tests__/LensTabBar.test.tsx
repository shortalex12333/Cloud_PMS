// apps/web/src/components/lens/__tests__/LensTabBar.test.tsx
//
// LensTabBar contract tests — the component is shared across lenses
// (work-orders adopts first in PR-WO-3) so regressions must be caught early.

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import * as React from 'react';
import { LensTabBar, type LensTab } from '../LensTabBar';

function fixture(over: Partial<LensTab>[] = []): LensTab[] {
  const defaults: LensTab[] = [
    { key: 'checklist', label: 'Checklist', count: 4 },
    { key: 'notes',     label: 'Notes',     count: 0 },
    { key: 'safety',    label: 'Safety',    disabled: true, disabledReason: 'PR-WO-4' },
  ];
  // merge
  return defaults.map((d, i) => ({ ...d, ...(over[i] ?? {}) }));
}

describe('LensTabBar', () => {
  it('renders every tab with aria-selected and aria-controls wired', () => {
    render(
      <LensTabBar
        tabs={fixture()}
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    expect(screen.getAllByRole('tab')).toHaveLength(3);
    expect(screen.getByRole('tab', { name: /Checklist/ }).getAttribute('aria-selected')).toBe('true');
    expect(screen.getByRole('tab', { name: /Notes/ }).getAttribute('aria-selected')).toBe('false');
    // body shows initial active tab
    expect(screen.getByTestId('body').textContent).toBe('checklist');
  });

  it('suppresses count badge when count === 0', () => {
    render(<LensTabBar tabs={fixture()} renderBody={() => null} />);
    // Checklist count=4 should render the badge
    const checklistBtn = screen.getByRole('tab', { name: /Checklist/ });
    expect(checklistBtn.textContent).toContain('4');
    // Notes count=0 should NOT render a badge
    const notesBtn = screen.getByRole('tab', { name: /^Notes$/ });
    expect(notesBtn.textContent).toBe('Notes');
  });

  it('renders disabled tabs with aria-disabled and does not activate on click', () => {
    const onChange = vi.fn();
    render(
      <LensTabBar tabs={fixture()} onChange={onChange} renderBody={() => null} />,
    );
    const safety = screen.getByRole('tab', { name: /Safety/ }) as HTMLButtonElement;
    expect(safety.getAttribute('aria-disabled')).toBe('true');
    expect(safety.disabled).toBe(true);
    fireEvent.click(safety);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('fires onChange and switches body when a tab is clicked', () => {
    const onChange = vi.fn();
    render(
      <LensTabBar
        tabs={fixture()}
        onChange={onChange}
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    fireEvent.click(screen.getByRole('tab', { name: /^Notes$/ }));
    expect(onChange).toHaveBeenCalledWith('notes');
    expect(screen.getByTestId('body').textContent).toBe('notes');
  });

  it('ArrowRight/ArrowLeft wrap through enabled tabs, skipping disabled', () => {
    render(
      <LensTabBar
        tabs={fixture()}
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    const tablist = screen.getByRole('tablist');
    fireEvent.keyDown(tablist, { key: 'ArrowRight' });
    expect(screen.getByTestId('body').textContent).toBe('notes');
    // ArrowRight from last enabled tab wraps to first; disabled Safety skipped
    fireEvent.keyDown(tablist, { key: 'ArrowRight' });
    expect(screen.getByTestId('body').textContent).toBe('checklist');
    fireEvent.keyDown(tablist, { key: 'ArrowLeft' });
    expect(screen.getByTestId('body').textContent).toBe('notes');
  });

  it('controlled mode reflects activeKey prop and ignores internal state', () => {
    const { rerender } = render(
      <LensTabBar
        tabs={fixture()}
        activeKey="notes"
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    expect(screen.getByTestId('body').textContent).toBe('notes');
    // Clicking in controlled mode calls onChange but doesn't flip state unless parent updates
    const onChange = vi.fn();
    rerender(
      <LensTabBar
        tabs={fixture()}
        activeKey="notes"
        onChange={onChange}
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    fireEvent.click(screen.getByRole('tab', { name: /Checklist/ }));
    expect(onChange).toHaveBeenCalledWith('checklist');
    // body still shows notes because parent didn't re-render with new activeKey
    expect(screen.getByTestId('body').textContent).toBe('notes');
  });

  it('falls back to first enabled tab if defaultActiveKey is absent', () => {
    const onlyFirstDisabled: LensTab[] = [
      { key: 'a', label: 'A', disabled: true },
      { key: 'b', label: 'B' },
      { key: 'c', label: 'C' },
    ];
    render(
      <LensTabBar
        tabs={onlyFirstDisabled}
        renderBody={(key) => <div data-testid="body">{key}</div>}
      />,
    );
    expect(screen.getByTestId('body').textContent).toBe('b');
  });
});
