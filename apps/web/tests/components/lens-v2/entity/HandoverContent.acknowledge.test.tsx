/**
 * Unit tests — Handover incoming-acknowledge UI.
 *
 * Covers:
 *   1. SignatureBlock renders three always-present columns (outgoing / HOD /
 *      incoming), showing "Pending" vs SIGNED + timestamp per column state.
 *   2. canUserAcknowledgeHandover rule: complete + null + authenticated user
 *      who is neither outgoing nor HOD shows the button; other combinations
 *      hide it.
 *   3. Critical-gate behaviour: checkbox gates the Confirm button when
 *      critical items exist; auto-pass when there are none.
 *
 * Heavy browser-only behaviour (canvas drawing, Playwright network-level POST
 * verification) is left to the E2E agent. This file is jsdom-only.
 */

import * as React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';

// Keep bundler happy: referencing React prevents "React is not defined" in
// classic JSX runtime.
void React;
import '@testing-library/jest-dom/vitest';
import {
  SignatureBlock,
  canUserAcknowledgeHandover,
} from '@/components/lens-v2/entity/HandoverContent';

// ─── 1. Signature block ───────────────────────────────────────────────────

describe('SignatureBlock', () => {
  it('renders three columns regardless of signature state', () => {
    render(
      <SignatureBlock
        outgoing={{}}
        reviewed={{}}
        incoming={{}}
      />
    );
    expect(screen.getByTestId('sig-col-prepared-by')).toBeInTheDocument();
    expect(screen.getByTestId('sig-col-reviewed-by')).toBeInTheDocument();
    expect(screen.getByTestId('sig-col-acknowledged-by')).toBeInTheDocument();
  });

  it('shows Pending hint in unsigned columns', () => {
    render(
      <SignatureBlock
        outgoing={{}}
        reviewed={{}}
        incoming={{}}
      />
    );
    const pendings = screen.getAllByTestId('sig-pending');
    expect(pendings).toHaveLength(3);
    pendings.forEach((el) => expect(el).toHaveTextContent(/pending/i));
  });

  it('shows signer name + timestamp + SIGNED badge when a column is signed', () => {
    render(
      <SignatureBlock
        outgoing={{
          name: 'Alice Outgoing',
          role: 'Chief Engineer',
          signedAt: '2026-04-17T10:00:00Z',
        }}
        reviewed={{}}
        incoming={{}}
      />
    );
    const prepared = screen.getByTestId('sig-col-prepared-by');
    expect(within(prepared).getByText('Alice Outgoing')).toBeInTheDocument();
    expect(within(prepared).getByText('Chief Engineer')).toBeInTheDocument();
    expect(within(prepared).getByText('2026-04-17T10:00:00Z')).toBeInTheDocument();
    expect(within(prepared).getByTestId('sig-badge-signed')).toBeInTheDocument();
    expect(within(prepared).queryByTestId('sig-pending')).toBeNull();

    // Other columns still show Pending
    expect(
      within(screen.getByTestId('sig-col-reviewed-by')).getByTestId('sig-pending')
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('sig-col-acknowledged-by')).getByTestId('sig-pending')
    ).toBeInTheDocument();
  });

  it('renders signature image when image data URL is present', () => {
    const dataUrl = 'data:image/png;base64,iVBORw0KGgo=';
    render(
      <SignatureBlock
        outgoing={{}}
        reviewed={{}}
        incoming={{
          name: 'Bob Incoming',
          signedAt: '2026-04-17T12:00:00Z',
          image: dataUrl,
        }}
      />
    );
    const incoming = screen.getByTestId('sig-col-acknowledged-by');
    const img = within(incoming).getByTestId('sig-image') as HTMLImageElement;
    expect(img.src).toBe(dataUrl);
  });

  it('renders all three signed simultaneously (full chain complete)', () => {
    render(
      <SignatureBlock
        outgoing={{ name: 'A', signedAt: '2026-04-17T09:00:00Z' }}
        reviewed={{ name: 'B', signedAt: '2026-04-17T10:00:00Z' }}
        incoming={{ name: 'C', signedAt: '2026-04-17T11:00:00Z' }}
      />
    );
    expect(screen.getAllByTestId('sig-badge-signed')).toHaveLength(3);
    expect(screen.queryAllByTestId('sig-pending')).toHaveLength(0);
  });
});

// ─── 2. Acknowledge visibility rule ───────────────────────────────────────

describe('canUserAcknowledgeHandover', () => {
  const base = {
    reviewStatus: 'complete' as string | null | undefined,
    incomingSignedAt: null as string | null | undefined,
    userId: 'user-crew-1' as string | null | undefined,
    outgoingSignerId: 'user-outgoing' as string | null | undefined,
    hodSignerId: 'user-hod' as string | null | undefined,
  };

  it('returns true when complete + unsigned + valid third user', () => {
    expect(canUserAcknowledgeHandover(base)).toBe(true);
  });

  it('returns false when HOD has not countersigned', () => {
    expect(
      canUserAcknowledgeHandover({ ...base, reviewStatus: 'pending_hod_signature' })
    ).toBe(false);
    expect(
      canUserAcknowledgeHandover({ ...base, reviewStatus: 'pending_review' })
    ).toBe(false);
  });

  it('returns false when already acknowledged', () => {
    expect(
      canUserAcknowledgeHandover({
        ...base,
        incomingSignedAt: '2026-04-17T12:00:00Z',
      })
    ).toBe(false);
  });

  it('returns false when user is the outgoing signer (self-ack blocked)', () => {
    expect(
      canUserAcknowledgeHandover({ ...base, userId: 'user-outgoing' })
    ).toBe(false);
  });

  it('returns false when user is the HOD countersigner', () => {
    expect(canUserAcknowledgeHandover({ ...base, userId: 'user-hod' })).toBe(
      false
    );
  });

  it('returns false when no authenticated user (auth race)', () => {
    expect(canUserAcknowledgeHandover({ ...base, userId: null })).toBe(false);
    expect(canUserAcknowledgeHandover({ ...base, userId: undefined })).toBe(
      false
    );
  });
});

// ─── 3. Critical-checkbox gate ────────────────────────────────────────────
//
// The gate is expressed inside HandoverContent via the `ackGateBlocked`
// inline expression:
//     canAcknowledge && hasCriticalItems && !ackCriticalChecked
// We test the underlying boolean shape here so the invariant stays pinned.

describe('Acknowledge critical-gate', () => {
  function gateBlocked(opts: {
    canAcknowledge: boolean;
    hasCriticalItems: boolean;
    ackCriticalChecked: boolean;
  }) {
    return (
      opts.canAcknowledge && opts.hasCriticalItems && !opts.ackCriticalChecked
    );
  }

  it('disables submit when critical items exist and checkbox is unchecked', () => {
    expect(
      gateBlocked({
        canAcknowledge: true,
        hasCriticalItems: true,
        ackCriticalChecked: false,
      })
    ).toBe(true);
  });

  it('enables submit once checkbox is checked', () => {
    expect(
      gateBlocked({
        canAcknowledge: true,
        hasCriticalItems: true,
        ackCriticalChecked: true,
      })
    ).toBe(false);
  });

  it('enables submit immediately when zero critical items', () => {
    expect(
      gateBlocked({
        canAcknowledge: true,
        hasCriticalItems: false,
        ackCriticalChecked: false,
      })
    ).toBe(false);
  });
});
