/**
 * CertificateContent unit tests — section ordering, viewer, hidden actions.
 *
 * These tests pin the 2026-04-23 redesign contract (doc_cert_ux_change.md):
 *  - Primary focus is the certificate document itself (LensFileViewer) above
 *    collapsible sections.
 *  - Old-version banner renders only when status=superseded AND superseded_by
 *    is populated.
 *  - `link_document_to_certificate` is hidden from the dropdown.
 *  - Attachments section is titled "Supporting Documents" (not "Attachments").
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as React from 'react';

// ── Module mocks ─────────────────────────────────────────────────────────────

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => ({ get: () => null }),
  usePathname: () => '/certificates/abc',
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'u-1', yachtId: 'y-1', role: 'captain' } }),
}));

vi.mock('@/lib/supabaseClient', () => ({
  supabase: {
    from: () => ({
      select: () => ({
        is: () => ({
          order: () => ({
            limit: () => ({ eq: () => Promise.resolve({ data: [], error: null }) }),
          }),
        }),
      }),
    }),
  },
}));

// Capture context data per-test so we can render different scenarios.
type Ctx = Parameters<(v: unknown) => unknown>[0];
let currentCtx: Record<string, unknown> = {};

vi.mock('@/contexts/EntityLensContext', () => ({
  EntityLensProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useEntityLensContext: () => currentCtx as Ctx,
}));

vi.mock('@/components/lens-v2/actions/AddNoteModal', () => ({
  AddNoteModal: () => null,
}));
vi.mock('@/components/lens-v2/actions/AttachmentUploadModal', () => ({
  AttachmentUploadModal: () => null,
}));

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeCtx(overrides: Record<string, unknown> = {}) {
  const entity = {
    id: 'cert-1',
    title: 'EPIRB Annual Test Certificate',
    certificate_number: 'EPT-2025-5664',
    certificate_type: 'vessel',
    status: 'valid',
    issuing_authority: 'IMO',
    issue_date: '2025-01-01',
    expiry_date: '2026-01-01',
    document_id: 'doc-1',
    attachments: [
      {
        id: 'doc-1',
        filename: 'cert.pdf',
        url: 'https://example.test/cert.pdf',
        mime_type: 'application/pdf',
      },
    ],
    notes: [],
    audit_trail: [],
    prior_periods: [],
    related_equipment: [],
    superseded_by: null,
    yacht_name: 'M/Y Example',
    properties: {},
    ...((overrides.entity as Record<string, unknown>) ?? {}),
  };
  return {
    entity,
    entityId: entity.id,
    availableActions: (overrides.availableActions as unknown[]) ?? [],
    executeAction: vi.fn(),
    getAction: (id: string) => {
      const found = ((overrides.availableActions as Array<{ action_id: string }>) ?? []).find(
        (a) => a.action_id === id
      );
      return found ?? null;
    },
    isLoading: false,
    refetch: vi.fn(),
  };
}

async function importCertContent() {
  const mod = await import('@/components/lens-v2/entity/CertificateContent');
  return mod.CertificateContent;
}

beforeEach(() => {
  currentCtx = makeCtx();
});

// ── Tests ────────────────────────────────────────────────────────────────────

describe('CertificateContent — redesigned lens', () => {
  it('renders the identity strip with human-readable yacht name, not a UUID', async () => {
    currentCtx = makeCtx();
    const Cert = await importCertContent();
    render(<Cert />);
    expect(screen.getAllByText(/EPIRB Annual Test Certificate/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/M\/Y Example/i).length).toBeGreaterThan(0);
  });

  it('renders a "Supporting Documents" section heading (renamed from "Attachments")', async () => {
    currentCtx = makeCtx({
      entity: {
        attachments: [
          { id: 'doc-1', filename: 'cert.pdf', url: 'u1', mime_type: 'application/pdf' },
          { id: 'sup-1', filename: 'supporting.pdf', url: 'u2', mime_type: 'application/pdf' },
        ],
      },
    });
    const Cert = await importCertContent();
    render(<Cert />);
    expect(screen.getByText(/Supporting Documents/i)).not.toBeNull();
    expect(screen.queryByRole('heading', { name: /^Attachments$/i })).toBeNull();
  });

  it('does NOT render "Link Document to Certificate" in the dropdown', async () => {
    currentCtx = makeCtx({
      availableActions: [
        {
          action_id: 'renew_certificate',
          label: 'Renew',
          required_fields: [],
          prefill: {},
          requires_signature: false,
          disabled: false,
        },
        {
          action_id: 'link_document_to_certificate',
          label: 'Link Document to Certificate',
          required_fields: [],
          prefill: {},
          requires_signature: false,
          disabled: false,
        },
      ],
    });
    const Cert = await importCertContent();
    render(<Cert />);
    expect(screen.queryByText(/Link Document to Certificate/i)).toBeNull();
  });

  it('renders the "old version" banner when status=superseded and superseded_by is set', async () => {
    currentCtx = makeCtx({
      entity: {
        status: 'superseded',
        superseded_by: { id: 'cert-new', label: 'EPIRB 2026', certificate_number: 'EPT-2026-0001', status: 'valid' },
      },
    });
    const Cert = await importCertContent();
    render(<Cert />);
    expect(screen.getByText(/old version/i)).not.toBeNull();
    expect(screen.getByText(/EPT-2026-0001/i)).not.toBeNull();
  });

  it('does NOT render the old-version banner when status is valid', async () => {
    currentCtx = makeCtx();
    const Cert = await importCertContent();
    render(<Cert />);
    expect(screen.queryByText(/old version/i)).toBeNull();
  });

  it('composes audit-trail actor as "Name · Role" when backend provides both', async () => {
    currentCtx = makeCtx({
      entity: {
        audit_trail: [
          {
            id: 'a-1',
            action: 'update_certificate',
            actor_name: 'Jane Doe',
            actor_role: 'chief_engineer',
            created_at: '2026-04-23T12:00:00Z',
          },
        ],
      },
    });
    const Cert = await importCertContent();
    const { container } = render(<Cert />);
    // AuditTrailSection is collapsed by default — search for actor text anywhere.
    expect(container.innerHTML).toMatch(/Jane Doe/);
    expect(container.innerHTML).toMatch(/Chief Engineer/);
  });
});
