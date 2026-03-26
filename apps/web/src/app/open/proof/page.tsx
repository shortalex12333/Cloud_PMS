'use client';

/**
 * PROOF PAGE: Renders SuggestedActions with mock data for every lens
 * to prove it uses the NEW ActionPopup (not old ActionModal).
 *
 * Visit: http://localhost:3000/open/proof
 * No auth required (under /open route).
 */

import React, { useState } from 'react';
import SuggestedActions from '@/components/SuggestedActions';
import type { ActionSuggestion } from '@/lib/actionClient';

const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

const LENS_ACTIONS: { lens: string; actions: ActionSuggestion[] }[] = [
  { lens: 'Work Order', actions: [
    { action_id: 'create_work_order', label: 'Create Work Order', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'priority', 'description'], domain: 'work_orders', match_score: 1.0 },
  ]},
  { lens: 'Fault', actions: [
    { action_id: 'log_fault', label: 'Log Fault', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'description'], domain: 'faults', match_score: 1.0 },
  ]},
  { lens: 'Equipment', actions: [
    { action_id: 'add_note_equipment', label: 'Add Equipment Note', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'note_text'], domain: 'equipment', match_score: 1.0 },
  ]},
  { lens: 'Certificate', actions: [
    { action_id: 'create_vessel_certificate', label: 'Add Certificate', variant: 'SIGNED', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'certificate_type', 'expiry_date'], domain: 'certificates', match_score: 1.0 },
  ]},
  { lens: 'Parts / Inventory', actions: [
    { action_id: 'order_part', label: 'Order Part', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'quantity'], domain: 'inventory', match_score: 1.0 },
  ]},
  { lens: 'Purchase Order', actions: [
    { action_id: 'create_purchase_order', label: 'Create Purchase Order', variant: 'SIGNED', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'description'], domain: 'purchasing', match_score: 1.0 },
  ]},
  { lens: 'Receiving', actions: [
    { action_id: 'confirm_receiving', label: 'Confirm Receiving', variant: 'SIGNED', allowed_roles: ['captain'], required_fields: ['yacht_id', 'reason'], domain: 'receiving', match_score: 1.0 },
  ]},
  { lens: 'Shopping List', actions: [
    { action_id: 'add_to_shopping_list', label: 'Add to Shopping List', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'quantity', 'source_type'], domain: 'shopping', match_score: 1.0 },
  ]},
  { lens: 'Document', actions: [
    { action_id: 'upload_document', label: 'Upload Document', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title'], domain: 'documents', match_score: 1.0 },
  ]},
  { lens: 'Warranty', actions: [
    { action_id: 'file_warranty_claim', label: 'File Warranty Claim', variant: 'MUTATE', allowed_roles: ['captain'], required_fields: ['yacht_id', 'title', 'description'], domain: 'warranties', match_score: 1.0 },
  ]},
  { lens: 'Hours of Rest', actions: [
    { action_id: 'submit_hours_of_rest', label: 'Submit Hours of Rest', variant: 'SIGNED', allowed_roles: ['captain'], required_fields: ['yacht_id', 'reason'], domain: 'hours_of_rest', match_score: 1.0 },
  ]},
  { lens: 'Handover', actions: [
    { action_id: 'sign_handover', label: 'Sign Handover', variant: 'SIGNED', allowed_roles: ['captain'], required_fields: ['yacht_id', 'reason'], domain: 'handover', match_score: 1.0 },
  ]},
];

export default function ProofPage() {
  const [clickLog, setClickLog] = useState<string[]>([]);

  return (
    <div style={{
      fontFamily: 'var(--font-sans, system-ui)',
      background: 'var(--surface-base, #0C0B0A)',
      color: 'var(--txt, rgba(255,255,255,0.92))',
      minHeight: '100vh',
      padding: '40px 20px',
    }}>
      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
          ActionPopup Proof — All 12 Lenses
        </h1>
        <p style={{ fontSize: 13, color: 'var(--txt2, rgba(255,255,255,0.6))', marginBottom: 32 }}>
          Click any action button below. If the <strong>NEW ActionPopup</strong> renders
          (with signature levels, data gates, CSS-module styling from popup.module.css),
          this proves the fix works. The OLD ActionModal had Tailwind classes and no signature support.
        </p>

        {LENS_ACTIONS.map(({ lens, actions }) => (
          <div key={lens} style={{ marginBottom: 24, borderBottom: '1px solid var(--border-faint, rgba(255,255,255,0.05))', paddingBottom: 16 }}>
            <div style={{
              fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase',
              color: 'var(--txt3, rgba(255,255,255,0.36))', marginBottom: 8,
            }}>
              {lens}
            </div>
            <SuggestedActions
              actions={actions}
              yachtId={YACHT_ID}
              query={`test ${lens.toLowerCase()}`}
              onActionComplete={() => {
                setClickLog(prev => [...prev, `${lens}: action completed`]);
              }}
            />
          </div>
        ))}

        {clickLog.length > 0 && (
          <div style={{ marginTop: 32, padding: 16, background: 'var(--surface-el, #1A1714)', borderRadius: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--txt3)', marginBottom: 8 }}>
              Action Log
            </div>
            {clickLog.map((log, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--txt2)', marginBottom: 4 }}>{log}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
